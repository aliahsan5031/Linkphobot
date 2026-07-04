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

**AI-Powered LinkedIn Infographic Generator** — turn any topic into a polished,
ready-to-post LinkedIn infographic (1080×1350 PNG) plus a matching caption,
in seconds.

Built with **Groq + Llama 3.3 70B** for content generation, **Pillow (PIL)**
for rendering, and **Gradio** for the UI.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Gradio](https://img.shields.io/badge/gradio-5.9.1-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- **One-click generation** — enter a topic, get a full infographic + caption
- **14 color themes** — auto-detected from your topic, or pick manually
- **LinkedIn-ready captions** — hashtags, call-to-action, and SEO-aware copy
- **Multiple AI models** — fast / default / quality Groq model tiers
- **No paid dependencies** — runs entirely on Groq's free-tier API

## 🖼️ How It Works

1. Enter a topic (e.g. *"Top 10 Leadership Skills for 2025"*)
2. Choose a color theme and caption style
3. Click **Generate Infographic**
4. Download the PNG and copy the ready-to-post caption

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/linkphobot.git
cd linkphobot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your Groq API key

Get a free key at [console.groq.com/keys](https://console.groq.com/keys), then
open `app.py` and set it near the top of the file:

```python
GROQ_API_KEY = "gsk_your_real_key_here"
```

> You can also paste a key directly into the "Groq API Key" field in the
> app's Advanced Settings at runtime — this overrides the hardcoded key.

### 4. Run the app

```bash
python app.py
```

The app will launch locally at `http://localhost:7860`.

## 📦 Project Structure

```
linkphobot/
├── app.py              # Standalone Gradio app (content gen + rendering + UI)
├── main_pipeline.py     # Modular pipeline version (same logic, class-based)
├── requirements.txt     # Python dependencies
└── README.md
```

## 🛠️ Tech Stack

| Layer          | Tool                          |
|----------------|--------------------------------|
| Content AI     | Groq API (Llama 3.3 70B)      |
| Image Rendering| Pillow (PIL)                  |
| UI             | Gradio 5.9.1                  |
| Runtime        | Python 3.10+                  |

## ⚠️ Security Note

This project hardcodes the Groq API key directly in `app.py` for simplicity.
**Do not commit your real key to a public repository.** If you fork or push
this project publicly, either:

- Keep your real key out of version control (add it only in a local, private
  copy or via the in-app key field), or
- Switch back to loading it from an environment variable / secret manager
  before pushing.

## 📄 License

MIT — see LICENSE for details.
