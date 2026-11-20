from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "om_users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default="client")  # 'client', 'driver', 'admin'
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "om_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=True)
    icon_url = Column(Text, nullable=True)


class Product(Base):
    __tablename__ = "om_products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer, ForeignKey("om_categories.id", ondelete="SET NULL"), nullable=True
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    unit_label = Column(String(30), default="unité", nullable=False)
    unit_step = Column(Float, default=1.0, nullable=False)
    image_url = Column(Text, nullable=True)
    is_sponsored = Column(Boolean, default=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "om_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("om_users.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String(30), default="pending_payment")
    items_subtotal = Column(Float, default=0.0, nullable=False)
    delivery_fee = Column(Float, default=1000.0, nullable=False)
    service_fee = Column(Float, default=100.0, nullable=False)
    total_amount = Column(Float, nullable=False)
    delivery_zone = Column(String(50), default="standard", nullable=False)
    delivery_address = Column(Text, nullable=False)
    landmark = Column(Text, nullable=True)
    payment_status = Column(String(20), default="unpaid")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OrderItem(Base):
    __tablename__ = "om_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer, ForeignKey("om_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(
        Integer, ForeignKey("om_products.id", ondelete="SET NULL"), nullable=True
    )
    quantity = Column(Float, nullable=False)
    unit_label = Column(String(30), default="unité", nullable=False)
    unit_price = Column(Float, nullable=False)


class Driver(Base):
    __tablename__ = "om_drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("om_users.id", ondelete="CASCADE"), nullable=False
    )
    zone = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)


class AdsBanner(Base):
    __tablename__ = "om_ads_banners"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=True)
    image_url = Column(Text, nullable=False)
    target_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)