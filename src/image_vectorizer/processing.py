"""
processing.py — Image cleaning, text detection, and debug composite utilities.

All public functions accept a `params` dict (see config.default_params()) so
callers — including the notebook UI — can supply custom values without mutating
the global config module.
"""

from pathlib import Path

import cv2
import numpy as np


def load_image(path: Path | str) -> np.ndarray:
    """Load an image from disk as a BGR(A) numpy array."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img


def clean_image(
    img: np.ndarray,
    params: dict,
    debug_frames: list | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Produce a binary line mask and an RGBA image from a diagram image.

    Pipeline:
      grayscale → [upscale] → [blur] → [CLAHE] → threshold → [morph] → [skeletonize]

    Parameters
    ----------
    img          : BGR(A) or grayscale numpy array from load_image()
    params       : processing parameters dict (see config.default_params())
    debug_frames : if a list is passed, intermediate stages are appended as
                   (label, array) tuples so the caller can build a debug composite.

    Returns
    -------
    binary : uint8 ndarray — 255=line, 0=background; may be upscaled.
    rgba   : HxWx4 uint8 ndarray — black lines on a transparent background.
    """
    # Flatten to BGR regardless of input channels
    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        bgr = img[:, :, :3]
    else:
        bgr = img.copy()

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    upscale = params.get("upscale_factor", 1)
    if upscale > 1:
        h, w = gray.shape
        gray = cv2.resize(
            gray, (w * upscale, h * upscale), interpolation=cv2.INTER_CUBIC
        )

    blur = params.get("median_blur", 0)
    if blur > 1:
        gray = cv2.medianBlur(gray, blur | 1)

    if debug_frames is not None:
        debug_frames.append(("Gray", gray.copy()))

    if params.get("use_clahe", False):
        clahe = cv2.createCLAHE(
            clipLimit=params.get("clahe_clip_limit", 2.0),
            tileGridSize=(params.get("clahe_tile_size", 8),) * 2,
        )
        gray = clahe.apply(gray)
        if debug_frames is not None:
            debug_frames.append(("CLAHE", gray.copy()))

    thresh_type = (
        cv2.THRESH_BINARY_INV if params.get("invert", True) else cv2.THRESH_BINARY
    )

    if params.get("use_adaptive_threshold", False):
        block  = params.get("adaptive_block_size", 25) | 1
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresh_type,
            block,
            params.get("adaptive_c", 10),
        )
    elif params.get("use_otsu", True):
        _, binary = cv2.threshold(gray, 0, 255, thresh_type | cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(
            gray, params.get("threshold", 240), 255, thresh_type
        )

    if debug_frames is not None:
        debug_frames.append(("Threshold", binary.copy()))

    noise_k = params.get("noise_kernel", 0)
    if noise_k > 0:
        k      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (noise_k, noise_k))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)

    speckle_k = params.get("speckle_kernel", 0)
    if speckle_k > 0:
        k      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (speckle_k, speckle_k))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)

    if debug_frames is not None and (noise_k > 0 or speckle_k > 0):
        debug_frames.append(("Cleaned", binary.copy()))

    if params.get("skeletonize", False):
        binary = _skeletonize(binary)
        if debug_frames is not None:
            debug_frames.append(("Skeleton", binary.copy()))

    rgba = np.zeros((*binary.shape, 4), dtype=np.uint8)
    rgba[binary == 255] = [0, 0, 0, 255]
    rgba[binary == 0]   = [255, 255, 255, 0]

    return binary, rgba


def detect_text_regions(binary: np.ndarray, params: dict) -> list[dict]:
    """
    Heuristically locate text label bounding boxes via connected-component analysis.

    Filters components by area and aspect ratio to isolate characters such as
    "L1", "L2", "L3" while ignoring diagram geometry.

    Returns a list of dicts: {x, y, w, h, area}.
    """
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    min_area   = params.get("text_min_area", 30)
    max_area   = params.get("text_max_area", 8000)
    aspect_min = params.get("text_aspect_min", 0.15)
    aspect_max = params.get("text_aspect_max", 10.0)

    boxes = []
    for i in range(1, num_labels):
        x    = int(stats[i, cv2.CC_STAT_LEFT])
        y    = int(stats[i, cv2.CC_STAT_TOP])
        w    = int(stats[i, cv2.CC_STAT_WIDTH])
        h    = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])

        if not (min_area <= area <= max_area):
            continue
        aspect = w / max(h, 1)
        if not (aspect_min <= aspect <= aspect_max):
            continue
        # Exclude near-square blobs — likely diagram symbols, not text characters
        if 0.85 <= aspect <= 1.15 and area > 300:
            continue

        boxes.append({"x": x, "y": y, "w": w, "h": h, "area": area})

    return boxes


def draw_text_boxes(rgba: np.ndarray, boxes: list[dict]) -> np.ndarray:
    """Return a copy of an RGBA image with detected text boxes drawn in red."""
    vis = rgba.copy()
    for b in boxes:
        cv2.rectangle(
            vis, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]),
            (0, 0, 255, 200), 1,
        )
    return vis


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _skeletonize(binary: np.ndarray) -> np.ndarray:
    """Thin all strokes to single-pixel width using the Zhang-Suen algorithm."""
    try:
        return cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    except AttributeError:
        pass
    try:
        from skimage.morphology import skeletonize as _sk
        return (_sk(binary > 0) * 255).astype(np.uint8)
    except ImportError:
        print("  [skeletonize] Requires opencv-contrib-python or scikit-image — skipping.")
        return binary