from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    name: str
    brand: str
    shape: str
    color_description: str
    price_full_gbp: float
    allow_frame_only: bool = True
    price_frame_only_gbp: float
    image_url: str
    stock_quantity: int = 10
    is_featured: bool = False

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    shape: Optional[str] = None
    color_description: Optional[str] = None
    price_full_gbp: Optional[float] = None
    allow_frame_only: Optional[bool] = None
    price_frame_only_gbp: Optional[float] = None
    image_url: Optional[str] = None
    stock_quantity: Optional[int] = None
    is_featured: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True