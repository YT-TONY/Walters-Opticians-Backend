#app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    admin,
    ai,
    auth,
    cart,
    categories,
    contact_lenses,
    currency,
    favorites,
    orders,
    prescriptions,
    products,
)
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Import ALL database models so SQLAlchemy registers every mapper & relationship
from app.models.user import User
from app.models.product import Product
from app.models.order import Order
from app.models.store_settings import StoreSetting
from app.models.prescription import UserPrescription
from app.models.cart import CartItem
from app.models.categories import Category
from app.models.contact_lens import ContactLensProductDetail, ContactLensPrescription
from app.models.favorite import Favorite

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=getattr(settings, "PROJECT_NAME", "Walters Opticians API"),
    description="E-commerce and clinic management backend for Walters Opticians.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# Set up CORS middleware for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(currency.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories & Brands"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin Analytics & Management"])
app.include_router(favorites.router, prefix="/api/v1", tags=["Favorites & Wishlist"])
app.include_router(contact_lenses.router, prefix="/api/v1", tags=["Contact Lenses"])
app.include_router(prescriptions.router, prefix="/api/v1", tags=["Prescriptions"])


@app.get("/", tags=["Health Check"])
def root():
    return {
        "service": "Walters Opticians API",
        "status": "online",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "healthy"}