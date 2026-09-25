from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent import process_message
from .models import ChatRequest, ChatResponse


app = FastAPI(
    title="Conversational Workflow Builder",
    description="AI-powered conversational workflow planning system",
    version="1.0.0",
)


# Allow the Vite development frontend.
# Vite may use 5173, 5174, 5175, etc. if an earlier port is occupied.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Conversational Workflow Builder API is running"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    reply, state, workflow = process_message(
        request.message,
        request.state,
    )

    return ChatResponse(
        reply=reply,
        state=state,
        workflow=workflow,
    )