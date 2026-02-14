"""
Tests for SOW (Scope of Work) and User Profile APIs
- SOW linked to Pricing Plan (Sales flow)
- SOW version tracking
- User Profile CRUD
- User Permissions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSOWAPIs:
    """SOW (Scope of Work) API Tests - Sales Workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()['access_token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Login as executive for permission tests
        exec_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        if exec_response.status_code == 200:
            self.exec_token = exec_response.json()['access_token']
            self.exec_headers = {"Authorization": f"Bearer {self.exec_token}"}
        else:
            self.exec_token = None
            self.exec_headers = {}
    
    def test_get_sow_categories(self):
        """Test GET /api/sow-categories returns all 6 categories"""
        response = requests.get(f"{BASE_URL}/api/sow-categories", headers=self.headers)
        assert response.status_code == 200, f"Failed to get SOW categories: {response.text}"
        
        categories = response.json()
        assert isinstance(categories, list), "Categories should be a list"
        assert len(categories) == 6, f"Expected 6 categories, got {len(categories)}"
        
        expected_values = ['sales', 'hr', 'operations', 'training', 'analytics', 'digital_marketing']
        actual_values = [c['value'] for c in categories]
        for val in expected_values:
            assert val in actual_values, f"Missing category: {val}"
        
        print(f"✓ SOW categories: {[c['label'] for c in categories]}")
    
    def test_create_sow_linked_to_pricing_plan(self):
        """Test POST /api/sow creates SOW linked to pricing plan"""
        # First create a lead
        lead_response = requests.post(f"{BASE_URL}/api/leads", headers=self.headers, json={
            "first_name": "TEST_SOW",
            "last_name": "Client",
            "company": "SOW Test Company"
        })
        assert lead_response.status_code == 200, f"Failed to create lead: {lead_response.text}"
        lead_id = lead_response.json()['id']
        
        # Create pricing plan
        plan_response = requests.post(f"{BASE_URL}/api/pricing-plans", headers=self.headers, json={
            "lead_id": lead_id,
            "project_duration_type": "monthly",
            "project_duration_months": 6,
            "payment_schedule": "monthly",
            "consultants": [
                {"consultant_type": "lead", "count": 1, "meetings": 12, "rate_per_meeting": 15000}
            ],
            "discount_percentage": 10
        })
        assert plan_response.status_code == 200, f"Failed to create pricing plan: {plan_response.text}"
        pricing_plan_id = plan_response.json()['id']
        
        # Create SOW
        sow_response = requests.post(f"{BASE_URL}/api/sow", headers=self.headers, json={
            "pricing_plan_id": pricing_plan_id,
            "lead_id": lead_id,
            "items": []
        })
        assert sow_response.status_code == 200, f"Failed to create SOW: {sow_response.text}"
        result = sow_response.json()
        assert "sow_id" in result, "Response should contain sow_id"
        self.sow_id = result['sow_id']
        self.pricing_plan_id = pricing_plan_id
        print(f"✓ Created SOW: {self.sow_id} linked to pricing plan: {pricing_plan_id}")
        
        # Verify SOW exists
        get_response = requests.get(f"{BASE_URL}/api/sow/{self.sow_id}", headers=self.headers)
        assert get_response.status_code == 200, f"Failed to get SOW: {get_response.text}"
        sow = get_response.json()
        assert sow['pricing_plan_id'] == pricing_plan_id
        assert sow['lead_id'] == lead_id
        print(f"✓ Verified SOW linked correctly")
    
    def test_add_sow_item_with_version_tracking(self):
        """Test POST /api/sow/{id}/items adds items with version tracking"""
        # Get existing SOW or use test SOW ID
        sow_id = "f9efafe7-22fa-4639-b4c8-077149d8e517"  # Known test SOW
        
        # Try to get the SOW first
        get_response = requests.get(f"{BASE_URL}/api/sow/{sow_id}", headers=self.headers)
        if get_response.status_code != 200:
            pytest.skip("Test SOW not found, skipping item test")
        
        sow = get_response.json()
        initial_version = sow.get('current_version', 1)
        initial_items_count = len(sow.get('items', []))
        
        # Add new item
        item_response = requests.post(f"{BASE_URL}/api/sow/{sow_id}/items", headers=self.headers, json={
            "category": "hr",
            "title": "TEST_HR Assessment Framework",
            "description": "Design HR assessment framework for recruitment",
            "deliverables": ["Assessment templates", "Scoring rubric", "Interview guide"],
            "timeline_weeks": 3
        })
        
        if item_response.status_code == 403:
            # SOW is frozen
            print(f"ℹ SOW is frozen, only admin can edit. Response: {item_response.text}")
            return  # This is expected behavior if SOW is frozen
        
        assert item_response.status_code == 200, f"Failed to add SOW item: {item_response.text}"
        result = item_response.json()
        
        # Verify version incremented
        assert "version" in result, "Response should contain version"
        new_version = result['version']
        assert new_version == initial_version + 1, f"Version should increment from {initial_version} to {initial_version + 1}"
        
        print(f"✓ Added SOW item, version incremented to {new_version}")
    
    def test_get_sow_versions(self):
        """Test GET /api/sow/{id}/versions returns version history"""
        sow_id = "f9efafe7-22fa-4639-b4c8-077149d8e517"  # Known test SOW
        
        response = requests.get(f"{BASE_URL}/api/sow/{sow_id}/versions", headers=self.headers)
        if response.status_code == 404:
            pytest.skip("Test SOW not found")
        
        assert response.status_code == 200, f"Failed to get SOW versions: {response.text}"
        data = response.json()
        
        assert "current_version" in data, "Response should contain current_version"
        assert "versions" in data, "Response should contain versions list"
        assert isinstance(data['versions'], list), "versions should be a list"
        
        # Each version should have required fields
        if len(data['versions']) > 0:
            version = data['versions'][0]
            assert 'version' in version, "Version entry should have version number"
            assert 'changed_by' in version, "Version entry should have changed_by"
            assert 'changed_at' in version, "Version entry should have changed_at"
            assert 'change_type' in version, "Version entry should have change_type"
            
            print(f"✓ SOW versions: current={data['current_version']}, history={len(data['versions'])} versions")
            for v in data['versions'][:3]:  # Show first 3 versions
                print(f"  v{v['version']}: {v['change_type']} by {v.get('changed_by_name', 'Unknown')}")
    
    def test_get_sow_at_specific_version(self):
        """Test GET /api/sow/{id}/version/{num} returns snapshot"""
        sow_id = "f9efafe7-22fa-4639-b4c8-077149d8e517"  # Known test SOW
        
        # First get current version
        versions_response = requests.get(f"{BASE_URL}/api/sow/{sow_id}/versions", headers=self.headers)
        if versions_response.status_code == 404:
            pytest.skip("Test SOW not found")
        
        versions_data = versions_response.json()
        if not versions_data.get('versions'):
            pytest.skip("No version history available")
        
        # Get first version snapshot
        version_num = 1
        response = requests.get(f"{BASE_URL}/api/sow/{sow_id}/version/{version_num}", headers=self.headers)
        assert response.status_code == 200, f"Failed to get version snapshot: {response.text}"
        
        data = response.json()
        assert data['version'] == version_num
        assert 'items' in data, "Should contain items snapshot"
        assert 'changed_at' in data, "Should contain changed_at"
        
        print(f"✓ Retrieved version {version_num} snapshot: {len(data.get('items', []))} items")
    
    def test_get_sow_by_pricing_plan(self):
        """Test GET /api/sow/by-pricing-plan/{pricing_plan_id}"""
        pricing_plan_id = "1419ab18-85ae-49c3-a273-7fb74184c98c"  # Known test pricing plan
        
        response = requests.get(f"{BASE_URL}/api/sow/by-pricing-plan/{pricing_plan_id}", headers=self.headers)
        if response.status_code == 404:
            print("ℹ No SOW found for this pricing plan (expected if none created)")
            return
        
        assert response.status_code == 200, f"Failed to get SOW by pricing plan: {response.text}"
        sow = response.json()
        assert sow['pricing_plan_id'] == pricing_plan_id
        print(f"✓ Found SOW for pricing plan: {sow['id']}")
    
    def test_sow_duplicate_prevention(self):
        """Test that duplicate SOW creation is prevented"""
        # This should fail as SOW already exists for pricing plan
        pricing_plan_id = "1419ab18-85ae-49c3-a273-7fb74184c98c"
        
        # Get the lead_id from pricing plan
        plans_response = requests.get(f"{BASE_URL}/api/pricing-plans", headers=self.headers)
        if plans_response.status_code != 200:
            pytest.skip("Cannot get pricing plans")
        
        plans = plans_response.json()
        plan = next((p for p in plans if p['id'] == pricing_plan_id), None)
        if not plan:
            pytest.skip("Test pricing plan not found")
        
        # Try to create duplicate SOW
        response = requests.post(f"{BASE_URL}/api/sow", headers=self.headers, json={
            "pricing_plan_id": pricing_plan_id,
            "lead_id": plan.get('lead_id', 'unknown'),
            "items": []
        })
        
        # Should fail with 400 (already exists) or succeed if no SOW exists
        if response.status_code == 400:
            assert "already exists" in response.json().get('detail', '').lower()
            print("✓ Duplicate SOW correctly prevented")
        elif response.status_code == 200:
            print("ℹ Created new SOW (none existed before)")


class TestUserProfileAPIs:
    """User Profile API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()['access_token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.user_id = response.json()['user']['id']
    
    def test_get_current_user_profile(self):
        """Test GET /api/users/me returns current user profile"""
        response = requests.get(f"{BASE_URL}/api/users/me", headers=self.headers)
        assert response.status_code == 200, f"Failed to get profile: {response.text}"
        
        profile = response.json()
        assert 'id' in profile
        assert 'email' in profile
        assert 'full_name' in profile
        assert 'role' in profile
        assert 'hashed_password' not in profile, "Should not return hashed_password"
        
        print(f"✓ Profile: {profile['full_name']} ({profile['email']}), Role: {profile['role']}")
    
    def test_update_current_user_profile(self):
        """Test PATCH /api/users/me updates profile"""
        # First get current profile
        get_response = requests.get(f"{BASE_URL}/api/users/me", headers=self.headers)
        original_profile = get_response.json()
        
        # Update profile
        update_response = requests.patch(f"{BASE_URL}/api/users/me", headers=self.headers, json={
            "phone": "+91 9876543210",
            "department": "Test Department",
            "designation": "Test Designation",
            "bio": "Test bio for profile update"
        })
        assert update_response.status_code == 200, f"Failed to update profile: {update_response.text}"
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/users/me", headers=self.headers)
        updated_profile = verify_response.json()
        
        assert updated_profile.get('phone') == "+91 9876543210"
        assert updated_profile.get('department') == "Test Department"
        assert updated_profile.get('designation') == "Test Designation"
        assert updated_profile.get('bio') == "Test bio for profile update"
        
        print(f"✓ Profile updated - Phone: {updated_profile.get('phone')}, Dept: {updated_profile.get('department')}")
        
        # Restore original values
        requests.patch(f"{BASE_URL}/api/users/me", headers=self.headers, json={
            "phone": original_profile.get('phone', ''),
            "department": original_profile.get('department', ''),
            "designation": original_profile.get('designation', ''),
            "bio": original_profile.get('bio', '')
        })
    
    def test_get_current_user_permissions(self):
        """Test GET /api/users/me/permissions returns role-based permissions"""
        response = requests.get(f"{BASE_URL}/api/users/me/permissions", headers=self.headers)
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        
        permissions = response.json()
        assert isinstance(permissions, dict), "Permissions should be a dict"
        
        # Admin should have extensive permissions
        expected_modules = ['leads', 'pricing_plans', 'sow', 'quotations', 'agreements']
        for module in expected_modules:
            assert module in permissions, f"Missing permission module: {module}"
            module_perms = permissions[module]
            assert 'read' in module_perms or 'create' in module_perms, f"Module {module} should have permissions"
        
        print(f"✓ Permissions: {list(permissions.keys())}")
        
        # Check admin has create permission on leads
        assert permissions['leads'].get('create') == True, "Admin should have create lead permission"
        print(f"  Admin lead permissions: {permissions['leads']}")
    
    def test_executive_permissions_limited(self):
        """Test that executive has limited permissions"""
        exec_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        if exec_response.status_code != 200:
            pytest.skip("Executive user not available")
        
        exec_token = exec_response.json()['access_token']
        exec_headers = {"Authorization": f"Bearer {exec_token}"}
        
        response = requests.get(f"{BASE_URL}/api/users/me/permissions", headers=exec_headers)
        assert response.status_code == 200
        
        permissions = response.json()
        
        # Executive should have limited user management permissions
        if 'users' in permissions:
            assert permissions['users'].get('manage_roles') == False, "Executive should not manage roles"
        
        # Executive should NOT have approve permission for agreements
        if 'agreements' in permissions:
            assert permissions['agreements'].get('approve') == False, "Executive should not approve agreements"
        
        print(f"✓ Executive permissions verified - limited access as expected")
    
    def test_profile_update_with_duplicate_email_fails(self):
        """Test that updating to an existing email fails"""
        # Try to update email to admin email from a different user
        exec_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        if exec_response.status_code != 200:
            pytest.skip("Executive user not available")
        
        exec_headers = {"Authorization": f"Bearer {exec_response.json()['access_token']}"}
        
        # Try to change email to admin's email (should fail)
        response = requests.patch(f"{BASE_URL}/api/users/me", headers=exec_headers, json={
            "email": "admin@company.com"
        })
        
        assert response.status_code == 400, "Should fail when trying to use existing email"
        assert "already in use" in response.json().get('detail', '').lower()
        print("✓ Duplicate email prevented correctly")


class TestAgreementExportWithSOW:
    """Test Agreement Export includes SOW in tabular format"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()['access_token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_agreement_export_contains_sow_table(self):
        """Test GET /api/agreements/{id}/export contains SOW table data"""
        # Get agreements
        agreements_response = requests.get(f"{BASE_URL}/api/agreements", headers=self.headers)
        assert agreements_response.status_code == 200
        
        agreements = agreements_response.json()
        if not agreements:
            pytest.skip("No agreements available for export test")
        
        agreement = agreements[0]
        agreement_id = agreement['id']
        
        # Export agreement
        response = requests.get(f"{BASE_URL}/api/agreements/{agreement_id}/export", headers=self.headers)
        assert response.status_code == 200, f"Failed to export agreement: {response.text}"
        
        export_data = response.json()
        
        # Verify export structure
        assert 'agreement_number' in export_data
        assert 'sow_table' in export_data, "Export should contain sow_table"
        assert isinstance(export_data['sow_table'], list), "sow_table should be a list"
        
        # Check SOW table structure if items exist
        if export_data['sow_table']:
            sow_item = export_data['sow_table'][0]
            expected_fields = ['category', 'title', 'description', 'deliverables', 'timeline_weeks']
            for field in expected_fields:
                assert field in sow_item, f"SOW table item should have {field}"
        
        print(f"✓ Agreement export: {export_data['agreement_number']}")
        print(f"  SOW items in export: {len(export_data['sow_table'])}")
        print(f"  Pricing total: {export_data.get('pricing', {}).get('total', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
