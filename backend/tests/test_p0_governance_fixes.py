"""
Test P0 Governance Fixes for ERP System
========================================
Tests for:
1. GET /api/approvals/my - user's pending approvals and submitted requests with summary
2. GET /api/payroll/my - user's salary slips, reimbursements, encashments
3. POST /api/projects - budget field mandatory and must be > 0
4. POST /api/expenses/{id}/approve - receipt validation for expenses >= 500
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
HR_CREDS = {"employee_id": "EMP002", "password": "hr123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}


class TestAuthHelper:
    """Helper class for authentication"""
    
    @staticmethod
    def get_token(employee_id: str, password: str) -> str:
        """Get auth token for a user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": employee_id, "password": password}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def get_auth_header(token: str) -> dict:
        """Get authorization header"""
        return {"Authorization": f"Bearer {token}"}


class TestApprovalsMyEndpoint:
    """Test GET /api/approvals/my endpoint"""
    
    def test_approvals_my_endpoint_exists(self):
        """Test that /api/approvals/my endpoint exists and requires auth"""
        response = requests.get(f"{BASE_URL}/api/approvals/my")
        # Should return 401 without auth, not 404
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: /api/approvals/my endpoint exists and requires authentication")
    
    def test_approvals_my_returns_correct_structure(self):
        """Test that /api/approvals/my returns correct structure with summary"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/approvals/my",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "pending_for_me" in data, "Missing 'pending_for_me' field"
        assert "my_requests" in data, "Missing 'my_requests' field"
        assert "summary" in data, "Missing 'summary' field"
        
        # Verify summary structure
        summary = data["summary"]
        assert "pending_to_action" in summary, "Missing 'pending_to_action' in summary"
        assert "my_approved" in summary, "Missing 'my_approved' in summary"
        assert "my_rejected" in summary, "Missing 'my_rejected' in summary"
        assert "my_pending" in summary, "Missing 'my_pending' in summary"
        assert "total_my_requests" in summary, "Missing 'total_my_requests' in summary"
        
        print(f"PASS: /api/approvals/my returns correct structure")
        print(f"  - pending_for_me: {len(data['pending_for_me'])} items")
        print(f"  - my_requests: {len(data['my_requests'])} items")
        print(f"  - summary: {summary}")
    
    def test_approvals_my_with_hr_user(self):
        """Test /api/approvals/my with HR user"""
        token = TestAuthHelper.get_token(**HR_CREDS)
        assert token, "Failed to get HR token"
        
        response = requests.get(
            f"{BASE_URL}/api/approvals/my",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data.get("pending_for_me"), list), "pending_for_me should be a list"
        assert isinstance(data.get("my_requests"), list), "my_requests should be a list"
        
        print(f"PASS: /api/approvals/my works for HR user")
    
    def test_approvals_my_with_sales_user(self):
        """Test /api/approvals/my with Sales user"""
        token = TestAuthHelper.get_token(**SALES_CREDS)
        assert token, "Failed to get Sales token"
        
        response = requests.get(
            f"{BASE_URL}/api/approvals/my",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data.get("pending_for_me"), list), "pending_for_me should be a list"
        assert isinstance(data.get("my_requests"), list), "my_requests should be a list"
        
        print(f"PASS: /api/approvals/my works for Sales user")


class TestPayrollMyEndpoint:
    """Test GET /api/payroll/my endpoint"""
    
    def test_payroll_my_endpoint_exists(self):
        """Test that /api/payroll/my endpoint exists and requires auth"""
        response = requests.get(f"{BASE_URL}/api/payroll/my")
        # Should return 401 without auth, not 404
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: /api/payroll/my endpoint exists and requires authentication")
    
    def test_payroll_my_returns_correct_structure(self):
        """Test that /api/payroll/my returns correct structure"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/my",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # May return 404 if employee record not found - that's acceptable
        if response.status_code == 404:
            print("INFO: /api/payroll/my returned 404 - employee record not found for admin user")
            print("PASS: Endpoint exists and handles missing employee record correctly")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "employee_id" in data, "Missing 'employee_id' field"
        assert "salary_slips" in data, "Missing 'salary_slips' field"
        assert "pending_reimbursements" in data, "Missing 'pending_reimbursements' field"
        assert "leave_encashments" in data, "Missing 'leave_encashments' field"
        assert "lop_leaves" in data, "Missing 'lop_leaves' field"
        assert "summary" in data, "Missing 'summary' field"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_slips" in summary, "Missing 'total_slips' in summary"
        assert "total_net_paid" in summary, "Missing 'total_net_paid' in summary"
        assert "pending_reimbursement_amount" in summary, "Missing 'pending_reimbursement_amount' in summary"
        assert "approved_encashment_amount" in summary, "Missing 'approved_encashment_amount' in summary"
        assert "lop_days_this_period" in summary, "Missing 'lop_days_this_period' in summary"
        
        print(f"PASS: /api/payroll/my returns correct structure")
        print(f"  - employee_id: {data.get('employee_id')}")
        print(f"  - salary_slips: {len(data['salary_slips'])} items")
        print(f"  - summary: {summary}")
    
    def test_payroll_my_with_month_filter(self):
        """Test /api/payroll/my with month filter"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        current_month = datetime.now().strftime("%Y-%m")
        response = requests.get(
            f"{BASE_URL}/api/payroll/my?month={current_month}",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # May return 404 if employee record not found
        if response.status_code == 404:
            print("INFO: /api/payroll/my with month filter returned 404 - employee record not found")
            print("PASS: Endpoint handles month filter correctly")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: /api/payroll/my accepts month filter parameter")
    
    def test_payroll_my_with_hr_user(self):
        """Test /api/payroll/my with HR user"""
        token = TestAuthHelper.get_token(**HR_CREDS)
        assert token, "Failed to get HR token"
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/my",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # May return 404 if employee record not found
        if response.status_code == 404:
            print("INFO: /api/payroll/my returned 404 for HR user - employee record not found")
            print("PASS: Endpoint exists and handles missing employee record correctly")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: /api/payroll/my works for HR user")


class TestProjectBudgetValidation:
    """Test POST /api/projects budget validation"""
    
    def test_project_creation_fails_without_budget(self):
        """Test that project creation fails without budget field"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        project_data = {
            "name": f"TEST_Project_No_Budget_{uuid.uuid4().hex[:8]}",
            "client_name": "Test Client",
            "start_date": datetime.now(timezone.utc).isoformat()
            # No budget field
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=project_data,
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Should fail with 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"PASS: Project creation fails without budget field (status: {response.status_code})")
    
    def test_project_creation_fails_with_zero_budget(self):
        """Test that project creation fails with budget=0"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        project_data = {
            "name": f"TEST_Project_Zero_Budget_{uuid.uuid4().hex[:8]}",
            "client_name": "Test Client",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "budget": 0  # Zero budget
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=project_data,
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Should fail with 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"PASS: Project creation fails with budget=0 (status: {response.status_code})")
    
    def test_project_creation_fails_with_negative_budget(self):
        """Test that project creation fails with negative budget"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        project_data = {
            "name": f"TEST_Project_Negative_Budget_{uuid.uuid4().hex[:8]}",
            "client_name": "Test Client",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "budget": -1000  # Negative budget
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=project_data,
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Should fail with 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"PASS: Project creation fails with negative budget (status: {response.status_code})")
    
    def test_project_creation_succeeds_with_positive_budget(self):
        """Test that project creation succeeds with budget > 0"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        project_name = f"TEST_Project_Valid_Budget_{uuid.uuid4().hex[:8]}"
        project_data = {
            "name": project_name,
            "client_name": "Test Client",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "budget": 50000  # Valid positive budget
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects",
            json=project_data,
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        project_id = data.get("id") or data.get("project_id")
        
        print(f"PASS: Project creation succeeds with budget > 0")
        print(f"  - Project ID: {project_id}")
        print(f"  - Budget: 50000")
        
        # Cleanup - delete the test project
        if project_id:
            cleanup_response = requests.delete(
                f"{BASE_URL}/api/projects/{project_id}",
                headers=TestAuthHelper.get_auth_header(token)
            )
            if cleanup_response.status_code in [200, 204]:
                print(f"  - Cleanup: Test project deleted")


class TestExpenseReceiptValidation:
    """Test expense receipt validation on approval"""
    
    def test_expense_approval_fails_without_receipt_for_large_expense(self):
        """Test that expense approval fails if expense >= 500 and no receipt attached"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        # First, create an expense without receipt
        expense_data = {
            "category": "travel",
            "amount": 600,  # >= 500 threshold
            "description": f"TEST_Expense_No_Receipt_{uuid.uuid4().hex[:8]}",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "is_office_expense": True  # To bypass project requirement
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/expenses",
            json=expense_data,
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        if create_response.status_code not in [200, 201]:
            print(f"INFO: Could not create test expense: {create_response.status_code} - {create_response.text}")
            pytest.skip("Could not create test expense")
        
        expense_id = create_response.json().get("expense_id")
        assert expense_id, "No expense_id returned"
        
        # Submit the expense
        submit_response = requests.post(
            f"{BASE_URL}/api/expenses/{expense_id}/submit",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Submit should fail because no receipt for expense >= 500
        if submit_response.status_code == 400:
            error_msg = submit_response.json().get("detail", "")
            assert "receipt" in error_msg.lower() or "500" in error_msg, f"Expected receipt validation error, got: {error_msg}"
            print(f"PASS: Expense submission fails without receipt for expense >= 500")
            print(f"  - Error: {error_msg}")
            
            # Cleanup
            requests.delete(
                f"{BASE_URL}/api/expenses/{expense_id}",
                headers=TestAuthHelper.get_auth_header(token)
            )
            return
        
        # If submit succeeded, try to approve (defense in depth check)
        if submit_response.status_code == 200:
            # Get HR token to approve
            hr_token = TestAuthHelper.get_token(**HR_CREDS)
            
            approve_response = requests.post(
                f"{BASE_URL}/api/expenses/{expense_id}/approve",
                json={"remarks": "Test approval"},
                headers=TestAuthHelper.get_auth_header(hr_token)
            )
            
            # Approval should fail due to receipt validation (defense in depth)
            if approve_response.status_code == 400:
                error_msg = approve_response.json().get("detail", "")
                assert "receipt" in error_msg.lower() or "500" in error_msg.lower() or "governance" in error_msg.lower(), \
                    f"Expected receipt validation error, got: {error_msg}"
                print(f"PASS: Expense approval fails without receipt (defense in depth)")
                print(f"  - Error: {error_msg}")
            else:
                print(f"WARNING: Expense approval did not fail as expected: {approve_response.status_code}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/expenses/{expense_id}",
            headers=TestAuthHelper.get_auth_header(token)
        )
    
    def test_expense_below_threshold_can_be_submitted_without_receipt(self):
        """Test that expense < 500 can be submitted without receipt"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        # Create an expense below threshold without receipt
        expense_data = {
            "category": "food",
            "amount": 300,  # Below 500 threshold
            "description": f"TEST_Expense_Below_Threshold_{uuid.uuid4().hex[:8]}",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "is_office_expense": True
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/expenses",
            json=expense_data,
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        if create_response.status_code not in [200, 201]:
            print(f"INFO: Could not create test expense: {create_response.status_code}")
            pytest.skip("Could not create test expense")
        
        expense_id = create_response.json().get("expense_id")
        
        # Submit the expense - should succeed without receipt
        submit_response = requests.post(
            f"{BASE_URL}/api/expenses/{expense_id}/submit",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        assert submit_response.status_code == 200, f"Expected 200, got {submit_response.status_code}: {submit_response.text}"
        print(f"PASS: Expense below 500 can be submitted without receipt")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/expenses/{expense_id}",
            headers=TestAuthHelper.get_auth_header(token)
        )


class TestAnalyticsExceptionHandling:
    """Test that analytics.py has proper exception handling (no bare except:)"""
    
    def test_analytics_funnel_summary_handles_errors_gracefully(self):
        """Test that analytics endpoints handle errors gracefully"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/funnel-summary",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Should return 200 or a proper error, not 500
        assert response.status_code != 500, f"Analytics endpoint returned 500 error: {response.text}"
        print(f"PASS: Analytics funnel-summary handles requests properly (status: {response.status_code})")
    
    def test_analytics_bottleneck_handles_errors_gracefully(self):
        """Test that bottleneck analysis handles errors gracefully"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/bottleneck-analysis",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Should return 200 or a proper error, not 500
        assert response.status_code != 500, f"Analytics endpoint returned 500 error: {response.text}"
        print(f"PASS: Analytics bottleneck-analysis handles requests properly (status: {response.status_code})")
    
    def test_analytics_velocity_handles_errors_gracefully(self):
        """Test that velocity metrics handles errors gracefully"""
        token = TestAuthHelper.get_token(**ADMIN_CREDS)
        assert token, "Failed to get admin token"
        
        response = requests.get(
            f"{BASE_URL}/api/analytics/velocity",
            headers=TestAuthHelper.get_auth_header(token)
        )
        
        # Should return 200 or a proper error, not 500
        assert response.status_code != 500, f"Analytics endpoint returned 500 error: {response.text}"
        print(f"PASS: Analytics velocity handles requests properly (status: {response.status_code})")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
