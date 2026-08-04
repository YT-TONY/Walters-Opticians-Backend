from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=False)
    shape = Column(String, nullable=False)  # Round, Square, Aviator, Rectangle, Cat-Eye
    color_description = Column(String, nullable=False)  # Tortoise Amber, Cobalt Depth
    
    # Pricing in Base Currency (GBP £)
    price_full_gbp = Column(Float, nullable=False)  # Frame + Standard Prescription Lens
    allow_frame_only = Column(Boolean, default=True)
    price_frame_only_gbp = Column(Float, nullable=False)  # Frame without lens
    
    image_url = Column(Text, nullable=False)
    stock_quantity = Column(Integer, default=15)
    is_featured = Column(Boolean, default=False)