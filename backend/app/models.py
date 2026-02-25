import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Mall(Base):
    __tablename__ = "malls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    address = Column(String)
    region = Column(String)
    website = Column(String)
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    mall_stores = relationship("MallStore", back_populates="mall", cascade="all, delete-orphan")


class Store(Base):
    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    category = Column(String)
    normalized_name = Column(String, nullable=False, unique=True)

    mall_stores = relationship("MallStore", back_populates="store", cascade="all, delete-orphan")


class MallStore(Base):
    __tablename__ = "mall_stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mall_id = Column(UUID(as_uuid=True), ForeignKey("malls.id"), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    floor = Column(String)
    unit_number = Column(String)

    mall = relationship("Mall", back_populates="mall_stores")
    store = relationship("Store", back_populates="mall_stores")

    __table_args__ = (UniqueConstraint("mall_id", "store_id", name="uq_mall_store"),)
