#app/models/product.py
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    model_code = Column(String, index=True, nullable=True)
    name = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=False)
    gender = Column(String, default="unisex", nullable=True)
    shape = Column(String, index=True, nullable=False)
    color_description = Column(String, index=True, nullable=False)
    color_code = Column(String, nullable=True) # e.g. "8228"
    frame_type = Column(String, default="full-rim", nullable=False)

    # Narrative Description
    description = Column(Text, nullable=True)

    # Materials & Lens Specs
    frame_material = Column(String, nullable=True, default="Plastic")
    lens_material = Column(String, nullable=True, default="Demo Lens")
    lens_color = Column(String, nullable=True, default="Transparent")
    glass_base = Column(String, nullable=True, default="Base 4")
    polarized = Column(Boolean, default=False)
    photochromic = Column(Boolean, default=False)
    gradables = Column(Boolean, default=False)
    
    # Sizes & Size Chart Reference Image
    sizes = Column(JSON, default=list, nullable=True)
    size_chart_url = Column(Text, nullable=True)

    # Optical Sizing (mm)
    lens_width = Column(Float, nullable=True, default=54.0)
    bridge_width = Column(Float, nullable=True, default=17.0)
    temple_length = Column(Float, nullable=True, default=140.0)
    lens_height = Column(Float, nullable=True, default=38.0)

    # Pricing & Stock
    price_full_gbp = Column(Float, nullable=False)
    allow_frame_only = Column(Boolean, default=True)
    price_frame_only_gbp = Column(Float, nullable=False)
    image_url = Column(Text, nullable=False)
    gallery = Column(JSON, default=list, nullable=True)
    stock_quantity = Column(Integer, default=15, nullable=False)
    is_active = Column(Boolean, index=True, default=True, nullable=False)
    is_featured = Column(Boolean, default=False)
    is_bestseller = Column(Boolean, default=False)