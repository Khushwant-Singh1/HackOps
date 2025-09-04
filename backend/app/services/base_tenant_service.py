"""
Tenant-Scoped Base Service

This base service provides automatic tenant isolation for all service operations.
All other services should inherit from this to ensure proper multi-tenant data isolation.
"""

from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from uuid import UUID
from abc import ABC, abstractmethod

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from sqlalchemy.sql import Select

from app.core.database_utils import TenantManager
from app.models.base import Base


T = TypeVar('T', bound=Base)


class TenantScopedService(Generic[T], ABC):
    """
    Base service class that provides tenant isolation for all database operations.
    
    All service classes should inherit from this to ensure proper multi-tenant data access.
    """
    
    def __init__(self, model_class: Type[T]):
        """
        Initialize the tenant-scoped service.
        
        Args:
            model_class: The SQLAlchemy model class this service manages
        """
        self.model_class = model_class
        self.tenant_manager = TenantManager()
    
    # Core CRUD operations with tenant isolation
    
    async def create(
        self,
        db: Session,
        tenant_id: UUID,
        obj_data: Dict[str, Any],
        created_by_id: Optional[UUID] = None
    ) -> T:
        """
        Create a new object within tenant context.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            obj_data: Data for creating the object
            created_by_id: ID of user creating the object
        
        Returns:
            Created object instance
        
        Raises:
            HTTPException: If creation fails or tenant access denied
        """
        try:
            # Set tenant context
            async with self.tenant_manager.tenant_session(db, tenant_id):
                # Add tenant_id to object data if model supports it
                if hasattr(self.model_class, 'tenant_id'):
                    obj_data['tenant_id'] = tenant_id
                
                # Add created_by if model supports it and provided
                if created_by_id and hasattr(self.model_class, 'created_by_id'):
                    obj_data['created_by_id'] = created_by_id
                
                # Create object
                obj = self.model_class(**obj_data)
                db.add(obj)
                db.flush()
                
                # Run any post-creation hooks
                await self._after_create(db, obj, tenant_id)
                
                db.commit()
                db.refresh(obj)
                
                return obj
                
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {self.model_class.__name__}: {str(e)}"
            )
    
    async def get_by_id(
        self,
        db: Session,
        tenant_id: UUID,
        obj_id: UUID,
        raise_not_found: bool = True
    ) -> Optional[T]:
        """
        Get object by ID within tenant context.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            obj_id: ID of the object to retrieve
            raise_not_found: Whether to raise exception if not found
        
        Returns:
            Object instance or None
        
        Raises:
            HTTPException: If object not found and raise_not_found is True
        """
        async with self.tenant_manager.tenant_session(db, tenant_id):
            query = db.query(self.model_class).filter(self.model_class.id == obj_id)
            
            # Add tenant filter if model supports it
            if hasattr(self.model_class, 'tenant_id'):
                query = query.filter(self.model_class.tenant_id == tenant_id)
            
            # Add soft delete filter if model supports it
            if hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            obj = query.first()
            
            if not obj and raise_not_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model_class.__name__} not found"
                )
            
            return obj
    
    async def list_objects(
        self,
        db: Session,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[T]:
        """
        List objects within tenant context with filtering and pagination.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Additional filters to apply
            order_by: Field to order by
            order_desc: Whether to order in descending order
        
        Returns:
            List of objects matching criteria
        """
        async with self.tenant_manager.tenant_session(db, tenant_id):
            query = db.query(self.model_class)
            
            # Add tenant filter if model supports it
            if hasattr(self.model_class, 'tenant_id'):
                query = query.filter(self.model_class.tenant_id == tenant_id)
            
            # Add soft delete filter if model supports it
            if hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            # Apply additional filters
            if filters:
                query = self._apply_filters(query, filters)
            
            # Apply ordering
            if order_by:
                order_field = getattr(self.model_class, order_by, None)
                if order_field:
                    if order_desc:
                        query = query.order_by(order_field.desc())
                    else:
                        query = query.order_by(order_field)
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            return query.all()
    
    async def update(
        self,
        db: Session,
        tenant_id: UUID,
        obj_id: UUID,
        update_data: Dict[str, Any],
        updated_by_id: Optional[UUID] = None
    ) -> T:
        """
        Update object within tenant context.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            obj_id: ID of the object to update
            update_data: Data to update
            updated_by_id: ID of user updating the object
        
        Returns:
            Updated object instance
        
        Raises:
            HTTPException: If object not found or update fails
        """
        obj = await self.get_by_id(db, tenant_id, obj_id)
        
        try:
            async with self.tenant_manager.tenant_session(db, tenant_id):
                # Update fields
                for field, value in update_data.items():
                    if hasattr(obj, field) and field not in ['id', 'created_at', 'tenant_id']:
                        setattr(obj, field, value)
                
                # Add updated_by if model supports it and provided
                if updated_by_id and hasattr(obj, 'updated_by_id'):
                    obj.updated_by_id = updated_by_id
                
                # Update timestamp if model supports it
                if hasattr(obj, 'updated_at'):
                    from datetime import datetime
                    obj.updated_at = datetime.utcnow()
                
                # Run any pre-update hooks
                await self._before_update(db, obj, update_data, tenant_id)
                
                db.commit()
                db.refresh(obj)
                
                # Run any post-update hooks
                await self._after_update(db, obj, update_data, tenant_id)
                
                return obj
                
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {self.model_class.__name__}: {str(e)}"
            )
    
    async def delete(
        self,
        db: Session,
        tenant_id: UUID,
        obj_id: UUID,
        hard_delete: bool = False,
        deleted_by_id: Optional[UUID] = None
    ) -> bool:
        """
        Delete object within tenant context.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            obj_id: ID of the object to delete
            hard_delete: Whether to permanently delete or soft delete
            deleted_by_id: ID of user deleting the object
        
        Returns:
            True if deletion successful
        
        Raises:
            HTTPException: If object not found or deletion fails
        """
        obj = await self.get_by_id(db, tenant_id, obj_id)
        
        try:
            async with self.tenant_manager.tenant_session(db, tenant_id):
                if hard_delete or not hasattr(obj, 'is_deleted'):
                    # Permanent deletion
                    await self._before_delete(db, obj, tenant_id)
                    db.delete(obj)
                else:
                    # Soft deletion
                    obj.is_deleted = True
                    if hasattr(obj, 'deleted_at'):
                        from datetime import datetime
                        obj.deleted_at = datetime.utcnow()
                    if deleted_by_id and hasattr(obj, 'deleted_by_id'):
                        obj.deleted_by_id = deleted_by_id
                
                db.commit()
                
                # Run any post-delete hooks
                await self._after_delete(db, obj, tenant_id)
                
                return True
                
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {self.model_class.__name__}: {str(e)}"
            )
    
    async def count(
        self,
        db: Session,
        tenant_id: UUID,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count objects within tenant context.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            filters: Additional filters to apply
        
        Returns:
            Count of objects matching criteria
        """
        async with self.tenant_manager.tenant_session(db, tenant_id):
            query = db.query(self.model_class)
            
            # Add tenant filter if model supports it
            if hasattr(self.model_class, 'tenant_id'):
                query = query.filter(self.model_class.tenant_id == tenant_id)
            
            # Add soft delete filter if model supports it
            if hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            # Apply additional filters
            if filters:
                query = self._apply_filters(query, filters)
            
            return query.count()
    
    async def exists(
        self,
        db: Session,
        tenant_id: UUID,
        obj_id: UUID
    ) -> bool:
        """
        Check if object exists within tenant context.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            obj_id: ID of the object to check
        
        Returns:
            True if object exists
        """
        obj = await self.get_by_id(db, tenant_id, obj_id, raise_not_found=False)
        return obj is not None
    
    # Tenant-aware query building
    
    def get_tenant_query(self, db: Session, tenant_id: UUID) -> Query:
        """
        Get a base query with tenant isolation applied.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
        
        Returns:
            Query with tenant filters applied
        """
        query = db.query(self.model_class)
        
        # Add tenant filter if model supports it
        if hasattr(self.model_class, 'tenant_id'):
            query = query.filter(self.model_class.tenant_id == tenant_id)
        
        # Add soft delete filter if model supports it
        if hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query
    
    def _apply_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """
        Apply additional filters to a query.
        
        Args:
            query: Base query
            filters: Dictionary of field->value filters
        
        Returns:
            Query with filters applied
        """
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                field_attr = getattr(self.model_class, field)
                
                if isinstance(value, list):
                    # IN filter
                    query = query.filter(field_attr.in_(value))
                elif isinstance(value, dict):
                    # Range or special filters
                    if 'gte' in value:
                        query = query.filter(field_attr >= value['gte'])
                    if 'lte' in value:
                        query = query.filter(field_attr <= value['lte'])
                    if 'gt' in value:
                        query = query.filter(field_attr > value['gt'])
                    if 'lt' in value:
                        query = query.filter(field_attr < value['lt'])
                    if 'like' in value:
                        query = query.filter(field_attr.ilike(f"%{value['like']}%"))
                else:
                    # Exact match
                    query = query.filter(field_attr == value)
        
        return query
    
    # Hook methods for custom behavior
    
    async def _after_create(self, db: Session, obj: T, tenant_id: UUID) -> None:
        """Hook called after object creation. Override in subclasses."""
        pass
    
    async def _before_update(
        self,
        db: Session,
        obj: T,
        update_data: Dict[str, Any],
        tenant_id: UUID
    ) -> None:
        """Hook called before object update. Override in subclasses."""
        pass
    
    async def _after_update(
        self,
        db: Session,
        obj: T,
        update_data: Dict[str, Any],
        tenant_id: UUID
    ) -> None:
        """Hook called after object update. Override in subclasses."""
        pass
    
    async def _before_delete(self, db: Session, obj: T, tenant_id: UUID) -> None:
        """Hook called before object deletion. Override in subclasses."""
        pass
    
    async def _after_delete(self, db: Session, obj: T, tenant_id: UUID) -> None:
        """Hook called after object deletion. Override in subclasses."""
        pass
    
    # Utility methods
    
    async def validate_tenant_access(
        self,
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        required_permissions: Optional[List[str]] = None
    ) -> bool:
        """
        Validate that a user has access to perform operations in a tenant.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
            user_id: ID of the user
            required_permissions: List of required permissions
        
        Returns:
            True if user has access
        
        Raises:
            HTTPException: If access denied
        """
        from app.services.tenant_service import tenant_service
        
        # Get user's tenant membership
        tenant_users = await tenant_service.get_tenant_users(
            db=db,
            tenant_id=tenant_id,
            active_only=True
        )
        
        user_tenant = next(
            (tu for tu in tenant_users if tu.user_id == user_id),
            None
        )
        
        if not user_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this tenant"
            )
        
        # TODO: Check required permissions against user's role and permissions
        if required_permissions:
            # Implement permission checking logic here
            pass
        
        return True
    
    async def get_tenant_stats(
        self,
        db: Session,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Get statistics for objects of this type within a tenant.
        
        Args:
            db: Database session
            tenant_id: ID of the tenant
        
        Returns:
            Dictionary with statistics
        """
        total_count = await self.count(db, tenant_id)
        
        stats = {
            "total_count": total_count,
            "model_type": self.model_class.__name__
        }
        
        # Add soft delete stats if supported
        if hasattr(self.model_class, 'is_deleted'):
            async with self.tenant_manager.tenant_session(db, tenant_id):
                query = db.query(self.model_class)
                if hasattr(self.model_class, 'tenant_id'):
                    query = query.filter(self.model_class.tenant_id == tenant_id)
                
                deleted_count = query.filter(self.model_class.is_deleted == True).count()
                stats["deleted_count"] = deleted_count
                stats["active_count"] = total_count
        
        return stats


class TenantScopedRepository(TenantScopedService[T]):
    """
    Alias for TenantScopedService to use as repository pattern.
    Provides the same functionality with repository naming convention.
    """
    pass
