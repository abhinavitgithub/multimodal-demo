from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# --------------------------
# CORS
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# CONFIG
# --------------------------
NVIDIA_API_KEY = "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"

MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


# --------------------------
# HOME API
# --------------------------
@app.get("/")
def home():
    return {"message": "Backend running successfully"}


# --------------------------
# TEXT API
# --------------------------
@app.post("/text")
async def text_query(prompt: str = Form(...)):

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 60,
        "temperature": 0.5
    }

    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )

        if response.status_code != 200:
            return {
                "response": "Server busy. Please retry."
            }

        data = response.json()

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
        else:
            answer = "No response received."

    except requests.exceptions.Timeout:
        answer = "Request timeout. Please try again."

    except Exception:
        answer = "Temporary connection issue. Retry."

    return {"response": answer}


# --------------------------
# IMAGE API
# --------------------------
@app.post("/image")
async def image_query(file: UploadFile = File(...)):
    return {
        "response": f"Image uploaded successfully: {file.filename}"
    }


# --------------------------
# AUDIO API
# --------------------------
@app.post("/audio")
async def audio_query(file: UploadFile = File(...)):
    return {
        "response": f"Audio uploaded successfully: {file.filename}"
    }


# --------------------------
# VIDEO API
# --------------------------
@app.post("/video")
async def video_query(file: UploadFile = File(...)):
    return {
        "response": f"Video uploaded successfully: {file.filename}"
    }