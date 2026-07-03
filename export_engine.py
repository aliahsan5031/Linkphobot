"""
export_engine.py
================
Linkphobot - Phase 7: Export System
Master Export Orchestrator

Pipeline:
  1. Accept PIL Image(s) or render from content
  2. Apply export presets
  3. Optimize each image
  4. Save to structured output folders
  5. Generate export manifest
  6. Return ExportBatch with all results

Public API:
  ExportEngine.export_images(images, topic, config)  -> ExportBatch
  ExportEngine.export_from_content(content, config)  -> ExportBatch
  quick_export(img, topic, output_dir)               -> list[str]
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Optional, Union, Dict

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export_config import (
    ExportConfig, ExportPreset, DEFAULT_CONFIG,
    PRESET_REGISTRY, PRESET_THUMB, get_preset,
    EXPECTED_SIZE_RANGES, WARN_SIZE_KB,
)
from file_manager import (
    ExportResult, ExportBatch,
    build_folder_structure, ensure_dir,
    generate_batch_filenames, generate_filename,
    resolve_output_path, save_manifest,
    get_file_size_kb, list_exports,
    sanitize_filename,
)
from image_optimizer import (
    optimize_for_export, write_image_bytes,
    validate_exported_file, resize_image,
    ensure_rgb,
)


# ════════════════════════════════════════════════════════════════════════════
# PHASE 3 RENDERER BRIDGE
# ════════════════════════════════════════════════════════════════════════════

def _render_content_to_images(content: dict,
                                template_name: Optional[str] = None) -> List[Image.Image]:
    """
    Bridge to Phase 3 renderer. Returns list of PIL Images.
    Falls back to a placeholder if Phase 3 is not available.
    """
    # Try to load Phase 3 infographic_renderer
    for search_path in [
        os.path.join(os.path.dirname(__file__), "..", "phase3"),
        "/content/linkphobot/phase3",
        "/tmp/linkphobot/phase3",
    ]:
        renderer_path = os.path.join(search_path, "infographic_renderer.py")
        if os.path.isfile(renderer_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "infographic_renderer", renderer_path
            )
            mod = importlib.util.module_from_spec(spec)
            sys.path.insert(0, search_path)
            spec.loader.exec_module(mod)

            # render_infographic returns list of file paths
            tmp_dir = os.path.join(os.path.dirname(__file__), "_tmp_render")
            os.makedirs(tmp_dir, exist_ok=True)
            paths   = mod.render_infographic(
                content, template_name, tmp_dir, verbose=False
            )
            images  = [Image.open(p).copy() for p in paths]
            # cleanup tmp
            for p in paths:
                try:
                    os.remove(p)
                except OSError:
                    pass
            return images

    # Fallback: return a solid-color placeholder
    print("[ExportEngine] Phase 3 renderer not found — using placeholder image")
    from PIL import ImageDraw
    img  = Image.new("RGB", (1080, 1350), "#1E3A5F")
    draw = ImageDraw.Draw(img)
    title = content.get("title", "Infographic")[:60]
    draw.rectangle([54, 54, 1026, 300], fill="#2E6DA4")
    draw.text((540, 177), title, fill="#FFFFFF", anchor="mm")
    return [img]


# ════════════════════════════════════════════════════════════════════════════
# EXPORT ENGINE
# ════════════════════════════════════════════════════════════════════════════

class ExportEngine:
    """
    Phase 7 Export Engine.

    Handles the complete export pipeline:
    render -> optimize -> save -> manifest -> report

    Usage:
        engine = ExportEngine()
        batch  = engine.export_images([pil_img], topic="AI in Healthcare")
        batch.print_summary()
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    # ── Core export: list of PIL Images ───────────────────────────────────
    def export_images(self,
                       images:       List[Image.Image],
                       topic:        str,
                       config:       ExportConfig = None,
                       extra_presets: List[str] = None) -> ExportBatch:
        """
        Export a list of PIL Images with all configured presets.

        Args:
            images       : list of PIL Images (one per carousel page)
            topic        : topic string (used for filenames)
            config       : ExportConfig (uses DEFAULT_CONFIG if None)
            extra_presets: additional preset names beyond config.presets

        Returns:
            ExportBatch with all ExportResults
        """
        if config is None:
            config = DEFAULT_CONFIG

        t_start = time.time()
        batch   = ExportBatch(
            topic        = topic,
            generated_at = datetime.now().isoformat(),
        )

        # Resolve presets
        preset_names = list(config.presets)
        if extra_presets:
            preset_names += [p for p in extra_presets if p not in preset_names]
        if config.generate_thumb and "thumb" not in preset_names:
            preset_names.append("thumb")

        presets = [get_preset(p) for p in preset_names]

        self._log(f"\n[ExportEngine] Exporting {len(images)} image(s), {len(presets)} preset(s)")
        self._log(f"  Topic: {topic[:50]}")
        self._log(f"  Presets: {preset_names}")

        # Build folder structure
        folders = build_folder_structure(config.output_dir)

        # Map preset -> output folder
        folder_map = {
            "linkedin":    folders["linkedin"],
            "linkedin_hq": folders["linkedin"],
            "web":         folders["web"],
            "thumb":       folders["thumbs"],
            "print":       folders["print"],
        }

        # Export each image x each preset
        for page_idx, img in enumerate(images):
            page_num = page_idx + 1 if len(images) > 1 else 0

            for preset in presets:
                result = self._export_single(
                    img        = img,
                    topic      = topic,
                    preset     = preset,
                    page_num   = page_num,
                    output_dir = folder_map.get(preset.name, folders["root"]),
                    config     = config,
                )
                batch.add(result)
                status = "OK" if result.success else f"FAIL: {result.error}"
                self._log(f"  [{status}] {result.filename}  ({result.file_size_kb:.0f} KB)")

        # Save manifest
        if config.save_metadata:
            manifest_path = save_manifest(batch, folders["metadata"])
            self._log(f"  Manifest: {manifest_path}")

        batch.total_time_s = round(time.time() - t_start, 2)
        self._log(f"  Total time: {batch.total_time_s}s")

        if self.verbose:
            batch.print_summary()

        return batch

    def _export_single(self,
                        img:        Image.Image,
                        topic:      str,
                        preset:     ExportPreset,
                        page_num:   int,
                        output_dir: str,
                        config:     ExportConfig) -> ExportResult:
        """Export one image with one preset. Returns ExportResult."""
        t0 = time.time()

        try:
            ensure_dir(output_dir)

            # Generate filename
            ext      = preset.format.lower().replace("jpeg", "jpg")
            fname    = generate_filename(
                topic       = config.filename_prefix or topic,
                preset_name = preset.name,
                page_num    = page_num,
                suffix      = preset.suffix,
                extension   = ext,
                timestamp   = True,
            )
            fpath = resolve_output_path(output_dir, fname, config.overwrite)

            # Optimize
            img_data, stats = optimize_for_export(img.copy(), preset)

            # Write
            write_image_bytes(img_data, fpath)
            size_kb = get_file_size_kb(fpath)

            # Warn on large files
            if size_kb > WARN_SIZE_KB:
                self._log(f"  WARNING: {fname} is {size_kb:.0f} KB — may be slow to upload")

            return ExportResult(
                filepath      = fpath,
                filename      = os.path.basename(fpath),
                preset_name   = preset.name,
                format        = preset.format,
                width         = preset.width,
                height        = preset.height,
                file_size_kb  = size_kb,
                page_num      = page_num,
                export_time_s = round(time.time() - t0, 3),
                success       = True,
            )

        except Exception as e:
            return ExportResult(
                filepath      = "",
                filename      = f"FAILED_{preset.name}",
                preset_name   = preset.name,
                format        = preset.format,
                width         = preset.width,
                height        = preset.height,
                file_size_kb  = 0,
                page_num      = page_num,
                export_time_s = round(time.time() - t0, 3),
                success       = False,
                error         = str(e),
            )

    # ── Export from content dict (calls Phase 3 renderer) ─────────────────
    def export_from_content(self,
                             content:       dict,
                             config:        ExportConfig = None,
                             template_name: Optional[str] = None) -> ExportBatch:
        """
        Render infographic from Phase 1 content and export.

        Args:
            content       : Phase 1 content dict
            config        : ExportConfig
            template_name : Phase 3 template override

        Returns:
            ExportBatch
        """
        self._log("[ExportEngine] Rendering from content...")
        images = _render_content_to_images(content, template_name)
        self._log(f"[ExportEngine] Rendered {len(images)} page(s)")

        topic  = content.get("topic") or content.get("title", "infographic")
        return self.export_images(images, topic, config)

    # ── Validate all exports in a batch ───────────────────────────────────
    def validate_batch(self, batch: ExportBatch) -> dict:
        """
        Validate all exported files in a batch.

        Returns:
            dict with overall valid flag + per-file results
        """
        results  = {}
        all_valid = True

        for r in batch.results:
            if r.success and r.filepath:
                v = validate_exported_file(r.filepath, r.format)
                results[r.filename] = v
                if not v["valid"]:
                    all_valid = False

        return {
            "all_valid":    all_valid,
            "file_results": results,
        }


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def quick_export(img:        Union[Image.Image, List[Image.Image]],
                  topic:      str,
                  output_dir: str = "outputs",
                  presets:    List[str] = None,
                  verbose:    bool = True) -> List[str]:
    """
    Fast single-call export. Returns list of saved file paths.

    Args:
        img        : PIL Image or list of images
        topic      : topic string
        output_dir : base output directory
        presets    : preset names list (default: ["linkedin"])
        verbose    : print progress

    Returns:
        list of absolute file paths

    Example:
        paths = quick_export(my_img, "AI in Healthcare")
    """
    if isinstance(img, Image.Image):
        img = [img]

    config = ExportConfig(
        output_dir    = output_dir,
        presets       = presets or ["linkedin"],
        generate_thumb= True,
        save_metadata = True,
        verbose       = verbose,
    )
    engine = ExportEngine(verbose=verbose)
    batch  = engine.export_images(img, topic, config)
    return batch.all_paths


def export_all_presets(img:        Union[Image.Image, List[Image.Image]],
                        topic:      str,
                        output_dir: str = "outputs",
                        verbose:    bool = True) -> ExportBatch:
    """
    Export with ALL available presets in one call.

    Returns:
        ExportBatch
    """
    if isinstance(img, Image.Image):
        img = [img]

    config = ExportConfig(
        output_dir    = output_dir,
        presets       = list(PRESET_REGISTRY.keys()),
        generate_thumb= False,  # already in registry
        save_metadata = True,
        verbose       = verbose,
    )
    engine = ExportEngine(verbose=verbose)
    return engine.export_images(img, topic, config)


def export_from_content(content:       dict,
                         output_dir:    str = "outputs",
                         template_name: Optional[str] = None,
                         presets:       List[str] = None,
                         verbose:       bool = True) -> ExportBatch:
    """
    One-liner: render + export from Phase 1 content dict.

    Example:
        batch = export_from_content(content_dict, output_dir="my_outputs")
        print(batch.linkedin_paths)
    """
    config = ExportConfig(
        output_dir    = output_dir,
        presets       = presets or ["linkedin"],
        generate_thumb= True,
        save_metadata = True,
        verbose       = verbose,
    )
    engine = ExportEngine(verbose=verbose)
    return engine.export_from_content(content, config, template_name)
