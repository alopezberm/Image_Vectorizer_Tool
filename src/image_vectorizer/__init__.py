"""
image_vectorizer — Local tool for vectorizing technical diagram images.

Public API
----------
process_image(input_path, output_dir, params=None, save_debug=False) -> dict
default_params() -> dict
"""

from pathlib import Path

from .config import default_params
from .io_utils import (
    make_output_paths,
    save_clean_png,
    save_debug_composite,
    save_text_json,
)
from .processing import clean_image, detect_text_regions, draw_text_boxes, load_image
from .vectorization import vectorize_to_svg

__all__ = ["process_image", "default_params"]


def process_image(
    input_path: Path | str,
    output_dir: Path | str,
    params: dict | None = None,
    save_debug: bool = False,
) -> dict:
    """
    Run the full vectorization pipeline on a single image.

    Parameters
    ----------
    input_path : path to the source image
    output_dir : folder where all outputs are written (created if absent)
    params     : processing parameters dict (see default_params()).
                 Pass None to use the defaults from config.py.
    save_debug : if True, save a pipeline contact sheet to <stem>_debug.png

    Returns
    -------
    dict with keys: input, png, svg, engine, text_boxes
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if params is None:
        params = default_params()

    paths        = make_output_paths(input_path.stem, output_dir)
    debug_frames = [] if save_debug else None

    img            = load_image(input_path)
    binary, rgba   = clean_image(img, params, debug_frames=debug_frames)

    text_boxes: list[dict] = []
    if params.get("detect_text", True):
        text_boxes = detect_text_regions(binary, params)
        if text_boxes:
            if debug_frames is not None:
                vis = draw_text_boxes(rgba, text_boxes)
                debug_frames.append(("Text regions", vis))

            upscale = params.get("upscale_factor", 1)
            if upscale > 1:
                text_boxes = [
                    {
                        "x":    b["x"]    // upscale,
                        "y":    b["y"]    // upscale,
                        "w":    b["w"]    // upscale,
                        "h":    b["h"]    // upscale,
                        "area": b["area"] // (upscale * upscale),
                    }
                    for b in text_boxes
                ]

            save_text_json(text_boxes, paths["json"])

    save_clean_png(rgba, paths["png"])
    engine = vectorize_to_svg(binary, paths["svg"], params)

    if debug_frames:
        save_debug_composite(debug_frames, paths["debug"])

    return {
        "input":      str(input_path),
        "png":        str(paths["png"]),
        "svg":        str(paths["svg"]),
        "engine":     engine,
        "text_boxes": text_boxes,
    }