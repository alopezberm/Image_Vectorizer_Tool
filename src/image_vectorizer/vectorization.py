"""
vectorization.py — SVG output via potrace (CLI) or vtracer (pip).

Priority: potrace (best path quality) → vtracer (no external binary needed).
Both engines accept an upscale_factor param and correct SVG dimensions accordingly.
"""

import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def vectorize_to_svg(binary: np.ndarray, svg_path: Path, params: dict) -> str:
    """
    Vectorize a binary mask to SVG using the best available engine.

    Returns the engine name ("potrace" or "vtracer").
    Raises RuntimeError if neither engine is installed.
    """
    if _vectorize_potrace(binary, svg_path, params):
        return "potrace"
    if _vectorize_vtracer(binary, svg_path, params):
        return "vtracer"
    raise RuntimeError(
        "No vectorization engine found.\n"
        "  Option A (recommended): Install potrace\n"
        "    Windows : choco install potrace\n"
        "    macOS   : brew install potrace\n"
        "    Linux   : sudo apt install potrace\n"
        "  Option B: pip install vtracer"
    )


# ---------------------------------------------------------------------------
# Potrace
# ---------------------------------------------------------------------------

def _vectorize_potrace(binary: np.ndarray, svg_path: Path, params: dict) -> bool:
    potrace_bin = shutil.which("potrace")
    if potrace_bin is None:
        return False

    pbm_path = svg_path.with_suffix(".pbm")
    try:
        _save_pbm(binary, pbm_path)
        upscale = params.get("upscale_factor", 1)
        cmd = [
            potrace_bin, str(pbm_path),
            "--svg",
            "--output",       str(svg_path),
            "--turdsize",     str(params.get("potrace_turdsize", 2)),
            "--alphamax",     str(params.get("potrace_alphamax", 0.0)),
            "--opttolerance", str(params.get("potrace_opttolerance", 0.1)),
            "--resolution",   str(72 * upscale),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    [potrace] {result.stderr.strip()}")
            return False
        return True
    except Exception as exc:
        print(f"    [potrace] unexpected error: {exc}")
        return False
    finally:
        if pbm_path.exists():
            pbm_path.unlink()


def _save_pbm(binary: np.ndarray, path: Path) -> None:
    """Save a binary mask as PBM (potrace's native input format)."""
    Image.fromarray(binary).convert("1").save(str(path))


# ---------------------------------------------------------------------------
# vtracer
# ---------------------------------------------------------------------------

def _vectorize_vtracer(binary: np.ndarray, svg_path: Path, params: dict) -> bool:
    try:
        import vtracer  # noqa: PLC0415
    except ImportError:
        return False

    tmp_png = svg_path.with_suffix(".tmp.png")
    try:
        # vtracer reads image files; write a white-bg / black-lines PNG
        cv2.imwrite(str(tmp_png), cv2.bitwise_not(binary))
        vtracer.convert_image_to_svg_py(
            str(tmp_png),
            str(svg_path),
            colormode="binary",
            hierarchical="stacked",
            filter_speckle=params.get("vtracer_filter_speckle", 2),
            color_precision=params.get("vtracer_color_precision", 6),
            corner_threshold=params.get("vtracer_corner_threshold", 60),
            length_threshold=params.get("vtracer_segment_length", 3.0),
            splice_threshold=params.get("vtracer_splice_threshold", 45),
            path_precision=8,
        )
        upscale = params.get("upscale_factor", 1)
        if upscale > 1:
            _fix_svg_scale(svg_path, upscale)
        return True
    except Exception as exc:
        print(f"    [vtracer] {exc}")
        return False
    finally:
        if tmp_png.exists():
            tmp_png.unlink()


def _fix_svg_scale(svg_path: Path, factor: float) -> None:
    """
    Divide the SVG root width and height by factor to restore the original
    physical dimensions after vectorizing an upscaled bitmap.
    """
    text = svg_path.read_text(encoding="utf-8")

    def _scale(m: re.Match) -> str:
        attr, val, unit = m.group(1), float(m.group(2)), m.group(3) or ""
        return f'{attr}="{val / factor:.4f}{unit}"'

    text = re.sub(r'(width)="([\d.]+)([a-z%]*)"',  _scale, text, count=1)
    text = re.sub(r'(height)="([\d.]+)([a-z%]*)"', _scale, text, count=1)
    svg_path.write_text(text, encoding="utf-8")