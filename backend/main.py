from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import uvicorn

app = FastAPI()

# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NVIDIA API KEY
NVIDIA_API_KEY = "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"

MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


@app.get("/")
def home():
    return {"message": "Backend running"}


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
        "max_tokens": 100
    }

    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        data = response.json()

        print(data)

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
        else:
            answer = f"API Error: {data}"

    except Exception as e:
        answer = f"Error: {str(e)}"

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


# --------------------------
# RAILWAY STARTUP
# --------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )