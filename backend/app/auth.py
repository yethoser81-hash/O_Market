from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import sign_value

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class PhoneAuthRequest(BaseModel):
    phone: str
    full_name: Optional[str] = "Client O'Market"


@router.post("/login-register")
def phone_login_register(payload: PhoneAuthRequest, db: Session = Depends(get_db)):
    clean_phone = payload.phone.strip()

    if not clean_phone:
        raise HTTPException(
            status_code=400, detail="Le numéro de téléphone est obligatoire."
        )

    user = db.query(models.User).filter(models.User.phone == clean_phone).first()

    if not user:
        user = models.User(
            phone=clean_phone,
            full_name=(payload.full_name or "Client O'Market").strip(),
            role="client",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        message = "Compte créé avec succès. Bienvenue sur O'Market !"
    else:
        if payload.full_name and payload.full_name.strip():
            user.full_name = payload.full_name.strip()
            db.commit()
            db.refresh(user)
        message = "Connexion réussie."

    staff_session_token = (
        sign_value(str(user.id)) if user.role in ("admin", "driver") else None
    )

    return {
        "success": True,
        "message": message,
        "staff_token": staff_session_token,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
        },
    }