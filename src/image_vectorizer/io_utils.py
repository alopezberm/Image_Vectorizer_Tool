"""
io_utils.py — File saving, output path helpers, and debug composite builder.
"""

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def make_output_paths(stem: str, output_dir: Path) -> dict[str, Path]:
    """Return the standard output file paths for a given input file stem."""
    return {
        "png":   output_dir / f"{stem}_clean.png",
        "svg":   output_dir / f"{stem}.svg",
        "json":  output_dir / f"{stem}_text.json",
        "debug": output_dir / f"{stem}_debug.png",
    }


def save_clean_png(rgba: np.ndarray, path: Path) -> None:
    """Save an RGBA array as a transparent-background PNG."""
    Image.fromarray(rgba, "RGBA").save(str(path))


def save_text_json(boxes: list[dict], path: Path) -> None:
    """Save text region bounding boxes to a JSON file."""
    path.write_text(json.dumps(boxes, indent=2), encoding="utf-8")


def save_debug_composite(
    frames: list[tuple[str, np.ndarray]],
    out_path: Path,
    panel_height: int = 320,
) -> None:
    """
    Build a horizontal contact sheet from (label, image) pairs and save it.

    Each panel is rescaled to panel_height with a label bar on top.
    Input arrays may be grayscale (2D), BGR (3-channel), or RGBA (4-channel).
    """
    LABEL_H = 22
    panels  = []

    for label, arr in frames:
        if arr.ndim == 2:
            disp = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        elif arr.shape[2] == 4:
            white = np.full((*arr.shape[:2], 3), 255, dtype=np.uint8)
            alpha = arr[:, :, 3:4] / 255.0
            disp  = (arr[:, :, :3] * alpha + white * (1 - alpha)).astype(np.uint8)
        else:
            disp = arr.copy()

        h, w  = disp.shape[:2]
        scale = panel_height / max(h, 1)
        disp  = cv2.resize(
            disp, (max(1, int(w * scale)), panel_height), interpolation=cv2.INTER_AREA
        )

        bar = np.full((LABEL_H, disp.shape[1], 3), 30, dtype=np.uint8)
        cv2.putText(
            bar, label, (4, LABEL_H - 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (210, 210, 210), 1, cv2.LINE_AA,
        )
        panels.append(np.vstack([bar, disp]))

    cv2.imwrite(str(out_path), np.hstack(panels))