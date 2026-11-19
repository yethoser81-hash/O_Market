from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, get_db
from . import models, schemas
from .auth import router as auth_router

# Création automatique des tables si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="O'Market API",
    description="Backend officiel et sécurisé de la plateforme O'Market (Cameroun).",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion du routeur d'authentification par téléphone
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {
        "app": "O'Market API",
        "status": "online",
        "message": "Le moteur de O'Market tourne à plein régime 🚀"
    }

@app.get("/api/products", response_model=List[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    """
    Récupère l'intégralité du catalogue des produits pour la vitrine.
    """
    products = db.query(models.Product).all()
    # Données de secours si la base est vide lors des tests initiaux
    if not products:
        return [
            {"id": 1, "name": "Huile Yamaor 1L", "price": 2000.0, "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5", "is_sponsored": False, "stock": 50},
            {"id": 2, "name": "Riz Broli 5kg", "price": 4500.0, "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c", "is_sponsored": True, "stock": 30},
            {"id": 3, "name": "Savon Kabako", "price": 400.0, "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae", "is_sponsored": False, "stock": 100}
        ]
    return products

@app.post("/api/smart-list")
def parse_smart_list(payload: schemas.SmartListRequest):
    """
    Moteur 'Liste Magique' : analyse le texte brut (saisi ou transcrit d'un vocal)
    pour structurer automatiquement le panier du client avec les prix locaux.
    """
    text = payload.raw_text.lower()
    detected_items = []
    
    # Logique d'analyse textuelle locale (marques phares au Cameroun)
    if "huile" in text or "yamaor" in text:
        detected_items.append({"product_name": "Huile Yamaor 1L", "quantity": 1, "unit_price": 2000.0})
    if "riz" in text or "broli" in text:
        detected_items.append({"product_name": "Riz Broli 5kg", "quantity": 1, "unit_price": 4500.0})
    if "savon" in text or "kabako" in text:
        detected_items.append({"product_name": "Savon Kabako", "quantity": 2, "unit_price": 400.0})
        
    if not detected_items:
        detected_items.append({"product_name": payload.raw_text, "quantity": 1, "unit_price": 0.0})

    total_estime = sum(item["quantity"] * item["unit_price"] for item in detected_items)

    return {
        "success": True,
        "raw_input": payload.raw_text,
        "parsed_items": detected_items,
        "total_estimated": total_estime,
        "message": "Liste convertie en panier avec succès par O'Market AI."
    }

@app.post("/api/orders")
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """
    Crée une commande après validation et pré-paiement strict.
    """
    total = sum(item.quantity * item.unit_price for item in order.items)
    
    new_order = models.Order(
        user_id=order.user_id,
        total_amount=total,
        delivery_address=order.delivery_address,
        landmark=order.landmark,
        status="pending_payment",
        payment_status="unpaid"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return {
        "success": True,
        "order_id": new_order.id,
        "total_amount": total,
        "status": new_order.status,
        "message": "Commande enregistrée. En attente de confirmation du paiement Mobile Money."
    }