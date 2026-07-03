"""
app.py
======
Linkphobot — Production App
LinkedIn Infographic Generator powered by Groq + Llama 3.3 + PIL

Entry point for:
  - Hugging Face Spaces  (SDK: gradio, sdk_version: 3.50.2)
  - Google Colab         (share=True auto-detected)
  - Local development    (python app.py)

Architecture:
  app.py
    ↓ imports
  main_pipeline.py          ← master pipeline (PathManager + phase runners)
    ↓ calls phases
  linkphobot P1/            ← content generation (Groq API)
  linkphobot P3/            ← PIL rendering
  linkphobot P4/            ← typography
  linkphobot P5/            ← layout
  linkphobot P6/            ← caption generation
  linkphobot P7/            ← PNG export

Environment variables:
  GROQ_API_KEY     : Groq API key (required)
  LINKPHOBOT_PORT  : server port (default 7860)
  LINKPHOBOT_SHARE : "true" for Gradio public URL
"""

# ════════════════════════════════════════════════════════════════════════════
# STDLIB
# ════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import time
import tempfile
import traceback
from datetime import datetime
from typing import Optional, Tuple, List

# ════════════════════════════════════════════════════════════════════════════
# THIRD-PARTY
# ════════════════════════════════════════════════════════════════════════════

from PIL import Image, ImageDraw, ImageFont
import gradio as gr

# ════════════════════════════════════════════════════════════════════════════
# PATH SETUP
# Ensures main_pipeline.py and all phase folders can be found
# regardless of whether we're on Colab, HF Spaces, or local
# ════════════════════════════════════════════════════════════════════════════

_APP_DIR  = os.path.dirname(os.path.abspath(__file__))
_ROOTS    = [
    _APP_DIR,
    os.path.join(_APP_DIR, ".."),
    "/content/linkphobot",    # Google Colab
    "/app",                   # HF Spaces Docker container
]
for _r in _ROOTS:
    if os.path.isdir(_r) and _r not in sys.path:
        sys.path.insert(0, _r)


# ════════════════════════════════════════════════════════════════════════════
# API KEY LOADER
# ════════════════════════════════════════════════════════════════════════════

def _load_api_key(user_provided: str = "") -> str:
    """
    Resolve Groq API key from (in order of priority):
      1. User input field in the UI
      2. GROQ_API_KEY environment variable
      3. Linkphobot_API environment variable  (legacy secret name)
      4. Google Colab secrets (GROQ_API_KEY or Linkphobot_API)

    Returns the key string, or "" if not found.
    """
    # 1. User typed it in the UI
    if user_provided and user_provided.strip():
        key = user_provided.strip()
        os.environ["GROQ_API_KEY"] = key
        return key

    # 2. Environment variable
    key = os.environ.get("GROQ_API_KEY", "") or os.environ.get("Linkphobot_API", "")
    if key:
        os.environ["GROQ_API_KEY"] = key
        return key

    # 3. Colab secrets
    try:
        from google.colab import userdata
        key = userdata.get("GROQ_API_KEY") or userdata.get("Linkphobot_API") or ""
        if key:
            os.environ["GROQ_API_KEY"] = key
            return key
    except Exception:
        pass

    return ""


# ════════════════════════════════════════════════════════════════════════════
# PIPELINE LOADER
# Loads main_pipeline.py from disk — works across all environments
# ════════════════════════════════════════════════════════════════════════════

_pipeline_module = None   # cached after first load

def _get_pipeline():
    """
    Lazy-load main_pipeline.py. Searches common locations.
    Returns the module object, or None if not found.
    """
    global _pipeline_module
    if _pipeline_module is not None:
        return _pipeline_module

    import importlib.util

    search_paths = [
        os.path.join(_APP_DIR, "main_pipeline.py"),
        "/content/linkphobot/main_pipeline.py",
        "/app/main_pipeline.py",
        os.path.join(_APP_DIR, "..", "main_pipeline.py"),
    ]

    for path in search_paths:
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("main_pipeline", path)
            mod  = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                _pipeline_module = mod
                print(f"[Linkphobot] Pipeline loaded from: {path}")
                return _pipeline_module
            except Exception as e:
                print(f"[Linkphobot] Failed to load {path}: {e}")
                continue

    return None


# ════════════════════════════════════════════════════════════════════════════
# PLACEHOLDER IMAGE RENDERER
# Used when Phase 3 renderer fails or pipeline is unavailable
# ════════════════════════════════════════════════════════════════════════════

def _make_placeholder(content: dict) -> Image.Image:
    """
    Create a clean branded placeholder infographic using PIL only.
    No external dependencies — always works as fallback.
    """
    PALETTES = {
        "tech_purple":    ("#0D0D1A", "#6C3FC5", "#00D4FF"),
        "health_blue":    ("#EBF8FF", "#0077B6", "#F4A261"),
        "finance_navy":   ("#F8F9FA", "#0A2342", "#F7C948"),
        "executive_navy": ("#FAFBFF", "#1A1F36", "#FF6B35"),
        "eco_green":      ("#F0FFF4", "#1B4332", "#95D5B2"),
        "data_indigo":    ("#FAF8FF", "#3C1053", "#FFB347"),
        "engineering_navy":("#F5F5F5","#0A192F","#64FFDA"),
        "cyber_dark":     ("#0A0A0A", "#111111", "#00FF41"),
        "clean_blue":     ("#F8FAFC", "#2563EB", "#FBBF24"),
        "edu_teal":       ("#FFF8F0", "#004E64", "#F4A261"),
        "creative_coral": ("#FFFBF0", "#FF4E50", "#F9D423"),
        "dev_dark":       ("#11111B", "#89B4FA", "#A6E3A1"),
        "people_warm":    ("#FFFAF5", "#B5451B", "#FFD166"),
        "professional":   ("#FAFBFF", "#1E3A5F", "#FF6B35"),
    }

    theme       = content.get("color_theme", "professional")
    bg, pri, acc = PALETTES.get(theme, PALETTES["professional"])
    W, H        = 1080, 1350

    def h2r(h):
        h = h.lstrip("#")
        return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # ── Header gradient ───────────────────────────────────────────────────
    r1,g1,b1 = h2r(pri)
    r2,g2,b2 = h2r(acc) if theme in ("tech_purple","eco_green","cyber_dark") else (46,109,164)
    for y in range(390):
        t = y / 390
        draw.line([(0,y),(W,y)],
                  fill=(int(r1+(r2-r1)*t*0.45), int(g1+(g2-g1)*t*0.45), int(b1+(b2-b1)*t*0.45)))

    # ── Load fonts ────────────────────────────────────────────────────────
    def _font(sz, bold=False):
        paths = [
            f"/content/linkphobot/linkphobot P3/fonts/Inter-{'ExtraBold' if bold else 'Regular'}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        ]
        for p in paths:
            if os.path.isfile(p):
                try: return ImageFont.truetype(p, sz)
                except Exception: pass
        return ImageFont.load_default()

    f_title = _font(52, bold=True)
    f_sub   = _font(24)
    f_head  = _font(26, bold=True)
    f_body  = _font(21)
    f_small = _font(17)
    f_badge = _font(15, bold=True)

    def _tw(txt, fnt):
        try: return fnt.getbbox(txt)[2]
        except: return len(txt) * (fnt.size // 2 if hasattr(fnt,'size') else 8)

    def _center(txt, fnt, y_pos, fill=(255,255,255)):
        draw.text(((W - _tw(txt, fnt)) // 2, y_pos), txt, font=fnt, fill=fill)

    # ── Content type badge ────────────────────────────────────────────────
    badge   = content.get("content_type", "educational").upper()
    acc_rgb = h2r(acc)
    bw      = _tw(badge, f_badge) + 32
    draw.rounded_rectangle([(W-bw)//2, 42, (W+bw)//2, 78], radius=18, fill=acc_rgb)
    draw.text(((W - _tw(badge, f_badge)) // 2, 50), badge, font=f_badge, fill=(255,255,255))

    # ── Title ─────────────────────────────────────────────────────────────
    title = content.get("title", "Linkphobot Infographic")[:55]
    _center(title, f_title, 104)
    subtitle = content.get("subtitle", "")[:72]
    _center(subtitle, f_sub, 174, fill=h2r("#CBD5E0"))

    # ── Section cards ─────────────────────────────────────────────────────
    sections  = content.get("sections", [])
    pri_rgb   = h2r(pri)
    txt_rgb   = h2r("#1E3A5F") if bg not in ("#0D0D1A","#0A0A0A","#11111B") else h2r("#E2E8F0")
    card_bg   = "#FFFFFF" if bg not in ("#FFFFFF","#F8F9FA","#FAFBFF","#F5F5F5","#EBF8FF","#FFF8F0","#FFFBF0","#FFFAF5","#FAF8FF","#F8FAFC","#F0FFF4") else "#EEF4FF"

    cy = 410
    for i, sec in enumerate(sections[:4]):
        alt_bg = card_bg if i % 2 == 0 else (
            "#EEF4FF" if bg not in ("#0D0D1A","#0A0A0A","#11111B") else "#1A1A2E"
        )
        draw.rounded_rectangle([54, cy, 1026, cy+148], radius=14, fill=alt_bg)
        draw.rounded_rectangle([54, cy+10, 61, cy+138], radius=4, fill=acc_rgb)

        icon    = sec.get("icon_suggestion","")
        heading = (icon + " " + sec.get("heading",""))[:44]
        draw.text((80, cy+16), heading, font=f_head, fill=pri_rgb if bg not in ("#0D0D1A","#0A0A0A") else h2r("#89B4FA"))

        bullets = sec.get("content",[])[:2]
        by = cy + 60
        for b in bullets:
            draw.ellipse([80, by+8, 89, by+17], fill=acc_rgb)
            draw.text((100, by), b[:62], font=f_body, fill=txt_rgb)
            by += 34
        cy += 162

    # ── Key points strip ──────────────────────────────────────────────────
    kps = content.get("key_points", [])[:3]
    if kps:
        strip_y = cy + 6
        draw.rounded_rectangle([54, strip_y, 1026, strip_y+116], radius=12, fill=pri_rgb)
        kp_x = 80
        for kp in kps:
            draw.ellipse([kp_x, strip_y+18, kp_x+8, strip_y+26], fill=acc_rgb)
            draw.text((kp_x+14, strip_y+12), kp[:45], font=f_small, fill=(255,255,255))
            kp_x += 316
        cy = strip_y + 116

    # ── Statistics ────────────────────────────────────────────────────────
    stats = content.get("statistics",[])[:3]
    if stats:
        st_y = cy + 14
        n    = len(stats)
        sw   = (972 - 12*(n-1)) // n
        sx   = 54
        stat_card = "#EEF4FF" if bg not in ("#0D0D1A","#0A0A0A","#11111B") else "#1A1A2E"
        for stat in stats:
            draw.rounded_rectangle([sx, st_y, sx+sw, st_y+110], radius=12, fill=stat_card)
            draw.rounded_rectangle([sx, st_y, sx+sw, st_y+5], radius=3, fill=acc_rgb)
            val = stat.get("value","")
            vw  = _tw(val, f_head)
            draw.text((sx+(sw-vw)//2, st_y+14), val, font=f_head, fill=acc_rgb)
            lbl = stat.get("label","")[:30]
            lw  = _tw(lbl, f_small)
            draw.text((sx+(sw-lw)//2, st_y+60), lbl, font=f_small, fill=txt_rgb)
            sx += sw + 12
        cy = st_y + 110

    # ── Footer ────────────────────────────────────────────────────────────
    foot_y = H - 106
    draw.line([(54, foot_y), (1026, foot_y)], fill=h2r("#E2E8F0"), width=1)
    cta = content.get("call_to_action","Save this post and share it with your network.")[:68]
    draw.text(((W - _tw(cta, f_body)) // 2, foot_y+8), cta, font=f_body, fill=pri_rgb)
    tags = " ".join(content.get("hashtags",[])[:5])
    draw.text(((W - _tw(tags, f_small)) // 2, foot_y+46), tags, font=f_small, fill=h2r("#718096"))
    brand = "Linkphobot  |  AI-Powered LinkedIn Infographics"
    draw.text(((W - _tw(brand, f_small)) // 2, H-28), brand, font=f_small, fill=h2r("#A0AEC0"))

    return img


# ════════════════════════════════════════════════════════════════════════════
# MAIN GENERATE HANDLER
# Called by every Gradio button / textbox submit event
# ════════════════════════════════════════════════════════════════════════════

def generate_infographic(
    topic:          str,
    template_name:  str  = "auto",
    color_theme:    str  = "auto",
    caption_style:  str  = "educational",
    export_preset:  str  = "linkedin",
    model:          str  = "default",
    groq_api_key:   str  = "",
) -> Tuple:
    """
    Full pipeline handler.

    Args:
        topic         : user's topic string
        template_name : "auto" | "business" | "educational" | "technical"
        color_theme   : "auto" | any VALID_COLOR_THEMES value
        caption_style : "educational" | "data_driven" | "thought_leadership" | "story" | "listicle"
        export_preset : "linkedin" | "linkedin_hq" | "web" | "thumb"
        model         : "default" | "fast" | "quality"
        groq_api_key  : optional key override from UI

    Returns:
        7-tuple matching Gradio OUTPUTS:
        (status_str, pil_image, caption_str, seo_str, download_path, json_str, metadata_str)
    """

    # ── Helper ────────────────────────────────────────────────────────────
    def _ts(msg: str) -> str:
        return f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"

    EMPTY = (_ts("Ready"), None, "", "", None, "{}", "")

    # ── Validate topic ────────────────────────────────────────────────────
    topic = (topic or "").strip()
    if len(topic) < 3:
        return (_ts("Please enter a topic (minimum 3 characters)"),
                None, "", "", None, "{}", "")

    # ── Resolve API key ───────────────────────────────────────────────────
    api_key = _load_api_key(groq_api_key)
    if not api_key:
        return (
            _ts("Error: GROQ_API_KEY not found. "
                "Add it to HF Secrets / Colab Secrets, or paste it above."),
            None, "", "", None, "{}", ""
        )

    t_start = time.time()
    print(f"\n[Linkphobot] Topic: {topic}")

    # ── Load pipeline ─────────────────────────────────────────────────────
    pipeline = _get_pipeline()

    if pipeline is None:
        return (
            _ts("Error: main_pipeline.py not found. "
                "Ensure it is in the same folder as app.py."),
            None, "", "", None, "{}", ""
        )

    # ── Run pipeline ──────────────────────────────────────────────────────
    try:
        bot = pipeline.LinkphoBot(
            output_dir     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs"),
            model          = model,
            template_name  = None if template_name == "auto" else template_name,
            caption_style  = caption_style,
            export_preset  = export_preset,
            api_key        = api_key,
            use_caption_ai = True,
            verbose        = True,
        )
        result = bot.run(topic)

    except Exception as e:
        tb  = traceback.format_exc()
        msg = f"Pipeline error: {str(e)}"
        print(f"[Linkphobot] ERROR:\n{tb}")
        return (_ts(msg), None, msg, "", None, "{}", f"Error:\n{str(e)}\n\n{tb[-400:]}")

    # ── Handle pipeline failure ───────────────────────────────────────────
    if not result.success:
        return (
            _ts(f"Error: {result.error[:100]}"),
            None,
            f"Generation failed:\n{result.error}",
            "", None, "{}", result.error
        )

    # ── Apply manual color theme override ─────────────────────────────────
    # (pipeline auto-detects theme from topic; user can override here)
    if color_theme and color_theme != "auto":
        result.content_dict["color_theme"] = color_theme

    # ── Get output image ──────────────────────────────────────────────────
    # Priority: pipeline rendered images → placeholder fallback
    if result.rendered_images:
        image_out = result.rendered_images[0]
    else:
        print("[Linkphobot] No rendered images — using placeholder")
        image_out = _make_placeholder(result.content_dict)

    # ── Get download path ─────────────────────────────────────────────────
    # Priority: exported PNG from Phase 7 → save image directly
    download_path = result.primary_image_path or ""
    if not download_path or not os.path.isfile(download_path):
        try:
            tmp_path = tempfile.mktemp(suffix=".png", prefix="linkphobot_")
            image_out.save(tmp_path, "PNG", optimize=True, compress_level=6)
            download_path = tmp_path
        except Exception as e:
            print(f"[Linkphobot] Warning: could not save PNG: {e}")
            download_path = ""

    # ── Caption ───────────────────────────────────────────────────────────
    caption = result.linkedin_post
    if not caption:
        # Fallback from Phase 1 content
        raw_cap = result.content_dict.get("linkedin_caption","")
        tags    = " ".join(result.content_dict.get("hashtags",[]))
        caption = f"{raw_cap}\n\n{tags}"

    # ── SEO info line ─────────────────────────────────────────────────────
    seo_info = ""
    if result.seo_grade:
        seo_info = (
            f"SEO Grade: {result.seo_grade}  ({result.seo_score}/100)  |  "
            f"Words: {len(caption.split())}  |  "
            f"Pages: {result.pages_count}  |  "
            f"Tokens: {result.tokens_used}"
        )

    # ── JSON content ──────────────────────────────────────────────────────
    json_str = json.dumps(
        {k: v for k, v in result.content_dict.items() if not k.startswith("_")},
        indent=2, ensure_ascii=False
    )[:5000]

    # ── Metadata ──────────────────────────────────────────────────────────
    elapsed  = round(time.time() - t_start, 1)
    metadata = (
        f"Topic:        {topic}\n"
        f"Title:        {result.title}\n"
        f"Theme:        {result.color_theme}\n"
        f"Content type: {result.content_type}\n"
        f"Pages:        {result.pages_count}\n"
        f"Template:     {template_name}\n"
        f"Model:        {model}\n"
        f"Caption style:{caption_style}\n"
        f"Tokens used:  {result.tokens_used}\n"
        f"Generated in: {elapsed}s\n"
        f"Phase timings:\n"
        + "\n".join(f"  {k}: {v}s" for k, v in result.elapsed_by_phase.items())
        + f"\nGenerated at: {result.generated_at}"
    )

    status = _ts(
        f"Done in {elapsed}s  |  {result.title[:45]}  |  "
        f"SEO: {result.seo_grade or 'N/A'}"
    )
    print(f"[Linkphobot] {status}")

    return (
        status,
        image_out,
        caption,
        seo_info,
        download_path if download_path and os.path.isfile(download_path) else None,
        json_str,
        metadata,
    )


def clear_outputs() -> Tuple:
    """Reset all UI output components to initial empty state."""
    return (
        f"[{datetime.now().strftime('%H:%M:%S')}] Ready — enter a topic and click Generate",
        None,   # image
        "",     # caption
        "",     # seo
        None,   # download
        "{}",   # json
        "",     # metadata
    )


def check_system_status(groq_api_key: str = "") -> str:
    """Check which components are available and return status string."""
    api_key = _load_api_key(groq_api_key)
    pipeline = _get_pipeline()

    lines = ["System Status:\n"]

    lines.append(f"  [{'OK  ' if api_key else 'MISS'}] GROQ_API_KEY")
    lines.append(f"  [{'OK  ' if pipeline else 'MISS'}] main_pipeline.py")

    if pipeline:
        pm = getattr(pipeline, "PathManager", None)
        if pm:
            for phase_num in [1, 3, 4, 5, 6, 7]:
                found = pm.find_phase_dir(phase_num)
                lines.append(f"  [{'OK  ' if found else 'MISS'}] Phase {phase_num}")

    lines.append("")
    if not api_key:
        lines.append("  Add GROQ_API_KEY to HF Secrets or paste it in Advanced Settings")
    if not pipeline:
        lines.append("  main_pipeline.py not found — ensure it is in the same folder as app.py")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════════
# UI CONSTANTS
# ════════════════════════════════════════════════════════════════════════════

CSS = """
/* ── Global ─────────────────────────────────────────── */
.gradio-container {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    max-width: 1200px !important;
    margin: auto !important;
}

/* ── Header ─────────────────────────────────────────── */
#linkphobot-header {
    background: linear-gradient(135deg, #1E3A5F 0%, #2E6DA4 55%, #FF6B35 100%);
    border-radius: 14px;
    padding: 26px 36px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 6px 24px rgba(30,58,95,0.35);
}
#linkphobot-header h1 {
    color: #FFFFFF !important;
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    margin: 0 0 4px 0 !important;
    letter-spacing: -0.5px;
}
#linkphobot-header p {
    color: #CBD5E0 !important;
    font-size: 0.93rem !important;
    margin: 0 !important;
}

/* ── Generate button ─────────────────────────────────── */
#generate-btn {
    background: linear-gradient(135deg, #FF6B35, #E85A25) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 14px !important;
    width: 100% !important;
    box-shadow: 0 4px 14px rgba(255,107,53,0.4) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
#generate-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(255,107,53,0.55) !important;
}

/* ── Caption text area ───────────────────────────────── */
#caption-out textarea {
    font-size: 0.9rem !important;
    line-height: 1.65 !important;
}

/* ── Status box ──────────────────────────────────────── */
#status-box textarea {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}

/* ── Example buttons ─────────────────────────────────── */
.example-btn {
    font-size: 0.82rem !important;
    padding: 6px 10px !important;
    border-radius: 6px !important;
}

/* ── Footer ──────────────────────────────────────────── */
#linkphobot-footer {
    text-align: center;
    color: #718096;
    font-size: 0.78rem;
    padding: 14px;
    margin-top: 6px;
    border-top: 1px solid #E2E8F0;
}
"""

HEADER_HTML = """
<div id="linkphobot-header">
    <h1>🤖 Linkphobot</h1>
    <p>AI-Powered LinkedIn Infographic Generator &nbsp;·&nbsp; Groq + Llama 3.3 + PIL &nbsp;·&nbsp; v1.0.0</p>
</div>
"""

FOOTER_HTML = """
<div id="linkphobot-footer">
    Built with <strong>Linkphobot</strong> &nbsp;·&nbsp;
    Powered by <strong>Groq</strong> + <strong>Llama 3.3 70B</strong> + <strong>Pillow</strong> &nbsp;·&nbsp;
    <a href="https://console.groq.com/keys" target="_blank" style="color:#718096">Get Groq API Key →</a>
</div>
"""

TEMPLATE_CHOICES = ["auto", "business", "educational", "technical"]

COLOR_THEME_CHOICES = [
    "auto",
    "tech_purple",
    "health_blue",
    "finance_navy",
    "executive_navy",
    "eco_green",
    "data_indigo",
    "engineering_navy",
    "cyber_dark",
    "clean_blue",
    "edu_teal",
    "creative_coral",
    "dev_dark",
    "people_warm",
    "professional",
]

CAPTION_STYLE_CHOICES = [
    "educational",
    "data_driven",
    "thought_leadership",
    "story",
    "listicle",
]

EXPORT_PRESET_CHOICES = [
    "linkedin",
    "linkedin_hq",
    "web",
    "thumb",
]

MODEL_CHOICES = ["default", "fast", "quality"]

EXAMPLE_TOPICS = [
    "Artificial Intelligence in Healthcare",
    "Top 10 Leadership Skills for 2025",
    "How to Build a Personal Brand on LinkedIn",
    "Machine Learning for Beginners",
    "The Future of Remote Work",
    "Data Science Career Roadmap 2025",
    "Habits of High-Performance Teams",
    "Python vs JavaScript: Which to Learn First",
    "The Rise of Generative AI in Business",
    "Blockchain Technology Explained Simply",
]


# ════════════════════════════════════════════════════════════════════════════
# GRADIO INTERFACE BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_interface() -> gr.Blocks:
    """
    Build and return the complete Gradio Blocks interface.

    Layout:
      Header
      ┌────────────────┬──────────────────────────────┐
      │ Controls (40%) │ Outputs (60%)                │
      │                │  Status bar                  │
      │  Topic input   │  Tabs:                       │
      │  Examples      │    [Infographic] [Caption]   │
      │  Template      │    [JSON]        [Info]      │
      │  Theme         │                              │
      │  Caption style │                              │
      │  [Generate]    │                              │
      │  [Clear]       │                              │
      └────────────────┴──────────────────────────────┘
      Footer
    """
    with gr.Blocks(
        css   = CSS,
        title = "Linkphobot — LinkedIn Infographic Generator",
    ) as demo:

        # ── Header ────────────────────────────────────────────────────
        gr.HTML(HEADER_HTML)

        # ── Main Row ──────────────────────────────────────────────────
        with gr.Row(equal_height=False):

            # ════════════════════════════════════════════════════════════
            # LEFT COLUMN — Controls
            # ════════════════════════════════════════════════════════════
            with gr.Column(scale=4, min_width=320):

                # ── Topic input ───────────────────────────────────────
                topic_input = gr.Textbox(
                    label       = "Topic",
                    placeholder = "e.g. Artificial Intelligence in Healthcare",
                    lines       = 2,
                    max_lines   = 5,
                    info        = "Be specific for best results — longer = better content",
                    elem_id     = "topic-input",
                )

                # ── Quick example buttons ─────────────────────────────
                gr.Markdown("**Quick start — click any topic:**")
                with gr.Row():
                    ex_btn = [gr.Button(t[:36]+"..." if len(t)>36 else t,
                                        size="sm", variant="secondary",
                                        elem_classes=["example-btn"])
                              for t in EXAMPLE_TOPICS[:2]]
                with gr.Row():
                    ex_btn += [gr.Button(t[:36]+"..." if len(t)>36 else t,
                                         size="sm", variant="secondary",
                                         elem_classes=["example-btn"])
                               for t in EXAMPLE_TOPICS[2:4]]
                with gr.Row():
                    ex_btn += [gr.Button(t[:36]+"..." if len(t)>36 else t,
                                         size="sm", variant="secondary",
                                         elem_classes=["example-btn"])
                               for t in EXAMPLE_TOPICS[4:6]]

                gr.HTML("<hr style='border-color:#E2E8F0;margin:14px 0'>")

                # ── Design settings ───────────────────────────────────
                gr.Markdown("### Design Settings")

                template_dd = gr.Dropdown(
                    choices = TEMPLATE_CHOICES,
                    value   = "auto",
                    label   = "Template Style",
                    info    = "auto = selected based on topic domain",
                )

                color_theme_dd = gr.Dropdown(
                    choices = COLOR_THEME_CHOICES,
                    value   = "auto",
                    label   = "Color Theme",
                    info    = "auto = detected from topic keywords",
                )

                caption_style_dd = gr.Dropdown(
                    choices = CAPTION_STYLE_CHOICES,
                    value   = "educational",
                    label   = "Caption Style",
                    info    = "Tone and structure of the LinkedIn post",
                )

                gr.HTML("<hr style='border-color:#E2E8F0;margin:14px 0'>")

                # ── Advanced settings (collapsed) ─────────────────────
                with gr.Accordion("Advanced Settings", open=False):
                    export_preset_dd = gr.Dropdown(
                        choices = EXPORT_PRESET_CHOICES,
                        value   = "linkedin",
                        label   = "Export Preset",
                        info    = "linkedin = 1080x1350 PNG (recommended)",
                    )
                    model_dd = gr.Dropdown(
                        choices = MODEL_CHOICES,
                        value   = "default",
                        label   = "AI Model",
                        info    = "default = llama-3.3-70b (recommended)",
                    )
                    api_key_input = gr.Textbox(
                        label       = "Groq API Key (optional)",
                        placeholder = "gsk_... leave blank if set in Secrets",
                        type        = "password",
                        info        = "Only needed if GROQ_API_KEY is not in HF/Colab Secrets",
                    )
                    status_btn = gr.Button("Check System Status", size="sm",
                                           variant="secondary")

                gr.HTML("<hr style='border-color:#E2E8F0;margin:14px 0'>")

                # ── Primary action buttons ────────────────────────────
                generate_btn = gr.Button(
                    "Generate Infographic",
                    variant  = "primary",
                    elem_id  = "generate-btn",
                )

                with gr.Row():
                    clear_btn = gr.Button("Clear", variant="stop", size="sm")

                gr.Markdown("""
### How to Use
1. **Enter a topic** — any professional subject
2. **Adjust settings** — template, theme, caption style
3. **Click Generate** — AI creates content + renders infographic
4. **Preview, copy, download** — LinkedIn-ready PNG + caption
""")

            # ════════════════════════════════════════════════════════════
            # RIGHT COLUMN — Outputs
            # ════════════════════════════════════════════════════════════
            with gr.Column(scale=6, min_width=480):

                # ── Status bar ────────────────────────────────────────
                status_text = gr.Textbox(
                    label       = "Status",
                    value       = f"[{datetime.now().strftime('%H:%M:%S')}] Ready — enter a topic and click Generate",
                    interactive = False,
                    lines       = 1,
                    max_lines   = 2,
                    elem_id     = "status-box",
                )

                # ── Output Tabs ───────────────────────────────────────
                with gr.Tabs():

                    # ── Tab 1: Infographic preview ────────────────────
                    with gr.Tab("🖼 Infographic"):
                        image_output = gr.Image(
                            label  = "Generated Infographic (1080 × 1350 px)",
                            type   = "pil",
                            height = 580,
                            
                        )
                        download_file = gr.File(
                            label = "Download PNG",
                        )
                        seo_info_box = gr.Textbox(
                            label       = "Analytics",
                            interactive = False,
                            lines       = 1,
                            max_lines   = 2,
                            placeholder = "SEO grade, word count, token usage appear here after generation",
                        )

                    # ── Tab 2: LinkedIn Caption ───────────────────────
                    with gr.Tab("✍ Caption"):
                        caption_output = gr.Textbox(
                            label            = "LinkedIn Post — Copy & Paste Ready",
                            lines            = 18,
                            max_lines        = 35,
                            interactive      = True,
                            placeholder      = "Your LinkedIn caption appears here after generation...\n\nYou can edit it before copying.",
                            
                            elem_id          = "caption-out",
                        )
                        gr.Markdown(
                            "*Tip: Edit the caption freely before copying. "
                            "The copy button copies the full post including hashtags.*"
                        )

                    # ── Tab 3: Content JSON ───────────────────────────
                    with gr.Tab("📋 JSON"):
                        json_output = gr.Code(
                            label    = "Generated Content Structure",
                            language = "json",
                            value    = "{}",
                        )

                    # ── Tab 4: Generation info ────────────────────────
                    with gr.Tab("ℹ Info"):
                        metadata_box = gr.Textbox(
                            label       = "Generation Details",
                            lines       = 16,
                            interactive = False,
                            placeholder = "Phase timings and generation metadata appear here...",
                        )

        # ── Footer ────────────────────────────────────────────────────
        gr.HTML(FOOTER_HTML)

        # ════════════════════════════════════════════════════════════════
        # INPUTS & OUTPUTS — mapped to every event handler
        # ════════════════════════════════════════════════════════════════

        INPUTS = [
            topic_input,
            template_dd,
            color_theme_dd,
            caption_style_dd,
            export_preset_dd,
            model_dd,
            api_key_input,
        ]

        OUTPUTS = [
            status_text,
            image_output,
            caption_output,
            seo_info_box,
            download_file,
            json_output,
            metadata_box,
        ]

        # ════════════════════════════════════════════════════════════════
        # EVENT WIRING
        # ════════════════════════════════════════════════════════════════

        # Generate button click
        generate_btn.click(
            fn      = generate_infographic,
            inputs  = INPUTS,
            outputs = OUTPUTS,
        )

        # Enter key in topic box also generates
        topic_input.submit(
            fn      = generate_infographic,
            inputs  = INPUTS,
            outputs = OUTPUTS,
        )

        # Clear button resets all outputs
        clear_btn.click(
            fn      = clear_outputs,
            inputs  = [],
            outputs = OUTPUTS,
        )

        # Example topic buttons — each sets the topic input
        for btn, topic_text in zip(ex_btn, EXAMPLE_TOPICS[:6]):
            btn.click(
                fn      = lambda t=topic_text: t,
                inputs  = [],
                outputs = [topic_input],
            )

        # System status check
        status_btn.click(
            fn      = check_system_status,
            inputs  = [api_key_input],
            outputs = [status_text],
        )

    return demo


# ════════════════════════════════════════════════════════════════════════════
# LAUNCH CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

def _get_launch_config() -> dict:
    """Return Gradio launch kwargs based on environment."""
    is_hf_space = bool(os.environ.get("SPACE_ID"))
    is_colab    = os.path.exists("/content") or "google.colab" in sys.modules
    share_env   = os.environ.get("LINKPHOBOT_SHARE","").lower()
    share       = share_env in ("true","1","yes") or is_colab

    if is_hf_space:
        # HF Spaces: bind to 0.0.0.0:7860, no public share link needed
        return {
            "server_name": "0.0.0.0",
            "server_port": 7860,
            "share":       False,
            "show_error":  True,
        }

    if is_colab:
        # Colab: share=True creates the public tunneled URL
        return {
            "share":      True,
            "show_error": True,
        }

    # Local development
    return {
        "server_name": "0.0.0.0",
        "server_port": int(os.environ.get("LINKPHOBOT_PORT", 7860)),
        "share":       share,
        "show_error":  True,
        "inbrowser":   True,
    }


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  LINKPHOBOT v1.0.0")
    print("  LinkedIn Infographic Generator")
    print("=" * 55)

    # Load API key at startup
    key = _load_api_key()
    if key:
        print(f"[Linkphobot] GROQ_API_KEY: loaded ({key[:8]}...)")
    else:
        print("[Linkphobot] GROQ_API_KEY: NOT SET — user can enter in UI")

    # Verify pipeline
    pipeline = _get_pipeline()
    if pipeline:
        print("[Linkphobot] main_pipeline.py: loaded")
        pm = getattr(pipeline, "PathManager", None)
        if pm:
            found = sum(1 for p in range(1,11) if pm.find_phase_dir(p))
            print(f"[Linkphobot] Phase folders found: {found}/10")
    else:
        print("[Linkphobot] WARNING: main_pipeline.py not found")
        print("             Place main_pipeline.py in same folder as app.py")

    # Build and launch UI
    print("\n[Linkphobot] Building Gradio interface...")
    demo   = build_interface()
    config = _get_launch_config()
    print(f"[Linkphobot] Launching: port={config.get('server_port',7860)} share={config.get('share',False)}\n")

    demo.queue(max_size=5).launch(**config)


if __name__ == "__main__":
    main()
