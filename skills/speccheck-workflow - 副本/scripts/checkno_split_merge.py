#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checkno_split_merge.py

Step2(チェック項目ラベリング) の「1差分=1サブエージェント」化を支援する分割/マージスクリプト。

親エージェントが差分本文(before_markdown/after_markdown)を読み込むことなく、
Step1出力JSONの各差分レコードをサブエージェントへ配布し、サブエージェントが付与した
`checkno` を機械的に元JSONへ書き戻すために用いる。

2つのモードを持つ:

  split : Step1出力JSON(差分レコード列)を、`excluded:false` のレコードごとに
          1ファイル(rec_XXXXX.json)へ分割して outdir へ出力する。
          あわせて manifest.json(本文を含まない軽量メタ)を出力する。
          親は manifest.json のみを読めばよく、差分本文は読み込まない。

  merge : サブエージェントが outdir(=resultsdir) へ書き出した結果ファイル
          (rec_XXXXX.checkno.json = {"index": i, "checkno": [...]}) を集約し、
          元のStep1出力JSONの各レコードへ `checkno`(配列) を付与して書き戻す。
          - `excluded:true` のレコードは常に checkno=[]。
          - 結果ファイルが見つからない `excluded:false` レコードは checkno=[] とし、
            未処理indexとして警告を出力する(親が未完了サブエージェントを検知できる)。

使い方（プロジェクトの .claude を起点に実行。cd は不要。パスはすべて .claude からの相対）:
    # 分割(サブエージェント配布用のレコードファイル群を生成)
    python skills/speccheck-workflow/scripts/checkno_split_merge.py split \
        --in "specification_check/output/<name>_diff.json" \
        --outdir "specification_check/output/<name>_records"

    # マージ(サブエージェント結果を元JSONへ書き戻し)
    python skills/speccheck-workflow/scripts/checkno_split_merge.py merge \
        --in "specification_check/output/<name>_diff.json" \
        --resultsdir "specification_check/output/<name>_records" \
        --out "specification_check/output/<name>_diff.json"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REC_PREFIX = "rec_"
REC_SUFFIX = ".json"
RESULT_SUFFIX = ".checkno.json"
MANIFEST_NAME = "manifest.json"

# manifest に載せる軽量メタ項目(差分本文=before/after_markdown は載せない)
META_KEYS = [
    "file_old",
    "sheet_old",
    "chapter_old",
    "file_new",
    "sheet_new",
    "chapter_new",
    "item",
    "source",
]


def _rec_name(index: int) -> str:
    return f"{REC_PREFIX}{index:05d}{REC_SUFFIX}"


def _result_name(index: int) -> str:
    return f"{REC_PREFIX}{index:05d}{RESULT_SUFFIX}"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def cmd_split(args: argparse.Namespace) -> int:
    in_path = Path(args.infile)
    outdir = Path(args.outdir)
    records = _load_json(in_path)
    if not isinstance(records, list):
        print(
            f"[split] エラー: 入力JSONはレコード配列である必要があります: {in_path}",
            file=sys.stderr,
        )
        return 1

    outdir.mkdir(parents=True, exist_ok=True)

    manifest_records = []
    excluded_indices = []
    written = 0
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            print(
                f"[split] 警告: index={i} はオブジェクトでないためスキップします。",
                file=sys.stderr,
            )
            continue
        if rec.get("excluded") is True:
            excluded_indices.append(i)
            continue
        # 1差分=1ファイル。index を付与して原文をそのまま書き出す(要約・改変しない)。
        rec_out = dict(rec)
        rec_out["index"] = i
        _dump_json(rec_out, outdir / _rec_name(i))
        written += 1
        manifest_records.append(
            {
                "index": i,
                "rec_file": _rec_name(i),
                "result_file": _result_name(i),
                **{k: rec.get(k) for k in META_KEYS if k in rec},
            }
        )

    manifest = {
        "source_json": str(in_path),
        "total": len(records),
        "to_label": written,
        "excluded_count": len(excluded_indices),
        "excluded_indices": excluded_indices,
        "records": manifest_records,
    }
    _dump_json(manifest, outdir / MANIFEST_NAME)

    print(
        f"[split] 総レコード数={len(records)}  ラベリング対象(excluded:false)={written}  "
        f"除外(excluded:true)={len(excluded_indices)}"
    )
    print(f"[split] レコードファイルと {MANIFEST_NAME} を出力しました: {outdir}")
    print(
        f"[split] 親は {outdir / MANIFEST_NAME} のみを読み、各 rec_file をサブエージェントへ渡してください。"
    )
    return 0


def _extract_checkno(result_obj) -> list[str]:
    """結果ファイルから checkno(文字列配列) を取り出して正規化する。"""
    checkno = result_obj.get("checkno") if isinstance(result_obj, dict) else None
    if checkno is None:
        return []
    if isinstance(checkno, str):
        checkno = [checkno]
    if not isinstance(checkno, list):
        return []
    out = []
    for c in checkno:
        if c is None:
            continue
        s = str(c).strip()
        if s:
            out.append(s)
    return out


def _extract_excluded(result_obj):
    """結果ファイルから excluded(bool) を取り出す。存在しない/型不正なら None を返す。

    ラベリングサブエージェントが判定した除外フラグ(変更履歴/新フォーマット無効情報)を
    元JSONへ書き戻すために用いる(全フォーマットで除外判定をサブエージェントへ委譲)。
    """
    if not isinstance(result_obj, dict):
        return None
    exc = result_obj.get("excluded")
    return exc if isinstance(exc, bool) else None


def cmd_merge(args: argparse.Namespace) -> int:
    in_path = Path(args.infile)
    resultsdir = Path(args.resultsdir)
    out_path = Path(args.out)
    records = _load_json(in_path)
    if not isinstance(records, list):
        print(
            f"[merge] エラー: 入力JSONはレコード配列である必要があります: {in_path}",
            file=sys.stderr,
        )
        return 1

    labeled = 0
    excluded = 0
    missing_indices = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        if rec.get("excluded") is True:
            rec["checkno"] = []
            excluded += 1
            continue
        result_path = resultsdir / _result_name(i)
        if not result_path.exists():
            rec["checkno"] = []
            missing_indices.append(i)
            continue
        try:
            result_obj = _load_json(result_path)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[merge] 警告: 結果ファイル読込失敗 index={i}: {e}", file=sys.stderr)
            rec["checkno"] = []
            missing_indices.append(i)
            continue
        # 除外判定はサブエージェントへ委譲(全フォーマット)。結果に excluded があれば書き戻す。
        exc = _extract_excluded(result_obj)
        if exc is not None:
            rec["excluded"] = exc
        if rec.get("excluded") is True:
            rec["checkno"] = []
            excluded += 1
        else:
            rec["checkno"] = _extract_checkno(result_obj)
            labeled += 1

    _dump_json(records, out_path)

    print(f"[merge] 書き戻し完了: {out_path}")
    print(
        f"[merge] checkno付与(サブエージェント結果)={labeled}  excluded(checkno=[])={excluded}"
    )
    if missing_indices:
        print(
            f"[merge] 警告: 結果ファイルが見つからない excluded:false レコードが {len(missing_indices)} 件あります "
            f"(checkno=[] を暫定付与)。未処理index: {missing_indices}",
            file=sys.stderr,
        )
        print(
            "[merge] 該当indexのサブエージェントを再実行し、結果ファイルを出力後に再度 merge してください。",
            file=sys.stderr,
        )
        if args.strict:
            return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Step2 ラベリング用 分割/マージスクリプト")
    sub = p.add_subparsers(dest="mode", required=True)

    ps = sub.add_parser(
        "split", help="Step1出力JSONをレコード単位に分割し manifest を出力"
    )
    ps.add_argument("--in", dest="infile", required=True, help="入力(Step1出力JSON)")
    ps.add_argument(
        "--outdir",
        required=True,
        help="レコードファイル/ manifest.json の出力先ディレクトリ",
    )
    ps.set_defaults(func=cmd_split)

    pm = sub.add_parser(
        "merge", help="サブエージェント結果を集約して元JSONへ checkno を書き戻す"
    )
    pm.add_argument(
        "--in",
        dest="infile",
        required=True,
        help="入力(Step1出力JSON。checkno を書き戻す対象)",
    )
    pm.add_argument(
        "--resultsdir",
        required=True,
        help="サブエージェント結果(rec_XXXXX.checkno.json)の格納ディレクトリ",
    )
    pm.add_argument(
        "--out", required=True, help="出力JSONパス(--in と同一パス指定で上書き可)"
    )
    pm.add_argument(
        "--strict", action="store_true", help="未処理レコードがある場合に非0で終了する"
    )
    pm.set_defaults(func=cmd_merge)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
