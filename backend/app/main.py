import math
import re
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import router as auth_router
from .database import Base, engine, get_db
from .security import require_staff_access

Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

SERVICE_FEE_FCFA = 100.0
MIN_DELIVERY_FEE_FCFA = 1000.0
INTERMEDIATE_DELIVERY_FEE_FCFA = 1500.0
REMOTE_DELIVERY_FEE_FCFA = 2000.0

REMOTE_ZONE_KEYWORDS = {
    "soba",
    "nkolfoulou",
    "mbalmayo",
    "ekounou",
    "odza",
    "nkolbisson",
    "ping",
    "minboman",
    "ahala",
    "nkoabang",
    "simbock",
    "oyomabang",
}

INTERMEDIATE_ZONE_KEYWORDS = {
    "mvan",
    "emana",
    "mendong",
    "etoudi",
    "essos",
    "melen",
    "biyem-assi",
    "biyem assi",
    "ekoudou",
    "nlongkak",
    "ngousso",
    "mokolo",
}

NUMBER_WORDS = {
    "un": 1.0,
    "une": 1.0,
    "deux": 2.0,
    "trois": 3.0,
    "quatre": 4.0,
    "cinq": 5.0,
    "six": 6.0,
    "sept": 7.0,
    "huit": 8.0,
    "neuf": 9.0,
    "dix": 10.0,
    "demi": 0.5,
    "demie": 0.5,
}

app = FastAPI(
    title="O'Market API",
    description="Backend officiel et sécurisé de la plateforme O'Market (Cameroun).",
    version="1.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


def calculate_delivery_pricing(address: str, landmark: Optional[str]) -> Tuple[str, float]:
    """
    Calcule la zone et les frais de livraison côté serveur.
    Plancher minimal : 1 000 FCFA.
    """
    combined = f"{address or ''} {landmark or ''}".lower()

    for kw in REMOTE_ZONE_KEYWORDS:
        if kw in combined:
            return "reculée / éloignée", max(MIN_DELIVERY_FEE_FCFA, REMOTE_DELIVERY_FEE_FCFA)

    for kw in INTERMEDIATE_ZONE_KEYWORDS:
        if kw in combined:
            return "intermédiaire", max(MIN_DELIVERY_FEE_FCFA, INTERMEDIATE_DELIVERY_FEE_FCFA)

    return "standard", MIN_DELIVERY_FEE_FCFA


def extract_quantity_for_match(text: str, start_idx: int, default_unit: str) -> Tuple[float, str]:
    """
    Extrait une quantité et une unité éventuelle autour d'un produit détecté dans le texte.
    """
    window = text[max(0, start_idx - 28) : min(len(text), start_idx + 28)]

    gram_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:g|gr|grammes?)\b", window)
    if gram_match and default_unit in ("kg", "g", "unité"):
        grams = float(gram_match.group(1).replace(",", "."))
        if default_unit == "kg":
            return round(grams / 1000.0, 3), "kg"
        return grams, "g"

    kg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?|kilogrammes?)\b", window)
    if kg_match:
        kg_val = float(kg_match.group(1).replace(",", "."))
        if default_unit == "g":
            return kg_val * 1000.0, "g"
        return kg_val, "kg"

    unit_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:mottes?|tas|sachets?|bidons?|bouteilles?|litres?|l|pièces?|pieces?)?\b",
        window,
    )
    if unit_match:
        qty_val = float(unit_match.group(1).replace(",", "."))
        if qty_val > 0:
            return qty_val, default_unit

    for word, val in NUMBER_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", window):
            return val, default_unit

    return 1.0, default_unit


@app.get("/api/health")
def api_health():
    return {
        "app": "O'Market API",
        "status": "online",
        "message": "Le moteur de O'Market tourne à plein régime",
    }


@app.get("/")
def read_root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "app": "O'Market API",
        "status": "online",
        "message": "Le moteur de O'Market tourne à plein régime",
    }


@app.head("/")
def head_root():
    return {"status": "online"}


# --- CATÉGORIES / RAYONS ---
@app.get("/api/categories", response_model=List[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.id.asc()).all()


@app.post(
    "/api/categories",
    response_model=schemas.CategoryOut,
    status_code=201,
    dependencies=[Depends(require_staff_access)],
)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db)):
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Le nom de la catégorie est obligatoire.")

    clean_slug = (
        payload.slug.strip().lower()
        if payload.slug and payload.slug.strip()
        else re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-")
    )
    category = models.Category(
        name=clean_name,
        slug=clean_slug,
        icon_url=payload.icon_url,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# --- GESTION DES RÔLES ÉQUIPE (ADMIN & LIVREURS MOTO) ---
@app.get(
    "/api/users",
    response_model=List[schemas.UserOut],
    dependencies=[Depends(require_staff_access)],
)
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id.desc()).all()


@app.patch(
    "/api/users/{user_id}/role",
    response_model=schemas.UserOut,
    dependencies=[Depends(require_staff_access)],
)
def update_user_role(
    user_id: int, payload: schemas.UserRoleUpdate, db: Session = Depends(get_db)
):
    allowed_roles = {"client", "driver", "admin"}
    clean_role = payload.role.strip().lower()
    if clean_role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail="Rôle invalide. Valeurs autorisées : client, driver, admin.",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    user.role = clean_role
    db.commit()
    db.refresh(user)
    return user


# --- PRODUITS, UNITÉS, PRIX & PROMOTIONS ---
@app.get("/api/products", response_model=List[schemas.ProductOut])
def get_products(
    category_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)
):
    query = db.query(models.Product)
    if category_id is not None:
        query = query.filter(models.Product.category_id == category_id)
    return query.order_by(models.Product.id.desc()).all()


@app.post(
    "/api/products",
    response_model=schemas.ProductOut,
    status_code=201,
    dependencies=[Depends(require_staff_access)],
)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    product = models.Product(
        category_id=payload.category_id,
        name=payload.name.strip(),
        description=payload.description,
        price=payload.price,
        unit_label=payload.unit_label.strip().lower(),
        unit_step=payload.unit_step,
        image_url=payload.image_url,
        is_sponsored=payload.is_sponsored,
        stock=payload.stock,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.patch(
    "/api/products/{product_id}",
    response_model=schemas.ProductOut,
    dependencies=[Depends(require_staff_access)],
)
def update_product(
    product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable.")

    updates = payload.model_dump(exclude_unset=True)
    if "unit_label" in updates and updates["unit_label"]:
        updates["unit_label"] = updates["unit_label"].strip().lower()

    for key, value in updates.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@app.delete(
    "/api/products/{product_id}",
    dependencies=[Depends(require_staff_access)],
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable.")

    db.delete(product)
    db.commit()
    return {"success": True, "deleted_id": product_id}


# --- BANNÈRES / PROMOS ---
@app.get("/api/banners", response_model=List[schemas.BannerOut])
def get_banners(db: Session = Depends(get_db)):
    return db.query(models.AdsBanner).order_by(models.AdsBanner.id.desc()).all()


@app.post(
    "/api/banners",
    response_model=schemas.BannerOut,
    status_code=201,
    dependencies=[Depends(require_staff_access)],
)
def create_banner(payload: schemas.BannerCreate, db: Session = Depends(get_db)):
    banner = models.AdsBanner(
        title=payload.title,
        image_url=payload.image_url.strip(),
        target_url=payload.target_url,
        is_active=payload.is_active,
    )
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


# --- LISTE MAGIQUE ---
@app.post("/api/smart-list")
def parse_smart_list(payload: schemas.SmartListRequest, db: Session = Depends(get_db)):
    raw = payload.raw_text.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Le texte de la liste est vide.")

    text = raw.lower()
    detected_items = []
    db_products = db.query(models.Product).all()

    for prod in db_products:
        tokens = [w for w in prod.name.lower().split() if len(w) > 2]
        matched_pos = None
        for tok in tokens:
            idx = text.find(tok)
            if idx != -1:
                matched_pos = idx
                break

        if matched_pos is not None:
            default_unit = (prod.unit_label or "unité").lower()
            qty, resolved_unit = extract_quantity_for_match(text, matched_pos, default_unit)
            unit_price = float(prod.price)
            detected_items.append(
                {
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "quantity": qty,
                    "unit_label": resolved_unit,
                    "unit_price": unit_price,
                    "line_total": round(qty * unit_price, 2),
                }
            )

    total_estime = round(
        sum(item["quantity"] * item["unit_price"] for item in detected_items), 2
    )

    return {
        "success": True,
        "raw_input": raw,
        "parsed_items": detected_items,
        "total_estimated": total_estime,
        "message": (
            "Liste analysée avec succès par O'Market."
            if detected_items
            else "Aucun produit du catalogue ne correspond encore à cette saisie."
        ),
    }


def _build_order_out(db: Session, ord_obj: models.Order) -> schemas.OrderOut:
    items = (
        db.query(models.OrderItem)
        .filter(models.OrderItem.order_id == ord_obj.id)
        .all()
    )
    return schemas.OrderOut(
        id=ord_obj.id,
        user_id=ord_obj.user_id,
        status=ord_obj.status,
        items_subtotal=ord_obj.items_subtotal,
        delivery_fee=ord_obj.delivery_fee,
        service_fee=ord_obj.service_fee,
        total_amount=ord_obj.total_amount,
        delivery_zone=ord_obj.delivery_zone,
        delivery_address=ord_obj.delivery_address,
        landmark=ord_obj.landmark,
        payment_status=ord_obj.payment_status,
        created_at=ord_obj.created_at,
        items=items,
    )


# --- HISTORIQUE ACHATS CLIENT ---
@app.get("/api/my-orders", response_model=List[schemas.OrderOut])
def get_my_orders(
    user_id: int = Query(..., gt=0), db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    orders = (
        db.query(models.Order)
        .filter(models.Order.user_id == user_id)
        .order_by(models.Order.id.desc())
        .all()
    )
    return [_build_order_out(db, ord_obj) for ord_obj in orders]


# --- COMMANDES & LOGISTIQUE (PRIX, LIVRAISON & COMMISSION VERROUILLÉS SERVEUR) ---
@app.get(
    "/api/orders",
    response_model=List[schemas.OrderOut],
    dependencies=[Depends(require_staff_access)],
)
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).order_by(models.Order.id.desc()).all()
    return [_build_order_out(db, ord_obj) for ord_obj in orders]


@app.post("/api/orders")
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    if not order.items:
        raise HTTPException(
            status_code=400, detail="La commande doit contenir au moins un article."
        )

    if not order.delivery_address.strip():
        raise HTTPException(
            status_code=400, detail="L'adresse de livraison est obligatoire."
        )

    resolved_user_id = order.user_id
    if resolved_user_id is None:
        guest_user = (
            db.query(models.User).filter(models.User.phone == "000000000").first()
        )
        if not guest_user:
            guest_user = models.User(
                phone="000000000", full_name="Client Rapide", role="client"
            )
            db.add(guest_user)
            db.commit()
            db.refresh(guest_user)
        resolved_user_id = guest_user.id
    else:
        user_exists = (
            db.query(models.User).filter(models.User.id == resolved_user_id).first()
        )
        if not user_exists:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    requested_qty_by_id = {}
    requested_unit_by_id = {}
    for item in order.items:
        requested_qty_by_id[item.product_id] = (
            requested_qty_by_id.get(item.product_id, 0.0) + float(item.quantity)
        )
        if item.unit_label and item.unit_label.strip():
            requested_unit_by_id[item.product_id] = item.unit_label.strip().lower()

    verified_lines = []
    items_subtotal = 0.0

    for prod_id, qty in requested_qty_by_id.items():
        product = (
            db.query(models.Product)
            .filter(models.Product.id == prod_id)
            .with_for_update()
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Produit #{prod_id} introuvable dans le catalogue.",
            )

        stock_units_needed = max(1, math.ceil(qty))
        if product.stock < stock_units_needed:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant pour '{product.name}' (disponible : {product.stock}).",
            )

        official_unit_price = float(product.price)
        line_total = round(official_unit_price * qty, 2)
        items_subtotal += line_total
        chosen_unit = requested_unit_by_id.get(prod_id) or (product.unit_label or "unité")
        verified_lines.append((product, qty, stock_units_needed, chosen_unit, official_unit_price))

    items_subtotal = round(items_subtotal, 2)
    delivery_zone, delivery_fee = calculate_delivery_pricing(
        order.delivery_address, order.landmark
    )
    service_fee = SERVICE_FEE_FCFA
    total_amount = round(items_subtotal + delivery_fee + service_fee, 2)

    new_order = models.Order(
        user_id=resolved_user_id,
        items_subtotal=items_subtotal,
        delivery_fee=delivery_fee,
        service_fee=service_fee,
        total_amount=total_amount,
        delivery_zone=delivery_zone,
        delivery_address=order.delivery_address.strip(),
        landmark=order.landmark.strip() if order.landmark else None,
        status="pending_payment",
        payment_status="unpaid",
    )
    db.add(new_order)
    db.flush()

    for product, qty, stock_units_needed, chosen_unit, official_unit_price in verified_lines:
        product.stock -= stock_units_needed
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=qty,
            unit_label=chosen_unit,
            unit_price=official_unit_price,
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    return {
        "success": True,
        "order_id": new_order.id,
        "items_subtotal": items_subtotal,
        "delivery_fee": delivery_fee,
        "service_fee": service_fee,
        "total_amount": total_amount,
        "delivery_zone": delivery_zone,
        "status": new_order.status,
        "payment_status": new_order.payment_status,
        "message": "Commande validée et chiffrée par le serveur.",
    }


@app.patch(
    "/api/orders/{order_id}/status",
    response_model=schemas.OrderOut,
    dependencies=[Depends(require_staff_access)],
)
def update_order_status(
    order_id: int, payload: schemas.OrderStatusUpdate, db: Session = Depends(get_db)
):
    allowed_statuses = {
        "pending_payment",
        "paid",
        "processing",
        "out_for_delivery",
        "delivered",
        "cancelled",
    }
    allowed_payments = {"unpaid", "paid", "refunded"}

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")

    if payload.status:
        if payload.status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Statut de commande invalide.")
        order.status = payload.status

    if payload.payment_status:
        if payload.payment_status not in allowed_payments:
            raise HTTPException(status_code=400, detail="Statut de paiement invalide.")
        order.payment_status = payload.payment_status

    db.commit()
    db.refresh(order)
    return _build_order_out(db, order)


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")