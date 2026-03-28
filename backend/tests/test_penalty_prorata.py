"""
Backend API Tests for Penalty Management and Pro-rata Features
Tests the P1 features: Penalty Management UI APIs and Onboarding Pro-rata APIs
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://erp-checkin-bug.preview.emergentagent.com')

class TestPenaltyManagementAPIs:
    """Tests for Penalty Management APIs - 5 categories, 21 violation types"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "EMP001", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Get an employee ID for testing
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        if emp_response.status_code == 200:
            data = emp_response.json()
            items = data.get("items", []) if isinstance(data, dict) else data
            if items:
                self.test_employee_id = items[0].get("id")
                self.test_employee_code = items[0].get("employee_id")
            else:
                self.test_employee_id = None
                self.test_employee_code = None
        else:
            self.test_employee_id = None
            self.test_employee_code = None
    
    def test_get_penalty_categories_returns_5_categories(self):
        """GET /api/penalties/categories should return 5 categories"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/categories",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        categories = data.get("categories", {})
        
        # Verify 5 categories exist
        expected_categories = ["attendance", "leave", "travel", "expense", "general"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        assert len(categories) == 5, f"Expected 5 categories, got {len(categories)}"
        print(f"✓ Found 5 categories: {list(categories.keys())}")
    
    def test_get_penalty_categories_returns_21_violations(self):
        """GET /api/penalties/categories should return 21 total violation types"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/categories",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        total_violations = data.get("total_violation_types", 0)
        
        assert total_violations == 21, f"Expected 21 violations, got {total_violations}"
        
        # Verify each category has violations
        categories = data.get("categories", {})
        for cat_key, cat_data in categories.items():
            violations = cat_data.get("violations", [])
            assert len(violations) > 0, f"Category {cat_key} has no violations"
            print(f"  {cat_key}: {len(violations)} violations")
        
        print(f"✓ Total violation types: {total_violations}")
    
    def test_get_monthly_penalties(self):
        """GET /api/penalties/month/{month} should return monthly penalties"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/month/2026-03",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "month" in data, "Response should contain 'month'"
        assert "total_penalties" in data, "Response should contain 'total_penalties'"
        assert "total_amount" in data, "Response should contain 'total_amount'"
        assert "employees_affected" in data, "Response should contain 'employees_affected'"
        assert "by_category" in data, "Response should contain 'by_category'"
        
        print(f"✓ Monthly penalties for 2026-03:")
        print(f"  Total penalties: {data.get('total_penalties')}")
        print(f"  Total amount: {data.get('total_amount')}")
        print(f"  Employees affected: {data.get('employees_affected')}")
    
    def test_apply_penalty_success(self):
        """POST /api/penalties/apply should apply a penalty successfully"""
        if not self.test_employee_id:
            pytest.skip("No test employee available")
        
        # Use a unique reference to avoid duplicates
        unique_ref = f"TEST_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "employee_id": self.test_employee_id,
            "month": "2026-03",
            "violation_code": "AT_LATE",  # Late Arrival
            "amount": 100,
            "description": f"Test penalty - {unique_ref}",
            "reference_id": unique_ref,
            "apply_to_payroll": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=self.headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "penalty_id" in data, "Response should contain 'penalty_id'"
        assert "message" in data, "Response should contain 'message'"
        assert data.get("action") in ["created", "updated"], f"Unexpected action: {data.get('action')}"
        
        print(f"✓ Penalty applied successfully: {data.get('message')}")
        
        # Store penalty_id for cleanup
        self.created_penalty_id = data.get("penalty_id")
    
    def test_apply_penalty_missing_fields(self):
        """POST /api/penalties/apply should fail with missing required fields"""
        payload = {
            "employee_id": self.test_employee_id,
            # Missing month and violation_code
        }
        
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=self.headers,
            json=payload
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Correctly rejected penalty with missing fields")
    
    def test_apply_penalty_invalid_violation_code(self):
        """POST /api/penalties/apply should fail with invalid violation code"""
        if not self.test_employee_id:
            pytest.skip("No test employee available")
        
        payload = {
            "employee_id": self.test_employee_id,
            "month": "2026-03",
            "violation_code": "INVALID_CODE",
            "amount": 100
        }
        
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=self.headers,
            json=payload
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Correctly rejected invalid violation code")


class TestProRataAPIs:
    """Tests for Pro-rata Salary APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "EMP001", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_prorata_check_endpoint_exists(self):
        """GET /api/payroll/engine/pro-rata/check/{month} should exist and return data"""
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/pro-rata/check/2026-03",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "month" in data, "Response should contain 'month'"
        assert "prorata_employees" in data, "Response should contain 'prorata_employees'"
        assert "total_prorata" in data, "Response should contain 'total_prorata'"
        assert "message" in data, "Response should contain 'message'"
        
        print(f"✓ Pro-rata check for 2026-03:")
        print(f"  Total mid-month joiners: {data.get('total_prorata')}")
        print(f"  Message: {data.get('message')}")
    
    def test_prorata_check_returns_correct_structure(self):
        """Pro-rata check should return correct data structure for employees"""
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/pro-rata/check/2026-03",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        prorata_employees = data.get("prorata_employees", [])
        
        # If there are any pro-rata employees, verify structure
        if prorata_employees:
            emp = prorata_employees[0]
            expected_fields = [
                "employee_id", "employee_code", "employee_name", "department",
                "joining_date", "full_gross", "prorata_gross", "days_worked",
                "days_in_month", "is_prorata"
            ]
            for field in expected_fields:
                assert field in emp, f"Missing field in pro-rata employee: {field}"
            print(f"✓ Pro-rata employee structure verified with {len(prorata_employees)} employees")
        else:
            print("✓ No mid-month joiners found (expected for 2026-03)")
    
    def test_prorata_check_different_months(self):
        """Pro-rata check should work for different months"""
        months = ["2026-01", "2026-02", "2026-03", "2026-04"]
        
        for month in months:
            response = requests.get(
                f"{BASE_URL}/api/payroll/engine/pro-rata/check/{month}",
                headers=self.headers
            )
            
            assert response.status_code == 200, f"Failed for month {month}: {response.text}"
            data = response.json()
            assert data.get("month") == month, f"Month mismatch for {month}"
        
        print(f"✓ Pro-rata check works for all test months: {months}")


class TestPayrollEngineIntegration:
    """Integration tests for Payroll Engine with Pro-rata"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "EMP001", "password": "admin123"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_payroll_register_endpoint(self):
        """GET /api/payroll/engine/register should return payroll registers"""
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/register",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of registers"
        print(f"✓ Payroll register endpoint works, found {len(data)} registers")
    
    def test_penalty_summary_endpoint(self):
        """GET /api/penalties/summary should return penalty summary"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/summary",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "by_category" in data, "Response should contain 'by_category'"
        assert "monthly_breakdown" in data, "Response should contain 'monthly_breakdown'"
        assert "grand_total" in data, "Response should contain 'grand_total'"
        
        print(f"✓ Penalty summary endpoint works")
        print(f"  Grand total: {data.get('grand_total')}")
        print(f"  Total employees penalized: {data.get('total_employees_penalized')}")


class TestAutoDetectViolations:
    """Tests for Auto-Detect Violations feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "EMP001", "password": "admin123"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_auto_detect_endpoint_exists(self):
        """POST /api/penalties/auto-detect/{month} should exist"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/auto-detect/2026-03",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "month" in data, "Response should contain 'month'"
        assert "detected_violations" in data, "Response should contain 'detected_violations'"
        assert "total_detected" in data, "Response should contain 'total_detected'"
        
        print(f"✓ Auto-detect endpoint works")
        print(f"  Total detected: {data.get('total_detected')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
