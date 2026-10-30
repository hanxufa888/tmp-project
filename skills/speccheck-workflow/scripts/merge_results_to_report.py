#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""merge_results_to_report.py

Step3(サブエージェントによるチェック実施) → Step4(結果集約・レポート出力) の
「サブエージェント出力をファイルとして収集し、機械的に集約する」ための集約スクリプト。

各サブエージェントは自身の判定結果を JSON ファイル(res_XXXXX.json 等)として
resultsdir へ書き出し、親エージェントはその中身を読み込まず本スクリプトへ集約を委ねる。
本スクリプトが全結果ファイルを機械的に集約して Step4 のレポート(Markdown)を生成する。
これにより親エージェントのコンテキスト消費を軽量に保つ。
生成した Markdown はさらに report_md_to_xlsx.py で Excel へ変換する。

■ ファイル名の一意性(並列書き込みの衝突回避)
  - 通常差分フロー: 1サブエージェント=1差分レコード。ファイル名キーは差分レコードの
    `index`(Step2 split で確定済み)。例: res_00007.json。
  - 新設・ファイル追加(new_spec)のチャンク起動: 1サブエージェント=複数章節レコード。
    ファイル名キーはチャンクID。例: res_chunk_000.json。
  いずれも「ファイル名=どのサブエージェントが書いたか」の一意性のみを担保し、
  レポート各行の論理キーは中身の (index, checkno) で担保する(重複検知・行順の決定に使用)。

■ 結果ファイルのスキーマ(サブエージェントが書き出す)
  {
    "index": 7,                      // 通常フロー: 担当差分レコードの index
                                     //   (省略時はファイル名 res_XXXXX.json から補完)
    "results": [                     // 1差分に複数 checkno があれば複数要素(1要素=レポート1行)
      {
        "index": 7,                  // new_spec チャンクで1ファイルに複数章節を含む場合は
                                     //   各結果ごとに index(章節)を持たせる(任意)
        "checkno": "CHK-076",        // → 列「チェック項目No.」
        "check_item": "…",           // → 列「チェック項目」(任意。空/未指定なら checkno から
                                     //   check/CHK-*.md の「# チェック項目」本文を機械補完する)
        "target_file": "PF_METER.docx", // → 列「対象ファイル名」
        "sheet": "…",                // → 列「対象シート」
        "chapter": "…",              // → 列「対象章節番号」
        "excerpt": "…原文…",         // → 列「該当記述」(原文のまま。改行・パイプもそのまま)
        "judgement": "問題あり",      // → 列「AI判定結果」(問題あり/問題なし/要確認)
        "reason": "…"                // → 列「AI判定理由」
      }
    ]
  }
  - excerpt/reason 等の原文は JSON 文字列としてそのまま(生の改行・パイプ可)保持する。
    Markdown への変換時に、本スクリプトが改行を <br>、パイプを \| へ機械エスケープする
    (report_md_to_xlsx.py が Excel セルへ復元する)。サブエージェント側は原文をそのまま格納する。

使い方（プロジェクトの .claude を起点に実行。cd は不要。パスは .claude からの相対）:
    python skills/speccheck-workflow/scripts/merge_results_to_report.py \
        --resultsdir "specification_check/output/<仕様書名>_check_results" \
        --out "specification_check/output/<仕様書名>_report.md" \
        --spec-name "<仕様書名>" \
        --diff "specification_check/output/spec_diff.json"   # 任意(欠落検知)。通常差分フロー: spec_diff.json / 新設・ファイル追加フロー: <仕様書名>_newspec.json

■ 出力フォーマット
  - 既定は通常フォーマット(13列: … 最終判定 / 判定理由 / 実施者 / 確認者 / 承認者)。
  - ユーザープロンプトで「精度検証用フォーマット」での出力指示があった場合は --accuracy-format を付与し、
    精度検証(AI判定の正誤ラベリング)用の列構成(14列: … チェック選定正誤判定 / チェック結果正誤判定 / 判定理由 / 実施者 / 確認者 / 期待チェックフラグ)で出力する。

生成された Markdown は続けて Excel へ変換する:
    python skills/speccheck-workflow/scripts/report_md_to_xlsx.py \
        --in "specification_check/output/<仕様書名>_report.md" \
        --out "specification_check/output/<仕様書名>_report.xlsx"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# レポート結果テーブルの列定義(templates/report_format.md と一致させること)。
# 先頭8列はサブエージェント結果から埋め、残りは人手記載のため空欄で出力する。
# 2種類のフォーマットを切り替える:
#   - 既定(COLUMNS): 通常の納品フォーマット(13列)。
#   - 精度検証用(COLUMNS_ACCURACY): --accuracy-format 指定時。AI判定の正誤ラベリング用の列構成(14列)。
#     ユーザープロンプトで「精度検証用フォーマット」での出力指示があった場合に使用する。
COLUMNS = [
    "チェック項目No.",
    "チェック項目",
    "対象ファイル名",
    "対象シート",
    "対象章節番号",
    "該当記述",
    "AI判定結果",
    "AI判定理由",
    "最終判定",
    "判定理由",
    "実施者",
    "確認者",
    "承認者",
]

# 精度検証用フォーマット(AI判定の正誤ラベリング用の列構成)。先頭8列は COLUMNS と共通。
COLUMNS_ACCURACY = [
    "チェック項目No.",
    "チェック項目",
    "対象ファイル名",
    "対象シート",
    "対象章節番号",
    "該当記述",
    "AI判定結果",
    "AI判定理由",
    "チェック選定正誤判定",
    "チェック結果正誤判定",
    "判定理由",
    "実施者",
    "確認者",
    "期待チェックフラグ",
]

# サブエージェント結果(JSON)のキー → レポート列(先頭8列)の対応。
FIELD_TO_COL = {
    "チェック項目No.": ("checkno",),
    "チェック項目": ("check_item", "チェック項目"),
    "対象ファイル名": ("target_file", "対象ファイル名"),
    "対象シート": ("sheet", "対象シート"),
    "対象章節番号": ("chapter", "対象章節番号"),
    "該当記述": ("excerpt", "該当記述"),
    "AI判定結果": ("judgement", "判定結果", "AI判定結果"),
    "AI判定理由": ("reason", "判定理由", "AI判定理由"),
}

RESULT_GLOB = "res_*.json"
# ファイル名 res_00007.json から index=7 を取り出す(res_chunk_000.json 等は対象外)。
_REC_INDEX_RE = re.compile(r"^res_(\d+)\.json$", re.IGNORECASE)

# 列「チェック項目」の機械補完用。
#   サブエージェント結果の check_item が空の場合、checkno から
#   check/CHK-*.md の「# チェック項目」本文を引いて補完する。
_CHK_MD_GLOB = "CHK-*.md"
# 既定の CHK 定義フォルダ(MET-G を含まない仕様書向け)。MET-G 系は --check-dir で MET-G_check を指定する。
DEFAULT_CHECK_DIR = Path(__file__).resolve().parent.parent / "check"


def _is_h1(stripped_line: str) -> bool:
    """Markdown の最上位見出し( "# " で始まり "## " ではない )か判定する。"""
    return stripped_line.startswith("# ") and not stripped_line.startswith("## ")


def _extract_h1_section(md_text: str, heading_predicate) -> str:
    """指定した最上位見出し(H1)の本文を、次のH1直前まで抽出して返す。"""
    capturing = False
    body: list[str] = []
    for line in md_text.splitlines():
        stripped = line.strip()
        if _is_h1(stripped):
            heading = stripped[2:].strip()
            if capturing:
                break  # 次のH1に到達したので終了
            if heading_predicate(heading):
                capturing = True
            continue
        if capturing:
            body.append(line)
    return "\n".join(body).strip()


def _parse_checkno_from_md(md_text: str, fallback: str) -> str:
    """「# チェック項目No.」本文の最初の非空行を checkno として返す。無ければ fallback。"""
    section = _extract_h1_section(
        md_text, lambda h: h.replace(" ", "").startswith("チェック項目No")
    )
    for line in section.splitlines():
        if line.strip():
            return line.strip()
    return fallback


def _parse_check_item_from_md(md_text: str) -> str:
    """「# チェック項目」本文をそのまま(原文)返す。"""
    return _extract_h1_section(md_text, lambda h: h == "チェック項目")


def _build_check_item_map(check_dir: Path) -> dict[str, str]:
    """check_dir 配下の CHK-*.md を走査し、checkno → 「# チェック項目」本文 の対応を作る。"""
    mapping: dict[str, str] = {}
    if not check_dir.is_dir():
        return mapping
    for path in sorted(check_dir.glob(_CHK_MD_GLOB)):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        checkno = _parse_checkno_from_md(text, path.stem)
        item = _parse_check_item_from_md(text)
        if checkno and item:
            mapping[checkno.strip()] = item
    return mapping


def _load_json(path: Path):
    # utf-8-sig: BOM 付き(一部ツール/エディタが付与)・BOM無しの双方を許容する。
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def _cell(value) -> str:
    """セル値を Markdown テーブル1物理行に収める。

    - None/欠損は空文字。
    - 生の改行(\\r\\n / \\r / \\n)は <br> へ変換(1結果=1物理行を保つ)。
    - パイプ | は \\| へエスケープ(report_md_to_xlsx.py がリテラル | へ復元)。
    値そのものの要約・改変は行わない(エスケープのみ)。
    """
    if value is None:
        s = ""
    elif isinstance(value, (list, dict)):
        s = json.dumps(value, ensure_ascii=False)
    else:
        s = str(value)
    s = s.replace("|", "\\|")
    s = re.sub(r"\r\n|\r|\n", "<br>", s)
    return s


def _pick(obj: dict, keys: tuple[str, ...]) -> str:
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return ""


def _iter_result_rows(resultsdir: Path, check_item_map: dict[str, str] | None = None):
    """resultsdir 配下の全結果ファイルを読み、(index, order, row_dict) を列挙する。

    row_dict は列名→生値(未エスケープ)。index はソート/欠落検知用。
    check_item_map が与えられた場合、結果の check_item が空なら checkno から
    「# チェック項目」本文を補完する。
    """
    files = sorted(resultsdir.glob(RESULT_GLOB))
    seen_keys: dict[tuple, int] = {}
    dup_keys: list[tuple] = []
    found_indices: set[int] = set()
    rows: list[tuple[int, int, str, dict]] = []
    load_errors: list[str] = []

    for path in files:
        try:
            obj = _load_json(path)
        except (json.JSONDecodeError, OSError) as e:
            load_errors.append(f"{path.name}: {e}")
            continue

        # ファイル名由来の index(res_XXXXX.json のみ)。チャンク等は None。
        m = _REC_INDEX_RE.match(path.name)
        file_index = int(m.group(1)) if m else None

        if isinstance(obj, dict):
            base_index = obj.get("index", file_index)
            results = obj.get("results")
            if results is None:
                # results を持たない単一結果ファイルにも後方互換で対応する。
                results = [obj]
        elif isinstance(obj, list):
            base_index = file_index
            results = obj
        else:
            load_errors.append(f"{path.name}: 未対応のJSON形式(オブジェクト/配列のみ)")
            continue

        if not isinstance(results, list):
            load_errors.append(f"{path.name}: results は配列である必要があります")
            continue

        for order, res in enumerate(results):
            if not isinstance(res, dict):
                load_errors.append(
                    f"{path.name}[{order}]: 結果要素はオブジェクトである必要があります"
                )
                continue
            idx = res.get("index", base_index)
            idx_sort = (
                idx
                if isinstance(idx, int)
                else (file_index if file_index is not None else 10**9)
            )
            if isinstance(idx, int):
                found_indices.add(idx)
            checkno = _pick(res, FIELD_TO_COL["チェック項目No."])
            key = (idx, str(checkno))
            if key in seen_keys:
                dup_keys.append(key)
            else:
                seen_keys[key] = 1
            row = {col: _pick(res, keys) for col, keys in FIELD_TO_COL.items()}
            # 列「チェック項目」が空なら CHK 定義の「# チェック項目」本文で補完。
            if check_item_map:
                if not str(row.get("チェック項目") or "").strip():
                    filled = check_item_map.get(str(checkno).strip())
                    if filled:
                        row["チェック項目"] = filled
            rows.append((idx_sort, order, path.name, row))

    # index 昇順 → 同一index内はファイル内の記載順(order) → ファイル名 の安定ソート。
    rows.sort(key=lambda t: (t[0], t[2], t[1]))
    return rows, found_indices, dup_keys, load_errors


def _expected_indices_from_diff(diff_path: Path) -> set[int]:
    """diff.json から、結果ファイルが存在すべき index 集合を求める。

    excluded が True でなく、かつ checkno が非空のレコードが Step3 のチェック対象。
    """
    records = _load_json(diff_path)
    expected: set[int] = set()
    if not isinstance(records, list):
        return expected
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        if rec.get("excluded") is True:
            continue
        checkno = rec.get("checkno")
        if isinstance(checkno, list) and len(checkno) > 0:
            expected.add(i)
    return expected


def _render_markdown(rows, spec_name: str, columns: list[str]) -> str:
    lines: list[str] = []
    lines.append("# AIチェック結果レポート")
    lines.append("")
    if spec_name:
        lines.append(f"- 対象仕様書: {spec_name}")
    lines.append(f"- チェック結果件数: {len(rows)}")
    lines.append("")
    lines.append("## 結果出力")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    if rows:
        for _idx, _order, _fname, row in rows:
            cells = [_cell(row.get(col, "")) for col in columns]
            lines.append("| " + " | ".join(cells) + " |")
    else:
        # チェック対象の差分が0件の場合。空テーブル(ヘッダーのみ)を出力する。
        lines.append(f"| {'(チェック対象の差分なし)'} |" + " |" * (len(columns) - 1))
    lines.append("")
    lines.append("## 判定ラベルの定義")
    lines.append(
        "- **問題あり**: チェック基準のいずれかの手順で「問題あり」と判定した場合"
    )
    lines.append("- **問題なし**: チェック基準の全ての項目で「問題なし」と判定した場合")
    lines.append("- **要確認**: 情報不足等により判定できない場合")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Step3 のサブエージェント結果(JSON群)を集約して Step4 レポート(Markdown)を生成する。"
    )
    p.add_argument(
        "--resultsdir",
        required=True,
        help="サブエージェント結果(res_*.json)の格納ディレクトリ",
    )
    p.add_argument("--out", required=True, help="出力 Markdown レポートのパス")
    p.add_argument(
        "--spec-name", default="", help="対象仕様書の代表名(レポート見出しに記載)"
    )
    p.add_argument(
        "--diff",
        default=None,
        help="任意: Step2出力 diff.json。結果ファイルの欠落検知に使用",
    )
    p.add_argument(
        "--check-dir",
        default=str(DEFAULT_CHECK_DIR),
        help="CHK-*.md 格納フォルダ(列「チェック項目」の補完用)。既定は speccheck-workflow/check。"
        "MET-G を含む仕様書のチェックでは speccheck-workflow/MET-G_check を指定する。",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="欠落/重複/読込失敗がある場合に非0で終了する",
    )
    p.add_argument(
        "--accuracy-format",
        action="store_true",
        help="精度検証用フォーマット(AI判定の正誤をラベリングするための列構成: 先頭8列に加え チェック選定正誤判定/チェック結果正誤判定/判定理由/実施者/確認者/期待チェックフラグ の計14列)で出力する。"
        "ユーザープロンプトで「精度検証用フォーマット」の指示があった場合に付与する。既定は通常フォーマット。",
    )
    args = p.parse_args(argv)

    resultsdir = Path(args.resultsdir)
    if not resultsdir.is_dir():
        print(
            f"[merge] エラー: 結果ディレクトリが見つかりません: {resultsdir}",
            file=sys.stderr,
        )
        return 2

    # 案X: checkno → 「# チェック項目」本文 のマップを作り、空の check_item を補完する。
    check_dir = Path(args.check_dir)
    check_item_map = _build_check_item_map(check_dir)
    if not check_item_map:
        print(
            f"[merge] 注意: CHK定義が読めず check_item 補完をスキップします(check-dir={check_dir})",
            file=sys.stderr,
        )

    rows, found_indices, dup_keys, load_errors = _iter_result_rows(
        resultsdir, check_item_map
    )

    columns = COLUMNS_ACCURACY if args.accuracy_format else COLUMNS

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        _render_markdown(rows, args.spec_name, columns), encoding="utf-8"
    )

    print(f"[merge] レポートを出力しました: {out_path}  (結果行数={len(rows)})")

    problems = False
    if load_errors:
        problems = True
        print(
            f"[merge] 警告: 読込/形式エラーが {len(load_errors)} 件あります:",
            file=sys.stderr,
        )
        for e in load_errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "[merge] 該当サブエージェントを再実行して結果ファイルを出力し直してください。",
            file=sys.stderr,
        )

    if dup_keys:
        problems = True
        uniq = sorted(set(dup_keys), key=lambda t: (str(t[0]), t[1]))
        print(
            f"[merge] 警告: 重複する (index, checkno) が {len(uniq)} 件あります(全て出力に含めています): {uniq}",
            file=sys.stderr,
        )

    if args.diff:
        diff_path = Path(args.diff)
        if diff_path.is_file():
            expected = _expected_indices_from_diff(diff_path)
            missing = sorted(expected - found_indices)
            if missing:
                problems = True
                print(
                    f"[merge] 警告: 結果ファイルが見つからないチェック対象 index が {len(missing)} 件あります: {missing}",
                    file=sys.stderr,
                )
                print(
                    "[merge] 該当indexのサブエージェントを再実行し、結果ファイルを出力後に再度 merge してください。",
                    file=sys.stderr,
                )
        else:
            print(
                f"[merge] 警告: --diff が見つかりません(欠落検知をスキップ): {diff_path}",
                file=sys.stderr,
            )

    if problems and args.strict:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
