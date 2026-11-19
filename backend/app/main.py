from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException
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

app = FastAPI(
    title="O'Market API",
    description="Backend officiel et sécurisé de la plateforme O'Market (Cameroun).",
    version="1.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


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


# --- PRODUITS, PRIX & PROMOTIONS ---
@app.get("/api/products", response_model=List[schemas.ProductOut])
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).order_by(models.Product.id.desc()).all()


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

    for key, value in payload.model_dump(exclude_unset=True).items():
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
        if any(tok in text for tok in tokens):
            detected_items.append(
                {
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "quantity": 1,
                    "unit_price": float(prod.price),
                }
            )

    total_estime = sum(item["quantity"] * item["unit_price"] for item in detected_items)

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


# --- COMMANDES & LOGISTIQUE (PRIX VERROUILLÉS CÔTÉ SERVEUR) ---
@app.get(
    "/api/orders",
    response_model=List[schemas.OrderOut],
    dependencies=[Depends(require_staff_access)],
)
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).order_by(models.Order.id.desc()).all()
    results = []
    for ord_obj in orders:
        items = (
            db.query(models.OrderItem)
            .filter(models.OrderItem.order_id == ord_obj.id)
            .all()
        )
        results.append(
            schemas.OrderOut(
                id=ord_obj.id,
                user_id=ord_obj.user_id,
                status=ord_obj.status,
                total_amount=ord_obj.total_amount,
                delivery_address=ord_obj.delivery_address,
                landmark=ord_obj.landmark,
                payment_status=ord_obj.payment_status,
                created_at=ord_obj.created_at,
                items=items,
            )
        )
    return results


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
    for item in order.items:
        requested_qty_by_id[item.product_id] = (
            requested_qty_by_id.get(item.product_id, 0) + item.quantity
        )

    verified_lines = []
    total = 0.0

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
        if product.stock < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant pour '{product.name}' (disponible : {product.stock}).",
            )

        official_unit_price = float(product.price)
        line_total = official_unit_price * qty
        total += line_total
        verified_lines.append((product, qty, official_unit_price))

    new_order = models.Order(
        user_id=resolved_user_id,
        total_amount=total,
        delivery_address=order.delivery_address.strip(),
        landmark=order.landmark.strip() if order.landmark else None,
        status="pending_payment",
        payment_status="unpaid",
    )
    db.add(new_order)
    db.flush()

    for product, qty, official_unit_price in verified_lines:
        product.stock -= qty
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=qty,
            unit_price=official_unit_price,
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)

    return {
        "success": True,
        "order_id": new_order.id,
        "total_amount": total,
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
    items = (
        db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).all()
    )
    return schemas.OrderOut(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_amount=order.total_amount,
        delivery_address=order.delivery_address,
        landmark=order.landmark,
        payment_status=order.payment_status,
        created_at=order.created_at,
        items=items,
    )


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")