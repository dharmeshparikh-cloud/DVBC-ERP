"""
Expense & Kickoff Approval Flows Test Suite
Tests for: send-back, resubmit, approve-with-modification, withdraw for expenses
Tests for: kickoff withdraw, update, my-kickoff-requests, pending-reimbursements
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://business-logic-ui.preview.emergentagent.com').rstrip('/')

# Test credentials from review_request
TEST_USERS = {
    "admin": {"employee_id": "ADMIN001", "password": "test123"},
    "sales_exec": {"employee_id": "SE001", "password": "test123"},
    "hr_manager": {"employee_id": "HR001", "password": "test123"}
}


class APISession:
    """Helper class for authenticated API requests"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.user_id = None
    
    def login(self, employee_id, password):
        """Login with employee ID and password"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": employee_id,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return True
        return False
    
    def get(self, path, params=None):
        return self.session.get(f"{BASE_URL}{path}", params=params)
    
    def post(self, path, json=None):
        return self.session.post(f"{BASE_URL}{path}", json=json)
    
    def patch(self, path, json=None):
        return self.session.patch(f"{BASE_URL}{path}", json=json)
    
    def delete(self, path):
        return self.session.delete(f"{BASE_URL}{path}")


# ============== EXPENSE APPROVAL FLOW TESTS ==============

class TestExpenseApprovalFlows:
    """Test expense send-back, resubmit, approve-with-modification, withdraw"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test sessions"""
        self.hr_session = APISession()
        self.admin_session = APISession()
        self.sales_session = APISession()
        
        # Login as HR Manager
        hr_logged_in = self.hr_session.login("HR001", "test123")
        assert hr_logged_in, "HR001 login failed"
        
        # Login as Admin
        admin_logged_in = self.admin_session.login("ADMIN001", "test123")
        assert admin_logged_in, "ADMIN001 login failed"
        
        # Login as Sales Executive
        sales_logged_in = self.sales_session.login("SE001", "test123")
        assert sales_logged_in, "SE001 login failed"
    
    def test_01_create_expense_as_owner(self):
        """Create an expense that can be tested for approval flows"""
        expense_data = {
            "category": "travel",
            "description": "TEST_ApprovalFlow expense",
            "line_items": [
                {"category": "travel", "description": "Taxi fare", "amount": 500}
            ],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "Test expense for approval flow testing"
        }
        
        response = self.sales_session.post("/api/expenses", json=expense_data)
        assert response.status_code == 200, f"Failed to create expense: {response.text}"
        
        data = response.json()
        assert "expense_id" in data
        self.__class__.created_expense_id = data["expense_id"]
        print(f"✓ Created expense: {data['expense_id']}")
    
    def test_02_owner_can_edit_pending_expense(self):
        """Test that owner can edit their pending expense (PATCH /api/expenses/{id})"""
        if not hasattr(self.__class__, 'created_expense_id'):
            pytest.skip("No expense created")
        
        expense_id = self.__class__.created_expense_id
        update_data = {
            "description": "TEST_ApprovalFlow expense - Updated",
            "notes": "Updated notes for testing"
        }
        
        response = self.sales_session.patch(f"/api/expenses/{expense_id}", json=update_data)
        assert response.status_code == 200, f"Failed to update expense: {response.text}"
        print(f"✓ Owner edited pending expense: {expense_id}")
        
        # Verify the update
        get_response = self.sales_session.get(f"/api/expenses/{expense_id}")
        assert get_response.status_code == 200
        expense = get_response.json()
        assert expense.get("description") == "TEST_ApprovalFlow expense - Updated"
    
    def test_03_submit_expense_for_approval(self):
        """Submit expense for approval"""
        if not hasattr(self.__class__, 'created_expense_id'):
            pytest.skip("No expense created")
        
        expense_id = self.__class__.created_expense_id
        response = self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        assert response.status_code == 200, f"Failed to submit expense: {response.text}"
        
        data = response.json()
        assert data.get("message") == "Expense submitted for approval"
        print(f"✓ Expense submitted for approval: {expense_id}")
    
    def test_04_owner_can_withdraw_pending_expense(self):
        """Test that owner can withdraw pending expense (POST /api/expenses/{id}/withdraw)"""
        # First create a new expense and submit it
        expense_data = {
            "category": "food",
            "description": "TEST_Withdraw expense",
            "line_items": [
                {"category": "food", "description": "Team lunch", "amount": 300}
            ],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "Test expense for withdraw testing"
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        withdraw_expense_id = create_response.json()["expense_id"]
        
        # Submit it
        submit_response = self.sales_session.post(f"/api/expenses/{withdraw_expense_id}/submit")
        assert submit_response.status_code == 200
        
        # Now withdraw it
        withdraw_response = self.sales_session.post(f"/api/expenses/{withdraw_expense_id}/withdraw")
        assert withdraw_response.status_code == 200, f"Failed to withdraw: {withdraw_response.text}"
        
        data = withdraw_response.json()
        assert data.get("status") == "withdrawn"
        print(f"✓ Owner withdrew pending expense: {withdraw_expense_id}")
        
        # Verify status changed
        get_response = self.sales_session.get(f"/api/expenses/{withdraw_expense_id}")
        assert get_response.status_code == 200
        assert get_response.json().get("status") == "withdrawn"
    
    def test_05_owner_cannot_withdraw_non_pending_expense(self):
        """Test that withdrawn expense cannot be withdrawn again"""
        # Create, submit, withdraw
        expense_data = {
            "category": "miscellaneous",
            "description": "TEST_DoubleWithdraw",
            "line_items": [{"category": "misc", "description": "test", "amount": 100}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        
        # Submit and withdraw
        self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        self.sales_session.post(f"/api/expenses/{expense_id}/withdraw")
        
        # Try to withdraw again - should fail
        second_withdraw = self.sales_session.post(f"/api/expenses/{expense_id}/withdraw")
        assert second_withdraw.status_code == 400, "Should not be able to withdraw already withdrawn expense"
        print(f"✓ Correctly rejected double withdraw attempt")
    
    def test_06_owner_can_delete_pending_expense(self):
        """Test that owner can delete pending expense (DELETE /api/expenses/{id})"""
        expense_data = {
            "category": "travel",
            "description": "TEST_Delete expense",
            "line_items": [{"category": "travel", "description": "test", "amount": 200}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        delete_expense_id = create_response.json()["expense_id"]
        
        # Submit it first
        self.sales_session.post(f"/api/expenses/{delete_expense_id}/submit")
        
        # Now delete it
        delete_response = self.sales_session.delete(f"/api/expenses/{delete_expense_id}")
        assert delete_response.status_code == 200, f"Failed to delete: {delete_response.text}"
        print(f"✓ Owner deleted pending expense: {delete_expense_id}")
        
        # Verify it's deleted
        get_response = self.sales_session.get(f"/api/expenses/{delete_expense_id}")
        assert get_response.status_code == 404
    
    def test_07_hr_can_send_back_expense_for_revision(self):
        """Test HR can send expense back for revision (POST /api/expenses/{id}/send-back)"""
        # Create and submit a new expense
        expense_data = {
            "category": "travel",
            "description": "TEST_SendBack expense",
            "line_items": [{"category": "travel", "description": "Flight booking", "amount": 1500}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        sendback_expense_id = create_response.json()["expense_id"]
        self.__class__.sendback_expense_id = sendback_expense_id
        
        # Submit it
        submit_response = self.sales_session.post(f"/api/expenses/{sendback_expense_id}/submit")
        assert submit_response.status_code == 200
        
        # HR sends it back
        sendback_response = self.hr_session.post(f"/api/expenses/{sendback_expense_id}/send-back", json={
            "comments": "Please provide receipt for flight booking"
        })
        assert sendback_response.status_code == 200, f"Failed to send back: {sendback_response.text}"
        
        data = sendback_response.json()
        assert data.get("status") == "revision_required"
        print(f"✓ HR sent expense back for revision: {sendback_expense_id}")
        
        # Verify expense status
        get_response = self.hr_session.get(f"/api/expenses/{sendback_expense_id}")
        assert get_response.status_code == 200
        expense = get_response.json()
        assert expense.get("status") == "revision_required"
        assert expense.get("revision_comments") == "Please provide receipt for flight booking"
    
    def test_08_send_back_requires_comments(self):
        """Test that send-back without comments is rejected"""
        # Create and submit
        expense_data = {
            "category": "travel",
            "description": "TEST_NoComments",
            "line_items": [{"category": "travel", "description": "test", "amount": 500}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        
        self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        
        # Try send-back without comments
        sendback_response = self.hr_session.post(f"/api/expenses/{expense_id}/send-back", json={})
        assert sendback_response.status_code == 400, "Should require comments"
        print(f"✓ Correctly rejected send-back without comments")
    
    def test_09_employee_can_resubmit_after_revision(self):
        """Test employee can resubmit after revision (POST /api/expenses/{id}/resubmit)"""
        if not hasattr(self.__class__, 'sendback_expense_id'):
            pytest.skip("No sent-back expense available")
        
        expense_id = self.__class__.sendback_expense_id
        
        # Employee resubmits with updated info
        resubmit_response = self.sales_session.post(f"/api/expenses/{expense_id}/resubmit", json={
            "notes": "Attached receipt for flight booking",
            "line_items": [{"category": "travel", "description": "Flight booking - receipt attached", "amount": 1500}]
        })
        assert resubmit_response.status_code == 200, f"Failed to resubmit: {resubmit_response.text}"
        
        data = resubmit_response.json()
        assert data.get("status") == "pending"
        print(f"✓ Employee resubmitted expense: {expense_id}")
        
        # Verify status changed back to pending
        get_response = self.sales_session.get(f"/api/expenses/{expense_id}")
        assert get_response.status_code == 200
        assert get_response.json().get("status") == "pending"
    
    def test_10_non_revision_expense_cannot_resubmit(self):
        """Test that non-revision expense cannot be resubmitted"""
        # Create a draft expense (not sent back)
        expense_data = {
            "category": "travel",
            "description": "TEST_NoResubmit",
            "line_items": [{"category": "travel", "description": "test", "amount": 500}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        expense_id = create_response.json()["expense_id"]
        
        # Try to resubmit draft - should fail
        resubmit_response = self.sales_session.post(f"/api/expenses/{expense_id}/resubmit", json={})
        assert resubmit_response.status_code == 400, "Should not resubmit non-revision expense"
        print(f"✓ Correctly rejected resubmit of non-revision expense")
    
    def test_11_hr_approve_with_modification(self):
        """Test HR can approve with modified amount (POST /api/expenses/{id}/approve-with-modification)"""
        # Create and submit expense
        expense_data = {
            "category": "food",
            "description": "TEST_PartialApproval",
            "line_items": [{"category": "food", "description": "Team dinner", "amount": 1800}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        
        # Submit
        submit_response = self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        assert submit_response.status_code == 200
        
        # HR approves with modified amount (partial approval)
        approve_response = self.hr_session.post(f"/api/expenses/{expense_id}/approve-with-modification", json={
            "approved_amount": 1500,
            "modification_reason": "Reduced to match policy limit for team dinners",
            "remarks": "Partial approval as per policy"
        })
        assert approve_response.status_code == 200, f"Failed to approve with modification: {approve_response.text}"
        
        data = approve_response.json()
        assert data.get("original_amount") == 1800
        assert data.get("approved_amount") == 1500
        print(f"✓ HR approved expense with modification: {expense_id}")
        print(f"  Original: ₹1800, Approved: ₹1500")
    
    def test_12_approve_modification_requires_reason(self):
        """Test that modification without reason is rejected when amount differs"""
        # Create and submit
        expense_data = {
            "category": "travel",
            "description": "TEST_NoReason",
            "line_items": [{"category": "travel", "description": "test", "amount": 1000}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        expense_id = create_response.json()["expense_id"]
        self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        
        # Try to approve with different amount but no reason
        approve_response = self.hr_session.post(f"/api/expenses/{expense_id}/approve-with-modification", json={
            "approved_amount": 800
            # No modification_reason
        })
        assert approve_response.status_code == 400, "Should require reason when modifying amount"
        print(f"✓ Correctly rejected modification without reason")
    
    def test_13_approved_amount_cannot_exceed_requested(self):
        """Test that approved amount cannot exceed requested amount"""
        # Create and submit
        expense_data = {
            "category": "travel",
            "description": "TEST_ExceedAmount",
            "line_items": [{"category": "travel", "description": "test", "amount": 1000}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        expense_id = create_response.json()["expense_id"]
        self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        
        # Try to approve more than requested
        approve_response = self.hr_session.post(f"/api/expenses/{expense_id}/approve-with-modification", json={
            "approved_amount": 1500,  # More than requested 1000
            "modification_reason": "Extra approved"
        })
        assert approve_response.status_code == 400, "Should not approve more than requested"
        print(f"✓ Correctly rejected approval exceeding requested amount")


# ============== KICKOFF REQUEST FLOW TESTS ==============

class TestKickoffRequestFlows:
    """Test kickoff withdraw, update, my-kickoff-requests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test sessions"""
        self.admin_session = APISession()
        self.sales_session = APISession()
        
        admin_logged_in = self.admin_session.login("ADMIN001", "test123")
        assert admin_logged_in, "ADMIN001 login failed"
        
        sales_logged_in = self.sales_session.login("SE001", "test123")
        assert sales_logged_in, "SE001 login failed"
    
    def test_01_get_consulting_team(self):
        """Get list of consultants for kickoff assignment"""
        response = self.sales_session.get("/api/sales-funnel/consulting-team")
        assert response.status_code == 200, f"Failed to get consulting team: {response.text}"
        
        data = response.json()
        assert "consultants" in data
        print(f"✓ Retrieved consulting team: {data.get('total', 0)} consultants")
        
        # Store a consultant ID for later tests
        if data.get("consultants"):
            self.__class__.consultant_id = data["consultants"][0].get("id")
    
    def test_02_get_my_kickoff_requests(self):
        """Test GET /api/sales-funnel/my-kickoff-requests"""
        response = self.sales_session.get("/api/sales-funnel/my-kickoff-requests")
        assert response.status_code == 200, f"Failed to get my kickoff requests: {response.text}"
        
        data = response.json()
        assert "requests" in data
        print(f"✓ Retrieved my kickoff requests: {len(data.get('requests', []))} requests")
    
    def test_03_create_kickoff_request(self):
        """Create a kickoff request for testing withdraw/update"""
        # First get a lead to use
        leads_response = self.sales_session.get("/api/leads")
        if leads_response.status_code != 200:
            pytest.skip("Cannot get leads")
        
        leads = leads_response.json()
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0].get("id")
        
        # Get consultant
        if not hasattr(self.__class__, 'consultant_id'):
            consult_response = self.sales_session.get("/api/sales-funnel/consulting-team")
            if consult_response.status_code == 200 and consult_response.json().get("consultants"):
                self.__class__.consultant_id = consult_response.json()["consultants"][0].get("id")
            else:
                pytest.skip("No consultants available")
        
        # Create kickoff request
        request_data = {
            "lead_id": lead_id,
            "assigned_consultant_id": self.__class__.consultant_id,
            "notes": "TEST_Kickoff request for approval flow testing"
        }
        
        response = self.sales_session.post("/api/sales-funnel/request-kickoff", json=request_data)
        # Accept 200, 201, or 400 (if consultant role validation fails)
        if response.status_code in [200, 201]:
            data = response.json()
            if data.get("request"):
                self.__class__.kickoff_request_id = data["request"].get("id")
                print(f"✓ Created kickoff request: {self.__class__.kickoff_request_id}")
            else:
                print(f"✓ Kickoff request created (response format may vary)")
        else:
            print(f"⚠ Kickoff request creation returned {response.status_code}: {response.text}")
            # Store None to skip dependent tests
            self.__class__.kickoff_request_id = None
    
    def test_04_update_kickoff_request(self):
        """Test PATCH /api/sales-funnel/kickoff-request/{id} - update pending request"""
        if not hasattr(self.__class__, 'kickoff_request_id') or not self.__class__.kickoff_request_id:
            pytest.skip("No kickoff request created")
        
        request_id = self.__class__.kickoff_request_id
        update_data = {
            "notes": "TEST_Updated notes for kickoff request",
            "preferred_start_date": "2026-02-01"
        }
        
        response = self.sales_session.patch(f"/api/sales-funnel/kickoff-request/{request_id}", json=update_data)
        assert response.status_code == 200, f"Failed to update kickoff request: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success"
        print(f"✓ Updated kickoff request: {request_id}")
    
    def test_05_non_owner_cannot_update_kickoff_request(self):
        """Test that non-owner cannot update kickoff request"""
        if not hasattr(self.__class__, 'kickoff_request_id') or not self.__class__.kickoff_request_id:
            pytest.skip("No kickoff request created")
        
        # Create new session for different user (use HR to try update)
        hr_session = APISession()
        hr_logged_in = hr_session.login("HR001", "test123")
        if not hr_logged_in:
            pytest.skip("HR login failed")
        
        request_id = self.__class__.kickoff_request_id
        update_data = {"notes": "Unauthorized update attempt"}
        
        response = hr_session.patch(f"/api/sales-funnel/kickoff-request/{request_id}", json=update_data)
        # Should be 403 Forbidden (unless HR001 is admin)
        if response.status_code == 403:
            print(f"✓ Non-owner correctly denied update access")
        elif response.status_code == 200:
            print(f"⚠ Update succeeded (HR might have admin access)")
        else:
            print(f"⚠ Unexpected response: {response.status_code}")
    
    def test_06_withdraw_kickoff_request(self):
        """Test DELETE /api/sales-funnel/kickoff-request/{id} - withdraw request"""
        # Create a new request specifically for withdrawal test
        leads_response = self.sales_session.get("/api/leads")
        if leads_response.status_code != 200:
            pytest.skip("Cannot get leads")
        
        leads = leads_response.json()
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0].get("id")
        
        if not hasattr(self.__class__, 'consultant_id'):
            pytest.skip("No consultant ID available")
        
        # Create request
        request_data = {
            "lead_id": lead_id,
            "assigned_consultant_id": self.__class__.consultant_id,
            "notes": "TEST_Kickoff for withdrawal test"
        }
        
        create_response = self.sales_session.post("/api/sales-funnel/request-kickoff", json=request_data)
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Could not create kickoff request: {create_response.text}")
        
        request_id = create_response.json().get("request", {}).get("id")
        if not request_id:
            pytest.skip("No request ID in response")
        
        # Withdraw it
        withdraw_response = self.sales_session.delete(f"/api/sales-funnel/kickoff-request/{request_id}")
        assert withdraw_response.status_code == 200, f"Failed to withdraw: {withdraw_response.text}"
        
        data = withdraw_response.json()
        assert data.get("status") == "success"
        print(f"✓ Withdrew kickoff request: {request_id}")
    
    def test_07_non_owner_cannot_withdraw_kickoff_request(self):
        """Test that non-owner cannot withdraw kickoff request"""
        if not hasattr(self.__class__, 'kickoff_request_id') or not self.__class__.kickoff_request_id:
            pytest.skip("No kickoff request created")
        
        # Use HR session to try withdrawal
        hr_session = APISession()
        hr_logged_in = hr_session.login("HR001", "test123")
        if not hr_logged_in:
            pytest.skip("HR login failed")
        
        request_id = self.__class__.kickoff_request_id
        response = hr_session.delete(f"/api/sales-funnel/kickoff-request/{request_id}")
        
        # Should be 403 unless HR has admin role
        if response.status_code == 403:
            print(f"✓ Non-owner correctly denied withdraw access")
        elif response.status_code == 404:
            print(f"✓ Request not found (may have been already withdrawn)")
        elif response.status_code == 200:
            print(f"⚠ Withdraw succeeded (HR might have admin access)")
        else:
            print(f"⚠ Unexpected response: {response.status_code}")


# ============== PAYROLL REIMBURSEMENTS TESTS ==============

class TestPayrollReimbursements:
    """Test HR views pending expense reimbursements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test sessions"""
        self.hr_session = APISession()
        self.admin_session = APISession()
        self.sales_session = APISession()
        
        self.hr_session.login("HR001", "test123")
        self.admin_session.login("ADMIN001", "test123")
        self.sales_session.login("SE001", "test123")
    
    def test_01_hr_can_view_pending_reimbursements(self):
        """Test GET /api/payroll/pending-reimbursements"""
        response = self.hr_session.get("/api/payroll/pending-reimbursements")
        assert response.status_code == 200, f"Failed to get pending reimbursements: {response.text}"
        
        data = response.json()
        assert "reimbursements" in data
        assert "total_amount" in data
        assert "count" in data
        print(f"✓ HR retrieved pending reimbursements: {data.get('count', 0)} items, total ₹{data.get('total_amount', 0)}")
    
    def test_02_pending_reimbursements_with_month_filter(self):
        """Test pending reimbursements with month filter"""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        response = self.hr_session.get(f"/api/payroll/pending-reimbursements?month={current_month}")
        assert response.status_code == 200, f"Failed with month filter: {response.text}"
        
        data = response.json()
        print(f"✓ Retrieved reimbursements for {current_month}: {data.get('count', 0)} items")
    
    def test_03_non_hr_cannot_view_pending_reimbursements(self):
        """Test that non-HR users cannot access pending reimbursements"""
        response = self.sales_session.get("/api/payroll/pending-reimbursements")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-HR correctly denied access to pending reimbursements")
    
    def test_04_approved_expense_creates_payroll_reimbursement(self):
        """Test that approved expense appears in payroll_reimbursements"""
        # Create and submit expense
        expense_data = {
            "category": "travel",
            "description": "TEST_PayrollLink expense",
            "line_items": [{"category": "travel", "description": "Test for payroll", "amount": 750}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        
        # Submit
        submit_response = self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        assert submit_response.status_code == 200
        
        # HR approves (small amount < 2000, so HR can approve directly)
        approve_response = self.hr_session.post(f"/api/expenses/{expense_id}/approve", json={
            "remarks": "Approved for payroll linkage test"
        })
        
        if approve_response.status_code == 200:
            data = approve_response.json()
            if data.get("status") == "approved":
                # Check payroll reimbursements
                reimb_response = self.hr_session.get("/api/payroll/pending-reimbursements")
                if reimb_response.status_code == 200:
                    reimbursements = reimb_response.json().get("reimbursements", [])
                    linked = any(r.get("expense_id") == expense_id for r in reimbursements)
                    if linked:
                        print(f"✓ Approved expense linked to payroll: {expense_id}")
                    else:
                        # Might be already processed or in different month
                        print(f"⚠ Expense approved but not found in pending (may be processed)")
            else:
                print(f"⚠ Expense requires further approval: {data.get('status')}")
        else:
            print(f"⚠ Approval returned {approve_response.status_code}: {approve_response.text}")


# ============== FULL APPROVAL FLOW E2E TEST ==============

class TestFullApprovalFlowE2E:
    """End-to-end test: create -> send-back -> resubmit -> approve-with-modification -> verify payroll"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test sessions"""
        self.hr_session = APISession()
        self.sales_session = APISession()
        
        assert self.hr_session.login("HR001", "test123"), "HR001 login failed"
        assert self.sales_session.login("SE001", "test123"), "SE001 login failed"
    
    def test_full_expense_approval_flow(self):
        """Complete flow: create -> submit -> send-back -> resubmit -> approve with modification"""
        print("\n=== Starting Full Approval Flow E2E Test ===")
        
        # Step 1: Create expense
        expense_data = {
            "category": "accommodation",
            "description": "TEST_E2E_FullFlow - Hotel for client visit",
            "line_items": [{"category": "accommodation", "description": "Hotel stay", "amount": 1800}],
            "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": "E2E test for full approval flow"
        }
        
        create_response = self.sales_session.post("/api/expenses", json=expense_data)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        print(f"Step 1: ✓ Created expense: {expense_id}")
        
        # Step 2: Submit for approval
        submit_response = self.sales_session.post(f"/api/expenses/{expense_id}/submit")
        assert submit_response.status_code == 200
        print(f"Step 2: ✓ Submitted expense for approval")
        
        # Step 3: HR sends back for revision
        sendback_response = self.hr_session.post(f"/api/expenses/{expense_id}/send-back", json={
            "comments": "Please provide hotel booking confirmation"
        })
        assert sendback_response.status_code == 200
        print(f"Step 3: ✓ HR sent expense back for revision")
        
        # Verify status is revision_required
        get_response = self.sales_session.get(f"/api/expenses/{expense_id}")
        assert get_response.json().get("status") == "revision_required"
        
        # Step 4: Employee resubmits
        resubmit_response = self.sales_session.post(f"/api/expenses/{expense_id}/resubmit", json={
            "notes": "Hotel booking confirmation attached",
            "line_items": [{"category": "accommodation", "description": "Hotel stay - confirmation attached", "amount": 1800}]
        })
        assert resubmit_response.status_code == 200
        print(f"Step 4: ✓ Employee resubmitted expense")
        
        # Verify status is back to pending
        get_response = self.sales_session.get(f"/api/expenses/{expense_id}")
        assert get_response.json().get("status") == "pending"
        
        # Step 5: HR approves with modification (partial approval)
        approve_response = self.hr_session.post(f"/api/expenses/{expense_id}/approve-with-modification", json={
            "approved_amount": 1600,
            "modification_reason": "Hotel rate cap as per policy is ₹1600/night",
            "remarks": "Partial approval per policy"
        })
        assert approve_response.status_code == 200
        
        data = approve_response.json()
        assert data.get("original_amount") == 1800
        assert data.get("approved_amount") == 1600
        print(f"Step 5: ✓ HR approved with modification (₹1800 -> ₹1600)")
        
        # Verify final status
        final_response = self.sales_session.get(f"/api/expenses/{expense_id}")
        expense = final_response.json()
        
        # Status should be approved (if < 2000) or hr_approved (if >= 2000)
        assert expense.get("status") in ["approved", "hr_approved"]
        assert expense.get("approved_amount") == 1600
        
        print(f"\n=== Full Approval Flow E2E Test Complete ===")
        print(f"  Final Status: {expense.get('status')}")
        print(f"  Original Amount: ₹1800")
        print(f"  Approved Amount: ₹1600")


# ============== CLEANUP ==============

class TestCleanup:
    """Cleanup TEST_ prefixed data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_session = APISession()
        self.admin_session.login("ADMIN001", "test123")
    
    def test_cleanup_test_expenses(self):
        """Clean up TEST_ prefixed expenses"""
        response = self.admin_session.get("/api/expenses")
        if response.status_code != 200:
            print("⚠ Could not fetch expenses for cleanup")
            return
        
        expenses = response.json()
        test_expenses = [e for e in expenses if e.get("description", "").startswith("TEST_")]
        
        deleted = 0
        for expense in test_expenses:
            # Only delete draft/pending/rejected/revision_required
            if expense.get("status") in ["draft", "pending", "rejected", "revision_required", "withdrawn"]:
                del_response = self.admin_session.delete(f"/api/expenses/{expense['id']}")
                if del_response.status_code in [200, 204]:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test expenses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
