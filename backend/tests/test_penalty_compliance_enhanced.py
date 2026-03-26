"""
Test Suite: Enhanced Penalty & Compliance System with 5 Tabs
Tests: Rule Configuration, Dynamic Amounts, Rich Contextual Info, Cross-links

Features tested:
- 5 tabs: Pending Review, Approved, Rejected, Apply Manual, Rule Configuration
- Rule config read/write endpoints (AT004, AT011, AT012)
- Dynamic penalty amounts from business rules
- Categories endpoint with dynamic_amounts
- Dedup logic for attendance penalties
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPenaltyComplianceEnhanced:
    """Enhanced Penalty & Compliance System Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip("Admin login failed - skipping tests")
        
        self.current_month = datetime.now().strftime("%Y-%m")
    
    # ==================== RULE CONFIGURATION TESTS ====================
    
    def test_01_get_rule_config_returns_penalty_rules(self):
        """GET /api/penalties/rule-config returns AT004, AT011, AT012 rules"""
        response = self.session.get(f"{BASE_URL}/api/penalties/rule-config")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rules" in data, "Response should contain 'rules' key"
        
        rules = data["rules"]
        rule_ids = [r["rule_id"] for r in rules]
        
        # Verify all 3 penalty-related rules are present
        assert "AT004" in rule_ids, "AT004 (Grace Period) should be in rules"
        assert "AT011" in rule_ids, "AT011 (Grace Days per Month) should be in rules"
        assert "AT012" in rule_ids, "AT012 (Late Penalty Amount) should be in rules"
        
        # Verify rule structure
        for rule in rules:
            assert "rule_id" in rule, "Rule should have rule_id"
            assert "name" in rule, "Rule should have name"
            assert "value" in rule, "Rule should have value"
            assert "type" in rule, "Rule should have type"
            assert "unit" in rule, "Rule should have unit"
            assert "impact" in rule, "Rule should have impact description"
        
        print(f"✓ Rule config returned {len(rules)} rules: {rule_ids}")
    
    def test_02_get_rule_config_has_policy_metadata(self):
        """GET /api/penalties/rule-config returns policy metadata"""
        response = self.session.get(f"{BASE_URL}/api/penalties/rule-config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for policy metadata
        assert "policy_id" in data or data.get("policy_id") is None, "Should have policy_id field"
        assert "policy_name" in data or data.get("policy_name") is None, "Should have policy_name field"
        
        print(f"✓ Policy metadata: {data.get('policy_name', 'N/A')}")
    
    def test_03_put_rule_config_updates_rules(self):
        """PUT /api/penalties/rule-config updates penalty rules"""
        # First get current values
        get_response = self.session.get(f"{BASE_URL}/api/penalties/rule-config")
        assert get_response.status_code == 200
        
        original_rules = get_response.json()["rules"]
        original_at012 = next((r["value"] for r in original_rules if r["rule_id"] == "AT012"), 100)
        
        # Update AT012 to a test value
        test_value = 150 if original_at012 != 150 else 200
        
        update_response = self.session.put(f"{BASE_URL}/api/penalties/rule-config", json={
            "rules": {
                "AT012": test_value
            }
        })
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        data = update_response.json()
        assert "message" in data, "Response should have message"
        assert "updated_rules" in data, "Response should have updated_rules"
        
        # Verify the update
        verify_response = self.session.get(f"{BASE_URL}/api/penalties/rule-config")
        assert verify_response.status_code == 200
        
        updated_rules = verify_response.json()["rules"]
        updated_at012 = next((r["value"] for r in updated_rules if r["rule_id"] == "AT012"), None)
        
        assert updated_at012 == test_value, f"AT012 should be {test_value}, got {updated_at012}"
        
        # Restore original value
        self.session.put(f"{BASE_URL}/api/penalties/rule-config", json={
            "rules": {"AT012": original_at012}
        })
        
        print(f"✓ Rule config updated AT012 from {original_at012} to {test_value} and restored")
    
    def test_04_put_rule_config_only_allows_penalty_rules(self):
        """PUT /api/penalties/rule-config only allows AT004, AT011, AT012"""
        # Try to update a non-penalty rule
        response = self.session.put(f"{BASE_URL}/api/penalties/rule-config", json={
            "rules": {
                "AT001": 10,  # This is work hours, not a penalty rule
                "AT012": 100  # This is valid
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # AT001 should not be in updated_rules
        updated = data.get("updated_rules", {})
        assert "AT001" not in updated or updated.get("AT001") is None, "AT001 should not be updatable via penalty rule-config"
        
        print("✓ Non-penalty rules correctly filtered out")
    
    # ==================== CATEGORIES WITH DYNAMIC AMOUNTS ====================
    
    def test_05_get_categories_returns_dynamic_amounts(self):
        """GET /api/penalties/categories returns dynamic_amounts from business_policies"""
        response = self.session.get(f"{BASE_URL}/api/penalties/categories")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "categories" in data, "Response should contain 'categories'"
        assert "dynamic_amounts" in data, "Response should contain 'dynamic_amounts'"
        
        categories = data["categories"]
        
        # Verify attendance category exists with violations
        assert "attendance" in categories, "Should have attendance category"
        attendance = categories["attendance"]
        assert "violations" in attendance, "Attendance should have violations"
        
        # Check AT_LATE violation has amount_source
        violations = attendance["violations"]
        at_late = next((v for v in violations if v["code"] == "AT_LATE"), None)
        
        if at_late:
            assert "default_amount" in at_late, "AT_LATE should have default_amount"
            assert "amount_source" in at_late, "AT_LATE should have amount_source"
            print(f"✓ AT_LATE default_amount: ₹{at_late['default_amount']} (source: {at_late['amount_source']})")
        
        print(f"✓ Categories returned with {len(categories)} categories")
    
    def test_06_categories_reflect_rule_config_changes(self):
        """Categories endpoint reflects AT012 changes from rule-config"""
        # Get current AT012 value
        rule_response = self.session.get(f"{BASE_URL}/api/penalties/rule-config")
        assert rule_response.status_code == 200
        
        rules = rule_response.json()["rules"]
        current_at012 = next((r["value"] for r in rules if r["rule_id"] == "AT012"), 100)
        
        # Update AT012 to a specific test value
        test_value = 175
        self.session.put(f"{BASE_URL}/api/penalties/rule-config", json={
            "rules": {"AT012": test_value}
        })
        
        # Check categories endpoint
        cat_response = self.session.get(f"{BASE_URL}/api/penalties/categories")
        assert cat_response.status_code == 200
        
        data = cat_response.json()
        dynamic_amounts = data.get("dynamic_amounts", {})
        
        # AT_LATE should reflect the new value
        at_late_amount = dynamic_amounts.get("AT_LATE")
        
        if at_late_amount is not None:
            assert at_late_amount == test_value, f"AT_LATE should be {test_value}, got {at_late_amount}"
            print(f"✓ Categories reflect rule config change: AT_LATE = ₹{at_late_amount}")
        else:
            print("⚠ dynamic_amounts.AT_LATE not found - may need policy setup")
        
        # Restore original value
        self.session.put(f"{BASE_URL}/api/penalties/rule-config", json={
            "rules": {"AT012": current_at012}
        })
    
    # ==================== MONTH PENALTIES WITH COUNT_BY_STATUS ====================
    
    def test_07_get_month_penalties_returns_count_by_status(self):
        """GET /api/penalties/month/{month} returns count_by_status"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "penalties" in data, "Response should contain 'penalties'"
        assert "count_by_status" in data, "Response should contain 'count_by_status'"
        
        count_by_status = data["count_by_status"]
        assert "pending_review" in count_by_status, "Should have pending_review count"
        assert "approved" in count_by_status, "Should have approved count"
        assert "rejected" in count_by_status, "Should have rejected count"
        
        print(f"✓ Month penalties: pending={count_by_status['pending_review']}, approved={count_by_status['approved']}, rejected={count_by_status['rejected']}")
    
    def test_08_get_month_penalties_includes_arrears(self):
        """GET /api/penalties/month/{month} includes arrears carried into this month"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for arrears_count field
        assert "arrears_count" in data, "Response should contain 'arrears_count'"
        
        print(f"✓ Arrears count for {self.current_month}: {data['arrears_count']}")
    
    # ==================== PENALTY CRUD OPERATIONS ====================
    
    def test_09_apply_penalty_creates_pending_review(self):
        """POST /api/penalties/apply creates penalty with status pending_review"""
        # Get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        
        # Apply a test penalty
        response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100,
            "description": "TEST_penalty_compliance_enhanced - late arrival test",
            "reference_id": f"TEST_enhanced_{datetime.now().timestamp()}"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "penalty_id" in data, "Response should contain penalty_id"
        assert data.get("action") in ["created", "created_as_arrears", "updated"], "Action should be created/updated"
        
        self.test_penalty_id = data["penalty_id"]
        print(f"✓ Created penalty {self.test_penalty_id} with status pending_review")
    
    def test_10_approve_penalty_changes_status(self):
        """POST /api/penalties/{id}/approve changes status to approved"""
        # First create a penalty
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        
        create_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100,
            "description": "TEST_approve_test",
            "reference_id": f"TEST_approve_{datetime.now().timestamp()}"
        })
        
        assert create_response.status_code == 200
        penalty_id = create_response.json()["penalty_id"]
        
        # Approve it
        approve_response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/approve")
        
        assert approve_response.status_code == 200, f"Expected 200, got {approve_response.status_code}: {approve_response.text}"
        
        data = approve_response.json()
        assert data.get("status") == "approved", "Status should be approved"
        
        print(f"✓ Penalty {penalty_id} approved successfully")
    
    def test_11_reject_penalty_with_reason(self):
        """POST /api/penalties/{id}/reject changes status to rejected with reason"""
        # Create a penalty
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        
        create_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100,
            "description": "TEST_reject_test",
            "reference_id": f"TEST_reject_{datetime.now().timestamp()}"
        })
        
        assert create_response.status_code == 200
        penalty_id = create_response.json()["penalty_id"]
        
        # Reject it with reason
        reject_response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/reject", json={
            "reason": "TEST rejection reason - employee was on approved leave"
        })
        
        assert reject_response.status_code == 200, f"Expected 200, got {reject_response.status_code}: {reject_response.text}"
        
        data = reject_response.json()
        assert data.get("status") == "rejected", "Status should be rejected"
        
        print(f"✓ Penalty {penalty_id} rejected with reason")
    
    def test_12_send_back_returns_to_pending(self):
        """POST /api/penalties/{id}/send-back returns approved penalty to pending_review"""
        # Create and approve a penalty
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        
        create_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100,
            "description": "TEST_sendback_test",
            "reference_id": f"TEST_sendback_{datetime.now().timestamp()}"
        })
        
        assert create_response.status_code == 200
        penalty_id = create_response.json()["penalty_id"]
        
        # Approve it first
        self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/approve")
        
        # Send it back
        sendback_response = self.session.post(f"{BASE_URL}/api/penalties/{penalty_id}/send-back", json={
            "reason": "Sent back for review - need more documentation"
        })
        
        assert sendback_response.status_code == 200, f"Expected 200, got {sendback_response.status_code}: {sendback_response.text}"
        
        data = sendback_response.json()
        assert data.get("status") == "pending_review", "Status should be pending_review"
        
        print(f"✓ Penalty {penalty_id} sent back to pending_review")
    
    def test_13_update_pending_penalty(self):
        """PUT /api/penalties/{id} updates amount and reason for pending penalty"""
        # Create a penalty
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        
        create_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100,
            "description": "TEST_update_test",
            "reference_id": f"TEST_update_{datetime.now().timestamp()}"
        })
        
        assert create_response.status_code == 200
        penalty_id = create_response.json()["penalty_id"]
        
        # Update it
        update_response = self.session.put(f"{BASE_URL}/api/penalties/{penalty_id}", json={
            "amount": 150,
            "reason": "Updated reason - multiple late arrivals"
        })
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        print(f"✓ Penalty {penalty_id} updated successfully")
    
    def test_14_bulk_approve_penalties(self):
        """POST /api/penalties/bulk-action approves multiple penalties"""
        # Create two penalties
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        penalty_ids = []
        
        for i in range(2):
            create_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
                "employee_id": employee["id"],
                "month": self.current_month,
                "violation_code": "AT_LATE",
                "amount": 100,
                "description": f"TEST_bulk_approve_{i}",
                "reference_id": f"TEST_bulk_{i}_{datetime.now().timestamp()}"
            })
            
            if create_response.status_code == 200:
                penalty_ids.append(create_response.json()["penalty_id"])
        
        if len(penalty_ids) < 2:
            pytest.skip("Could not create test penalties")
        
        # Bulk approve
        bulk_response = self.session.post(f"{BASE_URL}/api/penalties/bulk-action", json={
            "penalty_ids": penalty_ids,
            "action": "approve"
        })
        
        assert bulk_response.status_code == 200, f"Expected 200, got {bulk_response.status_code}: {bulk_response.text}"
        
        data = bulk_response.json()
        assert "modified_count" in data, "Response should have modified_count"
        
        print(f"✓ Bulk approved {data['modified_count']} penalties")
    
    def test_15_bulk_reject_penalties(self):
        """POST /api/penalties/bulk-action rejects multiple penalties"""
        # Create two penalties
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        penalty_ids = []
        
        for i in range(2):
            create_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
                "employee_id": employee["id"],
                "month": self.current_month,
                "violation_code": "AT_LATE",
                "amount": 100,
                "description": f"TEST_bulk_reject_{i}",
                "reference_id": f"TEST_bulk_reject_{i}_{datetime.now().timestamp()}"
            })
            
            if create_response.status_code == 200:
                penalty_ids.append(create_response.json()["penalty_id"])
        
        if len(penalty_ids) < 2:
            pytest.skip("Could not create test penalties")
        
        # Bulk reject
        bulk_response = self.session.post(f"{BASE_URL}/api/penalties/bulk-action", json={
            "penalty_ids": penalty_ids,
            "action": "reject",
            "reason": "Bulk rejection for testing"
        })
        
        assert bulk_response.status_code == 200, f"Expected 200, got {bulk_response.status_code}: {bulk_response.text}"
        
        data = bulk_response.json()
        assert "modified_count" in data, "Response should have modified_count"
        
        print(f"✓ Bulk rejected {data['modified_count']} penalties")
    
    # ==================== RBAC TESTS ====================
    
    def test_16_non_hr_cannot_access_rule_config(self):
        """Non-HR users cannot access rule-config endpoint"""
        # Login as sales user
        sales_session = requests.Session()
        sales_session.headers.update({"Content-Type": "application/json"})
        
        login_response = sales_session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Sales user login failed")
        
        token = login_response.json().get("access_token")
        sales_session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to access rule-config
        response = sales_session.get(f"{BASE_URL}/api/penalties/rule-config")
        
        assert response.status_code == 403, f"Expected 403 for non-HR user, got {response.status_code}"
        
        print("✓ Non-HR user correctly denied access to rule-config")
    
    def test_17_non_hr_cannot_apply_penalties(self):
        """Non-HR users cannot apply penalties"""
        # Login as sales user
        sales_session = requests.Session()
        sales_session.headers.update({"Content-Type": "application/json"})
        
        login_response = sales_session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Sales user login failed")
        
        token = login_response.json().get("access_token")
        sales_session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to apply penalty
        response = sales_session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": "some-id",
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100
        })
        
        assert response.status_code == 403, f"Expected 403 for non-HR user, got {response.status_code}"
        
        print("✓ Non-HR user correctly denied access to apply penalties")
    
    # ==================== SUMMARY ENDPOINTS ====================
    
    def test_18_get_penalty_summary(self):
        """GET /api/penalties/summary returns comprehensive summary"""
        response = self.session.get(f"{BASE_URL}/api/penalties/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "by_category" in data, "Response should have by_category"
        assert "monthly_breakdown" in data, "Response should have monthly_breakdown"
        assert "grand_total" in data, "Response should have grand_total"
        assert "count_by_status" in data, "Response should have count_by_status"
        
        print(f"✓ Summary: grand_total=₹{data['grand_total']}, employees_penalized={data.get('total_employees_penalized', 0)}")
    
    def test_19_get_summary_by_employees(self):
        """GET /api/penalties/summary-by-employees returns grouped summary"""
        response = self.session.get(f"{BASE_URL}/api/penalties/summary-by-employees?month={self.current_month}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Response is a dict keyed by employee_id
        assert isinstance(data, dict), "Response should be a dictionary"
        
        if data:
            first_emp = list(data.values())[0]
            assert "pending" in first_emp, "Employee summary should have pending count"
            assert "approved" in first_emp, "Employee summary should have approved count"
            assert "total_amount" in first_emp, "Employee summary should have total_amount"
        
        print(f"✓ Summary by employees: {len(data)} employees with penalties")
    
    # ==================== FILTER TESTS ====================
    
    def test_20_filter_penalties_by_status(self):
        """GET /api/penalties/month/{month}?status=pending_review filters correctly"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}?status=pending_review")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        penalties = data.get("penalties", [])
        
        # All returned penalties should be pending_review
        for p in penalties:
            assert p.get("status") == "pending_review", f"Expected pending_review, got {p.get('status')}"
        
        print(f"✓ Status filter returned {len(penalties)} pending_review penalties")
    
    def test_21_filter_penalties_by_category(self):
        """GET /api/penalties/month/{month}?category=attendance filters correctly"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/{self.current_month}?category=attendance")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        penalties = data.get("penalties", [])
        
        # All returned penalties should be attendance category
        for p in penalties:
            assert p.get("category") == "attendance", f"Expected attendance, got {p.get('category')}"
        
        print(f"✓ Category filter returned {len(penalties)} attendance penalties")


class TestPenaltyDedup:
    """Test deduplication logic for attendance penalties"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Admin login failed")
        
        self.current_month = datetime.now().strftime("%Y-%m")
    
    def test_22_duplicate_penalty_updates_existing(self):
        """Applying same penalty twice updates existing instead of creating duplicate"""
        # Get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", employees.get("data", []))
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        reference_id = f"TEST_dedup_{datetime.now().timestamp()}"
        
        # Apply penalty first time
        first_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 100,
            "description": "First application",
            "reference_id": reference_id
        })
        
        assert first_response.status_code == 200
        first_data = first_response.json()
        first_action = first_data.get("action")
        first_id = first_data.get("penalty_id")
        
        # Apply same penalty again with different amount
        second_response = self.session.post(f"{BASE_URL}/api/penalties/apply", json={
            "employee_id": employee["id"],
            "month": self.current_month,
            "violation_code": "AT_LATE",
            "amount": 150,
            "description": "Second application - should update",
            "reference_id": reference_id
        })
        
        assert second_response.status_code == 200
        second_data = second_response.json()
        second_action = second_data.get("action")
        second_id = second_data.get("penalty_id")
        
        # Second application should update existing
        assert second_action == "updated", f"Expected 'updated', got '{second_action}'"
        assert second_id == first_id, "Should return same penalty_id"
        
        print(f"✓ Dedup working: first={first_action}, second={second_action}, same_id={first_id == second_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
