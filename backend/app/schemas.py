from pydantic import BaseModel
from typing import List, Optional

# --- SCHEMAS UTILISATEURS ---
class UserCreate(BaseModel):
    phone: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    phone: str
    full_name: Optional[str] = None
    role: str

    class Config:
        from_attributes = True

# --- SCHEMAS PRODUITS ---
class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    image_url: Optional[str] = None
    is_sponsored: bool = False
    stock: int

    class Config:
        from_attributes = True

# --- SCHEMAS LISTE MAGIQUE & COMMANDES ---
class SmartListRequest(BaseModel):
    raw_text: str

class CartItem(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    user_id: int
    delivery_address: str
    landmark: Optional[str] = None
    items: List[CartItem]