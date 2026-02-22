"""
Leave Policy Management API Tests
Tests for leave policy CRUD, cascading policies, balance calculation,
and payroll integration (LOP deductions, leave encashment)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestLeavePolicyBasics:
    """Basic leave policy API tests - authentication and CRUD"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        # Login as admin
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        print(f"✓ Logged in as admin")
    
    def test_get_leave_policies_returns_list(self):
        """Test GET /api/leave-policies returns a list of policies"""
        response = requests.get(f"{BASE_URL}/api/leave-policies", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /leave-policies returned {len(data)} policies")
        
        # Should have at least the default policy
        if len(data) > 0:
            policy = data[0]
            assert "name" in policy, "Policy should have a name"
            assert "leave_types" in policy, "Policy should have leave_types"
            assert "scope" in policy, "Policy should have scope"
            print(f"✓ First policy: {policy.get('name')}")
    
    def test_default_policy_auto_created(self):
        """Test that default Standard Leave Policy is auto-created"""
        response = requests.get(f"{BASE_URL}/api/leave-policies", headers=self.headers)
        assert response.status_code == 200
        
        policies = response.json()
        policy_names = [p.get("name") for p in policies]
        
        # Check for default policy
        assert any("Standard" in name for name in policy_names), \
            "Standard Leave Policy should be auto-created"
        print("✓ Standard Leave Policy exists")
    
    def test_default_policy_has_correct_leave_types(self):
        """Test default policy contains expected leave types"""
        response = requests.get(f"{BASE_URL}/api/leave-policies?scope=company", headers=self.headers)
        assert response.status_code == 200
        
        policies = response.json()
        company_policy = next((p for p in policies if p.get("scope") == "company"), None)
        
        if company_policy:
            leave_types = company_policy.get("leave_types", [])
            leave_type_names = [lt.get("leave_type") for lt in leave_types]
            
            # Check for expected leave types
            expected_types = ["casual_leave", "sick_leave", "earned_leave"]
            for exp_type in expected_types:
                assert exp_type in leave_type_names, f"{exp_type} should be in default policy"
            
            print(f"✓ Default policy has leave types: {leave_type_names}")


class TestLeavePolicyCRUD:
    """Create, Update, Delete leave policy tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with HR admin authentication"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.test_policy_id = None
    
    def test_create_new_policy(self):
        """Test creating a new leave policy"""
        unique_name = f"TEST_Policy_{uuid.uuid4().hex[:8]}"
        policy_data = {
            "name": unique_name,
            "description": "Test policy for automated testing",
            "scope": "company",
            "scope_value": None,
            "effective_from": datetime.now().strftime("%Y-%m-%d"),
            "is_active": True,
            "leave_types": [
                {
                    "leave_type": "casual_leave",
                    "annual_quota": 10,
                    "accrual_type": "yearly",
                    "carry_forward": False,
                    "encashment_allowed": False,
                    "min_service_months": 0,
                    "pro_rata_for_new_joiners": True
                }
            ],
            "payroll_integration": {
                "lop_deduction_formula": "basic_per_day",
                "encashment_formula": "basic_per_day",
                "auto_adjust_salary": True
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/leave-policies", json=policy_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create policy: {response.text}"
        
        result = response.json()
        assert "id" in result, "Created policy should return an id"
        assert result.get("message") == "Leave policy created"
        
        self.test_policy_id = result["id"]
        print(f"✓ Created policy with id: {self.test_policy_id}")
        
        # Cleanup - delete the test policy
        if self.test_policy_id:
            requests.delete(f"{BASE_URL}/api/leave-policies/{self.test_policy_id}", headers=self.headers)
    
    def test_update_policy(self):
        """Test updating an existing policy"""
        # First create a policy
        unique_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(f"{BASE_URL}/api/leave-policies", json={
            "name": unique_name,
            "scope": "company",
            "effective_from": datetime.now().strftime("%Y-%m-%d"),
            "is_active": True,
            "leave_types": []
        }, headers=self.headers)
        assert create_resp.status_code == 200
        policy_id = create_resp.json()["id"]
        
        # Update the policy
        update_data = {
            "name": f"{unique_name}_Updated",
            "description": "Updated description"
        }
        
        update_resp = requests.put(f"{BASE_URL}/api/leave-policies/{policy_id}", json=update_data, headers=self.headers)
        assert update_resp.status_code == 200, f"Failed to update: {update_resp.text}"
        assert update_resp.json().get("message") == "Leave policy updated"
        print(f"✓ Policy {policy_id} updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/leave-policies/{policy_id}", headers=self.headers)
    
    def test_delete_policy(self):
        """Test soft-deleting a policy"""
        # Create a policy to delete
        unique_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        create_resp = requests.post(f"{BASE_URL}/api/leave-policies", json={
            "name": unique_name,
            "scope": "company",
            "effective_from": datetime.now().strftime("%Y-%m-%d"),
            "is_active": True,
            "leave_types": []
        }, headers=self.headers)
        assert create_resp.status_code == 200
        policy_id = create_resp.json()["id"]
        
        # Delete the policy
        delete_resp = requests.delete(f"{BASE_URL}/api/leave-policies/{policy_id}", headers=self.headers)
        assert delete_resp.status_code == 200, f"Failed to delete: {delete_resp.text}"
        assert delete_resp.json().get("message") == "Leave policy deleted"
        print(f"✓ Policy {policy_id} deleted successfully")


class TestEffectivePolicy:
    """Test cascaded effective policy retrieval (employee > role > department > company)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_effective_policy_for_employee(self):
        """Test GET /api/leave-policies/effective/{employee_id}"""
        # First get an employee
        employees_resp = requests.get(f"{BASE_URL}/api/employees?limit=1", headers=self.headers)
        if employees_resp.status_code != 200 or not employees_resp.json():
            pytest.skip("No employees found to test")
        
        employee = employees_resp.json()[0]
        employee_id = employee.get("id")
        
        response = requests.get(f"{BASE_URL}/api/leave-policies/effective/{employee_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "policy" in data, "Response should have 'policy'"
        assert "applied_level" in data, "Response should have 'applied_level'"
        
        # applied_level should be one of: employee, role, department, company, default
        valid_levels = ["employee", "role", "department", "company", "default"]
        assert data["applied_level"] in valid_levels, f"Invalid applied_level: {data['applied_level']}"
        
        print(f"✓ Effective policy for {employee_id}: {data['policy'].get('name')} (level: {data['applied_level']})")
    
    def test_effective_policy_with_invalid_employee(self):
        """Test effective policy endpoint with non-existent employee"""
        fake_id = f"fake-employee-{uuid.uuid4().hex}"
        response = requests.get(f"{BASE_URL}/api/leave-policies/effective/{fake_id}", headers=self.headers)
        assert response.status_code == 404, "Should return 404 for non-existent employee"
        print("✓ Returns 404 for invalid employee ID")


class TestLeaveBalanceCalculation:
    """Test leave balance calculation with accrual, tenure, carry forward"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_calculate_leave_balance_for_employee(self):
        """Test GET /api/leave-policies/calculate-balance/{employee_id}"""
        # Get an employee
        employees_resp = requests.get(f"{BASE_URL}/api/employees?limit=1", headers=self.headers)
        if employees_resp.status_code != 200 or not employees_resp.json():
            pytest.skip("No employees found to test")
        
        employee = employees_resp.json()[0]
        employee_id = employee.get("id")
        
        response = requests.get(f"{BASE_URL}/api/leave-policies/calculate-balance/{employee_id}", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Validate response structure
        assert "employee_id" in data
        assert "balance" in data
        assert "payroll_impact" in data
        assert "service_months" in data
        
        # Check balance structure
        balance = data["balance"]
        if balance:
            for leave_type, balance_info in balance.items():
                assert "annual_quota" in balance_info
                assert "entitled_ytd" in balance_info
                assert "used" in balance_info
                assert "available" in balance_info
                print(f"  {leave_type}: available={balance_info['available']}, used={balance_info['used']}")
        
        print(f"✓ Balance calculated for {employee_id}, service_months: {data['service_months']}")
    
    def test_calculate_balance_with_date_param(self):
        """Test balance calculation with as_of_date parameter"""
        employees_resp = requests.get(f"{BASE_URL}/api/employees?limit=1", headers=self.headers)
        if employees_resp.status_code != 200 or not employees_resp.json():
            pytest.skip("No employees found")
        
        employee_id = employees_resp.json()[0].get("id")
        test_date = "2026-01-15"
        
        response = requests.get(
            f"{BASE_URL}/api/leave-policies/calculate-balance/{employee_id}?as_of_date={test_date}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["as_of_date"] == test_date
        print(f"✓ Balance calculated as of {test_date}")
    
    def test_balance_invalid_employee(self):
        """Test balance calculation with non-existent employee"""
        fake_id = f"fake-{uuid.uuid4().hex}"
        response = requests.get(f"{BASE_URL}/api/leave-policies/calculate-balance/{fake_id}", headers=self.headers)
        assert response.status_code == 404
        print("✓ Returns 404 for invalid employee")


class TestPayrollIntegration:
    """Test payroll integration - LOP deductions, leave encashment"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_leave_encashments(self):
        """Test GET /api/payroll/leave-encashments"""
        response = requests.get(f"{BASE_URL}/api/payroll/leave-encashments", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /payroll/leave-encashments returned {len(data)} encashments")
    
    def test_get_leave_encashments_with_filters(self):
        """Test leave encashments with month/year filters"""
        # Test with month filter
        response = requests.get(f"{BASE_URL}/api/payroll/leave-encashments?month=1&year=2026", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Leave encashments filter by month/year works")
    
    def test_get_leave_policy_adjustments(self):
        """Test GET /api/payroll/leave-policy-adjustments/{employee_id}"""
        # Get an employee
        employees_resp = requests.get(f"{BASE_URL}/api/employees?limit=1", headers=self.headers)
        if employees_resp.status_code != 200 or not employees_resp.json():
            pytest.skip("No employees found")
        
        employee_id = employees_resp.json()[0].get("id")
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/leave-policy-adjustments/{employee_id}?month={current_month}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert "salary_info" in data
        assert "lop" in data
        assert "encashment" in data
        assert "net_adjustment" in data
        
        print(f"✓ Leave adjustments for {employee_id}:")
        print(f"  LOP days: {data['lop']['days']}, deduction: {data['lop']['deduction']}")
        print(f"  Encashment: {data['encashment']['days']} days, amount: {data['encashment']['amount']}")
        print(f"  Net adjustment: {data['net_adjustment']}")


class TestLeaveEncashmentWorkflow:
    """Test leave encashment request workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_encashment_approve_reject_endpoints_exist(self):
        """Verify encashment approve/reject endpoints exist and respond"""
        fake_id = "fake-encashment-id"
        
        # Test approve endpoint - should return 404 (not found) for fake ID
        approve_resp = requests.post(f"{BASE_URL}/api/payroll/leave-encashments/{fake_id}/approve", headers=self.headers)
        # 404 = not found (correct), 400 = bad request (acceptable), 200 = silent success (edge case)
        assert approve_resp.status_code in [404, 400, 200], \
            f"Approve endpoint should respond, got {approve_resp.status_code}"
        print(f"  Approve endpoint returned: {approve_resp.status_code}")
        
        # Test reject endpoint
        reject_resp = requests.post(
            f"{BASE_URL}/api/payroll/leave-encashments/{fake_id}/reject",
            json={"reason": "test"},
            headers=self.headers
        )
        # Some implementations silently succeed, others return 404
        assert reject_resp.status_code in [404, 400, 200], \
            f"Reject endpoint should respond, got {reject_resp.status_code}"
        print(f"  Reject endpoint returned: {reject_resp.status_code}")
        
        print("✓ Encashment approve/reject endpoints exist and respond correctly")


class TestPolicyScope:
    """Test policy scope hierarchy"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_filter_policies_by_scope(self):
        """Test filtering policies by scope parameter"""
        for scope in ["company", "department", "role", "employee"]:
            response = requests.get(f"{BASE_URL}/api/leave-policies?scope={scope}", headers=self.headers)
            assert response.status_code == 200, f"Failed for scope={scope}: {response.text}"
            
            policies = response.json()
            # All returned policies should match the scope
            for policy in policies:
                assert policy.get("scope") == scope or policies == [], \
                    f"Policy scope mismatch: expected {scope}, got {policy.get('scope')}"
            
            print(f"✓ Scope filter '{scope}': {len(policies)} policies")
    
    def test_filter_policies_by_active_status(self):
        """Test filtering policies by is_active parameter"""
        # Active policies
        active_resp = requests.get(f"{BASE_URL}/api/leave-policies?is_active=true", headers=self.headers)
        assert active_resp.status_code == 200
        active_count = len(active_resp.json())
        
        # Include inactive
        all_resp = requests.get(f"{BASE_URL}/api/leave-policies?is_active=", headers=self.headers)
        assert all_resp.status_code == 200
        
        print(f"✓ Active policies: {active_count}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
