# app/api/v1/favorites.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.favorite import Favorite
from app.models.product import Product
from app.models.user import User
from app.schemas.favorite import FavoriteResponse, FavoriteToggleResponse

router = APIRouter(prefix="/favorites", tags=["Favorites & Wishlist"])

@router.get("/", response_model=List[FavoriteResponse])
def get_user_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all favorited products for the currently authenticated user.
    """
    favorites = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return favorites

@router.post("/toggle/{product_id}", response_model=FavoriteToggleResponse)
def toggle_favorite(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggle a product in user's favorites list (Adds if absent, Removes if present).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} does not exist."
        )

    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == product_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {
            "favorited": False,
            "product_id": product_id,
            "message": "Removed from wishlist"
        }

    new_fav = Favorite(user_id=current_user.id, product_id=product_id)
    db.add(new_fav)
    db.commit()
    return {
        "favorited": True,
        "product_id": product_id,
        "message": "Saved to wishlist"
    }

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def remove_favorite(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a specific product from favorites.
    """
    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == product_id
    ).first()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in favorites."
        )

    db.delete(favorite)
    db.commit()
    return {"message": "Product removed from favorites", "product_id": product_id}

@router.delete("/", status_code=status.HTTP_200_OK)
def clear_all_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all saved items from the user's wishlist.
    """
    db.query(Favorite).filter(Favorite.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Wishlist cleared successfully"}