import time
import os
import streamlit as st
from dotenv import load_dotenv
from frontend.scroll import scroll_smooth_once


from backend.genai_backend import (
    get_client, upload_bytes, stream_model, UploadedRef
)

# ---- Env & client ----
load_dotenv(override=True)
API_KEY = os.environ.get("GEMINI_API_KEY")
if API_KEY:
    _ = get_client(api_key=API_KEY)
else:
    # We'll warn *after* set_page_config to avoid Streamlit's "must be first" issue.
    pass

# ------------------ Page setup ------------------
st.set_page_config(page_title="Gemini Chat", page_icon="💬", layout="wide")

if not API_KEY:
    st.warning("Set GEMINI_API_KEY in your environment (or .env) to use the app.")

# ------------------ Session State ------------------
ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("first_message_sent", False)
ss.setdefault("usage_totals", {"input": 0, "output": 0, "reasoning": 0})
ss.setdefault("pending_attachments", [])        # pre-send bytes
ss.setdefault("uploader_key", f"uploader_{time.time_ns()}")
ss.setdefault("composer_input_value", "")
ss.setdefault("model_choice", "gemini-2.5-flash")
ss.setdefault("send_flag", False)
ss.setdefault("input_key", f"composer_{time.time_ns()}")
# NEW: persistent uploaded files library (usable across turns)
ss.setdefault("file_refs", [])                  # list[UploadedRef]
ss.setdefault("pending_request", None)   # holds the request that will be fulfilled next run
ss.setdefault("staged_files", [])        # used in the modal before "Attach"
ss.setdefault("session_file_refs", [])     # list[UploadedRef] persisted across the session
ss.setdefault("session_file_ids", set())   # to dedupe by file id

def _send_on_enter():
    ss.send_flag = True

# ---- Build a lightweight "history" prompt for persistence ----
def _build_history_prompt(messages, max_turns=6, max_chars=6000) -> str:
    """
    Render the last few turns as plain text so the stateless model
    keeps context across requests.
    """
    if not messages:
        return "You are a helpful AI assistant."

    blocks = ["You are a helpful AI assistant. The following is the recent chat history.\n"]
    # only the last N turns
    for m in messages[-max_turns:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        text = m.get("text") or ""
        # mention attachments by name (the actual files are sent via Files API)
        if m.get("attachments"):
            att_list = ", ".join((a or {}).get("name", "file") for a in m["attachments"])
            text = f"{text}\n[Attached files: {att_list}]"
        blocks.append(f"{role}: {text}\n")

    history = "\n".join(blocks)
    # Trim if overly long
    if len(history) > max_chars:
        history = history[-max_chars:]
    return history


# ------------------ Global CSS ------------------
CSS = """
<style>
header[data-testid="stHeader"] { display: none !important; }

.stApp {
  background:
    radial-gradient(1200px 800px at 18% 12%, rgba(99,102,241,0.24), transparent 40%),
    radial-gradient(1100px 750px at 82% 18%, rgba(255,215,0,0.20), transparent 46%),
    radial-gradient(950px 650px at 46% 78%, rgba(236,72,153,0.22), transparent 52%),
    linear-gradient(180deg, #0b0f16 0%, #0a0e14 60%, #0a0e14 100%);
}

.block-container {
  padding-top: 0px;
  padding-bottom: 15px;
  padding-left: 100px;
  padding-right: 100px;
  max-width: 1500px;
}

.header-row { margin-top: .25rem; }
.model-box .stSelectbox, .model-box .stSelectbox > div, .model-box div[data-baseweb="select"] {
  min-width: 260px !important;
  max-width: 260px !important;
}
.header-right { display:flex; justify-content:flex-end; align-items:center; }

.brand {
  font-weight: 800; font-size: 40px; letter-spacing: .3px;
  background: linear-gradient(90deg, #7c3aed 0%, #f59e0b 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  display: flex; justify-content: center; align-items: center;
  height: 100px;
}

/* Fixed composer (single definition) */
.composer-shell{
  position: fixed; left:0; right:0; bottom:0; z-index:3000; transform: translateZ(0);
  background: linear-gradient(180deg, rgba(10,14,20,0.00) 0%, rgba(10,14,20,0.72) 35%, rgba(10,14,20,0.96) 100%);
  padding: 10px 0 calc(env(safe-area-inset-bottom,0) + 10px);
}
.composer-inner{ max-width: min(1200px, 96vw); width: 100%; margin: 0 auto; }

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

.composer-input [data-testid="stTextInput"] > div { width: 100% !important; }
.composer-input input[type="text"]{
  width: 100% !important;
  height: 46px !important;
  line-height: 46px !important;
  border-radius: 12px; padding: 0 12px; font-size: 16px;
}

/* Send button */
.send-btn button{
  height: 46px !important; border-radius: 999px; border: none;
  background: linear-gradient(90deg, #7c3aed 0%, #f59e0b 100%);
  color: white; font-weight: 600;
}
.send-btn button:hover{ filter: brightness(1.05); }

/* Pre-send preview area */
.staged-preview {
  margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap;
}
.staged-pill {
  background: rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12);
  border-radius: 12px; padding: 6px 10px; font-size: 13px;
}

/* small preview bar for attached files (shows in composer before send) */
.preview-bar {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  margin-bottom: 6px;
}
.preview-pill {
  display:inline-flex; align-items:center; gap:8px;
  padding: 6px 10px; border-radius: 999px;
  background: rgba(255,255,255,0.06);
  border:1px solid rgba(255,255,255,0.10);
  font-size: 13px;
}
.preview-thumb { width: 24px; height: 24px; object-fit: cover; border-radius: 6px; }

/* floating scroll-to-bottom button */
.scroll-down-btn{
  position: fixed; right: 18px; bottom: 86px;
  z-index: 9999;                       /* above composer */
  border: 0; border-radius: 999px; padding: 10px 12px;
  background: linear-gradient(90deg, #7c3aed 0%, #f59e0b 100%);
  color: #fff; font-weight: 700; box-shadow: 0 6px 18px rgba(0,0,0,.35);
  cursor: pointer;
  opacity: 1; transform: scale(1); transition: opacity .18s, transform .18s;
  pointer-events: auto;
}
.scroll-down-btn.hidden{
  opacity: 0; transform: scale(.96); pointer-events: none;
}
.scroll-down-btn:hover{ filter:brightness(1.05); }

/* thinking loader: three pulsing dots */
@keyframes blink { 0%{opacity:.2} 20%{opacity:1} 100%{opacity:.2} }
.dot { animation: blink 1.4s infinite both; }
.dot:nth-child(2){ animation-delay: .2s; }
.dot:nth-child(3){ animation-delay: .4s; }

.hero-inner {
  text-align: center;
}

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------ Header ------------------
st.markdown('<div class="header-row">', unsafe_allow_html=True)
left, spacer, right = st.columns([2, 6, 2], gap="small")

with spacer:
    st.markdown('<div class="brand">Aurora Chat</div>', unsafe_allow_html=True)

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
        c1, c2, c3 = st.columns(3)
        c1.metric("Input", int(ss.usage_totals["input"]))
        c2.metric("Output", int(ss.usage_totals["output"]))
        c3.metric("Reasoning", int(ss.usage_totals["reasoning"]))
    st.markdown('<div class="header-right">', unsafe_allow_html=True)
    
    # Add two mini buttons: Clear Pins and Usage
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Clear pinned files", help="Stop sending previous files with new questions"):
            ss.session_file_refs = []
            ss.session_file_ids = set()
            st.rerun()
    with c2:
        if st.button("Usage"):
            usage_modal()
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)



# ------------------ Greeting + suggestions (first run only) ------------------
if not ss.first_message_sent and len(ss.messages) == 0:
    st.markdown("""
<div class="hero-inner">
    <h2>Hello there!</h2>
    <h4>How can I help you today?</h4>
</div>
""", unsafe_allow_html=True)

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

        # Show attachments for USER messages inside the bubble
        if m.get("role") == "user":
            atts = m.get("attachments") or []
            if atts:
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            for att in atts:
                t = (att or {}).get("type")
                data = (att or {}).get("preview")
                name = (att or {}).get("name", "")
                if t == "image" and isinstance(data, (bytes, bytearray)):
                    # deprecation-safe: use width instead of use_container_width/use_column_width
                    st.image(data, caption=name, width="content")
                elif t == "audio" and isinstance(data, (bytes, bytearray)):
                    st.audio(data)
                elif t == "pdf":
                    st.write(f"📄 {name} (PDF attached)")



# ------------------ Pending request: show "Thinking..." and fulfill (STREAMING) ------------------
if ss.get("pending_request"):
    req = ss.pending_request


    # 1) show the thinking bubble right under the last user message
    with st.chat_message("assistant"):
        ph = st.empty()
        # loader (visible until first tokens arrive)
        ph.markdown("**Thinking**<span class='dot'>.</span><span class='dot'>.</span><span class='dot'>.</span>", unsafe_allow_html=True)

        scroll_smooth_once()

        # 2) upload files, then stream the model output into `ph`
        uploaded_refs: list[UploadedRef] = []
        # include files that are already pinned in the session
        session_refs: list[UploadedRef] = list(ss.session_file_refs or [])
        try:
            for a in (req.get("attachments") or []):
                # Ensure dict shape — avoids "tuple indices" if something odd slipped in
                if not isinstance(a, dict):
                    continue
                name = a.get("name", "file.bin")
                data = a.get("preview")
                if not isinstance(data, (bytes, bytearray)):
                    continue

                lname = name.lower()
                mime = (
                    "image/png" if lname.endswith(".png") else
                    "image/jpeg" if lname.endswith((".jpg", ".jpeg")) else
                    "image/webp" if lname.endswith(".webp") else
                    "audio/mpeg" if lname.endswith(".mp3") else
                    "audio/wav"  if lname.endswith(".wav") else
                    "audio/mp4"  if lname.endswith(".m4a") else
                    "application/pdf" if lname.endswith(".pdf") else
                    "application/octet-stream"
                )
                uploaded_refs.append(upload_bytes(name, data, mime))
                # ---- pin uploaded file in session for persistence across turns ----
                last = uploaded_refs[-1]
                # Build a small set of existing ids (fallback to object id if API doesn't expose .id)
                existing_ids = {
                    (getattr(r.file_obj, "id", None) or str(id(r.file_obj)))
                    for r in (ss.session_file_refs or [])
                }
                new_id = (getattr(last.file_obj, "id", None) or str(id(last.file_obj)))
                if new_id not in existing_ids:
                    ss.session_file_refs.append(last)
                # cap to last 6 files to avoid unbounded growth
                ss.session_file_refs = ss.session_file_refs[-6:]

            # STREAM!
            full_text = ""
            final_usage = None

            # union: previously pinned files + just-uploaded
            all_refs = (session_refs + uploaded_refs) if session_refs else uploaded_refs

            # prepend short history so the model remembers the last turns
            prompt_text = (req.get("history") or "You are a helpful AI assistant.") \
                        + "\n\nUser: " + req["text"] + "\nAssistant:"

            for ev in stream_model(req["model"], prompt_text, uploads=all_refs):
                if isinstance(ev, dict) and "usage" in ev:
                    final_usage = ev["usage"]
                    break
                # ev is a chunk of text
                chunk = str(ev)
                if chunk:
                    full_text += chunk
                    ph.markdown(full_text)
                    # keep view following while streaming (no timers)
                    #scroll_smooth_once()

            # 3) replace the thinking bubble with the final streamed content in history
            ss.messages.append({
                "role": "assistant",
                "text": full_text or "_(no text response)_",
                "attachments": [],
                "model": req["model"],
                "usage": {
                    "input": final_usage.prompt if final_usage else 0,
                    "output": final_usage.response if final_usage else 0,
                    "reasoning": final_usage.reasoning if final_usage else 0,
                    "total": final_usage.total if final_usage else 0
                },
                "ts": time.time()
            })

            if final_usage:
                ss.usage_totals["input"]     += int(final_usage.prompt or 0)
                ss.usage_totals["output"]    += int(final_usage.response or 0)
                ss.usage_totals["reasoning"] += int(final_usage.reasoning or 0)
            scroll_smooth_once()


        except Exception as exc:
            kind = exc.__class__.__name__
            msg  = str(exc)
            friendly = "The model is unavailable at the moment."
            if "429" in msg or "ResourceExhausted" in msg:
                friendly = "This model is currently rate-limited. Try again in a moment or switch models."
            elif "503" in msg or "Service Unavailable" in msg:
                friendly = "Service is temporarily unavailable. Retrying later usually helps."
            elif "400" in msg:
                friendly = "The request wasn’t accepted. Please simplify the prompt or try a different file."

            ph.markdown(f"⚠️ {friendly}\n\n`{kind}: {msg}`")

            ss.messages.append({
                "role": "assistant",
                "text": f"⚠️ {friendly}\n\n`{kind}: {msg}`",
                "attachments": [],
                "model": req["model"],
                "usage": {},
                "ts": time.time()
            })
            scroll_smooth_once()

        finally:
            ss.pending_request = None
            st.rerun()

# === Bottom sentinel (anchor for smooth scroll) ===
st.markdown("<div id='chat-bottom-sentinel' style='height:1px'></div>", unsafe_allow_html=True)


# ------------------ Attach Modal ------------------
@st.dialog("Attach files")
def attach_modal():
    st.write("Files you select here will be attached to **your next message** only after you click **Attach**.")
    files = st.file_uploader(
        "Upload images, audio, or PDFs",
        type=["png","jpg","jpeg","webp","mp3","wav","m4a","pdf"],
        accept_multiple_files=True,
        key=ss.uploader_key
    )

    # Use a temporary list while the dialog is open
    staged = []
    if files:
        for f in files:
            data = f.read()
            ext = (f.name.split(".")[-1] or "").lower()
            typ = "image" if ext in ["png","jpg","jpeg","webp"] else ("audio" if ext in ["mp3","wav","m4a"] else "pdf")
            staged.append({"type": typ, "name": f.name, "preview": data, "file_id": None})

    # Remember the staged selection in state so rerenders of the dialog don't lose it
    if staged:
        ss.staged_files = staged

    if ss.staged_files:
        st.success(f"Staged {len(ss.staged_files)} file(s). They will be attached only if you click **Attach**.")
        st.write("Staged:")
        for a in ss.staged_files:
            st.markdown(
                f"<span class='pill' style='display:inline-block;padding:6px 10px;margin:4px 6px 0 0;"
                f"background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.10);"
                f"border-radius:999px;font-size:13px;'>{a['name']}</span>",
                unsafe_allow_html=True,
            )

    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Attach", type="primary"):
            # promote staged → pending (composer shows previews right away)
            ss.pending_attachments = ss.staged_files[:]
            ss.staged_files = []
            # rotate uploader key so dialog is fresh next time
            ss.uploader_key = f"uploader_{time.time_ns()}"
            st.rerun()
    with c2:
        if st.button("Cancel"):
            # discard staging
            ss.staged_files = []
            st.rerun()



# ------------------ Composer ------------------
st.markdown('<div id="composer-shell" class="composer-shell"><div class="composer-inner">', unsafe_allow_html=True)
with st.container(border=True):

    # --- show previews for files the user attached (before sending) ---
    if ss.pending_attachments:
        st.markdown("<div class='preview-bar'>", unsafe_allow_html=True)
        for a in ss.pending_attachments:
            # tiny image thumb if it's an image, otherwise just a pill
            if a["type"] == "image":
                # small inline <img> using base64
                import base64
                b64 = base64.b64encode(a["preview"]).decode("ascii")
                st.markdown(
                    f"<span class='preview-pill'>"
                    f"<img class='preview-thumb' src='data:image/*;base64,{b64}'/>"
                    f"{a['name']}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<span class='preview-pill'>📎 {a['name']}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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

st.markdown('</div></div>', unsafe_allow_html=True)

# ------------------ Send Handler (Enter or button) ------------------
should_send = ss.send_flag or send_click
if should_send and ss.composer_input_value.strip():
    text = ss.composer_input_value.strip()

    # Capture and clear attachments optimistically
    msg_attachments = ss.pending_attachments[:] if ss.pending_attachments else []
    ss.pending_attachments = []

    # 1) push the USER message immediately (so you see it right away)
    ss.messages.append({
        "role": "user",
        "text": text,
        "attachments": msg_attachments,
        "model": ss.model_choice,
        "usage": {},
        "ts": time.time()
    })
    ss.first_message_sent = True

    # 2) queue a pending request for the next run (model work + assistant message)
    hist = []
    for m in ss.messages[-6:]:
        if not m.get("text"):
            continue
        hist.append({"role": m.get("role", "user"), "text": m["text"]})

    ss.pending_request = {
    "text": text,
    "attachments": msg_attachments,
    "model": ss.model_choice,
    "history": _build_history_prompt(ss.messages)  # <-- NEW
    }

    # 3) clear composer immediately
    ss.composer_input_value = ""
    ss.send_flag = False
    ss.input_key = f"composer_{time.time_ns()}"

    st.rerun()
