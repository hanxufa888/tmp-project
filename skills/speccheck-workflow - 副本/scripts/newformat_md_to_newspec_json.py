#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""newformat_md_to_newspec_json.py

Step1(チェック対象データの作成) の「新設仕様書 / ファイル追加」用スクリプト（新フォーマット .xlsm 由来md 用）。

差分データ(差分CSV)が存在しないケース、すなわち
  (1) 変更前仕様書が無い新設仕様書
  (2) 変更後仕様書に新規追加され差分データに現れないファイル
について、`.claude/specification_check/check_spec/<仕様書名>/` 配下の
変換済みマークダウン(仕様書本体/添付資料)を入力とし、
通常の差分JSON(csv_to_diff_json.py の出力)と同一スキーマのレコード列へ変換する。

新設/追加ファイルでは全内容が「追加」であるため、各レコードは
  before_markdown = ""（変更前なし）, after_markdown = 当該箇所の原文
として生成する。

分解粒度は「シート×章節」。1レコード = （シート × 章節(段落)）であり、
after_markdown には当該章節の表（複数表がある場合は連結）を原文のまま保持する。
章節見出しを持たないシート（添付資料 English translations 等）は、シート全体を1レコードとする。

出力JSONの各レコードのキー（通常差分JSONと互換 + 拡張）:
    file_old, sheet_old, chapter_old,
    file_new, sheet_new, chapter_new,
    before_markdown, after_markdown,
    item,            # 互換用。章節単位のため "(章節全体)" 固定
    source,          # "new_spec"（本スクリプト生成の識別用）
    excluded         # 無効情報(無効シート/無効章節/「要求無し」宣言セクション)該当= true

使い方（プロジェクトの .claude を起点に実行。cd は不要。パスは .claude からの相対）:
    python skills/speccheck-workflow/scripts/newformat_md_to_newspec_json.py \
        --spec-dir "specification_check/check_spec/<仕様書名>" \
        --out "specification_check/output/<仕様書名>_newspec.json"

依存: 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

# ---------------------------------------------------------------------------
# 無効情報の定義（meter-spec-common/reference/guide-newformat-invalid.md 準拠）
# 章節/シート単位の無効に加え、項目(列)単位の無効は Step2(mark_invalid_items.py)が
# invalid_items 付与時に参照し、サブエージェントが場所条件照合から当該列を除外する。
# ---------------------------------------------------------------------------

# シート単位で全体が無効（補足情報シート・変更履歴シート）
INVALID_SHEETS = {"MSG", "Variable_MSG", "SW_MSG", "Revision history"}

# 全シート共通で無効な項目(列)名
INVALID_ITEMS_ALL = {"Ver"}

# 章節番号(prefix)単位で章ごと無効
INVALID_CHAPTER_PREFIXES = {
    "1",  # TT: 1. システム内容説明
    "7",  # Revision history: 7. 変更履歴
}

# (シート, 章節番号の正規表現) -> 無効な項目名集合
INVALID_ITEMS_BY_SHEET = {
    "TT": [
        (r"^2-.+-1$", {"O/M上の警告灯・表示灯名", "仕向け先違いのシンボルの引当条件"}),
        (
            r"^2-.+-2$",
            {
                "TT表示状態数",
                "TT表示時のシステムの状態",
                "システム状態のR/R",
                "TT表示のR/R",
                "情報種類",
                "システム / 状態のR/R",
                "TT表示 / のR/R",
                "TT表示時の / システムの状態",
                "情報 / 種類",
            },
        ),
        (r"^2-.+-3$", {"データラベル数"}),
        (r"^2-.+-4$", {"信号数"}),
    ],
    "BZR": [
        (
            r"^3-1$",
            {
                "BZR吹鳴状態数",
                "BZR吹鳴時のシステムの状態",
                "ユーザ操作フィードバック情報、制御介入情報",
                "回避余裕",
                "重大性",
                "遭遇度合",
                "システム状態のR/R",
                "BZR吹鳴のR/R",
                "BZR吹鳴時の / システムの状態",
                "(優先吹鳴決定用) / 回避余裕",
                "システム / 状態のR/R",
                "BZR吹鳴 / のR/R",
            },
        ),
        (r"^3-2$", {"データラベル数"}),
        (r"^3-3$", {"信号数"}),
    ],
    "MID": [
        (
            r"^4-1$",
            {
                "固定MID表示数",
                "固定MID表示時のシステムの状態",
                "工場・サービス専用",
                "ユーザ操作フィードバック情報、制御介入情報",
                "回避余裕",
                "重大性",
                "遭遇度合",
                "最低0.9s表示可否（拡張用）",
                "システム状態のR/R",
                "固定MIDのR/R",
                "固定MID表示時の / システムの状態",
                "工場・ / サービス専用",
                "(優先表示決定用) / 回避余裕",
                "最低0.9s 表示可否 (拡張用)",
                "システム / 状態のR/R",
                "固定MID / 表示のR/R",
            },
        ),
        (r"^4-2$", {"データラベル数"}),
        (r"^4-3$", {"信号数"}),
        (r"^4-4$", {"値がリセットしても問題ない理由"}),
    ],
    "Variable_MID": [
        (
            r"^5-1$",
            {
                "基本画面数",
                "基本画面表示時のシステムの状態",
                "工場・サービス専用",
                "ユーザー操作フィードバック情報、制御介入情報",
                "回避余裕",
                "重大性",
                "遭遇度合",
                "最低0.9s表示可否（拡張用）",
                "システム状態のR/R",
                "可変MIDのR/R",
                "基本画面表示時の / システムの状態",
                "工場・ / サービス専用",
                "(優先表示決定用) / 回避余裕",
                "最低0.9s 表示可否 (拡張用)",
                "システム / 状態のR/R",
                "可変MID / 表示のR/R",
            },
        ),
        (r"^5-2$", {"データラベル数"}),
        (r"^5-3-.+$", {"表示グループ数"}),
        (
            r"^G.+-1$",
            {
                "表示状態/効果数",
                "可変MID表示時のシステムの状態",
                "可変MID表示時の / システムの状態",
            },
        ),
        (r"^G.+-2$", {"データラベル数"}),
        (r"^5-4$", {"値がリセットしても問題ない理由"}),
    ],
    "SW": [
        (r"^6$", {"SW要求数"}),
        (r"^S.+-2$", {"SW操作状態数", "表示時のシステムの状態"}),
        (r"^S.+-3$", {"SW状態表示数", "システムの状態"}),
        (r"^S.+-4$", {"データラベル数"}),
    ],
    "Detailed Spec": [(r".*", {"特別処理が必要な理由"})],
    "Detailed Spec2": [(r".*", {"特別処理が必要な理由"})],
    "Detailed Spec3": [(r".*", {"特別処理が必要な理由"})],
}

# 行識別子列（値テキスト・項目判定の対象外）
IDENTIFIER_HEADERS = {
    "要求ID",
    "Ver",
    "No",
    "No.",
    "基本 画面 / No",
    "基本画面 / No",
    "基本画面No",
}

# 添付資料ファイル（旧フォーマット扱い）。ファイル名トークンで識別する。
# 添付資料(.docx由来)は本体(.xlsm由来 新フォーマット)とは別フォーマットとして扱うため、
# 本スクリプト（新フォーマット変換）では変換対象から除外し、
# oldformat_md_to_newspec_json.py（--attachment-only）で旧フォーマットとして変換する。
ATTACH = re.compile(r"_Appendix|_Attachment|添付", re.IGNORECASE)

# 「要求無し」宣言の検出（meter-spec-common/reference/guide-newformat-item.md の
#   項目「要求無し***/ ■要求有り***」の行 準拠）。
#   ルールは2段構え:
#     - 汎用(BZR/MID/Variable_MID/SW): 要求無し → 該当「シート」の確認不要 → シート全体を excluded。
#     - TT固有: 要求無し → 章節「2-*-1」～「2-*-4」(当該警告灯ブロックのみ)の確認不要
#              → 宣言見出し番号(例 2-A / 2-B / 2-N)を接頭辞に、そのブロック配下のみ excluded。
#                (2-1-*/2-2-* 等の要求有りブロックはシート単位で巻き込まない=項目単位で反映)
# NOREQUIREMENT_DECL は宣言「行」の検出のみを担う（表|始まり以外の本文行で、先頭にセルID等の
# 1トークンを許容し「要求無し」で始まる行）。どのレコードへ適用するかは parse_md での帰属記録
# （norec: sheets / prefixes）と is_norequirement() の判定で行う。
# 「機能有無判別無し」等の別セマンティクス(Sn-1固有)は先頭が「要求無し」でないため一致しない。
NOREQUIREMENT_DECL = re.compile(r"^(?:[0-9A-Za-z_]+\s+)?要求無し")


# ---------------------------------------------------------------------------
# パース補助
# ---------------------------------------------------------------------------


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("　", " ")).strip()


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_separator(cells: list[str]) -> bool:
    return any(c.strip() for c in cells) and all(
        re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells if c.strip() != ""
    )


def heading_number(title: str) -> str:
    m = re.match(r"^([0-9A-Za-z]+(?:-[0-9A-Za-z]+)*)[.\s]", title.strip())
    return m.group(1) if m else clean(title)


def item_is_invalid(sheet: str, chapter_no: str, item: str) -> bool:
    """項目(列)単位の無効判定（Step2 のチェック項目選定時に列除外用）。"""
    if item in INVALID_ITEMS_ALL:
        return True
    for rule_sheet, rules in INVALID_ITEMS_BY_SHEET.items():
        if rule_sheet != sheet:
            continue
        for pat, items in rules:
            if re.search(pat, chapter_no) and item in items:
                return True
    return False


def chapter_is_invalid(chapter_no: str) -> bool:
    head = chapter_no.split("-")[0]
    return head in INVALID_CHAPTER_PREFIXES


def _tt_block_norequirement(tt_block: str, norec: dict) -> bool:
    """TT警告灯ブロック（例 2-A / 2-1）が要求無しか。"""
    if "TT" in norec["sheets"]:
        return True
    for s, pfx in norec["prefixes"]:
        if s == "TT" and (tt_block == pfx or tt_block.startswith(pfx + "-")):
            return True
    return False


def is_norequirement(sheet: str, chapter_no: str, norec: dict) -> bool:
    """「要求無し」宣言に基づく除外判定。

    (1) 宣言箇所そのもの（guide-newformat-item.md「要求無し***/ ■要求有り***」行 準拠）:
        - 非TTシート: シート全体が要求無し（norec["sheets"] に登録）なら True。
        - TTシート: 要求無しの警告灯ブロック接頭辞（例 2-A）に一致する章節のみ True
                    （2-A-1〜2-A-4 等。2-1-*/2-2-* 等の要求有りブロックは対象外）。
    (2) 特別処理指示シートへの波及（guide-newformat-sheetsection.md の 機能ブロック↔特別処理指示 の対応準拠）:
        機能ブロックが要求無しなら、対応する特別処理指示の章節も確認不要として除外する。
        - Detailed Spec  「8-<X>」 ← TT 警告灯ブロック「2-<X>」（8-N↔2-N, 8-A↔2-A, 8-B↔2-B）
        - Detailed Spec  「9(-*)」  ← BZR シート
        - Detailed Spec  「10(-*)」 ← MID シート
        - Detailed Spec2 「11-*」    ← Variable_MID シート（基本画面）
        - Detailed Spec3 「12-*」    ← SW シート
    """
    # (1) 宣言箇所そのもの
    if sheet in norec["sheets"]:
        return True
    for s, pfx in norec["prefixes"]:
        if s == sheet and (chapter_no == pfx or chapter_no.startswith(pfx + "-")):
            return True

    # (2) 特別処理指示シートへの波及
    top = chapter_no.split("-")[0]
    if sheet == "Detailed Spec":
        if chapter_no.startswith("8-"):
            # 8-<X> → TT 2-<X>
            if _tt_block_norequirement("2-" + chapter_no[len("8-") :], norec):
                return True
        elif top == "9" and "BZR" in norec["sheets"]:
            return True
        elif top == "10" and "MID" in norec["sheets"]:
            return True
    elif sheet == "Detailed Spec2":
        if top == "11" and "Variable_MID" in norec["sheets"]:
            return True
    elif sheet == "Detailed Spec3":
        if top == "12" and "SW" in norec["sheets"]:
            return True
    return False


def chap_number(chapter_new: str) -> str:
    m = re.match(r"^([0-9A-Za-z]+(?:-[0-9A-Za-z]+)*)", chapter_new)
    return m.group(1) if m else chapter_new


def has_special_processing(blocks: list[str]) -> bool:
    """Detailed Spec系章節に、作成者記載欄「特別処理」の非空値（"-"以外）があるか。

    guide-newformat-item.md では、仕様/標準処理は「フォーマット定義項目＝仕様書作成者が記載する
    箇所ではない」とされ、作成者が記載するのは「特別処理」列のみ。よって Detailed Spec系
    章節の content 判定は「特別処理」列のみで行う（"-"＝特別処理不要の明示 は content とみなさない）。
    「特別処理が必要な理由」列は判定対象外（列名一致は "特別処理" のみ）。
    """
    for block_md in blocks:
        rows = [
            split_row(ln) for ln in block_md.splitlines() if ln.strip().startswith("|")
        ]
        if not rows:
            continue
        sep_idx = next((k for k, r in enumerate(rows) if is_separator(r)), -1)
        if sep_idx >= 0:
            header = rows[sep_idx - 1] if sep_idx >= 1 else rows[0]
            data = rows[sep_idx + 1 :]
        else:
            header = rows[0]
            data = rows[1:]
        sp_idx = next(
            (ci for ci, h in enumerate(header) if h.strip() == "特別処理"), -1
        )
        if sp_idx < 0:
            continue
        for r in data:
            if sp_idx < len(r):
                v = r[sp_idx].strip()
                if v != "" and v != "-":
                    return True
    return False


def has_data_content(blocks: list[str]) -> bool:
    """章節の表に、識別子列(要求ID/Ver/No)以外で非空のデータセルがあるか。

    全データセルが空（要求IDのみ記載の「要求無し」プレースホルダ等）の章節は
    「空章節」とみなし False を返す。"-" は意味のある値として content 扱い。
    """
    for block_md in blocks:
        rows = [
            split_row(ln) for ln in block_md.splitlines() if ln.strip().startswith("|")
        ]
        if not rows:
            continue
        sep_idx = next((k for k, r in enumerate(rows) if is_separator(r)), -1)
        if sep_idx >= 0:
            header = rows[sep_idx - 1] if sep_idx >= 1 else rows[0]
            data = rows[sep_idx + 1 :]
        else:
            header = rows[0]
            data = rows[1:]
        for r in data:
            for ci, cell in enumerate(r):
                h = header[ci] if ci < len(header) else ""
                if h in IDENTIFIER_HEADERS:
                    continue
                if cell.strip() != "":
                    return True
    return False


# ---------------------------------------------------------------------------
# メイン変換（シート×章節 単位で集約）
# ---------------------------------------------------------------------------


def parse_md(md_path: Path, sections: "OrderedDict", norec: dict) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    file_new = md_path.name

    sheet = ""
    chapter_no = chapter_title = ""
    para_no = para_title = ""
    last_heading_no = (
        ""  # 直近に出現した見出し(## or ###/####)の番号。要求無し宣言の帰属先。
    )
    seen_chapter_in_sheet = False
    in_toc = False

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m1 = re.match(r"^#\s+(.*)$", line)
        m2 = re.match(r"^##\s+(.*)$", line)
        m34 = re.match(r"^#{3,4}\s+(.*)$", line)
        if m2:
            chapter_title = clean(m2.group(1))
            chapter_no = heading_number(m2.group(1))
            para_no = para_title = ""
            last_heading_no = chapter_no
            seen_chapter_in_sheet = True
            i += 1
            continue
        if m34:
            para_title = clean(m34.group(1))
            para_no = heading_number(m34.group(1))
            last_heading_no = para_no
            i += 1
            continue
        if m1:
            title = clean(m1.group(1))
            if title == "目次":
                in_toc = True
                sheet = ""
            else:
                in_toc = False
                sheet = title
                chapter_no = chapter_title = para_no = para_title = ""
                last_heading_no = ""
                seen_chapter_in_sheet = False
            i += 1
            continue

        if line.strip().startswith("|") and not in_toc and sheet:
            block = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(split_row(lines[i]))
                i += 1
            add_block(
                sections,
                file_new,
                sheet,
                para_no or chapter_no,
                para_title or chapter_title,
                seen_chapter_in_sheet,
                block,
            )
            continue

        # 「要求無し」宣言行（表以外の本文行）を検出し、直前見出しへ帰属させて登録する。
        if sheet and not in_toc and NOREQUIREMENT_DECL.match(clean(line)):
            if sheet == "TT":
                # TT: 警告灯ブロック単位（宣言見出し番号を接頭辞に配下章節のみ除外）
                if last_heading_no:
                    norec["prefixes"].add((sheet, last_heading_no))
            else:
                # 非TT: シート全体を要求無しとして除外
                norec["sheets"].add(sheet)
        i += 1


def add_block(sections, file_new, sheet, chap, chap_title, seen_chapter, block):
    joined_all = " ".join(c for r in block for c in r)
    # シート見出し直後の「メータDB用エリア」バナー表はスキップ
    if "メータDB用エリア" in joined_all and len(block) <= 2:
        return

    block_md = "\n".join("| " + " | ".join(r) + " |" for r in block)

    if sheet in INVALID_SHEETS:
        key = (file_new, sheet, "", "")
        excluded = True
    elif not seen_chapter:
        # 章節見出しを持たないシート（添付資料 等）はシート全体を1レコードに
        key = (file_new, sheet, "", "")
        excluded = False
    else:
        key = (file_new, sheet, chap, chap_title)
        excluded = chapter_is_invalid(chap)

    if key not in sections:
        sections[key] = {"blocks": [], "excluded": excluded}
    sections[key]["blocks"].append(block_md)
    # excluded は OR（無効章節/シートに該当すれば true）
    sections[key]["excluded"] = sections[key]["excluded"] or excluded


def make_record(file_new, sheet, chap, chap_title, after_markdown, excluded):
    chapter_new = chap_title or chap
    return {
        "file_old": "",
        "sheet_old": "",
        "chapter_old": "",
        "file_new": file_new,
        "sheet_new": sheet,
        "chapter_new": chapter_new,
        "before_markdown": "",
        "after_markdown": after_markdown,
        "item": "(章節全体)",
        "source": "new_spec",
        "excluded": bool(excluded),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="新設/追加仕様書(check_spec配下のmd)をシート×章節単位のレコードJSONへ変換する。"
    )
    p.add_argument(
        "--spec-dir",
        required=True,
        help="check_spec/<仕様書名>/ ディレクトリ（配下のmdを全て取り込む。DMSファイルは除外）",
    )
    p.add_argument("--out", required=True, help="出力JSONパス")
    args = p.parse_args()

    spec_dir = Path(args.spec_dir).expanduser()
    if not spec_dir.is_dir():
        sys.stderr.write(f"[error] spec-dir が見つかりません: {spec_dir}\n")
        return 2

    all_md = sorted(spec_dir.glob("*.md"))
    if not all_md:
        sys.stderr.write(f"[error] mdファイルが見つかりません: {spec_dir}\n")
        return 2

    # 変換対象から除外するファイル:
    #  - DMSファイル(通信仕様書): 差分相当レコードへ変換しない
    #  - 添付資料(_Appendix/_Attachment/添付): 旧フォーマット扱いとし oldformat_md_to_newspec_json.py で変換する
    md_files, skipped_dms, skipped_attach = [], [], []
    for m in all_md:
        if re.search(r"DMS", m.name, re.IGNORECASE):
            skipped_dms.append(m.name)
        elif ATTACH.search(m.name):
            skipped_attach.append(m.name)
        else:
            md_files.append(m)
    if skipped_dms:
        sys.stderr.write(
            "[skip] DMSファイルを変換対象から除外: " + ", ".join(skipped_dms) + "\n"
        )
    if skipped_attach:
        sys.stderr.write(
            "[skip] 添付資料を新フォーマット変換対象から除外（旧フォーマット扱い。oldformat_md_to_newspec_json.py で変換）: "
            + ", ".join(skipped_attach)
            + "\n"
        )
    if not md_files:
        sys.stderr.write(
            f"[error] 変換対象mdがありません（DMS・添付資料除外後）: {spec_dir}\n"
        )
        return 2

    sections: "OrderedDict" = OrderedDict()
    norec = {
        "sheets": set(),
        "prefixes": set(),
    }  # 「要求無し」帰属: シート全体 / TT警告灯ブロック接頭辞
    for md in md_files:
        parse_md(md, sections, norec)

    records = []
    skipped_empty = 0
    norequirement_excluded = 0
    for (file_new, sheet, chap, chap_title), sec in sections.items():
        # 「要求無し」宣言セクション（guide-newformat-item.md「要求無し***/ ■要求有り***」行 準拠）は excluded:true とする。
        norequirement = is_norequirement(sheet, chap, norec)
        excluded = sec["excluded"] or norequirement
        # 空章節（内容なし）はレコード化しない（無効シート/要求無し等は対象外＝従来通り保持）。
        #  - Detailed Spec系（Detailed Spec/Spec2/Spec3）: content 判定は作成者記載欄「特別処理」で行う。
        #    仕様/標準処理はフォーマット定義（作成者記載箇所ではない）ため、特別処理が全空の章節は
        #    「作成者記載なし＝Step2ラベリング対象外」としてドロップする（excluded:true にはしない＝
        #    参照先/影響確認先としては有効内容のまま。無効=不在扱いにはしない）。
        #  - それ以外のシート: 従来どおり識別子列以外の非空セル有無で判定。
        if sheet.startswith("Detailed Spec"):
            has_content = has_special_processing(sec["blocks"])
        else:
            has_content = has_data_content(sec["blocks"])
        if not excluded and not has_content:
            skipped_empty += 1
            continue
        if norequirement and not sec["excluded"]:
            norequirement_excluded += 1
        after = "\n\n".join(sec["blocks"])
        records.append(make_record(file_new, sheet, chap, chap_title, after, excluded))
    if skipped_empty:
        sys.stderr.write(f"[skip] 空章節を除外: {skipped_empty} 章節\n")
    if norequirement_excluded:
        sys.stderr.write(
            f"[excluded] 「要求無し」宣言セクションを除外(excluded:true): {norequirement_excluded} 章節 "
            f"(sheets={sorted(norec['sheets'])}, TT-blocks={sorted(p for _, p in norec['prefixes'])})\n"
        )

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total = len(records)
    excluded = sum(1 for r in records if r["excluded"])
    sys.stderr.write(
        f"[done] {out_path} 生成 (章節レコード={total}, excluded={excluded}, "
        f"有効={total - excluded}, 取込md={len(md_files)})\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
