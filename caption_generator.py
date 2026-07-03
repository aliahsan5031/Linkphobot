"""
caption_generator.py
====================
Linkphobot - Phase 6: LinkedIn Caption Generator
Main Orchestrator

Pipeline:
  1. Accept Phase 1 content dict
  2. Generate caption via Groq LLM
  3. Generate hashtags (AI or rule-based)
  4. Run SEO analysis
  5. Return CaptionPackage with everything
  6. Save to JSON

Public API:
  CaptionGenerator.generate(content)  -> CaptionPackage
  generate_caption(content)           -> CaptionPackage  (one-liner)
"""

import os
import sys
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from linkedin_prompt_templates import (
    SYSTEM_PROMPT_CAPTION, CAPTION_STYLES,
    build_caption_prompt, build_hashtag_prompt,
)
from hashtag_engine import (
    generate_hashtags_rule_based,
    generate_hashtags_ai,
    format_hashtags_for_linkedin,
    score_hashtag_set,
)
from seo_optimizer import (
    score_caption_seo,
    optimize_caption_text,
    compute_readability,
    generate_seo_report,
)


# ════════════════════════════════════════════════════════════════════════════
# GROQ CLIENT LOADER
# ════════════════════════════════════════════════════════════════════════════

def _load_groq_client():
    import importlib.util
    for path in [
        os.path.join(os.path.dirname(__file__), ".."),
        "/content/linkphobot",
        "/tmp/linkphobot",
    ]:
        fp = os.path.join(path, "groq_client.py")
        if os.path.isfile(fp):
            spec = importlib.util.spec_from_file_location("groq_client", fp)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.create_groq_client(), mod
    raise RuntimeError(
        "groq_client.py not found. Run Phase 1 cell first to write it to disk."
    )


def _groq_complete(client, prompt: str, system: str,
                    model: str = "llama-3.3-70b-versatile",
                    temperature: float = 0.72,
                    max_tokens: int = 1200) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    response = client.chat.completions.create(
        model=model, messages=messages,
        temperature=temperature, max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _parse_json_response(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```\s*$",          "", raw, flags=re.MULTILINE)
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    return json.loads(raw)


# ════════════════════════════════════════════════════════════════════════════
# CAPTION PACKAGE  –  output object
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class CaptionPackage:
    topic:            str
    title:            str
    style:            str

    # Caption components
    hook:             str = ""
    caption_body:     str = ""
    full_caption:     str = ""
    cta_line:         str = ""
    hook_type:        str = ""

    # Hashtags
    hashtags:         List[str] = field(default_factory=list)
    hashtag_string:   str = ""
    hashtag_strategy: str = ""

    # Final post-ready text
    linkedin_post:    str = ""     # full_caption + blank line + hashtag_string

    # Analytics
    word_count:       int = 0
    readability:      str = ""
    seo_score:        int = 0
    seo_grade:        str = ""
    emotional_triggers: List[str] = field(default_factory=list)
    best_posting_time:  str = ""
    content_format_tip: str = ""

    # Meta
    generated_at:     str = ""
    model_used:       str = ""
    generation_time:  float = 0.0
    caption_source:   str = ""   # "ai" or "fallback"
    hashtag_source:   str = ""   # "ai" or "rule_based"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def print_preview(self):
        sep = "=" * 60
        print(f"\n{sep}")
        print(" LINKPHOBOT - CAPTION PREVIEW")
        print(sep)
        print(f"Topic:      {self.topic}")
        print(f"Style:      {self.style}")
        print(f"SEO Grade:  {self.seo_grade}  ({self.seo_score}/100)")
        print(f"Words:      {self.word_count}")
        print(f"Readability:{self.readability}")
        print()
        print("--- LINKEDIN POST (copy-paste ready) ---")
        print(self.linkedin_post)
        print(sep)


# ════════════════════════════════════════════════════════════════════════════
# FALLBACK CAPTION BUILDER  –  no API needed
# ════════════════════════════════════════════════════════════════════════════

def _build_fallback_caption(content: dict, style: str = "educational") -> dict:
    topic      = content.get("topic") or content.get("title", "this topic")
    title      = content.get("title", "")
    sections   = content.get("sections", [])
    key_points = content.get("key_points", [])
    statistics = content.get("statistics", [])
    cta        = content.get("call_to_action", "Save this post and share it.")
    audience   = content.get("target_audience", "professionals")

    # Hook
    if statistics:
        stat = statistics[0]
        hook = f"{stat.get('value', '')} — {stat.get('label', title)}"
    else:
        hook = f"Most {audience} still don't fully understand {topic}."

    # Body paragraphs from key points
    body_lines = []
    if key_points:
        for kp in key_points[:3]:
            body_lines.append(kp)
        body = "\n\n".join(body_lines)
    elif sections:
        for sec in sections[:3]:
            bullets = sec.get("content", [])
            if bullets:
                body_lines.append(bullets[0])
        body = "\n\n".join(body_lines)
    else:
        body = f"Understanding {topic} is one of the most valuable skills you can develop."

    body = (
        f"Here is what every professional needs to know:\n\n"
        f"{body}\n\n"
        f"The professionals who invest time understanding {topic} "
        f"will have a significant edge in the years ahead."
    )

    cta_line = cta if cta else "Save this post — you will want to refer back to it."

    full = f"{hook}\n\n{body}\n\n{cta_line}"

    return {
        "hook":               hook,
        "caption_body":       body,
        "full_caption":       full,
        "cta_line":           cta_line,
        "hook_type":          "stat" if statistics else "bold_claim",
        "word_count":         len(full.split()),
        "readability_score":  "medium",
        "emotional_triggers": ["curiosity", "authority", "urgency"],
        "best_posting_time":  "Morning (7-9am)",
        "content_format_tip": "Pair with a clean infographic for maximum engagement.",
    }


# ════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR CLASS
# ════════════════════════════════════════════════════════════════════════════

class CaptionGenerator:
    """
    Phase 6 LinkedIn Caption Generator.

    Usage:
        gen     = CaptionGenerator()
        package = gen.generate(content_dict)
        package.print_preview()
        gen.save(package, "caption.json")
    """

    def __init__(self,
                 model:       str   = "llama-3.3-70b-versatile",
                 style:       str   = "educational",
                 use_ai:      bool  = True,
                 verbose:     bool  = True):
        self.model   = model
        self.style   = style
        self.use_ai  = use_ai
        self.verbose = verbose
        self._client = None
        self._gc_mod = None

    def _log(self, msg: str):
        if self.verbose:
            print(msg)

    def _get_client(self):
        if self._client is None and self.use_ai:
            try:
                self._client, self._gc_mod = _load_groq_client()
            except Exception as e:
                self._log(f"[Caption] Groq client unavailable: {e}. Using fallback.")
                self.use_ai = False
        return self._client

    def generate(self, content: dict) -> CaptionPackage:
        import time
        t0 = time.time()

        topic        = content.get("topic") or content.get("title", "")
        title        = content.get("title", "")
        key_points   = content.get("key_points", [])
        statistics   = content.get("statistics", [])
        hashtags_p1  = content.get("hashtags", [])
        content_type = content.get("content_type", "educational")
        style        = self.style

        self._log(f"\n[Caption Generator] Topic: {topic[:50]}")
        self._log(f"  Style:  {style}")
        self._log(f"  AI:     {self.use_ai}")

        # ── Step 1: Generate caption ──────────────────────────────────
        caption_data   = None
        caption_source = "fallback"

        if self.use_ai:
            client = self._get_client()
            if client:
                try:
                    self._log("  Calling Groq for caption...")
                    prompt   = build_caption_prompt(content, style)
                    raw      = _groq_complete(client, prompt,
                                              SYSTEM_PROMPT_CAPTION,
                                              self.model)
                    caption_data   = _parse_json_response(raw)
                    caption_source = "ai"
                    self._log("  Caption generated via AI")
                except Exception as e:
                    self._log(f"  Caption AI failed: {e}. Using fallback.")

        if caption_data is None:
            caption_data   = _build_fallback_caption(content, style)
            caption_source = "fallback"
            self._log("  Caption generated via fallback template")

        # ── Step 2: Generate hashtags ─────────────────────────────────
        hashtag_data   = None
        hashtag_source = "rule_based"

        if self.use_ai and self._client:
            try:
                self._log("  Calling Groq for hashtags...")
                hashtag_data   = generate_hashtags_ai(
                    topic, content_type, key_points, self._client, self.model
                )
                hashtag_source = hashtag_data.get("source", "ai_generated")
                self._log("  Hashtags generated via AI")
            except Exception as e:
                self._log(f"  Hashtag AI failed: {e}. Using rule-based.")

        if hashtag_data is None:
            hashtag_data   = generate_hashtags_rule_based(topic, content_type)
            hashtag_source = "rule_based"
            self._log("  Hashtags generated via rule-based engine")

        # Merge with Phase 1 hashtags if available
        ai_tags = hashtag_data.get("full_set", [])
        all_tags = list(dict.fromkeys(ai_tags + hashtags_p1))[:8]
        hashtag_data["full_set"]       = all_tags
        hashtag_data["hashtag_string"] = " ".join(all_tags)

        # ── Step 3: Optimise caption ──────────────────────────────────
        full_caption = caption_data.get("full_caption", "")
        full_caption = optimize_caption_text(full_caption, topic)

        # ── Step 4: Build linkedin_post ───────────────────────────────
        tag_string   = hashtag_data.get("hashtag_string", "")
        linkedin_post = f"{full_caption}\n\n{tag_string}"

        # ── Step 5: SEO analysis ──────────────────────────────────────
        seo_report = generate_seo_report(full_caption, topic, all_tags)
        readable   = compute_readability(full_caption)

        elapsed = round(time.time() - t0, 2)

        pkg = CaptionPackage(
            topic             = topic,
            title             = title,
            style             = style,
            hook              = caption_data.get("hook", ""),
            caption_body      = caption_data.get("caption_body", ""),
            full_caption      = full_caption,
            cta_line          = caption_data.get("cta_line", ""),
            hook_type         = caption_data.get("hook_type", ""),
            hashtags          = all_tags,
            hashtag_string    = tag_string,
            hashtag_strategy  = hashtag_data.get("strategy_note", ""),
            linkedin_post     = linkedin_post,
            word_count        = len(full_caption.split()),
            readability       = readable.get("level", "medium"),
            seo_score         = seo_report.get("overall_score", 0),
            seo_grade         = seo_report.get("grade", "B"),
            emotional_triggers= caption_data.get("emotional_triggers", []),
            best_posting_time = caption_data.get("best_posting_time", "Morning (7-9am)"),
            content_format_tip= caption_data.get("content_format_tip", ""),
            generated_at      = datetime.now().isoformat(),
            model_used        = self.model if caption_source == "ai" else "fallback",
            generation_time   = elapsed,
            caption_source    = caption_source,
            hashtag_source    = hashtag_source,
        )

        self._log(f"  Done in {elapsed}s | SEO: {pkg.seo_grade} ({pkg.seo_score}/100) | Words: {pkg.word_count}")
        return pkg

    def generate_all_styles(self, content: dict) -> Dict[str, CaptionPackage]:
        """Generate captions in all 5 styles for A/B testing."""
        results = {}
        for style_key in CAPTION_STYLES:
            self._log(f"\nGenerating style: {style_key}")
            self.style = style_key
            results[style_key] = self.generate(content)
        return results

    def save(self, package: CaptionPackage,
             filepath: Optional[str] = None,
             output_dir: str = "outputs") -> str:
        if filepath is None:
            os.makedirs(output_dir, exist_ok=True)
            safe = re.sub(r"[^\w]", "_", package.topic)[:36].lower()
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(output_dir, f"{safe}_caption_{ts}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(package.to_json())
        self._log(f"Saved: {filepath}")
        return filepath


# ════════════════════════════════════════════════════════════════════════════
# ONE-LINER
# ════════════════════════════════════════════════════════════════════════════

def generate_caption(content: dict,
                     style:   str  = "educational",
                     use_ai:  bool = True,
                     save:    bool = True,
                     output_dir: str = "outputs",
                     verbose: bool = True) -> CaptionPackage:
    gen = CaptionGenerator(style=style, use_ai=use_ai, verbose=verbose)
    pkg = gen.generate(content)
    if save:
        gen.save(pkg, output_dir=output_dir)
    if verbose:
        pkg.print_preview()
    return pkg
