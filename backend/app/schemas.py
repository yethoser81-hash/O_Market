from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# --- SCHEMAS UTILISATEURS ---
class UserCreate(BaseModel):
    phone: str
    full_name: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: str  # 'client', 'driver', 'admin'


class UserOut(BaseModel):
    id: int
    phone: str
    full_name: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


# --- SCHEMAS CATÉGORIES ---
class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    icon_url: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None
    icon_url: Optional[str] = None

    class Config:
        from_attributes = True


# --- SCHEMAS PRODUITS ---
class ProductCreate(BaseModel):
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    unit_label: str = Field(default="unité", min_length=1, max_length=30)
    unit_step: float = Field(default=1.0, gt=0)
    image_url: Optional[str] = None
    is_sponsored: bool = False
    stock: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    unit_label: Optional[str] = Field(default=None, min_length=1, max_length=30)
    unit_step: Optional[float] = Field(default=None, gt=0)
    image_url: Optional[str] = None
    is_sponsored: Optional[bool] = None
    stock: Optional[int] = Field(default=None, ge=0)


class ProductOut(BaseModel):
    id: int
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    unit_label: str = "unité"
    unit_step: float = 1.0
    image_url: Optional[str] = None
    is_sponsored: bool = False
    stock: int

    class Config:
        from_attributes = True


# --- SCHEMAS BANNÈRES / PROMOS ---
class BannerCreate(BaseModel):
    title: Optional[str] = None
    image_url: str
    target_url: Optional[str] = None
    is_active: bool = True


class BannerOut(BaseModel):
    id: int
    title: Optional[str] = None
    image_url: str
    target_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# --- SCHEMAS LISTE MAGIQUE & COMMANDES ---
class SmartListRequest(BaseModel):
    raw_text: str
    source: Optional[str] = "text"


class CartItem(BaseModel):
    product_id: int
    product_name: Optional[str] = None
    quantity: float = Field(..., gt=0)
    unit_label: Optional[str] = None
    unit_price: Optional[float] = None  # Ignoré par le serveur lors de la commande


class OrderCreate(BaseModel):
    user_id: Optional[int] = None
    delivery_address: str
    landmark: Optional[str] = None
    items: List[CartItem]


class OrderStatusUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None


class OrderItemOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    quantity: float
    unit_label: str = "unité"
    unit_price: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    items_subtotal: float = 0.0
    delivery_fee: float = 1000.0
    service_fee: float = 100.0
    total_amount: float
    delivery_zone: str = "standard"
    delivery_address: str
    landmark: Optional[str] = None
    payment_status: str
    created_at: Optional[datetime] = None
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True