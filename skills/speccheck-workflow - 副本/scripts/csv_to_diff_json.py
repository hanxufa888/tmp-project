#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csv_to_diff_json.py

Step1(チェック対象データの作成) 手順1 用スクリプト（CSV入力版）。

`spec2model-cloud-diff` / `spec2model-local-diff` の出力である差分CSV
（`specification_check/output/spec_diff.csv`。`compare_documents()` の生の差分行を
`apply_default_diff_filters` 適用後に `to_csv` したもの）を取り込み、
後続手順の入力として使用する JSON ファイル（8キー）へ変換する。

従来の差分Excel（`batch_diff_html_reports.py` がこのCSVから生成していた中間物）を
経由せず、CSVから直接 JSON 化する。列対応は当該Excel生成ロジック
（batch_diff_html_reports.py の append_diffs_to_worksheet）を忠実に踏襲する。

入力CSVの主な列（spec2model diff 共通スキーマ。順不同・欠落は空文字扱い）:
    file_old, file_new,
    scope, sheet_name,
    chapter_key, chapter_title_old, chapter_title_new,
    paragraph_key, paragraph_title_old, paragraph_title_new,
    block_type, granularity, change_type,
    before_markdown, after_markdown, ...

出力JSONの各レコードのキー（8キー）:
    file_old, sheet_old, chapter_old,
    file_new, sheet_new, chapter_new,
    before_markdown, after_markdown

列対応:
    file_old        <- basename(file_old)
    sheet_old       <- sheet_name
    chapter_old     <- 最初に非空となる値: paragraph_title_old / chapter_title_old
                       / paragraph_key / chapter_key
    file_new        <- basename(file_new)
    sheet_new       <- sheet_name
    chapter_new     <- 最初に非空となる値: paragraph_title_new / chapter_title_new
                       / paragraph_key / chapter_key
    before_markdown <- before_markdown
    after_markdown  <- after_markdown

- CSVの1行 = 変更ブロック単位（TextBlock/TableRow）の差分。
- 【末端段落ノード単位の統合（既定ON。--no-coalesce で無効化）】
    spec2model diff は TextBlock（段落）単位で差分を出すため、1つの末端段落に対する
    1回の編集（例: プレースホルダ "T.B.D" → 複数行の記載）が「削除1＋追加N」等の
    複数レコードに過分割されることがある。これを是正するため、block_type=="text" の行のうち、
    同一の (file_old, file_new, sheet_name, chapter_key, order_path親) を共有する行を
    1レコードへ統合する（before は before_markdown を、after は after_markdown を、
    order_path/block_order 順に原文のまま改行連結。要約・改変・並べ替えはしない）。
    - 統合キーに order_path親（末端段落ノード）を用いるため、同名末端段落が親章節配下に
      複数存在しても（例: メータ演算タイプ／EFI演算タイプの各「(3)リセット処理」）、
      実際に変更のあった出現のみが統合対象となり、他出現（別ノード）は巻き込まない。
      → 独立した変更は分割保持されたまま（章節単位への集約はしない）。
    - block_type!="text"（TableRow 等）や order_path に親が無い行は統合対象外（各1レコード）。
- 行の抽出・破棄・要約・改変は行わない（各セルの値そのものは保持し、統合時も原文を連結するのみ）。

使い方（プロジェクトの .claude を起点に実行。cd は不要。パスは .claude からの相対）:
    python skills/speccheck-workflow/scripts/csv_to_diff_json.py \
        --in "specification_check/output/spec_diff.csv" \
        --out "specification_check/output/spec_diff.json"

変更前・変更後の仕様書が複数ファイル構成（本体＋添付資料 等）の場合:
    spec2model-local-diff / spec2model-cloud-diff は「1ファイル対1ファイル」でしか
    差分できないため、同一種別ファイルのペアごとに差分CSVを個別生成する
    （本体=spec_diff_body.csv、添付資料=spec_diff_appendix_<n>.csv 等の固定名）。
    それらペア別CSVは、CSV自体は結合せず本スクリプトの JSON化時に統合する
    （JSONレコードを連結するため、CSV本文セルの埋め込み改行に依存した破損が起きない）。
    `--in` は複数回指定でき、各値は**グロブパターン**として展開される。添付資料が
    複数（2〜3個等）でも `spec_diff_appendix_*.csv` の1パターンでまとめて取り込める。
    差分0件でCSV未生成のペア（グロブが0件一致）は、警告を出してスキップする
    （`diff_documents.py` は差分0件のときCSVを出力せず early return するため）。
    `--in` の指定順、同一パターン内はファイル名昇順でレコードを連結する
    （並べ替え・集約はしない）:

    python skills/speccheck-workflow/scripts/csv_to_diff_json.py \
        --in "specification_check/output/spec_diff_body.csv" \
        --in "specification_check/output/spec_diff_appendix_*.csv" \
        --out "specification_check/output/spec_diff.json"

依存: 標準ライブラリのみ（csv / glob / json / argparse / pathlib / re）。
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from pathlib import Path

# 出力JSONの各レコードのキー。
OUTPUT_KEYS = [
    "file_old",
    "sheet_old",
    "chapter_old",
    "file_new",
    "sheet_new",
    "chapter_new",
    "before_markdown",
    "after_markdown",
]

# chapter_old / chapter_new を決める優先順（batch_diff_html_reports の
# before_section_list / after_section_list と同一）。最初に非空となった値を採用する。
CHAPTER_OLD_KEYS = [
    "paragraph_title_old",
    "chapter_title_old",
    "paragraph_key",
    "chapter_key",
]
CHAPTER_NEW_KEYS = [
    "paragraph_title_new",
    "chapter_title_new",
    "paragraph_key",
    "chapter_key",
]

# JSON化に最低限必要な列（存在検証用。1つも無ければ入力CSVの取り違えを疑う）。
CORE_COLUMNS = ["before_markdown", "after_markdown"]

# ファイルパス区切り（Windows/Posix 双方）。basename 抽出に用いる。
_PATH_SEP_RE = re.compile(r"[\\/]")


def cell_to_str(value) -> str:
    """セル値を文字列へ正規化する（None は空文字、それ以外はそのまま文字列化）。"""
    if value is None:
        return ""
    return str(value)


def basename(value: str) -> str:
    """ファイルパスの末尾要素（ファイル名）を返す。空文字はそのまま返す。

    Windows(\\)・Posix(/) どちらの区切りにも対応する。
    """
    s = cell_to_str(value)
    if s == "":
        return ""
    return _PATH_SEP_RE.split(s)[-1]


def pick_section(row: dict, keys: list[str]) -> str:
    """keys を優先順に走査し、最初に非空となった値を返す（無ければ空文字）。"""
    for k in keys:
        val = cell_to_str(row.get(k))
        if val != "":
            return val
    return ""


def order_path_parent(value) -> str | None:
    """order_path の親（末端の1セグメントを除いたパス）を返す。

    例: "000/005/006/001" -> "000/005/006"（末端段落ノード）。
    空、または区切り "/" を含まない（親が無い）場合は None を返し、統合対象外とする。
    """
    s = cell_to_str(value).strip()
    if s == "" or "/" not in s:
        return None
    return s.rsplit("/", 1)[0]


def row_to_record(row: dict) -> dict[str, str]:
    """CSVの1行を出力JSONの8キーのレコードへ変換する（統合しない場合）。"""
    return {
        "file_old": basename(row.get("file_old")),
        "sheet_old": cell_to_str(row.get("sheet_name")),
        "chapter_old": pick_section(row, CHAPTER_OLD_KEYS),
        "file_new": basename(row.get("file_new")),
        "sheet_new": cell_to_str(row.get("sheet_name")),
        "chapter_new": pick_section(row, CHAPTER_NEW_KEYS),
        "before_markdown": cell_to_str(row.get("before_markdown")),
        "after_markdown": cell_to_str(row.get("after_markdown")),
    }


def coalesce_group(rows: list[dict]) -> dict[str, str]:
    """同一末端段落ノードの複数行（block_type=text）を1レコードへ統合する。

    before は before_markdown を、after は after_markdown を、order_path/block_order 順に
    原文のまま改行連結する（空文字はスキップ。要約・改変・並べ替えはしない）。
    メタ情報（file/sheet/chapter）は先頭行から採る（グループ内は同一ノード＝共通）。
    """
    ordered = sorted(
        rows,
        key=lambda r: (
            cell_to_str(r.get("order_path")),
            cell_to_str(r.get("block_order")),
        ),
    )
    before_parts = [
        cell_to_str(r.get("before_markdown"))
        for r in ordered
        if cell_to_str(r.get("before_markdown")) != ""
    ]
    after_parts = [
        cell_to_str(r.get("after_markdown"))
        for r in ordered
        if cell_to_str(r.get("after_markdown")) != ""
    ]
    head = ordered[0]
    return {
        "file_old": basename(head.get("file_old")),
        "sheet_old": cell_to_str(head.get("sheet_name")),
        "chapter_old": pick_section(head, CHAPTER_OLD_KEYS),
        "file_new": basename(head.get("file_new")),
        "sheet_new": cell_to_str(head.get("sheet_name")),
        "chapter_new": pick_section(head, CHAPTER_NEW_KEYS),
        "before_markdown": "\n".join(before_parts),
        "after_markdown": "\n".join(after_parts),
    }


def expand_inputs(patterns: list[str]) -> list[Path]:
    """`--in` のパターン列をグロブ展開し、実在CSVのパス列を返す。

    - 各パターンをグロブ展開する（リテラルパスは自身に一致、非実在は0件）。
    - パターンの指定順を保持しつつ、同一パターン内はファイル名昇順で連結する。
    - 重複パス（別パターンで再一致）は初出のみ残す。
    - 0件一致のパターンは警告してスキップする（差分0件でCSV未生成のペア等）。
    """
    seen: set[str] = set()
    result: list[Path] = []
    for pat in patterns:
        matches = sorted(glob.glob(pat))
        if not matches:
            sys.stderr.write(
                f"[warn] 一致する差分CSVがありません（差分0件でCSV未生成の可能性）: {pat}\n"
            )
            continue
        for m in matches:
            key = str(Path(m).resolve())
            if key in seen:
                continue
            seen.add(key)
            result.append(Path(m))
    return result


def count_csv_rows(in_path: Path) -> int:
    """CSVのデータ行数（ヘッダを除く）を返す（統合前後の件数比較ログ用）。"""
    with in_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def read_records(in_path: Path, coalesce: bool = True) -> list[dict[str, str]]:
    """1つのCSVを読み込み、出力JSONの8キーのレコード列へ変換して返す。

    必要列（before_markdown / after_markdown）が無い場合は ValueError を送出する。

    coalesce=True（既定）では、block_type=="text" の行のうち同一末端段落ノード
    （(file_old, file_new, sheet_name, chapter_key, order_path親) が一致）を1レコードへ
    統合する（過分割の是正）。統合対象外の行・非textブロックは1行=1レコードのまま。
    行の走査順（CSVの並び）を保持し、並べ替え・集約（章節単位への統合）はしない。
    """
    with in_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing_core = [c for c in CORE_COLUMNS if c not in fieldnames]
        if missing_core:
            raise ValueError(
                f"入力CSVに必要な列が見つかりません: {missing_core}\n"
                f"  ファイル: {in_path}\n"
                f"  検出した列: {fieldnames}\n"
                "  spec2model-cloud-diff / spec2model-local-diff の出力CSVを指定してください。"
            )
        rows = list(reader)

    if not coalesce:
        return [row_to_record(row) for row in rows]

    # 走査順を保持したままグループ化する（dict は挿入順を保持）。
    # 統合対象（block_type=text かつ order_path親あり）は末端段落ノード単位で束ね、
    # それ以外は行ごとにユニークキーを与えて統合対象から外す。
    groups: dict[object, list[dict]] = {}
    for i, row in enumerate(rows):
        block_type = cell_to_str(row.get("block_type")).strip().lower()
        parent = order_path_parent(row.get("order_path"))
        if block_type == "text" and parent is not None:
            key = (
                "G",
                basename(row.get("file_old")),
                basename(row.get("file_new")),
                cell_to_str(row.get("sheet_name")),
                cell_to_str(row.get("chapter_key")),
                parent,
            )
        else:
            key = ("U", i)  # ユニーク＝統合しない
        groups.setdefault(key, []).append(row)

    records: list[dict[str, str]] = []
    for grp in groups.values():
        if len(grp) == 1:
            records.append(row_to_record(grp[0]))
        else:
            records.append(coalesce_group(grp))
    return records


def convert(in_paths: list[Path], out_path: Path, coalesce: bool = True) -> int:
    all_records: list[dict[str, str]] = []
    used = 0
    for p in in_paths:
        try:
            raw_count = count_csv_rows(p)
            records = read_records(p, coalesce=coalesce)
        except ValueError as e:
            sys.stderr.write(f"[error] {e}\n")
            return 2
        all_records.extend(records)
        used += 1
        if coalesce and raw_count != len(records):
            sys.stderr.write(
                f"[info] 取り込み: {p} (CSV行数={raw_count} → レコード={len(records)}"
                f"; 末端段落ノード単位で統合={raw_count - len(records)}件分)\n"
            )
        else:
            sys.stderr.write(f"[info] 取り込み: {p} (行数={len(records)})\n")

    if used == 0:
        # 有効な差分CSVが1件も無い＝全ペアが差分0件、または入力指定の誤り。
        sys.stderr.write(
            "[error] 取り込める差分CSVが1件もありませんでした"
            "（全ペアが差分0件、または --in の指定誤りの可能性）。\n"
        )
        return 3

    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sys.stderr.write(
        f"[done] JSON を出力しました: {out_path} "
        f"(取り込みCSV数={used}, 要素数={len(all_records)})\n"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="spec2model diff の差分CSVを後続手順用のJSONへ変換する。"
    )
    p.add_argument(
        "--in",
        dest="in_patterns",
        action="append",
        required=True,
        metavar="CSV_OR_GLOB",
        help=(
            "入力CSVパスまたはグロブパターン（複数回指定可）。単一ファイル構成では "
            "specification_check/output/spec_diff.csv を1つ指定。複数ファイル構成では "
            "本体と添付資料のペア別CSVを複数指定する"
            "（例: --in .../spec_diff_body.csv --in .../spec_diff_appendix_*.csv）。"
        ),
    )
    p.add_argument(
        "--out",
        default="diff.json",
        help="出力 JSON パス (既定: diff.json)",
    )
    p.add_argument(
        "--no-coalesce",
        dest="coalesce",
        action="store_false",
        default=True,
        help=(
            "末端段落ノード単位のTextBlock統合を無効化し、CSVの1行=1レコードのまま出力する"
            "（既定は統合ON。過分割是正を無効にしたい場合のみ指定）。"
        ),
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    in_paths = expand_inputs(args.in_patterns)
    if not in_paths:
        sys.stderr.write(
            "[error] 入力CSVが1件も見つかりません（--in の指定を確認してください）。\n"
        )
        return 2
    return convert(in_paths, Path(args.out).expanduser(), coalesce=args.coalesce)


if __name__ == "__main__":
    raise SystemExit(main())
