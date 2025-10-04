<div align="center">
  <h1>🌌 Aurora — Gemini Chat (Streamlit)</h1>
  <p><i>Sleek dark-mode AI chat with file/image/audio/PDF attach, chat history, streaming replies, token usage, and robust error handling — powered by Streamlit & Google Gemini (Files API)</i></p>
</div>

<br>

<div align="center">
  <a href="https://github.com/brej-29/aurora-chat-streamlit">
    <img alt="Last Commit" src="https://img.shields.io/github/last-commit/brej-29/aurora-chat-streamlit">
  </a>
  <img alt="Language" src="https://img.shields.io/badge/Language-Python-blue">
  <img alt="Framework" src="https://img.shields.io/badge/Framework-Streamlit-ff4b4b">
  <img alt="API" src="https://img.shields.io/badge/API-Google%20AI%20(Gemini)-orange">
  <img alt="Libraries" src="https://img.shields.io/badge/Libraries-google--genai%20%7C%20python--dotenv%20%7C%20Streamlit-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-black">
</div>

<div align="center">
  <br>
  <b>Built with the tools and technologies:</b>
  <br><br>
  <code>Python</code> | <code>Streamlit</code> | <code>Google Gemini (google-genai)</code> | <code>Files API</code> | <code>python-dotenv</code>
</div>

---

## **Table of Contents**
* [Overview](#overview)
* [Features](#features)
* [Getting Started](#getting-started)
  * [Project Structure](#project-structure)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Configuration](#configuration)
  * [Usage](#usage)
* [Roadmap](#roadmap)
* [License](#license)
* [Contact](#contact)
* [Contributing](#contributing)
* [Screenshots](#screenshots)

---

## **Overview**

Aurora is a professional, dark-mode AI chat interface for Google Gemini with a polished gradient UI, sticky composer, and a modular backend. It supports image/audio/PDF uploads via the **Files API**, shows previews before send, persists uploaded files across turns, streams model output token-by-token, tracks usage, and handles errors gracefully (e.g., rate limits, temporary outages). The UI is tuned for productivity: model picker, usage dialog, suggestion chips, and a centered greeting on first run.

<br>

### **Project Highlights**

- **Modern UI/UX:** fixed bottom composer, gradient send button, attach modal with staged previews, centered hero + 2×2 suggestions.
- **Files API only:** images, audio, PDFs uploaded once; references reused across the session for follow-up questions.
- **Streaming replies:** incremental rendering with a visible “Thinking…” placeholder.
- **Usage metrics:** input/output/reasoning tokens per turn; running totals in a modal.
- **Resilient backend:** modular `backend/genai_backend.py` with graceful fallbacks and robust retries for transient server errors.
- **Model switcher:** choose between `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-preview-09-2025`, fallback `gemini-2.0-flash`.

---

## **Features**

- Dark, indigo-magenta-gold gradient theme; compact header with model select (≈1/8 width) and Usage button.
- Sticky composer with **＋** button → staging modal → **Attach** confirmation; tiny thumbnail chips above composer.
- Chat history with user/assistant bubbles; user messages display attached files inline.
- **Image persistence**: ask follow-up questions about previously attached files (without re-uploading).
- “Thinking…” indicator placed right after the user’s latest message.
- **Streaming output** with smooth autoscroll behavior during the stream.
- Friendly error surfaces (429 suggest model switch; 503 explain temporary unavailability; 400 guidance to simplify).
- Token usage (prompt/response/reasoning) aggregated across session.

---

## **Getting Started**

Follow these steps to run the project locally.

### **Project Structure**

    aurora-chat-streamlit/
    ├─ app.py                          # Streamlit UI & chat orchestration
    ├─ backend/
    │  └─ genai_backend.py             # google-genai client, Files API upload, generate/stream helpers
    ├─ frontend/
    │  └─ scroll.py                    # (Optional helper) one-shot scroll utilities for UX polish
    ├─ .env                            # contains GEMINI_API_KEY (not committed)
    ├─ requirements.txt
    ├─ LICENSE
    └─ README.md

### **Prerequisites**
- Python **3.9+**
- A **Google AI Studio** API key with access to Gemini models
- Internet connectivity to call the API

### **Installation**
1) Create and activate a virtual environment (recommended).

       python -m venv .venv
       # Windows:
       .venv\Scripts\activate
       # macOS/Linux:
       source .venv/bin/activate

2) Install dependencies.

       pip install -r requirements.txt

### **Configuration**
Create a `.env` file at the project root:

    GEMINI_API_KEY=your_api_key_here

`app.py` loads this via `python-dotenv`. Environment variables also work.

### **Usage**
Run the app:

    streamlit run app.py

Workflow inside the app:
1) Pick a model from the header dropdown.
2) (Optional) Click **Usage** to see token totals (updates after model calls).
3) Start typing in the composer or click a suggestion chip.
4) Click the **＋** button to open the attach modal → upload files → click **Attach**.
5) Send your message. You’ll see your message bubble (with files) followed by a **Thinking…** placeholder and streamed output.
6) Ask follow-ups without re-uploading — the Files API references persist for the session.

---

## **Roadmap**

### ✅ Completed
- Dark gradient UI with sticky composer and compact header
- 2×2 suggestion chips and centered greeting on first load
- Files API integration; staged previews and inline message attachments
- Image/audio/PDF support; **image persistence across turns**
- Streaming responses with “Thinking…” indicator
- Error handling with user-friendly guidance (429/503/400)
- Token usage: prompt/response/reasoning + session totals
- Modular backend (`genai_backend.py`) and frontend utility (`frontend/scroll.py`)
- Model picker: 2.5 Pro, 2.5 Flash, 2.5 Flash Preview, 2.0 Flash (fallback)

### ⏭️ Pending / Nice-to-Have
- In-app model capability hints (vision/audio limits, file caps)
- Chat export (markdown/HTML) and “Share link” (optional)
- Theming controls (font size/compact mode/high-contrast)
- Advanced file library view (rename/remove/inspect metadata)
- Settings drawer (system prompt, temperature, safety toggles)
- Unit tests and linting (pytest/ruff)
- Example deployments (Streamlit Community Cloud / Docker)
- Keyboard shortcuts cheat-sheet and accessibility polish (ARIA)
- Basic analytics (per-turn latency, success/error rates)

---

## **License**
MIT — see `LICENSE` for details.

---

## **Contact**
Questions, feedback, or feature requests? Open an issue or reach out on LinkedIn.

- Maintainer: Brejesh Balakrishnan
- LinkedIn: https://www.linkedin.com/in/brejesh-balakrishnan-7855051b9/
- Project: https://github.com/brej-29/aurora-chat-streamlit

---

## **Contributing**
Contributions are very welcome! If you’d like to improve the UX, add tests, wire up deployments, or extend model features, please:
1) Fork the repo and create a branch,
2) Keep changes focused and documented,
3) Open a PR with a clear description and screenshots where relevant.

If you use Aurora in your own project, I’d love to hear about it — please share a link! 🎉

---

## **Screenshots**


<img width="1915" height="916" alt="image" src="https://github.com/user-attachments/assets/3453622e-9108-4ea8-86b8-775335d1542e" />

<img width="1917" height="925" alt="image" src="https://github.com/user-attachments/assets/6e5d2e41-9ef7-4db4-8e7f-03bc28953693" />

<img width="1912" height="922" alt="image" src="https://github.com/user-attachments/assets/80be215b-b6e2-4b5f-a97a-15e6e17d7ac5" />

<img width="1627" height="409" alt="image" src="https://github.com/user-attachments/assets/d507355f-1b8c-429f-b668-31fbbe9532b7" />

<img width="1919" height="919" alt="image" src="https://github.com/user-attachments/assets/59bebd7d-2e50-4977-9403-3925029bff23" />
