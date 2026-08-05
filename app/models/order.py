from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Order Type: "frame_only", "upload_prescription", "manual_prescription", "book_appointment"
    order_type = Column(String, nullable=False)

    # Delivery & Location
    shipping_address = Column(String, nullable=False)
    country = Column(String, nullable=False)  # ISO code or country name (e.g., "UK", "NG")
    
    # Financial Breakdown (All in GBP £)
    frame_price = Column(Float, nullable=False)
    lens_fee = Column(Float, default=0.0)
    exam_fee = Column(Float, default=0.0)
    shipping_fee = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)

    # Status: "pending", "paid", "examined", "shipped", "delivered"
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Appointment Details (UK only)
    appointment_date = Column(DateTime, nullable=True)

    # Prescription Details
    prescription_file_url = Column(String, nullable=True)
    right_sph = Column(Float, nullable=True)
    right_cyl = Column(Float, nullable=True)
    right_axis = Column(Integer, nullable=True)
    left_sph = Column(Float, nullable=True)
    left_cyl = Column(Float, nullable=True)
    left_axis = Column(Integer, nullable=True)
    pd_mm = Column(Float, nullable=True)