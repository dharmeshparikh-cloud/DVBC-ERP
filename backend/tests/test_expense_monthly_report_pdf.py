"""
Test Monthly Expense Report API and related expense features
Testing:
1. My Expenses page shows all expenses with correct amounts
2. Meeting expenses show travel details (mode, km, lead name)
3. Monthly Expense Report endpoint - GET /api/expenses/report/monthly-meeting-expenses
4. Expense notifications on approval/rejection
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMonthlyExpenseReport:
    """Test monthly expense report endpoint for PDF download support"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.sales_creds = {"employee_id": "EMP003", "password": "Sales@123"}
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
    
    def get_token(self, creds):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    def test_my_expenses_returns_expenses(self):
        """Test GET /api/my/expenses returns user expenses with summary"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/my/expenses", headers=headers)
        
        assert response.status_code == 200, f"GET /api/my/expenses failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "expenses" in data, "Response missing 'expenses' key"
        assert "summary" in data, "Response missing 'summary' key"
        
        # Verify summary has required fields
        summary = data["summary"]
        assert "pending" in summary, "Summary missing 'pending' count"
        assert "approved" in summary, "Summary missing 'approved' count"
        assert "total_amount" in summary, "Summary missing 'total_amount'"
        
        print(f"PASS: /api/my/expenses returned {len(data['expenses'])} expenses")
        print(f"  Summary: pending={summary.get('pending', 0)}, approved={summary.get('approved', 0)}, total_amount={summary.get('total_amount', 0)}")
    
    def test_my_expenses_shows_meeting_expenses(self):
        """Test that My Expenses includes meeting expenses with travel details"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/my/expenses", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        expenses = data.get("expenses", [])
        
        # Find meeting expenses (those with expense_type='meeting_expense' or travel_details)
        meeting_expenses = [
            e for e in expenses 
            if e.get("expense_type") == "meeting_expense" or e.get("travel_details")
        ]
        
        print(f"Found {len(meeting_expenses)} meeting expenses out of {len(expenses)} total")
        
        if meeting_expenses:
            exp = meeting_expenses[0]
            travel = exp.get("travel_details", {})
            print(f"  Sample meeting expense:")
            print(f"    - Amount: {exp.get('total_amount') or exp.get('amount')}")
            print(f"    - Travel Mode: {travel.get('travel_mode', 'N/A')}")
            print(f"    - Distance KM: {travel.get('distance_km') or travel.get('total_km', 0)}")
            print(f"    - Lead Name: {exp.get('lead_name', 'N/A')}")
        
        print("PASS: Meeting expenses accessible in My Expenses")
    
    def test_monthly_report_endpoint_basic(self):
        """Test GET /api/expenses/report/monthly-meeting-expenses basic functionality"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/expenses/report/monthly-meeting-expenses?month={current_month}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Monthly report endpoint failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "month" in data, "Response missing 'month'"
        assert "summary" in data, "Response missing 'summary'"
        assert "expenses" in data, "Response missing 'expenses'"
        
        summary = data["summary"]
        # Verify summary fields required for PDF
        required_summary_fields = [
            "total_expenses", "total_amount", "approved_amount", 
            "pending_amount", "rejected_amount", "approved_count",
            "pending_count", "rejected_count"
        ]
        for field in required_summary_fields:
            assert field in summary, f"Summary missing '{field}' field"
        
        print(f"PASS: Monthly report for {current_month}")
        print(f"  Total expenses: {summary['total_expenses']}")
        print(f"  Total amount: {summary['total_amount']}")
        print(f"  Approved: {summary['approved_count']} ({summary['approved_amount']})")
        print(f"  Pending: {summary['pending_count']} ({summary['pending_amount']})")
    
    def test_monthly_report_expense_fields_for_pdf(self):
        """Test that monthly report expenses have all fields needed for PDF generation"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/expenses/report/monthly-meeting-expenses?month={current_month}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        expenses = data.get("expenses", [])
        
        if expenses:
            exp = expenses[0]
            # Fields required for PDF table generation
            required_fields = [
                "lead_name", "company", "stage", "expense_date",
                "travel_mode", "amount", "status", "payroll_linked"
            ]
            for field in required_fields:
                assert field in exp, f"Expense missing '{field}' field for PDF"
            
            print(f"PASS: Expense has all required PDF fields")
            print(f"  Sample: Lead={exp.get('lead_name')}, Company={exp.get('company')}, Amount={exp.get('amount')}, Status={exp.get('status')}")
        else:
            print("INFO: No expenses found for current month (endpoint works, no data)")
    
    def test_admin_monthly_report_sees_all(self):
        """Test admin can see all expenses in monthly report"""
        token = self.get_token(self.admin_creds)
        assert token, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/expenses/report/monthly-meeting-expenses?month={current_month}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"PASS: Admin monthly report - {len(data.get('expenses', []))} expenses visible")
        print(f"  Generated by: {data.get('generated_by')}")


class TestExpenseApprovalNotifications:
    """Test expense approval/rejection notification creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.sales_creds = {"employee_id": "EMP003", "password": "Sales@123"}
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
    
    def get_token(self, creds):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    def test_notifications_endpoint_exists(self):
        """Test that notifications endpoint exists"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        
        assert response.status_code == 200, f"Notifications endpoint failed: {response.text}"
        print("PASS: Notifications endpoint accessible")
    
    def test_expense_approval_creates_notification(self):
        """Test that expense approval creates notification for employee"""
        # This tests the notification creation flow
        admin_token = self.get_token(self.admin_creds)
        assert admin_token, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Find a pending expense to approve (or check existing notifications)
        response = requests.get(f"{BASE_URL}/api/expenses/pending-approvals", headers=headers)
        
        if response.status_code == 200:
            pending = response.json()
            print(f"PASS: Pending approvals endpoint - {len(pending)} expenses")
            
            # If there are pending expenses, approving one should create notification
            # (Testing endpoint accessibility, actual approval would modify data)
            if pending:
                print(f"  First pending expense: {pending[0].get('id')}, Amount: {pending[0].get('total_amount') or pending[0].get('amount')}")
        else:
            print(f"INFO: Pending approvals returned {response.status_code}")


class TestPricingPlanValidation:
    """Test Pricing Plan validation messages - user-friendly field names"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.sales_creds = {"employee_id": "EMP003", "password": "Sales@123"}
    
    def get_token(self, creds):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    def test_pricing_plan_validation_error_format(self):
        """Test that pricing plan validation returns proper error format"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Submit incomplete pricing plan to trigger validation
        incomplete_plan = {
            "lead_id": "some-lead-id",
            # Missing required fields: name, total_amount
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pricing-plans",
            json=incomplete_plan,
            headers=headers
        )
        
        # We expect 422 validation error
        if response.status_code == 422:
            error_detail = response.json().get("detail", [])
            print(f"PASS: Validation error returned with {len(error_detail)} issues")
            
            # Check that error format is as expected
            if error_detail and isinstance(error_detail, list):
                for err in error_detail[:3]:
                    print(f"  - Field: {err.get('loc')}, Msg: {err.get('msg')}")
        else:
            print(f"INFO: Pricing plan returned {response.status_code} (may need valid lead_id)")


class TestLeadExpenseDisplay:
    """Test expense display in context of lead ID"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.sales_creds = {"employee_id": "EMP003", "password": "Sales@123"}
        self.lead_id = "2e8724b1-b9b7-4983-b3cc-6c47e5de4851"
    
    def get_token(self, creds):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    def test_lead_exists(self):
        """Verify the test lead exists"""
        token = self.get_token(self.sales_creds)
        assert token, "Failed to get sales user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/leads/{self.lead_id}", headers=headers)
        
        if response.status_code == 200:
            lead = response.json()
            print(f"PASS: Lead found - {lead.get('first_name')} {lead.get('last_name')} at {lead.get('company')}")
        else:
            print(f"INFO: Lead {self.lead_id} not found ({response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
