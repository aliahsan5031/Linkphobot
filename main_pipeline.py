"""
main_pipeline.py
================
Linkphobot - Master Pipeline
Integrates all 10 phases into a single production-grade workflow.

PIPELINE FLOW:
  Topic (str)
    → Phase 1: Content Generation     (groq_client + content_generator)
    → Phase 4: Typography Resolution   (typography_engine)
    → Phase 5: Layout Planning         (layout_engine)
    → Phase 3: Infographic Rendering   (infographic_renderer)
    → Phase 6: Caption Generation      (caption_generator)
    → Phase 7: PNG Export              (export_engine)
    → Result:  PipelineResult (images + caption + paths)

CONNECTED FILES:
  Phase 1 → content_generator.py, groq_client.py, prompt_templates.py
  Phase 2 → infographic_structure_generator.py (optional layout JSON)
  Phase 3 → infographic_renderer.py, card_renderer.py, templates.py
  Phase 4 → typography_engine.py, font_scaling.py
  Phase 5 → layout_engine.py, section_balancer.py
  Phase 6 → caption_generator.py, hashtag_engine.py, seo_optimizer.py
  Phase 7 → export_engine.py, image_optimizer.py, file_manager.py
  Phase 8 → event_handlers.py (Gradio UI calls this pipeline)
  Phase 9 → app.py (HF Spaces runs this pipeline)

FIXED ISSUES:
  - P1 uses SYSTEM_PROMPT_CONTENT_GENERATOR; master re-exports as SYSTEM_PROMPT
  - P3 imports from same directory; master adds correct sys.path per phase
  - P6 CaptionGenerator needs content dict (not InfographicContent object)
  - P7 ExportEngine needs PIL Images list (not file paths)
  - Cross-phase sys.path conflicts resolved via PathManager
"""

import os
import sys
import json
import time
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Union
from PIL import Image


# ════════════════════════════════════════════════════════════════════════════
# PATH MANAGER  –  resolves all phase module paths
# ════════════════════════════════════════════════════════════════════════════

class PathManager:
    """
    Centralised path resolver for all phase modules.
    Searches multiple common locations (Colab, local dev, HF Spaces).
    """

    # Candidate root directories (searched in order)
    SEARCH_ROOTS = [
        "/content/linkphobot",          # Google Colab
        "/app",                          # HF Spaces Docker
        os.path.dirname(os.path.abspath(__file__)),   # script dir
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
    ]

    # Phase folder name patterns (handles "linkphobot P1", "phase1", etc.)
    PHASE_PATTERNS = {
        1:  ["linkphobot P1", "phase1", "p1", "Phase1"],
        2:  ["linkphobot P2", "phase2", "p2", "Phase2"],
        3:  ["linkphobot P3", "phase3", "p3", "Phase3"],
        4:  ["linkphobot P4", "phase4", "p4", "Phase4"],
        5:  ["linkphobot P5", "phase5", "p5", "Phase5"],
        6:  ["linkphobot P6", "phase6", "p6", "Phase6"],
        7:  ["linkphobot P7", "phase7", "p7", "Phase7"],
        8:  ["linkphobot P8", "phase8", "p8", "Phase8"],
        9:  ["linkphobot P9", "phase9", "p9", "Phase9"],
        10: ["linkphobot P10","phase10","p10","Phase10"],
    }

    _resolved: dict = {}  # cache: phase_num -> abs_path

    @classmethod
    def find_phase_dir(cls, phase_num: int) -> Optional[str]:
        """Return absolute path to a phase directory, or None if not found."""
        if phase_num in cls._resolved:
            return cls._resolved[phase_num]

        patterns = cls.PHASE_PATTERNS.get(phase_num, [])
        for root in cls.SEARCH_ROOTS:
            if not os.path.isdir(root):
                continue
            for pattern in patterns:
                candidate = os.path.join(root, pattern)
                if os.path.isdir(candidate):
                    cls._resolved[phase_num] = os.path.abspath(candidate)
                    return cls._resolved[phase_num]
            # Also check if modules sit directly in root (flat layout)
            probe_files = {
                1: "content_generator.py",
                3: "infographic_renderer.py",
                6: "caption_generator.py",
                7: "export_engine.py",
            }
            if phase_num in probe_files:
                if os.path.isfile(os.path.join(root, probe_files[phase_num])):
                    cls._resolved[phase_num] = os.path.abspath(root)
                    return cls._resolved[phase_num]

        return None

    @classmethod
    def inject(cls, phase_num: int) -> bool:
        """Add phase directory to sys.path. Returns True if successful."""
        path = cls.find_phase_dir(phase_num)
        if path and path not in sys.path:
            sys.path.insert(0, path)
            return True
        return bool(path)

    @classmethod
    def inject_all(cls, phases: List[int]) -> dict:
        """Inject multiple phases. Returns {phase: success} dict."""
        return {p: cls.inject(p) for p in phases}

    @classmethod
    def status_report(cls) -> str:
        """Return human-readable path resolution report."""
        lines = ["PathManager Status:"]
        for num in range(1, 11):
            path = cls.find_phase_dir(num)
            status = path if path else "NOT FOUND"
            lines.append(f"  Phase {num:2d}: {status}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# PIPELINE RESULT  –  output object returned to callers
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class PipelineResult:
    """
    Complete output from a single run of the master pipeline.
    Contains everything the caller (UI, API, Gradio) needs.
    """
    # Input
    topic:              str = ""

    # Phase 1 outputs
    content_dict:       dict = field(default_factory=dict)
    title:              str  = ""
    color_theme:        str  = ""
    content_type:       str  = ""

    # Phase 5 outputs
    layout_plan:        Optional[object] = None
    pages_count:        int = 1

    # Phase 3 outputs
    rendered_images:    List[Image.Image] = field(default_factory=list)

    # Phase 6 outputs
    linkedin_post:      str = ""
    caption_body:       str = ""
    hashtags:           List[str] = field(default_factory=list)
    seo_grade:          str = ""
    seo_score:          int = 0

    # Phase 7 outputs
    export_paths:       List[str] = field(default_factory=list)
    primary_image_path: str = ""

    # Pipeline metadata
    success:            bool  = False
    error:              str   = ""
    elapsed_total:      float = 0.0
    elapsed_by_phase:   dict  = field(default_factory=dict)
    generated_at:       str   = ""
    tokens_used:        int   = 0

    def to_dict(self) -> dict:
        """Serialisable summary (excludes PIL Image objects)."""
        return {
            "topic":            self.topic,
            "title":            self.title,
            "color_theme":      self.color_theme,
            "content_type":     self.content_type,
            "pages_count":      self.pages_count,
            "linkedin_post":    self.linkedin_post,
            "hashtags":         self.hashtags,
            "seo_grade":        self.seo_grade,
            "seo_score":        self.seo_score,
            "export_paths":     self.export_paths,
            "primary_image_path": self.primary_image_path,
            "success":          self.success,
            "error":            self.error,
            "elapsed_total":    self.elapsed_total,
            "elapsed_by_phase": self.elapsed_by_phase,
            "generated_at":     self.generated_at,
            "tokens_used":      self.tokens_used,
        }

    def print_summary(self):
        print("\n" + "=" * 60)
        print("  LINKPHOBOT PIPELINE RESULT")
        print("=" * 60)
        print(f"  Topic:       {self.topic}")
        print(f"  Title:       {self.title}")
        print(f"  Theme:       {self.color_theme}")
        print(f"  Pages:       {self.pages_count}")
        print(f"  SEO Grade:   {self.seo_grade} ({self.seo_score}/100)")
        print(f"  Tokens:      {self.tokens_used}")
        print(f"  Time:        {self.elapsed_total}s")
        print(f"  Success:     {self.success}")
        if self.export_paths:
            print(f"  Exports:     {len(self.export_paths)} file(s)")
            for p in self.export_paths:
                print(f"    -> {p}")
        if self.error:
            print(f"  Error:       {self.error}")
        print("=" * 60)


# ════════════════════════════════════════════════════════════════════════════
# PHASE RUNNERS  –  each phase wrapped in try/except with timing
# ════════════════════════════════════════════════════════════════════════════

def _run_phase1_content(topic: str,
                         model: str,
                         api_key: str,
                         verbose: bool) -> tuple:
    """
    Phase 1: Generate structured content from topic using Groq.

    Connects:
      groq_client.py         → API auth + completion
      prompt_templates.py    → SYSTEM_PROMPT_CONTENT_GENERATOR + build_content_prompt
      content_generator.py   → ContentGenerator class → InfographicContent

    Fix applied:
      prompt_templates.py exports SYSTEM_PROMPT_CONTENT_GENERATOR
      (not SYSTEM_PROMPT). We import by exact name.

    Returns:
      (content_dict: dict, tokens_used: int)
    """
    PathManager.inject(1)

    # Set API key before importing (groq_client reads from env at import time)
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key

    from content_generator import ContentGenerator

    gen     = ContentGenerator(model=model, verbose=verbose)
    content = gen.generate(topic)

    return content.to_dict(), content.tokens_used


def _run_phase4_typography(content_dict: dict, verbose: bool) -> dict:
    """
    Phase 4: Resolve font sizes across all content elements.

    Connects:
      text_measurement.py  → pixel-accurate measurement
      font_scaling.py      → dynamic size resolution + density scaling
      typography_engine.py → TypographyEngine.resolve_all()

    Output: dict of {element_type: {size, weight}}
    This dict is passed to Phase 3 renderer to override default sizes.
    """
    PathManager.inject(4)

    from typography_engine import TypographyEngine

    engine   = TypographyEngine(content=content_dict)
    resolved = engine.resolve_all()
    report   = engine.overflow_report()

    if verbose:
        print(f"    Typography: {len(resolved)} elements resolved | "
              f"overflow_risk={report.get('overflow_risk','?')}")

    return resolved


def _run_phase5_layout(content_dict: dict, verbose: bool) -> object:
    """
    Phase 5: Compute pixel-accurate layout plan for all blocks.

    Connects:
      coordinate_system.py  → Rect, Point, collision detection
      grid_system.py        → 12-column grid
      auto_spacing_engine.py→ dynamic gap calculator
      section_balancer.py   → weight-based height allocation
      layout_engine.py      → LayoutEngine → LayoutPlan

    Output: LayoutPlan object (pages, blocks, Rects)
    Phase 3 renderer uses block positions from this plan.
    """
    PathManager.inject(5)

    from layout_engine import generate_layout_plan

    plan = generate_layout_plan(content_dict, verbose=False)

    if verbose:
        print(f"    Layout: {plan.total_pages} page(s) | "
              f"{len(plan.pages[0].blocks)} blocks on page 1")

    return plan


def _run_phase3_render(content_dict: dict,
                        template_name: Optional[str],
                        output_dir: str,
                        verbose: bool) -> List[Image.Image]:
    """
    Phase 3: Render infographic PNG images from content.

    Connects:
      font_loader.py         → font discovery + caching
      templates.py           → business/educational/technical templates
      renderer.py            → draw_title(), draw_card(), draw_icon()
      card_renderer.py       → render_header_card(), render_section_card()
      icon_renderer.py       → draw_icon_circle(), draw_brand_strip()
      infographic_renderer.py→ render_infographic() → list of PNG paths

    Fix applied:
      P3 files all import from same directory.
      PathManager.inject(3) adds the correct dir to sys.path so
      all P3 relative imports resolve correctly.

    Returns:
      list of PIL Image objects (one per carousel page)
    """
    PathManager.inject(3)

    from infographic_renderer import render_infographic

    os.makedirs(output_dir, exist_ok=True)

    paths = render_infographic(
        content       = content_dict,
        template_name = template_name,
        output_dir    = output_dir,
        verbose       = verbose,
    )

    images = []
    for p in paths:
        try:
            images.append(Image.open(p).copy())
        except Exception as e:
            if verbose:
                print(f"    Warning: could not open {p}: {e}")

    if verbose:
        print(f"    Rendered: {len(images)} page(s)")

    return images


def _run_phase6_caption(content_dict: dict,
                         caption_style: str,
                         use_ai: bool,
                         verbose: bool) -> tuple:
    """
    Phase 6: Generate LinkedIn caption, hashtags, SEO analysis.

    Connects:
      linkedin_prompt_templates.py → SYSTEM_PROMPT_CAPTION + build_caption_prompt
      hashtag_engine.py            → rule-based + AI hashtag generation
      seo_optimizer.py             → score_caption_seo + generate_seo_report
      caption_generator.py         → CaptionGenerator → CaptionPackage

    Fix applied:
      CaptionGenerator.generate() expects content_dict (plain dict).
      We pass content_obj.to_dict() from Phase 1 — this is correct.

    Returns:
      (linkedin_post: str, seo_grade: str, seo_score: int, hashtags: list)
    """
    PathManager.inject(6)

    from caption_generator import CaptionGenerator

    gen = CaptionGenerator(style=caption_style, use_ai=use_ai, verbose=verbose)
    pkg = gen.generate(content_dict)

    return pkg.linkedin_post, pkg.seo_grade, pkg.seo_score, pkg.hashtags


def _run_phase7_export(images: List[Image.Image],
                        topic: str,
                        export_preset: str,
                        output_dir: str,
                        verbose: bool) -> List[str]:
    """
    Phase 7: Export PIL Images to optimized LinkedIn-ready PNG files.

    Connects:
      export_config.py   → ExportPreset definitions (linkedin/web/thumb/print)
      image_optimizer.py → resize, sharpen, PNG compression
      file_manager.py    → filename generator, folder builder, ExportBatch
      export_engine.py   → ExportEngine.export_images() → ExportBatch

    Fix applied:
      ExportEngine.export_images() expects List[PIL.Image], not file paths.
      We pass the rendered_images list directly from Phase 3.

    Returns:
      list of absolute paths to exported PNG files
    """
    PathManager.inject(7)

    from export_engine import ExportEngine
    from export_config import ExportConfig

    os.makedirs(output_dir, exist_ok=True)

    config = ExportConfig(
        output_dir     = output_dir,
        presets        = [export_preset],
        generate_thumb = True,
        save_metadata  = True,
        verbose        = verbose,
    )
    engine = ExportEngine(verbose=verbose)
    batch  = engine.export_images(images, topic, config)

    return batch.all_paths


# ════════════════════════════════════════════════════════════════════════════
# MASTER PIPELINE CLASS
# ════════════════════════════════════════════════════════════════════════════

class LinkphoBot:
    """
    Master Pipeline Orchestrator.

    Connects all 10 phases in correct order with proper
    inter-phase data handoff and error isolation.

    Usage:
        bot    = LinkphoBot(output_dir="outputs")
        result = bot.run("Artificial Intelligence in Healthcare")
        result.print_summary()

    One-liner:
        result = LinkphoBot().run("AI in Healthcare")
    """

    def __init__(self,
                 output_dir:     str  = "outputs",
                 model:          str  = "default",
                 template_name:  Optional[str] = None,
                 caption_style:  str  = "educational",
                 export_preset:  str  = "linkedin",
                 api_key:        str  = "",
                 use_caption_ai: bool = True,
                 verbose:        bool = True):
        """
        Args:
            output_dir    : base directory for all exported files
            model         : Groq model key ("fast","default","quality")
            template_name : Phase 3 template ("business","educational","technical",None=auto)
            caption_style : Phase 6 style ("educational","data_driven","thought_leadership","story","listicle")
            export_preset : Phase 7 preset ("linkedin","linkedin_hq","web","thumb")
            api_key       : Groq API key (uses env GROQ_API_KEY if blank)
            use_caption_ai: use Groq for caption generation (False=rule-based fallback)
            verbose       : print phase progress
        """
        self.output_dir      = output_dir
        self.model           = model
        self.template_name   = template_name
        self.caption_style   = caption_style
        self.export_preset   = export_preset
        self.api_key         = api_key or os.environ.get("GROQ_API_KEY","") or os.environ.get("Linkphobot_API","")
        self.use_caption_ai  = use_caption_ai
        self.verbose         = verbose

        # Try to load Colab secret if key still empty
        if not self.api_key:
            try:
                from google.colab import userdata
                self.api_key = (userdata.get("GROQ_API_KEY")
                                or userdata.get("Linkphobot_API")
                                or "")
            except Exception:
                pass

        if self.api_key:
            os.environ["GROQ_API_KEY"] = self.api_key

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _time_phase(self, name: str, fn, result: PipelineResult):
        """Run a phase function with timing. Returns fn() return value."""
        t0 = time.time()
        out = fn()
        elapsed = round(time.time() - t0, 2)
        result.elapsed_by_phase[name] = elapsed
        self._log(f"  [{elapsed:5.1f}s] {name}")
        return out

    def run(self, topic: str) -> PipelineResult:
        """
        Execute the full pipeline for a given topic.

        Args:
            topic: Any professional subject string

        Returns:
            PipelineResult with all outputs populated
        """
        topic  = topic.strip()
        result = PipelineResult(
            topic        = topic,
            generated_at = datetime.now().isoformat(),
        )

        if not topic or len(topic) < 3:
            result.error = "Topic too short (min 3 characters)"
            return result

        if not self.api_key:
            result.error = "GROQ_API_KEY not set. Pass api_key= or set env var."
            return result

        t_total = time.time()
        self._log(f"\n{'='*60}")
        self._log(f"  LINKPHOBOT MASTER PIPELINE")
        self._log(f"  Topic: {topic}")
        self._log(f"{'='*60}")

        # ── Phase 1: Content Generation ───────────────────────────────
        self._log("\n[Phase 1] Generating content with Groq AI...")
        try:
            content_dict, tokens = self._time_phase(
                "Phase 1: Content",
                lambda: _run_phase1_content(
                    topic, self.model, self.api_key, self.verbose
                ),
                result,
            )
            result.content_dict  = content_dict
            result.title         = content_dict.get("title", "")
            result.color_theme   = content_dict.get("color_theme", "professional")
            result.content_type  = content_dict.get("content_type", "educational")
            result.tokens_used   = tokens
            self._log(f"    Title: {result.title}")
            self._log(f"    Theme: {result.color_theme}")
        except Exception as e:
            result.error = f"Phase 1 failed: {e}\n{traceback.format_exc()[-400:]}"
            result.elapsed_total = round(time.time() - t_total, 2)
            return result

        # ── Phase 4: Typography Resolution ───────────────────────────
        self._log("\n[Phase 4] Resolving typography scales...")
        try:
            typo_map = self._time_phase(
                "Phase 4: Typography",
                lambda: _run_phase4_typography(result.content_dict, self.verbose),
                result,
            )
            # Attach to content_dict so Phase 3 can use it
            result.content_dict["_typography"] = typo_map
        except Exception as e:
            # Typography failure is non-fatal — Phase 3 has its own defaults
            self._log(f"    [Warning] Phase 4 non-fatal error: {e}")
            result.elapsed_by_phase["Phase 4: Typography"] = 0.0

        # ── Phase 5: Layout Planning ──────────────────────────────────
        self._log("\n[Phase 5] Computing layout plan...")
        try:
            layout_plan = self._time_phase(
                "Phase 5: Layout",
                lambda: _run_phase5_layout(result.content_dict, self.verbose),
                result,
            )
            result.layout_plan  = layout_plan
            result.pages_count  = layout_plan.total_pages
        except Exception as e:
            self._log(f"    [Warning] Phase 5 non-fatal error: {e}")
            result.pages_count  = 1
            result.elapsed_by_phase["Phase 5: Layout"] = 0.0

        # ── Phase 3: Rendering ────────────────────────────────────────
        self._log("\n[Phase 3] Rendering infographic PNG(s)...")
        render_dir = os.path.join(self.output_dir, "_render_tmp")
        try:
            images = self._time_phase(
                "Phase 3: Render",
                lambda: _run_phase3_render(
                    result.content_dict,
                    self.template_name,
                    render_dir,
                    self.verbose,
                ),
                result,
            )
            result.rendered_images = images
            if not images:
                raise RuntimeError("Renderer returned 0 images")
        except Exception as e:
            result.error = f"Phase 3 failed: {e}\n{traceback.format_exc()[-400:]}"
            result.elapsed_total = round(time.time() - t_total, 2)
            return result

        # ── Phase 6: Caption Generation ───────────────────────────────
        self._log("\n[Phase 6] Generating LinkedIn caption...")
        try:
            post, grade, score, tags = self._time_phase(
                "Phase 6: Caption",
                lambda: _run_phase6_caption(
                    result.content_dict,
                    self.caption_style,
                    self.use_caption_ai,
                    self.verbose,
                ),
                result,
            )
            result.linkedin_post = post
            result.seo_grade     = grade
            result.seo_score     = score
            result.hashtags      = tags
            self._log(f"    SEO: {grade} ({score}/100) | Words: {len(post.split())}")
        except Exception as e:
            # Caption failure is non-fatal — use Phase 1 caption
            self._log(f"    [Warning] Phase 6 non-fatal error: {e}")
            fallback_cap = result.content_dict.get("linkedin_caption","")
            fallback_tags = " ".join(result.content_dict.get("hashtags",[]))
            result.linkedin_post = f"{fallback_cap}\n\n{fallback_tags}"
            result.seo_grade     = "N/A"
            result.seo_score     = 0
            result.elapsed_by_phase["Phase 6: Caption"] = 0.0

        # ── Phase 7: Export ───────────────────────────────────────────
        self._log("\n[Phase 7] Exporting LinkedIn-ready PNG(s)...")
        export_dir = os.path.join(self.output_dir, "exports")
        try:
            paths = self._time_phase(
                "Phase 7: Export",
                lambda: _run_phase7_export(
                    result.rendered_images,
                    topic,
                    self.export_preset,
                    export_dir,
                    self.verbose,
                ),
                result,
            )
            result.export_paths       = paths
            result.primary_image_path = paths[0] if paths else ""
            self._log(f"    Exported: {len(paths)} file(s)")
        except Exception as e:
            # Export failure is non-fatal — images still in result.rendered_images
            self._log(f"    [Warning] Phase 7 non-fatal error: {e}")
            # Save directly from PIL as fallback
            try:
                fb_path = os.path.join(self.output_dir, "infographic_fallback.png")
                os.makedirs(self.output_dir, exist_ok=True)
                result.rendered_images[0].save(fb_path, "PNG")
                result.export_paths       = [fb_path]
                result.primary_image_path = fb_path
                self._log(f"    Fallback saved: {fb_path}")
            except Exception:
                pass
            result.elapsed_by_phase["Phase 7: Export"] = 0.0

        # ── Final ──────────────────────────────────────────────────────
        result.elapsed_total = round(time.time() - t_total, 2)
        result.success       = True

        self._log(f"\n{'='*60}")
        self._log(f"  PIPELINE COMPLETE in {result.elapsed_total}s")
        self._log(f"{'='*60}\n")

        return result

    def run_batch(self, topics: List[str],
                   delay_between: float = 2.0) -> List[PipelineResult]:
        """
        Run the pipeline for multiple topics sequentially.

        Args:
            topics         : list of topic strings
            delay_between  : seconds to wait between runs (API rate limiting)

        Returns:
            list of PipelineResult objects
        """
        results = []
        for i, topic in enumerate(topics, 1):
            self._log(f"\n[Batch {i}/{len(topics)}] {topic}")
            result = self.run(topic)
            results.append(result)
            if i < len(topics):
                time.sleep(delay_between)
        return results


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION  –  single-call API
# ════════════════════════════════════════════════════════════════════════════

def generate_infographic(
    topic:          str,
    output_dir:     str  = "outputs",
    model:          str  = "default",
    template_name:  Optional[str] = None,
    caption_style:  str  = "educational",
    export_preset:  str  = "linkedin",
    api_key:        str  = "",
    verbose:        bool = True,
) -> PipelineResult:
    """
    One-liner entry point. Creates LinkphoBot and runs full pipeline.

    Args:
        topic         : professional topic string
        output_dir    : base output directory
        model         : Groq model ("fast","default","quality")
        template_name : visual template (None=auto, "business","educational","technical")
        caption_style : caption tone ("educational","data_driven","thought_leadership","story","listicle")
        export_preset : export format ("linkedin","linkedin_hq","web","thumb")
        api_key       : Groq API key (uses GROQ_API_KEY env var if blank)
        verbose       : print progress

    Returns:
        PipelineResult

    Example:
        from main_pipeline import generate_infographic

        result = generate_infographic(
            topic      = "AI in Healthcare",
            output_dir = "my_outputs",
        )
        print(result.linkedin_post)
        result.rendered_images[0].save("preview.png")
    """
    bot = LinkphoBot(
        output_dir     = output_dir,
        model          = model,
        template_name  = template_name,
        caption_style  = caption_style,
        export_preset  = export_preset,
        api_key        = api_key,
        verbose        = verbose,
    )
    result = bot.run(topic)
    if verbose:
        result.print_summary()
    return result


# ════════════════════════════════════════════════════════════════════════════
# GRADIO INTEGRATION HELPER
# (called by Phase 8 event_handlers.py)
# ════════════════════════════════════════════════════════════════════════════

def run_for_gradio(topic:          str,
                    template_name:  str  = "auto",
                    color_theme:    str  = "auto",
                    caption_style:  str  = "educational",
                    export_preset:  str  = "linkedin",
                    model:          str  = "default",
                    groq_api_key:   str  = "") -> tuple:
    """
    Wrapper for Phase 8 Gradio UI event_handlers.py.

    Maps Gradio component values → pipeline → Gradio outputs.

    Returns:
        (status_str, pil_image, caption_str, seo_str, dl_path, json_str, meta_str)
    """
    def ts(msg): return f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"

    topic = (topic or "").strip()
    if len(topic) < 3:
        return (ts("Error: topic too short"), None, "", "", None, "{}", "")

    # Apply color theme override before running
    result = generate_infographic(
        topic         = topic,
        output_dir    = "outputs",
        model         = model,
        template_name = None if template_name == "auto" else template_name,
        caption_style = caption_style,
        export_preset = export_preset,
        api_key       = groq_api_key,
        verbose       = True,
    )

    # Apply manual color theme override if set
    if color_theme and color_theme != "auto" and result.content_dict:
        result.content_dict["color_theme"] = color_theme

    if not result.success:
        return (ts(f"Error: {result.error[:80]}"),
                None, "", "", None, "{}", "")

    image    = result.rendered_images[0] if result.rendered_images else None
    dl_path  = result.primary_image_path or None
    json_str = json.dumps(
        {k: v for k, v in result.content_dict.items() if not k.startswith("_")},
        indent=2, ensure_ascii=False
    )[:4000]

    meta = (
        f"Topic:    {result.topic}\n"
        f"Title:    {result.title}\n"
        f"Theme:    {result.color_theme}\n"
        f"Pages:    {result.pages_count}\n"
        f"Tokens:   {result.tokens_used}\n"
        f"Time:     {result.elapsed_total}s\n"
        f"SEO:      {result.seo_grade} ({result.seo_score}/100)\n"
        f"Generated:{result.generated_at}"
    )

    return (
        ts(f"Done in {result.elapsed_total}s — {result.title[:50]}"),
        image,
        result.linkedin_post,
        f"SEO: {result.seo_grade} ({result.seo_score}/100) | Words: {len(result.linkedin_post.split())}",
        dl_path,
        json_str,
        meta,
    )


# ════════════════════════════════════════════════════════════════════════════
# CLI  –  run directly
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Linkphobot Master Pipeline")
    parser.add_argument("topic",           type=str,                  help="Infographic topic")
    parser.add_argument("--output-dir",    type=str, default="outputs",help="Output directory")
    parser.add_argument("--model",         type=str, default="default",help="Groq model key")
    parser.add_argument("--template",      type=str, default=None,     help="Template name")
    parser.add_argument("--caption-style", type=str, default="educational")
    parser.add_argument("--export-preset", type=str, default="linkedin")
    parser.add_argument("--api-key",       type=str, default="",       help="Groq API key")
    parser.add_argument("--paths",         action="store_true",        help="Show path status")
    args = parser.parse_args()

    if args.paths:
        print(PathManager.status_report())
        sys.exit(0)

    result = generate_infographic(
        topic         = args.topic,
        output_dir    = args.output_dir,
        model         = args.model,
        template_name = args.template,
        caption_style = args.caption_style,
        export_preset = args.export_preset,
        api_key       = args.api_key,
    )
    sys.exit(0 if result.success else 1)
