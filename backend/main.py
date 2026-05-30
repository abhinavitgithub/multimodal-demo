from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import requests
import json
import traceback
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

app = FastAPI()

# --------------------------
# CORS
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# CONFIG
# --------------------------
NVIDIA_API_KEY       = "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"
MODEL                = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
NVIDIA_API_URL       = "https://integrate.api.nvidia.com/v1/chat/completions"

CONNECT_TIMEOUT      = 15    # seconds to establish connection
READ_TIMEOUT         = 300   # seconds to wait for data between chunks
MAX_TOKENS           = 4096  # enough for 500-800 word responses with reasoning tokens
EMPTY_STREAM_RETRIES = 2     # max retries when model returns 200 OK but zero content


# --------------------------
# HELPERS
# --------------------------

def strip_think_tags(text: str) -> str:
    text = text.replace("<think>", "").replace("</think>", "")
    return text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError,
                                   requests.exceptions.Timeout,
                                   requests.exceptions.ChunkedEncodingError)),
    reraise=True,
)
def _open_nvidia_stream(prompt: str) -> requests.Response:
    """Open the SSE streaming connection to NVIDIA with retry logic."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.6,
        "stream": True,
    }
    raw = requests.post(
        NVIDIA_API_URL,
        headers=headers,
        json=payload,
        stream=True,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )
    return raw


def _consume_stream(prompt: str, attempt: int, request_start: float):
    """
    Consume one SSE stream attempt.
    Returns (chunks_yielded: list[str], finished_cleanly: bool, error_kind: str|None).
    chunks_yielded is empty if the model returned no content.
    """
    chunks_yielded     = []
    first_token_logged = False

    print(f"[/text] Stream attempt {attempt} — opening connection")

    try:
        raw = _open_nvidia_stream(prompt)
    except requests.exceptions.ConnectionError as exc:
        print(f"[/text] EXCEPTION ConnectionError after retries: {exc}")
        return chunks_yielded, False, "connection"
    except requests.exceptions.Timeout:
        print("[/text] EXCEPTION Timeout after retries")
        return chunks_yielded, False, "timeout"
    except Exception as exc:
        print(f"[/text] EXCEPTION unexpected while opening stream: {exc}")
        traceback.print_exc()
        return chunks_yielded, False, "unexpected"

    print(f"[/text] NVIDIA HTTP status: {raw.status_code}")

    if raw.status_code != 200:
        try:
            err_body = raw.json()
        except Exception:
            err_body = {"raw": raw.text[:400]}
        detail = (
            err_body.get("detail")
            or err_body.get("message")
            or (err_body.get("error") or {}).get("message")
            or f"HTTP {raw.status_code}"
        )
        print(f"[/text] NVIDIA error: {detail}")
        return chunks_yielded, False, f"http:{detail}"

    try:
        for raw_line in raw.iter_lines(decode_unicode=True):
            if not raw_line:
                continue

            if not raw_line.startswith("data: "):
                print(f"[/text] Skipping non-data line: {raw_line[:80]}")
                continue

            data_str = raw_line[6:].strip()

            if data_str == "[DONE]":
                elapsed = time.time() - request_start
                print(f"[/text] STREAM COMPLETE (attempt {attempt}) — "
                      f"{len(chunks_yielded)} chunks, {elapsed:.2f}s")
                return chunks_yielded, True, None

            try:
                chunk_json = json.loads(data_str)
            except json.JSONDecodeError:
                print(f"[/text] Skipping non-JSON SSE data: {data_str[:120]}")
                continue

            try:
                choices = chunk_json.get("choices")
                if not choices or not isinstance(choices, list):
                    continue
                delta = choices[0].get("delta")
                if not delta or not isinstance(delta, dict):
                    continue
                content = delta.get("content")
                if not content or not isinstance(content, str):
                    continue
            except Exception as parse_exc:
                print(f"[/text] Delta parse error: {parse_exc} — raw: {data_str[:120]}")
                continue

            visible = strip_think_tags(content)
            if not visible:
                continue

            if not first_token_logged:
                elapsed_first = time.time() - request_start
                print(f"[/text] FIRST TOKEN (attempt {attempt}) at {elapsed_first:.2f}s")
                first_token_logged = True

            n = len(chunks_yielded) + 1
            if n <= 5 or n % 50 == 0:
                print(f"[/text] chunk {n:05d} "
                      f"({len(visible):3d} chars): {repr(visible[:60])}")

            chunks_yielded.append(visible)

    except requests.exceptions.ChunkedEncodingError as exc:
        elapsed = time.time() - request_start
        print(f"[/text] EXCEPTION ChunkedEncodingError at {elapsed:.2f}s: {exc}")
        return chunks_yielded, False, "chunked"

    except requests.exceptions.ReadTimeout as exc:
        elapsed = time.time() - request_start
        print(f"[/text] EXCEPTION ReadTimeout at {elapsed:.2f}s "
              f"after {len(chunks_yielded)} chunks: {exc}")
        return chunks_yielded, False, "read_timeout"

    except Exception as exc:
        elapsed = time.time() - request_start
        print(f"[/text] EXCEPTION unexpected during stream at "
              f"{time.time() - request_start:.2f}s: {exc}")
        traceback.print_exc()
        return chunks_yielded, False, "unexpected"

    finally:
        try:
            raw.close()
        except Exception:
            pass

    return chunks_yielded, True, None


def stream_nvidia_response(prompt: str):
    """
    Generator that yields incremental text chunks for StreamingResponse.
    Implements ChatGPT-style token-by-token streaming with empty-stream retries.
    Each chunk is yielded as soon as it arrives — no buffering.
    """
    request_start = time.time()

    print(f"\n{'='*60}")
    print(f"[/text] REQUEST START — prompt length: {len(prompt)} chars")
    print(f"[/text] Prompt preview: {repr(prompt[:200])}")

    for attempt in range(1, EMPTY_STREAM_RETRIES + 2):   # attempts: 1, 2, 3
        chunks, finished_cleanly, error_kind = _consume_stream(
            prompt, attempt, request_start
        )

        # ── We got content — stream each chunk immediately ────────────────────
        if chunks:
            yield from chunks

            if not finished_cleanly and error_kind in ("chunked", "read_timeout", "unexpected"):
                print(f"[/text] Stream ended early after {len(chunks)} chunks "
                      f"(error={error_kind}); partial response delivered.")
            return

        # ── Empty stream — decide whether to retry ────────────────────────────
        if error_kind and error_kind.startswith("http:"):
            detail = error_kind[5:]
            yield f"AI model error: {detail}. Please retry."
            return

        if error_kind in ("connection", "timeout"):
            yield f"{'Connection error' if error_kind == 'connection' else 'Connection timed out'}. Please retry."
            return

        if attempt <= EMPTY_STREAM_RETRIES:
            wait_s = 1.5 * attempt          # 1.5 s then 3 s
            print(f"[/text] Empty stream on attempt {attempt} "
                  f"(error={error_kind}); retrying in {wait_s:.1f}s ...")
            time.sleep(wait_s)
            continue

        print(f"[/text] WARNING: {EMPTY_STREAM_RETRIES + 1} attempts all returned "
              f"zero content chunks.")
        yield "[No content received from model after retries. Try rephrasing your prompt.]"
        return


# --------------------------
# HOME  (health check)
# --------------------------
@app.get("/")
def home():
    return {"message": "Backend running successfully"}


# --------------------------
# TEXT  (ChatGPT-style streaming)
# --------------------------
@app.post("/text")
async def text_query(prompt: str = Form(...)):
    print(f"\n{'='*60}")
    return StreamingResponse(
        stream_nvidia_response(prompt),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",          # disables nginx proxy buffering
            "X-Content-Type-Options": "nosniff", # prevents browser sniffing delays
        },
    )


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
