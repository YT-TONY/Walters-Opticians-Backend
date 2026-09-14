#app/api/v1/contact_lenses.py

from typing import List, Optional
from datetime import date
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.contact_lens import (
    ContactLensProductDetail, 
    ContactLensPrescription,
    ReplacementFrequency, 
    LensDesign,
    VerificationStatus
)
from app.schemas.contact_lens import (
    ContactLensOrderCreate, 
    EyeConfigSchema
)

router = APIRouter(prefix="/contact-lenses", tags=["Contact Lenses"])


# ==========================================
# PUBLIC CATALOG ENDPOINTS
# ==========================================

@router.get("/catalog")
def list_contact_lenses(
    brand: Optional[str] = Query(None, description="Filter by manufacturer (CooperVision, Acuvue, Alcon)"),
    frequency: Optional[ReplacementFrequency] = Query(None, description="Daily, bi-weekly, monthly, ortho-k"),
    design: Optional[LensDesign] = Query(None, description="Spherical, toric, multifocal, colored"),
    min_price: Optional[float] = Query(None, description="Min price per box"),
    max_price: Optional[float] = Query(None, description="Max price per box"),
    in_stock_only: bool = Query(True, description="Only show available stock"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve contact lens catalog with specialized optometry filters (wear schedule & design).
    """
    query = db.query(Product).join(ContactLensProductDetail).options(
        joinedload(Product.contact_lens_detail)
    ).filter(Product.is_active == True)

    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand.strip()}%"))
    if frequency:
        query = query.filter(ContactLensProductDetail.replacement_frequency == frequency)
    if design:
        query = query.filter(ContactLensProductDetail.lens_design == design)
    if min_price is not None:
        query = query.filter(Product.price_full_gbp >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_full_gbp <= max_price)
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)

    results = query.offset(skip).limit(limit).all()
    return results


@router.get("/catalog/{identifier}")
def get_contact_lens_detail(identifier: str, db: Session = Depends(get_db)):
    """
    Get lens product specifications including Base Curve (BC) and Diameter (DIA) option arrays.
    """
    clean_id = unquote(identifier).strip()
    
    query = db.query(Product).join(ContactLensProductDetail).options(
        joinedload(Product.contact_lens_detail)
    )

    if clean_id.isdigit():
        product = query.filter(Product.id == int(clean_id)).first()
    else:
        product = query.filter(Product.name.ilike(clean_id)).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact lens product '{identifier}' not found."
        )

    return product


# ==========================================
# CUSTOMER PRESCRIPTION VERIFICATION
# ==========================================

@router.post("/prescriptions", status_code=status.HTTP_201_CREATED)
def submit_contact_lens_prescription(
    prescription_data: ContactLensOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a UK contact lens specification sheet. Enforces unexpired date verification.
    """
    if prescription_data.expiry_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Under UK Opticians Act regulations, contact lens prescriptions must be active and unexpired."
        )

    new_prescription = ContactLensPrescription(
        user_id=current_user.id,
        prescription_file_url=prescription_data.prescription_file_url,
        expiry_date=prescription_data.expiry_date,
        status=VerificationStatus.PENDING,
        
        # Left Eye (OS)
        left_sph=prescription_data.left_eye.sph if prescription_data.left_eye else None,
        left_cyl=prescription_data.left_eye.cyl if prescription_data.left_eye else None,
        left_axis=prescription_data.left_eye.axis if prescription_data.left_eye else None,
        left_add=prescription_data.left_eye.add_power if prescription_data.left_eye else None,
        left_bc=prescription_data.left_eye.bc if prescription_data.left_eye else None,
        left_dia=prescription_data.left_eye.dia if prescription_data.left_eye else None,
        left_boxes_qty=prescription_data.left_eye.boxes_quantity if prescription_data.left_eye else 0,
        
        # Right Eye (OD)
        right_sph=prescription_data.right_eye.sph if prescription_data.right_eye else None,
        right_cyl=prescription_data.right_eye.cyl if prescription_data.right_eye else None,
        right_axis=prescription_data.right_eye.axis if prescription_data.right_eye else None,
        right_add=prescription_data.right_eye.add_power if prescription_data.right_eye else None,
        right_bc=prescription_data.right_eye.bc if prescription_data.right_eye else None,
        right_dia=prescription_data.right_eye.dia if prescription_data.right_eye else None,
        right_boxes_qty=prescription_data.right_eye.boxes_quantity if prescription_data.right_eye else 0,
    )

    db.add(new_prescription)
    db.commit()
    db.refresh(new_prescription)

    return {
        "message": "Prescription submitted for verification",
        "prescription_id": new_prescription.id,
        "status": new_prescription.status
    }


# ==========================================
# EYE-BY-EYE CART SELECTION
# ==========================================

@router.post("/cart/add")
def add_contact_lenses_to_cart(
    order: ContactLensOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configures and adds an eye-by-eye contact lens order to the customer's cart session.
    """
    product = db.query(Product).filter(Product.id == order.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact lens model not found."
        )

    total_boxes = 0
    if order.left_eye:
        total_boxes += order.left_eye.boxes_quantity
    if order.right_eye:
        total_boxes += order.right_eye.boxes_quantity

    if total_boxes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must select at least 1 box for left or right eye."
        )

    if product.stock_quantity < total_boxes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested {total_boxes} boxes, but only {product.stock_quantity} are in stock."
        )

    return {
        "status": "success",
        "product_id": product.id,
        "product_name": product.name,
        "total_boxes": total_boxes,
        "unit_price_gbp": product.price_full_gbp,
        "total_price_gbp": product.price_full_gbp * total_boxes,
        "left_eye_config": order.left_eye.dict() if order.left_eye else None,
        "right_eye_config": order.right_eye.dict() if order.right_eye else None
    }