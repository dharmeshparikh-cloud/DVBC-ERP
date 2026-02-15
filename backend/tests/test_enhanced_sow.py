"""
Test suite for Enhanced SOW Workflow - Role-based SOW management
Features tested:
1. SOW Master Categories API (8 default categories)
2. SOW Master Scopes API (grouped by category)
3. Sales scope selection and SOW creation
4. Consulting scope view and updates
5. Enhanced SOW endpoints
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data constants
TEST_ADMIN_EMAIL = "admin@company.com"
TEST_ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_ADMIN_EMAIL,
        "password": TEST_ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed - status {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestSOWMasterCategories:
    """Test SOW Master Categories API"""
    
    def test_get_categories_returns_8_default_categories(self, api_client):
        """SOW Master should return 8 default categories"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/categories")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        categories = response.json()
        assert isinstance(categories, list), "Response should be a list"
        assert len(categories) == 8, f"Expected 8 categories, got {len(categories)}"
        
        # Verify category codes
        expected_codes = {"sales", "hr", "operations", "training", "analytics", "digital_marketing", "finance", "strategy"}
        actual_codes = {cat.get("code") for cat in categories}
        assert expected_codes == actual_codes, f"Category codes mismatch: expected {expected_codes}, got {actual_codes}"
    
    def test_category_has_required_fields(self, api_client):
        """Each category should have required fields"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/categories")
        assert response.status_code == 200
        
        categories = response.json()
        required_fields = ["id", "name", "code", "color", "is_active"]
        
        for cat in categories:
            for field in required_fields:
                assert field in cat, f"Missing field '{field}' in category {cat.get('name', 'unknown')}"
            assert cat["is_active"] == True, f"Category {cat['name']} should be active"
    
    def test_categories_sorted_by_order(self, api_client):
        """Categories should be sorted by order field"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/categories")
        assert response.status_code == 200
        
        categories = response.json()
        orders = [cat.get("order", 0) for cat in categories]
        assert orders == sorted(orders), f"Categories not sorted by order: {orders}"


class TestSOWMasterScopes:
    """Test SOW Master Scopes API"""
    
    def test_get_scopes_returns_scopes(self, api_client):
        """SOW Master should return scopes"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/scopes")
        
        assert response.status_code == 200
        
        scopes = response.json()
        assert isinstance(scopes, list)
        assert len(scopes) >= 41, f"Expected at least 41 scopes, got {len(scopes)}"
    
    def test_get_scopes_grouped_returns_grouped_structure(self, api_client):
        """Grouped scopes API should return scopes organized by category"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/scopes/grouped")
        
        assert response.status_code == 200
        
        grouped = response.json()
        assert isinstance(grouped, list)
        assert len(grouped) == 8, f"Expected 8 category groups, got {len(grouped)}"
        
        # Verify structure
        for group in grouped:
            assert "category" in group, "Group should have category"
            assert "scopes" in group, "Group should have scopes"
            
            cat = group["category"]
            assert "id" in cat and "name" in cat and "code" in cat, "Category missing fields"
            
            scopes = group["scopes"]
            assert isinstance(scopes, list), "Scopes should be a list"
    
    def test_scopes_have_category_reference(self, api_client):
        """Each scope should have category_id and category_code"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/scopes")
        assert response.status_code == 200
        
        scopes = response.json()
        for scope in scopes[:10]:  # Check first 10
            assert "category_id" in scope, f"Scope {scope.get('name')} missing category_id"
            assert "category_code" in scope, f"Scope {scope.get('name')} missing category_code"
    
    def test_filter_scopes_by_category(self, api_client):
        """Should be able to filter scopes by category_code"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/scopes?category_code=sales")
        
        assert response.status_code == 200
        
        scopes = response.json()
        assert len(scopes) >= 6, f"Expected at least 6 sales scopes, got {len(scopes)}"
        
        for scope in scopes:
            assert scope.get("category_code") == "sales", f"Scope {scope.get('name')} has wrong category_code"


class TestEnhancedSOWCreation:
    """Test Enhanced SOW creation endpoint"""
    
    @pytest.fixture(scope="class")
    def test_pricing_plan(self, authenticated_client):
        """Get or create a pricing plan for testing"""
        # First get existing pricing plans
        response = authenticated_client.get(f"{BASE_URL}/api/pricing-plans")
        if response.status_code == 200:
            plans = response.json()
            if plans:
                # Return first plan without enhanced SOW
                for plan in plans:
                    if not plan.get("enhanced_sow_id"):
                        return plan
        return None
    
    def test_get_enhanced_sow_by_nonexistent_pricing_plan(self, authenticated_client):
        """Should return 404 for non-existent pricing plan"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{fake_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_enhanced_sow_sales_selection_requires_pricing_plan(self, authenticated_client):
        """Sales selection should fail for non-existent pricing plan"""
        fake_id = str(uuid.uuid4())
        
        # Get some scope template IDs
        scopes_response = authenticated_client.get(f"{BASE_URL}/api/sow-masters/scopes")
        scope_ids = [s["id"] for s in scopes_response.json()[:3]]
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/enhanced-sow/{fake_id}/sales-selection",
            json={"scope_template_ids": scope_ids, "custom_scopes": []},
            params={"current_user_id": "test-user", "current_user_name": "Test User", "current_user_role": "admin"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestEnhancedSOWEndpoints:
    """Test Enhanced SOW various endpoints"""
    
    def test_get_enhanced_sow_by_id_404(self, authenticated_client):
        """Should return 404 for non-existent SOW ID"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow/{fake_id}")
        
        assert response.status_code == 404
    
    def test_update_scope_404_for_nonexistent_sow(self, authenticated_client):
        """Should return 404 when updating scope on non-existent SOW"""
        fake_sow_id = str(uuid.uuid4())
        fake_scope_id = str(uuid.uuid4())
        
        response = authenticated_client.patch(
            f"{BASE_URL}/api/enhanced-sow/{fake_sow_id}/scopes/{fake_scope_id}",
            json={"status": "in_progress", "progress_percentage": 50}
        )
        
        assert response.status_code == 404
    
    def test_add_scope_to_nonexistent_sow(self, authenticated_client):
        """Should return 404 when adding scope to non-existent SOW"""
        fake_sow_id = str(uuid.uuid4())
        
        # Get a category ID
        cats_response = authenticated_client.get(f"{BASE_URL}/api/sow-masters/categories")
        category_id = cats_response.json()[0]["id"]
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/enhanced-sow/{fake_sow_id}/scopes",
            json={
                "name": "Test Scope",
                "category_id": category_id,
                "description": "Test description"
            },
            params={"current_user_id": "test-user", "current_user_name": "Test User", "current_user_role": "admin"}
        )
        
        assert response.status_code == 404
    
    def test_variance_report_404_for_nonexistent_sow(self, authenticated_client):
        """Should return 404 for variance report on non-existent SOW"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow/{fake_id}/variance-report")
        
        assert response.status_code == 404
    
    def test_change_log_404_for_nonexistent_sow(self, authenticated_client):
        """Should return 404 for change log on non-existent SOW"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow/{fake_id}/change-log")
        
        assert response.status_code == 404


class TestSOWMastersCRUD:
    """Test SOW Masters CRUD operations"""
    
    def test_create_category(self, authenticated_client):
        """Admin can create a new category"""
        test_code = f"test_category_{uuid.uuid4().hex[:8]}"
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/sow-masters/categories",
            json={
                "name": "Test Category",
                "code": test_code,
                "description": "Test category for testing",
                "color": "#FF5733",
                "order": 99
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["name"] == "Test Category"
        assert data["code"] == test_code
        assert data["color"] == "#FF5733"
        
        return data["id"]
    
    def test_create_category_duplicate_code_fails(self, authenticated_client):
        """Creating category with duplicate code should fail"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/sow-masters/categories",
            json={
                "name": "Duplicate Sales",
                "code": "sales",  # Already exists
                "description": "Duplicate test"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    def test_create_scope_template(self, authenticated_client):
        """Can create a scope template under existing category"""
        # Get first category
        cats_response = authenticated_client.get(f"{BASE_URL}/api/sow-masters/categories")
        category = cats_response.json()[0]
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/sow-masters/scopes",
            json={
                "category_id": category["id"],
                "name": f"TEST_Scope_{uuid.uuid4().hex[:8]}",
                "description": "Test scope for testing",
                "default_timeline_weeks": 4
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["category_id"] == category["id"]
        assert data["category_code"] == category["code"]
        assert "TEST_Scope_" in data["name"]
    
    def test_create_scope_invalid_category_fails(self, authenticated_client):
        """Creating scope with invalid category should fail"""
        fake_category_id = str(uuid.uuid4())
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/sow-masters/scopes",
            json={
                "category_id": fake_category_id,
                "name": "Invalid Scope",
                "description": "Should fail"
            }
        )
        
        assert response.status_code == 404


class TestRoadmapApprovalEndpoints:
    """Test roadmap approval workflow endpoints"""
    
    def test_submit_roadmap_404_for_nonexistent_sow(self, authenticated_client):
        """Should return 404 when submitting roadmap for non-existent SOW"""
        fake_sow_id = str(uuid.uuid4())
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/enhanced-sow/{fake_sow_id}/roadmap/submit",
            json={
                "approval_cycle": "monthly",
                "period_label": "January 2026"
            },
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        assert response.status_code == 404
    
    def test_upload_consent_document_404(self, authenticated_client):
        """Should return 404 when uploading consent to non-existent SOW"""
        fake_sow_id = str(uuid.uuid4())
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/enhanced-sow/{fake_sow_id}/consent-documents",
            json={
                "filename": "consent.pdf",
                "file_data": "dGVzdCBkYXRh",  # base64 encoded "test data"
                "consent_type": "document",
                "consent_for": "roadmap_approval"
            }
        )
        
        assert response.status_code == 404


class TestHandoverEndpoints:
    """Test sales handover endpoints"""
    
    def test_complete_handover_404_for_nonexistent_sow(self, authenticated_client):
        """Should return 404 for handover on non-existent SOW"""
        fake_sow_id = str(uuid.uuid4())
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/enhanced-sow/{fake_sow_id}/complete-handover"
        )
        
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
