#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mark_invalid_items.py

新設・ファイル追加（new_spec, 新フォーマット）レコードに、項目(列)単位の無効列を
`invalid_items`（配列）として付与する列除外アノテータ。

Step2ラベリングはサブエージェントが行うが、章節テーブル全体を走査する新設フローでは
無効列（要求ID/Ver/No 等の識別子列や、guide-newformat-invalid.md 由来の各種"数"・R/R・
"特別処理が必要な理由" 等）を場所条件照合の対象から除外する必要がある。
本スクリプトは、その無効列の判定を機械的に行い、各レコードの表に実在する無効列名を
`invalid_items` として付与する（原文 after_markdown は改変しない）。
サブエージェントは rec ファイル内の `invalid_items` を照合対象から除外する。

無効列の定義は newformat_md_to_newspec_json.py（guide-newformat-invalid.md をコード化した
IDENTIFIER_HEADERS / INVALID_ITEMS_ALL / INVALID_ITEMS_BY_SHEET）を再利用する。
チェック項目の追加・変更では本スクリプトを更新する必要はない（無効列自体が増えた場合のみ）。

対象は新フォーマットの章節テーブルを持つレコード。旧フォーマット（sheet_new="" 等で
無効列の概念がテーブル列として存在しない）レコードでは invalid_items は概ね空になる。
excluded:true のレコードはラベリング対象外のため invalid_items=[] とする。

使い方（プロジェクトの .claude を起点に実行。cd は不要。パスは .claude からの相対）:
    python skills/speccheck-workflow/scripts/mark_invalid_items.py --io "specification_check/output/<仕様書名>_newspec.json"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 無効列の定義・パース補助を newformat モジュールから再利用
import newformat_md_to_newspec_json as conv


def parse_headers(after: str) -> list[str]:
    """after_markdown 内の全テーブルのヘッダ行セル（列名）を収集する。

    各表ブロックについて、区切り行（|---|）の直前行をヘッダとみなす。
    区切り行が無い場合は先頭行をヘッダとみなす。
    """
    headers: list[str] = []
    # 空行区切りで表ブロックへ分割
    blocks, cur = [], []
    for ln in after.splitlines():
        if ln.strip().startswith("|"):
            cur.append(conv.split_row(ln))
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)

    for rows in blocks:
        sep_idx = next((k for k, r in enumerate(rows) if conv.is_separator(r)), -1)
        if sep_idx >= 1:
            header = rows[sep_idx - 1]
        else:
            header = rows[0]
        headers.extend(h for h in header if h)
    return headers


def invalid_items_for(rec: dict) -> list[str]:
    """レコードの表に実在する無効列名（識別子列＋無効情報一覧由来の無効項目）を返す。"""
    sheet = rec.get("sheet_new", "") or ""
    chap = conv.chap_number(rec.get("chapter_new", "") or "")
    after = rec.get("after_markdown", "") or ""

    seen, out = set(), []
    for h in parse_headers(after):
        if h in seen:
            continue
        if h in conv.IDENTIFIER_HEADERS or conv.item_is_invalid(sheet, chap, h):
            seen.add(h)
            out.append(h)
    return out


def main() -> int:
    p = argparse.ArgumentParser(
        description="new_spec レコードへ invalid_items(無効列) を付与する列除外アノテータ。"
    )
    p.add_argument(
        "--io", required=True, help="入出力JSON（Step1出力の newspec.json。上書き更新）"
    )
    args = p.parse_args()

    path = Path(args.io).expanduser()
    recs = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(recs, list):
        sys.stderr.write(
            f"[error] 入力JSONはレコード配列である必要があります: {path}\n"
        )
        return 1

    annotated = 0
    for r in recs:
        if not isinstance(r, dict):
            continue
        if r.get("excluded") is True:
            r["invalid_items"] = []
            continue
        r["invalid_items"] = invalid_items_for(r)
        if r["invalid_items"]:
            annotated += 1

    path.write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stderr.write(f"[done] invalid_items 付与: {path}\n")
    sys.stderr.write(f"  レコード総数={len(recs)}  invalid_items非空={annotated}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
