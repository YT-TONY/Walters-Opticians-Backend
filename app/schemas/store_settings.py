# app/schemas/store_settings.py
from typing import Dict, Any, Optional
from pydantic import BaseModel


class StoreSettingsUpdate(BaseModel):
    standard_lens_fee: Optional[float] = None
    eye_exam_fee: Optional[float] = None
    uk_base_shipping: Optional[float] = None
    eu_base_shipping: Optional[float] = None
    intl_base_shipping: Optional[float] = None
    low_stock_threshold: Optional[float] = None
    promo_banner_text: Optional[str] = None
    promo_banner_active: Optional[bool] = None


class StoreSettingsResponse(BaseModel):
    rates: Dict[str, Any]