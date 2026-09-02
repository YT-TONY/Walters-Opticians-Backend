# app/models/order.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

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

    # Fulfillment Status: "Order Placed", "Processing", "In Fulfillment", "Dispatched", "In Transit", "Out for Delivery", "Delivered", etc.
    status = Column(String, default="Order Placed")

    # Prescription Status: "pending_review", "verified", "rejected", "sent_to_lab", "lab_completed", "n_a"
    prescription_status = Column(String, default="pending_review")

    # Shipping & Tracking Metadata
    carrier = Column(String, nullable=True)  # e.g., "Royal Mail", "DHL Express"
    tracking_number = Column(String, nullable=True, index=True)
    shipping_label_url = Column(String, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)

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