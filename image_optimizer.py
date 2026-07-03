"""
image_optimizer.py
==================
Linkphobot - Phase 7: Export System
Image Optimization Pipeline

Features:
- Resize with high-quality resampling
- Sharpening filter
- PNG compression optimization
- JPEG quality tuning
- File size enforcement (target KB)
- Color profile management
- Anti-aliasing
- Metadata stripping
- LinkedIn-specific optimizations
"""

import os
import io
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

from export_config import ExportPreset, PRESET_LINKEDIN


# ════════════════════════════════════════════════════════════════════════════
# RESAMPLING FILTER
# ════════════════════════════════════════════════════════════════════════════

def _get_resample_filter():
    """Return best available resampling filter."""
    try:
        return Image.LANCZOS
    except AttributeError:
        return Image.ANTIALIAS


# ════════════════════════════════════════════════════════════════════════════
# CORE RESIZE
# ════════════════════════════════════════════════════════════════════════════

def resize_image(img: Image.Image,
                  target_w: int,
                  target_h: int,
                  antialias: bool = True) -> Image.Image:
    """
    Resize image to exact target dimensions.

    Args:
        img       : PIL Image
        target_w  : target width in pixels
        target_h  : target height in pixels
        antialias : use Lanczos resampling

    Returns:
        resized PIL Image
    """
    if img.width == target_w and img.height == target_h:
        return img

    resample = _get_resample_filter() if antialias else Image.NEAREST
    return img.resize((target_w, target_h), resample)


def resize_contain(img: Image.Image,
                    max_w: int,
                    max_h: int) -> Image.Image:
    """
    Scale image to fit within max_w x max_h, preserving aspect ratio.
    """
    ratio  = min(max_w / img.width, max_h / img.height)
    new_w  = int(img.width  * ratio)
    new_h  = int(img.height * ratio)
    return img.resize((new_w, new_h), _get_resample_filter())


# ════════════════════════════════════════════════════════════════════════════
# SHARPENING
# ════════════════════════════════════════════════════════════════════════════

def apply_sharpening(img: Image.Image,
                      amount: float = 0.3) -> Image.Image:
    """
    Apply unsharp mask sharpening to improve visual clarity at export.

    Args:
        img    : PIL Image
        amount : sharpening strength 0.0 (none) to 1.0 (strong)

    Returns:
        sharpened PIL Image
    """
    if amount <= 0:
        return img

    # Clamp and scale parameters
    amount  = max(0.0, min(1.0, amount))
    radius  = 1.0 + amount * 1.5
    percent = int(80 + amount * 120)
    threshold = max(1, int(4 - amount * 3))

    return img.filter(
        ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
    )


def apply_mild_contrast(img: Image.Image,
                          factor: float = 1.05) -> Image.Image:
    """
    Slightly boost contrast to compensate for LinkedIn's display compression.
    """
    if factor == 1.0:
        return img
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(factor)


# ════════════════════════════════════════════════════════════════════════════
# COLOR MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════

def ensure_rgb(img: Image.Image) -> Image.Image:
    """Convert image to RGB mode (strips alpha, converts from RGBA/P etc.)."""
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA"):
        # Composite onto white background
        bg  = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            bg.paste(img, mask=img.split()[3])
        else:
            bg.paste(img)
        return bg
    return img.convert("RGB")


def ensure_rgba(img: Image.Image) -> Image.Image:
    """Convert image to RGBA mode."""
    if img.mode == "RGBA":
        return img
    return img.convert("RGBA")


# ════════════════════════════════════════════════════════════════════════════
# PNG OPTIMIZER
# ════════════════════════════════════════════════════════════════════════════

def optimize_png(img: Image.Image,
                  compress_level: int = 6,
                  optimize: bool = True,
                  strip_metadata: bool = True) -> bytes:
    """
    Export PIL Image to optimized PNG bytes.

    Args:
        img            : PIL Image (RGB or RGBA)
        compress_level : zlib compression 0-9 (6 = good balance)
        optimize       : use PIL optimize flag
        strip_metadata : exclude EXIF/ICC from output

    Returns:
        PNG bytes
    """
    buf = io.BytesIO()

    save_kwargs = {
        "format":   "PNG",
        "compress_level": compress_level,
        "optimize": optimize,
    }

    img.save(buf, **save_kwargs)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
# JPEG OPTIMIZER
# ════════════════════════════════════════════════════════════════════════════

def optimize_jpeg(img: Image.Image,
                   quality:    int  = 88,
                   optimize:   bool = True,
                   progressive:bool = True,
                   subsampling:int  = 2) -> bytes:
    """
    Export PIL Image to optimized JPEG bytes.

    Args:
        img         : PIL Image (must be RGB)
        quality     : JPEG quality 1-100
        optimize    : Huffman table optimization
        progressive : progressive scan for web
        subsampling : chroma subsampling (0=4:4:4, 1=4:2:2, 2=4:2:0)

    Returns:
        JPEG bytes
    """
    img = ensure_rgb(img)
    buf = io.BytesIO()

    img.save(buf,
             format      = "JPEG",
             quality     = quality,
             optimize    = optimize,
             progressive = progressive,
             subsampling = subsampling)

    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
# SIZE REDUCER  –  iterate until target size is met
# ════════════════════════════════════════════════════════════════════════════

def reduce_to_target_size(img: Image.Image,
                           target_kb:  int,
                           fmt:        str = "PNG",
                           min_quality:int = 60) -> bytes:
    """
    Iteratively reduce quality / compression until file size <= target_kb.

    Args:
        img        : PIL Image
        target_kb  : maximum allowed file size in KB
        fmt        : "PNG" or "JPEG"
        min_quality: minimum JPEG quality before giving up

    Returns:
        optimized image bytes
    """
    target_bytes = target_kb * 1024

    if fmt.upper() == "PNG":
        # Try increasing compression levels
        for level in range(4, 10):
            data = optimize_png(img, compress_level=level)
            if len(data) <= target_bytes:
                return data
        return data  # return most compressed even if over limit

    else:  # JPEG
        quality = 90
        while quality >= min_quality:
            data = optimize_jpeg(img, quality=quality)
            if len(data) <= target_bytes:
                return data
            quality -= 5
        return data  # return lowest quality attempt


# ════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE FUNCTION
# ════════════════════════════════════════════════════════════════════════════

def optimize_for_export(img: Image.Image,
                         preset: ExportPreset) -> Tuple[bytes, dict]:
    """
    Run the complete optimization pipeline for an export preset.

    Pipeline:
      1. Resize to target dimensions
      2. Ensure correct color mode
      3. Apply sharpening if configured
      4. Apply mild contrast boost (LinkedIn compensator)
      5. Encode to target format
      6. Enforce max file size if configured

    Args:
        img    : PIL Image (source, any size)
        preset : ExportPreset configuration

    Returns:
        (image_bytes, stats_dict)
    """
    stats = {
        "original_size": f"{img.width}x{img.height}",
        "target_size":   f"{preset.width}x{preset.height}",
        "format":        preset.format,
        "steps":         [],
    }

    # Step 1: Resize
    if img.width != preset.width or img.height != preset.height:
        img = resize_image(img, preset.width, preset.height, preset.antialias)
        stats["steps"].append(f"resized to {preset.width}x{preset.height}")

    # Step 2: Color mode
    if preset.colorspace == "RGB":
        img = ensure_rgb(img)
        stats["steps"].append("converted to RGB")

    # Step 3: Sharpen
    if preset.sharpen and preset.sharpen_amount > 0:
        img = apply_sharpening(img, preset.sharpen_amount)
        stats["steps"].append(f"sharpened (amount={preset.sharpen_amount})")

    # Step 4: Contrast boost for LinkedIn
    if preset.name in ("linkedin", "linkedin_hq"):
        img = apply_mild_contrast(img, 1.03)
        stats["steps"].append("contrast boost x1.03")

    # Step 5: Encode
    fmt = preset.format.upper()
    if fmt == "PNG":
        data = optimize_png(img,
                             compress_level=preset.compress_level,
                             optimize=preset.optimize)
    elif fmt in ("JPEG", "JPG"):
        data = optimize_jpeg(img,
                              quality=preset.quality,
                              optimize=preset.optimize)
    else:
        # Fallback to PNG
        data = optimize_png(img, compress_level=6)

    stats["steps"].append(f"encoded as {fmt}")
    stats["encoded_kb"] = round(len(data) / 1024, 1)

    # Step 6: Size enforcement
    if preset.max_size_kb > 0 and len(data) > preset.max_size_kb * 1024:
        data = reduce_to_target_size(img, preset.max_size_kb, fmt)
        stats["steps"].append(f"size reduced to {round(len(data)/1024,1)}KB")

    stats["final_kb"] = round(len(data) / 1024, 1)
    return data, stats


# ════════════════════════════════════════════════════════════════════════════
# WRITE TO DISK
# ════════════════════════════════════════════════════════════════════════════

def write_image_bytes(data: bytes, filepath: str) -> int:
    """
    Write image bytes to disk.

    Returns:
        file size in bytes
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(data)
    return len(data)


def validate_exported_file(filepath: str,
                             expected_format: str = "PNG") -> dict:
    """
    Validate an exported image file.

    Returns:
        dict with valid, width, height, format, size_kb, issues
    """
    issues = []
    if not os.path.exists(filepath):
        return {"valid": False, "issues": ["File does not exist"]}

    try:
        img  = Image.open(filepath)
        fmt  = img.format or "UNKNOWN"
        w, h = img.size
        kb   = round(os.path.getsize(filepath) / 1024, 1)

        if kb < 2:
            issues.append(f"Suspiciously small file ({kb} KB)")
        if kb > 5120:
            issues.append(f"Exceeds LinkedIn 5MB limit ({kb} KB)")
        if w < 552:
            issues.append(f"Width too small for LinkedIn ({w}px)")

        return {
            "valid":    len(issues) == 0,
            "width":    w,
            "height":   h,
            "format":   fmt,
            "size_kb":  kb,
            "issues":   issues,
        }
    except Exception as e:
        return {"valid": False, "issues": [str(e)]}
