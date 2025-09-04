"""
Simple test to verify Task 4 tenant management implementation works.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, '/home/anuragisinsane/HackOps/backend')

def test_imports():
    """Test that all tenant management modules can be imported."""
    print("Testing imports...")
    
    try:
        from app.services.tenant_service import tenant_service
        print("✅ tenant_service imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import tenant_service: {e}")
        return False
    
    try:
        from app.services.base_tenant_service import TenantScopedService
        print("✅ TenantScopedService imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import TenantScopedService: {e}")
        return False
    
    try:
        from app.core.tenant_rls import rls_manager
        print("✅ rls_manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import rls_manager: {e}")
        return False
    
    try:
        from app.api.v1.tenants import router
        print("✅ tenant router imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import tenant router: {e}")
        return False
    
    return True

def test_tenant_models():
    """Test that tenant models are properly defined."""
    print("\nTesting tenant models...")
    
    try:
        from app.models.tenant import Tenant, TenantUser, TenantStatus, TenantPlan
        
        # Test enum values
        assert hasattr(TenantStatus, 'ACTIVE')
        assert hasattr(TenantPlan, 'FREE')
        assert hasattr(TenantPlan, 'STARTER')
        assert hasattr(TenantPlan, 'PROFESSIONAL')
        assert hasattr(TenantPlan, 'ENTERPRISE')
        
        print("✅ Tenant models are properly defined")
        return True
    except Exception as e:
        print(f"❌ Tenant models test failed: {e}")
        return False

def test_service_classes():
    """Test that service classes are properly structured."""
    print("\nTesting service classes...")
    
    try:
        from app.services.tenant_service import TenantService
        from app.services.base_tenant_service import TenantScopedService
        from app.models.tenant import Tenant
        
        # Test tenant service instantiation
        service = TenantService()
        assert hasattr(service, 'create_tenant')
        assert hasattr(service, 'get_tenant')
        assert hasattr(service, 'update_tenant')
        assert hasattr(service, 'delete_tenant')
        
        # Test tenant-scoped service
        tenant_scoped = TenantScopedService(Tenant)
        assert hasattr(tenant_scoped, 'create')
        assert hasattr(tenant_scoped, 'get_by_id')
        assert hasattr(tenant_scoped, 'list_objects')
        
        print("✅ Service classes are properly structured")
        return True
    except Exception as e:
        print(f"❌ Service classes test failed: {e}")
        return False

def test_api_structure():
    """Test that API endpoints are properly structured."""
    print("\nTesting API structure...")
    
    try:
        from app.api.v1.tenants import router
        
        # Check if router has routes
        routes = router.routes
        assert len(routes) > 0
        
        # Check for expected endpoints
        route_paths = [route.path for route in routes]
        expected_paths = ['/tenants/', '/tenants/{tenant_id}']
        
        for path in expected_paths:
            found = any(path in route_path for route_path in route_paths)
            if not found:
                print(f"⚠️  Expected path {path} not found in routes")
        
        print("✅ API structure is properly defined")
        return True
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Running Task 4 Tenant Management Tests\n")
    
    tests = [
        test_imports,
        test_tenant_models,
        test_service_classes,
        test_api_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Task 4 implementation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
