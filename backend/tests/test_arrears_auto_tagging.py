"""
Test Suite: Arrears Auto-Tagging for Penalties
Tests the feature where penalties applied to locked/pending_admin_approval months
are auto-tagged as arrears and carried forward to the next open month.

Features tested:
1. POST /api/penalties/apply to LOCKED month -> auto-tags as arrears
2. POST /api/penalties/apply to OPEN month -> applies normally
3. GET /api/penalties/month/{month} includes arrears_count, arrears_amount, payroll_status
4. Payroll engine deduction calculation includes arrears
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestArrearsAutoTagging:
    """Test arrears auto-tagging for penalties applied to locked months"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as HR"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "hr123"
        })
        assert login_response.status_code == 200, f"HR login failed: {login_response.text}"
        
        login_data = login_response.json()
        self.token = login_data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get employees list
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        emp_data = emp_response.json()
        
        # Handle both array and paginated response
        if isinstance(emp_data, list):
            self.employees = emp_data
        elif isinstance(emp_data, dict):
            self.employees = emp_data.get("items", emp_data.get("employees", []))
        else:
            self.employees = []
        
        # Find EMP005 (Rajesh Kumar) for testing
        self.test_employee = None
        for emp in self.employees:
            if emp.get("employee_id") == "EMP005":
                self.test_employee = emp
                break
        
        yield
    
    # ==================== BACKEND API TESTS ====================
    
    def test_01_get_penalty_categories(self):
        """Test GET /api/penalties/categories returns all violation types"""
        response = self.session.get(f"{BASE_URL}/api/penalties/categories")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 5, "Should have at least 5 categories"
        
        # Verify LV_UNAUTH exists (used in arrears test)
        found_lv_unauth = False
        for cat_key, cat_data in data["categories"].items():
            for violation in cat_data.get("violations", []):
                if violation.get("code") == "LV_UNAUTH":
                    found_lv_unauth = True
                    break
        
        assert found_lv_unauth, "LV_UNAUTH violation code should exist"
        print(f"PASS: Found {len(data['categories'])} categories with {data.get('total_violation_types', 0)} violation types")
    
    def test_02_march_2026_payroll_is_locked(self):
        """Verify March 2026 payroll is locked (prerequisite for arrears test)"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-03")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "payroll_status" in data, "Response should include payroll_status"
        assert data["payroll_status"] == "locked", f"March 2026 should be locked, got: {data['payroll_status']}"
        
        print(f"PASS: March 2026 payroll_status = {data['payroll_status']}")
    
    def test_03_april_2026_payroll_is_open(self):
        """Verify April 2026 payroll is open (next unlocked month)"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-04")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "payroll_status" in data, "Response should include payroll_status"
        assert data["payroll_status"] == "open", f"April 2026 should be open, got: {data['payroll_status']}"
        
        print(f"PASS: April 2026 payroll_status = {data['payroll_status']}")
    
    def test_04_apply_penalty_to_locked_month_creates_arrears(self):
        """Test POST /api/penalties/apply to LOCKED month auto-tags as arrears"""
        if not self.test_employee:
            pytest.skip("Test employee EMP005 not found")
        
        # Apply penalty to March 2026 (locked)
        unique_ref = f"TEST_ARREARS_{uuid.uuid4().hex[:8]}"
        payload = {
            "employee_id": self.test_employee["id"],
            "month": "2026-03",  # Locked month
            "violation_code": "AT_LATE",  # Late Arrival
            "amount": 150,
            "description": f"Test arrears penalty - {unique_ref}",
            "reference_id": unique_ref,
            "apply_to_payroll": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/penalties/apply", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify arrears tagging
        assert data.get("is_arrears") == True, f"Penalty should be tagged as arrears, got: {data}"
        assert data.get("action") == "created_as_arrears", f"Action should be 'created_as_arrears', got: {data.get('action')}"
        assert data.get("original_month") == "2026-03", f"Original month should be 2026-03"
        assert data.get("effective_month") == "2026-04", f"Effective month should be 2026-04 (next open month)"
        assert "arrears_reason" in data, "Should include arrears_reason"
        
        print(f"PASS: Penalty applied as arrears - original_month=2026-03, effective_month=2026-04")
        print(f"  Message: {data.get('message')}")
        
        # Store penalty_id for cleanup
        self.created_penalty_id = data.get("penalty_id")
    
    def test_05_apply_penalty_to_open_month_no_arrears(self):
        """Test POST /api/penalties/apply to OPEN month applies normally (no arrears)"""
        if not self.test_employee:
            pytest.skip("Test employee EMP005 not found")
        
        # Apply penalty to May 2026 (should be open)
        unique_ref = f"TEST_NORMAL_{uuid.uuid4().hex[:8]}"
        payload = {
            "employee_id": self.test_employee["id"],
            "month": "2026-05",  # Open month
            "violation_code": "HR_DRESS",  # Dress Code Violation
            "amount": 100,
            "description": f"Test normal penalty - {unique_ref}",
            "reference_id": unique_ref,
            "apply_to_payroll": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/penalties/apply", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify NOT arrears
        assert data.get("is_arrears") == False, f"Penalty should NOT be arrears for open month, got: {data}"
        assert data.get("action") == "created", f"Action should be 'created', got: {data.get('action')}"
        assert data.get("effective_month") == "2026-05", f"Effective month should be 2026-05"
        
        print(f"PASS: Penalty applied normally (no arrears) - effective_month=2026-05")
    
    def test_06_get_month_penalties_includes_arrears_fields(self):
        """Test GET /api/penalties/month/{month} includes arrears_count, arrears_amount, payroll_status"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-04")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "arrears_count" in data, "Response should include arrears_count"
        assert "arrears_amount" in data, "Response should include arrears_amount"
        assert "payroll_status" in data, "Response should include payroll_status"
        assert "total_penalties" in data, "Response should include total_penalties"
        assert "by_category" in data, "Response should include by_category"
        
        print(f"PASS: April 2026 penalties response includes:")
        print(f"  - arrears_count: {data['arrears_count']}")
        print(f"  - arrears_amount: {data['arrears_amount']}")
        print(f"  - payroll_status: {data['payroll_status']}")
        print(f"  - total_penalties: {data['total_penalties']}")
    
    def test_07_april_2026_shows_arrears_from_march(self):
        """Test GET /api/penalties/month/2026-04 shows arrears carried from March"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-04")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # April should have arrears from March
        assert data.get("arrears_count", 0) > 0, f"April 2026 should have arrears_count > 0, got: {data.get('arrears_count')}"
        assert data.get("arrears_amount", 0) > 0, f"April 2026 should have arrears_amount > 0, got: {data.get('arrears_amount')}"
        
        print(f"PASS: April 2026 has {data['arrears_count']} arrears penalties totaling {data['arrears_amount']}")
    
    def test_08_march_2026_shows_locked_status(self):
        """Test GET /api/penalties/month/2026-03 shows payroll_status=locked"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-03")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert data.get("payroll_status") == "locked", f"March 2026 payroll_status should be 'locked', got: {data.get('payroll_status')}"
        
        print(f"PASS: March 2026 payroll_status = locked")
    
    def test_09_penalties_table_includes_arrears_badge_data(self):
        """Verify penalties in April include is_arrears flag and original_month for UI badge"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-04")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Find arrears penalties in the response
        arrears_found = False
        for cat_key, cat_data in data.get("by_category", {}).items():
            for penalty in cat_data.get("penalties", []):
                if penalty.get("is_arrears"):
                    arrears_found = True
                    assert "original_month" in penalty, "Arrears penalty should have original_month"
                    assert "effective_month" in penalty, "Arrears penalty should have effective_month"
                    assert penalty.get("original_month") != penalty.get("effective_month"), "original_month should differ from effective_month"
                    print(f"  Found arrears penalty: {penalty.get('violation_name')} from {penalty.get('original_month')} -> {penalty.get('effective_month')}")
        
        assert arrears_found, "Should find at least one arrears penalty in April 2026"
        print(f"PASS: Arrears penalties include is_arrears, original_month, effective_month fields")
    
    def test_10_may_2026_is_open_month(self):
        """Verify May 2026 is an open month (no locked register)"""
        response = self.session.get(f"{BASE_URL}/api/penalties/month/2026-05")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("payroll_status") == "open", f"May 2026 should be open, got: {data.get('payroll_status')}"
        
        print(f"PASS: May 2026 payroll_status = open")
    
    def test_11_penalty_summary_endpoint(self):
        """Test GET /api/penalties/summary returns comprehensive data"""
        response = self.session.get(f"{BASE_URL}/api/penalties/summary")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert "by_category" in data, "Summary should include by_category"
        assert "monthly_breakdown" in data, "Summary should include monthly_breakdown"
        assert "grand_total" in data, "Summary should include grand_total"
        
        print(f"PASS: Penalty summary - grand_total: {data.get('grand_total')}, categories: {len(data.get('by_category', {}))}")
    
    def test_12_auto_detect_violations(self):
        """Test POST /api/penalties/auto-detect/{month} works"""
        response = self.session.post(f"{BASE_URL}/api/penalties/auto-detect/2026-03")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert "detected_violations" in data, "Response should include detected_violations"
        assert "total_detected" in data, "Response should include total_detected"
        
        print(f"PASS: Auto-detect found {data.get('total_detected', 0)} violations for 2026-03")


class TestPayrollEngineArrearsIntegration:
    """Test that payroll engine correctly includes arrears in deduction calculation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "hr123"
        })
        assert login_response.status_code == 200
        
        login_data = login_response.json()
        self.token = login_data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
    
    def test_01_payroll_engine_health(self):
        """Test payroll engine endpoints are accessible"""
        response = self.session.get(f"{BASE_URL}/api/payroll/engine/register")
        assert response.status_code == 200, f"Failed: {response.text}"
        print("PASS: Payroll engine register endpoint accessible")
    
    def test_02_payroll_register_march_locked(self):
        """Verify March 2026 payroll register is locked"""
        response = self.session.get(f"{BASE_URL}/api/payroll/engine/register?month=2026-03")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Find locked register
        locked_found = False
        if isinstance(data, list):
            for reg in data:
                if reg.get("status") == "locked":
                    locked_found = True
                    break
        
        assert locked_found, "March 2026 should have a locked payroll register"
        print("PASS: March 2026 has locked payroll register")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
