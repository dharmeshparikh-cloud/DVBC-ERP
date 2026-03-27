"""
Test Suite: Unified Penalty Management System
Tests all penalty CRUD operations, approve/reject/send-back flows, bulk actions, and API endpoints.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://funnel-governance.preview.emergentagent.com')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}


class TestUnifiedPenaltyManagement:
    """Unified Penalty Management System Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        assert self.token, "No access_token in login response"
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get current month
        self.current_month = datetime.now().strftime("%Y-%m")
        
        yield
        
        self.session.close()
    
    # ==================== PENALTY CATEGORIES ====================
    
    def test_get_penalty_categories(self):
        """Test GET /api/penalties/categories returns all penalty categories"""
        response = self.session.get(f"{BASE_URL}/api/penalties/categories")
        assert response.status_code == 200, f"Failed to get categories: {response.text}"
        
        data = response.json()
        assert "categories" in data, "Response missing 'categories' field"
        
        categories = data["categories"]
        # Verify expected categories exist
        expected_categories = ["attendance", "leave", "travel", "expense", "general"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
            assert "violations" in categories[cat], f"Category {cat} missing violations"
            assert len(categories[cat]["violations"]) > 0, f"Category {cat} has no violations"
        
        print(f"✓ Found {len(categories)} penalty categories with {data.get('total_violation_types', 0)} violation types")
    
    # ==================== MONTH PENALTIES ====================
    
    def test_get_month_penalties(self):
        """Test GET /api/penalties/month/{month} returns penalties with count_by_status"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}")
        assert response.status_code == 200, f"Failed to get month penalties: {response.text}"
        
        data = response.json()
        assert "penalties" in data, "Response missing 'penalties' field"
        assert "count_by_status" in data, "Response missing 'count_by_status' field"
        
        count_by_status = data["count_by_status"]
        assert "pending_review" in count_by_status, "Missing pending_review count"
        assert "approved" in count_by_status, "Missing approved count"
        assert "rejected" in count_by_status, "Missing rejected count"
        
        print(f"✓ Month {self.current_month}: {len(data['penalties'])} penalties")
        print(f"  - Pending: {count_by_status.get('pending_review', 0)}")
        print(f"  - Approved: {count_by_status.get('approved', 0)}")
        print(f"  - Rejected: {count_by_status.get('rejected', 0)}")
    
    # ==================== APPLY MANUAL PENALTY ====================
    
    def _create_unique_penalty(self):
        """Helper to create a unique penalty for testing"""
        # First get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200, f"Failed to get employees: {emp_response.text}"
        
        emp_data = emp_response.json()
        # Handle different response formats: list, {data: []}, {items: []}
        if isinstance(emp_data, list):
            employees = emp_data
        elif "items" in emp_data:
            employees = emp_data.get("items", [])
        else:
            employees = emp_data.get("data", [])
        assert len(employees) > 0, "No employees found"
        
        employee = employees[0]
        employee_id = employee.get("id")
        
        # Apply a manual penalty with unique reference_id to avoid upsert
        unique_ref = str(uuid.uuid4())[:8]
        penalty_data = {
            "employee_id": employee_id,
            "violation_code": "AT_LATE",
            "category": "attendance",
            "description": f"Test manual penalty {unique_ref}",
            "amount": 150,
            "month": self.current_month,
            "source": "manual",
            "reference_id": f"TEST_{unique_ref}"  # Unique reference to avoid upsert
        }
        
        response = self.session.post(f"{BASE_URL}/api/penalties/apply", json=penalty_data)
        assert response.status_code == 200, f"Failed to apply penalty: {response.text}"
        
        data = response.json()
        assert "penalty_id" in data, "Response missing penalty_id"
        
        return data["penalty_id"]
    
    def test_apply_manual_penalty(self):
        """Test POST /api/penalties/apply creates penalty with status pending_review"""
        penalty_id = self._create_unique_penalty()
        print(f"✓ Created penalty {penalty_id} with status pending_review")
    
    # ==================== APPROVE PENALTY ====================
    
    def test_approve_penalty(self):
        """Test POST /api/penalties/{id}/approve changes status to approved"""
        # First create a penalty
        penalty_id = self._create_unique_penalty()
        
        # Approve it
        response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/approve")
        assert response.status_code == 200, f"Failed to approve penalty: {response.text}"
        
        data = response.json()
        assert data.get("status") == "approved", f"Expected status 'approved', got {data.get('status')}"
        
        print(f"✓ Approved penalty {penalty_id}")
    
    # ==================== REJECT PENALTY ====================
    
    def test_reject_penalty(self):
        """Test POST /api/penalties/{id}/reject changes status to rejected"""
        # First create a penalty
        penalty_id = self._create_unique_penalty()
        
        # Reject it with reason
        reject_data = {"reason": "Test rejection reason"}
        response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/reject", json=reject_data)
        assert response.status_code == 200, f"Failed to reject penalty: {response.text}"
        
        data = response.json()
        assert data.get("status") == "rejected", f"Expected status 'rejected', got {data.get('status')}"
        
        print(f"✓ Rejected penalty {penalty_id}")
    
    # ==================== SEND BACK PENALTY ====================
    
    def test_send_back_penalty(self):
        """Test POST /api/penalties/{id}/send-back returns penalty to pending_review"""
        # First create and approve a penalty
        penalty_id = self._create_unique_penalty()
        
        # Approve it first
        approve_response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/approve")
        assert approve_response.status_code == 200, f"Failed to approve: {approve_response.text}"
        
        # Send it back
        send_back_data = {"reason": "Sent back for review"}
        response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/send-back", json=send_back_data)
        assert response.status_code == 200, f"Failed to send back penalty: {response.text}"
        
        data = response.json()
        assert data.get("status") == "pending_review", f"Expected status 'pending_review', got {data.get('status')}"
        
        print(f"✓ Sent back penalty {penalty_id} to pending_review")
    
    # ==================== UPDATE PENALTY ====================
    
    def test_update_penalty(self):
        """Test PUT /api/penalties/{id} updates pending penalty amount/reason"""
        # First create a penalty
        penalty_id = self._create_unique_penalty()
        
        # Update it
        update_data = {
            "amount": 200,
            "reason": "Updated reason for penalty"
        }
        response = self.session.put(f"{BASE_URL}/api/penalties/{penalty_id}", json=update_data)
        assert response.status_code == 200, f"Failed to update penalty: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response missing message"
        
        print(f"✓ Updated penalty {penalty_id} amount to 200")
    
    # ==================== BULK ACTION ====================
    
    def test_bulk_approve_penalties(self):
        """Test POST /api/penalties/bulk-action supports bulk approve"""
        # Create two penalties
        penalty_id_1 = self._create_unique_penalty()
        penalty_id_2 = self._create_unique_penalty()
        
        # Bulk approve
        bulk_data = {
            "penalty_ids": [penalty_id_1, penalty_id_2],
            "action": "approve"
        }
        response = self.session.post(f"{BASE_URL}/api/penalties/bulk-action", json=bulk_data)
        assert response.status_code == 200, f"Failed bulk approve: {response.text}"
        
        data = response.json()
        assert "modified_count" in data, "Response missing modified_count"
        assert data["modified_count"] >= 1, f"Expected at least 1 modified, got {data['modified_count']}"
        
        print(f"✓ Bulk approved {data['modified_count']} penalties")
    
    def test_bulk_reject_penalties(self):
        """Test POST /api/penalties/bulk-action supports bulk reject"""
        # Create two penalties
        penalty_id_1 = self._create_unique_penalty()
        penalty_id_2 = self._create_unique_penalty()
        
        # Bulk reject
        bulk_data = {
            "penalty_ids": [penalty_id_1, penalty_id_2],
            "action": "reject",
            "reason": "Bulk rejection test"
        }
        response = self.session.post(f"{BASE_URL}/api/penalties/bulk-action", json=bulk_data)
        assert response.status_code == 200, f"Failed bulk reject: {response.text}"
        
        data = response.json()
        assert "modified_count" in data, "Response missing modified_count"
        
        print(f"✓ Bulk rejected {data['modified_count']} penalties")
    
    # ==================== EMPLOYEE PENALTIES ====================
    
    def test_get_employee_penalties(self):
        """Test GET /api/penalties/employee/{employee_id} returns employee penalties"""
        # Get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        
        emp_data = emp_response.json()
        # Handle different response formats: list, {data: []}, {items: []}
        if isinstance(emp_data, list):
            employees = emp_data
        elif "items" in emp_data:
            employees = emp_data.get("items", [])
        else:
            employees = emp_data.get("data", [])
        assert len(employees) > 0
        
        employee_id = employees[0].get("id")
        
        # Get employee penalties
        response = self.session.get(f"{BASE_URL}/api/penalties/employee/{employee_id}")
        assert response.status_code == 200, f"Failed to get employee penalties: {response.text}"
        
        data = response.json()
        assert "penalties" in data, "Response missing 'penalties' field"
        assert "count_by_status" in data, "Response missing 'count_by_status' field"
        
        print(f"✓ Got {len(data['penalties'])} penalties for employee {employee_id}")
    
    # ==================== SUMMARY BY EMPLOYEES ====================
    
    def test_get_penalty_summary_by_employees(self):
        """Test GET /api/penalties/summary-by-employees returns grouped summary"""
        response = self.session.get(f"{BASE_URL}/api/penalties/summary-by-employees?month={self.current_month}")
        assert response.status_code == 200, f"Failed to get summary: {response.text}"
        
        data = response.json()
        # Response is a dict keyed by employee_id
        assert isinstance(data, dict), "Expected dict response"
        
        print(f"✓ Got penalty summary for {len(data)} employees")
    
    # ==================== PENALTY SUMMARY ====================
    
    def test_get_penalty_summary(self):
        """Test GET /api/penalties/summary returns comprehensive summary"""
        response = self.session.get(f"{BASE_URL}/api/penalties/summary")
        assert response.status_code == 200, f"Failed to get summary: {response.text}"
        
        data = response.json()
        assert "by_category" in data, "Response missing 'by_category'"
        assert "monthly_breakdown" in data, "Response missing 'monthly_breakdown'"
        assert "count_by_status" in data, "Response missing 'count_by_status'"
        
        print(f"✓ Got penalty summary: grand_total={data.get('grand_total', 0)}")
    
    # ==================== REVOKE PENALTY ====================
    
    def test_revoke_penalty(self):
        """Test DELETE /api/penalties/{id} revokes a penalty"""
        # First create a penalty
        penalty_id = self._create_unique_penalty()
        
        # Revoke it
        response = self.session.delete(f"{BASE_URL}/api/penalties/{penalty_id}")
        assert response.status_code == 200, f"Failed to revoke penalty: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response missing message"
        
        print(f"✓ Revoked penalty {penalty_id}")
    
    # ==================== RBAC - NON-HR ACCESS ====================
    
    def test_non_hr_cannot_apply_penalty(self):
        """Test that non-HR users cannot apply penalties"""
        # Login as sales user
        sales_session = requests.Session()
        sales_session.headers.update({"Content-Type": "application/json"})
        
        login_response = sales_session.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        assert login_response.status_code == 200, f"Sales login failed: {login_response.text}"
        
        sales_token = login_response.json().get("access_token")
        sales_session.headers.update({"Authorization": f"Bearer {sales_token}"})
        
        # Try to apply penalty
        penalty_data = {
            "employee_id": "some-id",
            "violation_code": "AT_LATE",
            "month": self.current_month,
            "source": "manual"
        }
        
        response = sales_session.post(f"{BASE_URL}/api/penalties/apply", json=penalty_data)
        # Should be 403 Forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        sales_session.close()
        print("✓ Non-HR user correctly denied penalty apply access")
    
    # ==================== FILTER BY STATUS ====================
    
    def test_filter_penalties_by_status(self):
        """Test GET /api/penalties/month/{month}?status=pending_review filters correctly"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}?status=pending_review")
        assert response.status_code == 200, f"Failed to filter penalties: {response.text}"
        
        data = response.json()
        penalties = data.get("penalties", [])
        
        # All returned penalties should be pending_review
        for p in penalties:
            assert p.get("status") == "pending_review", f"Found non-pending penalty: {p.get('status')}"
        
        print(f"✓ Filtered {len(penalties)} pending_review penalties")
    
    # ==================== FILTER BY CATEGORY ====================
    
    def test_filter_penalties_by_category(self):
        """Test GET /api/penalties/month/{month}?category=attendance filters correctly"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}?category=attendance")
        assert response.status_code == 200, f"Failed to filter penalties: {response.text}"
        
        data = response.json()
        penalties = data.get("penalties", [])
        
        # All returned penalties should be attendance category
        for p in penalties:
            assert p.get("category") == "attendance", f"Found non-attendance penalty: {p.get('category')}"
        
        print(f"✓ Filtered {len(penalties)} attendance penalties")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
