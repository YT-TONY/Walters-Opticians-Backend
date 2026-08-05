from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import ai, auth, cart, currency, orders, products
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

from app.models.user import User
from app.models.product import Product
from app.models.order import Order
from app.models.store_settings import StoreSetting

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

# Set up CORS middleware for frontend clients (React/Next.js/Mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
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