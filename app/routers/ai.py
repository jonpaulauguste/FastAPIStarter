from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.ai_service import ask_ai

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Handle chat messages from the AI widget."""
    reply = ask_ai(request.message)
    return ChatResponse(reply=reply)


@router.get("/chat/suggestions")
async def chat_suggestions():
    """Return suggested questions for the chat widget."""
    return JSONResponse({
        "suggestions": [
            "What's good for lunch?",
            "Show me cheap eats",
            "Where can I get coffee?",
            "Spicy food recommendations",
            "Best rated restaurants",
            "What's near the library?"
        ]
    })