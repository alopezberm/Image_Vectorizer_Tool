# Image Vectorizer Tool

Convert technical diagram images (PNG / JPG) into clean, editable SVG vector graphics — optimised for electrical layouts, MV station diagrams, and similar engineering line drawings.

Licensed under the [MIT License](LICENSE).

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Input / Output](#input--output)
- [Example Workflow — Technical Proposals](#example-workflow--technical-proposals)
- [Tuning Parameters](#tuning-parameters)
- [Dependencies](#dependencies)
- [License](#license)

---

## Features

- **Batch CLI** — drop images into `input/`, get SVGs in `output/`
- **Transparent PNG** — output has a fully transparent background, ready for overlay use
- **Thin-line preservation** — Otsu auto-threshold + 2× upscale keeps 1–3 px lines intact
- **SVG vectorization** — via [vtracer](https://github.com/visioncortex/vtracer) (pip, default) or [potrace](https://potrace.sourceforge.net) (CLI, optional higher quality)
- **Text region detection** — heuristically locates labels (L1, L2, L3…) and saves bounding boxes to JSON
- **Debug mode** — saves a side-by-side pipeline contact sheet per image (`<stem>_debug.png`)
- **Two presets** — Clean Engineering Diagram (default) and Scanned Document, switchable in `config.py`
- **Optional notebook UI** — secondary interface with sliders and live preview (see [Usage](#usage))

---

## Project Structure

```
Image_Vectorizer_Tool/
├── src/
│   └── image_vectorizer/
│       ├── __init__.py       # Public API: process_image(), default_params()
│       ├── config.py         # All tuneable parameters + default_params()
│       ├── processing.py     # Image cleaning, text detection
│       ├── vectorization.py  # potrace / vtracer logic
│       └── io_utils.py       # File saving, output paths, debug composite
├── notebooks/
│   └── vectorizer_ui.ipynb   # Optional interactive UI (see note below)
├── input/
│   └── example_diagram.png   # Bundled sample — safe to overwrite with your own files
├── output/
│   ├── example_diagram.svg          # Sample output (vector)
│   ├── example_diagram_clean.png    # Sample output (transparent PNG)
│   └── example_diagram_text.json    # Sample output (label bounding boxes)
├── run.py                    # Batch CLI entry point — primary usage
├── requirements.txt
├── README.md
└── LICENSE
```

> `input/` and `output/` are working directories. Everything you drop in `input/` or generate in `output/` is gitignored except the bundled `example_diagram.*` files, so your own diagrams never get committed by accident.

---

## Installation

### 1. Python environment

**Requires Python 3.11 or 3.12.** Avoid Python 3.13+ for now — `vtracer`'s native extension does not yet ship stable wheels for the newest interpreters and will crash the process (access violation) rather than raising a normal error.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

If you use [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
```

### 2. Vectorization engine

`vtracer` (installed via `requirements.txt`) works out of the box with no external binary. For higher-quality SVG paths, you can optionally also install potrace:

| Platform | Command |
|----------|---------|
| Windows  | `choco install potrace` or download from https://potrace.sourceforge.net |
| macOS    | `brew install potrace` |
| Linux    | `sudo apt install potrace` |

The tool tries potrace first (if installed) and falls back to vtracer automatically — no configuration needed either way.

---

## Quick Start

The repo ships with a small synthetic example diagram so you can verify your setup immediately, with no data of your own required:

```bash
python run.py
```

This processes `input/example_diagram.png` and writes three files to `output/`:

- `example_diagram_clean.png` — transparent-background cleaned PNG
- `example_diagram.svg` — vector SVG
- `example_diagram_text.json` — detected label bounding boxes

If that runs without errors, your setup is working. Replace the contents of `input/` with your own images and run `python run.py` again.

---

## Usage

### Command-line batch runner (primary)

```bash
# Process all images in input/ → output/
python run.py

# Custom folders
python run.py --input my_scans --output results

# Debug mode — also saves <stem>_debug.png per image
python run.py --debug
```

### Optional: Notebook UI

A secondary, file-upload-based interface is available at [notebooks/vectorizer_ui.ipynb](notebooks/vectorizer_ui.ipynb). It is **not required** — everything it does, `run.py` does from the command line without extra dependencies.

```bash
jupyter lab notebooks/vectorizer_ui.ipynb
```

> **Known limitation:** in VS Code's built-in notebook UI, ipywidgets needs to fetch JavaScript from `unpkg.com`. On networks that block this CDN, the widgets fail to render and the cell may appear to crash. Use **JupyterLab** (as above, which serves widget assets locally) if you hit this, or just use `run.py`.

---

## Input / Output

Place PNG, JPG, BMP, or TIFF files in `input/`. All outputs are named after the original file — only suffixes are appended, and no random or hashed filenames are ever generated.

```
input/
└── layout_A.png

output/
├── layout_A_clean.png    # Transparent-background PNG
├── layout_A.svg          # Vector SVG for PowerPoint
├── layout_A_text.json    # Label bounding boxes (if DETECT_TEXT=True)
└── layout_A_debug.png    # Pipeline contact sheet (if --debug)
```

---

## Example Workflow — Technical Proposals

```
1. Export or scan the diagram as PNG or JPG
   └── Place it in input/

2. Run the tool
   └── python run.py --debug

3. Check output/<stem>_debug.png to verify the threshold caught all lines

4. Import output/<stem>.svg into PowerPoint
   └── Insert → Pictures → This Device → select the SVG

5. Right-click the image → Convert to Shape
   └── PowerPoint converts the SVG into grouped, editable shapes

6. Replace distance labels (L1, L2, L3…)
   └── Use output/<stem>_text.json for bounding box coordinates
   └── Or manually select label shapes after ungrouping
```

---

## Tuning Parameters

All parameters live in [src/image_vectorizer/config.py](src/image_vectorizer/config.py). Two presets are provided — switch by commenting / uncommenting the relevant block.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Thin lines disappear | `NOISE_KERNEL = 0`, `SPECKLE_KERNEL = 0`, `USE_OTSU = True` |
| Background noise remains | `THRESHOLD = 150` (with `USE_OTSU = False`) |
| Lines appear broken in SVG | `NOISE_KERNEL = 2` |
| JPEG compression artifacts | `MEDIAN_BLUR = 3` |
| Uneven scan background | `USE_ADAPTIVE_THRESHOLD = True` or `USE_CLAHE = True` |
| Too many small/false text regions detected | Raise `TEXT_MIN_AREA` or narrow `TEXT_ASPECT_MIN`/`TEXT_ASPECT_MAX` |
| SVG has too many fragments | `POTRACE_TURDSIZE = 10` (potrace) / `VTRACER_FILTER_SPECKLE` higher (vtracer) |
| Corners are rounded | `POTRACE_ALPHAMAX = 0.0` |
| SVG file is very large | `POTRACE_OPTTOLERANCE = 0.5` |
| SVG looks cropped / cut off | Make sure you're on the latest `vectorization.py` — older versions had a `viewBox` scaling bug when `UPSCALE_FACTOR > 1` |

### Preset A — Clean Engineering Diagram *(default)*

Best for CAD exports, Visio / Draw.io exports, clean digital diagrams.

```python
USE_OTSU             = True
MEDIAN_BLUR          = 0
NOISE_KERNEL         = 0
SPECKLE_KERNEL       = 0
UPSCALE_FACTOR       = 2
POTRACE_ALPHAMAX     = 0.0
POTRACE_OPTTOLERANCE = 0.1
```

### Preset B — Scanned Document

Best for photo scans, photocopies, printed-then-scanned PDFs.

```python
USE_OTSU               = False
THRESHOLD              = 180
USE_ADAPTIVE_THRESHOLD = True
MEDIAN_BLUR            = 3
NOISE_KERNEL           = 2
SPECKLE_KERNEL         = 1
USE_CLAHE              = True
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `opencv-python` | Image loading, grayscale, threshold, morphology |
| `Pillow` | PNG with transparency, PBM export for potrace |
| `numpy` | Array operations |
| `vtracer` | Default vectorization engine (pure pip, no external binary) |
| `potrace` (CLI, optional) | Higher-quality vectorization engine, used automatically if installed |
| `ipywidgets`, `matplotlib`, `jupyterlab` | Optional notebook UI only |
| `opencv-contrib-python` (optional) | Fast skeletonization |
| `scikit-image` (optional) | Fallback skeletonization |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.