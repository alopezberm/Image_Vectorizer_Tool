"""
vectorizer.py — Batch raster-to-SVG pipeline for technical diagrams.

Pipeline per image:
  load → clean (grayscale + threshold + denoise) → transparent PNG
       → vectorize (potrace or vtracer) → SVG
       → (optional) detect text regions → JSON annotation

Usage:
  python vectorizer.py
  python vectorizer.py --input my_images --output results
  python vectorizer.py --debug
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import config


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

def load_image(path: Path) -> np.ndarray:
    """Load image from disk as a BGR(A) numpy array."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img


# ---------------------------------------------------------------------------
# Image cleaning
# ---------------------------------------------------------------------------

def clean_image(
    img: np.ndarray,
    debug_frames: list | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Produce a binary line mask and an RGBA image from a diagram image.

    Pipeline:
      grayscale → [upscale] → [blur] → [CLAHE] → threshold → [morph] → [skeletonize]

    Parameters
    ----------
    img          : BGR(A) or grayscale numpy array from load_image()
    debug_frames : if a list is passed, intermediate stages are appended as
                   (label, array) tuples so the caller can build a debug composite.

    Returns
    -------
    binary : np.ndarray (uint8)   255=line, 0=background; may be upscaled.
    rgba   : np.ndarray (uint8)   HxWx4, black lines on transparent background.
    """
    # Flatten to BGR regardless of source depth/channels
    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        bgr = img[:, :, :3]
    else:
        bgr = img.copy()

    # 1. Grayscale
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # 2. Upscale — cubic keeps anti-aliased edges intact better than bilinear.
    #    Gives the tracer more pixels to work with on thin 1–3px lines.
    if config.UPSCALE_FACTOR > 1:
        h, w = gray.shape
        gray = cv2.resize(
            gray,
            (w * config.UPSCALE_FACTOR, h * config.UPSCALE_FACTOR),
            interpolation=cv2.INTER_CUBIC,
        )

    # 3. Median blur — only useful for JPEG compression artifacts.
    if config.MEDIAN_BLUR > 1:
        ksize = config.MEDIAN_BLUR | 1  # ensure odd
        gray = cv2.medianBlur(gray, ksize)

    if debug_frames is not None:
        debug_frames.append(("Gray", gray.copy()))

    # 4. CLAHE — lifts local contrast for unevenly lit or faded scans.
    if config.USE_CLAHE:
        clahe = cv2.createCLAHE(
            clipLimit=config.CLAHE_CLIP_LIMIT,
            tileGridSize=(config.CLAHE_TILE_SIZE, config.CLAHE_TILE_SIZE),
        )
        gray = clahe.apply(gray)
        if debug_frames is not None:
            debug_frames.append(("CLAHE", gray.copy()))

    # 5. Threshold → binary mask (255 = line pixel, 0 = background)
    thresh_type = cv2.THRESH_BINARY_INV if config.INVERT else cv2.THRESH_BINARY

    if config.USE_ADAPTIVE_THRESHOLD:
        block = config.ADAPTIVE_BLOCK_SIZE | 1  # must be odd
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresh_type,
            block,
            config.ADAPTIVE_C,
        )
    elif config.USE_OTSU:
        # Otsu finds the split that minimises intra-class variance on the
        # histogram — ideal for clean diagrams with a clear bimodal distribution.
        otsu_val, binary = cv2.threshold(gray, 0, 255, thresh_type | cv2.THRESH_OTSU)
        if debug_frames is not None:
            print(f"    Otsu threshold value: {otsu_val:.0f}")
    else:
        _, binary = cv2.threshold(gray, config.THRESHOLD, 255, thresh_type)

    if debug_frames is not None:
        debug_frames.append(("Threshold", binary.copy()))

    # 6. Morphological CLOSE — bridges tiny gaps in broken lines.
    #    Disabled by default for clean exports (NOISE_KERNEL = 0).
    if config.NOISE_KERNEL > 0:
        k = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (config.NOISE_KERNEL, config.NOISE_KERNEL),
        )
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)

    # 7. Morphological OPEN — removes isolated speckle noise.
    #    Disabled by default for clean exports (SPECKLE_KERNEL = 0).
    #    WARNING: any SPECKLE_KERNEL >= line_width will erase thin lines entirely.
    if config.SPECKLE_KERNEL > 0:
        k = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (config.SPECKLE_KERNEL, config.SPECKLE_KERNEL),
        )
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)

    if debug_frames is not None and (config.NOISE_KERNEL > 0 or config.SPECKLE_KERNEL > 0):
        debug_frames.append(("Cleaned", binary.copy()))

    # 8. Skeletonize — reduces every stroke to exactly 1px width.
    #    Produces the cleanest path fits on uniform-weight engineering lines.
    if config.SKELETONIZE:
        binary = _skeletonize(binary)
        if debug_frames is not None:
            debug_frames.append(("Skeleton", binary.copy()))

    # 9. Build RGBA: black lines on a fully-transparent background.
    rgba = np.zeros((*binary.shape, 4), dtype=np.uint8)
    rgba[binary == 255] = [0, 0, 0, 255]
    rgba[binary == 0]   = [255, 255, 255, 0]

    return binary, rgba


# ---------------------------------------------------------------------------
# Text region detection
# ---------------------------------------------------------------------------

def detect_text_regions(binary: np.ndarray) -> list[dict]:
    """
    Heuristically identify bounding boxes that likely contain text labels
    (e.g. "L1", "L2", "L3") using connected-component analysis.

    Returns a list of dicts: {"x", "y", "w", "h", "area"}.
    """
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    boxes = []
    for i in range(1, num_labels):  # label 0 is the background
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])

        if not (config.TEXT_MIN_AREA <= area <= config.TEXT_MAX_AREA):
            continue

        aspect = w / max(h, 1)
        if not (config.TEXT_ASPECT_MIN <= aspect <= config.TEXT_ASPECT_MAX):
            continue

        # Exclude components that are suspiciously square (likely diagram symbols,
        # not text characters). Text labels tend to be wider than tall.
        if 0.85 <= aspect <= 1.15 and area > 300:
            continue

        boxes.append({"x": x, "y": y, "w": w, "h": h, "area": area})

    return boxes


def draw_text_boxes(rgba: np.ndarray, boxes: list[dict]) -> np.ndarray:
    """Return a copy of the RGBA image with detected text boxes highlighted."""
    vis = rgba.copy()
    for b in boxes:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        # Draw a semi-transparent red rectangle over the alpha channel
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 255, 200), 1)
    return vis


# ---------------------------------------------------------------------------
# Optional processing helpers
# ---------------------------------------------------------------------------

def _skeletonize(binary: np.ndarray) -> np.ndarray:
    """
    Thin all strokes to single-pixel width using the Zhang-Suen algorithm.
    Tries opencv-contrib first (faster), falls back to scikit-image.
    """
    try:
        return cv2.ximgproc.thinning(
            binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN
        )
    except AttributeError:
        pass
    try:
        from skimage.morphology import skeletonize as _sk
        return (_sk(binary > 0) * 255).astype(np.uint8)
    except ImportError:
        print("  [skeletonize] Requires opencv-contrib-python or scikit-image — skipping.")
        return binary


def _fix_svg_scale(svg_path: Path, factor: float) -> None:
    """
    Rescale SVG root width/height after tracing an upscaled bitmap so the
    output SVG renders at the original image's physical dimensions.
    Only modifies the first width= and height= attributes (the root element).
    """
    text = svg_path.read_text(encoding="utf-8")

    def _scale_attr(m: re.Match) -> str:
        attr, val, unit = m.group(1), float(m.group(2)), m.group(3) or ""
        return f'{attr}="{val / factor:.4f}{unit}"'

    text = re.sub(r'(width)="([\d.]+)([a-z%]*)"',  _scale_attr, text, count=1)
    text = re.sub(r'(height)="([\d.]+)([a-z%]*)"', _scale_attr, text, count=1)
    svg_path.write_text(text, encoding="utf-8")


def _save_debug_composite(
    frames: list[tuple[str, np.ndarray]],
    out_path: Path,
    panel_height: int = 320,
) -> None:
    """
    Build a horizontal contact sheet from (label, image) pairs and save it.
    Each image may be grayscale (2D), BGR (3-channel), or RGBA (4-channel).
    The output filename preserves the input stem with a _debug.png suffix.
    """
    LABEL_H = 22
    panels  = []

    for label, arr in frames:
        # Normalise to BGR for display
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
        disp  = cv2.resize(disp, (max(1, int(w * scale)), panel_height),
                           interpolation=cv2.INTER_AREA)

        bar = np.full((LABEL_H, disp.shape[1], 3), 30, dtype=np.uint8)
        cv2.putText(bar, label, (4, LABEL_H - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (210, 210, 210), 1, cv2.LINE_AA)
        panels.append(np.vstack([bar, disp]))

    cv2.imwrite(str(out_path), np.hstack(panels))


# ---------------------------------------------------------------------------
# Vectorization — potrace
# ---------------------------------------------------------------------------

def _save_pbm(binary: np.ndarray, path: Path) -> None:
    """Save a binary mask as PBM (potrace's native input format)."""
    pil = Image.fromarray(binary).convert("1")
    pil.save(str(path))


def _vectorize_potrace(binary: np.ndarray, svg_path: Path) -> bool:
    """
    Call the potrace CLI to convert a binary mask to SVG.
    Returns True on success, False if potrace is not installed.
    """
    potrace_bin = shutil.which("potrace")
    if potrace_bin is None:
        return False

    pbm_path = svg_path.with_suffix(".pbm")
    try:
        _save_pbm(binary, pbm_path)
        # --resolution tells potrace the DPI of the bitmap so the SVG
        # width/height are expressed in correct physical units. Multiplying
        # by UPSCALE_FACTOR compensates for the upscaled input, keeping the
        # output SVG at the original image's visual dimensions.
        cmd = [
            potrace_bin,
            str(pbm_path),
            "--svg",
            "--output",       str(svg_path),
            "--turdsize",     str(config.POTRACE_TURDSIZE),
            "--alphamax",     str(config.POTRACE_ALPHAMAX),
            "--opttolerance", str(config.POTRACE_OPTTOLERANCE),
            "--resolution",   str(72 * config.UPSCALE_FACTOR),
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


# ---------------------------------------------------------------------------
# Vectorization — vtracer (pip install vtracer)
# ---------------------------------------------------------------------------

def _vectorize_vtracer(binary: np.ndarray, svg_path: Path) -> bool:
    """
    Use the vtracer Python package to convert a binary mask to SVG.
    Returns True on success, False if vtracer is not installed.
    """
    try:
        import vtracer  # noqa: PLC0415
    except ImportError:
        return False

    tmp_png = svg_path.with_suffix(".tmp.png")
    try:
        # vtracer reads image files; write white-bg / black-lines PNG
        display = cv2.bitwise_not(binary)
        cv2.imwrite(str(tmp_png), display)

        vtracer.convert_image_to_svg_py(
            str(tmp_png),
            str(svg_path),
            colormode="binary",
            hierarchical="stacked",
            filter_speckle=config.VTRACER_FILTER_SPECKLE,
            color_precision=config.VTRACER_COLOR_PRECISION,
            corner_threshold=config.VTRACER_CORNER_THRESHOLD,
            length_threshold=config.VTRACER_SEGMENT_LENGTH,
            splice_threshold=config.VTRACER_SPLICE_THRESHOLD,
            path_precision=8,
        )
        if config.UPSCALE_FACTOR > 1:
            _fix_svg_scale(svg_path, config.UPSCALE_FACTOR)
        return True
    except Exception as exc:
        print(f"    [vtracer] {exc}")
        return False
    finally:
        if tmp_png.exists():
            tmp_png.unlink()


def vectorize_to_svg(binary: np.ndarray, svg_path: Path) -> str:
    """
    Vectorize binary mask to SVG using the best available engine.

    Priority: potrace (best quality) → vtracer (pip fallback).
    Returns the engine name used.
    Raises RuntimeError if neither engine is available.
    """
    if _vectorize_potrace(binary, svg_path):
        return "potrace"
    if _vectorize_vtracer(binary, svg_path):
        return "vtracer"
    raise RuntimeError(
        "No vectorization engine found.\n"
        "  Option A (recommended): Install potrace\n"
        "    Windows : choco install potrace  OR  download from https://potrace.sourceforge.net\n"
        "    macOS   : brew install potrace\n"
        "    Linux   : sudo apt install potrace\n"
        "  Option B: pip install vtracer"
    )


# ---------------------------------------------------------------------------
# Single-image pipeline
# ---------------------------------------------------------------------------

def process_image(input_path: Path, output_dir: Path, save_debug: bool = False) -> dict:
    """
    Run the full pipeline on one image.

    Outputs (all named after the original input stem):
      <stem>_clean.png — transparent-background PNG
      <stem>.svg       — vector SVG
      <stem>_text.json — text region bounding boxes (if DETECT_TEXT=True)
      <stem>_debug.png — pipeline contact sheet (if save_debug=True)
    """
    stem      = input_path.stem
    out_png   = output_dir / f"{stem}_clean.png"
    out_svg   = output_dir / f"{stem}.svg"
    out_json  = output_dir / f"{stem}_text.json"
    out_debug = output_dir / f"{stem}_debug.png"

    debug_frames: list | None = [] if save_debug else None

    print(f"  Loading   {input_path.name}")
    img = load_image(input_path)

    print(f"  Cleaning  …")
    binary, rgba = clean_image(img, debug_frames=debug_frames)

    # Text detection
    text_boxes: list[dict] = []
    if config.DETECT_TEXT:
        text_boxes = detect_text_regions(binary)
        if text_boxes:
            print(f"  Text      {len(text_boxes)} region(s) detected")

            if debug_frames is not None:
                vis = draw_text_boxes(rgba, text_boxes)
                debug_frames.append(("Text regions", vis))

            # Scale coordinates back to original image space so the JSON
            # is usable against the source image, not the upscaled bitmap.
            if config.UPSCALE_FACTOR > 1:
                f = config.UPSCALE_FACTOR
                text_boxes = [
                    {
                        "x": b["x"] // f,
                        "y": b["y"] // f,
                        "w": b["w"] // f,
                        "h": b["h"] // f,
                        "area": b["area"] // (f * f),
                    }
                    for b in text_boxes
                ]

            out_json.write_text(json.dumps(text_boxes, indent=2))

    # Save cleaned PNG
    Image.fromarray(rgba, "RGBA").save(str(out_png))
    print(f"  PNG       → {out_png.name}")

    # Vectorize
    engine = vectorize_to_svg(binary, out_svg)
    print(f"  SVG [{engine:8s}] → {out_svg.name}")

    # Save debug composite (single file, named after the input)
    if debug_frames:
        _save_debug_composite(debug_frames, out_debug)
        print(f"  Debug     → {out_debug.name}")

    return {
        "input": str(input_path),
        "png":   str(out_png),
        "svg":   str(out_svg),
        "engine": engine,
        "text_boxes": text_boxes,
    }


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch vectorize technical diagram images to SVG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        default=config.INPUT_DIR,
        help=f"Folder containing source images (default: {config.INPUT_DIR})",
    )
    parser.add_argument(
        "--output", "-o",
        default=config.OUTPUT_DIR,
        help=f"Folder to write results (default: {config.OUTPUT_DIR})",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        default=config.SAVE_DEBUG_IMAGES,
        help="Save a pipeline contact sheet for each file: output/<stem>_debug.png",
    )
    args = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"ERROR: Input folder '{input_dir}' does not exist.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() in config.SUPPORTED_FORMATS
    )

    if not images:
        print(f"No images found in '{input_dir}'.")
        print(f"Supported formats: {', '.join(config.SUPPORTED_FORMATS)}")
        sys.exit(0)

    print(f"Image Vectorizer Tool")
    print(f"{'─' * 50}")
    print(f"Input  : {input_dir.resolve()}")
    print(f"Output : {output_dir.resolve()}")
    print(f"Images : {len(images)}")
    print(f"{'─' * 50}\n")

    results, errors = [], []

    for img_path in images:
        print(f"[{images.index(img_path) + 1}/{len(images)}] {img_path.name}")
        try:
            result = process_image(img_path, output_dir, save_debug=args.debug)
            results.append(result)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors.append({"file": str(img_path), "error": str(exc)})
        print()

    print(f"{'─' * 50}")
    print(f"Completed: {len(results)} succeeded, {len(errors)} failed.")

    if errors:
        print("\nFailed:")
        for e in errors:
            print(f"  {Path(e['file']).name}: {e['error']}")


if __name__ == "__main__":
    main()