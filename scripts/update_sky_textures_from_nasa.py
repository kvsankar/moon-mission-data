#!/usr/bin/env python3
"""
Download NASA SVS 4851 sky assets and generate runtime textures.

Outputs:
  - images/sky/starmap_2020_4k_stars.jpg
  - images/sky/constellation_figures_2020_4k.jpg

The starmap EXR is HDR linear-light. We apply a power stretch and scale
factor before quantizing to 8-bit RGB to keep faint structure visible while
avoiding blown highlights.

Dependencies:
  pip install OpenEXR Imath numpy pillow
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

import Imath
import numpy as np
import OpenEXR
from PIL import Image


NASA_BASE = "https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851"
STARMAP_EXR = "starmap_2020_4k.exr"
CONSTELLATION_FIGURES_TIF = "constellation_figures_4k.tif"

OUT_STARMAP = "starmap_2020_4k_stars.jpg"
OUT_CONSTELLATION = "constellation_figures_2020_4k.jpg"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def load_exr_rgb(path: Path) -> np.ndarray:
    exr = OpenEXR.InputFile(str(path))
    header = exr.header()
    data_window = header["dataWindow"]
    width = data_window.max.x - data_window.min.x + 1
    height = data_window.max.y - data_window.min.y + 1

    pixel_type = Imath.PixelType(Imath.PixelType.FLOAT)
    channels = [
        np.frombuffer(exr.channel(channel_name, pixel_type), dtype=np.float32)
        for channel_name in ("R", "G", "B")
    ]
    stacked = np.stack(channels, axis=-1)
    return stacked.reshape((height, width, 3))


def write_starmap_jpg(
    source_exr: Path,
    destination_jpg: Path,
    power: float,
    scale: float,
) -> None:
    rgb = load_exr_rgb(source_exr)
    stretched = np.power(np.clip(rgb, 0.0, None), power) * scale
    srgb = np.clip(stretched, 0.0, 1.0)
    out = (srgb * 255.0).round().astype(np.uint8)
    Image.fromarray(out).save(destination_jpg, quality=92, optimize=True)


def write_constellation_jpg(source_tif: Path, destination_jpg: Path) -> None:
    image = Image.open(source_tif).convert("RGB")
    image.save(destination_jpg, quality=92, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        default=".",
        help="moon-mission-data repository root",
    )
    parser.add_argument(
        "--power",
        type=float,
        default=0.55,
        help="Power curve exponent for starmap tone stretch",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.68,
        help="Linear multiplier after power stretch",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    out_dir = data_root / "images" / "sky"
    out_dir.mkdir(parents=True, exist_ok=True)

    starmap_out = out_dir / OUT_STARMAP
    constellation_out = out_dir / OUT_CONSTELLATION

    with tempfile.TemporaryDirectory(prefix="nasa-sky-") as tmp:
        tmp_dir = Path(tmp)
        starmap_exr = tmp_dir / STARMAP_EXR
        constellation_tif = tmp_dir / CONSTELLATION_FIGURES_TIF

        starmap_url = f"{NASA_BASE}/{STARMAP_EXR}"
        constellation_url = f"{NASA_BASE}/{CONSTELLATION_FIGURES_TIF}"

        print(f"Downloading {starmap_url}")
        download(starmap_url, starmap_exr)
        print(f"Downloading {constellation_url}")
        download(constellation_url, constellation_tif)

        write_starmap_jpg(starmap_exr, starmap_out, args.power, args.scale)
        write_constellation_jpg(constellation_tif, constellation_out)

        summary = {
            "sources": {
                STARMAP_EXR: {
                    "url": starmap_url,
                    "sha256": sha256(starmap_exr),
                },
                CONSTELLATION_FIGURES_TIF: {
                    "url": constellation_url,
                    "sha256": sha256(constellation_tif),
                },
            },
            "outputs": {
                OUT_STARMAP: {
                    "path": str(starmap_out.relative_to(data_root).as_posix()),
                    "sha256": sha256(starmap_out),
                },
                OUT_CONSTELLATION: {
                    "path": str(constellation_out.relative_to(data_root).as_posix()),
                    "sha256": sha256(constellation_out),
                },
            },
            "transform": {
                "starmap_power": args.power,
                "starmap_scale": args.scale,
                "constellation": "TIFF to JPEG",
            },
        }
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
