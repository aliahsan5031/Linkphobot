"""
app.py - Linkphobot
===================
Standalone LinkedIn Infographic Generator for Hugging Face Spaces.
Self-contained: no main_pipeline.py dependency needed.

HF Secret name: GROQ_API_KEY  OR  Linkphobot_API  (either works)
"""

import os, sys, json, re, time, tempfile, traceback
from datetime import datetime
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import gradio as gr


# ════════════════════════════════════════════════════════════════════════════
# API KEY  — checks every possible secret name
# ════════════════════════════════════════════════════════════════════════════

def get_api_key(user_key: str = "") -> str:
    if user_key and user_key.strip():
        return user_key.strip()
    for name in ["GROQ_API_KEY", "Linkphobot_API", "LINKPHOBOT_API",
                 "groq_api_key", "linkphobot_api"]:
        val = os.environ.get(name, "").strip()
        if val:
            return val
    return ""


# ════════════════════════════════════════════════════════════════════════════
# CONTENT GENERATION  — Groq + Llama 3.3
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = (
    "You are an elite LinkedIn infographic content strategist.\n"
    "CRITICAL: Respond ONLY with pure valid JSON. No markdown. No explanation.\n"
    "Start with { and end with }. Generate EXACTLY 4 sections.\n"
    "Bullets max 12 words. Title max 8 words. Subtitle max 15 words.\n"
)

VALID_THEMES = {
    "tech_purple","dev_dark","finance_navy","health_blue","eco_green",
    "executive_navy","creative_coral","engineering_navy","data_indigo",
    "clean_blue","edu_teal","people_warm","cyber_dark","professional"
}

GROQ_MODELS = {
    "default": "llama-3.3-70b-versatile",
    "fast":    "llama-3.1-8b-instant",
    "quality": "llama-3.3-70b-versatile",
}

def _extract_json(text):
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    start = text.find("{")
    if start == -1: raise ValueError("No JSON found")
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return text[start:i+1]
    return text[start:] + "}" * depth

def _repair_json(raw):
    for fn in [lambda: json.loads(raw),
               lambda: json.loads(_extract_json(raw))]:
        try: return fn()
        except: pass
    for c in ["}", "}}", "]}}", "]}]}}"]:
        try: return json.loads(_extract_json(raw) + c)
        except: pass
    raise ValueError("Cannot parse JSON: " + raw[:200])

def _validate(data, topic):
    data.setdefault("title", topic[:60])
    data.setdefault("subtitle", "Key professional insights for 2025")
    data.setdefault("sections", [])
    data.setdefault("key_points", ["Deep expertise drives results",
                                    "Practice builds mastery",
                                    "Collaboration amplifies outcomes"])
    data.setdefault("statistics", [])
    data.setdefault("call_to_action", "Save this post and share it with your network.")
    data.setdefault("linkedin_caption", "Key insights on " + topic + ".")
    data.setdefault("hashtags", ["#LinkedIn", "#Learning", "#Professional"])
    data.setdefault("color_theme", "professional")
    data.setdefault("target_audience", "Professionals")
    data.setdefault("content_type", "educational")
    if data.get("color_theme") not in VALID_THEMES:
        data["color_theme"] = "professional"
    data["sections"] = [
        {"heading": s.get("heading", "Key Insights"),
         "icon_suggestion": s.get("icon_suggestion", "📌"),
         "content": s.get("content", [])[:4]}
        for s in data.get("sections", []) if isinstance(s, dict)
    ][:4]
    data["statistics"] = [
        {"value": s.get("value",""), "label": s.get("label",""), "context": s.get("context","")}
        for s in data.get("statistics", []) if isinstance(s, dict) and s.get("value")
    ][:3]
    data["hashtags"] = data["hashtags"][:8]
    return data

def generate_content(topic: str, model: str = "default", api_key: str = "") -> dict:
    from groq import Groq
    client = Groq(api_key=api_key)
    prompt = (
        "TOPIC: " + topic + "\n\n"
        "Generate a LinkedIn infographic content plan. Exactly 4 sections.\n\n"
        "COLOR THEME - return only the theme name:\n"
        "AI/ML=tech_purple, Healthcare=health_blue, Finance=finance_navy,\n"
        "Leadership=executive_navy, Sustainability=eco_green, Data=data_indigo,\n"
        "Education=edu_teal, Tech/Software=dev_dark, Default=professional\n\n"
        'Return ONLY this JSON: {"title":"","subtitle":"","sections":[{"heading":"",'
        '"icon_suggestion":"emoji","content":["bullet1","bullet2","bullet3"]}],'
        '"key_points":[],"statistics":[{"value":"","label":"","context":""}],'
        '"call_to_action":"","linkedin_caption":"","hashtags":[],'
        '"color_theme":"","target_audience":"","content_type":"educational"}\n'
        "EXACTLY 4 SECTIONS. Return ONLY JSON."
    )
    t0 = time.time()
    response = client.chat.completions.create(
        model       = GROQ_MODELS.get(model, GROQ_MODELS["default"]),
        messages    = [{"role": "system", "content": SYSTEM_PROMPT},
                       {"role": "user",   "content": prompt}],
        temperature = 0.65,
        max_tokens  = 2800,
    )
    elapsed = round(time.time() - t0, 2)
    raw     = response.choices[0].message.content
    data    = _validate(_repair_json(raw), topic)
    data["_tokens"]  = response.usage.total_tokens
    data["_elapsed"] = elapsed
    data["_model"]   = response.model
    return data


# ════════════════════════════════════════════════════════════════════════════
# INFOGRAPHIC RENDERER  — pure PIL, no external dependencies
# ════════════════════════════════════════════════════════════════════════════

PALETTES = {
    "tech_purple":     ("#0D0D1A", "#6C3FC5", "#00D4FF", "#B0B0C8"),
    "health_blue":     ("#EBF8FF", "#0077B6", "#F4A261", "#0077B6"),
    "finance_navy":    ("#F8F9FA", "#0A2342", "#F7C948", "#2C3E50"),
    "executive_navy":  ("#FAFBFF", "#1A1F36", "#FF6B35", "#2D3561"),
    "eco_green":       ("#F0FFF4", "#1B4332", "#95D5B2", "#2D6A4F"),
    "data_indigo":     ("#FAF8FF", "#3C1053", "#FFB347", "#7B2D8B"),
    "engineering_navy":("#F5F5F5", "#0A192F", "#64FFDA", "#172A45"),
    "cyber_dark":      ("#0A0A0A", "#111111", "#00FF41", "#CCCCCC"),
    "clean_blue":      ("#F8FAFC", "#2563EB", "#FBBF24", "#1E40AF"),
    "edu_teal":        ("#FFF8F0", "#004E64", "#F4A261", "#00A5CF"),
    "creative_coral":  ("#FFFBF0", "#FF4E50", "#F9D423", "#FF4E50"),
    "dev_dark":        ("#11111B", "#89B4FA", "#A6E3A1", "#BAC2DE"),
    "people_warm":     ("#FFFAF5", "#B5451B", "#FFD166", "#B5451B"),
    "professional":    ("#FAFBFF", "#1E3A5F", "#FF6B35", "#2E6DA4"),
}

def _get_font(size: int, bold: bool = False):
    paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-{}.ttf".format(
            "Bold" if bold else "Regular"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format(
            "-Bold" if bold else ""),
    ]
    for p in paths:
        if os.path.isfile(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def _tw(text, font):
    try: return font.getbbox(text)[2]
    except: return len(text) * 8

def _center_text(draw, text, font, y, W, color):
    draw.text(((W - _tw(text, font)) // 2, y), text, font=font, fill=color)

def render_infographic(content: dict, color_theme: str = "") -> Image.Image:
    theme = color_theme or content.get("color_theme", "professional")
    if theme not in PALETTES: theme = "professional"
    bg, pri, acc, txt = PALETTES[theme]

    def h(c):
        c = c.lstrip("#")
        return int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)

    W, H = 1080, 1350
    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Fonts
    f_title = _get_font(52, True)
    f_sub   = _get_font(24)
    f_head  = _get_font(26, True)
    f_body  = _get_font(21)
    f_small = _get_font(17)
    f_badge = _get_font(15, True)

    # Header gradient
    r1,g1,b1 = h(pri)
    r2,g2,b2 = (46,109,164)
    for y in range(390):
        t = y/390
        draw.line([(0,y),(W,y)],
            fill=(int(r1+(r2-r1)*t*0.4), int(g1+(g2-g1)*t*0.4), int(b1+(b2-b1)*t*0.4)))

    # Badge
    badge   = content.get("content_type","educational").upper()
    acc_rgb = h(acc)
    bw      = _tw(badge, f_badge) + 32
    draw.rounded_rectangle([(W-bw)//2, 42, (W+bw)//2, 78], radius=18, fill=acc_rgb)
    draw.text(((W - _tw(badge, f_badge))//2, 50), badge, font=f_badge, fill=(255,255,255))

    # Title + subtitle
    title = content.get("title","Linkphobot")[:55]
    _center_text(draw, title, f_title, 104, W, (255,255,255))
    subtitle = content.get("subtitle","")[:72]
    _center_text(draw, subtitle, f_sub, 172, W, h("#CBD5E0"))

    # Section cards
    sections = content.get("sections",[])
    pri_rgb  = h(pri)
    txt_rgb  = h(txt)
    dark_bg  = bg in ("#0D0D1A","#0A0A0A","#11111B","#0A192F")
    card_bg  = "#1A1A2E" if dark_bg else "#FFFFFF"
    cy = 412

    for i, sec in enumerate(sections[:4]):
        cb = card_bg if i%2==0 else ("#16213E" if dark_bg else "#F0F4FF")
        draw.rounded_rectangle([54, cy, 1026, cy+148], radius=14, fill=cb)
        draw.rounded_rectangle([54, cy+10, 61, cy+138], radius=4, fill=acc_rgb)
        icon    = sec.get("icon_suggestion","")
        heading = (icon + " " + sec.get("heading",""))[:44]
        head_color = h("#89B4FA") if dark_bg else pri_rgb
        draw.text((80, cy+16), heading, font=f_head, fill=head_color)
        bullets = sec.get("content",[])[:2]
        by = cy+60
        for b in bullets:
            draw.ellipse([80,by+8,89,by+17], fill=acc_rgb)
            draw.text((100,by), b[:62], font=f_body, fill=txt_rgb)
            by += 34
        cy += 162

    # Key points
    kps = content.get("key_points",[])[:3]
    if kps:
        ky = cy+6
        draw.rounded_rectangle([54,ky,1026,ky+116], radius=12, fill=pri_rgb)
        kx = 80
        for kp in kps:
            draw.ellipse([kx,ky+18,kx+8,ky+26], fill=acc_rgb)
            draw.text((kx+14,ky+12), kp[:44], font=f_small, fill=(255,255,255))
            kx += 316
        cy = ky+116

    # Stats
    stats = content.get("statistics",[])[:3]
    if stats:
        sy = cy+14
        n  = len(stats)
        sw = (972-12*(n-1))//n
        sx = 54
        sc = "#1A1A2E" if dark_bg else "#EEF4FF"
        for stat in stats:
            draw.rounded_rectangle([sx,sy,sx+sw,sy+110], radius=12, fill=sc)
            draw.rounded_rectangle([sx,sy,sx+sw,sy+5], radius=3, fill=acc_rgb)
            val = stat.get("value","")
            draw.text((sx+(_tw(val,f_head) and (sw-_tw(val,f_head))//2),sy+14),
                      val, font=f_head, fill=acc_rgb)
            lbl = stat.get("label","")[:30]
            draw.text((sx+(sw-_tw(lbl,f_small))//2,sy+60),
                      lbl, font=f_small, fill=txt_rgb)
            sx += sw+12

    # Footer
    fy = H-106
    draw.line([(54,fy),(1026,fy)], fill=h("#E2E8F0"), width=1)
    cta = content.get("call_to_action","Save and share this post.")[:68]
    _center_text(draw, cta, f_body, fy+8, W, pri_rgb)
    tags = " ".join(content.get("hashtags",[])[:5])
    _center_text(draw, tags, f_small, fy+46, W, h("#718096"))
    brand = "Linkphobot  |  AI-Powered LinkedIn Infographics"
    _center_text(draw, brand, f_small, H-28, W, h("#A0AEC0"))

    return img


# ════════════════════════════════════════════════════════════════════════════
# CAPTION BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_caption(content: dict) -> str:
    caption  = content.get("linkedin_caption","")
    hashtags = " ".join(content.get("hashtags",[]))
    if not caption:
        kps     = content.get("key_points",[])
        kp_text = "\n".join("• " + kp for kp in kps[:3])
        caption = (
            content.get("title","") + "\n\n"
            "Here is what every professional needs to know:\n\n"
            + kp_text + "\n\n"
            + content.get("call_to_action","Save and share this post.")
        )
    return caption + "\n\n" + hashtags


# ════════════════════════════════════════════════════════════════════════════
# MAIN HANDLER
# ════════════════════════════════════════════════════════════════════════════

def generate(topic, color_theme, model, caption_style, api_key_input):
    def ts(m): return f"[{datetime.now().strftime('%H:%M:%S')}] {m}"

    topic = (topic or "").strip()
    if len(topic) < 3:
        return (ts("Please enter a topic (min 3 characters)"),
                None, "", None, "{}", "")

    api_key = get_api_key(api_key_input)
    if not api_key:
        return (
            ts("No API key found — paste your Groq key in the API Key field below"),
            None,
            "No API key.\n\nGet a free key at https://console.groq.com/keys\n"
            "Then paste it in the 'Groq API Key' field in Advanced Settings.",
            None, "{}", ""
        )

    t0 = time.time()
    try:
        # Generate content
        content = generate_content(topic, model, api_key)
        if color_theme and color_theme != "auto":
            content["color_theme"] = color_theme

        # Render image
        img = render_infographic(content)

        # Save PNG
        tmp = tempfile.mktemp(suffix=".png", prefix="linkphobot_")
        img.save(tmp, "PNG", optimize=True)

        # Build caption
        caption = build_caption(content)

        elapsed = round(time.time()-t0, 1)
        tokens  = content.get("_tokens", 0)
        json_str= json.dumps(
            {k:v for k,v in content.items() if not k.startswith("_")},
            indent=2, ensure_ascii=False)[:4000]
        meta    = (
            f"Topic:    {topic}\n"
            f"Title:    {content.get('title','')}\n"
            f"Theme:    {content.get('color_theme','')}\n"
            f"Sections: {len(content.get('sections',[]))}\n"
            f"Tokens:   {tokens}\n"
            f"Time:     {elapsed}s\n"
            f"Model:    {content.get('_model','')}\n"
            f"Generated:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return (
            ts(f"Done in {elapsed}s  |  {content.get('title','')[:45]}"),
            img,
            caption,
            tmp,
            json_str,
            meta,
        )

    except Exception as e:
        tb  = traceback.format_exc()
        err = str(e)
        print(f"[Linkphobot] ERROR: {tb}")
        return (ts(f"Error: {err[:80]}"), None,
                f"Error: {err}\n\n{tb[-500:]}", None, "{}", "")

def clear():
    return (
        f"[{datetime.now().strftime('%H:%M:%S')}] Ready — enter a topic and click Generate",
        None, "", None, "{}", ""
    )


# ════════════════════════════════════════════════════════════════════════════
# GRADIO UI
# ════════════════════════════════════════════════════════════════════════════

THEMES = ["auto","tech_purple","health_blue","finance_navy","executive_navy",
          "eco_green","data_indigo","engineering_navy","cyber_dark","clean_blue",
          "edu_teal","creative_coral","dev_dark","people_warm","professional"]
MODELS  = ["default","fast","quality"]
STYLES  = ["educational","data_driven","thought_leadership","story","listicle"]
EXAMPLES= [
    "Artificial Intelligence in Healthcare",
    "Top 10 Leadership Skills for 2025",
    "How to Build a Personal Brand on LinkedIn",
    "Machine Learning for Beginners",
    "The Future of Remote Work",
    "Data Science Career Roadmap 2025",
]

CSS = """
.gradio-container{font-family:'Inter','Segoe UI',sans-serif !important;max-width:1200px !important;margin:auto !important}
#gen-btn{background:linear-gradient(135deg,#FF6B35,#E85A25) !important;border:none !important;color:white !important;font-weight:700 !important;border-radius:10px !important;font-size:1.05rem !important;padding:14px !important;width:100% !important}
#gen-btn:hover{transform:translateY(-2px) !important;box-shadow:0 8px 20px rgba(255,107,53,0.5) !important}
"""

HEADER = """
<div style="background:linear-gradient(135deg,#1E3A5F,#2E6DA4,#FF6B35);border-radius:14px;
            padding:26px;text-align:center;margin-bottom:20px">
  <h1 style="color:#FFF;margin:0;font-weight:800;font-size:2rem">🤖 Linkphobot</h1>
  <p style="color:#CBD5E0;margin:6px 0 0;font-size:0.93rem">
    AI-Powered LinkedIn Infographic Generator &nbsp;·&nbsp; Groq + Llama 3.3 + PIL &nbsp;·&nbsp; v1.0.0
  </p>
</div>
"""

FOOTER = """
<div style="text-align:center;color:#718096;font-size:0.78rem;padding:14px;
            margin-top:6px;border-top:1px solid #E2E8F0">
  Linkphobot &nbsp;·&nbsp; Groq + Llama 3.3 70B + Pillow &nbsp;·&nbsp;
  <a href="https://console.groq.com/keys" target="_blank" style="color:#718096">
    Get Free Groq API Key →</a>
</div>
"""

def build_ui():
    with gr.Blocks(css=CSS, title="Linkphobot — LinkedIn Infographic Generator") as demo:

        gr.HTML(HEADER)

        with gr.Row():

            # ── LEFT: Controls ────────────────────────────────────────
            with gr.Column(scale=4, min_width=320):

                topic_in = gr.Textbox(
                    label="Topic",
                    placeholder="e.g. Artificial Intelligence in Healthcare",
                    lines=2, info="Be specific for best results")

                gr.Markdown("**Quick start:**")
                with gr.Row():
                    ex1 = gr.Button(EXAMPLES[0][:34]+"...", size="sm", variant="secondary")
                    ex2 = gr.Button(EXAMPLES[1][:34]+"...", size="sm", variant="secondary")
                with gr.Row():
                    ex3 = gr.Button(EXAMPLES[2][:34]+"...", size="sm", variant="secondary")
                    ex4 = gr.Button(EXAMPLES[3][:34]+"...", size="sm", variant="secondary")
                with gr.Row():
                    ex5 = gr.Button(EXAMPLES[4][:34]+"...", size="sm", variant="secondary")
                    ex6 = gr.Button(EXAMPLES[5][:34]+"...", size="sm", variant="secondary")

                gr.HTML("<hr style='border-color:#E2E8F0;margin:14px 0'>")
                gr.Markdown("### Settings")

                theme_dd = gr.Dropdown(THEMES, value="auto", label="Color Theme",
                                        info="auto = detected from topic")
                style_dd = gr.Dropdown(STYLES, value="educational", label="Caption Style")

                with gr.Accordion("Advanced Settings", open=False):
                    model_dd  = gr.Dropdown(MODELS, value="default", label="AI Model")
                    api_key_in= gr.Textbox(
                        label="Groq API Key",
                        placeholder="gsk_... paste your key here if secrets not working",
                        type="password",
                        info="Get free key at console.groq.com/keys")

                gr.HTML("<hr style='border-color:#E2E8F0;margin:14px 0'>")

                gen_btn   = gr.Button("Generate Infographic", variant="primary", elem_id="gen-btn")
                clear_btn = gr.Button("Clear", variant="stop", size="sm")

                gr.Markdown("""
### How to Use
1. Enter a topic
2. Choose color theme
3. Click **Generate**
4. Download your PNG + copy caption
""")

            # ── RIGHT: Outputs ────────────────────────────────────────
            with gr.Column(scale=6, min_width=480):

                status_box = gr.Textbox(
                    label="Status",
                    value=f"[{datetime.now().strftime('%H:%M:%S')}] Ready",
                    interactive=False, lines=1, max_lines=2)

                with gr.Tabs():
                    with gr.Tab("🖼 Infographic"):
                        img_out = gr.Image(label="Generated Infographic (1080×1350)",
                                            type="pil", height=560)
                        dl_file = gr.File(label="Download PNG")

                    with gr.Tab("✍ Caption"):
                        cap_out = gr.Textbox(
                            label="LinkedIn Post — Copy & Paste Ready",
                            lines=16, max_lines=30, interactive=True,
                            placeholder="Your LinkedIn caption appears here...")

                    with gr.Tab("📋 JSON"):
                        json_out = gr.Code(label="Content Structure",
                                           language="json", value="{}")

                    with gr.Tab("ℹ Info"):
                        meta_out = gr.Textbox(label="Generation Details",
                                               lines=12, interactive=False)

        gr.HTML(FOOTER)

        # ── Outputs / Inputs lists ────────────────────────────────────
        OUTPUTS = [status_box, img_out, cap_out, dl_file, json_out, meta_out]
        INPUTS  = [topic_in, theme_dd, model_dd, style_dd, api_key_in]

        # ── Wire events ───────────────────────────────────────────────
        gen_btn.click(fn=generate, inputs=INPUTS, outputs=OUTPUTS)
        topic_in.submit(fn=generate, inputs=INPUTS, outputs=OUTPUTS)
        clear_btn.click(fn=clear,   inputs=[],     outputs=OUTPUTS)

        ex1.click(fn=lambda: EXAMPLES[0], inputs=[], outputs=[topic_in])
        ex2.click(fn=lambda: EXAMPLES[1], inputs=[], outputs=[topic_in])
        ex3.click(fn=lambda: EXAMPLES[2], inputs=[], outputs=[topic_in])
        ex4.click(fn=lambda: EXAMPLES[3], inputs=[], outputs=[topic_in])
        ex5.click(fn=lambda: EXAMPLES[4], inputs=[], outputs=[topic_in])
        ex6.click(fn=lambda: EXAMPLES[5], inputs=[], outputs=[topic_in])

    return demo


# ════════════════════════════════════════════════════════════════════════════
# STARTUP
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 50)
    print("  LINKPHOBOT v1.0.0")
    print("=" * 50)

    key = get_api_key()
    print(f"API key: {'loaded (' + key[:8] + '...)' if key else 'NOT SET (user must enter in UI)'}")

    is_hf    = bool(os.environ.get("SPACE_ID"))
    is_colab = os.path.exists("/content")

    demo = build_ui()

    if is_hf:
        demo.queue(max_size=5).launch(server_name="0.0.0.0", server_port=7860,
                                       share=False, show_error=True)
    elif is_colab:
        demo.queue(max_size=3).launch(share=True, show_error=True)
    else:
        demo.queue(max_size=3).launch(server_name="0.0.0.0", server_port=7860,
                                       share=False, inbrowser=True, show_error=True)

if __name__ == "__main__":
    main()
