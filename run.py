"""
run.py — Command-line batch runner for Image Vectorizer Tool.

Usage:
  python run.py
  python run.py --input my_images --output results
  python run.py --debug
"""

import argparse
import sys
from pathlib import Path

from src.image_vectorizer import process_image
from src.image_vectorizer.config import (
    INPUT_DIR,
    OUTPUT_DIR,
    SAVE_DEBUG_IMAGES,
    SUPPORTED_FORMATS,
    default_params,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch vectorize technical diagram images to SVG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i", default=INPUT_DIR,
        help=f"Source image folder (default: {INPUT_DIR})",
    )
    parser.add_argument(
        "--output", "-o", default=OUTPUT_DIR,
        help=f"Output folder (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true", default=SAVE_DEBUG_IMAGES,
        help="Save a pipeline contact sheet per image: <stem>_debug.png",
    )
    args = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"ERROR: Input folder '{input_dir}' does not exist.")
        sys.exit(1)

    images = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() in SUPPORTED_FORMATS
    )

    if not images:
        print(f"No images found in '{input_dir}'.")
        print(f"Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(0)

    params = default_params()

    print("Image Vectorizer Tool")
    print("─" * 50)
    print(f"Input  : {input_dir.resolve()}")
    print(f"Output : {output_dir.resolve()}")
    print(f"Images : {len(images)}")
    print("─" * 50)
    print()

    results, errors = [], []

    for i, img_path in enumerate(images, 1):
        print(f"[{i}/{len(images)}] {img_path.name}")
        try:
            result = process_image(img_path, output_dir, params=params, save_debug=args.debug)
            results.append(result)
            print(f"  → {Path(result['png']).name}")
            print(f"  → {Path(result['svg']).name}  [{result['engine']}]")
            if result["text_boxes"]:
                print(f"  → {len(result['text_boxes'])} text region(s) detected")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors.append({"file": str(img_path), "error": str(exc)})
        print()

    print("─" * 50)
    print(f"Done: {len(results)} succeeded, {len(errors)} failed.")

    if errors:
        print("\nFailed files:")
        for e in errors:
            print(f"  {Path(e['file']).name}: {e['error']}")


if __name__ == "__main__":
    main()