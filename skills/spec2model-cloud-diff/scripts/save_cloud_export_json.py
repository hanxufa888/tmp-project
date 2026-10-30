#!/usr/bin/env python3
"""Atomically save a graph_export_document_json response as a Document JSON file."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def _document_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("MCP export response must be a JSON object")

    # The export contract allows either an inline ``document_json`` object or a
    # serialized ``json_text`` string. Accept both so a valid MCP response is
    # never rejected before the comparison step.
    document_json = payload.get("document_json")
    if document_json is None:
        json_text = payload.get("json_text")
        if isinstance(json_text, str) and json_text.strip():
            try:
                document_json = json.loads(json_text)
            except json.JSONDecodeError as error:
                raise ValueError(f"json_text is not valid JSON: {error}") from error
    if document_json is None:
        document_json = payload

    if not isinstance(document_json, dict) or not isinstance(
        document_json.get("document"), dict
    ):
        raise ValueError(
            "MCP export response does not contain document_json.document "
            "or a json_text string that decodes to it"
        )
    return document_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Save a fresh graph_export_document_json response atomically."
    )
    parser.add_argument("mcp_response", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-file-name")
    args = parser.parse_args()

    payload = json.loads(args.mcp_response.read_text(encoding="utf-8-sig"))
    document_json = _document_payload(payload)
    exported_name = str(payload.get("file_name") or "").strip()
    if args.expected_file_name and exported_name != args.expected_file_name:
        raise ValueError(
            f"Exported file_name {exported_name!r} does not match "
            f"{args.expected_file_name!r}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=args.output.parent,
        prefix=f".{args.output.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(document_json, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary_path = Path(handle.name)
    os.replace(temporary_path, args.output)
    print(f"saved fresh cloud JSON: {args.output}")
    print(f"file_name: {exported_name or '(not supplied)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
