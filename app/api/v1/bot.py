from fastapi import APIRouter
import httpx
from app.schemas.ai import ChatRequest, ChatResponse
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["AI Customer Bot"])

SYSTEM_PROMPT = (
    "You are the official AI Eyecare Assistant for Walters Opticians (Gainsborough & Lincoln). "
    "You help customers choose frame shapes (Round, Aviator, Square), explain prescription lens options "
    "(Single Vision, Varifocal, Blue Light Filter), and assist with booking eye tests. "
    "Keep answers friendly, precise, and professional."
)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    user_msg = request.message.strip()

    # Smart Keyword Responses (Instant Local Logic)
    if "booking" in user_msg.lower() or "eye test" in user_msg.lower():
        return {"reply": "You can book an eye test at our Gainsborough or Lincoln branches using the 'Book Eye Test' button in the top navigation bar!"}
    if "location" in user_msg.lower() or "address" in user_msg.lower():
        return {"reply": "Walters Opticians has primary practices in Gainsborough (01427 616506) and Lincoln (01522 686200)."}

    # Call Gemini API if API key is provided
    if settings.GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\nCustomer: {user_msg}"}]}
                ]
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    reply = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {"reply": reply}
        except Exception:
            pass

    # Default Helpful Response
    return {
        "reply": f"Thanks for asking about '{user_msg}'! Our optical team offers custom single vision and varifocal lenses, as well as frame-only orders across our Tom Ford, Ray-Ban, and Gucci collections."
    }