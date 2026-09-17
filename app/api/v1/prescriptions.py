#app/api/v1/prescriptions.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.prescription import UserPrescription
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionUpdate,
    PrescriptionResponse,
)
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.get("/me", response_model=List[PrescriptionResponse])
def get_my_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(UserPrescription)
        .filter(UserPrescription.user_id == current_user.id)
        .order_by(UserPrescription.is_default.desc(), UserPrescription.created_at.desc())
        .all()
    )


@router.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    prescription_in: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if prescription_in.is_default:
        db.query(UserPrescription).filter(
            UserPrescription.user_id == current_user.id,
            UserPrescription.is_default == True,
        ).update({"is_default": False})

    db_prescription = UserPrescription(
        **prescription_in.model_dump(),
        user_id=current_user.id,
    )
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription


@router.put("/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(
    prescription_id: int,
    prescription_in: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rx = (
        db.query(UserPrescription)
        .filter(
            UserPrescription.id == prescription_id,
            UserPrescription.user_id == current_user.id,
        )
        .first()
    )
    if not rx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    update_data = prescription_in.model_dump(exclude_unset=True)

    if update_data.get("is_default"):
        db.query(UserPrescription).filter(
            UserPrescription.user_id == current_user.id,
            UserPrescription.is_default == True,
        ).update({"is_default": False})

    for field, value in update_data.items():
        setattr(rx, field, value)

    db.commit()
    db.refresh(rx)
    return rx


@router.put("/{prescription_id}/default", response_model=PrescriptionResponse)
def set_default_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rx = (
        db.query(UserPrescription)
        .filter(
            UserPrescription.id == prescription_id,
            UserPrescription.user_id == current_user.id,
        )
        .first()
    )
    if not rx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    db.query(UserPrescription).filter(
        UserPrescription.user_id == current_user.id,
        UserPrescription.is_default == True,
    ).update({"is_default": False})

    rx.is_default = True
    db.commit()
    db.refresh(rx)
    return rx


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rx = (
        db.query(UserPrescription)
        .filter(
            UserPrescription.id == prescription_id,
            UserPrescription.user_id == current_user.id,
        )
        .first()
    )
    if not rx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    db.delete(rx)
    db.commit()
    return None