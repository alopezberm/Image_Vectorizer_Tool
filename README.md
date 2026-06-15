# Image Vectorizer Tool

Convert technical diagram images (PNG / JPG) into clean, editable SVG vector graphics — optimised for electrical layouts, MV station diagrams, and similar engineering line drawings.

Licensed under the [MIT License](LICENSE).

---

## Features

- **Batch CLI** — drop images into `input/`, get SVGs in `output/`
- **Interactive notebook** — file-upload UI with sliders, live preview, and ZIP download (no terminal required)
- **Transparent PNG** — output has a fully transparent background, ready for overlay use
- **Thin-line preservation** — Otsu auto-threshold + 2× upscale keeps 1–3 px lines intact
- **SVG vectorization** — via [potrace](https://potrace.sourceforge.net) (preferred) or [vtracer](https://github.com/visioncortex/vtracer) (pip fallback)
- **Text region detection** — heuristically locates labels (L1, L2, L3…) and saves bounding boxes to JSON
- **Debug mode** — saves a side-by-side pipeline contact sheet per image (`<stem>_debug.png`)
- **Two presets** — Clean Engineering Diagram (default) and Scanned Document, switchable in `config.py`

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
│   └── vectorizer_ui.ipynb   # Interactive UI (no core logic inside)
├── input/                    # Place source images here (CLI usage)
├── output/                   # Results are written here (CLI usage)
├── run.py                    # Batch CLI entry point
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Installation

### 1. Python environment

Requires **Python 3.11+**.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Vectorization engine

You need **at least one** of the following.

#### Option A — potrace (recommended)

Produces the cleanest SVG paths for black-and-white line art.

| Platform | Command |
|----------|---------|
| Windows  | `choco install potrace` or download from https://potrace.sourceforge.net |
| macOS    | `brew install potrace` |
| Linux    | `sudo apt install potrace` |

Verify: `potrace --version`

#### Option B — vtracer (no external binary)

```bash
pip install vtracer
```

The tool tries potrace first and falls back to vtracer automatically.

---

## Usage

### Jupyter Notebook (recommended)

```bash
jupyter lab notebooks/vectorizer_ui.ipynb
```

1. **Kernel → Restart & Run All**
2. Click **Upload Images** and select your files
3. Adjust parameters with the sliders if needed
4. Click **▶ Process Images**
5. Review the before / after preview
6. Click **⬇ Download ZIP** to save all outputs

### Command-line batch runner

```bash
# Process all images in input/ → output/
python run.py

# Custom folders
python run.py --input my_scans --output results

# Debug mode — also saves <stem>_debug.png per image
python run.py --debug
```

---

## Input / Output

Place PNG, JPG, BMP, or TIFF files in `input/`. All outputs are named after the original file — only suffixes are appended.

```
input/
└── layout_A.png

output/
├── layout_A_clean.png    # Transparent-background PNG
├── layout_A.svg          # Vector SVG for PowerPoint
├── layout_A_text.json    # Label bounding boxes (if DETECT_TEXT=True)
└── layout_A_debug.png    # Pipeline contact sheet (if --debug)
```

No random or hashed filenames are ever generated.

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
| SVG has too many fragments | `POTRACE_TURDSIZE = 10` |
| Corners are rounded | `POTRACE_ALPHAMAX = 0.0` |
| SVG file is very large | `POTRACE_OPTTOLERANCE = 0.5` |

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
| `ipywidgets` | Notebook UI widgets |
| `matplotlib` | Notebook before / after previews |
| `potrace` (CLI) | Primary vectorization engine |
| `vtracer` (pip, optional) | Fallback vectorization engine |
| `opencv-contrib-python` (optional) | Fast skeletonization |
| `scikit-image` (optional) | Fallback skeletonization |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.