"""
Base model with common fields and utilities
"""
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4
from sqlalchemy import Column, DateTime, String, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session


@as_declarative()
class Base:
    """Base class for all database models"""
    
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'
    
    # Common fields for all models
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def create(cls, db: Session, **kwargs) -> "Base":
        """Create and save new instance"""
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
    
    def save(self, db: Session) -> "Base":
        """Save current instance"""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
    
    def delete(self, db: Session) -> None:
        """Delete current instance"""
        db.delete(self)
        db.commit()


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    def soft_delete(self, db: Session) -> None:
        """Soft delete the instance"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.save(db)
    
    def restore(self, db: Session) -> None:
        """Restore soft deleted instance"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(db)


class TenantMixin:
    """Mixin for multi-tenant models"""
    
    tenant_id = Column(
        UUID(as_uuid=True), 
        nullable=False, 
        index=True,
        comment="Tenant isolation identifier"
    )
