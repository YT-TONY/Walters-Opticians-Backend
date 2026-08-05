from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartItemResponse, CartSummaryResponse
from app.api.deps import get_current_user
from app.api.v1.orders import standard_lens_fee, eye_exam_fee

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


def calculate_item_subtotal(item: CartItem) -> float:
    """Helper to compute subtotal per cart item based on frame price & lens/exam add-ons."""
    base_price = item.product.price
    if item.order_type in ["upload_prescription", "manual_prescription"]:
        base_price += standard_lens_fee
    elif item.order_type == "book_appointment":
        base_price += (standard_lens_fee + eye_exam_fee)
    return round(base_price * item.quantity, 2)


@router.get("/", response_model=CartSummaryResponse)
def get_user_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all active items in the current user's persistent cart along with overall totals.
    """
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    
    formatted_items = []
    total_quantity = 0
    estimated_subtotal = 0.0

    for item in cart_items:
        subtotal = calculate_item_subtotal(item)
        item_data = CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            order_type=item.order_type,
            appointment_date=item.appointment_date,
            prescription_file_url=item.prescription_file_url,
            right_sph=item.right_sph,
            right_cyl=item.right_cyl,
            right_axis=item.right_axis,
            left_sph=item.left_sph,
            left_cyl=item.left_cyl,
            left_axis=item.left_axis,
            pd_mm=item.pd_mm,
            product=item.product,
            item_subtotal=subtotal
        )
        formatted_items.append(item_data)
        total_quantity += item.quantity
        estimated_subtotal += subtotal

    return {
        "items": formatted_items,
        "total_items": total_quantity,
        "estimated_subtotal": round(estimated_subtotal, 2)
    }


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_item_to_cart(
    item_in: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a frame to the user's cart. If the same frame and order_type exist, increment quantity.
    """
    product = db.query(Product).filter(Product.id == item_in.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    # Check for existing item with identical product and configuration
    existing_item = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.product_id == item_in.product_id,
        CartItem.order_type == item_in.order_type
    ).first()

    if existing_item:
        existing_item.quantity += item_in.quantity
        db.commit()
        db.refresh(existing_item)
        cart_item = existing_item
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            **item_in.dict()
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)

    subtotal = calculate_item_subtotal(cart_item)
    return CartItemResponse(
        id=cart_item.id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity,
        order_type=cart_item.order_type,
        appointment_date=cart_item.appointment_date,
        prescription_file_url=cart_item.prescription_file_url,
        right_sph=cart_item.right_sph,
        right_cyl=cart_item.right_cyl,
        right_axis=cart_item.right_axis,
        left_sph=cart_item.left_sph,
        left_cyl=cart_item.left_cyl,
        left_axis=cart_item.left_axis,
        pd_mm=cart_item.pd_mm,
        product=cart_item.product,
        item_subtotal=subtotal
    )


@router.put("/items/{item_id}", response_model=CartItemResponse)
def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quantity or selected configuration for a cart item.
    """
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user.id
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found.")

    update_data = item_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cart_item, field, value)

    db.commit()
    db.refresh(cart_item)

    subtotal = calculate_item_subtotal(cart_item)
    return CartItemResponse(
        id=cart_item.id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity,
        order_type=cart_item.order_type,
        appointment_date=cart_item.appointment_date,
        prescription_file_url=cart_item.prescription_file_url,
        right_sph=cart_item.right_sph,
        right_cyl=cart_item.right_cyl,
        right_axis=cart_item.right_axis,
        left_sph=cart_item.left_sph,
        left_cyl=cart_item.left_cyl,
        left_axis=cart_item.left_axis,
        pd_mm=cart_item.pd_mm,
        product=cart_item.product,
        item_subtotal=subtotal
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a single item from the cart.
    """
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user.id
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found.")

    db.delete(cart_item)
    db.commit()
    return None


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all items in the user's cart (e.g., post-checkout or manual reset).
    """
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    return None