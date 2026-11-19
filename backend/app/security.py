import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import models
from .database import get_db

ADMIN_ACCESS_TOKEN = os.getenv("OMARKET_ADMIN_TOKEN", "")
SESSION_SIGNING_SECRET = os.getenv("OMARKET_SESSION_SECRET", secrets.token_hex(32))


def sign_value(raw_value: str) -> str:
    digest = hmac.new(
        SESSION_SIGNING_SECRET.encode("utf-8"),
        raw_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{raw_value}.{digest}"


def verify_signed_value(signed_token: str) -> Optional[str]:
    if "." not in signed_token:
        return None
    raw_value, provided_sig = signed_token.rsplit(".", 1)
    expected_sig = hmac.new(
        SESSION_SIGNING_SECRET.encode("utf-8"),
        raw_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if hmac.compare_digest(provided_sig, expected_sig):
        return raw_value
    return None


def require_staff_access(
    x_admin_token: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Vérifie soit un jeton admin signé / clé d'accès configurée,
    soit un utilisateur existant en base avec le rôle 'admin' ou 'driver'.
    """
    if ADMIN_ACCESS_TOKEN and x_admin_token:
        if hmac.compare_digest(x_admin_token.strip(), ADMIN_ACCESS_TOKEN.strip()):
            admin_user = (
                db.query(models.User).filter(models.User.role == "admin").first()
            )
            if admin_user:
                return admin_user
            return models.User(
                id=0,
                phone="admin-system",
                full_name="Administrateur O'Market",
                role="admin",
            )

    if x_user_id:
        verified_id = verify_signed_value(x_user_id.strip())
        if verified_id and verified_id.isdigit():
            user = (
                db.query(models.User)
                .filter(models.User.id == int(verified_id))
                .first()
            )
            if user and user.role in ("admin", "driver"):
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Accès refusé : authentification opérateur ou administrateur requise.",
    )