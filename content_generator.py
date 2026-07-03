"""
content_generator.py
====================
Linkphobot - Phase 1: Content Generator
Main Orchestration Module

Responsibilities:
- Accept topic input
- Call Groq API via groq_client
- Parse and validate JSON response
- Apply fallback/repair logic for malformed JSON
- Return clean structured InfographicContent object
- Save output to JSON file
- Display rich preview in terminal / Colab
"""

import json
import re
import os
import time
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from groq_client import groq_complete, create_groq_client, GROQ_MODELS
from prompt_templates import (
    SYSTEM_PROMPT_CONTENT_GENERATOR,
    build_content_prompt,
)

# ── Try rich for pretty terminal output ────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


# ════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class InfographicSection:
    heading: str
    icon_suggestion: str
    content: list[str]


@dataclass
class Statistic:
    value: str
    label: str
    context: str


@dataclass
class InfographicContent:
    """
    Fully structured infographic content object.
    Matches the JSON schema defined in prompt_templates.py
    """
    title: str
    subtitle: str
    topic_summary: str
    sections: list[InfographicSection]
    key_points: list[str]
    statistics: list[Statistic]
    call_to_action: str
    linkedin_caption: str
    hashtags: list[str]
    color_theme: str
    target_audience: str
    content_type: str
    reading_time_seconds: int

    # Metadata added by the generator (not from LLM)
    topic: str = ""
    generated_at: str = ""
    model_used: str = ""
    tokens_used: int = 0
    generation_time_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════════════
# JSON REPAIR UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def _extract_json_from_text(text: str) -> str:
    """
    Extract JSON object from text that may contain surrounding prose.
    Handles cases where the LLM wraps JSON in markdown code blocks.
    """
    # Strip markdown code blocks (```json ... ``` or ``` ... ```)
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)

    # Find the outermost { ... } block
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM response.")

    # Walk through and find the matching closing brace
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError("Malformed JSON: unbalanced braces in LLM response.")


def _repair_json(raw: str) -> dict:
    """
    Attempt to parse JSON with progressive repair strategies:
    1. Direct parse
    2. Strip surrounding text, then parse
    3. Raise clear error with raw snippet

    Returns:
        Parsed dict

    Raises:
        ValueError with helpful context
    """
    # Strategy 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract JSON block
    try:
        extracted = _extract_json_from_text(raw)
        return json.loads(extracted)
    except (ValueError, json.JSONDecodeError):
        pass

    # Strategy 3: fail with context
    snippet = raw[:300].replace("\n", " ")
    raise ValueError(
        f"[Linkphobot] ❌  Could not parse LLM response as JSON.\n"
        f"Response snippet: {snippet}…\n"
        "Try running again — the model may have returned malformed output."
    )


# ════════════════════════════════════════════════════════════════════════════
# VALIDATION & DEFAULTS
# ════════════════════════════════════════════════════════════════════════════

VALID_CONTENT_TYPES = {"educational", "how-to", "statistics", "framework", "comparison", "listicle"}

VALID_COLOR_THEMES = {
    "tech_purple", "dev_dark", "finance_navy", "health_blue", "eco_green",
    "executive_navy", "creative_coral", "engineering_navy", "data_indigo",
    "clean_blue", "edu_teal", "people_warm", "cyber_dark", "professional",
}

def _validate_and_fill(data: dict, topic: str) -> dict:
    """
    Validate parsed JSON and fill missing/invalid fields with safe defaults.
    Ensures the object always has all required keys.
    """
    data.setdefault("title", f"{topic}: A Complete Guide")
    data.setdefault("subtitle", f"Everything professionals need to know about {topic}")
    data.setdefault("topic_summary", f"{topic} is an important concept in modern professional practice.")
    data.setdefault("sections", [])
    data.setdefault("key_points", ["Deep understanding leads to better outcomes",
                                   "Consistent practice builds expertise",
                                   "Collaboration accelerates results"])
    data.setdefault("statistics", [])
    data.setdefault("call_to_action", "Save this post and share with your network.")
    data.setdefault("linkedin_caption", f"Great insights on {topic}. Save this for later.")
    data.setdefault("hashtags", [f"#{topic.replace(' ', '')}", "#LinkedIn", "#Learning"])
    data.setdefault("color_theme", "professional")
    data.setdefault("target_audience", "Professionals looking to grow their expertise")
    data.setdefault("reading_time_seconds", 20)

    # Validate content_type
    if data.get("content_type") not in VALID_CONTENT_TYPES:
        data["content_type"] = "educational"

    # Validate color_theme
    if data.get("color_theme") not in VALID_COLOR_THEMES:
        data["color_theme"] = "professional"

    # Ensure sections have required fields
    cleaned_sections = []
    for sec in data.get("sections", []):
        if isinstance(sec, dict):
            cleaned_sections.append({
                "heading":          sec.get("heading", "Key Insights"),
                "icon_suggestion":  sec.get("icon_suggestion", "📌"),
                "content":          sec.get("content", [])[:6],  # cap at 6 bullets
            })
    data["sections"] = cleaned_sections

    # Ensure statistics have required fields
    cleaned_stats = []
    for stat in data.get("statistics", []):
        if isinstance(stat, dict) and stat.get("value"):
            cleaned_stats.append({
                "value":   stat.get("value", ""),
                "label":   stat.get("label", ""),
                "context": stat.get("context", ""),
            })
    data["statistics"] = cleaned_stats

    # Cap hashtags
    data["hashtags"] = data["hashtags"][:10]

    return data


# ════════════════════════════════════════════════════════════════════════════
# MAIN GENERATOR CLASS
# ════════════════════════════════════════════════════════════════════════════

class ContentGenerator:
    """
    Phase 1 Content Generator.

    Usage:
        generator = ContentGenerator()
        content   = generator.generate("Artificial Intelligence in Healthcare")
        generator.save(content, "output.json")
        generator.preview(content)
    """

    def __init__(
        self,
        model: str = "default",
        temperature: float = 0.72,
        max_tokens: int = 4096,
        verbose: bool = True,
    ):
        """
        Initialize the content generator.

        Args:
            model       : Model key from GROQ_MODELS dict (or full model string)
            temperature : LLM creativity setting
            max_tokens  : Max response tokens
            verbose     : Print progress to console
        """
        self.model_key   = model
        self.model       = GROQ_MODELS.get(model, model)
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.verbose     = verbose
        self.client      = None  # Lazy init to avoid key error at import time

    def _get_client(self):
        """Lazy-initialize Groq client."""
        if self.client is None:
            self.client = create_groq_client()
        return self.client

    def _log(self, msg: str, style: str = ""):
        """Print progress message if verbose."""
        if not self.verbose:
            return
        if RICH_AVAILABLE and console:
            console.print(f"[{style}]{msg}[/{style}]" if style else msg)
        else:
            print(msg)

    def generate(self, topic: str) -> InfographicContent:
        """
        Generate complete infographic content for a given topic.

        Args:
            topic: The subject matter (e.g., "Machine Learning", "Leadership")

        Returns:
            InfographicContent dataclass with all fields populated

        Raises:
            RuntimeError: on API failure after retries
            ValueError:   on JSON parsing failure
        """
        self._log(f"\n🚀  [bold cyan]Linkphobot[/bold cyan] — Generating content for: [bold yellow]{topic}[/bold yellow]", "")
        self._log("─" * 60)

        # ── Step 1: Build prompt ────────────────────────────────────────
        self._log("📝  Building prompt…", "dim")
        user_prompt = build_content_prompt(topic)

        # ── Step 2: Call Groq ───────────────────────────────────────────
        self._log(f"🧠  Calling Groq [{self.model}]…", "dim")
        t0 = time.time()
        result = groq_complete(
            prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT_CONTENT_GENERATOR,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            client=self._get_client(),
        )
        elapsed = round(time.time() - t0, 2)
        self._log(f"✅  Response received in {elapsed}s  |  Tokens: {result['usage']['total_tokens']}", "green")

        # ── Step 3: Parse JSON ──────────────────────────────────────────
        self._log("🔍  Parsing JSON response…", "dim")
        raw_data = _repair_json(result["content"])

        # ── Step 4: Validate and fill defaults ──────────────────────────
        self._log("🛡️   Validating structure…", "dim")
        clean_data = _validate_and_fill(raw_data, topic)

        # ── Step 5: Build typed objects ─────────────────────────────────
        sections = [
            InfographicSection(
                heading=s["heading"],
                icon_suggestion=s["icon_suggestion"],
                content=s["content"],
            )
            for s in clean_data["sections"]
        ]

        statistics = [
            Statistic(
                value=s["value"],
                label=s["label"],
                context=s["context"],
            )
            for s in clean_data["statistics"]
        ]

        content_obj = InfographicContent(
            title=clean_data["title"],
            subtitle=clean_data["subtitle"],
            topic_summary=clean_data["topic_summary"],
            sections=sections,
            key_points=clean_data["key_points"],
            statistics=statistics,
            call_to_action=clean_data["call_to_action"],
            linkedin_caption=clean_data["linkedin_caption"],
            hashtags=clean_data["hashtags"],
            color_theme=clean_data["color_theme"],
            target_audience=clean_data["target_audience"],
            content_type=clean_data["content_type"],
            reading_time_seconds=clean_data.get("reading_time_seconds", 20),
            # Metadata
            topic=topic,
            generated_at=datetime.now().isoformat(),
            model_used=result["model"],
            tokens_used=result["usage"]["total_tokens"],
            generation_time_seconds=elapsed,
        )

        self._log(f"\n✨  Content generated successfully!", "bold green")
        return content_obj

    def save(
        self,
        content: InfographicContent,
        filepath: Optional[str] = None,
        output_dir: str = "outputs",
    ) -> str:
        """
        Save InfographicContent to a JSON file.

        Args:
            content    : The generated InfographicContent object
            filepath   : Full path to save file (auto-generated if None)
            output_dir : Directory to save in if filepath not specified

        Returns:
            Absolute path to saved file
        """
        if filepath is None:
            os.makedirs(output_dir, exist_ok=True)
            safe_topic = re.sub(r"[^\w\s-]", "", content.topic).strip().replace(" ", "_")[:40]
            timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath   = os.path.join(output_dir, f"{safe_topic}_{timestamp}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.to_json())

        self._log(f"💾  Saved to: [bold]{filepath}[/bold]", "")
        return os.path.abspath(filepath)

    def preview(self, content: InfographicContent):
        """
        Print a rich preview of the generated content to the terminal / Colab.
        Falls back to plain print if Rich is not available.
        """
        if RICH_AVAILABLE and console:
            self._rich_preview(content)
        else:
            self._plain_preview(content)

    def _rich_preview(self, content: InfographicContent):
        """Rich-formatted terminal preview."""
        console.print()
        console.rule("[bold cyan]LINKPHOBOT — GENERATED CONTENT PREVIEW[/bold cyan]")

        # Title block
        console.print(Panel(
            f"[bold white]{content.title}[/bold white]\n[dim]{content.subtitle}[/dim]",
            title="📋 Infographic",
            border_style="cyan",
        ))

        # Metadata
        meta_table = Table(show_header=False, box=None, padding=(0, 2))
        meta_table.add_column("Key", style="dim")
        meta_table.add_column("Value", style="yellow")
        meta_table.add_row("Topic",         content.topic)
        meta_table.add_row("Content Type",  content.content_type)
        meta_table.add_row("Color Theme",   content.color_theme)
        meta_table.add_row("Audience",      content.target_audience)
        meta_table.add_row("Model",         content.model_used)
        meta_table.add_row("Tokens Used",   str(content.tokens_used))
        meta_table.add_row("Generated At",  content.generated_at[:19])
        console.print(Panel(meta_table, title="📊 Metadata", border_style="blue"))

        # Topic Summary
        console.print(Panel(
            content.topic_summary,
            title="📖 Topic Summary",
            border_style="green",
        ))

        # Sections
        for i, sec in enumerate(content.sections, 1):
            bullets = "\n".join(f"  • {c}" for c in sec.content)
            console.print(Panel(
                bullets,
                title=f"{sec.icon_suggestion} Section {i}: {sec.heading}",
                border_style="magenta",
            ))

        # Key Points
        kp_text = "\n".join(f"⚡ {kp}" for kp in content.key_points)
        console.print(Panel(kp_text, title="🔑 Key Points", border_style="yellow"))

        # Statistics
        if content.statistics:
            stat_table = Table(show_header=True, header_style="bold white")
            stat_table.add_column("Value",   style="bold cyan",  width=12)
            stat_table.add_column("Label",   style="white",      width=30)
            stat_table.add_column("Context", style="dim",        width=40)
            for stat in content.statistics:
                stat_table.add_row(stat.value, stat.label, stat.context)
            console.print(Panel(stat_table, title="📈 Statistics", border_style="cyan"))

        # Hashtags
        tags = "  ".join(content.hashtags)
        console.print(Panel(tags, title="🏷️  Hashtags", border_style="blue"))

        # Caption
        console.print(Panel(
            content.linkedin_caption,
            title="✍️  LinkedIn Caption",
            border_style="green",
        ))

        # CTA
        console.print(Panel(
            f"[bold]{content.call_to_action}[/bold]",
            title="📣 Call To Action",
            border_style="red",
        ))
        console.rule()

    def _plain_preview(self, content: InfographicContent):
        """Plain text fallback preview."""
        sep = "=" * 60
        print(f"\n{sep}")
        print(f" LINKPHOBOT — CONTENT PREVIEW")
        print(sep)
        print(f"TITLE:    {content.title}")
        print(f"SUBTITLE: {content.subtitle}")
        print(f"THEME:    {content.color_theme}")
        print(f"TYPE:     {content.content_type}")
        print()
        for i, sec in enumerate(content.sections, 1):
            print(f"[{i}] {sec.icon_suggestion} {sec.heading}")
            for bullet in sec.content:
                print(f"   • {bullet}")
        print()
        print("KEY POINTS:")
        for kp in content.key_points:
            print(f"  ⚡ {kp}")
        print()
        print("HASHTAGS:", " ".join(content.hashtags))
        print()
        print("CAPTION:")
        print(content.linkedin_caption)
        print(sep)


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION  –  One-line generation
# ════════════════════════════════════════════════════════════════════════════

def generate_content(
    topic: str,
    model: str = "default",
    save: bool = True,
    preview: bool = True,
    output_dir: str = "outputs",
) -> InfographicContent:
    """
    Convenience wrapper: generate, optionally save & preview in one call.

    Args:
        topic      : Topic string
        model      : Model key ("fast", "default", "quality")
        save       : Whether to save JSON to disk
        preview    : Whether to print terminal preview
        output_dir : Directory for saved JSON files

    Returns:
        InfographicContent object

    Example:
        content = generate_content("Machine Learning in Healthcare")
    """
    gen = ContentGenerator(model=model)
    content = gen.generate(topic)

    if save:
        gen.save(content, output_dir=output_dir)

    if preview:
        gen.preview(content)

    return content


# ════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT  –  Direct script run
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Artificial Intelligence in Business"
    content = generate_content(topic)
