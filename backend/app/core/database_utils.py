"""
Database utility functions for HackOps platform.

This module provides utilities for:
- Database connection management
- Query optimization
- Bulk operations
- Performance monitoring
- Connection pooling
- Transaction management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, TypeVar
from datetime import datetime

from sqlalchemy import text, func, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy.sql import Select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.models.base import Base

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)

class DatabaseManager:
    """Manages database connections, pooling, and operations."""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._is_initialized:
            return
        
        # Create async engine
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1 hour
            connect_args={
                "server_settings": {
                    "jit": "off",  # Disable JIT for better performance with many short queries
                }
            }
        )
        
        # Create session factory
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self._is_initialized = True
        logger.info("Database manager initialized")
    
    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self._is_initialized = False
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup."""
        if not self._is_initialized:
            await self.initialize()
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity."""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                
                # Check connection pool status
                pool = self.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalidated": pool.invalidated()
                }
                
                return {
                    "status": "healthy",
                    "pool": pool_status,
                    "timestamp": datetime.utcnow()
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session for FastAPI endpoints."""
    async with db_manager.get_session() as session:
        yield session

class QueryBuilder:
    """Helper class for building optimized queries."""
    
    @staticmethod
    def paginate(query: Select, page: int = 1, size: int = 20) -> Select:
        """Add pagination to a query."""
        offset = (page - 1) * size
        return query.offset(offset).limit(size)
    
    @staticmethod
    def apply_filters(query: Select, model: Type[T], filters: Dict[str, Any]) -> Select:
        """Apply filters to a query dynamically."""
        for field, value in filters.items():
            if hasattr(model, field) and value is not None:
                column = getattr(model, field)
                if isinstance(value, list):
                    query = query.where(column.in_(value))
                elif isinstance(value, dict):
                    # Handle range queries like {"gte": 10, "lte": 20}
                    if "gte" in value:
                        query = query.where(column >= value["gte"])
                    if "lte" in value:
                        query = query.where(column <= value["lte"])
                    if "gt" in value:
                        query = query.where(column > value["gt"])
                    if "lt" in value:
                        query = query.where(column < value["lt"])
                else:
                    query = query.where(column == value)
        
        return query
    
    @staticmethod
    def add_search(query: Select, model: Type[T], search_term: str, 
                   search_fields: List[str]) -> Select:
        """Add full-text search to a query."""
        if not search_term or not search_fields:
            return query
        
        # Build search conditions
        search_conditions = []
        for field in search_fields:
            if hasattr(model, field):
                column = getattr(model, field)
                search_conditions.append(
                    column.ilike(f"%{search_term}%")
                )
        
        if search_conditions:
            # Use OR condition for multiple fields
            from sqlalchemy import or_
            query = query.where(or_(*search_conditions))
        
        return query

class BulkOperations:
    """Utilities for bulk database operations."""
    
    @staticmethod
    async def bulk_insert(session: AsyncSession, model: Type[T], 
                         data: List[Dict[str, Any]]) -> None:
        """Perform bulk insert operation."""
        if not data:
            return
        
        stmt = insert(model).values(data)
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def bulk_upsert(session: AsyncSession, model: Type[T], 
                         data: List[Dict[str, Any]], 
                         index_elements: List[str]) -> None:
        """Perform bulk upsert (insert or update) operation."""
        if not data:
            return
        
        stmt = insert(model).values(data)
        
        # Create update dict excluding the index elements
        update_dict = {
            column.name: getattr(stmt.excluded, column.name)
            for column in model.__table__.columns
            if column.name not in index_elements and column.name != "id"
        }
        
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_=update_dict
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def bulk_update(session: AsyncSession, model: Type[T],
                         updates: List[Dict[str, Any]], 
                         id_field: str = "id") -> None:
        """Perform bulk update operation."""
        if not updates:
            return
        
        from sqlalchemy import update
        
        for update_data in updates:
            if id_field not in update_data:
                continue
            
            record_id = update_data.pop(id_field)
            stmt = update(model).where(
                getattr(model, id_field) == record_id
            ).values(**update_data)
            
            await session.execute(stmt)
        
        await session.commit()

class PerformanceMonitor:
    """Monitor database query performance."""
    
    def __init__(self):
        self.slow_query_threshold = 1.0  # seconds
        self.query_stats = {}
    
    def log_query(self, query: str, duration: float, params: Optional[Dict] = None):
        """Log query execution statistics."""
        if duration > self.slow_query_threshold:
            logger.warning(
                f"Slow query detected: {duration:.2f}s - {query[:100]}..."
            )
        
        # Update statistics
        if query not in self.query_stats:
            self.query_stats[query] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "max_time": 0.0
            }
        
        stats = self.query_stats[query]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["max_time"] = max(stats["max_time"], duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        return {
            "total_queries": sum(stats["count"] for stats in self.query_stats.values()),
            "slow_queries": sum(
                1 for stats in self.query_stats.values() 
                if stats["max_time"] > self.slow_query_threshold
            ),
            "top_slow_queries": sorted(
                [
                    {
                        "query": query[:100] + "..." if len(query) > 100 else query,
                        "stats": stats
                    }
                    for query, stats in self.query_stats.items()
                ],
                key=lambda x: x["stats"]["max_time"],
                reverse=True
            )[:10]
        }

class TenantManager:
    """
    Enhanced utilities for multi-tenant database operations with RLS support.
    
    Provides context managers and utilities for ensuring all database
    operations are properly scoped to a specific tenant using PostgreSQL
    row-level security.
    """
    
    def __init__(self):
        self._current_tenant_id: Optional[str] = None
    
    async def set_tenant_context(self, session: AsyncSession, tenant_id: str) -> None:
        """
        Set tenant context for row-level security.
        
        Args:
            session: Database session
            tenant_id: ID of the tenant to set as context
        """
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id}
        )
        self._current_tenant_id = tenant_id
    
    async def clear_tenant_context(self, session: AsyncSession) -> None:
        """
        Clear tenant context.
        
        Args:
            session: Database session
        """
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', NULL, true)")
        )
        self._current_tenant_id = None
    
    async def set_system_admin_context(self, session: AsyncSession, is_admin: bool = True) -> None:
        """
        Set system admin context for bypassing tenant isolation.
        
        Args:
            session: Database session
            is_admin: Whether to enable system admin context
        """
        await session.execute(
            text("SELECT set_config('app.is_system_admin', :is_admin, true)"),
            {"is_admin": str(is_admin).lower()}
        )
    
    async def get_current_tenant_id(self, session: AsyncSession) -> Optional[str]:
        """
        Get the current tenant context from the database session.
        
        Args:
            session: Database session
        
        Returns:
            Current tenant ID as string or None if not set
        """
        result = await session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
        
        tenant_id = result.scalar()
        return tenant_id if tenant_id != '' else None
    
    @asynccontextmanager
    async def tenant_session(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a session with tenant context automatically set.
        
        Args:
            tenant_id: ID of the tenant to scope operations to
        
        Yields:
            Database session with tenant context set
        """
        async with db_manager.get_session() as session:
            # Store original tenant context
            original_tenant_id = await self.get_current_tenant_id(session)
            
            try:
                # Set tenant context
                await self.set_tenant_context(session, tenant_id)
                yield session
            finally:
                # Restore original tenant context
                if original_tenant_id:
                    await self.set_tenant_context(session, original_tenant_id)
                else:
                    await self.clear_tenant_context(session)
    
    @asynccontextmanager
    async def system_admin_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a session with system admin context for bypassing tenant isolation.
        
        Yields:
            Database session with system admin context
        """
        async with db_manager.get_session() as session:
            try:
                # Set system admin context
                await self.set_system_admin_context(session, True)
                yield session
            finally:
                # Clear system admin context
                await self.set_system_admin_context(session, False)
    
    async def verify_tenant_isolation(self, tenant_id: str) -> Dict[str, Any]:
        """
        Verify that tenant isolation is working correctly.
        
        Args:
            tenant_id: Tenant ID to test isolation for
        
        Returns:
            Dictionary with isolation test results
        """
        results = {
            "tenant_id": tenant_id,
            "isolation_enabled": True,
            "tests": {}
        }
        
        # Test tenant context
        async with self.tenant_session(tenant_id) as session:
            try:
                # Verify tenant context is set
                current_tenant = await self.get_current_tenant_id(session)
                results["tests"]["tenant_context"] = {
                    "status": "pass" if current_tenant == tenant_id else "fail",
                    "current_tenant": current_tenant,
                    "expected_tenant": tenant_id
                }
                
                # Test isolation functions
                result = await session.execute(
                    text("SELECT get_current_tenant_id()::text")
                )
                db_tenant = result.scalar()
                
                results["tests"]["isolation_function"] = {
                    "status": "pass" if db_tenant == tenant_id else "fail",
                    "db_tenant": db_tenant,
                    "expected_tenant": tenant_id
                }
                
            except Exception as e:
                results["tests"]["error"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results

class CacheManager:
    """Database-level caching utilities."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_cached_query(self, cache_key: str, query_func, *args, **kwargs):
        """Get cached query result or execute and cache."""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if (datetime.utcnow() - timestamp).seconds < self.cache_ttl:
                return cached_data
        
        # Execute query and cache result
        result = await query_func(*args, **kwargs)
        self.cache[cache_key] = (result, datetime.utcnow())
        return result
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            self.cache.clear()
        else:
            keys_to_remove = [
                key for key in self.cache.keys() 
                if pattern in key
            ]
            for key in keys_to_remove:
                del self.cache[key]

# Global instances
query_builder = QueryBuilder()
bulk_ops = BulkOperations()
perf_monitor = PerformanceMonitor()
tenant_manager = TenantManager()
cache_manager = CacheManager()

# Database event handlers
async def startup_database():
    """Initialize database on application startup."""
    await db_manager.initialize()
    logger.info("Database startup completed")

async def shutdown_database():
    """Clean up database connections on shutdown."""
    await db_manager.close()
    logger.info("Database shutdown completed")
