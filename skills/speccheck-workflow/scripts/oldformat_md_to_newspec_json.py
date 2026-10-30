#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oldformat_md_to_newspec_json.py

旧フォーマット仕様書(Word由来 .doc/.docx の変換md)の「新設仕様書 / ファイル追加」用スクリプト
（Step1 チェック対象データ作成 のみ）。

新フォーマット(.xlsm)向けの newformat_md_to_newspec_json.py は
「# 見出し=シート, ## 見出し=章節」という構造を前提としており、
旧フォーマット(md先頭が `# 目次`、`## 章節`、`### 段落` のみでシート見出しを持たない)では
テーブルが捕捉されない。本スクリプトは旧フォーマット専用に、

  1) `## 章節` 単位でレコード化（`### 段落`は章節本文に含める。1レコード=1章節）
  2) 変更前が無いため before_markdown="", after_markdown=当該章節の原文（要約・改変なし）

を行う。checkno は付与しない（機械判定は行わない）。Step2 の checkno 付与は
サブエージェント（checkno_split_merge.py の split→サブエージェント→merge）で行う。
出力スキーマは newformat_md_to_newspec_json.py と同一（file_old.., item, source, excluded）。

章節名の同義（meter-spec-common/reference/guide-oldformat.md）:
  "*.入力" = "*.入力・定数",  "*.通常制御" = "*.制御仕様"

使い方（プロジェクトの .claude を起点に実行。cd は不要。パスは .claude からの相対）:
    python skills/speccheck-workflow/scripts/oldformat_md_to_newspec_json.py \
        --spec-dir "specification_check/check_spec/<仕様書名>" \
        --out "specification_check/output/<仕様書名>_newspec.json"

依存: 標準ライブラリのみ。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 変更履歴章節（無効）。concepts-spec-common-rules.md「変更履歴情報の扱いルール」準拠
HISTORY_KEYS = ("変更履歴", "変更概要", "更新履歴", "Revision history")

# 添付資料の識別（ファイル名トークン）。newformat_md_to_newspec_json.py の ATTACH と一致させる。
ATTACH = re.compile(r"_Appendix|_Attachment|添付", re.IGNORECASE)


def is_history(title: str) -> bool:
    return any(k in title for k in HISTORY_KEYS)


def parse_md(md_path: Path):
    """## 章節単位で (title, body_text) のリストを返す。### 段落は本文に含める。

    `## 章節` を1つも持たないmd（添付資料 等: `# シート見出し` + 表のみで章節見出しを持たない）は、
    `#` 見出し（「目次」を除く）を章節見出しとみなして1レコード化する（fallback）。
    """
    lines = md_path.read_text(encoding="utf-8").splitlines()
    has_h2 = any(re.match(r"^##\s+", ln) for ln in lines)
    chapters = []
    cur_title, cur_body = None, []
    for ln in lines:
        m2 = re.match(r"^##\s+(.*)$", ln)
        m1 = re.match(r"^#\s+(.*)$", ln)
        if m2:
            if cur_title is not None:
                chapters.append((cur_title, cur_body))
            cur_title = m2.group(1).strip()
            cur_body = []
        elif m1:
            title1 = m1.group(1).strip()
            # ## がある場合の `#` は目次見出し扱いで無視（従来通り）。
            # ## が無いmdでは `#`（目次以外）を章節見出しとみなす。
            if has_h2 or title1 == "目次":
                continue
            if cur_title is not None:
                chapters.append((cur_title, cur_body))
            cur_title = title1
            cur_body = []
        else:
            if cur_title is not None:
                cur_body.append(ln)
    if cur_title is not None:
        chapters.append((cur_title, cur_body))
    return chapters


def main() -> int:
    p = argparse.ArgumentParser(
        description="旧フォーマット新設/追加仕様書(md)を章節単位レコードへ変換する（Step1のみ。checknoは付与しない）。"
    )
    p.add_argument(
        "--spec-dir",
        required=True,
        help="check_spec/<仕様書名>/ ディレクトリ（配下の全mdを取込。DMSファイルは除外）",
    )
    p.add_argument("--out", required=True, help="出力JSONパス")
    p.add_argument(
        "--attachment-only",
        action="store_true",
        help="添付資料(_Appendix/_Attachment/添付)のみを変換対象とする"
        "（本体が新フォーマットの仕様書で、添付資料のみを旧フォーマット扱いする場合に指定）",
    )
    p.add_argument(
        "--append",
        action="store_true",
        help="--out が既存の配列JSONの場合、上書きせず末尾へレコードを追記する"
        "（本体の新フォーマットJSONへ添付資料レコードを結合する場合に指定）",
    )
    args = p.parse_args()

    spec_dir = Path(args.spec_dir).expanduser()
    if not spec_dir.is_dir():
        sys.stderr.write(f"[error] spec-dir が見つかりません: {spec_dir}\n")
        return 2

    all_md = sorted(spec_dir.glob("*.md"))
    if not all_md:
        sys.stderr.write(f"[error] mdファイルが見つかりません: {spec_dir}\n")
        return 2

    # DMSファイル(通信仕様書)は変換対象から除外
    non_dms = [m for m in all_md if not re.search(r"DMS", m.name, re.IGNORECASE)]
    skipped = [m.name for m in all_md if re.search(r"DMS", m.name, re.IGNORECASE)]
    if skipped:
        sys.stderr.write(
            "[skip] DMSファイルを変換対象から除外: " + ", ".join(skipped) + "\n"
        )
    # --attachment-only: 添付資料のみを変換対象とする（本体は newformat 側で新フォーマット変換する）
    if args.attachment_only:
        md_files = [m for m in non_dms if ATTACH.search(m.name)]
        skipped_body = [m.name for m in non_dms if not ATTACH.search(m.name)]
        if skipped_body:
            sys.stderr.write(
                "[skip] --attachment-only: 添付資料以外を変換対象から除外: "
                + ", ".join(skipped_body)
                + "\n"
            )
    else:
        md_files = non_dms
    if not md_files:
        which = "添付資料" if args.attachment_only else "変換対象md"
        sys.stderr.write(f"[error] {which} がありません（DMS除外後）: {spec_dir}\n")
        return 2

    records = []
    for md in md_files:
        file_new = md.name
        for title, body in parse_md(md):
            body_text = "\n".join(body)
            after = ("## " + title + "\n" + body_text).strip()
            # 変更履歴章節は無効。それ以外（空章節を含む）は excluded=false。
            excluded = is_history(title)
            records.append(
                {
                    "file_old": "",
                    "sheet_old": "",
                    "chapter_old": "",
                    "file_new": file_new,
                    "sheet_new": "",
                    "chapter_new": title,
                    "before_markdown": "",
                    "after_markdown": after,
                    "item": "(章節全体)",
                    "source": "new_spec",
                    "excluded": excluded,
                }
            )

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if args.append and out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            sys.stderr.write(
                f"[error] --append 先が配列JSONではありません: {out_path}\n"
            )
            return 2
        combined = existing + records
        sys.stderr.write(
            f"[append] 既存レコード {len(existing)} 件へ {len(records)} 件を追記します。\n"
        )
    else:
        combined = records
    out_path.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    total = len(records)
    excluded = sum(1 for r in records if r["excluded"])
    sys.stderr.write(
        f"[done] {out_path} 生成 (本スクリプト生成レコード={total}, excluded={excluded}, "
        f"取込md={len(md_files)}, 出力総レコード={len(combined)})\n"
    )
    for r in records:
        sys.stderr.write(f"  {r['chapter_new']!r:36} excluded={r['excluded']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
