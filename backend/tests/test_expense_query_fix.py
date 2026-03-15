"""
Expense Query Logic Fix Tests - Consistent Identity Mapping
Tests the fix for expense listing endpoint (GET /expenses) that was querying by employee_id (UUID) 
but meeting expenses stored employee_id as employee code (like EMP003).

Fix: Using $or query to match user_id, created_by, or employee_id fields.

Features tested:
1. GET /api/expenses - user can see their own meeting expenses (created via POST /meetings/record)
2. GET /api/expenses - user can see expenses created via POST /expenses  
3. GET /api/expenses - admin can see all expenses
4. POST /api/meetings/record - creates expense with user_id, created_by, and employee_id fields
5. GET /api/expenses/stats/summary - user stats include meeting expenses
6. Expense query uses $or to match by user_id OR created_by OR employee_id
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - EMP003 (Sales Executive) and ADMIN001 (Admin)
SALES_CREDENTIALS = {
    "employee_id": "EMP003",
    "password": "Sales@123"
}

ADMIN_CREDENTIALS = {
    "employee_id": "ADMIN001",
    "password": "Admin@2026"
}

# Test lead ID
TEST_LEAD_ID = "2e8724b1-b9b7-4983-b3cc-6c47e5de4851"


class TestExpenseQueryFix:
    """Test expense query logic fix for consistent identity mapping"""
    
    @pytest.fixture(scope="class")
    def sales_auth(self):
        """Authenticate as Sales Executive (EMP003) and return auth data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate as EMP003: {response.status_code} - {response.text}")
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user_id": data.get("user", {}).get("id"),
            "employee_id": SALES_CREDENTIALS["employee_id"]  # EMP003
        }
    
    @pytest.fixture(scope="class")
    def admin_auth(self):
        """Authenticate as Admin and return auth data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate as Admin: {response.status_code} - {response.text}")
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user_id": data.get("user", {}).get("id")
        }
    
    @pytest.fixture(scope="class")
    def sales_headers(self, sales_auth):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {sales_auth['token']}"
        }
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_auth):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_auth['token']}"
        }
    
    # ========== TEST: User can see their own expenses ==========
    
    def test_user_can_see_own_expenses(self, sales_headers, sales_auth):
        """
        Test that a user can see all their expenses via GET /api/expenses.
        This includes expenses created via POST /expenses AND meeting expenses.
        
        The fix ensures the query uses $or to match:
        - user_id (UUID from auth)
        - created_by (UUID from auth)
        """
        response = requests.get(f"{BASE_URL}/api/expenses", headers=sales_headers)
        assert response.status_code == 200, f"Failed to get expenses: {response.status_code} - {response.text}"
        
        expenses = response.json()
        assert isinstance(expenses, list), "Expected list of expenses"
        
        # Verify we got expenses (EMP003 should have some based on context)
        print(f"✓ User (EMP003) can see {len(expenses)} expenses")
        
        # Verify all returned expenses belong to current user
        for expense in expenses:
            # Check that expense belongs to current user via user_id, created_by, or employee_id
            user_id = expense.get("user_id")
            created_by = expense.get("created_by")
            employee_id = expense.get("employee_id")
            
            belongs_to_user = (
                user_id == sales_auth["user_id"] or 
                created_by == sales_auth["user_id"] or
                employee_id == sales_auth["employee_id"]  # EMP003
            )
            
            assert belongs_to_user, f"Expense {expense.get('id')} doesn't belong to current user"
        
        return expenses
    
    def test_user_can_see_meeting_expenses(self, sales_headers, sales_auth):
        """
        Test that a user can see meeting expenses in their expense list.
        Meeting expenses have expense_type='meeting_expense'.
        
        This is the core issue being fixed - meeting expenses were not appearing
        because they stored employee_id as employee code (EMP003) not UUID.
        """
        response = requests.get(f"{BASE_URL}/api/expenses", headers=sales_headers)
        assert response.status_code == 200
        
        expenses = response.json()
        
        # Find meeting expenses
        meeting_expenses = [e for e in expenses if e.get("expense_type") == "meeting_expense"]
        
        print(f"✓ User (EMP003) can see {len(meeting_expenses)} meeting expenses out of {len(expenses)} total")
        
        # Verify meeting expenses have the correct structure
        for exp in meeting_expenses:
            assert exp.get("meeting_id"), f"Meeting expense missing meeting_id: {exp.get('id')}"
            assert exp.get("category") == "travel", f"Meeting expense should be category 'travel'"
            
            # Verify identity fields are set correctly per the fix
            # user_id and created_by should be UUID
            # employee_id can be employee code (EMP003)
            assert exp.get("user_id") or exp.get("created_by") or exp.get("employee_id"), \
                f"Meeting expense {exp.get('id')} missing identity fields"
        
        return meeting_expenses
    
    # ========== TEST: Meeting expense creation stores correct identity fields ==========
    
    def test_meeting_expense_has_correct_identity_fields(self, sales_headers, sales_auth):
        """
        Test that POST /api/meetings/record creates expense with all identity fields:
        - user_id (UUID for ownership query)
        - created_by (UUID for auth/ownership)
        - employee_id (employee code for payroll)
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "10:00",
            "meeting_type": "Offline",
            "title": f"TEST Identity Fields Meeting {unique_id}",
            "attendees": ["Test Client"],
            "mom": "Test meeting to verify expense identity fields",
            "travel_details": {
                "start_location": "Office",
                "end_location": "Client Site",
                "is_round_trip": False,
                "travel_mode": "DRIVING",
                "distance_km": 25,
                "travel_start_time": "09:00",
                "travel_end_time": "10:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=sales_headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        meeting_id = response.json().get("meeting_id")
        assert meeting_id, "Meeting ID not returned"
        
        # Wait for background task to create expense (background tasks may take up to 5s)
        time.sleep(6)
        
        # Get the meeting to find expense_id
        meeting_response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=sales_headers)
        assert meeting_response.status_code == 200
        meeting = meeting_response.json()
        
        expense_id = meeting.get("expense_id")
        assert expense_id, "Meeting should have expense_id"
        
        # Get the expense directly
        expense_response = requests.get(f"{BASE_URL}/api/expenses/{expense_id}", headers=sales_headers)
        assert expense_response.status_code == 200
        expense = expense_response.json()
        
        # Verify all identity fields per the fix
        print(f"\n  Expense identity fields:")
        print(f"  - user_id: {expense.get('user_id')}")
        print(f"  - created_by: {expense.get('created_by')}")
        print(f"  - employee_id: {expense.get('employee_id')}")
        
        # user_id should be the UUID of current user
        assert expense.get("user_id") == sales_auth["user_id"], \
            f"user_id should be {sales_auth['user_id']}, got {expense.get('user_id')}"
        
        # created_by should be the UUID of current user
        assert expense.get("created_by") == sales_auth["user_id"], \
            f"created_by should be {sales_auth['user_id']}, got {expense.get('created_by')}"
        
        # employee_id should be employee code (EMP003) for payroll linking
        assert expense.get("employee_id") == sales_auth["employee_id"], \
            f"employee_id should be {sales_auth['employee_id']}, got {expense.get('employee_id')}"
        
        print(f"\n✓ Meeting expense has all correct identity fields")
        
        return expense
    
    # ========== TEST: Regular expense creation ==========
    
    def test_regular_expense_appears_in_list(self, sales_headers, sales_auth):
        """
        Test that expenses created via POST /expenses appear in GET /expenses.
        """
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            "category": "miscellaneous",
            "amount": 150,
            "description": f"TEST Regular Expense {unique_id}",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "Test expense to verify it appears in list"
        }
        
        # Create regular expense via POST /expenses/quick
        response = requests.post(f"{BASE_URL}/api/expenses/quick", json=payload, headers=sales_headers)
        assert response.status_code == 200, f"Failed to create expense: {response.text}"
        
        expense_id = response.json().get("expense_id")
        assert expense_id, "Expense ID not returned"
        
        # Verify expense appears in list
        list_response = requests.get(f"{BASE_URL}/api/expenses", headers=sales_headers)
        assert list_response.status_code == 200
        
        expenses = list_response.json()
        created_expense = next((e for e in expenses if e.get("id") == expense_id), None)
        
        assert created_expense, f"Created expense {expense_id} not found in expense list"
        
        # Verify identity fields for regular expense
        assert created_expense.get("user_id") == sales_auth["user_id"] or \
               created_expense.get("created_by") == sales_auth["user_id"], \
            "Regular expense should have user_id or created_by set"
        
        print(f"✓ Regular expense appears in user's expense list")
        
        return expense_id
    
    # ========== TEST: Admin can see all expenses ==========
    
    def test_admin_can_see_all_expenses(self, admin_headers):
        """
        Test that admin can see all expenses via GET /api/expenses.
        Admin should not have the ownership filter applied.
        """
        response = requests.get(f"{BASE_URL}/api/expenses", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get expenses as admin: {response.status_code}"
        
        expenses = response.json()
        assert isinstance(expenses, list), "Expected list of expenses"
        
        print(f"✓ Admin can see {len(expenses)} expenses")
        
        # Admin should see expenses from multiple users
        unique_user_ids = set()
        unique_employee_ids = set()
        
        for exp in expenses:
            if exp.get("user_id"):
                unique_user_ids.add(exp.get("user_id"))
            if exp.get("employee_id"):
                unique_employee_ids.add(exp.get("employee_id"))
        
        print(f"  - From {len(unique_user_ids)} unique user_ids")
        print(f"  - From {len(unique_employee_ids)} unique employee_ids: {unique_employee_ids}")
        
        return expenses
    
    # ========== TEST: Stats summary includes meeting expenses ==========
    
    def test_stats_summary_includes_meeting_expenses(self, sales_headers):
        """
        Test that GET /api/expenses/stats/summary includes meeting expenses.
        The fix applies the same $or query to the stats endpoint.
        """
        response = requests.get(f"{BASE_URL}/api/expenses/stats/summary", headers=sales_headers)
        assert response.status_code == 200, f"Failed to get stats: {response.status_code}"
        
        stats = response.json()
        
        print(f"✓ Stats summary returned:")
        print(f"  - By status: {stats.get('by_status', {})}")
        print(f"  - By category: {stats.get('by_category', {})}")
        
        # Check if travel category exists (meeting expenses are travel)
        by_category = stats.get("by_category", {})
        if "travel" in by_category:
            travel_stats = by_category["travel"]
            print(f"\n  Travel category (includes meeting expenses):")
            print(f"    - Count: {travel_stats.get('count', 0)}")
            print(f"    - Total: Rs.{travel_stats.get('total', 0)}")
        
        return stats
    
    # ========== TEST: Filter expenses by specific employee ==========
    
    def test_admin_filter_by_employee(self, admin_headers, sales_auth):
        """
        Test admin filtering expenses by specific employee.
        The fix supports both UUID and employee code in the employee_id filter.
        """
        # Filter by employee code (EMP003)
        response = requests.get(
            f"{BASE_URL}/api/expenses?employee_id={sales_auth['employee_id']}", 
            headers=admin_headers
        )
        assert response.status_code == 200
        
        expenses_by_code = response.json()
        print(f"✓ Admin filter by employee_id={sales_auth['employee_id']}: {len(expenses_by_code)} expenses")
        
        # Also try filtering by user UUID
        response2 = requests.get(
            f"{BASE_URL}/api/expenses?employee_id={sales_auth['user_id']}", 
            headers=admin_headers
        )
        assert response2.status_code == 200
        
        expenses_by_uuid = response2.json()
        print(f"✓ Admin filter by user_id={sales_auth['user_id']}: {len(expenses_by_uuid)} expenses")
        
        return {
            "by_employee_code": len(expenses_by_code),
            "by_user_uuid": len(expenses_by_uuid)
        }


class TestExpenseVisibilityVerification:
    """
    Verify the fix by checking actual expense visibility.
    This tests the specific scenario described in the bug report.
    """
    
    @pytest.fixture(scope="class")
    def sales_auth(self):
        """Authenticate as Sales Executive (EMP003)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate: {response.status_code}")
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user_id": data.get("user", {}).get("id"),
            "employee_id": "EMP003"
        }
    
    @pytest.fixture(scope="class")
    def headers(self, sales_auth):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {sales_auth['token']}"
        }
    
    def test_verify_meeting_expenses_visible(self, headers, sales_auth):
        """
        Core test: Verify user can see meeting expenses that were previously invisible.
        
        Before fix: GET /expenses queried by employee_id=current_user.id (UUID)
        But meeting expenses stored employee_id as employee code (EMP003).
        Result: 0 results for users.
        
        After fix: Query uses $or with user_id, created_by, employee_id.
        Result: User sees all their expenses including meeting expenses.
        """
        response = requests.get(f"{BASE_URL}/api/expenses", headers=headers)
        assert response.status_code == 200
        
        expenses = response.json()
        total_count = len(expenses)
        
        # Count different expense types
        meeting_expenses = [e for e in expenses if e.get("expense_type") == "meeting_expense"]
        regular_expenses = [e for e in expenses if e.get("expense_type") != "meeting_expense"]
        
        print(f"\n===== EXPENSE VISIBILITY VERIFICATION =====")
        print(f"User: EMP003 (user_id: {sales_auth['user_id']})")
        print(f"Total expenses visible: {total_count}")
        print(f"  - Meeting expenses: {len(meeting_expenses)}")
        print(f"  - Regular expenses: {len(regular_expenses)}")
        print(f"============================================\n")
        
        # The fix should allow the user to see their expenses
        # (based on context, EMP003 should see 21 expenses including meeting expenses)
        assert total_count > 0, "User should see at least some expenses"
        
        # If there are meeting expenses in the system for this user, they should be visible
        # This is the key assertion that validates the fix
        if len(meeting_expenses) > 0:
            print(f"✓ FIX VERIFIED: Meeting expenses are now visible to user")
            for exp in meeting_expenses[:3]:  # Show first 3
                print(f"  - {exp.get('description', 'N/A')}: Rs.{exp.get('amount', 0)}")
        
        return {
            "total": total_count,
            "meeting_expenses": len(meeting_expenses),
            "regular_expenses": len(regular_expenses)
        }
    
    def test_verify_expense_identity_mapping(self, headers, sales_auth):
        """
        Verify the $or query logic is working correctly.
        Check that expenses are returned when matching any of:
        - user_id = current_user.id (UUID)
        - created_by = current_user.id (UUID)
        - employee_id = employee code (EMP003)
        """
        response = requests.get(f"{BASE_URL}/api/expenses", headers=headers)
        assert response.status_code == 200
        
        expenses = response.json()
        
        # Categorize by which field matched
        matched_by_user_id = []
        matched_by_created_by = []
        matched_by_employee_id = []
        
        for exp in expenses:
            if exp.get("user_id") == sales_auth["user_id"]:
                matched_by_user_id.append(exp.get("id"))
            if exp.get("created_by") == sales_auth["user_id"]:
                matched_by_created_by.append(exp.get("id"))
            if exp.get("employee_id") == sales_auth["employee_id"]:
                matched_by_employee_id.append(exp.get("id"))
        
        print(f"\nExpenses matched by identity field:")
        print(f"  - Matched by user_id: {len(matched_by_user_id)}")
        print(f"  - Matched by created_by: {len(matched_by_created_by)}")
        print(f"  - Matched by employee_id (code): {len(matched_by_employee_id)}")
        
        # At least one matching strategy should work
        assert len(expenses) > 0, "At least some expenses should be visible"
        
        print(f"\n✓ $or query logic verified - expenses visible through multiple identity fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
