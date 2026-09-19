from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserCreate, UserUpdate, UserLogin, UserResponse, Token,
    OAuthGoogleRequest,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest, ResendVerificationRequest
)
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.core.oauth import (
    verify_google_id_token, verify_facebook_token,
    generate_random_token, send_email
)
from app.api.deps import get_current_user

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def issue_token_response(user: User, is_new_user: bool = False) -> dict:
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": role_val}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role_val,
        "user": user,
        "is_new_user": is_new_user
    }


@router.post(
    "/signup", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account"
)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    clean_email = user_in.email.lower().strip()

    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        if existing_user.google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is registered via Google. Please log in using Google."
            )
        if getattr(existing_user, "facebook_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is registered via Facebook. Please log in using Facebook."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    v_token = generate_random_token()

    new_user = User(
        full_name=user_in.full_name,
        email=clean_email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.CUSTOMER,
        is_verified=False,
        verification_token=v_token
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={v_token}"
    html = f"""
    <h2>Welcome to Walters Opticians!</h2>
    <p>Please click the link below to verify your email address and activate your account:</p>
    <p><a href="{verify_link}" style="padding: 10px 18px; background: #0F172A; color: white; border-radius: 8px; text-decoration: none;">Verify Email Address</a></p>
    <p>Or copy this URL: {verify_link}</p>
    """
    send_email(clean_email, "Verify Your Email — Walters Opticians", html)

    return new_user


@router.post(
    "/login", 
    response_model=Token,
    summary="Unified login for Customers & Admins"
)
@limiter.limit("5/minute")
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    email_clean = credentials.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()

    if user and not user.hashed_password:
        if user.google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is registered via Google Sign-In. Please click 'Google' to log in."
            )
        if getattr(user, "facebook_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is registered via Facebook Sign-In. Please click 'Facebook' to log in."
            )

    # Detect if user is attempting to log in with a recently changed old password
    if user and getattr(user, "previous_hashed_password", None) and user.previous_hashed_password:
        if verify_password(credentials.password, user.previous_hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This password was recently changed. Please log in using your new password."
            )

    if not user or not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in."
        )

    return issue_token_response(user)


@router.post("/google", response_model=Token, summary="Sign in or Sign up with Google")
def google_auth(payload: OAuthGoogleRequest, db: Session = Depends(get_db)):
    google_data = verify_google_id_token(payload.id_token)
    email = google_data["email"].lower().strip()

    user = db.query(User).filter(
        (User.google_id == google_data["google_id"]) | (User.email == email)
    ).first()

    is_new = False
    if user:
        if not user.google_id:
            user.google_id = google_data["google_id"]
        user.is_verified = True
        db.commit()
    else:
        is_new = True
        user = User(
            full_name=google_data["full_name"],
            email=email,
            google_id=google_data["google_id"],
            role=UserRole.CUSTOMER,
            is_verified=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return issue_token_response(user, is_new_user=is_new)


@router.post("/facebook", response_model=Token, summary="Sign in or Sign up with Facebook")
def facebook_auth(payload: OAuthGoogleRequest, db: Session = Depends(get_db)):
    fb_data = verify_facebook_token(payload.id_token)
    fb_id = fb_data["facebook_id"]
    raw_email = fb_data.get("email")

    user = db.query(User).filter(User.facebook_id == fb_id).first()

    if not user and raw_email:
        user = db.query(User).filter(User.email == raw_email).first()

    is_new = False
    if user:
        if not user.facebook_id:
            user.facebook_id = fb_id
        user.is_verified = True
        db.commit()
    else:
        is_new = True
        final_email = raw_email if raw_email else f"fb_{fb_id}@noemail.facebook.com"

        user = User(
            full_name=fb_data["full_name"],
            email=final_email,
            facebook_id=fb_id,
            role=UserRole.CUSTOMER,
            is_verified=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return issue_token_response(user, is_new_user=is_new)


@router.post("/verify-email", response_model=Token, summary="Verify email account with token")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == payload.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    user.is_verified = True
    user.verification_token = None
    db.commit()
    db.refresh(user)

    # Returns session token to log the user in immediately
    return issue_token_response(user)


@router.post("/resend-verification", summary="Resend email verification link")
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user and not user.is_verified:
        v_token = generate_random_token()
        user.verification_token = v_token
        db.commit()

        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={v_token}"
        html = f"""
        <h2>Verify Your Email — Walters Opticians</h2>
        <p>Click below to verify your account:</p>
        <p><a href="{verify_link}">Verify Email Address</a></p>
        """
        send_email(user.email, "Verify Your Email — Walters Opticians", html)

    return {"message": "If an unverified account exists for this email, a verification link has been sent."}


@router.post("/forgot-password", summary="Request password reset token email")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()

    if user:
        r_token = generate_random_token()
        user.reset_token = r_token
        user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.commit()

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={r_token}"
        html = f"""
        <h2>Password Reset Request</h2>
        <p>You requested a password reset for your Walters Opticians account. Click the button below to proceed:</p>
        <p><a href="{reset_link}" style="padding: 10px 18px; background: #0F172A; color: white; border-radius: 8px; text-decoration: none;">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
        """
        send_email(user.email, "Password Reset Request — Walters Opticians", html)

    return {"message": "If an account exists for this email, password reset instructions have been sent."}


@router.post("/reset-password", response_model=Token, summary="Reset password using token")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.reset_token == payload.token,
        User.reset_token_expires_at > datetime.utcnow()
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    # Reject if new password matches existing password
    if user.hashed_password and verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your new password cannot be the same as your old password."
        )

    user.previous_hashed_password = user.hashed_password
    user.hashed_password = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    db.refresh(user)

    # Returns session token to log the user in immediately
    return issue_token_response(user)


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Update current user profile")
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.full_name:
        current_user.full_name = payload.full_name.strip()

    db.commit()
    db.refresh(current_user)
    return current_user