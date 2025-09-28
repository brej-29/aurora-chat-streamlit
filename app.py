import time
import streamlit as st
from dotenv import load_dotenv
import os
from backend.genai_backend import get_client, upload_bytes, call_model, UploadedRef
# Load .env (if present) and try Streamlit secrets
load_dotenv(override=True)

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY") # 2) .env or environment

if GOOGLE_API_KEY:
    _ = get_client(api_key=GOOGLE_API_KEY)
else:
    st.warning("Add your Google API key in .env, st.secrets, or the field above.")

# ------------------ Page setup ------------------
st.set_page_config(page_title="Gemini Chat", page_icon="💬", layout="wide")

# ------------------ Session State ------------------
ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("first_message_sent", False)
ss.setdefault("usage_totals", {"input": 0, "output": 0, "reasoning": 0})
ss.setdefault("pending_attachments", [])      # staged by the + modal, consumed on next send
ss.setdefault("uploader_key", f"uploader_{time.time_ns()}")
ss.setdefault("composer_input_value", "")
ss.setdefault("model_choice", "gemini-2.5-flash")
ss.setdefault("send_flag", False)
ss.setdefault("input_key", f"composer_{time.time_ns()}")             # set True when Enter is pressed

def _send_on_enter():
    ss.send_flag = True

# ------------------ Global CSS ------------------
CSS = """
<style>
/* Hide Streamlit's native top header/toolbar so we can use our own bar */
header[data-testid="stHeader"] { display: none !important; }

/* Background with brighter, subtle glows */
.stApp {
  background:
    radial-gradient(1200px 800px at 18% 12%, rgba(99,102,241,0.24), transparent 40%),  /* indigo */
    radial-gradient(1100px 750px at 82% 18%, rgba(255,215,0,0.20), transparent 46%),   /* gold */
    radial-gradient(950px 650px at 46% 78%, rgba(236,72,153,0.22), transparent 52%),   /* magenta */
    linear-gradient(180deg, #0b0f16 0%, #0a0e14 60%, #0a0e14 100%);
}

/* Leave room for our fixed app bar and fixed composer */
.block-container {
  padding-top: 0px;        /* height of our fixed app bar */
  padding-bottom: 15px;    /* >= composer height to avoid overlap */
  padding-left: 20px;
  padding-right: 20px;
  max-width: 1500px;
}

/* ---------- Fixed App Bar ---------- */
.appbar {
  position: fixed; top: 0; left: 0; right: 0;
  z-index: 900;
  backdrop-filter: blur(6px);
  background: rgba(10,14,20,0.65);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.appbar-inner {
  max-width: 1200px; margin: 0 auto; padding: 10px 16px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
/* ~1/8 page width for model select */
.model-box { width: 100%; max-width: 280px; }
.appbar-actions { display: flex; align-items: center; gap: 8px; }

/* ---------- Greeting + 2x2 suggestions ---------- */
.hero-wrap {
  min-height: calc(100vh - 380px);
  display: grid; place-items: center; text-align: center;
}
.hero-inner { max-width: 820px; width: 100%; }
.chips-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 12px; margin-top: 16px; justify-items: center;
}
.chips-grid .stButton button { width: 100%; }

/* ---------- Header ---------- */
.header-row { margin-top: .25rem; }
.model-box .stSelectbox, .model-box .stSelectbox > div, .model-box div[data-baseweb="select"] {
  min-width: 260px !important;
  max-width: 260px !important;
}
.header-right { display:flex; justify-content:flex-end; align-items:center; }

/* ---------- Fixed Composer ---------- */
.composer-shell{
  position: fixed; left:0; right:0; bottom:0; z-index:3000; transform: translateZ(0);
  background: linear-gradient(180deg, rgba(10,14,20,0.00) 0%, rgba(10,14,20,0.72) 35%, rgba(10,14,20,0.96) 100%);
  padding: 10px 0 calc(env(safe-area-inset-bottom,0) + 10px);
}
.composer-inner{ max-width: min(1200px, 96vw); width: 100%; margin: 0 auto; }

/* Style the bordered container we're using for the composer card */
.composer-inner > div[data-testid="stAppViewContainer"] > .st-emotion-cache-1jicfl2 {
  background:rgba(255,255,255,0.04) !important;
  border:1px solid rgba(255,255,255,0.10) !important;
  border-radius: 16px !important;
}

/* Row: ＋ | input | Send */
.plus-btn button { width: 46px; height: 46px; border-radius: 12px; padding: 0; }
.badge{ display:inline-flex; align-items:center; justify-content:center;
  min-width:18px; height:18px; padding:0 4px; font-size:11px; border-radius:999px;
  background:#ef4444; color:#fff; margin-left:6px; }

/* Make st.text_input fill its column and match row height */
.composer-input [data-testid="stTextInput"] > div { width: 100% !important; }
.composer-input input[type="text"]{
  width: 100% !important;
  height: 46px !important;
  line-height: 46px !important;
  border-radius: 12px;
  padding: 0 12px;
  font-size: 16px;
}

/* Gradient Send button aligned with input */
.send-btn button{
  height: 46px !important; border-radius: 999px; border: none;
  background: linear-gradient(90deg, #7c3aed 0%, #f59e0b 100%);
  color: white; font-weight: 600;
}
.send-btn button:hover{ filter: brightness(1.05); }

.brand {
  font-weight: 800; font-size: 40px; letter-spacing: .3px;
  background: linear-gradient(90deg, #7c3aed 0%, #f59e0b 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;

  /* --- VERTICAL & HORIZONTAL CENTERING STYLES --- */
  display: flex; /* Enables flex context */
  justify-content: center; /* Centers horizontally */
  align-items: center; /* Centers vertically */
  height: 100px; /* Define a height for vertical centering to be visible */
}

/* keep this in your CSS */
.composer-shell{
  position: fixed; left:0; right:0; bottom:0;
  z-index: 3000;               /* high enough to float above app content */
  transform: translateZ(0);    /* creates its own layer; cheap perf win */
  /* ... your existing gradient + padding ... */
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------ Fixed App Bar (our header) ------------------
# ------------------ Header: model left, usage right ------------------
st.markdown('<div class="header-row">', unsafe_allow_html=True)
left, spacer, right = st.columns([2, 6, 1], gap="small")

with spacer:
    st.markdown('<div class="brand">Gemini Bot</div>', unsafe_allow_html=True)

with left:
    st.markdown('<div class="model-box">', unsafe_allow_html=True)
    model_choice = st.selectbox(
        "Model",
        options=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash-preview-09-2025",
            "gemini-2.0-flash"
        ],
        index=0,
        help="Choose a Gemini model."
    )
    ss.model_choice = model_choice
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    @st.dialog("Token usage")
    def usage_modal():
        st.write("Per-turn and session totals will appear after model calls.")
        st.metric("Input", st.session_state.usage_totals["input"])
        st.metric("Output", st.session_state.usage_totals["output"])
        st.metric("Reasoning", st.session_state.usage_totals["reasoning"])
    st.markdown('<div class="header-right">', unsafe_allow_html=True)
    if st.button("Usage"):
        usage_modal()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ------------------ Greeting + 2x2 Chips (before first message only) ------------------
if not ss.first_message_sent and len(ss.messages) == 0:
    st.markdown('<div class="hero-inner">', unsafe_allow_html=True)
    st.markdown("## Hello there!")
    st.markdown("#### How can I help you today?")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chips-grid">', unsafe_allow_html=True)
    suggestions = [
        "What are the advantages of using Next.js?",
        "Write code to demonstrate Dijkstra's algorithm",
        "Help me write an essay about Silicon Valley",
        "What is the weather in San Francisco?"
    ]
    cols = st.columns(2, gap="large")
    for i, text in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(text, key=f"sugg_{i}", use_container_width=True):
                ss.composer_input_value = text
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------ Chat Timeline ------------------
for m in ss.messages:
    with st.chat_message(m["role"]):
        if m.get("text"):
            st.markdown(m["text"])
        for att in m.get("attachments", []):
            if att["type"] == "image":
                st.image(att["preview"], caption=att["name"])
            elif att["type"] == "audio":
                st.audio(att["preview"])
            elif att["type"] == "pdf":
                st.write(f"📄 {att['name']} (PDF attached)")

# ------------------ “+” Attach Modal ------------------
@st.dialog("Attach files")
def attach_modal():
    st.write("Files you select here will be attached to **your next message** only.")
    files = st.file_uploader(
        "Upload images, audio, or PDFs",
        type=["png","jpg","jpeg","webp","mp3","wav","m4a","pdf"],
        accept_multiple_files=True,
        key=ss.uploader_key
    )
    if files:
        staged = []
        for f in files:
            data = f.read()
            ext = (f.name.split(".")[-1] or "").lower()
            typ = "image" if ext in ["png","jpg","jpeg","webp"] else ("audio" if ext in ["mp3","wav","m4a"] else "pdf")
            staged.append({"type": typ, "name": f.name, "preview": data, "file_id": None})
        ss.pending_attachments = staged
        st.success(f"Staged {len(staged)} file(s) for the next message.")
        ss.uploader_key = f"uploader_{time.time_ns()}"
    if ss.pending_attachments:
        st.write("Staged:")
        for a in ss.pending_attachments:
            st.markdown(f"<span class='pill' style='display:inline-block;padding:6px 10px;margin:4px 6px 0 0;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.10);border-radius:999px;font-size:13px;'>{a['name']}</span>", unsafe_allow_html=True)

# ------------------ Fixed Composer ------------------
st.markdown('<div id="composer-shell" class="composer-shell"><div class="composer-inner">', unsafe_allow_html=True)

with st.container(border=True):
    
    col_plus, col_text, col_send = st.columns([0.05, 0.89, 0.20], gap="small")
    
    with col_plus:
        st.markdown('<div class="plus-btn">', unsafe_allow_html=True)
        if st.button("＋", key="plus_btn", help="Attach files (opens modal)"):
            attach_modal()
        if ss.pending_attachments:
            st.markdown(f"<span class='badge'>{len(ss.pending_attachments)}</span>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_text:
        st.markdown('<div class="composer-input">', unsafe_allow_html=True)
        ss.composer_input_value = st.text_input(
            "Send a message...",
            value=ss.composer_input_value,
            label_visibility="collapsed",
            key=ss.input_key,
            on_change=_send_on_enter,
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_send:
        st.markdown('<div class="send-btn">', unsafe_allow_html=True)
        send_click = st.button("Send ➤", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True) # Closes composer-shell and composer-inner


# ------------------ Send Handler (Enter or button) ------------------
should_send = ss.send_flag or send_click
if should_send and ss.composer_input_value.strip():
    text = ss.composer_input_value.strip()

    # consume staged files ONCE
    # consume staged files ONCE + upload them to Files API
    msg_attachments = ss.pending_attachments[:] if ss.pending_attachments else []
    ss.pending_attachments = []

    uploaded_refs: list[UploadedRef] = []
    for a in msg_attachments:
        # our structure: {"type": "image"/"audio"/"pdf", "name": ..., "preview": bytes, "file_id": None}
        # decide MIME by type
        mime = (
            "image/png" if a["name"].lower().endswith(".png") else
            "image/jpeg" if a["name"].lower().endswith((".jpg", ".jpeg")) else
            "image/webp" if a["name"].lower().endswith(".webp") else
            "audio/mpeg" if a["name"].lower().endswith(".mp3") else
            "audio/wav"  if a["name"].lower().endswith(".wav") else
            "audio/mp4"  if a["name"].lower().endswith(".m4a") else
            "application/pdf" if a["name"].lower().endswith(".pdf") else
            "application/octet-stream"
        )
        try:
            uploaded_refs.append(upload_bytes(a["name"], a["preview"], mime))
        except Exception as exc:
            st.error(f"Failed to upload '{a['name']}'. You can retry or send without it. Details: {exc}")

    # --- Call Gemini with optional files and push assistant message ---
    reply_text, usage = call_model(ss.model_choice, text, uploads=uploaded_refs)

    ss.messages.append({
        "role": "assistant",
        "text": reply_text or "_(no text response)_",
        "attachments": [],  # assistant may also return files in other flows; not used here
        "model": ss.model_choice,
        "usage": {"input": usage.prompt, "output": usage.response, "reasoning": usage.reasoning, "total": usage.total},
        "ts": time.time()
    })

    # Update the running totals for your Usage dialog
    ss.usage_totals["input"]     += int(usage.prompt or 0)
    ss.usage_totals["output"]    += int(usage.response or 0)
    ss.usage_totals["reasoning"] += int(usage.reasoning or 0)

    # reset input + flag
    ss.composer_input_value = ""
    ss.send_flag = False
    ss.input_key = f"composer_{time.time_ns()}" 
    st.rerun()
