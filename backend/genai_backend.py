# backend/genai_backend.py
from __future__ import annotations
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple, Any, Generator

from google import genai
from google.genai import types, errors

# ---- Public API -------------------------------------------------------------

# Singleton-style client (lazy)
_client: Optional[genai.Client] = None

def get_client(api_key: str | None = None) -> genai.Client:
    """
    Returns a configured GenAI client (Gemini Developer API).
    Resolution order:
      1) explicit api_key argument,
      2) GEMINI_API_KEY environment variable.
    """
    global _client
    if _client is not None:
        return _client

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "Missing API key. Set GEMINI_API_KEY in your environment (or pass api_key)."
        )
    _client = genai.Client(api_key=key)
    return _client

@dataclass
class Usage:
    prompt: int = 0
    response: int = 0
    reasoning: int = 0    # thoughts_token_count if present
    total: int = 0

@dataclass
class UploadedRef:
    """Reference to a File stored by the Files API, ready to be sent to the model."""
    file_obj: types.File  # returned by client.files.upload()
    mime_type: str
    name: str

def upload_bytes(name: str, b: bytes, mime_type: str | None = None) -> UploadedRef:
    """
    Uploads bytes to the Files API by writing them to a temporary file path.
    Adds a robust retry on transient server errors (e.g., 503) and optionally
    polls briefly until the file is 'active' if the SDK exposes that state.
    """
    client = get_client()

    # Keep extension so server can infer MIME
    _, ext = os.path.splitext(name)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext or "")
    try:
        tmp.write(b)
        tmp.flush()
        tmp.close()

        # --- retry with jitter on transient server errors ---
        last_err = None
        for attempt in range(1, 5):  # up to 4 tries
            try:
                f = client.files.upload(file=tmp.name)  # path, not bytes/tuple
                break
            except errors.ServerError as e:
                last_err = e
                # Retry for classic transient codes
                if getattr(e, "status_code", None) in (500, 502, 503, 504) or "Service Unavailable" in str(e):
                    sleep_s = min(1.0 * attempt + (0.25 * (attempt ** 0.5)), 4.0)
                    time.sleep(sleep_s)
                    continue
                raise
        else:
            raise last_err or RuntimeError("Upload failed after retries")

        # --- optional: brief poll until file becomes usable ---
        file_id = getattr(f, "id", None)
        state   = getattr(f, "state", None)
        if file_id and state:
            for _ in range(12):  # ~ up to ~6s
                if str(state).upper() in ("ACTIVE", "READY", "SUCCEEDED"):
                    break
                time.sleep(0.5)
                f = client.files.get(file_id)
                state = getattr(f, "state", None)

        return UploadedRef(file_obj=f, mime_type=(mime_type or ""), name=name)

    finally:
        try:
            os.remove(tmp.name)
        except Exception:
            pass


def build_contents(prompt: str, uploads: Iterable[UploadedRef] | None) -> list[Any]:
    """
    Return a mixed list accepted by the SDK:
    - a plain string for text
    - File objects for uploaded files
    """
    parts: list[Any] = [prompt]
    if uploads:
        for u in uploads:
            parts.append(u.file_obj)   # SDK accepts the File directly
    return parts

# The following currently not in sure, but can be used to replace the stream_model when streaming is not needed
def call_model(model: str, prompt: str, uploads: Iterable[UploadedRef] | None = None) -> Tuple[str, Usage]:
    """
    Non-streaming call. Returns (text, Usage).
    """
    client = get_client()
    contents = build_contents(prompt, uploads)
    resp = client.models.generate_content(model=model, contents=contents)
    text = getattr(resp, "text", "") or ""
    u = getattr(resp, "usage_metadata", None)

    usage = Usage()
    if u:
        # Different SDKs / responses expose different names.
        prompt  = (
            getattr(u, "prompt_token_count", 0)
            or getattr(u, "input_token_count", 0)
            or getattr(u, "input_tokens", 0)
            or 0
        )
        output  = (
            getattr(u, "response_token_count", 0)
            or getattr(u, "candidates_token_count", 0)
            or getattr(u, "output_token_count", 0)
            or getattr(u, "output_tokens", 0)
            or 0
        )
        reasoning = (
            getattr(u, "thoughts_token_count", 0)
            or getattr(u, "reasoning_tokens", 0)
            or 0
        )
        total = (
            getattr(u, "total_token_count", 0)
            or prompt + output + reasoning
        )
        usage.prompt = int(prompt or 0)
        usage.response = int(output or 0)
        usage.reasoning = int(reasoning or 0)
        usage.total = int(total or 0)

    return text, usage

def stream_model(model: str, prompt: str, uploads: Iterable[UploadedRef] | None = None
                 ) -> Generator[tuple[str, Any], None, None]:
    """
    Streaming generator.
    Yields ('chunk', text_fragment) many times, then finally ('usage', Usage).
    Falls back to non-streaming if stream is not supported by the SDK.
    """
    client = get_client()
    contents = build_contents(prompt, uploads)
    usage = Usage()

    stream = client.models.generate_content_stream(model=model, contents=contents)

    for event in stream:
        # Some SDK builds deliver partial text on .text, some via candidate parts.
        txt = getattr(event, "text", None)
        if not txt:
            # fall back to parts aggregation if needed
            try:
                cands = getattr(event, "candidates", None)
                if cands:
                    parts = getattr(cands[0].content, "parts", None) or []
                    txt = "".join(getattr(p, "text", "") for p in parts)
            except Exception:
                txt = None

        if txt:
            yield txt

        um = getattr(event, "usage_metadata", None)
        if um:
            # Different SDKs / responses expose different names.
            prompt  = (
                getattr(um, "prompt_token_count", 0)
                or getattr(um, "input_token_count", 0)
                or getattr(um, "input_tokens", 0)
                or 0
            )
            output  = (
                getattr(um, "response_token_count", 0)
                or getattr(um, "candidates_token_count", 0)
                or getattr(um, "output_token_count", 0)
                or getattr(um, "output_tokens", 0)
                or 0
            )
            reasoning = (
                getattr(um, "thoughts_token_count", 0)
                or getattr(um, "reasoning_tokens", 0)
                or 0
            )
            total = (
                getattr(um, "total_token_count", 0)
                or prompt + output + reasoning
            )
            usage.prompt = int(prompt or 0)
            usage.response = int(output or 0)
            usage.reasoning = int(reasoning or 0)
            usage.total = int(total or 0)

    # final signal with usage
    yield {"usage": usage}
