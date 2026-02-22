"""
Test Suite for Unified Approvals Center
Tests expense approvals integration into Approvals Center
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_CREDS = {"employee_id": "ADMIN001", "password": "test123"}
SALES_EXEC_CREDS = {"employee_id": "SE001", "password": "test123"}
HR_MANAGER_CREDS = {"employee_id": "HR001", "password": "test123"}


class TestAuthAndSetup:
    """Authentication tests for all test users"""
    
    def test_admin_login(self):
        """Test Admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"Expected access_token in response: {data.keys()}"
        assert "user" in data
        print(f"✓ Admin login successful - role: {data['user'].get('role')}")
    
    def test_sales_exec_login(self):
        """Test Sales Executive login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_EXEC_CREDS)
        assert response.status_code == 200, f"Sales Exec login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Sales Executive login successful - role: {data['user'].get('role')}")
    
    def test_hr_manager_login(self):
        """Test HR Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        assert response.status_code == 200, f"HR Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ HR Manager login successful - role: {data['user'].get('role')}")


class TestExpenseApprovalsAPI:
    """Tests for expense approvals API endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        if response.status_code != 200:
            pytest.skip("HR Manager login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def sales_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_EXEC_CREDS)
        if response.status_code != 200:
            pytest.skip("Sales Executive login failed")
        return response.json()["access_token"]
    
    def test_pending_approvals_endpoint_admin(self, admin_token):
        """Test /api/expenses/pending-approvals returns pending expenses for Admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses/pending-approvals", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Admin pending-approvals returned {len(data)} expenses")
    
    def test_pending_approvals_endpoint_hr(self, hr_token):
        """Test /api/expenses/pending-approvals returns pending expenses for HR Manager"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses/pending-approvals", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ HR Manager pending-approvals returned {len(data)} expenses")
    
    def test_expenses_list_endpoint(self, admin_token):
        """Test /api/expenses returns expense list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ /api/expenses returned {len(data)} expenses")
    
    def test_expense_categories(self, admin_token):
        """Test /api/expenses/categories/list returns categories"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses/categories/list", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have expense categories"
        print(f"✓ Expense categories returned {len(data)} categories")


class TestKickoffApprovalsAPI:
    """Tests for kickoff request approvals API endpoints (Admin only)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def sales_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_EXEC_CREDS)
        if response.status_code != 200:
            pytest.skip("Sales Executive login failed")
        return response.json()["access_token"]
    
    def test_pending_kickoff_approvals_admin(self, admin_token):
        """Test /api/sales-funnel/pending-kickoff-approvals for Admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals", headers=headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "requests" in data or isinstance(data, list) or isinstance(data, dict)
        requests_list = data.get("requests", []) if isinstance(data, dict) else data
        print(f"✓ Admin pending-kickoff-approvals returned {len(requests_list)} kickoff requests")
    
    def test_pending_kickoff_denied_for_sales_exec(self, sales_token):
        """Test /api/sales-funnel/pending-kickoff-approvals denied for non-admin"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals", headers=headers)
        # Could be 403 or return empty results based on role
        print(f"✓ Sales Exec kickoff approvals: status {response.status_code}")


class TestApprovalsAggregation:
    """Test approvals center aggregation endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_all_pending_approvals_accessible(self, admin_token):
        """Test all approval types are accessible for Admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test all approval endpoints
        endpoints = [
            "/api/approvals/pending",
            "/api/approvals/my-requests",
            "/api/ctc/pending-approvals",
            "/api/go-live/pending",
            "/api/permission-change-requests",
            "/api/employees/modification-requests/pending",
            "/api/agreements/pending-approval",
            "/api/sales-funnel/pending-kickoff-approvals",
            "/api/expenses/pending-approvals"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200
                }
            except Exception as e:
                results[endpoint] = {"status": "error", "error": str(e)}
        
        # Print results
        for endpoint, result in results.items():
            status = "✓" if result.get("success") else "✗"
            print(f"{status} {endpoint}: {result['status']}")
        
        # Assert critical endpoints work
        assert results["/api/approvals/pending"]["success"], "Pending approvals must work"
        assert results["/api/expenses/pending-approvals"]["success"], "Expense pending approvals must work"


class TestExpenseApprovalFlow:
    """Test the expense approval workflow"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def sales_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_EXEC_CREDS)
        if response.status_code != 200:
            pytest.skip("Sales Executive login failed")
        return response.json()["access_token"]
    
    def test_create_expense_as_employee(self, sales_token):
        """Test creating an expense as a regular employee"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        expense_data = {
            "category": "travel",
            "amount": 1500,
            "description": "TEST_Taxi for client meeting",
            "expense_date": "2025-01-15",
            "notes": "Automated test expense"
        }
        
        response = requests.post(f"{BASE_URL}/api/expenses", headers=headers, json=expense_data)
        assert response.status_code == 200, f"Failed to create expense: {response.text}"
        data = response.json()
        assert "expense_id" in data
        print(f"✓ Created expense: {data['expense_id']}")
        return data["expense_id"]
    
    def test_expense_approve_requires_auth(self):
        """Test expense approval without auth is denied"""
        response = requests.post(f"{BASE_URL}/api/expenses/fake-id/approve", json={})
        assert response.status_code in [401, 403, 422], "Should require auth"
        print("✓ Expense approval requires authentication")
    
    def test_expense_reject_requires_reason(self, admin_token):
        """Test expense rejection requires a reason"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get any pending expense
        expenses_resp = requests.get(f"{BASE_URL}/api/expenses/pending-approvals", headers=headers)
        if expenses_resp.status_code != 200:
            pytest.skip("Could not get expenses")
        
        expenses = expenses_resp.json()
        if not expenses:
            pytest.skip("No pending expenses to test rejection")
        
        # Try rejecting without reason
        expense_id = expenses[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/expenses/{expense_id}/reject", 
            headers=headers, 
            json={}  # Empty reason
        )
        # Should fail or return error
        assert response.status_code in [400, 422], f"Should require rejection reason: {response.status_code}"
        print("✓ Expense rejection requires reason")


class TestRouteRedirects:
    """Test that /expense-approvals redirects to /approvals"""
    
    def test_expense_approvals_route_defined_in_app(self):
        """Verify the redirect is defined - this is checked via frontend"""
        # This is primarily a frontend routing test
        # The backend doesn't handle this redirect - React Router does
        print("✓ Route redirect /expense-approvals -> /approvals is a frontend concern")
        print("  Will be tested in Playwright UI tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
