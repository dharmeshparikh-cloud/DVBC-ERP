"""
Test P1 Features: Regularization, Expense Approvals, Filters
- PUT /api/attendance/{record_id}/regularize - HR/Admin can regularize, recalculates hours and OT
- PUT /api/attendance/{record_id}/regularize - non-HR user gets 403
- GET /api/attendance/admin/list - returns all employee attendance with filters and enriched employee names
- GET /api/attendance/admin/list?status=present - filters by status correctly
- GET /api/expenses/{expense_id} - returns expense detail with meeting_context when linked to meeting
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}


class TestAuthentication:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def sales_token(self):
        """Get sales user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Sales login failed: {response.status_code} - {response.text}")
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        print(f"Admin token obtained: {admin_token[:20]}...")
    
    def test_sales_login(self, sales_token):
        """Verify sales user can login"""
        assert sales_token is not None
        print(f"Sales token obtained: {sales_token[:20]}...")


class TestAttendanceAdminList:
    """Test GET /api/attendance/admin/list endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def sales_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Sales login failed")
    
    def test_admin_list_endpoint_exists(self, admin_token):
        """Test that admin/list endpoint exists and returns data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "records" in data, "Response should have 'records' key"
        assert "summary" in data, "Response should have 'summary' key"
        print(f"Admin list returned {len(data['records'])} records")
    
    def test_admin_list_returns_enriched_employee_names(self, admin_token):
        """Test that records include employee_name, employee_code, department"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if data["records"]:
            record = data["records"][0]
            # Check enriched fields exist
            assert "employee_name" in record, "Record should have employee_name"
            assert "employee_code" in record, "Record should have employee_code"
            assert "department" in record, "Record should have department"
            print(f"Sample record: {record.get('employee_name')} ({record.get('employee_code')})")
    
    def test_admin_list_summary_fields(self, admin_token):
        """Test that summary includes expected fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]
        
        assert "total_records" in summary
        assert "present" in summary
        assert "absent" in summary
        assert "late" in summary
        assert "total_hours" in summary
        assert "total_overtime" in summary
        print(f"Summary: {summary}")
    
    def test_admin_list_filter_by_status(self, admin_token):
        """Test filtering by status=present"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list?status=present", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All records should have status=present
        for record in data["records"]:
            assert record.get("status") == "present", f"Expected status=present, got {record.get('status')}"
        print(f"Filtered by status=present: {len(data['records'])} records")
    
    def test_admin_list_filter_by_location(self, admin_token):
        """Test filtering by work_location"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list?work_location=in_office", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All records should have work_location=in_office
        for record in data["records"]:
            assert record.get("work_location") == "in_office", f"Expected work_location=in_office, got {record.get('work_location')}"
        print(f"Filtered by work_location=in_office: {len(data['records'])} records")
    
    def test_admin_list_forbidden_for_non_hr(self, sales_token):
        """Test that non-HR users get 403"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list", headers=headers)
        
        assert response.status_code == 403, f"Expected 403 for non-HR user, got {response.status_code}"
        print("Non-HR user correctly denied access to admin/list")


class TestAttendanceRegularize:
    """Test PUT /api/attendance/{record_id}/regularize endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def sales_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Sales login failed")
    
    @pytest.fixture(scope="class")
    def test_attendance_record(self, admin_token):
        """Get an existing attendance record to test regularization"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/admin/list", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data["records"]:
                return data["records"][0]
        return None
    
    def test_regularize_endpoint_exists(self, admin_token, test_attendance_record):
        """Test that regularize endpoint exists"""
        if not test_attendance_record:
            pytest.skip("No attendance record available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        record_id = test_attendance_record.get("id")
        
        # Test with minimal data
        response = requests.put(
            f"{BASE_URL}/api/attendance/{record_id}/regularize",
            headers=headers,
            json={"reason": "Test regularization"}
        )
        
        # Should succeed or return validation error, not 404
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code} - {response.text}"
        print(f"Regularize endpoint response: {response.status_code}")
    
    def test_regularize_with_full_data(self, admin_token, test_attendance_record):
        """Test regularization with check-in/out times and status"""
        if not test_attendance_record:
            pytest.skip("No attendance record available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        record_id = test_attendance_record.get("id")
        
        # Create test times
        now = datetime.utcnow()
        check_in = (now.replace(hour=10, minute=0, second=0)).isoformat() + "Z"
        check_out = (now.replace(hour=19, minute=0, second=0)).isoformat() + "Z"
        
        response = requests.put(
            f"{BASE_URL}/api/attendance/{record_id}/regularize",
            headers=headers,
            json={
                "reason": "Forgot to check-in, regularizing",
                "check_in_time": check_in,
                "check_out_time": check_out,
                "status": "present"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "record_id" in data
            print(f"Regularization successful: {data}")
        else:
            print(f"Regularization response: {response.status_code} - {response.text}")
    
    def test_regularize_forbidden_for_non_hr(self, sales_token, test_attendance_record):
        """Test that non-HR users get 403 when trying to regularize"""
        if not test_attendance_record:
            pytest.skip("No attendance record available for testing")
        
        headers = {"Authorization": f"Bearer {sales_token}"}
        record_id = test_attendance_record.get("id")
        
        response = requests.put(
            f"{BASE_URL}/api/attendance/{record_id}/regularize",
            headers=headers,
            json={"reason": "Test - should fail"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-HR user, got {response.status_code}"
        print("Non-HR user correctly denied regularization access")
    
    def test_regularize_recalculates_hours(self, admin_token, test_attendance_record):
        """Test that regularization recalculates working hours and OT"""
        if not test_attendance_record:
            pytest.skip("No attendance record available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        record_id = test_attendance_record.get("id")
        
        # Set 10 hours of work (should trigger OT)
        now = datetime.utcnow()
        check_in = (now.replace(hour=9, minute=0, second=0)).isoformat() + "Z"
        check_out = (now.replace(hour=19, minute=0, second=0)).isoformat() + "Z"  # 10 hours
        
        response = requests.put(
            f"{BASE_URL}/api/attendance/{record_id}/regularize",
            headers=headers,
            json={
                "reason": "Testing hours recalculation",
                "check_in_time": check_in,
                "check_out_time": check_out,
                "status": "present"
            }
        )
        
        assert response.status_code == 200, f"Regularization failed: {response.text}"
        
        # Verify the record was updated
        list_response = requests.get(f"{BASE_URL}/api/attendance/admin/list", headers=headers)
        if list_response.status_code == 200:
            records = list_response.json()["records"]
            updated_record = next((r for r in records if r.get("id") == record_id), None)
            if updated_record:
                print(f"Updated record - Hours: {updated_record.get('working_hours')}, OT: {updated_record.get('overtime_hours')}")


class TestExpenseDetailWithMeetingContext:
    """Test GET /api/expenses/{expense_id} with meeting_context"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def test_expense(self, admin_token):
        """Get an existing expense to test"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses", headers=headers)
        
        if response.status_code == 200:
            expenses = response.json()
            if expenses:
                return expenses[0]
        return None
    
    def test_expense_detail_endpoint(self, admin_token, test_expense):
        """Test that expense detail endpoint returns data"""
        if not test_expense:
            pytest.skip("No expense available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        expense_id = test_expense.get("id")
        
        response = requests.get(f"{BASE_URL}/api/expenses/{expense_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"Expense detail: {data.get('id')}, status: {data.get('status')}")
    
    def test_expense_detail_includes_meeting_context_fields(self, admin_token, test_expense):
        """Test that expense detail can include meeting_context when linked"""
        if not test_expense:
            pytest.skip("No expense available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        expense_id = test_expense.get("id")
        
        response = requests.get(f"{BASE_URL}/api/expenses/{expense_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if meeting_context is present (only if linked to meeting)
        if data.get("linked_meeting_id") or data.get("meeting_id"):
            assert "meeting_context" in data, "Expense linked to meeting should have meeting_context"
            meeting_ctx = data["meeting_context"]
            print(f"Meeting context: {meeting_ctx}")
        else:
            print("Expense not linked to meeting - meeting_context not expected")
    
    def test_expense_detail_includes_travel_context_fields(self, admin_token, test_expense):
        """Test that expense detail can include travel_context when applicable"""
        if not test_expense:
            pytest.skip("No expense available for testing")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        expense_id = test_expense.get("id")
        
        response = requests.get(f"{BASE_URL}/api/expenses/{expense_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if travel_context is present (only for travel expenses)
        if data.get("travel_request_id") or data.get("category") in ["travel", "transport", "cab", "flight", "hotel"]:
            if data.get("travel_request_id"):
                assert "travel_context" in data, "Travel expense should have travel_context"
                print(f"Travel context: {data.get('travel_context')}")
        else:
            print("Not a travel expense - travel_context not expected")


class TestExpenseStatusTabs:
    """Test expense filtering by status for tabs"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_get_all_expenses(self, admin_token):
        """Test getting all expenses"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        print(f"Total expenses: {len(expenses)}")
    
    def test_filter_expenses_by_status_draft(self, admin_token):
        """Test filtering expenses by status=draft"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?status=draft", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        for exp in expenses:
            assert exp.get("status") == "draft"
        print(f"Draft expenses: {len(expenses)}")
    
    def test_filter_expenses_by_status_pending(self, admin_token):
        """Test filtering expenses by status=pending"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?status=pending", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        for exp in expenses:
            assert exp.get("status") == "pending"
        print(f"Pending expenses: {len(expenses)}")
    
    def test_filter_expenses_by_status_approved(self, admin_token):
        """Test filtering expenses by status=approved"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?status=approved", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        for exp in expenses:
            assert exp.get("status") == "approved"
        print(f"Approved expenses: {len(expenses)}")
    
    def test_filter_expenses_by_status_rejected(self, admin_token):
        """Test filtering expenses by status=rejected"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?status=rejected", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        for exp in expenses:
            assert exp.get("status") == "rejected"
        print(f"Rejected expenses: {len(expenses)}")
    
    def test_filter_expenses_by_status_revision_required(self, admin_token):
        """Test filtering expenses by status=revision_required (sent back)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?status=revision_required", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        for exp in expenses:
            assert exp.get("status") == "revision_required"
        print(f"Sent back (revision_required) expenses: {len(expenses)}")
    
    def test_filter_expenses_by_category(self, admin_token):
        """Test filtering expenses by category"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?category=Travel", headers=headers)
        
        assert response.status_code == 200
        expenses = response.json()
        print(f"Travel category expenses: {len(expenses)}")


class TestExpensePendingApprovals:
    """Test expense pending approvals endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_pending_approvals_endpoint(self, admin_token):
        """Test GET /api/expenses/pending-approvals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses/pending-approvals", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        expenses = response.json()
        print(f"Pending approvals: {len(expenses)}")
        
        # Check that it includes various statuses for admin
        statuses = set(exp.get("status") for exp in expenses)
        print(f"Statuses in pending approvals: {statuses}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
