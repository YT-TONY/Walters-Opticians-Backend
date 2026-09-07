# app/schemas/admin.py
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime


class SalesTrendPoint(BaseModel):
    date: str
    orders_count: int
    revenue: float


class TopMovingProduct(BaseModel):
    product_id: int
    name: str
    brand: str
    image_url: Optional[str] = None
    total_quantity_sold: int
    total_revenue: float


class SlowMovingProduct(BaseModel):
    product_id: int
    name: str
    brand: str
    image_url: Optional[str] = None
    stock_quantity: int
    price_full_gbp: float


class MarketOverviewResponse(BaseModel):
    total_revenue: float
    total_orders: int
    pending_orders_count: int
    low_stock_count: int
    total_appointments: int
    unread_notifications: int
    sales_trend: List[SalesTrendPoint]
    top_moving_products: List[TopMovingProduct]
    slow_moving_products: List[SlowMovingProduct]


class BrandProductItem(BaseModel):
    id: int
    name: str
    brand: str
    stock_quantity: int
    price_full_gbp: float
    price_frame_only_gbp: float
    image_url: str
    is_low_stock: bool
    is_out_of_stock: bool

    class Config:
        from_attributes = True


class BrandInventoryGroup(BaseModel):
    brand_name: str
    total_items_count: int
    low_stock_count: int
    products: List[BrandProductItem]