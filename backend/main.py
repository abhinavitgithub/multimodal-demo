from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import re
import traceback

app = FastAPI()

# --------------------------
# CORS
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://multimodal-frontend2.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# CONFIG
# --------------------------
NVIDIA_API_KEY = "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"
MODEL          = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


# --------------------------
# HELPERS
# --------------------------

def extract_content(message: dict) -> str:
    """
    Pull visible answer text from a message/delta dict.

    Priority order:
      1. message["content"] after stripping <think>…</think> blocks
         (reasoning models hide their chain-of-thought here)
      2. The raw <think> block itself if nothing follows it
         (model spent all tokens on reasoning — surface what we have)
      3. message["reasoning_content"]  (explicit reasoning field)
      4. Empty string  (genuine blank)
    """

    # ── 1. Primary content field ─────────────────────────────────────────────
    raw_content: str = message.get("content") or ""
    raw_content = raw_content.strip()

    if raw_content:
        # Strip ALL <think>…</think> blocks (can be nested or repeated)
        without_think = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()

        if without_think:
            # Happy path — there IS text after the reasoning block
            return without_think

        # Content existed but was *only* a <think> block with nothing after it.
        # The model used all its token budget on reasoning. Surface the reasoning
        # so the user gets something useful instead of a blank screen.
        think_match = re.search(r"<think>(.*?)</think>", raw_content, flags=re.DOTALL)
        if think_match:
            inner = think_match.group(1).strip()
            if inner:
                return f"[Reasoning trace — model ran out of tokens before answering]\n\n{inner}"

        # Content was a non-empty string but had no <think> and stripped to "".
        # Return it raw just in case.
        return raw_content

    # ── 2. Explicit reasoning_content field (some NVIDIA model versions) ─────
    reasoning: str = message.get("reasoning_content") or ""
    reasoning = reasoning.strip()
    if reasoning:
        return f"[Reasoning trace]\n\n{reasoning}"

    return ""


def safe_json_dump(obj, max_chars: int = 2000) -> str:
    """Pretty-print JSON, truncated so logs don't explode."""
    try:
        text = json.dumps(obj, indent=2, ensure_ascii=False)
        if len(text) > max_chars:
            return text[:max_chars] + f"\n… [truncated — {len(text)} chars total]"
        return text
    except Exception:
        return repr(obj)[:max_chars]


# --------------------------
# HOME
# --------------------------
@app.get("/")
def home():
    return {"message": "Backend running successfully"}


# --------------------------
# TEXT
# --------------------------
@app.post("/text")
async def text_query(prompt: str = Form(...)):

    print(f"\n{'='*60}")
    print(f"[/text] Prompt ({len(prompt)} chars): {repr(prompt[:200])}")

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    # max_tokens must be generous enough for reasoning trace + actual answer.
    # Reasoning models consume hundreds of tokens on chain-of-thought alone.
    # 2048 is a safe minimum; raise if you need longer articles.
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2048,
        "temperature": 0.6,
    }

    # ── Call NVIDIA API ──────────────────────────────────────────────────────
    try:
        print(f"[/text] Sending to NVIDIA API …")
        raw = requests.post(
            NVIDIA_API_URL,
            headers=headers,
            json=payload,
            timeout=45,   # reasoning models are slow; 20 s was too tight
        )
        print(f"[/text] NVIDIA HTTP status: {raw.status_code}")

    except requests.exceptions.Timeout:
        print("[/text] ERROR: NVIDIA request timed out")
        return {"response": "The AI model took too long to respond. Please try again."}

    except requests.exceptions.ConnectionError as exc:
        print(f"[/text] ERROR: Connection error — {exc}")
        return {"response": "Could not reach the AI model. Check your connection and retry."}

    except Exception as exc:
        print(f"[/text] ERROR: Unexpected exception — {exc}")
        traceback.print_exc()
        return {"response": "Unexpected error contacting the AI model. Please retry."}

    # ── Parse JSON body ──────────────────────────────────────────────────────
    try:
        data = raw.json()
        print(f"[/text] Response body:\n{safe_json_dump(data)}")
    except Exception:
        snippet = raw.text[:500]
        print(f"[/text] ERROR: Body is not valid JSON. Raw text: {snippet}")
        return {"response": f"AI model returned an unreadable response (HTTP {raw.status_code}). Please retry."}

    # ── Non-200 ──────────────────────────────────────────────────────────────
    if raw.status_code != 200:
        detail = (
            data.get("detail")
            or data.get("message")
            or (data.get("error") or {}).get("message")
            or f"HTTP {raw.status_code}"
        )
        print(f"[/text] Non-200 detail: {detail}")
        return {"response": f"AI model error: {detail}. Please retry."}

    # ── Extract answer from choices ──────────────────────────────────────────
    try:
        choices = data.get("choices")

        if not choices or not isinstance(choices, list) or len(choices) == 0:
            print("[/text] WARNING: 'choices' is missing or empty")
            # Last-ditch: sometimes the model puts content at top level
            top_content = data.get("content") or data.get("text") or ""
            if top_content:
                print(f"[/text] Found top-level content ({len(top_content)} chars) — using it")
                return {"response": top_content.strip()}
            return {"response": "AI model returned an empty response. Please retry."}

        first_choice = choices[0]
        print(f"[/text] first_choice keys: {list(first_choice.keys())}")
        print(f"[/text] finish_reason: {first_choice.get('finish_reason')}")

        # finish_reason "length" means max_tokens was hit mid-output
        finish_reason = first_choice.get("finish_reason", "")
        if finish_reason == "length":
            print("[/text] WARNING: finish_reason=length — output was truncated")

        # Support both non-streaming (message) and streaming (delta) shapes
        message = first_choice.get("message") or first_choice.get("delta") or {}
        print(f"[/text] message keys: {list(message.keys())}")

        content = extract_content(message)
        print(f"[/text] Extracted content length: {len(content)} chars")

        if content:
            # Append a note if the output was cut short
            if finish_reason == "length":
                content += "\n\n[Note: response was cut short — try a shorter prompt or request less text.]"
            print(f"[/text] SUCCESS — returning {len(content)} chars")
            return {"response": content}

        # Absolute last resort: dump the raw choice so we can debug in production
        raw_choice_text = safe_json_dump(first_choice, max_chars=800)
        print(f"[/text] FALLBACK: returning raw choice dump")
        return {"response": f"The model responded but content could not be extracted. Raw data:\n{raw_choice_text}"}

    except Exception as exc:
        print(f"[/text] ERROR: Failed to extract content — {exc}")
        traceback.print_exc()
        return {"response": "Could not parse AI model response. Please retry."}


# --------------------------
# IMAGE
# --------------------------
@app.post("/image")
async def image_query(file: UploadFile = File(...)):
    print(f"[/image] Received: {file.filename}")
    return {"response": f"Image uploaded successfully: {file.filename}"}


# --------------------------
# AUDIO
# --------------------------
@app.post("/audio")
async def audio_query(file: UploadFile = File(...)):
    print(f"[/audio] Received: {file.filename}")
    return {"response": f"Audio uploaded successfully: {file.filename}"}


# --------------------------
# VIDEO
# --------------------------
@app.post("/video")
async def video_query(file: UploadFile = File(...)):
    print(f"[/video] Received: {file.filename}")
    return {"response": f"Video uploaded successfully: {file.filename}"}
