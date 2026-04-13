from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import ask_ai

router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str


@router.post("/chat")
def chat(payload: ChatRequest):
    response = ask_ai(payload.prompt)
    return {"response": response}
