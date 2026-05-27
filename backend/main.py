from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NVIDIA settings
NVIDIA_API_KEY = "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"

MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


@app.get("/")
def home():
    return {"message": "Backend running"}


# TEXT API
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
        "max_tokens": 100
    }

    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    data = response.json()

    try:
        answer = data["choices"][0]["message"]["content"]
    except:
        answer = "Error getting response"

    return {"response": answer}


@app.post("/image")
async def image_query(file: UploadFile = File(...)):
    return {
        "response": f"Image uploaded successfully: {file.filename}"
    }


@app.post("/audio")
async def audio_query(file: UploadFile = File(...)):
    return {
        "response": f"Audio uploaded successfully: {file.filename}"
    }


@app.post("/video")
async def video_query(file: UploadFile = File(...)):
    return {
        "response": f"Video uploaded successfully: {file.filename}"
    }