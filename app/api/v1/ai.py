from typing import List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductResponse

router = APIRouter(prefix="/ai", tags=["AI Eyecare & Style Advisor"])

SYSTEM_PROMPT = (
    "You are the official AI Eyecare Assistant for Walters Opticians (Gainsborough & Lincoln). "
    "You help customers choose frame shapes (Round, Aviator, Square), explain prescription lens options "
    "(Single Vision, Varifocal, Blue Light Filter), and assist with booking eye tests. "
    "Keep answers friendly, precise, and professional."
)

FACE_SHAPE_MATRIX = {
    "round": ["Square", "Rectangle", "Cat-Eye"],
    "square": ["Round", "Aviator", "Oval"],
    "oval": ["Round", "Square", "Rectangle", "Aviator", "Cat-Eye"],
    "heart": ["Cat-Eye", "Round", "Aviator"],
    "diamond": ["Oval", "Cat-Eye"]
}

# --- Schemas ---

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class StyleAdvisorRequest(BaseModel):
    face_shape: str
    preferred_brand: Optional[str] = None
    max_budget_gbp: Optional[float] = None

class StyleAdvisorResponse(BaseModel):
    recommended_shapes: List[str] = []
    advice: str
    matching_frames: List[ProductResponse] = []


# --- Endpoints ---

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(request: ChatRequest):
    """
    Conversational AI Assistant using Gemini API with local keyword fallbacks.
    """
    user_msg = request.message.strip()

    if "booking" in user_msg.lower() or "eye test" in user_msg.lower():
        return {"reply": "You can book an eye test at our Gainsborough or Lincoln branches using the 'Book Eye Test' button in the navigation bar!"}
    if "location" in user_msg.lower() or "address" in user_msg.lower():
        return {"reply": "Walters Opticians has primary practices in Gainsborough (01427 616506) and Lincoln (01522 686200)."}

    if getattr(settings, "GEMINI_API_KEY", None):
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

    return {
        "reply": f"Thanks for asking about '{user_msg}'! Our optical team offers custom single vision and varifocal lenses, as well as frame-only orders across our Tom Ford, Ray-Ban, and Gucci collections."
    }


@router.post("/recommend-frames", response_model=StyleAdvisorResponse)
def recommend_frames(
    payload: StyleAdvisorRequest,
    db: Session = Depends(get_db)
):
    """
    Recommendation engine matching customer face shape against active, in-stock inventory.
    """
    shape_key = payload.face_shape.strip().lower()
    if shape_key not in FACE_SHAPE_MATRIX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid face shape. Allowed values: {list(FACE_SHAPE_MATRIX.keys())}"
        )

    target_shapes = FACE_SHAPE_MATRIX[shape_key]

    query = db.query(Product).filter(
        Product.is_active == True,
        Product.stock_quantity > 0,
        Product.shape.in_(target_shapes)
    )

    if payload.preferred_brand:
        query = query.filter(Product.brand.ilike(f"%{payload.preferred_brand.strip()}%"))
    if payload.max_budget_gbp:
        query = query.filter(Product.price_full_gbp <= payload.max_budget_gbp)

    matching_products = query.limit(10).all()

    advice_text = (
        f"For a {shape_key.title()} face shape, frames like {', '.join(target_shapes)} "
        f"provide contrast and balance your features. Here are matching frames currently in stock."
    )

    return StyleAdvisorResponse(
        recommended_shapes=target_shapes,
        advice=advice_text,
        matching_frames=matching_products
    )