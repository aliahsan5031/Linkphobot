"""Linkphobot: LinkedIn infographic generator (Gradio UI).

All logic lives in the ``linkphobot`` package; this file only wires the UI.

The Groq API key is read from the GROQ_API_KEY environment variable (on Hugging
Face Spaces: Settings > Variables and secrets). It is never stored in the source.
A visitor can also paste their own key in Advanced Settings.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import gradio as gr

from linkphobot import __version__
from linkphobot.config import (
    CAPTION_STYLES,
    MAX_BATCH,
    MODELS,
    THEME_CHOICES,
    get_api_key,
)
from linkphobot.content import ContentError
from linkphobot.pipeline import rerender, run_batch, run_one

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("linkphobot")

SIZE_CHOICES = [("Portrait 4:5 (1080×1350)", "portrait"), ("Square 1:1 (1080×1080)", "square")]
EXAMPLES = [
    "Artificial Intelligence in Healthcare",
    "Top 10 Leadership Skills for 2026",
    "How to Build a Personal Brand on LinkedIn",
    "Machine Learning for Beginners",
    "The Future of Remote Work",
    "Data Science Career Roadmap",
]

CSS = """
.gradio-container{font-family:'Inter','Segoe UI',sans-serif !important;max-width:1200px !important;margin:auto !important}
#gen-btn{background:linear-gradient(135deg,#FF6B35,#E85A25) !important;border:none !important;color:white !important;font-weight:700 !important;border-radius:10px !important;font-size:1.05rem !important;padding:14px !important;width:100% !important}
#gen-btn:hover{transform:translateY(-2px) !important;box-shadow:0 8px 20px rgba(255,107,53,0.5) !important}
"""

HEADER = f"""
<div style="background:linear-gradient(135deg,#1E3A5F,#2E6DA4,#FF6B35);border-radius:14px;
            padding:26px;text-align:center;margin-bottom:20px">
  <h1 style="color:#FFF;margin:0;font-weight:800;font-size:2rem">🤖 Linkphobot</h1>
  <p style="color:#E2E8F0;margin:6px 0 0;font-size:0.93rem">
    AI-Powered LinkedIn Infographic Generator &nbsp;·&nbsp; Groq + Llama 3.3 + Pillow
    &nbsp;·&nbsp; v{__version__}
  </p>
</div>
"""

FOOTER = """
<div style="text-align:center;color:#4A5568;font-size:0.78rem;padding:14px;
            margin-top:6px;border-top:1px solid #E2E8F0">
  Linkphobot &nbsp;·&nbsp; Groq + Llama 3.3 70B + Pillow &nbsp;·&nbsp;
  <a href="https://console.groq.com/keys" target="_blank" style="color:#4A5568">
    Get a free Groq API key →</a>
</div>
"""


def _stamp(message: str) -> str:
    return f"[{datetime.now():%H:%M:%S}] {message}"


def _crash_message(exc: Exception) -> str:
    """Unexpected errors: name the exception type so it can be diagnosed from the UI."""
    return f"Something went wrong ({type(exc).__name__}). See the Space logs for details."


def generate(topic, theme, model, style, size, brand, api_key_input):
    """Generate content, then render the image and caption."""
    started = time.time()
    try:
        result = run_one(topic, theme, model, style, size, brand, get_api_key(api_key_input))
    except ContentError as exc:
        return _stamp(str(exc)), None, str(exc), None, "{}", ""
    except Exception as exc:
        log.exception("Unexpected error while generating")
        message = _crash_message(exc)
        return _stamp(message), None, message, None, "{}", ""
    done = f"Done in {time.time() - started:.1f}s | {result.title[:45]}"
    return (
        _stamp(done),
        result.image,
        result.caption,
        result.png_path,
        result.json_text,
        result.meta,
    )


def rerender_edited(json_text, theme, style, size, brand):
    """Render the edited JSON again. No API call is made."""
    try:
        result = rerender(json_text, theme, style, size, brand)
    except ContentError as exc:
        # keep the current image and JSON on screen so the edit can be fixed
        return (_stamp(str(exc)), *(gr.update() for _ in range(5)))
    except Exception as exc:
        log.exception("Unexpected error while re-rendering")
        return (_stamp(_crash_message(exc)), *(gr.update() for _ in range(5)))
    return (
        _stamp(f"Re-rendered from your edits | {result.title[:45]}"),
        result.image,
        result.caption,
        result.png_path,
        result.json_text,
        result.meta,
    )


def generate_batch(topics_text, theme, model, style, size, brand, api_key_input,
                   progress=gr.Progress()):  # noqa: B008 - Gradio injects the tracker via this default
    """One infographic per line, returned as a ZIP of PNG + caption files."""
    try:
        zip_path, summary = run_batch(
            topics_text, theme, model, style, size, brand, get_api_key(api_key_input),
            progress=lambda fraction, desc: progress(fraction, desc=desc),
        )
    except ContentError as exc:
        return None, str(exc)
    except Exception as exc:
        log.exception("Unexpected error in batch run")
        return None, _crash_message(exc)
    return zip_path, summary


def clear():
    return _stamp("Ready. Enter a topic and click Generate."), None, "", None, "{}", ""


def _example_setter(text: str):
    return lambda: text


def build_ui():
    with gr.Blocks(css=CSS, title="Linkphobot: LinkedIn Infographic Generator") as demo:
        gr.HTML(HEADER)

        with gr.Tabs():
            with gr.Tab("Create"):
                with gr.Row():
                    # ── left: controls ────────────────────────────────────
                    with gr.Column(scale=4, min_width=320):
                        topic_in = gr.Textbox(
                            label="Topic",
                            placeholder="e.g. Artificial Intelligence in Healthcare",
                            lines=2,
                            max_length=200,
                            info="Be specific for best results",
                        )

                        gr.Markdown("**Quick start:**")
                        example_buttons = []
                        for row_start in range(0, len(EXAMPLES), 2):
                            with gr.Row():
                                for text in EXAMPLES[row_start : row_start + 2]:
                                    example_buttons.append(
                                        (gr.Button(text[:34] + "...", size="sm",
                                                   variant="secondary"), text)
                                    )

                        gr.Markdown("### Settings")
                        theme_dd = gr.Dropdown(THEME_CHOICES, value="auto", label="Color Theme",
                                               info="auto = chosen from the topic")
                        style_dd = gr.Dropdown(CAPTION_STYLES, value="educational",
                                               label="Caption Style",
                                               info="Changes how the LinkedIn post is written")
                        size_dd = gr.Dropdown(SIZE_CHOICES, value="portrait", label="Image Size")

                        with gr.Accordion("Advanced Settings", open=False):
                            model_dd = gr.Dropdown(list(MODELS), value="default", label="AI Model")
                            brand_in = gr.Textbox(
                                label="Footer brand line",
                                placeholder="e.g. Ali Ahsan | linkedin.com/in/yourname",
                                max_length=60,
                                info="Replaces the default 'Linkphobot' line",
                            )
                            api_key_in = gr.Textbox(
                                label="Groq API Key",
                                placeholder="Optional if the server already has GROQ_API_KEY set",
                                type="password",
                                info="Free key at console.groq.com/keys. Never saved or logged.",
                            )

                        gen_btn = gr.Button("Generate Infographic", variant="primary",
                                            elem_id="gen-btn")
                        clear_btn = gr.Button("Clear", variant="stop", size="sm")

                    # ── right: outputs ────────────────────────────────────
                    with gr.Column(scale=6, min_width=480):
                        status_box = gr.Textbox(
                            label="Status", value=_stamp("Ready"),
                            interactive=False, lines=2, max_lines=3,
                        )
                        with gr.Tabs():
                            with gr.Tab("🖼 Infographic"):
                                img_out = gr.Image(label="Generated Infographic", type="pil",
                                                   height=560)
                                dl_file = gr.File(label="Download PNG")
                            with gr.Tab("✍ Caption"):
                                cap_out = gr.Textbox(
                                    label="LinkedIn Post (copy and paste)",
                                    lines=16, max_lines=30, interactive=True,
                                    placeholder="Your LinkedIn caption appears here...",
                                )
                            with gr.Tab("✏ Edit and re-render"):
                                gr.Markdown(
                                    "Change any text below, then re-render. This makes **no API "
                                    "call**, so it is instant and uses no tokens."
                                )
                                json_out = gr.Code(label="Content", language="json", value="{}",
                                                   interactive=True)
                                rerender_btn = gr.Button("Re-render from edited JSON",
                                                         variant="secondary")
                            with gr.Tab("ℹ Info"):
                                meta_out = gr.Textbox(label="Generation Details", lines=10,
                                                      interactive=False)

            with gr.Tab("Batch"):
                gr.Markdown(
                    f"One topic per line, up to {MAX_BATCH}. Uses the theme, style, size and "
                    "settings chosen in the **Create** tab. You get a ZIP with a PNG and a "
                    "caption file for each topic."
                )
                batch_in = gr.Textbox(label="Topics", lines=8,
                                      placeholder="Remote work trends\nCybersecurity basics\n...")
                batch_btn = gr.Button("Generate batch", variant="primary")
                batch_status = gr.Textbox(label="Result", lines=6, interactive=False)
                batch_file = gr.File(label="Download ZIP")

        gr.HTML(FOOTER)

        outputs = [status_box, img_out, cap_out, dl_file, json_out, meta_out]
        inputs = [topic_in, theme_dd, model_dd, style_dd, size_dd, brand_in, api_key_in]

        gen_btn.click(fn=generate, inputs=inputs, outputs=outputs)
        topic_in.submit(fn=generate, inputs=inputs, outputs=outputs)
        clear_btn.click(fn=clear, inputs=[], outputs=outputs)
        rerender_btn.click(
            fn=rerender_edited,
            inputs=[json_out, theme_dd, style_dd, size_dd, brand_in],
            outputs=outputs,
        )
        batch_btn.click(
            fn=generate_batch,
            inputs=[batch_in, theme_dd, model_dd, style_dd, size_dd, brand_in, api_key_in],
            outputs=[batch_file, batch_status],
        )
        for button, text in example_buttons:
            button.click(fn=_example_setter(text), inputs=[], outputs=[topic_in])

    return demo


def main():
    log.info("Linkphobot v%s", __version__)
    log.info(
        "Groq API key: %s",
        "configured via environment" if get_api_key() else "not set (visitors must enter one)",
    )

    demo = build_ui()
    on_hf = bool(os.environ.get("SPACE_ID"))
    on_colab = os.path.exists("/content")

    if on_hf:
        demo.queue(max_size=5).launch(server_name="0.0.0.0", server_port=7860,
                                      share=False, show_error=False, ssr_mode=False)
    elif on_colab:
        demo.queue(max_size=3).launch(share=True, show_error=False, ssr_mode=False)
    else:
        # Local run: bound to 127.0.0.1 so a key in the environment is not exposed
        # to the network. In a container or Codespace set GRADIO_SERVER_NAME=0.0.0.0.
        demo.queue(max_size=3).launch(share=False, inbrowser=True, show_error=False,
                                      ssr_mode=False)


if __name__ == "__main__":
    main()
