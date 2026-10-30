#!/usr/bin/env python3
"""Compare images in two local Office/PDF documents."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


def _workspace_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "spec2model" / "src").is_dir():
            return parent
    raise RuntimeError("Workspace root with tools/spec2model/src was not found")


WORKSPACE_DIR = _workspace_dir()
SPEC2MODEL_SRC = WORKSPACE_DIR / "tools" / "spec2model" / "src"
if str(SPEC2MODEL_SRC) not in sys.path:
    sys.path.insert(0, str(SPEC2MODEL_SRC))

from spec2model.parsers import parse_document


def _load_image_diff_module():
    path = (
        WORKSPACE_DIR
        / ".agents"
        / "skills"
        / "spec2model-cloud-diff"
        / "scripts"
        / "image_diff.py"
    )
    spec = importlib.util.spec_from_file_location("spec2model_image_diff", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load image comparison module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare images in two local documents."
    )
    parser.add_argument("old_file")
    parser.add_argument("new_file")
    parser.add_argument("--old-images-dir")
    parser.add_argument("--new-images-dir")
    parser.add_argument("--out-json", default="image_diff_result.json")
    args = parser.parse_args()

    old_path = Path(args.old_file).expanduser().resolve()
    new_path = Path(args.new_file).expanduser().resolve()
    if not old_path.is_file() or not new_path.is_file():
        parser.error("Both old_file and new_file must be existing files")

    config_path = (
        WORKSPACE_DIR / "tools" / "spec2model" / "config" / "parser_config.yaml"
    )
    old_doc = parse_document(
        str(old_path), images_dir=args.old_images_dir, config_path=str(config_path)
    )
    new_doc = parse_document(
        str(new_path), images_dir=args.new_images_dir, config_path=str(config_path)
    )
    report = _load_image_diff_module().compare_document_images(old_doc, new_doc)
    report["file_old"] = str(old_path)
    report["file_new"] = str(new_path)

    out_path = Path(args.out_json).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] Image JSON: {out_path}")
    print(
        "Image summary:",
        json.dumps(report["summary"], ensure_ascii=False, sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
