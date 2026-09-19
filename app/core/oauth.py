# app/core/oauth.py

import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException, status
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
import requests

from app.core.config import settings


def verify_google_id_token(token: str) -> dict:
    """Verifies a Google OAuth token (supports both JWT ID tokens and Access tokens)."""
    if token.startswith("ya29."):
        try:
            response = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Google access token.",
                )

            user_data = response.json()
            email = user_data.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google account email not found.",
                )

            return {
                "google_id": user_data.get("sub"),
                "email": email,
                "full_name": user_data.get("name", email.split("@")[0]),
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to verify Google access token: {str(e)}",
            )

    try:
        id_info = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        return {
            "google_id": id_info["sub"],
            "email": id_info["email"],
            "full_name": id_info.get("name", id_info["email"].split("@")[0]),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(e)}",
        )


def verify_facebook_token(token: str) -> dict:
    """
    Verifies a Facebook OAuth access token via Meta Graph API.
    Safely handles accounts with or without a primary email address.
    """
    try:
        response = requests.get(
            f"https://graph.facebook.com/v19.0/me?fields=id,name,email&access_token={token}",
            timeout=10,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Facebook access token.",
            )

        data = response.json()
        fb_id = str(data.get("id"))
        raw_email = data.get("email")
        clean_email = raw_email.lower().strip() if raw_email else None
        
        full_name = data.get("name") or (clean_email.split("@")[0] if clean_email else f"FB User {fb_id[-4:]}")

        return {
            "facebook_id": fb_id,
            "email": clean_email,
            "full_name": full_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to verify Facebook token: {str(e)}",
        )


def generate_random_token() -> str:
    return secrets.token_urlsafe(32)


def send_email(to_email: str, subject: str, body_html: str):
    """Sends transactional HTML emails using configured SMTP server."""
    if not settings.MAIL_SERVER or not settings.MAIL_USERNAME:
        print(f"[MOCK EMAIL SENT to {to_email}]: {subject}\n{body_html}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            if settings.MAIL_STARTTLS:
                server.starttls()
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")