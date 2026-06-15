# Image Vectorizer Tool

A local Python tool that converts raster technical diagram images (PNG / JPG) into clean, editable SVG vector graphics suitable for importing into PowerPoint.

Designed for electrical layouts, MV station diagrams, and similar engineering line drawings that contain thin black lines and distance labels such as L1, L2, L3.

Licensed under the [MIT License](LICENSE).

---

## Features

- **Batch processing** — drop any number of images into `input/`, get all results in `output/`
- **Background removal** — output PNGs have a fully transparent background
- **Line preservation** — Otsu auto-threshold + 2× upscale ensures 1–3 px thin lines survive
- **SVG vectorization** — via [potrace](https://potrace.sourceforge.net) (preferred) or [vtracer](https://github.com/visioncortex/vtracer) (pip fallback)
- **Text region detection** — heuristically locates labels (L1, L2, L3…) and saves their bounding boxes to JSON for downstream replacement
- **Debug mode** — saves a side-by-side pipeline contact sheet per image (`<stem>_debug.png`)
- **Interactive notebook** — `vectorizer_notebook.ipynb` provides a file-upload UI with sliders, previews, and ZIP download — no terminal required
- **Two presets** — Clean Engineering Diagram (default) and Scanned Document, switchable in `config.py`

---

## Project Structure

```
Image_Vectorizer_Tool/
├── vectorizer.py            # Batch CLI script
├── config.py                # All tuneable parameters
├── vectorizer_notebook.ipynb  # Interactive Jupyter UI
├── requirements.txt         # Python dependencies
├── input/                   # Place source images here
├── output/                  # Results are written here
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

You need **at least one** of the two engines below.

#### Option A — potrace (recommended)

Produces the cleanest SVG paths for black-and-white line art.

| Platform | Command |
|----------|---------|
| Windows  | `choco install potrace` **or** download the binary from https://potrace.sourceforge.net and add it to your PATH |
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

### Command-line script

```bash
# Process all images in input/ → output/
python vectorizer.py

# Custom folders
python vectorizer.py --input my_scans --output results

# Debug mode — also saves <stem>_debug.png per image
python vectorizer.py --debug
```

### Jupyter Notebook

1. Open `vectorizer_notebook.ipynb` in JupyterLab or VS Code
2. Run all cells (Kernel → Restart & Run All)
3. Use the **Upload Images** button to select files from your computer
4. Adjust parameters with the sliders if needed
5. Click **Process Images**
6. Review the before / after preview
7. Click **Download ZIP** to save all outputs

---

## Input / Output Structure

### Input

Place PNG, JPG, BMP, or TIFF files directly in the `input/` folder:

```
input/
├── layout_A.png
├── station_MV.jpg
└── diagram_01.png
```

### Output

All output files are named after the original input filename. Only suffixes are appended before the extension.

```
output/
├── layout_A_clean.png       # Transparent-background PNG
├── layout_A.svg             # Vector SVG for PowerPoint
├── layout_A_text.json       # Text label bounding boxes (if DETECT_TEXT=True)
├── layout_A_debug.png       # Pipeline contact sheet (if --debug)
├── station_MV_clean.png
├── station_MV.svg
└── diagram_01_clean.png
└── diagram_01.svg
```

> No random or hashed filenames are ever generated. Temporary files (`.pbm`, `.tmp.png`) used internally during vectorization are cleaned up automatically.

---

## Example Workflow for Technical Proposals

```
1. Export or scan the electrical / MV station diagram as PNG or JPG
   └── Place it in input/

2. Run the tool
   └── python vectorizer.py --debug

3. Check output/<stem>_debug.png to verify the threshold caught all lines

4. Import output/<stem>.svg into PowerPoint
   └── Insert → Pictures → This Device → select the SVG

5. Right-click the image → Convert to Shape
   └── PowerPoint converts the SVG into grouped editable shapes

6. Replace distance labels (L1, L2, L3…) with text boxes
   └── Use output/<stem>_text.json for the bounding box coordinates
   └── Or manually select the label shapes after ungrouping
```

---

## Tuning Parameters

All parameters live in [config.py](config.py). Two presets are provided — switch by commenting/uncommenting the relevant block.

### Quick reference

| Symptom | Fix |
|---------|-----|
| Thin lines disappear | `NOISE_KERNEL = 0`, `SPECKLE_KERNEL = 0`, `USE_OTSU = True` |
| Background noise remains | `THRESHOLD = 150` (with `USE_OTSU = False`) |
| Lines appear broken in SVG | `NOISE_KERNEL = 2` |
| JPEG compression artifacts | `MEDIAN_BLUR = 3` |
| Uneven scan background | `USE_ADAPTIVE_THRESHOLD = True` or `USE_CLAHE = True` |
| SVG has too many fragments | `POTRACE_TURDSIZE = 10` |
| Corners are rounded | `POTRACE_ALPHAMAX = 0.0` |
| SVG file is very large | Increase `POTRACE_OPTTOLERANCE` to 0.5 |

### Presets

**Preset A — Clean Engineering Diagram** (default)

Best for CAD exports, Visio / Draw.io exports, clean digital diagrams.

```python
USE_OTSU        = True
MEDIAN_BLUR     = 0
NOISE_KERNEL    = 0
SPECKLE_KERNEL  = 0
UPSCALE_FACTOR  = 2
POTRACE_ALPHAMAX = 0.0
POTRACE_OPTTOLERANCE = 0.1
```

**Preset B — Scanned Document**

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
| `Pillow` | PNG save with transparency, PBM export for potrace |
| `numpy` | Array operations |
| `ipywidgets` | Notebook UI widgets |
| `matplotlib` | Notebook before/after previews |
| `potrace` (CLI) | Primary vectorization engine |
| `vtracer` (pip, optional) | Fallback vectorization engine |
| `opencv-contrib-python` (optional) | Fast skeletonization via `ximgproc.thinning` |
| `scikit-image` (optional) | Fallback skeletonization |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.