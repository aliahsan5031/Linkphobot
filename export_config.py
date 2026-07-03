"""
export_config.py
================
Linkphobot - Phase 7: Export System
Export Configuration & Presets

Defines all export settings, quality presets,
format specs, and LinkedIn optimization parameters.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple
import json


# ════════════════════════════════════════════════════════════════════════════
# CANVAS SPECS
# ════════════════════════════════════════════════════════════════════════════

CANVAS_W = 1080
CANVAS_H = 1350

# LinkedIn image spec requirements
LINKEDIN_MAX_FILE_SIZE_MB = 5.0
LINKEDIN_MIN_WIDTH        = 552
LINKEDIN_MAX_WIDTH        = 7680
LINKEDIN_RECOMMENDED_W    = 1080
LINKEDIN_RECOMMENDED_H    = 1350
LINKEDIN_ASPECT_RATIO     = "4:5"


# ════════════════════════════════════════════════════════════════════════════
# EXPORT PRESETS
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ExportPreset:
    name:              str
    description:       str
    format:            str         # "PNG" | "JPEG" | "WEBP"
    width:             int
    height:            int
    dpi:               int
    quality:           int         # JPEG/WEBP quality 1-100 (PNG ignores this)
    optimize:          bool        # PIL optimize flag
    compress_level:    int         # PNG compress 0-9
    max_size_kb:       int         # target max file size in KB (0 = no limit)
    suffix:            str         # filename suffix e.g. "_linkedin"
    antialias:         bool = True
    sharpen:           bool = False
    sharpen_amount:    float = 0.0
    colorspace:        str = "RGB"

    def to_dict(self) -> dict:
        return asdict(self)


# ── LinkedIn (primary) ────────────────────────────────────────────────────
PRESET_LINKEDIN = ExportPreset(
    name           = "linkedin",
    description    = "LinkedIn feed post — 1080x1350 optimized PNG",
    format         = "PNG",
    width          = 1080,
    height         = 1350,
    dpi            = 96,
    quality        = 95,
    optimize       = True,
    compress_level = 6,
    max_size_kb    = 4096,   # 4 MB
    suffix         = "",
    antialias      = True,
    sharpen        = True,
    sharpen_amount = 0.3,
    colorspace     = "RGB",
)

# ── LinkedIn HQ (for highest quality) ────────────────────────────────────
PRESET_LINKEDIN_HQ = ExportPreset(
    name           = "linkedin_hq",
    description    = "LinkedIn high-quality — 1080x1350 minimal compression",
    format         = "PNG",
    width          = 1080,
    height         = 1350,
    dpi            = 144,
    quality        = 100,
    optimize       = True,
    compress_level = 3,
    max_size_kb    = 0,      # no size limit
    suffix         = "_hq",
    antialias      = True,
    sharpen        = True,
    sharpen_amount = 0.5,
    colorspace     = "RGB",
)

# ── Web optimized (smaller file) ─────────────────────────────────────────
PRESET_WEB = ExportPreset(
    name           = "web",
    description    = "Web-optimized — smaller file, still sharp",
    format         = "JPEG",
    width          = 1080,
    height         = 1350,
    dpi            = 72,
    quality        = 88,
    optimize       = True,
    compress_level = 6,
    max_size_kb    = 1024,   # 1 MB target
    suffix         = "_web",
    antialias      = True,
    sharpen        = False,
    sharpen_amount = 0.0,
    colorspace     = "RGB",
)

# ── Thumbnail ────────────────────────────────────────────────────────────
PRESET_THUMB = ExportPreset(
    name           = "thumb",
    description    = "Thumbnail preview — 540x675 half-size",
    format         = "JPEG",
    width          = 540,
    height         = 675,
    dpi            = 72,
    quality        = 80,
    optimize       = True,
    compress_level = 6,
    max_size_kb    = 256,
    suffix         = "_thumb",
    antialias      = True,
    sharpen        = False,
    sharpen_amount = 0.0,
    colorspace     = "RGB",
)

# ── Print ready ───────────────────────────────────────────────────────────
PRESET_PRINT = ExportPreset(
    name           = "print",
    description    = "Print-ready — 2160x2700 @300dpi",
    format         = "PNG",
    width          = 2160,
    height         = 2700,
    dpi            = 300,
    quality        = 100,
    optimize       = False,
    compress_level = 1,
    max_size_kb    = 0,
    suffix         = "_print",
    antialias      = True,
    sharpen        = True,
    sharpen_amount = 0.8,
    colorspace     = "RGB",
)

# ── Registry ──────────────────────────────────────────────────────────────
PRESET_REGISTRY = {
    "linkedin":    PRESET_LINKEDIN,
    "linkedin_hq": PRESET_LINKEDIN_HQ,
    "web":         PRESET_WEB,
    "thumb":       PRESET_THUMB,
    "print":       PRESET_PRINT,
}


def get_preset(name: str) -> ExportPreset:
    """Return export preset by name. Defaults to linkedin."""
    return PRESET_REGISTRY.get(name, PRESET_LINKEDIN)


# ════════════════════════════════════════════════════════════════════════════
# EXPORT JOB CONFIG
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ExportConfig:
    """
    Complete configuration for one export job.
    Passed to ExportEngine.export().
    """
    output_dir:       str   = "outputs"
    presets:          List[str] = field(default_factory=lambda: ["linkedin"])
    filename_prefix:  str   = ""          # auto-generated from topic if empty
    overwrite:        bool  = True
    create_dirs:      bool  = True
    save_metadata:    bool  = True        # save JSON metadata alongside PNG
    generate_thumb:   bool  = True        # always generate thumb
    verbose:          bool  = True
    watermark:        bool  = False
    watermark_text:   str   = "Linkphobot"

    def get_presets(self) -> List[ExportPreset]:
        return [get_preset(p) for p in self.presets]

    def to_dict(self) -> dict:
        return asdict(self)


# ── Default config ────────────────────────────────────────────────────────
DEFAULT_CONFIG = ExportConfig(
    output_dir    = "outputs",
    presets       = ["linkedin"],
    generate_thumb= True,
    save_metadata = True,
    verbose       = True,
)


# ════════════════════════════════════════════════════════════════════════════
# QUALITY THRESHOLDS
# ════════════════════════════════════════════════════════════════════════════

MIN_ACCEPTABLE_SIZE_KB  = 50    # below this = suspiciously small
MAX_LINKEDIN_SIZE_KB    = 5120  # LinkedIn hard limit 5MB
WARN_SIZE_KB            = 3072  # warn if above 3MB

# Expected size ranges per preset (KB)
EXPECTED_SIZE_RANGES = {
    "linkedin":    (200, 2500),
    "linkedin_hq": (500, 5000),
    "web":         (80,  800),
    "thumb":       (20,  200),
    "print":       (1000, 50000),
}
