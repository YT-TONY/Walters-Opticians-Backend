from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from app.schemas.product import ProductResponse

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    order_type: str = "frame_only"
    appointment_date: Optional[datetime] = None

    # Prescription options
    prescription_file_url: Optional[str] = None
    right_sph: Optional[float] = None
    right_cyl: Optional[float] = None
    right_axis: Optional[int] = None
    left_sph: Optional[float] = None
    left_cyl: Optional[float] = None
    left_axis: Optional[int] = None
    pd_mm: Optional[float] = None

    @validator("quantity")
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be at least 1")
        return v

    @validator("order_type")
    def validate_order_type(cls, v):
        allowed = ["frame_only", "upload_prescription", "manual_prescription", "book_appointment"]
        if v not in allowed:
            raise ValueError(f"order_type must be one of {allowed}")
        return v


class CartItemUpdate(BaseModel):
    quantity: Optional[int] = None
    order_type: Optional[str] = None
    appointment_date: Optional[datetime] = None


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    order_type: str
    appointment_date: Optional[datetime]
    prescription_file_url: Optional[str]
    right_sph: Optional[float]
    right_cyl: Optional[float]
    right_axis: Optional[int]
    left_sph: Optional[float]
    left_cyl: Optional[float]
    left_axis: Optional[int]
    pd_mm: Optional[float]
    product: ProductResponse
    item_subtotal: float

    class Config:
        from_attributes = True


class CartSummaryResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    estimated_subtotal: float