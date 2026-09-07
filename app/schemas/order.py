# app/schemas/order.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

UK_COUNTRY_CODES = ["UK", "GB", "UNITED KINGDOM", "GREAT BRITAIN"]


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)
    order_type: str  # "frame_only", "upload_prescription", "manual_prescription", "book_appointment"

    prescription_file_url: Optional[str] = None
    right_sph: Optional[float] = None
    right_cyl: Optional[float] = None
    right_axis: Optional[int] = None
    left_sph: Optional[float] = None
    left_cyl: Optional[float] = None
    left_axis: Optional[int] = None
    pd_mm: Optional[float] = None

    @validator("order_type")
    def validate_order_type(cls, v):
        allowed = ["frame_only", "upload_prescription", "manual_prescription", "book_appointment"]
        if v not in allowed:
            raise ValueError(f"order_type must be one of {allowed}")
        return v


class OrderCreate(BaseModel):
    shipping_address: str
    country: str  # e.g., "UK", "NG", "US"
    appointment_date: Optional[datetime] = None
    items: List[OrderItemCreate]

    @validator("items")
    def validate_items_non_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("An order must contain at least one item.")
        return v

    @validator("country")
    def validate_country(cls, v, values):
        country_clean = v.strip().upper()
        items = values.get("items", [])
        has_appointment = any(item.order_type == "book_appointment" for item in items)

        if has_appointment and country_clean not in UK_COUNTRY_CODES:
            raise ValueError("In-clinic eye exam appointments are only available for UK addresses.")
        return v


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    order_type: str
    frame_price: float
    lens_fee: float

    # Product Metadata
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    product_image_url: Optional[str] = None

    # Item Prescription Specs
    prescription_file_url: Optional[str] = None
    right_sph: Optional[float] = None
    right_cyl: Optional[float] = None
    right_axis: Optional[int] = None
    left_sph: Optional[float] = None
    left_cyl: Optional[float] = None
    left_axis: Optional[int] = None
    pd_mm: Optional[float] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    reference_id: str
    country: str
    shipping_address: str
    exam_fee: float
    shipping_fee: float
    total_amount: float
    status: str
    prescription_status: Optional[str] = "pending_review"
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_label_url: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    appointment_date: Optional[datetime] = None
    created_at: datetime

    # Grouped Items
    items: List[OrderItemResponse] = []

    # Backwards-compatibility fallbacks (populated from first item)
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    order_type: Optional[str] = None
    frame_price: Optional[float] = None
    lens_fee: Optional[float] = None
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    product_image_url: Optional[str] = None
    prescription_file_url: Optional[str] = None
    right_sph: Optional[float] = None
    right_cyl: Optional[float] = None
    right_axis: Optional[int] = None
    left_sph: Optional[float] = None
    left_cyl: Optional[float] = None
    left_axis: Optional[int] = None
    pd_mm: Optional[float] = None

    class Config:
        from_attributes = True