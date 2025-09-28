import time
import streamlit as st

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
ss.setdefault("send_flag", False)             # set True when Enter is pressed

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
  padding-top: 64px;        /* height of our fixed app bar */
  padding-bottom: 300px;    /* >= composer height to avoid overlap */
  max-width: 1200px;
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
.model-box { width: clamp(220px, 12.5vw, 320px); }
.model-box [data-testid="stSelectbox"] { width: 100% !important; }
.model-box [data-testid="stSelectbox"] > div { width: 100% !important; }
.model-box [data-baseweb="select"] { width: 100% !important; }
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

/* ---------- Fixed Composer ---------- */
.composer-shell{
  position: fixed; left:0; right:0; bottom:0; z-index:1000;
  background: linear-gradient(180deg, rgba(10,14,20,0.00) 0%, rgba(10,14,20,0.72) 35%, rgba(10,14,20,0.96) 100%);
  padding: 10px 0 calc(env(safe-area-inset-bottom,0) + 10px);
}
.composer-inner{ max-width: min(1200px, 96vw); width: 100%; margin: 0 auto; padding: 0 16px; }
.composer-card{
  border-radius:16px; padding:10px; background:rgba(255,255,255,0.04);
  border:1px solid rgba(255,255,255,0.10);
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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------ Fixed App Bar (our header) ------------------
st.markdown('<div class="appbar"><div class="appbar-inner">', unsafe_allow_html=True)

# Left: model dropdown (clamped width)
st.markdown('<div class="model-box">', unsafe_allow_html=True)
ss.model_choice = st.selectbox(
    "Model",
    ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-preview-09-2025", "gemini-2.0-flash"],
    index=["gemini-2.5-flash","gemini-2.5-pro","gemini-2.5-flash-preview-09-2025","gemini-2.0-flash"].index(ss.model_choice),
    help="Choose a Gemini model.",
)
st.markdown('</div>', unsafe_allow_html=True)

# Right: Usage button
st.markdown('<div class="appbar-actions">', unsafe_allow_html=True)

@st.dialog("Token usage")
def usage_modal():
    c1, c2, c3 = st.columns(3)
    c1.metric("Input", ss.usage_totals["input"])
    c2.metric("Output", ss.usage_totals["output"])
    c3.metric("Reasoning", ss.usage_totals["reasoning"])

if st.button("Usage"):
    usage_modal()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div></div>', unsafe_allow_html=True)

# ------------------ Greeting + 2x2 Chips (before first message only) ------------------
if not ss.first_message_sent and len(ss.messages) == 0:
    st.markdown('<div class="hero-wrap"><div class="hero-inner">', unsafe_allow_html=True)
    st.markdown("## Hello there!")
    st.markdown("#### How can I help you today?")
    st.markdown('</div></div>', unsafe_allow_html=True)

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
st.markdown('<div class="composer-shell"><div class="composer-inner"><div class="composer-card">', unsafe_allow_html=True)

col_plus, col_text, col_send = st.columns([0.08, 0.72, 0.20], gap="small")

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
        key="composer_input_widget",
        on_change=_send_on_enter,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col_send:
    st.markdown('<div class="send-btn">', unsafe_allow_html=True)
    send_click = st.button("Send ➤", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div></div></div>', unsafe_allow_html=True)

# ------------------ Send Handler (Enter or button) ------------------
should_send = ss.send_flag or send_click
if should_send and ss.composer_input_value.strip():
    text = ss.composer_input_value.strip()

    # consume staged files ONCE
    msg_attachments = ss.pending_attachments[:] if ss.pending_attachments else []
    ss.pending_attachments = []

    ss.messages.append({
        "role": "user",
        "text": text,
        "attachments": msg_attachments,
        "model": ss.model_choice,
        "usage": {"input": None, "output": None, "reasoning": None, "source": None},
        "ts": time.time()
    })
    ss.first_message_sent = True

    # reset input + flag
    ss.composer_input_value = ""
    ss.send_flag = False
    st.rerun()
