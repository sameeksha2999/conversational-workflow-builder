from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent import process_message
from .models import ChatRequest, ChatResponse


app = FastAPI(
    title="Conversational Workflow Builder",
    description="AI-powered conversational workflow planning system",
    version="1.0.0",
)


# Allow local development frontend and deployed Render frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",

        # Production frontend
        "https://conversational-workflow-builder-1.onrender.com",
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