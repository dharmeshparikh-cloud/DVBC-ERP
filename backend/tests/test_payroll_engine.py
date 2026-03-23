"""
Payroll Engine API Tests
Tests for:
1. LOP calculation using actual days in month (not fixed 30)
2. HR Test Mode simulation
3. Run Payroll (creates draft register)
4. Payroll Register retrieval
5. Approval workflow (HR Manager → Admin)
6. Field-level traceability
"""

import pytest
import requests
import os
import calendar
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HR_MANAGER_CREDS = {"employee_id": "EMP002", "password": "hr123"}
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}


class TestPayrollEngineAuth:
    """Authentication tests for payroll engine"""
    
    def test_hr_manager_login(self):
        """Test HR Manager can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "hr_manager"
        print(f"✓ HR Manager login successful: {data['user']['full_name']}")
    
    def test_admin_login(self):
        """Test Admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['full_name']}")


class TestPayrollEngineSimulation:
    """HR Test Mode - Payroll Simulation Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token and employee list"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        # Get employees
        emp_resp = requests.get(f"{BASE_URL}/api/employees/all", headers=self.hr_headers)
        self.employees = emp_resp.json()
        self.test_employee = self.employees[0] if self.employees else None
    
    def test_simulate_payroll_basic(self):
        """Test basic payroll simulation without LOP"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-03",
                "lop_days": 0,
                "bonus": 0,
                "incentive": 0,
                "penalty": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["employee_id"] == self.test_employee["id"]
        assert data["month"] == "2026-03"
        assert data["days_in_month"] == 31  # March has 31 days
        assert data["lop_days"] == 0
        assert data["gross_monthly"] > 0
        assert data["net_payable"] > 0
        assert "earnings" in data
        assert "deductions" in data
        assert data["is_simulation"] == True
        print(f"✓ Basic simulation: Gross={data['gross_monthly']}, Net={data['net_payable']}")
    
    def test_simulate_payroll_with_lop_march(self):
        """Test LOP calculation for March (31 days)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        lop_days = 2
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-03",
                "lop_days": lop_days,
                "bonus": 0,
                "incentive": 0,
                "penalty": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["days_in_month"] == 31  # March has 31 days
        assert data["lop_days"] == lop_days
        
        # Verify LOP calculation: Gross / 31 days * LOP days
        gross = data["gross_monthly"]
        expected_daily_rate = gross / 31
        expected_lop = expected_daily_rate * lop_days
        
        # Find LOP deduction
        lop_deduction = next((d for d in data["deductions"] if d["key"] == "lop"), None)
        assert lop_deduction is not None, "LOP deduction not found"
        
        # Verify calculation (allow small rounding difference)
        assert abs(lop_deduction["amount"] - expected_lop) < 0.01, \
            f"LOP mismatch: expected {expected_lop:.2f}, got {lop_deduction['amount']}"
        
        # Verify formula in calculation log
        assert "31 days" in lop_deduction["calculation"]["formula_used"]
        assert lop_deduction["calculation"]["input_values"]["actual_days_in_month"] == 31
        
        print(f"✓ LOP calculation correct: {lop_days} days × ₹{expected_daily_rate:.2f}/day = ₹{lop_deduction['amount']}")
    
    def test_simulate_payroll_with_lop_february(self):
        """Test LOP calculation for February 2026 (28 days - non-leap year)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        lop_days = 3
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-02",
                "lop_days": lop_days,
                "bonus": 0,
                "incentive": 0,
                "penalty": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["days_in_month"] == 28  # Feb 2026 has 28 days
        
        # Verify LOP calculation: Gross / 28 days * LOP days
        gross = data["gross_monthly"]
        expected_daily_rate = gross / 28
        expected_lop = expected_daily_rate * lop_days
        
        lop_deduction = next((d for d in data["deductions"] if d["key"] == "lop"), None)
        assert lop_deduction is not None
        assert abs(lop_deduction["amount"] - expected_lop) < 0.01
        assert "28 days" in lop_deduction["calculation"]["formula_used"]
        
        print(f"✓ February LOP correct: {lop_days} days × ₹{expected_daily_rate:.2f}/day = ₹{lop_deduction['amount']}")
    
    def test_simulate_payroll_with_lop_april(self):
        """Test LOP calculation for April (30 days)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        lop_days = 1
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-04",
                "lop_days": lop_days,
                "bonus": 0,
                "incentive": 0,
                "penalty": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["days_in_month"] == 30  # April has 30 days
        
        gross = data["gross_monthly"]
        expected_daily_rate = gross / 30
        
        lop_deduction = next((d for d in data["deductions"] if d["key"] == "lop"), None)
        assert lop_deduction is not None
        assert "30 days" in lop_deduction["calculation"]["formula_used"]
        
        print(f"✓ April LOP correct: {lop_days} day × ₹{expected_daily_rate:.2f}/day = ₹{lop_deduction['amount']}")
    
    def test_simulate_payroll_earnings_breakdown(self):
        """Test earnings breakdown (Basic, HRA, Special Allowance)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-03",
                "lop_days": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        earnings = data["earnings"]
        earning_keys = [e["key"] for e in earnings]
        
        # Verify standard earnings components
        assert "basic" in earning_keys, "Basic salary not found"
        assert "hra" in earning_keys, "HRA not found"
        assert "special_allowance" in earning_keys, "Special Allowance not found"
        
        # Verify each earning has calculation traceability
        for earning in earnings:
            assert "calculation" in earning
            assert "formula_used" in earning["calculation"]
            assert "input_values" in earning["calculation"]
            assert "output_value" in earning["calculation"]
        
        # Verify total earnings
        total = sum(e["amount"] for e in earnings)
        assert abs(total - data["total_earnings"]) < 0.01
        
        print(f"✓ Earnings breakdown: {len(earnings)} components, total=₹{data['total_earnings']}")
    
    def test_simulate_payroll_deductions_with_formulas(self):
        """Test deductions breakdown with formulas (LOP, PF, PT)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-03",
                "lop_days": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        deductions = data["deductions"]
        deduction_keys = [d["key"] for d in deductions]
        
        # Verify standard deductions
        assert "lop" in deduction_keys, "LOP deduction not found"
        assert "pf" in deduction_keys, "PF deduction not found"
        assert "professional_tax" in deduction_keys, "Professional Tax not found"
        
        # Verify each deduction has calculation traceability
        for deduction in deductions:
            assert "calculation" in deduction
            assert "formula_used" in deduction["calculation"]
            assert "input_values" in deduction["calculation"]
            
            # Verify specific formulas
            if deduction["key"] == "lop":
                assert "31 days" in deduction["calculation"]["formula_used"]
                assert "LOP days" in deduction["calculation"]["formula_used"]
            elif deduction["key"] == "pf":
                assert "12%" in deduction["calculation"]["formula_used"]
            elif deduction["key"] == "professional_tax":
                assert "Slab" in deduction["calculation"]["formula_used"]
        
        print(f"✓ Deductions breakdown: {len(deductions)} components with formulas")
    
    def test_simulate_payroll_with_bonus(self):
        """Test simulation with bonus"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        bonus_amount = 5000
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-03",
                "lop_days": 0,
                "bonus": bonus_amount
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find bonus in earnings
        bonus_earning = next((e for e in data["earnings"] if e["key"] == "bonus"), None)
        assert bonus_earning is not None, "Bonus not found in earnings"
        assert bonus_earning["amount"] == bonus_amount
        
        print(f"✓ Bonus added: ₹{bonus_amount}")
    
    def test_simulate_payroll_field_traceability(self):
        """Test field-level traceability (input → formula → output)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2026-03",
                "lop_days": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify calculation_log exists
        assert "calculation_log" in data
        assert len(data["calculation_log"]) > 0
        
        # Verify each log entry has required fields
        for log_entry in data["calculation_log"]:
            assert "id" in log_entry
            assert "component_name" in log_entry
            assert "input_values" in log_entry
            assert "formula_used" in log_entry
            assert "output_value" in log_entry
            assert "rule_id" in log_entry
            assert "rule_version" in log_entry
            assert "calculated_at" in log_entry
        
        print(f"✓ Field traceability: {len(data['calculation_log'])} calculation entries logged")


class TestPayrollEngineRunPayroll:
    """Run Payroll - Creates Draft Register"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
    
    def test_run_payroll_creates_draft(self):
        """Test running payroll creates draft register"""
        # Use a test month to avoid conflicts
        test_month = "2026-03"
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["month"] == test_month
        assert data["status"] == "draft"
        assert data["total_employees"] >= 0
        assert "total_gross_salary" in data
        assert "total_net_payable" in data
        assert "department_summary" in data
        
        print(f"✓ Payroll run: {data['total_employees']} employees, Net=₹{data['total_net_payable']}")
    
    def test_run_payroll_requires_month(self):
        """Test run payroll requires month parameter"""
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={}
        )
        
        assert response.status_code == 400
        assert "Month is required" in response.json()["detail"]
        print("✓ Month validation works")


class TestPayrollEngineRegister:
    """Payroll Register Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
    
    def test_get_payroll_register_list(self):
        """Test getting payroll register list"""
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/register",
            headers=self.hr_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            register = data[0]
            assert "month" in register
            assert "status" in register
            assert "total_employees" in register
            print(f"✓ Found {len(data)} payroll registers")
        else:
            print("✓ No payroll registers found (empty list)")
    
    def test_get_payroll_register_details(self):
        """Test getting detailed payroll register with calculations"""
        # First ensure we have a register
        requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": "2026-03"}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/register/2026-03/details",
            headers=self.hr_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "register" in data
        assert "calculations" in data
        
        if data["calculations"]:
            calc = data["calculations"][0]
            assert "employee_id" in calc
            assert "employee_name" in calc
            assert "gross_monthly" in calc
            assert "net_payable" in calc
            assert "earnings" in calc
            assert "deductions" in calc
            print(f"✓ Register details: {len(data['calculations'])} employee calculations")
        else:
            print("✓ Register details retrieved (no calculations)")


class TestPayrollEngineApproval:
    """Approval Workflow Tests - HR Manager → Admin"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR and Admin tokens"""
        hr_login = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = hr_login.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        self.admin_token = admin_login.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_submit_for_approval_hr_manager(self):
        """Test HR Manager can submit payroll for approval"""
        test_month = "2026-03"
        
        # First run payroll to create draft
        requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        
        # Submit for approval
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/submit-for-approval",
            headers=self.hr_headers,
            json={"month": test_month, "remarks": "Ready for review"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "submitted for admin approval" in data["message"].lower()
        print("✓ HR Manager submitted payroll for approval")
    
    def test_approve_payroll_admin(self):
        """Test Admin can approve payroll"""
        test_month = "2026-03"
        
        # Ensure payroll is in pending_admin_approval status
        # First run and submit
        requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        requests.post(
            f"{BASE_URL}/api/payroll/engine/submit-for-approval",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        
        # Admin approves
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/approve",
            headers=self.admin_headers,
            json={"month": test_month, "remarks": "Approved"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "approved" in data["message"].lower()
        print("✓ Admin approved payroll")
    
    def test_reject_payroll_requires_reason(self):
        """Test rejection requires reason"""
        test_month = "2026-03"
        
        # Run and submit first
        requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        requests.post(
            f"{BASE_URL}/api/payroll/engine/submit-for-approval",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        
        # Try to reject without reason
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/reject",
            headers=self.admin_headers,
            json={"month": test_month, "reason": ""}
        )
        
        assert response.status_code == 400
        assert "reason" in response.json()["detail"].lower()
        print("✓ Rejection requires reason")


class TestPayrollEngineExport:
    """Export Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
    
    def test_export_payroll_data(self):
        """Test exporting payroll data"""
        # Ensure we have data
        requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": "2026-03"}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/export/2026-03",
            headers=self.hr_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "month" in data
        assert "data" in data
        assert "columns" in data
        
        if data["data"]:
            row = data["data"][0]
            assert "Employee ID" in row or "Employee Name" in row
            print(f"✓ Export data: {len(data['data'])} rows, {len(data['columns'])} columns")
        else:
            print("✓ Export endpoint works (no data)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
