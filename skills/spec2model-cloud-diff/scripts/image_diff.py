"""Compare ImageBlock content without depending on document text differences."""

from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from spec2model.models import Chapter, Document, ImageBlock, Paragraph, TableBlock


# Perceptual comparison defaults. Used only when perceptual=True (local-vs-cloud),
# to tolerate cross-platform render noise (Windows Cairo/fonts vs Linux) so that
# visually-identical shapes are not reported as changed. Local-vs-local keeps the
# exact byte comparison and never uses this path.
_PERCEPTUAL_SIZE = 32  # downscale both images to this square before comparing
_PERCEPTUAL_MAX_MEAN_DIFF = 8.0  # mean per-pixel abs diff (0..255); <= => same

# Thresholds for same-size full-resolution comparisons.
_PIXEL_DIFF_TOLERANCE = 16.0  # per-pixel max RGB abs diff above this => changed pixel
_CHANGED_PIXEL_RATIO_THRESHOLD = 0.001  # >=0.1% changed pixels => changed
_MEAN_DIFF_THRESHOLD = 8.0  # or mean per-pixel abs diff above this => changed


def _decode_b64(data: Any) -> Optional[bytes]:
    if not data:
        return None
    if isinstance(data, bytes):
        return data
    try:
        return base64.b64decode(str(data), validate=False)
    except (binascii.Error, ValueError):
        return None


@lru_cache(maxsize=4096)
def _perceptual_signature(data: Any) -> Optional[Tuple[int, ...]]:
    """Return a small grayscale fingerprint of a PNG/base64 image.

    Downscales to a fixed square and returns the luminance grid. Two images whose
    signatures differ by a small mean absolute difference are treated as the same
    picture rendered slightly differently across platforms.
    """
    raw = _decode_b64(data)
    if raw is None:
        return None
    try:
        from PIL import Image  # local import; PIL is a spec2model dependency

        with Image.open(BytesIO(raw)) as image:
            # Flatten transparency onto white so alpha differences do not dominate.
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                background.alpha_composite(rgba)
                image = background.convert("L")
            else:
                image = image.convert("L")
            small = image.resize((_PERCEPTUAL_SIZE, _PERCEPTUAL_SIZE))
            return tuple(small.getdata())
    except Exception:  # noqa: BLE001 - any decode/render failure => no signature
        return None


@lru_cache(maxsize=1024)
def _full_resolution_signature(data: Any) -> Optional[Any]:
    """Return full-resolution RGB pixels, or None when decoding fails."""
    raw = _decode_b64(data)
    if raw is None:
        return None
    try:
        import numpy as np
        from PIL import Image  # local import; PIL is a spec2model dependency

        with Image.open(BytesIO(raw)) as image:
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                background.alpha_composite(rgba)
                image = background.convert("RGB")
            else:
                image = image.convert("RGB")
            return np.asarray(image, dtype=np.int16)
    except Exception:  # noqa: BLE001 - any decode/render failure => no signature
        return None


def _full_resolution_same_content(old_data: Any, new_data: Any) -> Optional[bool]:
    """Compare equal-size images at full resolution; return None otherwise."""
    a = _full_resolution_signature(old_data)
    b = _full_resolution_signature(new_data)
    if a is None or b is None:
        return None
    if a.shape != b.shape:
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    diff = np.abs(a - b)
    mean_diff = float(diff.mean())
    changed_pixels = int((diff.max(axis=-1) > _PIXEL_DIFF_TOLERANCE).sum())
    total = a.shape[0] * a.shape[1]
    changed_ratio = changed_pixels / total if total else 0.0
    is_changed = (
        changed_ratio >= _CHANGED_PIXEL_RATIO_THRESHOLD
        or mean_diff > _MEAN_DIFF_THRESHOLD
    )
    return not is_changed


def _images_visually_equal(
    old_data: Any,
    new_data: Any,
    max_mean_diff: float = _PERCEPTUAL_MAX_MEAN_DIFF,
) -> Optional[bool]:
    """Compare bytes, then same-size pixels, then perceptual signatures."""
    if old_data is not None and new_data is not None and old_data == new_data:
        return True
    full = _full_resolution_same_content(old_data, new_data)
    if full is not None:
        return full
    old_sig = _perceptual_signature(old_data)
    new_sig = _perceptual_signature(new_data)
    if old_sig is None or new_sig is None:
        return None
    total = sum(abs(a - b) for a, b in zip(old_sig, new_sig))
    mean_diff = total / len(old_sig)
    return mean_diff <= max_mean_diff


def _build_visual_match_map(
    old_refs: List[Dict[str, Any]],
    new_refs: List[Dict[str, Any]],
    max_mean_diff: float = _PERCEPTUAL_MAX_MEAN_DIFF,
) -> Tuple[Dict[str, str], Dict[str, set]]:
    """Find, for every old image, which new images look like it.

    Cross-platform renders never match byte-for-byte, so without this the
    content-based pairing stage finds nothing and nearly every image ends up
    reported as added/removed instead of paired.

    Returns ``(closest, similar)``:

    - ``closest`` maps an old id to its single nearest new image, and only when
      that image is strictly nearer than every other candidate. This mirrors byte
      equality, which also pairs only when exactly one identical image exists. A
      looser rule pulls in near-identical shapes, makes the match ambiguous, and
      pushes the pair down to positional matching, which mispairs once rows shift.
    - ``similar`` maps an old id to every candidate within the threshold, for the
      later fallback stage where an approximate partner beats no partner.
    """
    try:
        import numpy as np
    except ImportError:
        return {}, {}

    def signatures(refs: List[Dict[str, Any]]) -> List[Tuple[str, Tuple[int, ...]]]:
        out = []
        for ref in refs:
            image_id = str(ref.get("image_id_hint") or "")
            signature = _perceptual_signature(ref.get("data_b64"))
            if image_id and signature:
                out.append((image_id, signature))
        return out

    old_items = signatures(old_refs)
    new_items = signatures(new_refs)
    if not old_items or not new_items:
        return {}, {}

    new_ids = [image_id for image_id, _ in new_items]
    new_matrix = np.asarray([signature for _, signature in new_items], dtype=np.int16)
    closest: Dict[str, str] = {}
    similar: Dict[str, set] = {}
    chunk_size = 32  # keeps the broadcast difference buffer at a few tens of MB
    for start in range(0, len(old_items), chunk_size):
        block = old_items[start : start + chunk_size]
        old_matrix = np.asarray([signature for _, signature in block], dtype=np.int16)
        mean_diffs = np.abs(old_matrix[:, None, :] - new_matrix[None, :, :]).mean(
            axis=2
        )
        for row, (old_id, _) in enumerate(block):
            row_diffs = mean_diffs[row]
            hits = np.flatnonzero(row_diffs <= max_mean_diff)
            if not hits.size:
                continue
            similar[old_id] = {new_ids[int(index)] for index in hits}
            nearest = hits[row_diffs[hits] == row_diffs[hits].min()]
            if nearest.size == 1:
                closest[old_id] = new_ids[int(nearest[0])]
    return closest, similar


# Strip only known image extensions before parsing anchored name suffixes.
_IMAGE_NAME_EXT_RE = re.compile(
    r"\.(?:png|jpe?g|gif|bmp|tiff?|webp|svg|emf|wmf)$",
    re.IGNORECASE,
)


def _image_name_stem(name: str) -> str:
    return _IMAGE_NAME_EXT_RE.sub("", (name or "").strip())


_IMAGE_LOCATION_RE = re.compile(
    r"(?:^|_)r(?P<row>\d+)_c(?P<col>\d+)"
    r"(?:_rect_(?P<rect>\d+))?(?:\.[^.]+)?$",
    re.IGNORECASE,
)
_IMAGE_CHAPTER_RE = re.compile(
    r"(?:^|_)chapter_(?P<chapter>\d+)_pic(?P<picture>\d+)(?:\.[^.]+)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImageRecord:
    image: ImageBlock
    scope: str
    sheet_name: Optional[str]
    chapter_title: Optional[str]
    paragraph_title: Optional[str]

    @property
    def location_key(self) -> Optional[Tuple[str, int, int]]:
        name_match = _IMAGE_LOCATION_RE.search(
            _image_name_stem(str(self.image.name or ""))
        )
        sheet = str(self.sheet_name or self.image.section or "").strip()
        if name_match:
            if not sheet:
                return None
            return (
                sheet.lower(),
                int(name_match.group("row")),
                int(name_match.group("col")),
            )
        if not sheet:
            return None
        return sheet.lower(), int(self.image.row), int(self.image.col)

    @property
    def name_key(self) -> Optional[str]:
        name = str(self.image.name or "").strip().lower()
        ext = str(self.image.ext or "").strip().lower()
        if not name:
            return None
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        return f"{name}{ext}"

    @property
    def chapter_picture_key(self) -> Optional[Tuple[str, str]]:
        name_match = _IMAGE_CHAPTER_RE.search(
            _image_name_stem(str(self.image.name or ""))
        )
        if not name_match:
            return None
        return name_match.group("chapter"), name_match.group("picture")

    @property
    def document_path_key(self) -> Tuple[str, str, str]:
        return (
            str(self.sheet_name or self.image.section or "").strip().lower(),
            str(self.chapter_title or "").strip(),
            str(self.paragraph_title or "").strip(),
        )


def collect_images(document: Document) -> List[ImageRecord]:
    """Collect direct and table-contained images with their logical document path."""
    records: List[ImageRecord] = []

    def add_contents(
        contents: Iterable[Any],
        scope: str,
        sheet_name: Optional[str] = None,
        chapter_title: Optional[str] = None,
        paragraph_title: Optional[str] = None,
    ) -> None:
        for block in contents:
            if isinstance(block, ImageBlock):
                records.append(
                    ImageRecord(
                        block, scope, sheet_name, chapter_title, paragraph_title
                    )
                )
            elif isinstance(block, TableBlock):
                for image in getattr(block, "images", []) or []:
                    if isinstance(image, ImageBlock):
                        records.append(
                            ImageRecord(
                                image, scope, sheet_name, chapter_title, paragraph_title
                            )
                        )

    def add_paragraph(
        paragraph: Paragraph, sheet_name: Optional[str], chapter_title: Optional[str]
    ) -> None:
        add_contents(
            paragraph.contents,
            "paragraph",
            sheet_name,
            chapter_title,
            paragraph.title or None,
        )
        for child in paragraph.paragraphs:
            add_paragraph(child, sheet_name, chapter_title)

    def add_chapter(chapter: Chapter, sheet_name: Optional[str]) -> None:
        add_contents(chapter.contents, "chapter", sheet_name, chapter.title or None)
        for paragraph in chapter.paragraphs:
            add_paragraph(paragraph, sheet_name, chapter.title or None)

    add_contents(document.contents, "document")
    for chapter in document.chapters:
        add_chapter(chapter, None)
    for sheet in document.sheets:
        add_contents(sheet.contents, "sheet", sheet.name)
        for chapter in sheet.chapters:
            add_chapter(chapter, sheet.name)
    return records


def compare_document_images(
    old_document: Document,
    new_document: Document,
    diff_rows: Optional[Iterable[Dict[str, Any]]] = None,
    perceptual: bool = False,
    cloud_side: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare all distinct ImageBlocks with graph_diff_documents pairing semantics.

    ``diff_rows`` is accepted for call-site compatibility but intentionally not
    used: pairing relies on content, logical position, and name keys across all
    images rather than on aligned text-diff rows.

    ``perceptual`` selects how paired images are judged changed vs unchanged:

    - ``False`` (default): exact base64 byte comparison. Use for local-vs-local,
      where both sides are rendered on the same platform and identical shapes
      produce identical bytes.
    ``perceptual`` enables cross-platform local-vs-cloud matching; ``cloud_side``
    identifies the cloud document and position source.
    ``None`` preserves the existing local-vs-local position handling.
    """
    _ = diff_rows
    if cloud_side not in (None, "old", "new"):
        raise ValueError("cloud_side must be None, 'old', or 'new'")
    old_records = _distinct_records(collect_images(old_document))
    new_records = _distinct_records(collect_images(new_document))
    old_index = _build_record_index(old_records)
    new_index = _build_record_index(new_records)
    old_position_from_name = None if cloud_side is None else cloud_side == "old"
    new_position_from_name = None if cloud_side is None else cloud_side == "new"
    old_refs = [
        _record_to_ref(record, position_from_name=old_position_from_name)
        for record in old_records
    ]
    new_refs = [
        _record_to_ref(record, position_from_name=new_position_from_name)
        for record in new_records
    ]
    closest, similar = (
        _build_visual_match_map(old_refs, new_refs) if perceptual else ({}, {})
    )
    pairs = _pair_refs_across_all_images(
        old_refs, new_refs, old_index, new_index, closest, similar
    )
    # Rescue moved pictures (same/similar content, shifted position) that ended up
    # as leftover orphans so they become one pair instead of a spurious add+remove.
    triples = _rescue_moved_pairs(pairs, perceptual=perceptual)

    items: List[Dict[str, Any]] = []
    changed = unchanged = unavailable = moved = 0
    added_ids: set[str] = set()
    removed_ids: set[str] = set()
    for old_ref, new_ref, _rescued in triples:
        old_record = _record_from_ref(old_ref, old_index)
        new_record = _record_from_ref(new_ref, new_index)
        old_id = str(old_record.image.id) if old_record and old_record.image.id else ""
        new_id = str(new_record.image.id) if new_record and new_record.image.id else ""
        if old_record is None and new_record is not None:
            if new_record.image.get_base64_data() is None:
                status = "unavailable"
                unavailable += 1
            else:
                status = "added"
                if new_id:
                    added_ids.add(new_id)
        elif new_record is None and old_record is not None:
            if old_record.image.get_base64_data() is None:
                status = "unavailable"
                unavailable += 1
            else:
                status = "removed"
                if old_id:
                    removed_ids.add(old_id)
        elif old_record is None or new_record is None:
            status = "unavailable"
            unavailable += 1
        else:
            old_data = old_record.image.get_base64_data()
            new_data = new_record.image.get_base64_data()
            content_same = False
            status = "unavailable"
            if old_data is None or new_data is None:
                status = "unavailable"
                unavailable += 1
            elif old_data == new_data:
                content_same = True
            else:
                # Use full-resolution pixels before the perceptual fallback.
                full = _full_resolution_same_content(old_data, new_data)
                if full is True:
                    content_same = True
                elif full is False:
                    status = "changed"
                    changed += 1
                elif perceptual:
                    same = _images_visually_equal(old_data, new_data)
                    if same is None:
                        status = "unavailable"
                        unavailable += 1
                    elif same:
                        content_same = True
                    else:
                        status = "changed"
                        changed += 1
                else:
                    status = "changed"
                    changed += 1
            if content_same:
                # Same picture: distinguish an in-place image from one that moved to
                # a different sheet/row/col, so a shifted-but-identical picture is
                # reported as moved rather than unchanged (and never as add+remove).
                if _position_changed(old_ref, new_ref):
                    status = "moved"
                    moved += 1
                else:
                    status = "unchanged"
                    unchanged += 1
        items.append(_item(status, old_record, new_record, "graph-compatible"))

    items.sort(
        key=lambda item: (
            item["status"],
            item.get("old", {}).get("id", ""),
            item.get("new", {}).get("id", ""),
        )
    )
    return {
        "summary": {
            "old_image_count": len(old_records),
            "new_image_count": len(new_records),
            "matched": changed + unchanged + unavailable + moved,
            "changed": changed,
            "unchanged": unchanged,
            "moved": moved,
            "added": len(added_ids),
            "removed": len(removed_ids),
            "unavailable": unavailable,
        },
        "items": items,
    }


def _distinct_records(records: List[ImageRecord]) -> List[ImageRecord]:
    unique: Dict[str, ImageRecord] = {}
    for record in records:
        image_id = str(record.image.id or "")
        if image_id:
            unique.setdefault(image_id, record)
    return sorted(
        unique.values(),
        key=lambda record: (
            str(record.image.name or ""),
            str(record.image.id or ""),
        ),
    )


def _build_record_index(records: List[ImageRecord]) -> Dict[str, ImageRecord]:
    return {str(record.image.id): record for record in records if record.image.id}


def _record_to_ref(
    record: ImageRecord,
    *,
    position_from_name: Optional[bool] = None,
) -> Dict[str, Any]:
    name = str(record.image.name or "").strip()
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    # Keep dots in sheet names while stripping the image extension.
    ext_match = _IMAGE_NAME_EXT_RE.search(base)
    if ext_match:
        stem = base[: ext_match.start()]
        ext = ext_match.group(0).lower()
    else:
        stem = base
        ext = None
    chapter = _parse_graph_chapter(stem)
    sheet_name = str(record.sheet_name or record.image.section or "").strip().lower()
    record_row = int(record.image.row) if record.image.row is not None else None
    record_col = int(record.image.col) if record.image.col is not None else None
    name_position = _parse_graph_position(stem)
    if position_from_name is True:
        location = _parse_graph_location(stem)
        if name_position is None:
            pos_sheet = pos_row = pos_col = None
        else:
            pos_sheet, pos_row, pos_col = name_position
    elif position_from_name is False:
        pos_sheet = sheet_name or None
        pos_row = record_row
        pos_col = record_col
        location = (
            (pos_sheet, f"{pos_row}:{pos_col}")
            if pos_sheet is not None and pos_row is not None and pos_col is not None
            else None
        )
    else:
        location = _parse_graph_location(stem)
        pos_sheet = sheet_name or None
        pos_row = record_row
        pos_col = record_col
    return {
        "image_id_hint": str(record.image.id or ""),
        "ref_key": f"{stem.lower()}{ext or ''}" if stem else None,
        "data_b64": record.image.get_base64_data(),
        "sheet_key": location[0] if location else None,
        "coordinate_key": location[1] if location else None,
        "chapter_key": chapter[0] if chapter else None,
        "picture_key": chapter[1] if chapter else None,
        # Numeric position used to disambiguate duplicate-content pairing and to
        # decide moved vs unchanged.
        "pos_sheet": pos_sheet,
        "pos_row": pos_row,
        "pos_col": pos_col,
    }


def _parse_graph_position(name: str) -> Optional[Tuple[str, int, int]]:
    match = re.search(
        r"(?:^|_)(?P<sheet>[^_]+)_r(?P<row>\d+)_c(?P<col>\d+)"
        r"(?:_rect_\d+)?$",
        name,
        re.IGNORECASE,
    )
    if not match:
        return None
    return (
        match.group("sheet").lower(),
        int(match.group("row")),
        int(match.group("col")),
    )


def _parse_graph_location(name: str) -> Optional[Tuple[str, str]]:
    position = _parse_graph_position(name)
    if position is None:
        return None
    sheet, row, col = position
    return sheet, f"{row}:{col}"


def _parse_graph_chapter(name: str) -> Optional[Tuple[str, str]]:
    match = _IMAGE_CHAPTER_RE.search(name)
    if not match:
        return None
    return match.group("chapter"), match.group("picture")


def _record_from_ref(
    ref: Optional[Dict[str, Any]], index: Dict[str, ImageRecord]
) -> Optional[ImageRecord]:
    if not ref:
        return None
    return index.get(str(ref.get("image_id_hint") or ""))


def _pair_refs_across_all_images(
    old_refs: List[Dict[str, Any]],
    new_refs: List[Dict[str, Any]],
    old_index: Dict[str, ImageRecord],
    new_index: Dict[str, ImageRecord],
    visual_closest: Optional[Dict[str, str]] = None,
    visual_similar: Optional[Dict[str, set]] = None,
) -> List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]:
    pairs, old_unmatched, new_unmatched = _pair_refs(old_refs, new_refs, visual_closest)
    used_new_ids = {
        str(new_ref.get("image_id_hint"))
        for _, new_ref in pairs
        if new_ref and new_ref.get("image_id_hint")
    }
    # Byte-identical leftovers: pair them cluster-by-cluster in layout order so a
    # picture that only shifted position pairs with its true counterpart instead
    # of being stranded as add/remove.
    remaining_pairs, used_new_ids = _pair_same_content_by_layout(
        old_unmatched, new_unmatched, used_new_ids
    )

    # Visual-similarity fallback (perceptual/local-vs-cloud only): rescue leftover
    # look-alikes that are not byte-identical by claiming a still-free new orphan.
    if visual_similar:
        rescued: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
        for old_ref, new_ref in remaining_pairs:
            if old_ref is not None and new_ref is None:
                look_alike = visual_similar.get(
                    str(old_ref.get("image_id_hint")), set()
                )
                match = next(
                    (
                        ref
                        for ref in new_unmatched
                        if str(ref.get("image_id_hint")) in look_alike
                        and str(ref.get("image_id_hint")) not in used_new_ids
                    ),
                    None,
                )
                if match is not None:
                    used_new_ids.add(str(match.get("image_id_hint")))
                    rescued.append((old_ref, match))
                    continue
            rescued.append((old_ref, new_ref))
        # Drop new orphans that were just claimed as a visual match.
        remaining_pairs = [
            (old_ref, new_ref)
            for old_ref, new_ref in rescued
            if not (
                old_ref is None
                and new_ref is not None
                and str(new_ref.get("image_id_hint")) in used_new_ids
                and any(o is not None and n is new_ref for o, n in rescued)
            )
        ]
    return pairs + remaining_pairs


def _layout_sort_key(ref: Dict[str, Any]) -> Tuple[str, int, int]:
    """Stable document-order key: sheet, then column, then row.

    Column before row keeps the two columns of a paired figure (c24/c25) in
    separate ordered runs, so equal-content images pair with the matching column
    across versions instead of interleaving.
    """
    sheet = str(ref.get("pos_sheet") or "")
    col = ref.get("pos_col")
    row = ref.get("pos_row")
    return (
        sheet,
        col if isinstance(col, int) else 10**9,
        row if isinstance(row, int) else 10**9,
    )


def _pair_same_content_by_layout(
    old_unmatched: List[Dict[str, Any]],
    new_unmatched: List[Dict[str, Any]],
    used_new_ids: set,
) -> Tuple[List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]], set]:
    """Pair leftover byte-identical images cluster by cluster in layout order.

    Duplicate content makes any single old->new choice ambiguous, so instead of a
    greedy or nearest pick (which can steal one cluster member's true partner and
    strand another as add/remove), this groups both sides by content hash and, per
    cluster, sorts each side by sheet/col/row and zips them. Inserting rows shifts
    absolute rows but preserves each side's relative order, so the k-th old image
    pairs with the k-th new image of the same content. Leftovers when the counts
    differ become genuine orphans (real add/remove).
    """
    old_by_content: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ref in old_unmatched:
        if ref.get("data_b64"):
            old_by_content[ref["data_b64"]].append(ref)
    new_by_content: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ref in new_unmatched:
        key = ref.get("data_b64")
        if key and str(ref.get("image_id_hint")) not in used_new_ids:
            new_by_content[key].append(ref)

    out: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []
    paired_old_ids: set = set()
    for content, old_group in old_by_content.items():
        new_group = new_by_content.get(content, [])
        old_sorted = sorted(old_group, key=_layout_sort_key)
        new_sorted = sorted(new_group, key=_layout_sort_key)
        for index, old_ref in enumerate(old_sorted):
            if index < len(new_sorted):
                new_ref = new_sorted[index]
                used_new_ids.add(str(new_ref.get("image_id_hint")))
                paired_old_ids.add(str(old_ref.get("image_id_hint")))
                out.append((old_ref, new_ref))
            else:
                out.append((old_ref, None))

    # old refs never paired above (e.g. no content) become orphans.
    for ref in old_unmatched:
        if str(ref.get("image_id_hint")) not in paired_old_ids and not ref.get(
            "data_b64"
        ):
            out.append((ref, None))
    # Any new ref never claimed becomes an orphan.
    for ref in new_unmatched:
        if str(ref.get("image_id_hint")) not in used_new_ids:
            out.append((None, ref))
    return out, used_new_ids


def _position_changed(
    old_ref: Optional[Dict[str, Any]], new_ref: Optional[Dict[str, Any]]
) -> bool:
    """True if the two refs sit at different sheet/row/col document positions.

    Used to split identical-content pairs into ``moved`` vs ``unchanged``. When
    position data is missing on either side, treat it as unchanged (do not invent
    a move).
    """
    if not old_ref or not new_ref:
        return False
    for key in ("pos_sheet", "pos_row", "pos_col"):
        old_value, new_value = old_ref.get(key), new_ref.get(key)
        if old_value is None or new_value is None:
            return False
    return (
        old_ref.get("pos_sheet") != new_ref.get("pos_sheet")
        or old_ref.get("pos_row") != new_ref.get("pos_row")
        or old_ref.get("pos_col") != new_ref.get("pos_col")
    )


def _pair_refs(
    old_refs: List[Dict[str, Any]],
    new_refs: List[Dict[str, Any]],
    visual_closest: Optional[Dict[str, str]] = None,
) -> Tuple[
    List[Tuple[Dict[str, Any], Dict[str, Any]]],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    # Stage 1: pair byte-identical images globally, cluster by content, in layout
    # order. This runs BEFORE positional keys so a picture that only shifted rows
    # pairs with its identical counterpart instead of colliding on coordinate_key
    # with a different picture that happens to now occupy the old row (which used
    # to be mis-reported as changed on one row plus add/remove on the moved row).
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    old_by_content: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ref in old_refs:
        if ref.get("data_b64"):
            old_by_content[ref["data_b64"]].append(ref)
    new_by_content: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ref in new_refs:
        if ref.get("data_b64"):
            new_by_content[ref["data_b64"]].append(ref)
    paired_old: set = set()
    paired_new: set = set()
    for content, old_group in old_by_content.items():
        new_group = new_by_content.get(content)
        if not new_group:
            continue
        old_sorted = sorted(old_group, key=_layout_sort_key)
        new_sorted = sorted(new_group, key=_layout_sort_key)
        for index, old_ref in enumerate(old_sorted):
            if index >= len(new_sorted):
                break
            new_ref = new_sorted[index]
            pairs.append((old_ref, new_ref))
            paired_old.add(id(old_ref))
            paired_new.add(id(new_ref))

    remaining_old_refs = [ref for ref in old_refs if id(ref) not in paired_old]
    remaining_new = [ref for ref in new_refs if id(ref) not in paired_new]
    deferred_old: List[Dict[str, Any]] = []

    def unique_match(old_ref: Dict[str, Any], predicate: Any) -> Optional[int]:
        candidates = [
            index
            for index, new_ref in enumerate(remaining_new)
            if predicate(old_ref, new_ref)
        ]
        return candidates[0] if len(candidates) == 1 else None

    def same_content(old: Dict[str, Any], new: Dict[str, Any]) -> bool:
        if (
            old.get("data_b64")
            and new.get("data_b64")
            and old["data_b64"] == new["data_b64"]
        ):
            return True
        if not visual_closest:
            return False
        return visual_closest.get(str(old.get("image_id_hint"))) == str(
            new.get("image_id_hint")
        )

    # Stage 2: positional / name keys for the pictures whose content actually
    # changed (no identical twin remained) plus visual-similarity content.
    for old_ref in remaining_old_refs:
        match_index = None
        if old_ref.get("data_b64"):
            match_index = unique_match(
                old_ref,
                lambda old, new: (
                    same_content(old, new)
                    and (
                        not old.get("sheet_key")
                        or not new.get("sheet_key")
                        or old.get("sheet_key") == new.get("sheet_key")
                    )
                ),
            )
        for key_left, key_right in (
            ("coordinate_key", "sheet_key"),
            ("picture_key", "chapter_key"),
            ("ref_key", None),
        ):
            if match_index is not None:
                break
            if key_right is None:
                match_index = unique_match(
                    old_ref,
                    lambda old, new: (
                        bool(old.get("ref_key"))
                        and old.get("ref_key") == new.get("ref_key")
                    ),
                )
            else:
                match_index = unique_match(
                    old_ref,
                    lambda old, new: (
                        old.get(key_right) == new.get(key_right)
                        and bool(old.get(key_left))
                        and old.get(key_left) == new.get(key_left)
                    ),
                )
        if match_index is None:
            deferred_old.append(old_ref)
        else:
            pairs.append((old_ref, remaining_new.pop(match_index)))

    fallback_old = [
        ref
        for ref in deferred_old
        if not any(
            ref.get(key)
            for key in ("sheet_key", "coordinate_key", "chapter_key", "picture_key")
        )
    ]
    fallback_new = [
        ref
        for ref in remaining_new
        if not any(
            ref.get(key)
            for key in ("sheet_key", "coordinate_key", "chapter_key", "picture_key")
        )
    ]
    unmatched_old = [ref for ref in deferred_old if ref not in fallback_old]
    unmatched_new = [ref for ref in remaining_new if ref not in fallback_new]
    pairs.extend(zip(fallback_old, fallback_new))
    unmatched_old.extend(fallback_old[len(fallback_new) :])
    unmatched_new.extend(fallback_new[len(fallback_old) :])
    return pairs, unmatched_old, unmatched_new


def _rescue_moved_pairs(
    pairs: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]],
    perceptual: bool = False,
    visual_max_mean_diff: float = _PERCEPTUAL_MAX_MEAN_DIFF,
) -> List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]]:
    """Re-pair orphaned old/new images whose content is identical (or, when
    ``perceptual``, visually identical) but whose position moved.

    Positional pairing keys on sheet/row/col, so a picture that shifts to another
    row (a row was inserted above it) misses every key and is reported as removed
    on the old side AND added on the new side. This stage runs after all normal
    pairing: it takes the leftover ``(old, None)`` and ``(None, new)`` orphans and
    matches an old orphan to a new orphan with the same bytes (perceptual: same
    look), so a moved picture becomes one ``moved`` pair instead of a spurious
    add+remove. Duplicate-content orphans are paired greedily in encounter order,
    which is stable and never invents a match the content does not support.

    Returns triples ``(old_ref, new_ref, moved)`` where ``moved`` is True only for
    pairs created here; existing pairs are passed through with ``moved=False``.
    """
    kept: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]] = []
    old_orphans: List[Dict[str, Any]] = []
    new_orphans: List[Dict[str, Any]] = []
    for old_ref, new_ref in pairs:
        if old_ref is not None and new_ref is None:
            old_orphans.append(old_ref)
        elif old_ref is None and new_ref is not None:
            new_orphans.append(new_ref)
        else:
            kept.append((old_ref, new_ref, False))

    # First pass: exact byte content. new orphans grouped by content for O(1) claim.
    new_by_content: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ref in new_orphans:
        if ref.get("data_b64"):
            new_by_content[ref["data_b64"]].append(ref)
    claimed_new: set[int] = set()
    remaining_old: List[Dict[str, Any]] = []
    for old_ref in old_orphans:
        bucket = new_by_content.get(old_ref.get("data_b64") or "", [])
        match = next((ref for ref in bucket if id(ref) not in claimed_new), None)
        if match is None:
            remaining_old.append(old_ref)
        else:
            claimed_new.add(id(match))
            kept.append((old_ref, match, True))

    leftover_new = [ref for ref in new_orphans if id(ref) not in claimed_new]

    # Second pass (perceptual only): visually-identical content that differs byte
    # for byte across render platforms.
    if perceptual and remaining_old and leftover_new:
        still_old: List[Dict[str, Any]] = []
        for old_ref in remaining_old:
            match = None
            for ref in leftover_new:
                if id(ref) in claimed_new:
                    continue
                same = _images_visually_equal(
                    old_ref.get("data_b64"), ref.get("data_b64"), visual_max_mean_diff
                )
                if same:
                    match = ref
                    break
            if match is None:
                still_old.append(old_ref)
            else:
                claimed_new.add(id(match))
                kept.append((old_ref, match, True))
        remaining_old = still_old
        leftover_new = [ref for ref in leftover_new if id(ref) not in claimed_new]

    for old_ref in remaining_old:
        kept.append((old_ref, None, False))
    for new_ref in leftover_new:
        kept.append((None, new_ref, False))
    return kept


def _item(
    status: str,
    old_record: Optional[ImageRecord],
    new_record: Optional[ImageRecord],
    matched_by: Optional[str],
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "status": status,
        "old": _record_to_dict(old_record),
        "new": _record_to_dict(new_record),
    }
    if matched_by:
        item["matched_by"] = matched_by
    return item


def _record_to_dict(record: Optional[ImageRecord]) -> Dict[str, Any]:
    if record is None:
        return {}
    image = record.image
    return {
        "id": image.id,
        "name": image.name,
        "ext": image.ext,
        "section": image.section,
        "row": image.row,
        "col": image.col,
        "scope": record.scope,
        "sheet_name": record.sheet_name,
        "chapter_title": record.chapter_title,
        "paragraph_title": record.paragraph_title,
    }
