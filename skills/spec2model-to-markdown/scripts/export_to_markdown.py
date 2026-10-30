#!/usr/bin/env python3
"""Convert local Office documents to Markdown with workspace spec2model."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd
import yaml


def _find_workspace_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "spec2model" / "src").is_dir():
            return parent
    raise RuntimeError("Workspace root with tools/spec2model/src was not found")


WORKSPACE_DIR = _find_workspace_dir()
SPEC2MODEL_DIR = WORKSPACE_DIR / "tools" / "spec2model"
SPEC2MODEL_SRC_DIR = SPEC2MODEL_DIR / "src"
DEFAULT_CONFIG_PATH = SPEC2MODEL_DIR / "config" / "parser_config.yaml"
DEFAULT_OUTPUT_DIR = WORKSPACE_DIR / "data" / "output_data" / "markdown"
SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".pptx"}
PDF_UNSUPPORTED_MESSAGE = (
    "PDF input is not supported by this skill. Convert the PDF to Markdown with "
    "Azure AI Document Intelligence using the prebuilt-layout model and "
    "outputContentFormat=markdown. The API requires an Azure Document Intelligence "
    "resource, network access, and service credentials (this workspace uses "
    "AZURE_DI_ENDPOINT and AZURE_DI_API_KEY)."
)


def _unsupported_format_message(path: Path) -> str:
    extension = path.suffix.lower() or "<no extension>"
    supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    return (
        f"Input format '{extension}' is not supported by this skill and cannot be "
        f"converted to Markdown. Supported formats: {supported}."
    )


if str(SPEC2MODEL_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SPEC2MODEL_SRC_DIR))

import spec2model as s2m  # noqa: E402
from spec2model.models import Chapter, Document, Paragraph, TableBlock  # noqa: E402
from spec2model.utils.config import load_parser_config  # noqa: E402


_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")


def _parse_style_payload(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _visible_color_label(value: Any) -> Optional[str]:
    normalized = str(value).strip().lstrip("#").upper()
    if not _HEX_COLOR_RE.fullmatch(normalized):
        return None
    if len(normalized) == 8 and normalized.startswith("00"):
        return None
    return f"#{normalized[-6:]}"


def _extract_positions(raw_positions: Any) -> set[Tuple[int, int]]:
    positions: set[Tuple[int, int]] = set()
    if not isinstance(raw_positions, list):
        return positions

    for item in raw_positions:
        if isinstance(item, dict):
            row = item.get("row", item.get("row_index", item.get("body_row_index")))
            column = item.get("col", item.get("column", item.get("column_index")))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            row, column = item[:2]
        else:
            continue
        try:
            position = (int(row), int(column))
        except (TypeError, ValueError):
            continue
        if position[0] >= 0 and position[1] >= 0:
            positions.add(position)
    return positions


def _positions_by_key(
    raw_mapping: Any, *, color: bool = False
) -> Dict[str, set[Tuple[int, int]]]:
    if not isinstance(raw_mapping, dict):
        return {}

    result: Dict[str, set[Tuple[int, int]]] = {}
    for raw_key, raw_positions in raw_mapping.items():
        key = _visible_color_label(raw_key) if color else str(raw_key).strip()
        if not key:
            continue
        positions = _extract_positions(raw_positions)
        if positions:
            result.setdefault(key, set()).update(positions)
    return result


def _style_labels_by_position(raw_style: Any) -> Dict[Tuple[int, int], list[str]]:
    payload = _parse_style_payload(raw_style)
    if not payload:
        return {}

    labels: Dict[Tuple[int, int], list[str]] = {}
    mappings = (
        ("pattern", _positions_by_key(payload.get("patternTypes"))),
        ("fill", _positions_by_key(payload.get("fgColors"), color=True)),
    )
    for label_type, positions_by_key in mappings:
        for key, positions in positions_by_key.items():
            for position in positions:
                labels.setdefault(position, []).append(f"{label_type}:{key}")
    return {position: sorted(values) for position, values in labels.items()}


def _add_style_metadata_to_table(block: TableBlock) -> None:
    labels_by_position = _style_labels_by_position(block.style)
    if not labels_by_position:
        return

    styled_df = block.df.astype(object).copy()
    row_count, column_count = styled_df.shape
    for (row_index, column_index), labels in labels_by_position.items():
        if row_index >= row_count or column_index >= column_count:
            continue
        value = styled_df.iat[row_index, column_index]
        text = "" if value is None or pd.isna(value) else str(value)
        suffix = f"(style: {', '.join(labels)})"
        styled_df.iat[row_index, column_index] = f"{text} {suffix}" if text else suffix

    markdown = block.to_markdown_df(styled_df)
    block.markdown = f"{block.title}\n{markdown}" if block.title else markdown


def _apply_to_blocks(blocks: Iterable[Any]) -> None:
    for block in blocks:
        if isinstance(block, TableBlock):
            _add_style_metadata_to_table(block)


def _apply_to_paragraph(paragraph: Paragraph) -> None:
    _apply_to_blocks(paragraph.contents)
    for child in paragraph.paragraphs:
        _apply_to_paragraph(child)


def _apply_to_chapter(chapter: Chapter) -> None:
    _apply_to_blocks(chapter.contents)
    for paragraph in chapter.paragraphs:
        _apply_to_paragraph(paragraph)


def add_style_metadata_to_document(document: Document) -> None:
    _apply_to_blocks(document.contents)
    for chapter in document.chapters:
        _apply_to_chapter(chapter)
    for sheet in document.sheets:
        _apply_to_blocks(sheet.contents)
        for chapter in sheet.chapters:
            _apply_to_chapter(chapter)


def _is_supported_file(path: Path) -> bool:
    return (
        path.is_file()
        and not path.name.endswith(":Zone.Identifier")
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _collect_input_files(raw_inputs: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for raw_input in raw_inputs:
        path = Path(raw_input).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input not found: {path}")
        if path.is_file():
            if path.suffix.lower() == ".pdf":
                raise ValueError(PDF_UNSUPPORTED_MESSAGE)
            if not _is_supported_file(path):
                raise ValueError(_unsupported_format_message(path))
            files.append(path)
            continue
        candidates = sorted(path.rglob("*") if recursive else path.iterdir())
        if any(item.is_file() and item.suffix.lower() == ".pdf" for item in candidates):
            raise ValueError(PDF_UNSUPPORTED_MESSAGE)
        unsupported_files = [
            item
            for item in candidates
            if item.is_file()
            and not item.name.endswith(":Zone.Identifier")
            and item.suffix.lower() not in SUPPORTED_EXTENSIONS
        ]
        if unsupported_files:
            raise ValueError(_unsupported_format_message(unsupported_files[0]))
        files.extend(item for item in candidates if _is_supported_file(item))

    unique_files = sorted(set(files))
    if not unique_files:
        raise ValueError("No supported input documents were found")

    stems: Dict[str, Path] = {}
    for path in unique_files:
        key = path.stem.casefold()
        if key in stems:
            raise ValueError(
                "Output name collision for "
                f"{stems[key]} and {path}; convert them to separate output directories"
            )
        stems[key] = path
    return unique_files


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert local Office documents to Markdown with workspace spec2model.",
    )
    parser.add_argument(
        "inputs", nargs="+", help="Input document files or directories."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Markdown output directory.",
    )
    parser.add_argument(
        "--images-dir",
        help="Extracted image directory. Defaults to <output-dir>/images.",
    )
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG_PATH), help="Parser config YAML path."
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Search input directories recursively."
    )
    style_group = parser.add_mutually_exclusive_group()
    style_group.add_argument(
        "--style-metadata",
        action="store_true",
        dest="style_metadata",
        help="Append Excel fill/pattern metadata to cells (default).",
    )
    style_group.add_argument(
        "--no-style-metadata",
        action="store_false",
        dest="style_metadata",
        help="Do not append Excel fill/pattern metadata to cells.",
    )
    parser.add_argument(
        "--no-images", action="store_true", help="Disable image extraction."
    )
    parser.add_argument("--image-mode", choices=("link", "embed"), default="link")
    parser.add_argument(
        "--heading-base-level", type=int, choices=range(1, 7), default=1
    )
    parser.add_argument("--no-section-heading", action="store_true")
    parser.add_argument("--no-block-spacing", action="store_true")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first conversion error.",
    )
    toc_group = parser.add_mutually_exclusive_group()
    toc_group.add_argument("--toc", action="store_true", dest="toc")
    toc_group.add_argument("--no-toc", action="store_false", dest="toc")
    parser.set_defaults(toc=None, style_metadata=True)
    return parser


def _write_runtime_config(
    config_path: Path, images_enabled: bool, directory: Path
) -> Path:
    config = load_parser_config(config_path)
    config.setdefault("excel", {})["image_extraction"] = images_enabled
    config.setdefault("docx", {})["image_extraction"] = images_enabled
    runtime_config_path = directory / "parser_config.yaml"
    with runtime_config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)
    return runtime_config_path


def run(args: argparse.Namespace) -> int:
    input_files = _collect_input_files(args.inputs, args.recursive)
    output_dir = Path(args.output_dir).expanduser().resolve()
    images_dir = (
        Path(args.images_dir).expanduser().resolve()
        if args.images_dir
        else output_dir / "images"
    )
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Parser config not found: {config_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_images:
        images_dir.mkdir(parents=True, exist_ok=True)

    base_config = load_parser_config(config_path)
    include_toc = (
        base_config.get("markdown_toc_enabled", False) if args.toc is None else args.toc
    )
    print(
        f"[INFO] inputs={len(input_files)} output={output_dir} "
        f"toc={'enabled' if include_toc else 'disabled'} "
        f"images={'disabled' if args.no_images else images_dir}"
    )

    converted = 0
    failed = 0
    with tempfile.TemporaryDirectory(prefix="spec2model_markdown_") as temp_dir:
        runtime_config = _write_runtime_config(
            config_path, not args.no_images, Path(temp_dir)
        )
        for input_path in input_files:
            output_path = output_dir / f"{input_path.stem}.md"
            print(f"[INFO] converting: {input_path}")
            try:
                document = s2m.parse_document(
                    str(input_path),
                    images_dir=None if args.no_images else str(images_dir),
                    config_path=str(runtime_config),
                )
                if args.style_metadata:
                    add_style_metadata_to_document(document)
                options = s2m.MarkdownOptions(
                    heading_base_level=args.heading_base_level,
                    include_section_heading=not args.no_section_heading,
                    image_mode=args.image_mode,
                    newline_between_blocks=not args.no_block_spacing,
                    include_toc=include_toc,
                )
                s2m.to_markdown_file(document, str(output_path), options=options)
                converted += 1
                print(f"[OK] {output_path}")
            except Exception as error:
                failed += 1
                print(f"[ERROR] {input_path}: {error}", file=sys.stderr)
                if args.fail_fast:
                    break

    print(f"[DONE] converted={converted} failed={failed}")
    return 1 if failed else 0


def main() -> int:
    parser = _build_parser()
    try:
        return run(parser.parse_args())
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
