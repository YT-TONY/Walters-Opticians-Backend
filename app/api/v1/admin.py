# app/api/v1/admin.py
from typing import List, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api.deps import get_db, require_admin
from app.models.order import Order
from app.models.product import Product
from app.models.store_settings import StoreSetting
from app.schemas.admin import (
    MarketOverviewResponse,
    SalesTrendPoint,
    TopMovingProduct,
    SlowMovingProduct,
    BrandInventoryGroup,
    BrandProductItem
)

router = APIRouter(prefix="/admin", tags=["Admin Analytics & Management"])


def get_current_low_stock_threshold(db: Session) -> int:
    setting = db.query(StoreSetting).filter(StoreSetting.key == "low_stock_threshold").first()
    if setting:
        try:
            return int(float(setting.value))
        except ValueError:
            pass
    return 8


@router.get("/analytics/overview", response_model=MarketOverviewResponse)
def get_market_overview_analytics(
    days: int = Query(default=30, ge=7, le=365),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Computes aggregate metrics, revenue trends, pending order counts, and top/slow products.
    """
    threshold = get_current_low_stock_threshold(db)

    # 1. Total Metrics
    orders = db.query(Order).all()
    total_revenue = round(sum(o.total_amount for o in orders), 2)
    total_orders = len(orders)
    pending_orders_count = db.query(Order).filter(Order.status == "Order Placed").count()
    low_stock_count = db.query(Product).filter(
        Product.stock_quantity > 0,
        Product.stock_quantity <= threshold
    ).count()
    
    total_appointments = db.query(Order).filter(
        Order.order_type == "book_appointment",
        Order.appointment_date.isnot(None)
    ).count()

    # 2. Sales Trend Breakdown (Last N Days)
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    recent_orders = db.query(Order).filter(Order.created_at >= cutoff_date).all()

    daily_data: Dict[str, Dict[str, float]] = {}
    for i in range(days):
        day_str = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        daily_data[day_str] = {"count": 0, "revenue": 0.0}

    for order in recent_orders:
        day_str = order.created_at.strftime("%Y-%m-%d")
        if day_str in daily_data:
            daily_data[day_str]["count"] += 1
            daily_data[day_str]["revenue"] += order.total_amount

    sales_trend = [
        SalesTrendPoint(
            date=day_key,
            orders_count=val["count"],
            revenue=round(val["revenue"], 2)
        )
        for day_key, val in daily_data.items()
    ]

    # 3. Top Moving Products (Aggregated from Order table)
    product_sales = db.query(
        Order.product_id,
        func.sum(Order.quantity).label("total_sold"),
        func.sum(Order.total_amount).label("total_revenue")
    ).group_by(Order.product_id).order_by(func.sum(Order.quantity).desc()).limit(5).all()

    top_moving = []
    for p_id, sold, rev in product_sales:
        p = db.query(Product).filter(Product.id == p_id).first()
        if p:
            top_moving.append(TopMovingProduct(
                product_id=p.id,
                name=p.name,
                brand=p.brand,
                image_url=p.image_url,
                total_quantity_sold=int(sold or 0),
                total_revenue=round(float(rev or 0.0), 2)
            ))

    # 4. Slow Moving Products (High stock or 0 sales)
    slow_products = db.query(Product).filter(
        Product.is_active == True
    ).order_by(Product.stock_quantity.desc()).limit(5).all()

    slow_moving = [
        SlowMovingProduct(
            product_id=sp.id,
            name=sp.name,
            brand=sp.brand,
            image_url=sp.image_url,
            stock_quantity=sp.stock_quantity,
            price_full_gbp=sp.price_full_gbp
        )
        for sp in slow_products
    ]

    return MarketOverviewResponse(
        total_revenue=total_revenue,
        total_orders=total_orders,
        pending_orders_count=pending_orders_count,
        low_stock_count=low_stock_count,
        total_appointments=total_appointments,
        unread_notifications=pending_orders_count,
        sales_trend=sales_trend,
        top_moving_products=top_moving,
        slow_moving_products=slow_moving
    )


@router.get("/inventory/by-brand", response_model=List[BrandInventoryGroup])
def get_inventory_grouped_by_brand(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Retrieves all catalog items grouped cleanly by Brand with low-stock status flags.
    """
    threshold = get_current_low_stock_threshold(db)
    all_products = db.query(Product).order_by(Product.brand.asc(), Product.name.asc()).all()

    grouped_data: Dict[str, List[Product]] = {}
    for p in all_products:
        brand_key = p.brand.strip() if p.brand else "Unbranded"
        if brand_key not in grouped_data:
            grouped_data[brand_key] = []
        grouped_data[brand_key].append(p)

    result: List[BrandInventoryGroup] = []
    for brand_name, items in grouped_data.items():
        brand_items = [
            BrandProductItem(
                id=item.id,
                name=item.name,
                brand=item.brand,
                stock_quantity=item.stock_quantity,
                price_full_gbp=item.price_full_gbp,
                price_frame_only_gbp=item.price_frame_only_gbp,
                image_url=item.image_url,
                is_low_stock=item.stock_quantity > 0 and item.stock_quantity <= threshold,
                is_out_of_stock=item.stock_quantity <= 0
            )
            for item in items
        ]

        low_count = sum(1 for i in brand_items if i.is_low_stock or i.is_out_of_stock)

        result.append(BrandInventoryGroup(
            brand_name=brand_name,
            total_items_count=len(brand_items),
            low_stock_count=low_count,
            products=brand_items
        ))

    return result