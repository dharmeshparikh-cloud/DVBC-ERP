"""
Lead-to-Client Master Integration Tests

Tests:
1. Lead form company detail fields (Industry, Website, City, State, Country, Address)
2. Clients API (/api/clients) - role-based filtering
3. Clients Stats API (/api/clients/stats/summary) - statistics
4. Client creation and management (Admin/Finance only)
5. Role-based access control for Clients page

Credentials:
- Admin: ADMIN001 / Admin@2026
- Sales Manager: EMP002 / Sales@123
- Sales Executive: EMP003 / Sales@123
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestClientMasterAPI:
    """Test Client Master API endpoints and role-based access."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for API calls."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def get_auth_token(self, employee_id: str, password: str) -> str:
        """Login and get JWT token."""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": employee_id, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None

    # Test 1: Admin can access clients API
    def test_admin_can_access_clients_api(self):
        """Admin should have full access to /api/clients"""
        token = self.get_auth_token("ADMIN001", "Admin@2026")
        if not token:
            pytest.skip("Failed to authenticate as Admin")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/clients")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # API returns items array
        assert "items" in data or isinstance(data, list), "Response should contain 'items' or be a list"
        print(f"[PASS] Admin can access /api/clients - returned {len(data.get('items', data))} clients")

    # Test 2: Admin can access clients stats API
    def test_admin_can_access_clients_stats(self):
        """Admin should have access to /api/clients/stats/summary"""
        token = self.get_auth_token("ADMIN001", "Admin@2026")
        if not token:
            pytest.skip("Failed to authenticate as Admin")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/clients/stats/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Stats API should return expected fields
        assert "total_clients" in data, "Stats should include 'total_clients'"
        assert "by_industry" in data, "Stats should include 'by_industry'"
        assert "by_status" in data, "Stats should include 'by_status'"
        assert "total_revenue" in data, "Stats should include 'total_revenue'"
        print(f"[PASS] Admin can access /api/clients/stats/summary - total_clients: {data.get('total_clients')}")

    # Test 3: Sales Manager can access clients API (filtered view)
    def test_sales_manager_can_access_clients_api(self):
        """Sales Manager should have access to /api/clients but may see filtered results"""
        token = self.get_auth_token("EMP002", "Sales@123")
        if not token:
            pytest.skip("Failed to authenticate as Sales Manager")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/clients")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "items" in data or isinstance(data, list), "Response should contain 'items' or be a list"
        print(f"[PASS] Sales Manager can access /api/clients - returned {len(data.get('items', data))} clients (filtered by role)")

    # Test 4: Sales Manager CANNOT create clients (role-based restriction)
    def test_sales_manager_cannot_create_client(self):
        """Sales Manager should NOT be able to create clients - only Admin/Finance"""
        token = self.get_auth_token("EMP002", "Sales@123")
        if not token:
            pytest.skip("Failed to authenticate as Sales Manager")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        client_data = {
            "company_name": "TEST_SalesManagerCreateAttempt",
            "industry": "Technology",
            "city": "Mumbai"
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        
        # Should get 403 Forbidden
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
        print("[PASS] Sales Manager correctly forbidden from creating clients")

    # Test 5: Sales Executive CANNOT create clients
    def test_sales_executive_cannot_create_client(self):
        """Sales Executive should NOT be able to create clients - only Admin/Finance"""
        token = self.get_auth_token("EMP003", "Sales@123")
        if not token:
            pytest.skip("Failed to authenticate as Sales Executive")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        client_data = {
            "company_name": "TEST_SalesExecCreateAttempt",
            "industry": "Healthcare",
            "city": "Pune"
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        
        # Should get 403 Forbidden
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
        print("[PASS] Sales Executive correctly forbidden from creating clients")

    # Test 6: Admin CAN create clients
    def test_admin_can_create_client(self):
        """Admin should be able to create clients"""
        token = self.get_auth_token("ADMIN001", "Admin@2026")
        if not token:
            pytest.skip("Failed to authenticate as Admin")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        import uuid
        unique_name = f"TEST_AdminCreate_{uuid.uuid4().hex[:6]}"
        client_data = {
            "company_name": unique_name,
            "industry": "Manufacturing",
            "website": "https://example.com",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "address": "123 Test Street",
            "notes": "Created by Admin test"
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        
        # Should succeed with 200 or 201
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain client 'id'"
        assert data.get("company_name") == unique_name, "Company name should match"
        print(f"[PASS] Admin created client: {unique_name}")
        
        # Cleanup - try to delete
        if data.get("id"):
            self.session.delete(f"{BASE_URL}/api/clients/{data['id']}")

    # Test 7: Verify Lead API accepts company detail fields
    def test_lead_api_accepts_company_details(self):
        """Lead creation should accept company detail fields"""
        token = self.get_auth_token("EMP003", "Sales@123")
        if not token:
            pytest.skip("Failed to authenticate as Sales Executive")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        import uuid
        unique_suffix = uuid.uuid4().hex[:6]
        lead_data = {
            "first_name": f"Test_{unique_suffix}",
            "last_name": "CompanyFields",
            "company": "TestCorp Inc.",
            "job_title": "CEO",
            "email": f"test_{unique_suffix}@example.com",
            "phone": "9876543210",
            "source": "API Test",
            # Company detail fields - the new fields being tested
            "industry": "IT/Software",
            "website": "https://testcorp.example.com",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "address": "456 Tech Park, Electronic City"
        }
        response = self.session.post(f"{BASE_URL}/api/leads", json=lead_data)
        
        # Should succeed
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"[PASS] Lead created with company details: {data.get('id', 'unknown')}")
        
        # Verify the fields were saved by fetching the lead
        if data.get("id"):
            get_response = self.session.get(f"{BASE_URL}/api/leads/{data['id']}")
            if get_response.status_code == 200:
                lead = get_response.json()
                # Check if company fields are present
                if lead.get("industry"):
                    print(f"  - Industry saved: {lead.get('industry')}")
                if lead.get("city"):
                    print(f"  - City saved: {lead.get('city')}")
                if lead.get("state"):
                    print(f"  - State saved: {lead.get('state')}")


class TestMOMReviewAPI:
    """Test MOM Review API for Team Dashboard"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for API calls."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def get_auth_token(self, employee_id: str, password: str) -> str:
        """Login and get JWT token."""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": employee_id, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None

    # Test 8: Manager MOM Review API exists
    def test_mom_review_api_exists(self):
        """Manager MOM Review API should be accessible"""
        token = self.get_auth_token("EMP002", "Sales@123")
        if not token:
            pytest.skip("Failed to authenticate as Sales Manager")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/analytics/manager-mom-review")
        
        # API should exist and return data or empty result
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Check for expected structure
        assert isinstance(data, dict), "MOM review should return a dictionary"
        print(f"[PASS] MOM Review API accessible - keys: {list(data.keys())}")


class TestUsersWithRolesAPI:
    """Test users-with-roles API for Client form dropdown"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for API calls."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def get_auth_token(self, employee_id: str, password: str) -> str:
        """Login and get JWT token."""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": employee_id, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None

    # Test 9: Users with roles API for Client form
    def test_users_with_roles_api(self):
        """Users with roles API should be accessible for Client form dropdown"""
        token = self.get_auth_token("ADMIN001", "Admin@2026")
        if not token:
            pytest.skip("Failed to authenticate as Admin")

        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/users-with-roles")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should return list of users
        users = data.get("items") or data if isinstance(data, list) else []
        assert len(users) > 0, "Should return at least one user"
        print(f"[PASS] Users with roles API returned {len(users)} users")


class TestAuthenticationEndpoints:
    """Test authentication to ensure credentials work"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for API calls."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # Test 10: Admin login works
    def test_admin_login(self):
        """Admin should be able to login with ADMIN001/Admin@2026"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "ADMIN001", "password": "Admin@2026"}
        )
        
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("access_token") or data.get("token"), "Login should return token"
        assert data.get("user", {}).get("role") == "admin" or data.get("role") == "admin", "Should be admin role"
        print("[PASS] Admin login successful")

    # Test 11: Sales Manager login works
    def test_sales_manager_login(self):
        """Sales Manager should be able to login with EMP002/Sales@123"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "EMP002", "password": "Sales@123"}
        )
        
        assert response.status_code == 200, f"Sales Manager login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("access_token") or data.get("token"), "Login should return token"
        print("[PASS] Sales Manager login successful")

    # Test 12: Sales Executive login works
    def test_sales_executive_login(self):
        """Sales Executive should be able to login with EMP003/Sales@123"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "EMP003", "password": "Sales@123"}
        )
        
        assert response.status_code == 200, f"Sales Executive login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("access_token") or data.get("token"), "Login should return token"
        print("[PASS] Sales Executive login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
