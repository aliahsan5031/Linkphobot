---
title: Linkphobot
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: false
license: mit
---

# 🤖 Linkphobot

**AI-powered LinkedIn infographic generator.** Turn a topic into a polished,
ready-to-post infographic (PNG) and a matching caption in seconds.

Built with **Groq + gpt-oss-120b** for content, **Pillow** for rendering and
**Gradio** for the UI.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Gradio](https://img.shields.io/badge/gradio-5.9.1-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- **One-click generation**: enter a topic, get an infographic and a caption
- **Caption styles that matter**: educational, data-driven, thought leadership, story or listicle each change how the post is written
- **Edit and re-render for free**: fix any text in the JSON tab and re-render without another API call
- **Batch mode**: one topic per line (up to 10), downloaded as a ZIP of PNGs and captions
- **Two sizes**: portrait 4:5 (1080×1350) and square (1080×1080)
- **Your own brand line** in the footer instead of a fixed one
- **14 colour themes**, chosen from the topic or picked by hand, with text colours adjusted so they stay readable
- **Adaptive layout**: text is measured and wrapped, so blocks never overlap and long content shrinks to fit instead of being cut off
- **Faster and cheaper**: identical requests are cached, and transient Groq errors (rate limits, 5xx) are retried with backoff
- **Free to run** on Groq's free tier

## 🚀 Getting started

```bash
git clone https://github.com/aliahsan5031/Linkphobot.git
cd Linkphobot
pip install -r requirements.txt
```

### Add your Groq API key

Get a free key at [console.groq.com/keys](https://console.groq.com/keys). **Do not
put it in the source code.** Provide it as an environment variable:

```bash
cp .env.example .env      # then edit .env and set GROQ_API_KEY=...
# or:
export GROQ_API_KEY=your_key_here
```

- **Hugging Face Spaces:** *Settings → Variables and secrets → New secret* named `GROQ_API_KEY`.
- **Anyone using the app** can also paste their own key under *Advanced Settings*. It is never written to disk or logged; it only lives in server memory while the app runs.

### Run it

```bash
python app.py
```

The app opens at `http://127.0.0.1:7860`. It only listens on your own machine by
default, so a key in your environment is not exposed to the network. In a
container or Codespace, set `GRADIO_SERVER_NAME=0.0.0.0`.

### Optional settings

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq API key |
| `LINKPHOBOT_BRAND` | Default footer line, for example `Ali Ahsan \| linkedin.com/in/you` |
| `LINKPHOBOT_FONT`, `LINKPHOBOT_FONT_BOLD` | Paths to your own `.ttf` files |

## 📦 Project structure

```
app.py                 Gradio UI only
linkphobot/            the package the app uses
  config.py            themes, sizes, models, key and brand lookup
  content.py           prompt, Groq call with retry, JSON repair, validation, cache
  caption.py           hashtag cleanup and per-style captions
  render.py            adaptive Pillow renderer
  export.py            PNG/ZIP saving and temp-file cleanup
  pipeline.py          generate, re-render and batch entry points
tests/                 pytest suite (Groq is mocked, so it runs offline)
```

The other `*.py` files in the repository root (`main_pipeline.py`,
`content_generator.py`, `layout_engine.py` and so on) are an earlier, separate
pipeline. The app does not use them and they are unchanged. They are good
candidates to archive or delete once you confirm you do not need them.

## 🧪 Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

Pushes and pull requests run lint and tests in GitHub Actions. A push to `main`
only deploys to the Hugging Face Space if they pass.

## 🛠️ Tech stack

| Layer | Tool |
|---|---|
| Content AI | Groq API (gpt-oss-120b) |
| Image rendering | Pillow |
| UI | Gradio 5.9.1 |
| Runtime | Python 3.10+ |

## 🩺 Troubleshooting

- **Tiny or odd-looking text:** no TrueType font was found. Install Liberation or DejaVu fonts, or set `LINKPHOBOT_FONT` and `LINKPHOBOT_FONT_BOLD`.
- **`argument of type 'bool' is not iterable` at launch:** pydantic is too new for this Gradio version. `pip install -r requirements.txt` pins a compatible one.
- **"Groq's rate limit was reached":** the free tier is rate limited. Wait a moment, or use the *fast* model.

## 📄 License

MIT. See [LICENSE](LICENSE).
