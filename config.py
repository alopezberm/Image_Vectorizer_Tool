"""
config.py — Tuneable parameters for the Image Vectorizer Tool.

Two ready-to-use presets are provided. The active one is "Clean Engineering Diagram".
To switch, comment the CLEAN block and uncomment the SCAN block.
"""

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
INPUT_DIR  = "input"
OUTPUT_DIR = "output"
SUPPORTED_FORMATS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

# ===========================================================================
# PRESET A — Clean Engineering Diagram  ← ACTIVE
# Best for: CAD exports, Visio/Draw.io exports, clean digital diagrams.
#           Thin black lines on a pure white background, minimal noise.
# ===========================================================================

INVERT = True           # Black lines on white background

# Otsu auto-threshold: finds the ideal split from the image histogram.
# Eliminates the need to manually tune THRESHOLD for each image.
# Disable and set THRESHOLD manually only if Otsu gives wrong results.
USE_OTSU = True
THRESHOLD = 240         # Only used when USE_OTSU = False and USE_ADAPTIVE_THRESHOLD = False

USE_ADAPTIVE_THRESHOLD = False   # Better for uneven lighting — not needed for clean exports
ADAPTIVE_BLOCK_SIZE    = 25      # Neighbourhood size (must be odd)
ADAPTIVE_C             = 10      # Higher → fewer pixels classified as line

# Median blur removes JPEG block artifacts BEFORE thresholding.
# Set to 0 for clean PNG exports (no compression artifacts).
# Set to 3–5 for JPEG inputs.
MEDIAN_BLUR = 0

# Morphological CLOSE — bridges gaps in broken lines.
# Clean exports have no broken lines, so disable (0).
NOISE_KERNEL = 0

# Morphological OPEN — removes isolated speckle noise.
# Not needed for clean exports; enabling it WILL erase thin 1px lines.
SPECKLE_KERNEL = 0

# CLAHE (Contrast Limited Adaptive Histogram Equalization).
# Not needed for clean high-contrast exports. Enable for washed-out scans.
USE_CLAHE       = False
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_SIZE  = 8

# Upscale the image N× before thresholding and tracing.
# Gives potrace/vtracer more pixels to work with, significantly improving
# fidelity on 1–3px lines. SVG output dimensions are automatically corrected.
# Recommended: 2. Diminishing returns above 3. Use 1 to disable.
UPSCALE_FACTOR = 2

# Skeletonize: thin all strokes to exactly 1px before tracing.
# Produces the cleanest potrace paths on diagrams with uniform-weight lines.
# Requires: pip install opencv-contrib-python  OR  pip install scikit-image
# Caution: can create artifacts at T-junctions; test with --debug first.
SKELETONIZE = False

# ===========================================================================
# PRESET B — Scanned Document  (uncomment this block, comment block A above)
# Best for: photo scans, photocopies, printed-then-scanned PDFs.
# ===========================================================================
# INVERT                = True
# USE_OTSU              = False
# THRESHOLD             = 180
# USE_ADAPTIVE_THRESHOLD = True
# ADAPTIVE_BLOCK_SIZE   = 25
# ADAPTIVE_C            = 10
# MEDIAN_BLUR           = 3
# NOISE_KERNEL          = 2
# SPECKLE_KERNEL        = 1
# USE_CLAHE             = True
# CLAHE_CLIP_LIMIT      = 3.0
# CLAHE_TILE_SIZE       = 8
# UPSCALE_FACTOR        = 1
# SKELETONIZE           = False

# ---------------------------------------------------------------------------
# Vectorization — potrace (preferred, requires CLI install)
# ---------------------------------------------------------------------------

# Suppress connected components smaller than N px². Keep low for detail.
POTRACE_TURDSIZE = 2

# Corner smoothness: 0.0 = perfectly sharp corners (right for engineering geometry).
# Increase toward 1.33 only if you want rounded/organic curves.
POTRACE_ALPHAMAX = 0.0

# Bezier curve fit tolerance. Lower = more path nodes, more faithful geometry.
# 0.1 is tight. Loosen to 0.3–0.5 if SVG file size is a concern.
POTRACE_OPTTOLERANCE = 0.1

# ---------------------------------------------------------------------------
# Vectorization — vtracer (fallback, pip install vtracer)
# ---------------------------------------------------------------------------
VTRACER_FILTER_SPECKLE    = 2
VTRACER_COLOR_PRECISION   = 6
VTRACER_CORNER_THRESHOLD  = 60   # Degrees; lower = more corners preserved
VTRACER_SEGMENT_LENGTH    = 3.0
VTRACER_SPLICE_THRESHOLD  = 45

# ---------------------------------------------------------------------------
# Text region detection (connected-component heuristic)
# ---------------------------------------------------------------------------
DETECT_TEXT    = True
TEXT_MIN_AREA  = 30     # Minimum component area (px²) to be considered text
TEXT_MAX_AREA  = 8000   # Maximum — larger components are diagram geometry
TEXT_ASPECT_MIN = 0.15  # Min width/height ratio
TEXT_ASPECT_MAX = 10.0  # Max width/height ratio

# ---------------------------------------------------------------------------
# Debug output
# ---------------------------------------------------------------------------
# Saves a single pipeline contact sheet to output/<stem>_debug.png.
# The composite shows each stage (gray → threshold → cleaned → …) side by side.
# Always run with --debug first on a new image type to verify each stage.
SAVE_DEBUG_IMAGES = False