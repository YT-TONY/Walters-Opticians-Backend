#app/schemas/order.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

UK_COUNTRY_CODES = ["UK", "GB", "UNITED KINGDOM", "GREAT BRITAIN"]

class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)
    order_type: str  # "frame_only", "upload_prescription", "manual_prescription", "book_appointment"
    shipping_address: str
    country: str     # e.g., "UK", "NG", "US"

    appointment_date: Optional[datetime] = None

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

    @validator("country")
    def validate_country(cls, v, values):
        country_clean = v.strip().upper()
        order_type = values.get("order_type")
        if order_type == "book_appointment" and country_clean not in UK_COUNTRY_CODES:
            raise ValueError("In-clinic eye exam appointments are only available for UK addresses.")
        return v


class OrderResponse(BaseModel):
    id: int
    reference_id: str
    product_id: int
    quantity: int
    order_type: str
    country: str
    shipping_address: str
    frame_price: float
    lens_fee: float
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

    # Product Metadata
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    product_image_url: Optional[str] = None

    # Prescription Parameters
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