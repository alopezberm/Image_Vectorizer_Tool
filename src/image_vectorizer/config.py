"""
config.py — Default parameters for the Image Vectorizer Tool.

Two presets are provided below. To switch, comment the active block and
uncomment the other. Call default_params() to get a mutable copy as a dict.
"""

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
INPUT_DIR         = "input"
OUTPUT_DIR        = "output"
SUPPORTED_FORMATS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")

# ===========================================================================
# PRESET A — Clean Engineering Diagram  ← ACTIVE
# Best for: CAD exports, Visio/Draw.io exports, clean digital diagrams.
#           Thin black lines on a pure white background, minimal noise.
# ===========================================================================

INVERT = True

# Otsu auto-threshold: finds the ideal split from the image histogram.
# Eliminates the need to manually tune THRESHOLD for each image.
USE_OTSU  = True
THRESHOLD = 240   # Only used when USE_OTSU = False and USE_ADAPTIVE_THRESHOLD = False

USE_ADAPTIVE_THRESHOLD = False   # Better for uneven lighting — not needed for clean exports
ADAPTIVE_BLOCK_SIZE    = 25      # Neighbourhood size (must be odd)
ADAPTIVE_C             = 10      # Higher → fewer pixels classified as line

# Median blur removes JPEG block artifacts BEFORE thresholding.
# Set to 0 for clean PNG exports. Set to 3–5 for JPEG inputs.
MEDIAN_BLUR = 0

# Morphological CLOSE — bridges gaps in broken lines. Disable for clean exports.
NOISE_KERNEL = 0

# Morphological OPEN — removes speckle noise. WARNING: erases thin 1px lines.
SPECKLE_KERNEL = 0

# CLAHE — contrast boost for washed-out or unevenly lit scans.
USE_CLAHE        = False
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_SIZE  = 8

# Upscale the image Nx before tracing (gives potrace/vtracer more pixels).
# SVG output dimensions are automatically corrected. Recommended: 2.
UPSCALE_FACTOR = 2

# Skeletonize — thins all strokes to exactly 1px before tracing.
# Requires: pip install opencv-contrib-python  OR  pip install scikit-image
SKELETONIZE = False

# ===========================================================================
# PRESET B — Scanned Document  (uncomment this block, comment block A above)
# Best for: photo scans, photocopies, printed-then-scanned PDFs.
# ===========================================================================
# INVERT                 = True
# USE_OTSU               = False
# THRESHOLD              = 180
# USE_ADAPTIVE_THRESHOLD = True
# ADAPTIVE_BLOCK_SIZE    = 25
# ADAPTIVE_C             = 10
# MEDIAN_BLUR            = 3
# NOISE_KERNEL           = 2
# SPECKLE_KERNEL         = 1
# USE_CLAHE              = True
# CLAHE_CLIP_LIMIT       = 3.0
# CLAHE_TILE_SIZE        = 8
# UPSCALE_FACTOR         = 1
# SKELETONIZE            = False

# ---------------------------------------------------------------------------
# Vectorization — potrace (preferred, requires CLI install)
# ---------------------------------------------------------------------------
POTRACE_TURDSIZE     = 2
POTRACE_ALPHAMAX     = 0.0   # 0.0 = sharp corners; increase for curves
POTRACE_OPTTOLERANCE = 0.1   # Lower = more faithful; higher = smaller SVG

# ---------------------------------------------------------------------------
# Vectorization — vtracer (fallback, pip install vtracer)
# ---------------------------------------------------------------------------
VTRACER_FILTER_SPECKLE   = 2
VTRACER_COLOR_PRECISION  = 6
VTRACER_CORNER_THRESHOLD = 60
VTRACER_SEGMENT_LENGTH   = 3.0
VTRACER_SPLICE_THRESHOLD = 45

# ---------------------------------------------------------------------------
# Text region detection
# ---------------------------------------------------------------------------
DETECT_TEXT     = True
TEXT_MIN_AREA   = 30
TEXT_MAX_AREA   = 8000
TEXT_ASPECT_MIN = 0.15
TEXT_ASPECT_MAX = 10.0

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
SAVE_DEBUG_IMAGES = False


def default_params() -> dict:
    """Return a mutable dict of all processing parameters."""
    return {
        "invert":                 INVERT,
        "use_otsu":               USE_OTSU,
        "threshold":              THRESHOLD,
        "use_adaptive_threshold": USE_ADAPTIVE_THRESHOLD,
        "adaptive_block_size":    ADAPTIVE_BLOCK_SIZE,
        "adaptive_c":             ADAPTIVE_C,
        "median_blur":            MEDIAN_BLUR,
        "noise_kernel":           NOISE_KERNEL,
        "speckle_kernel":         SPECKLE_KERNEL,
        "use_clahe":              USE_CLAHE,
        "clahe_clip_limit":       CLAHE_CLIP_LIMIT,
        "clahe_tile_size":        CLAHE_TILE_SIZE,
        "upscale_factor":         UPSCALE_FACTOR,
        "skeletonize":            SKELETONIZE,
        "potrace_turdsize":       POTRACE_TURDSIZE,
        "potrace_alphamax":       POTRACE_ALPHAMAX,
        "potrace_opttolerance":   POTRACE_OPTTOLERANCE,
        "vtracer_filter_speckle":   VTRACER_FILTER_SPECKLE,
        "vtracer_color_precision":  VTRACER_COLOR_PRECISION,
        "vtracer_corner_threshold": VTRACER_CORNER_THRESHOLD,
        "vtracer_segment_length":   VTRACER_SEGMENT_LENGTH,
        "vtracer_splice_threshold": VTRACER_SPLICE_THRESHOLD,
        "detect_text":     DETECT_TEXT,
        "text_min_area":   TEXT_MIN_AREA,
        "text_max_area":   TEXT_MAX_AREA,
        "text_aspect_min": TEXT_ASPECT_MIN,
        "text_aspect_max": TEXT_ASPECT_MAX,
        "save_debug":      SAVE_DEBUG_IMAGES,
    }