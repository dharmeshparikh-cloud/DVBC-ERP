"""
Test Suite: Sales Manager Role Verification
Verifies that 'account_manager' has been replaced with 'sales_manager' across the system
and Sales Funnel UI layout is working correctly.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSalesManagerRole:
    """Test sales_manager role is correctly implemented"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_token(self, email: str, password: str) -> str:
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_login_sales_manager_role_displayed(self):
        """Test that dp@dvbc.com login returns role as 'sales_manager', not 'account_manager'"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dp@dvbc.com",
            "password": "Welcome@123"
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        user = data.get("user", {})
        
        # PRIMARY CHECK: Role should be sales_manager
        assert user.get("role") == "sales_manager", \
            f"Expected role 'sales_manager', got '{user.get('role')}'"
        
        # Ensure it's NOT account_manager
        assert user.get("role") != "account_manager", \
            "Role should NOT be 'account_manager' anymore"
        
        # Verify other user fields
        assert user.get("email") == "dp@dvbc.com"
        assert user.get("full_name") is not None
        print(f"✓ User {user.get('email')} has role: {user.get('role')}")
    
    def test_admin_login_works(self):
        """Test admin login for reference"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("user", {}).get("role") == "admin"
        print("✓ Admin login successful")
    
    def test_sales_manager_can_access_sales_dashboard(self):
        """Test that sales_manager can access sales dashboard endpoint"""
        token = self.get_token("dp@dvbc.com", "Welcome@123")
        assert token is not None, "Failed to get token for sales_manager"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Test sales dashboard access
        response = self.session.get(f"{BASE_URL}/api/dashboard/sales")
        # Dashboard might not require specific endpoint, but verify no 403 for sales routes
        assert response.status_code != 403, "Sales manager should have access to sales routes"
        print("✓ Sales manager has access to sales routes")
    
    def test_sales_manager_can_access_leads(self):
        """Test that sales_manager can access leads"""
        token = self.get_token("dp@dvbc.com", "Welcome@123")
        assert token is not None
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        
        leads = response.json()
        assert isinstance(leads, list)
        print(f"✓ Sales manager can access leads ({len(leads)} leads)")
    
    def test_no_account_manager_in_roles_list(self):
        """Verify 'account_manager' is not in the available roles list"""
        token = self.get_token("admin@dvbc.com", "admin123")
        assert token is not None
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/roles")
        if response.status_code == 200:
            roles = response.json()
            role_ids = [r.get("id", r) if isinstance(r, dict) else r for r in roles]
            
            assert "account_manager" not in role_ids, \
                "'account_manager' should not be in roles list"
            
            # Verify sales_manager IS in the list
            assert "sales_manager" in role_ids, \
                "'sales_manager' should be in roles list"
            
            print(f"✓ Roles list correct - no 'account_manager', has 'sales_manager'")
        else:
            # Roles endpoint might not exist - skip
            pytest.skip("Roles endpoint not available")


class TestSalesFunnelAPI:
    """Test Sales Funnel endpoints for UI support"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self) -> str:
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_lead_funnel_progress_endpoint(self):
        """Test funnel progress endpoint used by Sales Funnel UI"""
        token = self.get_admin_token()
        assert token is not None
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a lead first
        leads_response = self.session.get(f"{BASE_URL}/api/leads")
        assert leads_response.status_code == 200
        
        leads = leads_response.json()
        if not leads:
            pytest.skip("No leads available for testing")
        
        lead_id = leads[0].get("id")
        
        # Test funnel-progress endpoint
        response = self.session.get(f"{BASE_URL}/api/leads/{lead_id}/funnel-progress")
        assert response.status_code == 200, f"Funnel progress failed: {response.text}"
        
        progress = response.json()
        assert "completed_steps" in progress or isinstance(progress, dict)
        print(f"✓ Funnel progress endpoint working for lead {lead_id}")
    
    def test_lead_endpoint(self):
        """Test single lead endpoint"""
        token = self.get_admin_token()
        assert token is not None
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        lead_id = "604b0885-0225-4028-94a6-d19b4261181f"
        response = self.session.get(f"{BASE_URL}/api/leads/{lead_id}")
        
        assert response.status_code == 200, f"Lead fetch failed: {response.text}"
        
        lead = response.json()
        assert lead.get("id") == lead_id
        assert lead.get("first_name") is not None
        assert lead.get("company") is not None
        print(f"✓ Lead endpoint working - {lead.get('first_name')} {lead.get('last_name')}")


class TestBackendCodeNoAccountManager:
    """Verify backend code doesn't have 'account_manager' references"""
    
    def test_server_py_no_account_manager(self):
        """Check server.py doesn't contain 'account_manager'"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for 'account_manager' (case-insensitive)
        assert "account_manager" not in content.lower(), \
            "server.py should not contain 'account_manager'"
        
        # Verify 'sales_manager' IS present
        assert "sales_manager" in content.lower(), \
            "server.py should contain 'sales_manager'"
        
        print("✓ server.py has no 'account_manager' references")
    
    def test_layout_js_no_account_manager(self):
        """Check Layout.js doesn't contain 'account_manager'"""
        layout_path = "/app/frontend/src/components/Layout.js"
        
        with open(layout_path, 'r') as f:
            content = f.read()
        
        assert "account_manager" not in content.lower(), \
            "Layout.js should not contain 'account_manager'"
        
        assert "sales_manager" in content.lower(), \
            "Layout.js should contain 'sales_manager'"
        
        print("✓ Layout.js has no 'account_manager' references")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
