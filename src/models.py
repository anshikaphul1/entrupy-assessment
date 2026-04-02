from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True, nullable=False) # Grailed, Fashionphile, 1stdibs
    external_id = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=False)
    brand = Column(String, index=True)
    model = Column(String)
    currency = Column(String, default="USD")
    metadata_json = Column(JSON, nullable=True)

    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan", order_by="desc(PriceHistory.scraped_at)")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("Product", back_populates="price_history")

class APIUser(Base):
    __tablename__ = "api_users"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    request_count = Column(Integer, default=0)
