import random
import string
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

DEFAULT_RATES: Dict[str, float] = {
    "standard_lens_fee": 30.00,
    "eye_exam_fee": 25.00,
    "uk_base_shipping": 5.00,
    "eu_base_shipping": 15.00,
    "intl_base_shipping": 25.00,
}

standard_lens_fee = DEFAULT_RATES["standard_lens_fee"]
eye_exam_fee = DEFAULT_RATES["eye_exam_fee"]

EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GERMANY", "FRANCE",
    "SPAIN", "ITALY", "IRELAND", "NETHERLANDS"
}

# ==========================================
# HELPER TO SERIALIZE ORDER WITH PRODUCT DATA
# ==========================================

def serialize_order_with_product(ord_obj: Order, db: Session) -> Dict:
    """
    Constructs a dictionary containing full order details along with joined product metadata.
    Guarantees that Pydantic includes product_name, brand, and image_url in JSON.
    """
    prod = db.query(Product).filter(Product.id == ord_obj.product_id).first()
    
    return {
        "id": ord_obj.id,
        "reference_id": ord_obj.reference_id,
        "product_id": ord_obj.product_id,
        "quantity": ord_obj.quantity,
        "order_type": ord_obj.order_type,
        "country": ord_obj.country,
        "shipping_address": ord_obj.shipping_address,
        "frame_price": ord_obj.frame_price,
        "lens_fee": ord_obj.lens_fee,
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
        "prescription_file_url": ord_obj.prescription_file_url,
        "right_sph": ord_obj.right_sph,
        "right_cyl": ord_obj.right_cyl,
        "right_axis": ord_obj.right_axis,
        "left_sph": ord_obj.left_sph,
        "left_cyl": ord_obj.left_cyl,
        "left_axis": ord_obj.left_axis,
        "pd_mm": ord_obj.pd_mm,
        # Product Metadata
        "product_name": prod.name if prod else f"Optical Frame #{ord_obj.product_id}",
        "product_brand": getattr(prod, "brand", "Walters Opticians") if prod else "Walters Opticians",
        "product_image_url": prod.image_url if prod else None,
    }


def get_store_rates(db: Session) -> Dict[str, float]:
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
    quantity: int,
    db: Session
) -> Dict[str, float]:
    rates = get_store_rates(db)
    shipping_fee = calculate_shipping_fee(country, db)

    frame_price = product_price * quantity
    lens_fee = 0.0
    exam_fee = 0.0

    if order_type in ["upload_prescription", "manual_prescription"]:
        lens_fee = rates["standard_lens_fee"] * quantity
    elif order_type == "book_appointment":
        lens_fee = rates["standard_lens_fee"] * quantity
        exam_fee = rates["eye_exam_fee"]

    total_amount = round(frame_price + lens_fee + exam_fee + shipping_fee, 2)

    return {
        "frame_price": round(frame_price, 2),
        "lens_fee": round(lens_fee, 2),
        "exam_fee": round(exam_fee, 2),
        "shipping_fee": round(shipping_fee, 2),
        "total_amount": total_amount,
    }


def generate_unique_reference_id(db: Session) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=7))
        ref_id = f"WALT-{code}"
        if not db.query(Order).filter(Order.reference_id == ref_id).first():
            return ref_id


# ==========================================
# CUSTOMER ENDPOINTS
# ==========================================


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == order_in.product_id).first()
    if not product or not getattr(product, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unavailable."
        )

    if product.stock_quantity < order_in.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested quantity ({order_in.quantity}) exceeds available stock ({product.stock_quantity})."
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
        quantity=order_in.quantity,
        db=db
    )

    product.stock_quantity -= order_in.quantity
    reference_code = generate_unique_reference_id(db)

    new_order = Order(
        reference_id=reference_code,
        user_id=current_user.id,
        product_id=order_in.product_id,
        quantity=order_in.quantity,
        order_type=order_in.order_type,
        shipping_address=order_in.shipping_address,
        country=order_in.country,
        frame_price=fees["frame_price"],
        lens_fee=fees["lens_fee"],
        exam_fee=fees["exam_fee"],
        shipping_fee=fees["shipping_fee"],
        total_amount=fees["total_amount"],
        status="Order Placed",
        prescription_status="pending_review" if order_in.order_type in ["upload_prescription", "manual_prescription"] else "n_a",
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

    return serialize_order_with_product(new_order, db)


@router.get("/me", response_model=List[OrderResponse])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()
    return [serialize_order_with_product(o, db) for o in orders]


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

    return serialize_order_with_product(order, db)


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
        Order.order_type == "book_appointment",
        Order.appointment_date.isnot(None)
    ).order_by(Order.appointment_date.asc()).all()
    return [serialize_order_with_product(a, db) for a in appointments]


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
    return serialize_order_with_product(order, db)


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
    return serialize_order_with_product(order, db)


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
    return serialize_order_with_product(order, db)


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
    return serialize_order_with_product(order, db)


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
    return [serialize_order_with_product(o, db) for o in orders]