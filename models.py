"""
SQLAlchemy models for the application.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from config import DATABASE_URL

Base = declarative_base()


class Product(Base):
    """
    Product model representing items imported from CSV.
    SKU is case-insensitive unique identifier.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Case-insensitive index on SKU
    __table_args__ = (
        Index('ix_products_sku_lower', 'sku', postgresql_ops={'sku': 'LOWER'}),
    )

    def to_dict(self):
        """Convert product to dictionary."""
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"


class Webhook(Base):
    """
    Webhook model for managing webhook configurations.
    """
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1000), nullable=False)
    event_type = Column(String(100), nullable=False)  # e.g., 'product.created', 'product.updated', 'product.deleted'
    enabled = Column(Boolean, default=True, nullable=False)
    secret = Column(String(255), nullable=True)  # Optional webhook secret for signing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert webhook to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "event_type": self.event_type,
            "enabled": self.enabled,
            "secret": self.secret,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Webhook(id={self.id}, url='{self.url}', event_type='{self.event_type}')>"


# Database engine and session (to be initialized with actual connection later)
engine = None
SessionLocal = None


def init_db():
    """
    Initialize database engine and session factory.
    This will be called once the database connection is configured.
    """
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def get_db():
    """
    Get database session.
    """
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    """
    if engine is None:
        init_db()
    Base.metadata.create_all(bind=engine)

