from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from .database import get_db
from . import models

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class PhoneAuthRequest(BaseModel):
    phone: str
    full_name: Optional[str] = "Client O'Market"

@router.post("/login-register")
def phone_login_register(payload: PhoneAuthRequest, db: Session = Depends(get_db)):
    """
    Vérifie si l'utilisateur existe via son numéro de téléphone.
    S'il n'existe pas, le crée automatiquement. S'il existe, le connecte.
    Zéro friction, pas d'e-mail requis.
    """
    clean_phone = payload.phone.strip()
    
    if not clean_phone:
        raise HTTPException(status_code=400, status_message="Le numéro de téléphone est obligatoire.")

    # Recherche de l'utilisateur dans la base Supabase
    user = db.query(models.User).filter(models.User.phone == clean_phone).first()

    if not user:
        # Création automatique du compte
        user = models.User(
            phone=clean_phone,
            full_name=payload.full_name,
            role="client"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        message = "Compte créé avec succès. Bienvenue sur O'Market !"
    else:
        message = "Connexion réussie."

    return {
        "success": True,
        "message": message,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role
        }
    }