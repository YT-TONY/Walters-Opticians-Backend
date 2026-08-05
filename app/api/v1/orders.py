from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.order import Order
from app.models.product import Product
from app.models.store_settings import StoreSetting
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse, UK_COUNTRY_CODES
from app.schemas.store_settings import StoreSettingsResponse, StoreSettingsUpdate

router = APIRouter(prefix="/orders", tags=["Orders & Checkout"])

# Fallback defaults used only if database table is initially empty
DEFAULT_RATES: Dict[str, float] = {
    "standard_lens_fee": 30.00,
    "eye_exam_fee": 25.00,
    "uk_base_shipping": 5.00,
    "eu_base_shipping": 15.00,
    "intl_base_shipping": 25.00,
}

# Exports for external module imports (e.g., cart.py)
standard_lens_fee = DEFAULT_RATES["standard_lens_fee"]
eye_exam_fee = DEFAULT_RATES["eye_exam_fee"]

EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GERMANY", "FRANCE",
    "SPAIN", "ITALY", "IRELAND", "NETHERLANDS"
}

# ==========================================
# DYNAMIC RATE CALCULATION HELPERS
# ==========================================


def get_store_rates(db: Session) -> Dict[str, float]:
    """
    Fetches live rate configurations from the store_settings database table.
    Falls back to defaults for any unconfigured keys.
    """
    rates = DEFAULT_RATES.copy()
    db_settings = db.query(StoreSetting).all()

    for setting in db_settings:
        if setting.key in rates:
            try:
                rates[setting.key] = float(setting.value)
            except ValueError:
                pass

    return rates


def calculate_shipping_fee(country: str, db: Session) -> float:
    """
    Dynamically calculates shipping costs from live database rates.
    """
    country_clean = country.strip().upper()
    rates = get_store_rates(db)

    if country_clean in UK_COUNTRY_CODES:
        return rates["uk_base_shipping"]
    elif country_clean in EU_COUNTRY_CODES:
        return rates["eu_base_shipping"]
    else:
        return rates["intl_base_shipping"]


def calculate_order_fees(
    product_price: float,
    order_type: str,
    country: str,
    db: Session
) -> Dict[str, float]:
    """
    Calculates itemized financial breakdown using dynamic database values.
    """
    rates = get_store_rates(db)
    shipping_fee = calculate_shipping_fee(country, db)

    frame_price = product_price
    lens_fee = 0.0
    exam_fee = 0.0

    if order_type in ["upload_prescription", "manual_prescription"]:
        lens_fee = rates["standard_lens_fee"]
    elif order_type == "book_appointment":
        lens_fee = rates["standard_lens_fee"]
        exam_fee = rates["eye_exam_fee"]

    total_amount = round(frame_price + lens_fee + exam_fee + shipping_fee, 2)

    return {
        "frame_price": round(frame_price, 2),
        "lens_fee": round(lens_fee, 2),
        "exam_fee": round(exam_fee, 2),
        "shipping_fee": round(shipping_fee, 2),
        "total_amount": total_amount,
    }


# ==========================================
# CUSTOMER ENDPOINTS
# ==========================================


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process checkout using dynamic fees stored in the database.
    """
    product = db.query(Product).filter(Product.id == order_in.product_id).first()
    if not product or not getattr(product, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unavailable."
        )

    if product.stock_quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This frame is currently out of stock."
        )

    country_clean = order_in.country.strip().upper()
    is_uk = country_clean in UK_COUNTRY_CODES

    if order_in.order_type == "book_appointment":
        if not is_uk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="In-clinic eye exam appointments are only available for UK addresses."
            )
        if not order_in.appointment_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An appointment date and time must be selected when booking an eye exam."
            )

    base_frame_price = (
        product.price_frame_only_gbp 
        if order_in.order_type == "frame_only" 
        else product.price_full_gbp
    )

    fees = calculate_order_fees(
        product_price=base_frame_price,
        order_type=order_in.order_type,
        country=order_in.country,
        db=db
    )

    product.stock_quantity -= 1

    new_order = Order(
        user_id=current_user.id,
        product_id=order_in.product_id,
        order_type=order_in.order_type,
        shipping_address=order_in.shipping_address,
        country=order_in.country,
        frame_price=fees["frame_price"],
        lens_fee=fees["lens_fee"],
        exam_fee=fees["exam_fee"],
        shipping_fee=fees["shipping_fee"],
        total_amount=fees["total_amount"],
        appointment_date=order_in.appointment_date if order_in.order_type == "book_appointment" else None,
        prescription_file_url=order_in.prescription_file_url,
        right_sph=order_in.right_sph,
        right_cyl=order_in.right_cyl,
        right_axis=order_in.right_axis,
        left_sph=order_in.left_sph,
        left_cyl=order_in.left_cyl,
        left_axis=order_in.left_axis,
        pd_mm=order_in.pd_mm,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order


@router.get("/me", response_model=List[OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Order).filter(Order.user_id == current_user.id).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return order


# ==========================================
# ADMIN-ONLY ORDER, CLINIC & DYNAMIC RATES
# ==========================================


@router.get("/admin/settings", response_model=StoreSettingsResponse)
def get_admin_store_settings(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    View current dynamic store pricing and shipping fees (Admin only).
    """
    return StoreSettingsResponse(rates=get_store_rates(db))


@router.put("/admin/settings", response_model=StoreSettingsResponse)
def update_admin_store_settings(
    settings_in: StoreSettingsUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Dynamically update lens fees, exam fees, or shipping costs without restarting the server (Admin only).
    """
    updates = settings_in.dict(exclude_unset=True)

    for key, value in updates.items():
        if value is None:
            continue
        
        setting = db.query(StoreSetting).filter(StoreSetting.key == key).first()
        if setting:
            setting.value = str(value)
        else:
            new_setting = StoreSetting(key=key, value=str(value))
            db.add(new_setting)

    db.commit()
    return StoreSettingsResponse(rates=get_store_rates(db))


@router.get("/admin/appointments", response_model=List[OrderResponse])
def list_clinic_appointments(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return db.query(Order).filter(
        Order.order_type == "book_appointment",
        Order.appointment_date.isnot(None)
    ).order_by(Order.appointment_date.asc()).all()


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    order.status = status_update
    db.commit()
    db.refresh(order)
    return order


@router.get("/", response_model=List[OrderResponse])
def list_all_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()