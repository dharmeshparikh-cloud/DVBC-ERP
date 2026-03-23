"""
Business Rules API Tests - Testing CRUD operations, rule engine, and payroll simulator
Tests all 6 policy types: leave, travel, expense, attendance, payroll, general
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HR_CREDENTIALS = {"employee_id": "EMP002", "password": "hr123"}
EMPLOYEE_CREDENTIALS = {"employee_id": "EMP005", "password": "Welcome@EMP005"}
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}


class TestBusinessRulesAuth:
    """Test authentication and permission checks for Business Rules"""
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR Manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("HR login failed")
    
    @pytest.fixture(scope="class")
    def employee_token(self):
        """Get Employee token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Employee login failed")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_hr_login_success(self):
        """Test HR Manager can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        assert response.status_code == 200, f"HR login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"HR login successful, role: {data.get('user', {}).get('role')}")
    
    def test_employee_login_success(self):
        """Test Employee can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDENTIALS)
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"Employee login successful, role: {data.get('user', {}).get('role')}")


class TestBusinessRulesAPI:
    """Test Business Rules CRUD operations"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get authenticated HR session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("HR authentication failed")
    
    @pytest.fixture(scope="class")
    def employee_session(self):
        """Get authenticated Employee session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("Employee authentication failed")
    
    def test_get_all_policies(self, hr_session):
        """Test fetching all business policies"""
        response = hr_session.get(f"{BASE_URL}/api/business-rules")
        assert response.status_code == 200, f"Failed to get policies: {response.text}"
        policies = response.json()
        assert isinstance(policies, list), "Response should be a list"
        print(f"Found {len(policies)} policies")
        
        # Verify all 6 policy types exist
        policy_types = set(p.get("policy_type") for p in policies)
        expected_types = {"leave", "travel", "expense", "attendance", "payroll", "general"}
        assert expected_types.issubset(policy_types), f"Missing policy types: {expected_types - policy_types}"
        print(f"All 6 policy types present: {policy_types}")
    
    def test_get_policy_types(self, hr_session):
        """Test fetching policy types metadata"""
        response = hr_session.get(f"{BASE_URL}/api/business-rules/types")
        assert response.status_code == 200, f"Failed to get policy types: {response.text}"
        data = response.json()
        
        assert "policy_types" in data
        assert "rule_types" in data
        
        policy_types = data["policy_types"]
        assert len(policy_types) == 6, f"Expected 6 policy types, got {len(policy_types)}"
        
        rule_types = data["rule_types"]
        expected_rule_types = {"limit", "threshold", "condition", "formula", "approval"}
        actual_rule_types = set(rt["id"] for rt in rule_types)
        assert expected_rule_types == actual_rule_types, f"Rule types mismatch: {actual_rule_types}"
        print(f"Policy types: {[pt['id'] for pt in policy_types]}")
        print(f"Rule types: {list(actual_rule_types)}")
    
    def test_get_leave_policy(self, hr_session):
        """Test fetching leave policy with rules"""
        response = hr_session.get(f"{BASE_URL}/api/business-rules?policy_type=leave")
        assert response.status_code == 200
        policies = response.json()
        
        leave_policies = [p for p in policies if p.get("policy_type") == "leave"]
        assert len(leave_policies) > 0, "No leave policies found"
        
        leave_policy = leave_policies[0]
        assert "rules" in leave_policy
        rules = leave_policy["rules"]
        assert len(rules) > 0, "Leave policy has no rules"
        
        # Check for expected leave rules
        rule_ids = [r.get("rule_id") for r in rules]
        expected_rules = ["LV001", "LV002", "LV003"]  # Casual, Sick, Earned leave
        for rule_id in expected_rules:
            assert rule_id in rule_ids, f"Missing rule {rule_id}"
        
        print(f"Leave policy has {len(rules)} rules: {rule_ids}")
    
    def test_get_payroll_rules(self, hr_session):
        """Test fetching payroll rules with statutory components"""
        response = hr_session.get(f"{BASE_URL}/api/business-rules?policy_type=payroll")
        assert response.status_code == 200
        policies = response.json()
        
        payroll_policies = [p for p in policies if p.get("policy_type") == "payroll"]
        assert len(payroll_policies) > 0, "No payroll policies found"
        
        payroll_policy = payroll_policies[0]
        rules = payroll_policy.get("rules", [])
        
        # Check for statutory rules
        rule_names = [r.get("rule_name", "") for r in rules]
        assert any("PF" in name for name in rule_names), "Missing PF rules"
        assert any("ESI" in name for name in rule_names), "Missing ESI rules"
        assert any("Professional Tax" in name for name in rule_names), "Missing PT rules"
        
        print(f"Payroll policy has {len(rules)} rules")
    
    def test_employee_view_only_access(self, employee_session):
        """Test that employee can view but not edit policies"""
        # Employee should be able to view
        response = employee_session.get(f"{BASE_URL}/api/business-rules")
        assert response.status_code == 200, "Employee should be able to view policies"
        
        policies = response.json()
        if len(policies) > 0:
            policy_id = policies[0].get("id")
            
            # Employee should NOT be able to update
            update_response = employee_session.put(
                f"{BASE_URL}/api/business-rules/{policy_id}",
                json={"name": "TEST_Modified Policy"}
            )
            assert update_response.status_code == 403, f"Employee should not be able to update policies, got {update_response.status_code}"
            print("Employee correctly denied edit access")


class TestRuleEditing:
    """Test rule editing functionality"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get authenticated HR session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("HR authentication failed")
    
    def test_update_rule_numeric_value(self, hr_session):
        """Test updating a rule's numeric value"""
        # Get leave policy
        response = hr_session.get(f"{BASE_URL}/api/business-rules?policy_type=leave")
        assert response.status_code == 200
        policies = response.json()
        
        leave_policy = next((p for p in policies if p.get("policy_type") == "leave"), None)
        assert leave_policy is not None, "Leave policy not found"
        
        policy_id = leave_policy["id"]
        rules = leave_policy.get("rules", [])
        
        # Find casual leave rule (LV001)
        casual_leave_rule = next((r for r in rules if r.get("rule_id") == "LV001"), None)
        if casual_leave_rule is None:
            pytest.skip("LV001 rule not found")
        
        original_value = casual_leave_rule.get("numeric_value", 12)
        
        # Update the rule
        update_data = {
            **casual_leave_rule,
            "numeric_value": original_value  # Keep same value to avoid breaking tests
        }
        
        update_response = hr_session.put(
            f"{BASE_URL}/api/business-rules/{policy_id}/rule/LV001",
            json=update_data
        )
        assert update_response.status_code == 200, f"Failed to update rule: {update_response.text}"
        print(f"Successfully updated LV001 rule")
    
    def test_toggle_rule_enabled(self, hr_session):
        """Test toggling rule enabled/disabled"""
        # Get attendance policy
        response = hr_session.get(f"{BASE_URL}/api/business-rules?policy_type=attendance")
        assert response.status_code == 200
        policies = response.json()
        
        attendance_policy = next((p for p in policies if p.get("policy_type") == "attendance"), None)
        assert attendance_policy is not None, "Attendance policy not found"
        
        policy_id = attendance_policy["id"]
        rules = attendance_policy.get("rules", [])
        
        if len(rules) == 0:
            pytest.skip("No attendance rules found")
        
        test_rule = rules[0]
        rule_id = test_rule.get("rule_id")
        original_enabled = test_rule.get("is_enabled", True)
        
        # Toggle the rule
        update_data = {
            **test_rule,
            "is_enabled": not original_enabled
        }
        
        update_response = hr_session.put(
            f"{BASE_URL}/api/business-rules/{policy_id}/rule/{rule_id}",
            json=update_data
        )
        assert update_response.status_code == 200, f"Failed to toggle rule: {update_response.text}"
        
        # Restore original state
        restore_data = {
            **test_rule,
            "is_enabled": original_enabled
        }
        restore_response = hr_session.put(
            f"{BASE_URL}/api/business-rules/{policy_id}/rule/{rule_id}",
            json=restore_data
        )
        assert restore_response.status_code == 200
        print(f"Successfully toggled rule {rule_id}")


class TestRuleEngine:
    """Test rule engine evaluation endpoints"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get authenticated HR session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("HR authentication failed")
    
    def test_evaluate_condition_and_logic(self, hr_session):
        """Test AND condition evaluation"""
        data = {
            "condition": "basic_salary > 15000 AND department == 'Sales'",
            "context": {"basic_salary": 20000, "department": "Sales"}
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/evaluate-condition", json=data)
        assert response.status_code == 200, f"Condition evaluation failed: {response.text}"
        
        result = response.json()
        assert result["result"] == True, "AND condition should be True"
        print(f"AND condition result: {result['result']}, explanation: {result.get('explanation')}")
    
    def test_evaluate_condition_or_logic(self, hr_session):
        """Test OR condition evaluation"""
        data = {
            "condition": "basic_salary > 50000 OR department == 'Sales'",
            "context": {"basic_salary": 20000, "department": "Sales"}
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/evaluate-condition", json=data)
        assert response.status_code == 200
        
        result = response.json()
        assert result["result"] == True, "OR condition should be True (department matches)"
        print(f"OR condition result: {result['result']}")
    
    def test_evaluate_formula(self, hr_session):
        """Test formula evaluation"""
        data = {
            "formula": "basic_salary * 0.12",
            "context": {"basic_salary": 20000}
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/evaluate-formula", json=data)
        assert response.status_code == 200, f"Formula evaluation failed: {response.text}"
        
        result = response.json()
        assert result["result"] == 2400.0, f"Expected 2400, got {result['result']}"
        print(f"Formula result: {result['result']}")
    
    def test_calculate_statutory_deductions(self, hr_session):
        """Test statutory deductions calculation"""
        data = {
            "basic_salary": 25000,
            "gross_salary": 50000
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/calculate-statutory", json=data)
        assert response.status_code == 200, f"Statutory calculation failed: {response.text}"
        
        result = response.json()
        statutory = result.get("statutory_deductions", {})
        
        # PF should be calculated (12% of min(basic, 15000))
        assert "pf_employee" in statutory
        expected_pf = round(min(25000, 15000) * 0.12, 2)
        assert statutory["pf_employee"] == expected_pf, f"PF mismatch: expected {expected_pf}, got {statutory['pf_employee']}"
        
        # ESI should be 0 (gross > 21000)
        assert statutory.get("esi_employee", 0) == 0, "ESI should be 0 for gross > 21000"
        
        print(f"Statutory deductions: PF={statutory['pf_employee']}, PT={statutory.get('professional_tax')}")
    
    def test_calculate_lop_deduction(self, hr_session):
        """Test LOP deduction calculation"""
        data = {
            "basic_salary": 30000,
            "working_days": 26,
            "lop_days": 2
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/calculate-lop", json=data)
        assert response.status_code == 200, f"LOP calculation failed: {response.text}"
        
        result = response.json()
        lop = result.get("lop_deduction", {})
        
        expected_per_day = round(30000 / 26, 2)
        expected_total = round(expected_per_day * 2, 2)
        
        assert lop.get("lop_days") == 2
        assert abs(lop.get("total_deduction", 0) - expected_total) < 1, f"LOP mismatch: expected ~{expected_total}, got {lop.get('total_deduction')}"
        
        print(f"LOP deduction: {lop.get('total_deduction')} for {lop.get('lop_days')} days")


class TestPayrollSimulator:
    """Test payroll simulator functionality"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get authenticated HR session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("HR authentication failed")
    
    def test_simulate_payroll_basic(self, hr_session):
        """Test basic payroll simulation"""
        data = {
            "annual_ctc": 600000,
            "basic_percentage": 40,
            "hra_percentage": 50,
            "working_days": 26,
            "present_days": 26,
            "lop_days": 0,
            "expense_reimbursement": 0
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/simulate-payroll", json=data)
        assert response.status_code == 200, f"Payroll simulation failed: {response.text}"
        
        result = response.json()
        
        # Verify structure
        assert "earnings" in result
        assert "deductions" in result
        assert "summary" in result
        
        earnings = result["earnings"]
        assert earnings["basic_salary"] > 0
        assert earnings["hra"] > 0
        assert earnings["total_earnings"] > 0
        
        summary = result["summary"]
        assert summary["net_salary"] > 0
        assert summary["net_salary"] < summary["gross_salary"]
        
        print(f"Payroll simulation: Gross={summary['gross_salary']}, Net={summary['net_salary']}")
    
    def test_simulate_payroll_with_lop(self, hr_session):
        """Test payroll simulation with LOP days"""
        data = {
            "annual_ctc": 600000,
            "basic_percentage": 40,
            "hra_percentage": 50,
            "working_days": 26,
            "present_days": 24,
            "lop_days": 2,
            "expense_reimbursement": 0
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/simulate-payroll", json=data)
        assert response.status_code == 200
        
        result = response.json()
        deductions = result["deductions"]
        
        assert deductions.get("lop_deduction", 0) > 0, "LOP deduction should be > 0"
        print(f"LOP deduction: {deductions['lop_deduction']}")
    
    def test_simulate_payroll_with_reimbursement(self, hr_session):
        """Test payroll simulation with expense reimbursement"""
        data = {
            "annual_ctc": 600000,
            "basic_percentage": 40,
            "hra_percentage": 50,
            "working_days": 26,
            "present_days": 26,
            "lop_days": 0,
            "expense_reimbursement": 5000
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/simulate-payroll", json=data)
        assert response.status_code == 200
        
        result = response.json()
        earnings = result["earnings"]
        
        assert earnings.get("expense_reimbursement") == 5000
        assert earnings["total_earnings"] > earnings["gross_salary"]
        
        print(f"Total earnings with reimbursement: {earnings['total_earnings']}")
    
    def test_simulate_payroll_validation(self, hr_session):
        """Test payroll simulation with invalid values"""
        # Test with negative CTC (should still work but produce 0 or negative values)
        data = {
            "annual_ctc": 0,
            "basic_percentage": 40,
            "hra_percentage": 50,
            "working_days": 26,
            "present_days": 26,
            "lop_days": 0,
            "expense_reimbursement": 0
        }
        
        response = hr_session.post(f"{BASE_URL}/api/business-rules/engine/simulate-payroll", json=data)
        assert response.status_code == 200, "Should handle zero CTC gracefully"
        
        result = response.json()
        assert result["earnings"]["basic_salary"] == 0
        print("Zero CTC handled gracefully")


class TestCTCComponents:
    """Test CTC components endpoint"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get authenticated HR session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("HR authentication failed")
    
    def test_get_ctc_components(self, hr_session):
        """Test fetching CTC components"""
        response = hr_session.get(f"{BASE_URL}/api/business-rules/engine/ctc-components")
        assert response.status_code == 200, f"Failed to get CTC components: {response.text}"
        
        result = response.json()
        assert "components" in result
        assert "grouped" in result
        
        components = result["components"]
        assert len(components) > 0, "No CTC components found"
        
        grouped = result["grouped"]
        assert "earnings" in grouped
        assert "deductions" in grouped
        
        print(f"Found {len(components)} CTC components")
        print(f"Earnings: {len(grouped['earnings'])}, Deductions: {len(grouped['deductions'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
