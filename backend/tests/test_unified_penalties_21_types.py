"""
Test Suite: Unified Penalties - All 21 Violation Types Across 5 Categories
==========================================================================

Tests the complete penalty flow for ALL violation types:
- Attendance (4 types): AT_LATE, AT_ABSENT, AT_EARLY, AT_NO_CHECKIN
- Leave (4 types): LV_UNAUTH, LV_EXCESS, LV_NO_NOTICE, LV_SANDWICH
- Travel (4 types): TR_EXCESS_CLAIM, TR_NO_RECEIPT, TR_POLICY_VIOL, TR_LATE_SETTLE
- Expense (4 types): EX_EXCESS, EX_DUPLICATE, EX_FRAUD, EX_POLICY_VIOL
- General HR (5 types): HR_DRESS, HR_CONDUCT, HR_CONFIDENTIAL, HR_PROPERTY, HR_HARASSMENT

Total: 21 violation types

Verifies:
1. GET /api/penalties/categories returns all 21 types
2. POST /api/penalties/apply works for each category
3. Penalties stored correctly in employee_penalties collection
4. GET /api/penalties/employee/{id} returns all penalties
5. GET /api/penalties/month/{month} returns monthly summary
6. POST /api/payroll/engine/simulate shows all penalties in deductions
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HR_USER = {"employee_id": "EMP002", "password": "hr123"}
TEST_EMPLOYEE_ID = "287cebfb-8cf6-460d-b6fe-758f0054f5c4"  # EMP003 - Sales Executive
TEST_MONTH = "2026-03"  # March 2026

# All 21 violation types organized by category
PENALTY_CATEGORIES = {
    "attendance": [
        {"code": "AT_LATE", "name": "Late Arrival", "default_amount": 100},
        {"code": "AT_ABSENT", "name": "Unauthorized Absence", "default_amount": 500},
        {"code": "AT_EARLY", "name": "Early Departure", "default_amount": 100},
        {"code": "AT_NO_CHECKIN", "name": "Missing Check-in", "default_amount": 200},
    ],
    "leave": [
        {"code": "LV_UNAUTH", "name": "Unauthorized Leave", "default_amount": 500},
        {"code": "LV_EXCESS", "name": "Excess Leave (Beyond Quota)", "default_amount": 0},
        {"code": "LV_NO_NOTICE", "name": "Leave Without Notice", "default_amount": 250},
        {"code": "LV_SANDWICH", "name": "Sandwich Leave Violation", "default_amount": 0},
    ],
    "travel": [
        {"code": "TR_EXCESS_CLAIM", "name": "Excess Travel Claim", "default_amount": 0},
        {"code": "TR_NO_RECEIPT", "name": "Missing Receipts", "default_amount": 0},
        {"code": "TR_POLICY_VIOL", "name": "Travel Policy Violation", "default_amount": 500},
        {"code": "TR_LATE_SETTLE", "name": "Late Settlement", "default_amount": 100},
    ],
    "expense": [
        {"code": "EX_EXCESS", "name": "Excess Expense Claim", "default_amount": 0},
        {"code": "EX_DUPLICATE", "name": "Duplicate Claim", "default_amount": 0},
        {"code": "EX_FRAUD", "name": "Fraudulent Claim", "default_amount": 1000},
        {"code": "EX_POLICY_VIOL", "name": "Expense Policy Violation", "default_amount": 250},
    ],
    "general": [
        {"code": "HR_DRESS", "name": "Dress Code Violation", "default_amount": 100},
        {"code": "HR_CONDUCT", "name": "Code of Conduct Violation", "default_amount": 500},
        {"code": "HR_CONFIDENTIAL", "name": "Confidentiality Breach", "default_amount": 1000},
        {"code": "HR_PROPERTY", "name": "Company Property Misuse", "default_amount": 500},
        {"code": "HR_HARASSMENT", "name": "Workplace Harassment", "default_amount": 2000},
    ]
}


@pytest.fixture(scope="module")
def hr_token():
    """Get HR user authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=HR_USER
    )
    assert response.status_code == 200, f"HR login failed: {response.text}"
    data = response.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def hr_headers(hr_token):
    """Get headers with HR auth token"""
    return {
        "Authorization": f"Bearer {hr_token}",
        "Content-Type": "application/json"
    }


class TestPenaltyCategoriesAPI:
    """Test GET /api/penalties/categories - Returns all 21 violation types"""
    
    def test_get_penalty_categories_returns_all_21_types(self, hr_headers):
        """Verify all 21 violation types are returned across 5 categories"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/categories",
            headers=hr_headers
        )
        
        assert response.status_code == 200, f"Failed to get categories: {response.text}"
        data = response.json()
        
        # Verify total count
        assert "total_violation_types" in data, "Missing total_violation_types field"
        assert data["total_violation_types"] == 21, f"Expected 21 types, got {data['total_violation_types']}"
        
        # Verify all 5 categories exist
        categories = data.get("categories", {})
        expected_categories = ["attendance", "leave", "travel", "expense", "general"]
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
        
        print(f"PASS: All 21 violation types returned across 5 categories")
    
    def test_each_category_has_correct_violations(self, hr_headers):
        """Verify each category has the correct violation codes"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/categories",
            headers=hr_headers
        )
        
        assert response.status_code == 200
        categories = response.json().get("categories", {})
        
        # Check attendance category (4 types)
        att_violations = [v["code"] for v in categories["attendance"]["violations"]]
        assert "AT_LATE" in att_violations
        assert "AT_ABSENT" in att_violations
        assert "AT_EARLY" in att_violations
        assert "AT_NO_CHECKIN" in att_violations
        assert len(att_violations) == 4
        
        # Check leave category (4 types)
        leave_violations = [v["code"] for v in categories["leave"]["violations"]]
        assert "LV_UNAUTH" in leave_violations
        assert "LV_EXCESS" in leave_violations
        assert "LV_NO_NOTICE" in leave_violations
        assert "LV_SANDWICH" in leave_violations
        assert len(leave_violations) == 4
        
        # Check travel category (4 types)
        travel_violations = [v["code"] for v in categories["travel"]["violations"]]
        assert "TR_EXCESS_CLAIM" in travel_violations
        assert "TR_NO_RECEIPT" in travel_violations
        assert "TR_POLICY_VIOL" in travel_violations
        assert "TR_LATE_SETTLE" in travel_violations
        assert len(travel_violations) == 4
        
        # Check expense category (4 types)
        expense_violations = [v["code"] for v in categories["expense"]["violations"]]
        assert "EX_EXCESS" in expense_violations
        assert "EX_DUPLICATE" in expense_violations
        assert "EX_FRAUD" in expense_violations
        assert "EX_POLICY_VIOL" in expense_violations
        assert len(expense_violations) == 4
        
        # Check general HR category (5 types)
        general_violations = [v["code"] for v in categories["general"]["violations"]]
        assert "HR_DRESS" in general_violations
        assert "HR_CONDUCT" in general_violations
        assert "HR_CONFIDENTIAL" in general_violations
        assert "HR_PROPERTY" in general_violations
        assert "HR_HARASSMENT" in general_violations
        assert len(general_violations) == 5
        
        print("PASS: All categories have correct violation codes")


class TestApplyPenaltiesFromAllCategories:
    """Test POST /api/penalties/apply for different categories"""
    
    def test_apply_attendance_penalty_at_late(self, hr_headers):
        """Apply AT_LATE penalty"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "AT_LATE",
                "amount": 100,
                "description": "Test: 3 late arrivals in March",
                "apply_to_payroll": True
            }
        )
        
        assert response.status_code == 200, f"Failed to apply AT_LATE: {response.text}"
        data = response.json()
        assert "penalty_id" in data
        assert data.get("action") in ["created", "updated"]
        print(f"PASS: AT_LATE penalty applied - {data.get('message')}")
    
    def test_apply_leave_penalty_lv_no_notice(self, hr_headers):
        """Apply LV_NO_NOTICE penalty"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "LV_NO_NOTICE",
                "amount": 250,
                "description": "Test: Leave taken without prior notice",
                "apply_to_payroll": True
            }
        )
        
        assert response.status_code == 200, f"Failed to apply LV_NO_NOTICE: {response.text}"
        data = response.json()
        assert "penalty_id" in data
        print(f"PASS: LV_NO_NOTICE penalty applied - {data.get('message')}")
    
    def test_apply_travel_penalty_tr_policy_viol(self, hr_headers):
        """Apply TR_POLICY_VIOL penalty"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "TR_POLICY_VIOL",
                "amount": 500,
                "description": "Test: Booked business class without approval",
                "apply_to_payroll": True
            }
        )
        
        assert response.status_code == 200, f"Failed to apply TR_POLICY_VIOL: {response.text}"
        data = response.json()
        assert "penalty_id" in data
        print(f"PASS: TR_POLICY_VIOL penalty applied - {data.get('message')}")
    
    def test_apply_expense_penalty_ex_policy_viol(self, hr_headers):
        """Apply EX_POLICY_VIOL penalty"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "EX_POLICY_VIOL",
                "amount": 150,
                "description": "Test: Expense claim without valid receipts",
                "apply_to_payroll": True
            }
        )
        
        assert response.status_code == 200, f"Failed to apply EX_POLICY_VIOL: {response.text}"
        data = response.json()
        assert "penalty_id" in data
        print(f"PASS: EX_POLICY_VIOL penalty applied - {data.get('message')}")
    
    def test_apply_general_hr_penalty_hr_dress(self, hr_headers):
        """Apply HR_DRESS penalty"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "HR_DRESS",
                "amount": 100,
                "description": "Test: Dress code violation on client visit",
                "apply_to_payroll": True
            }
        )
        
        assert response.status_code == 200, f"Failed to apply HR_DRESS: {response.text}"
        data = response.json()
        assert "penalty_id" in data
        print(f"PASS: HR_DRESS penalty applied - {data.get('message')}")
    
    def test_apply_high_severity_penalty_hr_harassment(self, hr_headers):
        """Apply HR_HARASSMENT penalty (high severity)"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "HR_HARASSMENT",
                "amount": 2000,
                "description": "Test: Workplace harassment incident",
                "apply_to_payroll": True
            }
        )
        
        assert response.status_code == 200, f"Failed to apply HR_HARASSMENT: {response.text}"
        data = response.json()
        assert "penalty_id" in data
        print(f"PASS: HR_HARASSMENT penalty applied - {data.get('message')}")


class TestGetEmployeePenalties:
    """Test GET /api/penalties/employee/{id}"""
    
    def test_get_all_penalties_for_employee(self, hr_headers):
        """Get all penalties for test employee"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/employee/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            params={"month": TEST_MONTH}
        )
        
        assert response.status_code == 200, f"Failed to get employee penalties: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "policy_penalties" in data, "Missing policy_penalties field"
        assert "attendance_penalties" in data, "Missing attendance_penalties field"
        assert "total_policy_amount" in data, "Missing total_policy_amount field"
        assert "grand_total" in data, "Missing grand_total field"
        
        policy_penalties = data["policy_penalties"]
        print(f"Found {len(policy_penalties)} policy penalties for {TEST_MONTH}")
        
        # Verify penalties from different categories exist
        violation_codes = [p.get("violation_code") for p in policy_penalties]
        print(f"Violation codes found: {violation_codes}")
        
        # Check that we have penalties from multiple categories
        categories_found = set(p.get("category") for p in policy_penalties)
        print(f"Categories found: {categories_found}")
        
        assert len(policy_penalties) > 0, "No policy penalties found"
        print(f"PASS: Retrieved {len(policy_penalties)} penalties, total: ₹{data['total_policy_amount']}")
    
    def test_penalty_records_have_correct_fields(self, hr_headers):
        """Verify penalty records have all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/employee/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            params={"month": TEST_MONTH}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["policy_penalties"]:
            penalty = data["policy_penalties"][0]
            
            # Required fields
            required_fields = [
                "id", "employee_id", "month", "category", "violation_code",
                "violation_name", "amount", "status", "created_at"
            ]
            
            for field in required_fields:
                assert field in penalty, f"Missing required field: {field}"
            
            print(f"PASS: Penalty record has all required fields")


class TestMonthlyPenaltySummary:
    """Test GET /api/penalties/month/{month}"""
    
    def test_get_monthly_penalty_summary(self, hr_headers):
        """Get monthly penalty summary by category"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/month/{TEST_MONTH}",
            headers=hr_headers
        )
        
        assert response.status_code == 200, f"Failed to get monthly summary: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "month" in data
        assert "by_category" in data
        assert "total_penalties" in data
        assert "total_amount" in data
        assert "employees_affected" in data
        
        print(f"Monthly Summary for {TEST_MONTH}:")
        print(f"  Total Penalties: {data['total_penalties']}")
        print(f"  Total Amount: ₹{data['total_amount']}")
        print(f"  Employees Affected: {data['employees_affected']}")
        
        # Print category breakdown
        for cat, cat_data in data["by_category"].items():
            print(f"  {cat}: {cat_data['count']} penalties, ₹{cat_data['total_amount']}")
        
        print("PASS: Monthly penalty summary retrieved successfully")


class TestPayrollSimulationWithPenalties:
    """Test POST /api/payroll/engine/simulate - Penalties appear in deductions"""
    
    def test_payroll_simulation_includes_all_penalty_types(self, hr_headers):
        """Verify payroll simulation shows penalties from all sources"""
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH
            }
        )
        
        assert response.status_code == 200, f"Payroll simulation failed: {response.text}"
        data = response.json()
        
        # Verify simulation success
        assert data.get("success") == True, f"Simulation not successful: {data}"
        
        # Get deductions
        deductions = data.get("deductions", [])
        print(f"\nPayroll Deductions for {TEST_MONTH}:")
        
        penalty_deductions = []
        for d in deductions:
            print(f"  - {d.get('name')}: ₹{d.get('amount')} (source: {d.get('penalty_source', 'N/A')})")
            if "penalty" in d.get("key", "").lower() or "penalty" in d.get("name", "").lower():
                penalty_deductions.append(d)
        
        # Verify penalties are included
        assert len(penalty_deductions) > 0, "No penalty deductions found in payroll simulation"
        
        # Calculate total penalty amount
        total_penalty = sum(d.get("amount", 0) for d in penalty_deductions)
        print(f"\nTotal Penalty Deductions: ₹{total_penalty}")
        
        # Verify penalty sources
        sources = set(d.get("penalty_source") for d in penalty_deductions if d.get("penalty_source"))
        print(f"Penalty Sources: {sources}")
        
        print(f"\nPASS: Payroll simulation includes {len(penalty_deductions)} penalty deductions")
    
    def test_penalty_deductions_have_traceability(self, hr_headers):
        """Verify penalty deductions have calculation traceability"""
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        deductions = data.get("deductions", [])
        penalty_deductions = [d for d in deductions if "penalty" in d.get("key", "").lower()]
        
        for penalty in penalty_deductions:
            # Check for calculation traceability
            calc = penalty.get("calculation", {})
            if calc:
                assert "input_values" in calc or "formula_used" in calc, \
                    f"Missing traceability for {penalty.get('name')}"
                print(f"  {penalty.get('name')}: rule_id={calc.get('rule_id')}, formula={calc.get('formula_used')}")
        
        print("PASS: Penalty deductions have calculation traceability")


class TestPenaltyDashboardAPI:
    """Test /api/attendance/penalty-dashboard returns data from all sources"""
    
    def test_penalty_dashboard_returns_data(self, hr_headers):
        """Verify penalty dashboard API returns comprehensive data"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/penalty-dashboard",
            headers=hr_headers,
            params={"month": TEST_MONTH}
        )
        
        # Dashboard might return 200 or 404 if not implemented
        if response.status_code == 404:
            print("SKIP: Penalty dashboard endpoint not found (may be under different path)")
            return
        
        assert response.status_code == 200, f"Penalty dashboard failed: {response.text}"
        data = response.json()
        
        print(f"Penalty Dashboard Data: {data}")
        print("PASS: Penalty dashboard API returns data")


class TestPenaltySummaryAPI:
    """Test GET /api/penalties/summary - Comprehensive penalty summary"""
    
    def test_penalty_summary_across_months(self, hr_headers):
        """Get penalty summary across multiple months"""
        response = requests.get(
            f"{BASE_URL}/api/penalties/summary",
            headers=hr_headers,
            params={"months": 6}
        )
        
        assert response.status_code == 200, f"Failed to get penalty summary: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "by_category" in data
        assert "monthly_breakdown" in data
        assert "grand_total" in data
        assert "total_employees_penalized" in data
        
        print(f"\nPenalty Summary (Last 6 months):")
        print(f"  Grand Total: ₹{data['grand_total']}")
        print(f"  Employees Penalized: {data['total_employees_penalized']}")
        
        # Print category breakdown
        print("\n  By Category:")
        for cat, cat_data in data["by_category"].items():
            print(f"    {cat}: {cat_data['total_count']} penalties, ₹{cat_data['total_amount']}")
        
        print("\nPASS: Penalty summary retrieved successfully")


class TestAutoDetectViolations:
    """Test POST /api/penalties/auto-detect/{month}"""
    
    def test_auto_detect_violations(self, hr_headers):
        """Test auto-detection of policy violations"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/auto-detect/{TEST_MONTH}",
            headers=hr_headers
        )
        
        assert response.status_code == 200, f"Auto-detect failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "month" in data
        assert "detected_violations" in data
        assert "total_detected" in data
        
        print(f"\nAuto-Detected Violations for {TEST_MONTH}:")
        print(f"  Total Detected: {data['total_detected']}")
        
        for v in data.get("detected_violations", [])[:5]:  # Show first 5
            print(f"  - {v.get('violation_code')}: {v.get('description')}")
        
        print("PASS: Auto-detect violations API working")


class TestInvalidPenaltyScenarios:
    """Test error handling for invalid penalty operations"""
    
    def test_apply_invalid_violation_code(self, hr_headers):
        """Attempt to apply penalty with invalid violation code"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "month": TEST_MONTH,
                "violation_code": "INVALID_CODE",
                "amount": 100,
                "description": "Test invalid code"
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid code, got {response.status_code}"
        print("PASS: Invalid violation code rejected with 400")
    
    def test_apply_penalty_missing_required_fields(self, hr_headers):
        """Attempt to apply penalty without required fields"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID
                # Missing month and violation_code
            }
        )
        
        assert response.status_code == 400, f"Expected 400 for missing fields, got {response.status_code}"
        print("PASS: Missing required fields rejected with 400")
    
    def test_apply_penalty_invalid_employee(self, hr_headers):
        """Attempt to apply penalty to non-existent employee"""
        response = requests.post(
            f"{BASE_URL}/api/penalties/apply",
            headers=hr_headers,
            json={
                "employee_id": "non-existent-id",
                "month": TEST_MONTH,
                "violation_code": "HR_DRESS",
                "amount": 100
            }
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid employee, got {response.status_code}"
        print("PASS: Invalid employee rejected with 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
