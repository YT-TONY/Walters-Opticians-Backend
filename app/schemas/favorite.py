# app/schemas/favorite.py
from pydantic import BaseModel
from datetime import datetime
from typing import List
from app.schemas.product import ProductResponse

class FavoriteResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    created_at: datetime
    product: ProductResponse

    class Config:
        from_attributes = True

class FavoriteToggleResponse(BaseModel):
    favorited: bool
    product_id: int
    message: str