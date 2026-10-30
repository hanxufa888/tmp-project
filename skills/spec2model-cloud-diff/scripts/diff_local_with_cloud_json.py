#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Compare a local Office/PDF document with a freshly exported cloud Document JSON.

This script uses only the workspace-local spec2model package under tools/spec2model.
It intentionally avoids external project code paths so that local-vs-cloud behavior
is fully determined by the current workspace parser and config.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
import yaml

import pandas as pd


def _find_workspace_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "spec2model" / "src").is_dir():
            return parent
    raise RuntimeError("Workspace root with tools/spec2model/src was not found")


WORKSPACE_DIR = _find_workspace_dir()
SPEC2MODEL_SRC_DIR = WORKSPACE_DIR / "tools" / "spec2model" / "src"
PROJECT_SPEC2MODEL_DIR = WORKSPACE_DIR / "tools" / "spec2model"
PROJECT_DIFF_CONFIG_PATH = PROJECT_SPEC2MODEL_DIR / "config" / "diff_config.yaml"
PROJECT_PARSER_CONFIG_PATH = PROJECT_SPEC2MODEL_DIR / "config" / "parser_config.yaml"
IMPORT_SPEC2MODEL_SRC_DIR = SPEC2MODEL_SRC_DIR

if (
    IMPORT_SPEC2MODEL_SRC_DIR.is_dir()
    and str(IMPORT_SPEC2MODEL_SRC_DIR) not in sys.path
):
    sys.path.insert(0, str(IMPORT_SPEC2MODEL_SRC_DIR))

from spec2model.diff import (
    DiffMeta,
    DiffOptions,
    apply_default_diff_filters,
    build_diff_options,
    compare_documents,
)
from spec2model.exporters import render_diff_html
from spec2model.models import (
    Chapter,
    Document,
    ImageBlock,
    Paragraph,
    Sheet,
    TableBlock,
    TextBlock,
)
from image_diff import compare_document_images


def _load_project_diff_config() -> Dict[str, Any]:
    if not PROJECT_DIFF_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Project diff config not found: {PROJECT_DIFF_CONFIG_PATH}"
        )
    with PROJECT_DIFF_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _ensure_project_parser_config() -> None:
    if not PROJECT_PARSER_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Project parser config not found: {PROJECT_PARSER_CONFIG_PATH}"
        )
    with PROJECT_PARSER_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        yaml.safe_load(handle)


_PIPE_PLACEHOLDER = "\x00PIPE\x00"
_IMAGE_REF_PATTERN = re.compile(r"\{\{IMAGE_REF:[^}]+\}\}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare one local document with one cloud Document JSON.",
    )
    parser.add_argument("local_file", help="Local Office/PDF document path.")
    parser.add_argument(
        "cloud_ref",
        help=(
            "Path to a Document JSON freshly exported with "
            "graph_export_document_json before this comparison."
        ),
    )
    parser.add_argument(
        "--local-side",
        choices=("old", "new"),
        default="new",
        help="Whether the local file is the old or new side. Defaults to new.",
    )
    parser.add_argument("--local-name", help="Display name for the local side.")
    parser.add_argument("--cloud-name", help="Display name for the cloud JSON side.")
    parser.add_argument(
        "--out-csv",
        default="diff_local_cloud.csv",
        help="CSV output path. Defaults to diff_local_cloud.csv.",
    )
    parser.add_argument("--out-html", help="Optional HTML output path.")
    parser.add_argument(
        "--out-image-json",
        help="Image comparison JSON path. Defaults beside --out-csv.",
    )
    parser.add_argument(
        "--images-dir",
        help="Optional extracted images directory passed to local parser.",
    )
    parser.add_argument(
        "--local-parser",
        choices=("auto", "current"),
        default="auto",
        help=(
            "Parser used for local file. 'auto' uses the current local project parser."
        ),
    )
    parser.add_argument("--text-similarity", type=float, default=None)
    parser.add_argument("--row-similarity", type=float, default=None)
    parser.add_argument("--normalize-mode", default=None)

    parser.add_argument(
        "--project-local-as-graph",
        dest="project_local_as_graph",
        action="store_true",
        help=(
            "Project local parsed document to graph-compatible "
            "block semantics (TextBlock/TableBlock only)."
        ),
    )
    parser.add_argument(
        "--granularity",
        choices=("block", "paragraph", "chapter"),
        default="block",
        help="Output granularity. Defaults to block (raw compare_documents rows).",
    )

    word_level_group = parser.add_mutually_exclusive_group()
    word_level_group.add_argument(
        "--word-level-diff",
        action="store_true",
        dest="use_word_level_diff",
    )
    word_level_group.add_argument(
        "--char-level-diff",
        action="store_false",
        dest="use_word_level_diff",
    )
    parser.set_defaults(
        use_word_level_diff=None,
        project_local_as_graph=True,
    )

    parser.add_argument("--no-summary", action="store_true")
    parser.add_argument(
        "--cloud-source",
        choices=("auto", "json"),
        default="auto",
        help=(
            "Cloud source mode. The JSON must be refreshed from "
            "graph_export_document_json before invoking this script."
        ),
    )
    parser.add_argument(
        "--image-compare",
        choices=("auto", "bytes", "perceptual"),
        default="auto",
        help=(
            "How to judge paired images as changed/unchanged. 'bytes' requires "
            "identical base64 (use for same-platform local-vs-local). "
            "'perceptual' tolerates cross-platform render noise (Windows vs the "
            "Linux cloud renderer). 'auto' (default) uses perceptual when the "
            "cloud side is a Document JSON (local-vs-cloud) and bytes otherwise."
        ),
    )
    return parser


def _build_options(args: argparse.Namespace, config: dict) -> DiffOptions:
    diff_options = config.get("diff_options", {})
    options = build_diff_options(
        text_similarity_min=args.text_similarity,
        row_similarity_min=args.row_similarity,
    )
    if args.use_word_level_diff is not None:
        options.use_word_level_diff = args.use_word_level_diff
    if args.normalize_mode is not None:
        options.normalize_mode = args.normalize_mode
    if not hasattr(options, "max_pairing_cost"):
        options.max_pairing_cost = int(diff_options.get("max_pairing_cost", 10**6))
    if not getattr(options, "preferred_unique_column_keywords", None):
        options.preferred_unique_column_keywords = diff_options.get(
            "preferred_unique_column_keywords",
            ["No", "No."],
        )
    return options


def _parse_local_document(
    args: argparse.Namespace, local_path: Path
) -> Tuple[Document, str]:
    errors: List[str] = []

    if args.local_parser in ("auto", "current"):
        try:
            from spec2model.parsers import parse_document as parse_document_current

            images_dir = args.images_dir
            if not images_dir:
                images_dir = str(PROJECT_SPEC2MODEL_DIR / "data" / "images")
            Path(images_dir).mkdir(parents=True, exist_ok=True)

            return parse_document_current(
                str(local_path),
                images_dir=images_dir,
                config_path=str(PROJECT_PARSER_CONFIG_PATH),
            ), "current"
        except Exception as exc:
            errors.append(f"current parser failed: {exc}")

    raise RuntimeError("Unable to parse local document. " + " | ".join(errors))


def document_from_json_file(path: Path) -> Document:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return document_from_json_dict(payload)


def _resolve_cloud_document(args: argparse.Namespace) -> Tuple[Document, str, str]:
    """Return (document, display_name, source_label)."""
    cloud_ref = args.cloud_ref
    cloud_ref_path = Path(cloud_ref).expanduser()
    cloud_json_exists = (
        cloud_ref_path.exists()
        and cloud_ref_path.is_file()
        and cloud_ref_path.suffix.lower() == ".json"
    )

    mode = args.cloud_source
    if mode == "json" or (mode == "auto" and cloud_json_exists):
        cloud_json_path = cloud_ref_path.resolve()
        doc = document_from_json_file(cloud_json_path)
        inferred_cloud_name = _extract_cloud_file_name_from_json(cloud_json_path)
        display_name = args.cloud_name or inferred_cloud_name or cloud_json_path.name
        return doc, display_name, "json"

    raise RuntimeError(
        "Fresh cloud Document JSON not found. Export the document with "
        "graph_export_document_json, save it locally, then use --cloud-source json."
    )


def _extract_cloud_file_name_from_json(path: Path) -> Optional[str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return None

    if isinstance(payload, dict):
        value = payload.get("file_name")
        if isinstance(value, str) and value.strip():
            return value.strip()
        node = payload.get("document")
        if isinstance(node, dict):
            value = node.get("file_name")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def document_from_json_dict(payload: dict[str, Any]) -> Document:
    node = payload.get("document", payload)
    sheet_items = [
        _sheet_from_json(item)
        for item in node.get("sheets", node.get("sections", [])) or []
    ]
    chapter_items = [
        _chapter_from_json(item) for item in node.get("chapters", []) or []
    ]
    content_items = [_block_from_json(item) for item in node.get("contents", []) or []]

    document = Document(
        sheets=[item for item in sheet_items if item is not None],
        chapters=[item for item in chapter_items if item is not None],
        contents=[item for item in content_items if item is not None],
    )
    return _restore_id(document, node)


def _sheet_from_json(node: dict[str, Any]) -> Sheet:
    content_items = [_block_from_json(item) for item in node.get("contents", []) or []]
    chapter_items = [
        _chapter_from_json(item) for item in node.get("chapters", []) or []
    ]
    sheet = Sheet(
        name=str(node.get("name", "")),
        contents=[item for item in content_items if item is not None],
        chapters=[item for item in chapter_items if item is not None],
    )
    return _restore_id(sheet, node)


def _chapter_from_json(node: dict[str, Any]) -> Chapter:
    content_items = [_block_from_json(item) for item in node.get("contents", []) or []]
    paragraph_items = [
        _paragraph_from_json(item) for item in node.get("paragraphs", []) or []
    ]
    chapter = Chapter(
        title=str(node.get("title", "")),
        order=int(node.get("order") or 0),
        contents=[item for item in content_items if item is not None],
        paragraphs=[item for item in paragraph_items if item is not None],
    )
    return _restore_id(chapter, node)


def _paragraph_from_json(node: dict[str, Any]) -> Paragraph:
    content_items = [_block_from_json(item) for item in node.get("contents", []) or []]
    paragraph_items = [
        _paragraph_from_json(item) for item in node.get("paragraphs", []) or []
    ]
    paragraph = Paragraph(
        order=int(node.get("order") or 0),
        title=str(node.get("title", "")),
        contents=[item for item in content_items if item is not None],
        paragraphs=[item for item in paragraph_items if item is not None],
    )
    return _restore_id(paragraph, node)


def _block_from_json(node: dict[str, Any]) -> Optional[Any]:
    kind = node.get("kind")
    if kind == "text":
        text = str(node.get("text", ""))
        if not text.strip():
            return None
        return _restore_id(
            TextBlock(text=text, order=int(node.get("order") or 0)), node
        )
    if kind == "table":
        return _table_from_json(node)
    if kind == "image":
        return _image_from_json(node)

    text = str(node.get("text", ""))
    if not text.strip():
        return None
    return _restore_id(TextBlock(text=text, order=int(node.get("order") or 0)), node)


def _image_from_json(node: dict[str, Any]) -> ImageBlock:
    image = ImageBlock(
        path=str(node.get("path") or ""),
        section=str(node.get("section") or ""),
        row=int(node.get("row") or 0),
        col=int(node.get("col") or 0),
        name=str(node.get("name") or ""),
        ext=str(node.get("ext") or ""),
        order=int(node.get("order") or 0),
        data_b64=node.get("data_b64"),
    )
    return _restore_id(image, node)


def _table_from_json(node: dict[str, Any]) -> Optional[TableBlock]:
    table = node.get("table") or {}
    headers = [str(item) for item in table.get("headers", []) or []]
    rows = table.get("rows", []) or []
    markdown = str(node.get("markdown") or "")
    markdown_df, markdown_title = _parse_markdown_to_df(markdown)
    title = node.get("title") or markdown_title
    table_images = [
        _image_from_json(item)
        for item in node.get("images", []) or []
        if item.get("kind") == "image"
    ]

    # Mirror graph_diff_documents _build_blocks semantics: markdown -> df only.
    # A table without a parseable markdown body carries no text/table diff, but
    # its images must still reach image comparison, so preserve an image-only
    # placeholder table instead of dropping the block entirely.
    if not markdown.strip() or markdown_df.empty:
        if not table_images:
            return None
        placeholder = TableBlock.from_df(pd.DataFrame(), title=title)
        placeholder.order = int(node.get("order") or 0)
        _restore_id(placeholder, node)
        placeholder.images = table_images
        return placeholder

    block = TableBlock.from_df(markdown_df, title=title)

    block.order = int(node.get("order") or 0)
    _restore_id(block, node)
    block.images = table_images

    row_ids = list(node.get("row_dfs_ids", []) or [])
    if len(row_ids) == len(block.row_dfs):
        block.row_dfs_ids = row_ids
    return block


def _print_summary(df: pd.DataFrame) -> None:
    print("=== Diff Summary ===")
    print(f"Total rows: {len(df)}")
    for column in ["change_type", "scope", "block_type"]:
        if column in df.columns:
            print(f"{column}:")
            for key, value in df[column].value_counts().items():
                print(f"  {key}: {value}")


def _contains_image_ref(value: Any) -> bool:
    return bool(_IMAGE_REF_PATTERN.search("" if value is None else str(value)))


def _without_image_refs(value: Any) -> str:
    return _IMAGE_REF_PATTERN.sub("", "" if value is None else str(value)).strip()


def _normalize_for_image_ref_only_compare(value: Any) -> str:
    text = _without_image_refs(value)
    df, title = _parse_markdown_to_df(text)
    if not df.empty:
        normalized_rows: List[List[str]] = []
        for _, row in df.iterrows():
            normalized_rows.append(
                [re.sub(r"\s+", "", str(cell)) for cell in row.tolist()]
            )
        normalized_title = re.sub(r"\s+", "", title or "")
        return json.dumps(
            [normalized_title, normalized_rows], ensure_ascii=False, sort_keys=True
        )
    return re.sub(r"\s+", "", text)


def _is_pure_image_ref_only_diff(row: Any) -> bool:
    before = (
        "" if pd.isna(row.get("before_markdown")) else str(row.get("before_markdown"))
    )
    after = "" if pd.isna(row.get("after_markdown")) else str(row.get("after_markdown"))
    if not (_contains_image_ref(before) or _contains_image_ref(after)):
        return False
    return _normalize_for_image_ref_only_compare(
        before
    ) == _normalize_for_image_ref_only_compare(after)


def _count_pure_image_ref_only_diffs(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    if "before_markdown" not in df.columns or "after_markdown" not in df.columns:
        return 0

    count = 0
    for _, row in df.iterrows():
        if _is_pure_image_ref_only_diff(row):
            count += 1
    return count


def _drop_pure_image_ref_only_diffs(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    if df.empty:
        return df, 0
    if "before_markdown" not in df.columns or "after_markdown" not in df.columns:
        return df, 0

    mask = df.apply(_is_pure_image_ref_only_diff, axis=1)
    count = int(mask.sum())
    if count == 0:
        return df, 0
    return df.loc[~mask].copy(), count


def _strip_image_refs_from_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return _IMAGE_REF_PATTERN.sub("", value)


def _ignore_image_ref_diffs(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Remove image-reference-only changes and hide refs in mixed changes."""
    if (
        df.empty
        or "before_markdown" not in df.columns
        or "after_markdown" not in df.columns
    ):
        return df, 0

    before = df["before_markdown"].fillna("").astype(str)
    after = df["after_markdown"].fillna("").astype(str)
    has_image_ref = before.str.contains(_IMAGE_REF_PATTERN) | after.str.contains(
        _IMAGE_REF_PATTERN
    )
    normalized_before = before.map(_strip_image_refs_from_value)
    normalized_after = after.map(_strip_image_refs_from_value)
    ignored = has_image_ref & normalized_before.eq(normalized_after)

    cleaned = df.copy()
    for column in cleaned.columns:
        if cleaned[column].dtype == object:
            cleaned[column] = cleaned[column].map(_strip_image_refs_from_value)
    return cleaned.loc[~ignored].copy(), int(ignored.sum())


def _image_report_to_rows(
    image_report: Dict[str, Any],
    cloud_side: Optional[str] = None,
) -> pd.DataFrame:
    """Represent image statuses as rows in the main CSV/HTML result."""
    rows: List[Dict[str, Any]] = []
    status_to_change_type = {
        "changed": "changed",
        "added": "added",
        "removed": "removed",
    }
    for item in image_report.get("items", []):
        old = item.get("old") or {}
        new = item.get("new") or {}
        status = str(item.get("status") or "unavailable")
        if status not in status_to_change_type:
            continue
        old_name = old.get("name") or ""
        new_name = new.get("name") or ""
        old_id = old.get("id") or ""
        new_id = new.get("id") or ""
        cloud_record = (
            old if cloud_side == "old" else new if cloud_side == "new" else {}
        )
        cloud_id = cloud_record.get("id") or ""
        before_name = old_name if status != "added" else ""
        after_name = new_name if status != "removed" else ""
        before_id = old_id if status != "added" else ""
        after_id = new_id if status != "removed" else ""
        fallback_id = after_id or before_id
        imageblock_id = cloud_id or fallback_id
        before_content = (
            f"image_name:{before_name}\nimageblock_id:{imageblock_id}"
            if before_name
            else ""
        )
        after_content = (
            f"image_name:{after_name}\nimageblock_id:{imageblock_id}"
            if after_name
            else ""
        )
        display_content = (
            before_content if status == "removed" else after_content or before_content
        )
        rows.append(
            {
                "change_type": status_to_change_type.get(status, status),
                "scope": "image",
                "block_type": "image",
                "sheet_name": old.get("sheet_name") or new.get("sheet_name"),
                "chapter_name": old.get("chapter_title") or new.get("chapter_title"),
                "paragraph_name": old.get("paragraph_title")
                or new.get("paragraph_title"),
                "before_markdown": before_content,
                "after_markdown": after_content,
                "display_content": display_content,
            }
        )
    return pd.DataFrame(rows)


def _append_image_report_rows(
    df: pd.DataFrame,
    image_report: Dict[str, Any],
    cloud_side: Optional[str] = None,
) -> pd.DataFrame:
    image_rows = _image_report_to_rows(image_report, cloud_side=cloud_side)
    if image_rows.empty:
        return df

    def normalized_path_part(value: Any) -> str:
        return re.sub(r"\s+", "", "" if pd.isna(value) else str(value)).casefold()

    def path_key(row: pd.Series, include_paragraph: bool) -> Tuple[str, ...]:
        parts = [normalized_path_part(row.get("sheet_name"))]
        parts.append(normalized_path_part(row.get("chapter_name")))
        if include_paragraph:
            parts.append(normalized_path_part(row.get("paragraph_name")))
        return tuple(parts)

    text_rows = [row.copy() for _, row in df.iterrows()]
    last_by_paragraph: Dict[Tuple[str, ...], int] = {}
    last_by_chapter: Dict[Tuple[str, ...], int] = {}
    last_by_sheet: Dict[str, int] = {}
    for index, row in enumerate(text_rows):
        paragraph_key = path_key(row, include_paragraph=True)
        chapter_key = path_key(row, include_paragraph=False)
        sheet_key = chapter_key[0]
        if any(paragraph_key):
            last_by_paragraph[paragraph_key] = index
        if any(chapter_key):
            last_by_chapter[chapter_key] = index
        if sheet_key:
            last_by_sheet[sheet_key] = index

    images_after: Dict[int, List[pd.Series]] = {}
    for _, image_row in image_rows.iterrows():
        paragraph_key = path_key(image_row, include_paragraph=True)
        chapter_key = path_key(image_row, include_paragraph=False)
        sheet_key = chapter_key[0]
        insert_after = last_by_paragraph.get(paragraph_key)
        if insert_after is None:
            insert_after = last_by_chapter.get(chapter_key)
        if insert_after is None:
            insert_after = last_by_sheet.get(sheet_key)
        if insert_after is None:
            insert_after = len(text_rows) - 1
        images_after.setdefault(insert_after, []).append(image_row)

    merged_rows: List[pd.Series] = []
    for index, row in enumerate(text_rows):
        merged_rows.append(row)
        merged_rows.extend(images_after.pop(index, []))
    for image_rows_without_text in images_after.values():
        merged_rows.extend(image_rows_without_text)
    return pd.DataFrame(merged_rows).reindex(columns=df.columns).reset_index(drop=True)


def _restore_id(obj: Any, source: Any) -> Any:
    value = (
        source.get("id") if isinstance(source, dict) else getattr(source, "id", None)
    )
    if value:
        obj.id = value
    return obj


def _parse_markdown_to_df(markdown: str) -> Tuple[pd.DataFrame, Optional[str]]:
    lines = markdown.strip().split("\n")
    if not lines:
        return pd.DataFrame(), None

    title: Optional[str] = None
    while lines and not lines[0].strip().startswith("|"):
        title_line = lines.pop(0).strip()
        if title_line:
            title = title_line

    if len(lines) < 2:
        return pd.DataFrame(), title

    headers = _parse_md_row(lines[0])

    data_start = 1
    if len(lines) > 1:
        sep_cells = _parse_md_row(lines[1])
        if all(_is_separator_cell(cell) for cell in sep_cells):
            data_start = 2

    rows: List[List[str]] = []
    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        row = _parse_md_row(stripped)
        while len(row) < len(headers):
            row.append("")
        rows.append(row[: len(headers)])

    if not headers:
        return pd.DataFrame(), title
    return pd.DataFrame(rows, columns=headers), title


def _parse_md_row(line: str) -> List[str]:
    line = line.replace("\\|", _PIPE_PLACEHOLDER)
    parts = line.split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [_normalize_md_cell(part.replace(_PIPE_PLACEHOLDER, "|")) for part in parts]


def _normalize_md_cell(value: str) -> str:
    text = value.strip()
    if not text:
        return ""

    # Keep markdown cells as-is (except surrounding spaces) to match
    # graph_diff_documents markdown parser semantics.
    return text


def _is_separator_cell(cell: str) -> bool:
    stripped = cell.strip()
    if not stripped:
        return True
    return bool(re.match(r"^:?-+:?$", stripped))


def _project_blocks_like_graph_handler(blocks: list[Any]) -> list[Any]:
    """Project blocks to graph-compatible semantics."""
    projected: List[Any] = []
    for block in blocks:
        if isinstance(block, TextBlock):
            text = block.text or ""
            if not text.strip():
                continue
            projected.append(
                _restore_id(TextBlock(text=text, order=block.order), block)
            )
            continue

        if isinstance(block, TableBlock):
            markdown = getattr(block, "markdown", "") or ""
            if not markdown.strip():
                continue
            df, title = _parse_markdown_to_df(markdown)
            if df.empty:
                continue
            new_block = TableBlock.from_df(df, title=title)
            new_block.order = block.order
            _restore_id(new_block, block)
            row_ids = list(getattr(block, "row_dfs_ids", []) or [])
            if row_ids:
                new_block.row_dfs_ids = row_ids
            projected.append(new_block)
    return projected


def _project_paragraph_like_graph_handler(paragraph: Paragraph) -> Paragraph:
    projected = Paragraph(
        order=paragraph.order,
        title=paragraph.title,
        contents=_project_blocks_like_graph_handler(paragraph.contents),
        paragraphs=[
            _project_paragraph_like_graph_handler(item) for item in paragraph.paragraphs
        ],
    )
    return _restore_id(projected, paragraph)


def _project_chapter_like_graph_handler(chapter: Chapter) -> Chapter:
    projected = Chapter(
        title=chapter.title,
        order=chapter.order,
        contents=_project_blocks_like_graph_handler(chapter.contents),
        paragraphs=[
            _project_paragraph_like_graph_handler(item) for item in chapter.paragraphs
        ],
    )
    return _restore_id(projected, chapter)


def _project_sheet_like_graph_handler(sheet: Sheet) -> Sheet:
    projected = Sheet(
        name=sheet.name,
        contents=_project_blocks_like_graph_handler(sheet.contents),
        chapters=[_project_chapter_like_graph_handler(item) for item in sheet.chapters],
    )
    return _restore_id(projected, sheet)


def project_document_like_graph_handler(document: Document) -> Document:
    projected = Document(
        sheets=[_project_sheet_like_graph_handler(item) for item in document.sheets],
        chapters=[
            _project_chapter_like_graph_handler(item) for item in document.chapters
        ],
        contents=_project_blocks_like_graph_handler(document.contents),
    )
    return _restore_id(projected, document)


def _safe_first(df: pd.DataFrame, col: str) -> Optional[str]:
    if col not in df.columns:
        return None
    vals = df[col].dropna()
    if vals.empty:
        return None
    val = vals.iloc[0]
    return str(val) if val is not None else None


def _safe_val(row: Any, key: str) -> Optional[str]:
    val = row.get(key) if hasattr(row, "get") else getattr(row, key, None)
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    return str(val)


def _df_to_block_items(df: pd.DataFrame) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        item: Dict[str, Any] = {
            "change_type": row.get("change_type", "unknown"),
            "scope": row.get("scope", "block"),
            "sheet_name": _safe_val(row, "sheet_name"),
            "chapter_key": _safe_val(row, "chapter_key"),
            "paragraph_key": _safe_val(row, "paragraph_key"),
            "block_type": row.get("granularity") or row.get("block_type"),
            "before_markdown": _safe_val(row, "before_markdown"),
            "after_markdown": _safe_val(row, "after_markdown"),
        }
        items.append(item)
    return items


def aggregate_diff_items(df: pd.DataFrame, granularity: str) -> List[Dict[str, Any]]:
    if df.empty:
        return []

    if granularity == "block":
        return _df_to_block_items(df)

    if granularity == "chapter":
        group_keys = ["sheet_name", "chapter_key"]
    elif granularity == "paragraph":
        group_keys = ["sheet_name", "chapter_key", "paragraph_key"]
    else:
        return _df_to_block_items(df)

    group_keys = [k for k in group_keys if k in df.columns]
    if not group_keys:
        return _df_to_block_items(df)

    items: List[Dict[str, Any]] = []
    for group_key, group_df in df.groupby(group_keys, dropna=False):
        change_types = group_df["change_type"].value_counts().to_dict()
        agg_change_type = (
            list(change_types.keys())[0] if len(change_types) == 1 else "mixed"
        )

        before_col = (
            "before_markdown" if "before_markdown" in group_df.columns else None
        )
        after_col = "after_markdown" if "after_markdown" in group_df.columns else None

        before_texts = group_df[before_col].dropna().tolist() if before_col else []
        after_texts = group_df[after_col].dropna().tolist() if after_col else []

        if isinstance(group_key, tuple):
            path_parts = [
                str(v)
                for v in group_key
                if v is not None and str(v) != "nan" and str(v).strip()
            ]
        else:
            path_parts = (
                [str(group_key)]
                if group_key is not None and str(group_key) != "nan"
                else []
            )

        block_types_col = (
            "granularity" if "granularity" in group_df.columns else "block_type"
        )
        block_types = (
            list(group_df[block_types_col].dropna().unique())
            if block_types_col in group_df.columns
            else []
        )

        item: Dict[str, Any] = {
            "change_type": agg_change_type,
            "scope": granularity,
            "sheet_name": _safe_first(group_df, "sheet_name")
            if "sheet_name" in group_df.columns
            else None,
            "chapter_key": _safe_first(group_df, "chapter_key")
            if "chapter_key" in group_df.columns
            else None,
            "path": " > ".join(path_parts),
            "change_count": len(group_df),
            "change_summary": change_types,
            "before_markdown_preview": "\n".join(str(t) for t in before_texts[:5])[
                :500
            ],
            "after_markdown_preview": "\n".join(str(t) for t in after_texts[:5])[:500],
            "block_types": block_types,
        }

        if granularity == "paragraph" and "paragraph_key" in group_df.columns:
            item["paragraph_key"] = _safe_first(group_df, "paragraph_key")

        items.append(item)

    return items


def _print_items_summary(items: List[Dict[str, Any]], granularity: str) -> None:
    print("=== Aggregated Summary ===")
    print(f"Granularity: {granularity}")
    print(f"Total items: {len(items)}")
    if not items:
        return

    counts = pd.Series(
        [item.get("change_type", "unknown") for item in items]
    ).value_counts()
    for key, value in counts.items():
        print(f"  {key}: {value}")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    local_path = Path(args.local_file).expanduser().resolve()
    if not local_path.exists():
        parser.error(f"Local file not found: {local_path}")

    config = _load_project_diff_config()
    _ensure_project_parser_config()
    options = _build_options(args, config)

    local_doc, parser_label = _parse_local_document(args, local_path)
    cloud_doc, cloud_name, cloud_source = _resolve_cloud_document(args)
    image_old_doc, image_new_doc = (
        (local_doc, cloud_doc) if args.local_side == "old" else (cloud_doc, local_doc)
    )

    if args.project_local_as_graph:
        local_doc = project_document_like_graph_handler(local_doc)

    local_name = args.local_name or local_path.name

    if args.local_side == "old":
        old_doc, new_doc = local_doc, cloud_doc
        file_old, file_new = local_name, cloud_name
    else:
        old_doc, new_doc = cloud_doc, local_doc
        file_old, file_new = cloud_name, local_name
    cloud_image_side = "new" if args.local_side == "old" else "old"

    # local-vs-cloud renders on different platforms (Windows vs Linux cloud), so
    # identical shapes produce different PNG bytes. Use perceptual image matching
    # there; keep exact byte matching for same-platform comparisons.
    if args.image_compare == "auto":
        image_perceptual = cloud_source == "json"
    else:
        image_perceptual = args.image_compare == "perceptual"

    print("Comparing documents:")
    print(f"  old: {file_old}")
    print(f"  new: {file_new}")
    print(f"  local_parser: {parser_label}")
    print(f"  cloud_source: {cloud_source}")
    print(f"  image_compare: {'perceptual' if image_perceptual else 'bytes'}")
    raw_df = compare_documents(
        old_doc,
        new_doc,
        meta=DiffMeta(file_old=file_old, file_new=file_new),
        options=options,
    )
    image_report = compare_document_images(
        image_old_doc,
        image_new_doc,
        diff_rows=raw_df.to_dict("records"),
        perceptual=image_perceptual,
        cloud_side=cloud_image_side,
    )
    df = apply_default_diff_filters(raw_df)
    df, skipped_image_ref_only = _drop_pure_image_ref_only_diffs(df)
    df = _append_image_report_rows(df, image_report, cloud_side=cloud_image_side)

    if not args.no_summary:
        if skipped_image_ref_only > 0:
            print(f"Skipped pure IMAGE_REF-only diffs: {skipped_image_ref_only}")
        _print_summary(df)
        if args.granularity != "block":
            items = aggregate_diff_items(df, args.granularity)
            _print_items_summary(items, args.granularity)

    csv_path = Path(args.out_csv).expanduser()
    if csv_path.exists():
        print(f"[INFO] Existing CSV will be overwritten (no reuse): {csv_path}")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_encoding = "utf-8"
    df.to_csv(csv_path, index=False, encoding=csv_encoding)
    print(f"[OK] CSV: {csv_path} (encoding={csv_encoding})")

    image_json_path = (
        Path(args.out_image_json).expanduser()
        if args.out_image_json
        else csv_path.with_suffix(".images.json")
    )
    image_json_path.parent.mkdir(parents=True, exist_ok=True)
    image_json_path.write_text(
        json.dumps(image_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[OK] Image JSON: {image_json_path}")
    if not args.no_summary:
        print(
            "Image summary:",
            json.dumps(image_report["summary"], ensure_ascii=False, sort_keys=True),
        )

    if args.out_html:
        html_path = Path(args.out_html).expanduser()
        if html_path.exists():
            print(f"[INFO] Existing HTML will be overwritten (no reuse): {html_path}")
        html_path.parent.mkdir(parents=True, exist_ok=True)
        old_name = Path(file_old).stem
        new_name = Path(file_new).stem
        render_diff_html(
            df,
            str(html_path),
            title=f"Diff Report: {old_name} -> {new_name}",
            image_summary=image_report["summary"],
        )
        print(f"[OK] HTML: {html_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
