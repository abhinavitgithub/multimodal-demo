# TIAV Multimodal Demo

A simple multimodal AI demo built using **React + FastAPI + NVIDIA Nemotron Omni model**.

## Features

- Text query with NVIDIA Nemotron model
- Image upload support
- Audio upload support
- Video upload support
- React frontend + FastAPI backend
- NVIDIA API integration

## Tech Stack

### Frontend
- React (Vite)

### Backend
- FastAPI
- Python
- Requests

### AI Model
- NVIDIA Nemotron Omni

## Project Structure

```text
multimodal-demo/
│── backend/
│── frontend/
│── README.md
```

## Setup Instructions

### Backend Setup

Go to backend folder:

```bash
cd backend
```

Install dependencies:

```bash
pip install fastapi uvicorn python-multipart requests
```

Run backend:

```bash
uvicorn main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

---

### Frontend Setup

Go to frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run frontend:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Demo Capabilities

### Text
User enters prompt → NVIDIA Nemotron generates response.

### Image
User uploads image → upload flow demo implemented.

### Audio
User uploads audio → upload flow demo implemented.

### Video
User uploads video → upload flow demo implemented.

## Current Status

Basic working multimodal prototype completed.

### Future Improvements
- Actual image understanding
- Audio transcription / analysis
- Video understanding
- Improved frontend UI

## Author

**Abhinav Shukla**
