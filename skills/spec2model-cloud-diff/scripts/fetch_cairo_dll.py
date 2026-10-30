#!/usr/bin/env python3
"""Fetch the Cairo runtime DLLs (Windows) needed by cairocffi / CairoSVG.

``spec2model`` imports ``cairosvg`` unconditionally, which loads ``cairocffi``,
which in turn needs the native ``libcairo-2.dll`` and its dependency DLLs. On
Windows those native libraries are not provided by pip, so ``import spec2model``
fails with ``OSError: no library called "cairo-2" was found`` unless the DLLs
are made available.

This script downloads the required packages from conda-forge (win-64), extracts
their ``Library/bin/*.dll`` files into a target directory (default
``.venv/cairo_dll``), and creates a ``libcairo-2.dll`` alias (a copy of
``cairo.dll``) because that is one of the file names cairocffi tries.

No conda installation is required: only the package archives are downloaded and
unpacked. Nothing is installed system-wide.

Usage (from ``tools/spec2model``)::

    .venv\\Scripts\\python.exe fetch_cairo_dll.py .venv\\cairo_dll

After running, set the following before importing spec2model / running a diff
(PowerShell), because cairocffi resolves dependency DLLs via PATH::

    $env:PATH = (Resolve-Path ".venv\\cairo_dll").Path + ";" + $env:PATH
    $env:CAIROCFFI_DLL_DIRECTORIES = (Resolve-Path ".venv\\cairo_dll").Path

This script is only needed on Windows. On Linux/macOS install Cairo via the
system package manager (e.g. ``apt-get install libcairo2`` / ``brew install cairo``).
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

CHANNEL = "https://conda.anaconda.org/conda-forge/win-64"

# Packages that together provide libcairo-2.dll and its transitive DLL deps.
# conda-forge moved several runtime DLLs into ``lib*``/``lib*6`` packages, so the
# names below are chosen to actually contain the .dll files (verified):
#   - libfreetype6 provides freetype.dll (plain ``freetype`` only ships the .lib)
#   - libffi provides ffi-8.dll (required by gobject-2.0-0.dll)
#   - libharfbuzz provides harfbuzz*.dll
PACKAGES = [
    "cairo",
    "libpng",
    "libzlib",
    "pixman",
    "libfreetype6",
    "fontconfig",
    "libexpat",
    "bzip2",
    "libglib",
    "pcre2",
    "libintl",
    "libiconv",
    "getopt-win32",
    "graphite2",
    "libharfbuzz",
    "icu",
    "libffi",
]

DEFAULT_DEST = Path(".venv/cairo_dll")


def _repodata() -> dict:
    # current_repodata.json only lists the latest build per package -> smaller.
    url = f"{CHANNEL}/current_repodata.json"
    print(f"downloading repodata: {url}", flush=True)
    with urllib.request.urlopen(url, timeout=180) as response:
        data = response.read()
    return json.loads(data.decode("utf-8"))


def _latest_filename(repodata: dict, name: str) -> str | None:
    best: tuple[tuple[int, str], str] | None = None
    for section in ("packages.conda", "packages"):
        for filename, meta in repodata.get(section, {}).items():
            if meta.get("name") == name:
                key = (meta.get("timestamp", 0), filename)
                if best is None or key > best[0]:
                    best = (key, filename)
    return best[1] if best else None


def _ensure_zstandard():
    try:
        import zstandard  # noqa: F401
    except ImportError:
        print(
            "  installing zstandard (needed to unpack .conda archives)...", flush=True
        )
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "zstandard"]
        )


def _copy_dlls_from_tar(tar: tarfile.TarFile, dest: Path) -> int:
    count = 0
    for member in tar.getmembers():
        low = member.name.lower()
        if low.endswith(".dll") and ("/bin/" in low or low.startswith("library/bin")):
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            out = dest / Path(member.name).name
            out.write_bytes(extracted.read())
            print(f"  extracted {out.name}", flush=True)
            count += 1
    return count


def _extract_dlls(archive: bytes, filename: str, dest: Path) -> int:
    if filename.endswith(".conda"):
        # .conda is a zip containing pkg-*.tar.zst
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            inner = [
                n
                for n in zf.namelist()
                if n.startswith("pkg-") and n.endswith(".tar.zst")
            ]
            if not inner:
                return 0
            payload = zf.read(inner[0])
        _ensure_zstandard()
        import zstandard

        raw = zstandard.ZstdDecompressor().decompress(payload, max_output_size=1 << 30)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            return _copy_dlls_from_tar(tar, dest)
    if filename.endswith(".tar.bz2"):
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:bz2") as tar:
            return _copy_dlls_from_tar(tar, dest)
    return 0


def main() -> int:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST
    dest.mkdir(parents=True, exist_ok=True)

    repodata = _repodata()
    total = 0
    for pkg in PACKAGES:
        filename = _latest_filename(repodata, pkg)
        if not filename:
            print(f"[skip] {pkg}: not found in repodata", flush=True)
            continue
        url = f"{CHANNEL}/{filename}"
        print(f"downloading {pkg}: {filename}", flush=True)
        try:
            with urllib.request.urlopen(url, timeout=180) as response:
                archive = response.read()
            total += _extract_dlls(archive, filename, dest)
        except Exception as error:  # noqa: BLE001
            print(f"[warn] {pkg}: {error}", flush=True)

    cairo_dll = dest / "cairo.dll"
    alias = dest / "libcairo-2.dll"
    if cairo_dll.exists():
        alias.write_bytes(cairo_dll.read_bytes())
        print(f"  created alias {alias.name} (copy of cairo.dll)", flush=True)

    print(f"DONE: extracted {total} DLLs into {dest}", flush=True)
    ok = alias.exists()
    print("libcairo-2.dll present:", ok, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
