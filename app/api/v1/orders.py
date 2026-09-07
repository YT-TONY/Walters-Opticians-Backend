# app/api/v1/orders.py
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.store_settings import StoreSetting
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse, UK_COUNTRY_CODES
from app.schemas.store_settings import StoreSettingsResponse, StoreSettingsUpdate

router = APIRouter(prefix="/orders", tags=["Orders & Checkout"])

DEFAULT_RATES: Dict[str, Any] = {
    "standard_lens_fee": 30.00,
    "eye_exam_fee": 25.00,
    "uk_base_shipping": 5.00,
    "eu_base_shipping": 15.00,
    "intl_base_shipping": 25.00,
    "low_stock_threshold": 8.00,
    "promo_banner_text": "Complimentary UK Express Shipping & Lens Anti-Reflective Coating Included",
    "promo_banner_active": True,
}

# Module-level variable exports required by cart.py
standard_lens_fee: float = float(DEFAULT_RATES["standard_lens_fee"])
eye_exam_fee: float = float(DEFAULT_RATES["eye_exam_fee"])

EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GERMANY", "FRANCE",
    "SPAIN", "ITALY", "IRELAND", "NETHERLANDS"
}


def serialize_order_with_products(ord_obj: Order, db: Session) -> Dict:
    serialized_items = []

    if hasattr(ord_obj, "items") and ord_obj.items:
        for item in ord_obj.items:
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            serialized_items.append({
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "order_type": item.order_type,
                "frame_price": item.frame_price,
                "lens_fee": item.lens_fee,
                "prescription_file_url": item.prescription_file_url,
                "right_sph": item.right_sph,
                "right_cyl": item.right_cyl,
                "right_axis": item.right_axis,
                "left_sph": item.left_sph,
                "left_cyl": item.left_cyl,
                "left_axis": item.left_axis,
                "pd_mm": item.pd_mm,
                "product_name": prod.name if prod else f"Optical Frame #{item.product_id}",
                "product_brand": getattr(prod, "brand", "Walters Opticians") if prod else "Walters Opticians",
                "product_image_url": prod.image_url if prod else None,
            })

    first_item = serialized_items[0] if serialized_items else {}

    return {
        "id": ord_obj.id,
        "reference_id": ord_obj.reference_id,
        "country": ord_obj.country,
        "shipping_address": ord_obj.shipping_address,
        "exam_fee": ord_obj.exam_fee,
        "shipping_fee": ord_obj.shipping_fee,
        "total_amount": ord_obj.total_amount,
        "status": ord_obj.status,
        "prescription_status": ord_obj.prescription_status,
        "carrier": ord_obj.carrier,
        "tracking_number": ord_obj.tracking_number,
        "shipping_label_url": ord_obj.shipping_label_url,
        "appointment_date": ord_obj.appointment_date,
        "created_at": ord_obj.created_at,
        "items": serialized_items,
        # Legacy flat fallback fields
        "product_id": first_item.get("product_id") or getattr(ord_obj, "product_id", None),
        "quantity": first_item.get("quantity") or getattr(ord_obj, "quantity", 1),
        "order_type": first_item.get("order_type") or getattr(ord_obj, "order_type", "frame_only"),
        "frame_price": ord_obj.frame_price,
        "lens_fee": ord_obj.lens_fee,
        "product_name": first_item.get("product_name"),
        "product_brand": first_item.get("product_brand"),
        "product_image_url": first_item.get("product_image_url"),
        "prescription_file_url": first_item.get("prescription_file_url") or getattr(ord_obj, "prescription_file_url", None),
        "right_sph": first_item.get("right_sph") or getattr(ord_obj, "right_sph", None),
        "right_cyl": first_item.get("right_cyl") or getattr(ord_obj, "right_cyl", None),
        "right_axis": first_item.get("right_axis") or getattr(ord_obj, "right_axis", None),
        "left_sph": first_item.get("left_sph") or getattr(ord_obj, "left_sph", None),
        "left_cyl": first_item.get("left_cyl") or getattr(ord_obj, "left_cyl", None),
        "left_axis": first_item.get("left_axis") or getattr(ord_obj, "left_axis", None),
        "pd_mm": first_item.get("pd_mm") or getattr(ord_obj, "pd_mm", None),
    }


def serialize_order_with_product(ord_obj: Order, db: Session) -> Dict:
    """Backward compatibility alias for single-item order serialization."""
    return serialize_order_with_products(ord_obj, db)


def get_store_rates(db: Session) -> Dict[str, Any]:
    rates = DEFAULT_RATES.copy()
    db_settings = db.query(StoreSetting).all()

    for setting in db_settings:
        if setting.key in rates:
            if setting.key == "promo_banner_text":
                rates[setting.key] = str(setting.value)
            elif setting.key == "promo_banner_active":
                rates[setting.key] = str(setting.value).lower() in ("true", "1", "t", "yes")
            else:
                try:
                    rates[setting.key] = float(setting.value)
                except ValueError:
                    pass

    return rates


def calculate_shipping_fee(country: str, db: Session) -> float:
    country_clean = country.strip().upper()
    rates = get_store_rates(db)

    if country_clean in UK_COUNTRY_CODES:
        return float(rates["uk_base_shipping"])
    elif country_clean in EU_COUNTRY_CODES:
        return float(rates["eu_base_shipping"])
    else:
        return float(rates["intl_base_shipping"])


def generate_unique_reference_id(db: Session) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=7))
        ref_id = f"WALT-{code}"
        if not db.query(Order).filter(Order.reference_id == ref_id).first():
            return ref_id


# ==========================================
# CUSTOMER & PUBLIC ENDPOINTS
# ==========================================


@router.get("/settings", response_model=StoreSettingsResponse)
def get_public_store_settings(db: Session = Depends(get_db)):
    """Publicly accessible endpoint for customers to load promo banners and fees."""
    return StoreSettingsResponse(rates=get_store_rates(db))


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rates = get_store_rates(db)
    shipping_fee = calculate_shipping_fee(order_in.country, db)

    total_frame_price = 0.0
    total_lens_fee = 0.0
    exam_fee = 0.0
    has_prescription_items = False
    db_items_to_create = []

    for item_in in order_in.items:
        product = db.query(Product).filter(Product.id == item_in.product_id).first()
        if not product or not getattr(product, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product ID #{item_in.product_id} not found or unavailable."
            )

        if product.stock_quantity < item_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested quantity ({item_in.quantity}) for '{product.name}' exceeds available stock ({product.stock_quantity})."
            )

        if item_in.order_type == "book_appointment":
            exam_fee = float(rates["eye_exam_fee"])

        if item_in.order_type in ["upload_prescription", "manual_prescription"]:
            has_prescription_items = True

        unit_frame_price = (
            product.price_frame_only_gbp
            if item_in.order_type == "frame_only"
            else product.price_full_gbp
        )

        item_frame_price = round(unit_frame_price * item_in.quantity, 2)
        item_lens_fee = (
            round(float(rates["standard_lens_fee"]) * item_in.quantity, 2)
            if item_in.order_type != "frame_only"
            else 0.0
        )

        total_frame_price += item_frame_price
        total_lens_fee += item_lens_fee

        product.stock_quantity -= item_in.quantity

        db_items_to_create.append(
            OrderItem(
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                order_type=item_in.order_type,
                frame_price=item_frame_price,
                lens_fee=item_lens_fee,
                prescription_file_url=item_in.prescription_file_url,
                right_sph=item_in.right_sph,
                right_cyl=item_in.right_cyl,
                right_axis=item_in.right_axis,
                left_sph=item_in.left_sph,
                left_cyl=item_in.left_cyl,
                left_axis=item_in.left_axis,
                pd_mm=item_in.pd_mm,
            )
        )

    total_amount = round(total_frame_price + total_lens_fee + exam_fee + shipping_fee, 2)
    reference_code = generate_unique_reference_id(db)

    new_order = Order(
        reference_id=reference_code,
        user_id=current_user.id,
        shipping_address=order_in.shipping_address,
        country=order_in.country,
        frame_price=round(total_frame_price, 2),
        lens_fee=round(total_lens_fee, 2),
        exam_fee=round(exam_fee, 2),
        shipping_fee=round(shipping_fee, 2),
        total_amount=total_amount,
        status="Order Placed",
        prescription_status="pending_review" if has_prescription_items else "n_a",
        appointment_date=order_in.appointment_date,
        items=db_items_to_create,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return serialize_order_with_products(new_order, db)


@router.get("/me", response_model=List[OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()
    return [serialize_order_with_products(o, db) for o in orders]


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

    user_role = getattr(current_user.role, "value", str(current_user.role))
    if order.user_id != current_user.id and user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return serialize_order_with_products(order, db)


# ==========================================
# ADMIN-ONLY ORDER & CLINIC MANAGEMENT
# ==========================================


@router.get("/admin/settings", response_model=StoreSettingsResponse)
def get_admin_store_settings(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return StoreSettingsResponse(rates=get_store_rates(db))


@router.put("/admin/settings", response_model=StoreSettingsResponse)
def update_admin_store_settings(
    settings_in: StoreSettingsUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
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
    appointments = db.query(Order).filter(
        Order.appointment_date.isnot(None)
    ).order_by(Order.appointment_date.asc()).all()
    return [serialize_order_with_products(a, db) for a in appointments]


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
    return serialize_order_with_products(order, db)


@router.put("/{order_id}/prescription-status", response_model=OrderResponse)
def update_prescription_status(
    order_id: int,
    rx_status: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    valid_rx_statuses = ["pending_review", "verified", "rejected", "sent_to_lab", "lab_completed", "n_a"]
    if rx_status not in valid_rx_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prescription status. Choose from: {valid_rx_statuses}"
        )

    order.prescription_status = rx_status

    if rx_status == "sent_to_lab":
        order.status = "In Fulfillment"
    elif rx_status == "lab_completed":
        order.status = "Preparing for Dispatch"

    db.commit()
    db.refresh(order)
    return serialize_order_with_products(order, db)


@router.post("/{order_id}/generate-label", response_model=OrderResponse)
def generate_shipping_label(
    order_id: int,
    carrier_name: str = "Royal Mail",
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    random_digits = "".join([str(random.randint(0, 9)) for _ in range(9)])
    mock_tracking_no = f"GB{random_digits}RM"

    order.carrier = carrier_name
    order.tracking_number = mock_tracking_no
    order.shipping_label_url = f"https://api.waltersopticians.com/labels/{order.reference_id}.pdf"
    order.status = "Dispatched"

    db.commit()
    db.refresh(order)
    return serialize_order_with_products(order, db)


@router.post("/{order_id}/simulate-status", response_model=OrderResponse)
def simulate_carrier_status_update(
    order_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    order.status = new_status
    db.commit()
    db.refresh(order)
    return serialize_order_with_products(order, db)


@router.post("/webhook/carrier")
def carrier_tracking_webhook(
    payload: Dict,
    db: Session = Depends(get_db)
):
    tracking_code = payload.get("tracking_code")
    carrier_status = payload.get("status")

    if not tracking_code or not carrier_status:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")

    order = db.query(Order).filter(Order.tracking_number == tracking_code).first()
    if not order:
        return {"status": "ignored", "reason": "Tracking number not matched"}

    status_mapping = {
        "in_transit": "In Transit",
        "out_for_delivery": "Out for Delivery",
        "delivered": "Delivered",
        "failure": "Delivery Attempted",
        "return_to_sender": "Returned to Sender"
    }

    if carrier_status in status_mapping:
        order.status = status_mapping[carrier_status]
        db.commit()

    return {"status": "success", "updated_status": order.status}


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

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return [serialize_order_with_products(o, db) for o in orders]