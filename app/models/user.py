#app/models/user.py

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth-only users
    previous_hashed_password = Column(String, nullable=True)  # Stores previous password hash
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # True for OAuth users automatically
    
    # OAuth Provider IDs
    google_id = Column(String, unique=True, index=True, nullable=True)
    facebook_id = Column(String, unique=True, index=True, nullable=True)
    apple_id = Column(String, unique=True, index=True, nullable=True)

    # Verification & Reset Tokens
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    prescriptions = relationship("UserPrescription", back_populates="user", cascade="all, delete-orphan")