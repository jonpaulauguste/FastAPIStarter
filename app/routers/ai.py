from fastapi import APIRouter
from app.services.ai_service import ask_ai

router = APIRouter()

@router.post("/chat")
def chat(prompt: str):
    response = ask_ai(prompt)
    return {"response": response}