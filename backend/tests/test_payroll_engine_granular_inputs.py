"""
Payroll Engine Granular Inputs Tests
Tests for P0 features:
1. Granular payroll inputs - arrears, advance_recovery, loan_emi, travel_reimbursement, medical_reimbursement
2. Simulation correctly calculates all earnings and deductions with full breakdown
3. Running payroll multiple times for same month does NOT create duplicate draft records
4. PF calculation: min(Basic, 15000) x 12%
5. TDS calculation applies New Regime slabs correctly
6. Professional Tax applies Maharashtra slabs
7. API authentication - only HR roles can access payroll endpoints
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HR_MANAGER_CREDS = {"employee_id": "EMP002", "password": "hr123"}
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}
CONSULTANT_CREDS = {"employee_id": "EMP004", "password": "consultant123"}


class TestGranularPayrollInputs:
    """P0: Test all granular payroll inputs work in simulation API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token and employee list"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        assert login_resp.status_code == 200, f"HR login failed: {login_resp.text}"
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        # Get employees
        emp_resp = requests.get(f"{BASE_URL}/api/employees/all", headers=self.hr_headers)
        self.employees = emp_resp.json()
        self.test_employee = self.employees[0] if self.employees else None
    
    def test_simulate_with_arrears(self):
        """Test arrears field is passed and calculated correctly"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        arrears_amount = 5000
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0,
                "arrears": arrears_amount,
                "arrears_reason": "Salary revision from October"
            }
        )
        
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Find arrears in earnings
        arrears_earning = next((e for e in data["earnings"] if e["key"] == "arrears"), None)
        assert arrears_earning is not None, f"Arrears not found in earnings. Earnings: {[e['key'] for e in data['earnings']]}"
        assert arrears_earning["amount"] == arrears_amount, f"Arrears amount mismatch: expected {arrears_amount}, got {arrears_earning['amount']}"
        
        # Verify arrears has calculation traceability
        assert "calculation" in arrears_earning
        assert "formula_used" in arrears_earning["calculation"]
        
        print(f"✓ Arrears: ₹{arrears_amount} added to earnings with reason tracking")
    
    def test_simulate_with_advance_recovery(self):
        """Test advance_recovery field is passed and calculated correctly"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        advance_amount = 10000
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0,
                "advance_recovery": advance_amount,
                "advance_reason": "Salary advance from November"
            }
        )
        
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Find advance_recovery in deductions
        advance_deduction = next((d for d in data["deductions"] if d["key"] == "advance_recovery"), None)
        assert advance_deduction is not None, f"Advance recovery not found in deductions. Deductions: {[d['key'] for d in data['deductions']]}"
        assert advance_deduction["amount"] == advance_amount, f"Advance amount mismatch: expected {advance_amount}, got {advance_deduction['amount']}"
        
        print(f"✓ Advance Recovery: ₹{advance_amount} deducted correctly")
    
    def test_simulate_with_loan_emi(self):
        """Test loan_emi field is passed and calculated correctly"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        loan_emi_amount = 15000
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0,
                "loan_emi": loan_emi_amount,
                "loan_type": "personal"
            }
        )
        
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Find loan_emi in deductions
        loan_deduction = next((d for d in data["deductions"] if d["key"] == "loan_emi"), None)
        assert loan_deduction is not None, f"Loan EMI not found in deductions. Deductions: {[d['key'] for d in data['deductions']]}"
        assert loan_deduction["amount"] == loan_emi_amount, f"Loan EMI amount mismatch: expected {loan_emi_amount}, got {loan_deduction['amount']}"
        
        # Verify loan type is in the name or details
        assert "personal" in loan_deduction.get("name", "").lower() or "personal" in loan_deduction.get("details", "").lower(), \
            f"Loan type not reflected. Name: {loan_deduction.get('name')}, Details: {loan_deduction.get('details')}"
        
        print(f"✓ Loan EMI: ₹{loan_emi_amount} (personal) deducted correctly")
    
    def test_simulate_with_travel_reimbursement(self):
        """Test travel_reimbursement field is passed and calculated correctly"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        travel_amount = 8000
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0,
                "travel_reimbursement": travel_amount
            }
        )
        
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Find travel_reimbursement in reimbursements_breakdown
        reimbursements = data.get("reimbursements_breakdown", [])
        travel_reimb = next((r for r in reimbursements if r["key"] == "travel_reimbursement"), None)
        assert travel_reimb is not None, f"Travel reimbursement not found. Reimbursements: {[r['key'] for r in reimbursements]}"
        assert travel_reimb["amount"] == travel_amount, f"Travel amount mismatch: expected {travel_amount}, got {travel_reimb['amount']}"
        
        # Verify total_reimbursements includes travel
        assert data["total_reimbursements"] >= travel_amount
        
        print(f"✓ Travel Reimbursement: ₹{travel_amount} added to net payable")
    
    def test_simulate_with_medical_reimbursement(self):
        """Test medical_reimbursement field is passed and calculated correctly"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        medical_amount = 5000
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0,
                "medical_reimbursement": medical_amount
            }
        )
        
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Find medical_reimbursement in reimbursements_breakdown
        reimbursements = data.get("reimbursements_breakdown", [])
        medical_reimb = next((r for r in reimbursements if r["key"] == "medical_reimbursement"), None)
        assert medical_reimb is not None, f"Medical reimbursement not found. Reimbursements: {[r['key'] for r in reimbursements]}"
        assert medical_reimb["amount"] == medical_amount, f"Medical amount mismatch: expected {medical_amount}, got {medical_reimb['amount']}"
        
        print(f"✓ Medical Reimbursement: ₹{medical_amount} added to net payable")
    
    def test_simulate_with_all_granular_inputs(self):
        """Test all granular inputs together in one simulation"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        # All granular inputs
        inputs = {
            "employee_id": self.test_employee["id"],
            "month": "2024-12",
            "lop_days": 2,
            # Earnings
            "bonus": 10000,
            "incentive": 5000,
            "arrears": 3000,
            "arrears_reason": "Salary revision",
            "overtime_hours": 10,
            # Reimbursements
            "travel_reimbursement": 8000,
            "medical_reimbursement": 5000,
            "food_reimbursement": 2000,
            "telephone_reimbursement": 1000,
            "other_reimbursement": 500,
            # Deductions
            "penalty": 1000,
            "penalty_reason": "Late arrival",
            "advance_recovery": 5000,
            "advance_reason": "Salary advance",
            "loan_emi": 15000,
            "loan_type": "home",
            "other_deduction": 500,
            "other_deduction_name": "Canteen charges"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json=inputs
        )
        
        assert response.status_code == 200, f"Simulate failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        
        # Verify all earnings are present
        earning_keys = [e["key"] for e in data["earnings"]]
        assert "bonus" in earning_keys, "Bonus not found"
        assert "incentive" in earning_keys, "Incentive not found"
        assert "arrears" in earning_keys, "Arrears not found"
        
        # Verify all deductions are present
        deduction_keys = [d["key"] for d in data["deductions"]]
        assert "lop" in deduction_keys, "LOP not found"
        assert "penalty" in deduction_keys, "Penalty not found"
        assert "advance_recovery" in deduction_keys, "Advance recovery not found"
        assert "loan_emi" in deduction_keys, "Loan EMI not found"
        assert "other_deduction" in deduction_keys, "Other deduction not found"
        
        # Verify all reimbursements are present
        reimb_keys = [r["key"] for r in data.get("reimbursements_breakdown", [])]
        assert "travel_reimbursement" in reimb_keys, "Travel reimbursement not found"
        assert "medical_reimbursement" in reimb_keys, "Medical reimbursement not found"
        assert "food_reimbursement" in reimb_keys, "Food reimbursement not found"
        assert "telephone_reimbursement" in reimb_keys, "Telephone reimbursement not found"
        assert "other_reimbursement" in reimb_keys, "Other reimbursement not found"
        
        # Verify net payable calculation
        expected_net = data["total_earnings"] - data["total_deductions"] + data["total_reimbursements"]
        assert abs(data["net_payable"] - expected_net) < 1, f"Net payable mismatch: expected {expected_net}, got {data['net_payable']}"
        
        print(f"✓ All granular inputs work together:")
        print(f"  - Earnings: {len(data['earnings'])} components = ₹{data['total_earnings']}")
        print(f"  - Deductions: {len(data['deductions'])} components = ₹{data['total_deductions']}")
        print(f"  - Reimbursements: {len(data.get('reimbursements_breakdown', []))} components = ₹{data['total_reimbursements']}")
        print(f"  - Net Payable: ₹{data['net_payable']}")


class TestDuplicateDraftPrevention:
    """P1: Test running payroll multiple times does NOT create duplicate drafts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        assert login_resp.status_code == 200
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
    
    def test_run_payroll_twice_no_duplicates(self):
        """Test running payroll twice for same month doesn't create duplicates"""
        test_month = "2024-12"
        
        # Run payroll first time
        response1 = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        assert response1.status_code == 200, f"First run failed: {response1.text}"
        data1 = response1.json()
        assert data1["success"] == True
        register_id_1 = data1.get("register_id")
        
        # Run payroll second time
        response2 = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=self.hr_headers,
            json={"month": test_month}
        )
        assert response2.status_code == 200, f"Second run failed: {response2.text}"
        data2 = response2.json()
        assert data2["success"] == True
        register_id_2 = data2.get("register_id")
        
        # Get all registers for this month
        registers_resp = requests.get(
            f"{BASE_URL}/api/payroll/engine/register?month={test_month}",
            headers=self.hr_headers
        )
        assert registers_resp.status_code == 200
        registers = registers_resp.json()
        
        # Filter for non-cancelled registers
        active_registers = [r for r in registers if r.get("status") != "cancelled"]
        
        # Should only have ONE active register for this month
        assert len(active_registers) == 1, f"Expected 1 active register, found {len(active_registers)}: {[r.get('status') for r in active_registers]}"
        
        print(f"✓ No duplicate drafts: Running payroll twice created only 1 active register")
        print(f"  - First register ID: {register_id_1}")
        print(f"  - Second register ID: {register_id_2}")
    
    def test_run_payroll_three_times_no_duplicates(self):
        """Test running payroll three times still results in single draft"""
        test_month = "2024-11"
        
        # Run payroll three times
        for i in range(3):
            response = requests.post(
                f"{BASE_URL}/api/payroll/engine/run",
                headers=self.hr_headers,
                json={"month": test_month}
            )
            assert response.status_code == 200, f"Run {i+1} failed: {response.text}"
        
        # Get all registers for this month
        registers_resp = requests.get(
            f"{BASE_URL}/api/payroll/engine/register?month={test_month}",
            headers=self.hr_headers
        )
        registers = registers_resp.json()
        active_registers = [r for r in registers if r.get("status") != "cancelled"]
        
        assert len(active_registers) == 1, f"Expected 1 active register after 3 runs, found {len(active_registers)}"
        
        print(f"✓ No duplicate drafts after 3 runs: Only 1 active register exists")


class TestStatutoryCalculations:
    """Test statutory deduction calculations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token and employee"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        emp_resp = requests.get(f"{BASE_URL}/api/employees/all", headers=self.hr_headers)
        self.employees = emp_resp.json()
        self.test_employee = self.employees[0] if self.employees else None
    
    def test_pf_calculation_formula(self):
        """Test PF calculation: min(Basic, 15000) x 12%"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find PF deduction
        pf_deduction = next((d for d in data["deductions"] if d["key"] == "pf"), None)
        assert pf_deduction is not None, "PF deduction not found"
        
        # Verify PF calculation
        basic_monthly = data["basic_monthly"]
        pf_base = min(basic_monthly, 15000)
        expected_pf = pf_base * 0.12
        
        assert abs(pf_deduction["amount"] - expected_pf) < 0.01, \
            f"PF mismatch: expected {expected_pf:.2f}, got {pf_deduction['amount']}"
        
        # Verify formula in calculation
        assert "12%" in pf_deduction["calculation"]["formula_used"]
        assert pf_deduction["calculation"]["input_values"]["pf_ceiling"] == 15000
        
        print(f"✓ PF Calculation: min(₹{basic_monthly:.2f}, ₹15,000) × 12% = ₹{pf_deduction['amount']}")
    
    def test_professional_tax_maharashtra_slabs(self):
        """Test Professional Tax applies Maharashtra slabs"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find PT deduction
        pt_deduction = next((d for d in data["deductions"] if d["key"] == "professional_tax"), None)
        assert pt_deduction is not None, "Professional Tax not found"
        
        gross = data["gross_monthly"]
        
        # Maharashtra PT slabs
        if gross <= 7500:
            expected_pt = 0
        elif gross <= 10000:
            expected_pt = 175
        else:
            expected_pt = 200
        
        assert pt_deduction["amount"] == expected_pt, \
            f"PT mismatch for gross ₹{gross}: expected ₹{expected_pt}, got ₹{pt_deduction['amount']}"
        
        # Verify slab info in calculation
        assert "Slab" in pt_deduction["calculation"]["formula_used"]
        
        print(f"✓ Professional Tax: Gross ₹{gross} → PT ₹{pt_deduction['amount']} (Maharashtra slab)")
    
    def test_tds_new_regime_slabs(self):
        """Test TDS calculation applies New Regime slabs correctly"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify TDS details
        tds_details = data.get("tds_details", {})
        assert tds_details.get("regime") == "new", f"Expected new regime, got {tds_details.get('regime')}"
        
        # Verify standard deduction of 75000 is applied
        gross_annual = data["gross_annual"]
        taxable_income = tds_details.get("taxable_income", 0)
        
        # Taxable income should be gross_annual - 75000 (standard deduction)
        expected_taxable = max(0, gross_annual - 75000)
        assert abs(taxable_income - expected_taxable) < 1, \
            f"Taxable income mismatch: expected {expected_taxable}, got {taxable_income}"
        
        # Find TDS deduction
        tds_deduction = next((d for d in data["deductions"] if d["key"] == "tds"), None)
        if tds_deduction:
            assert tds_deduction["amount"] == tds_details["monthly_tds"]
            print(f"✓ TDS (New Regime): Annual CTC ₹{gross_annual} → Taxable ₹{taxable_income} → Monthly TDS ₹{tds_details['monthly_tds']}")
        else:
            print(f"✓ TDS: No TDS applicable (taxable income ₹{taxable_income} below threshold)")


class TestAPIAuthentication:
    """Test API authentication - only HR roles can access payroll endpoints"""
    
    def test_sales_cannot_access_simulate(self):
        """Test Sales role cannot access simulate endpoint"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        if login_resp.status_code != 200:
            pytest.skip("Sales user login failed")
        
        sales_token = login_resp.json()["access_token"]
        sales_headers = {"Authorization": f"Bearer {sales_token}"}
        
        # Get any employee ID
        hr_login = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        hr_headers = {"Authorization": f"Bearer {hr_login.json()['access_token']}"}
        emp_resp = requests.get(f"{BASE_URL}/api/employees/all", headers=hr_headers)
        employees = emp_resp.json()
        
        if not employees:
            pytest.skip("No employees found")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=sales_headers,
            json={
                "employee_id": employees[0]["id"],
                "month": "2024-12",
                "lop_days": 0
            }
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Sales role correctly denied access to simulate endpoint")
    
    def test_consultant_cannot_access_run_payroll(self):
        """Test Consultant role cannot access run payroll endpoint"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=CONSULTANT_CREDS)
        if login_resp.status_code != 200:
            pytest.skip("Consultant user login failed")
        
        consultant_token = login_resp.json()["access_token"]
        consultant_headers = {"Authorization": f"Bearer {consultant_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=consultant_headers,
            json={"month": "2024-12"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Consultant role correctly denied access to run payroll endpoint")
    
    def test_hr_manager_can_access_all_endpoints(self):
        """Test HR Manager can access all payroll endpoints"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        hr_token = login_resp.json()["access_token"]
        hr_headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Test simulate
        emp_resp = requests.get(f"{BASE_URL}/api/employees/all", headers=hr_headers)
        employees = emp_resp.json()
        
        if employees:
            sim_resp = requests.post(
                f"{BASE_URL}/api/payroll/engine/simulate",
                headers=hr_headers,
                json={"employee_id": employees[0]["id"], "month": "2024-12", "lop_days": 0}
            )
            assert sim_resp.status_code == 200, f"Simulate failed: {sim_resp.text}"
        
        # Test run payroll
        run_resp = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=hr_headers,
            json={"month": "2024-12"}
        )
        assert run_resp.status_code == 200, f"Run payroll failed: {run_resp.text}"
        
        # Test get register
        reg_resp = requests.get(
            f"{BASE_URL}/api/payroll/engine/register",
            headers=hr_headers
        )
        assert reg_resp.status_code == 200, f"Get register failed: {reg_resp.text}"
        
        print("✓ HR Manager has access to all payroll endpoints")
    
    def test_admin_can_approve_payroll(self):
        """Test Admin can approve payroll"""
        # HR runs and submits
        hr_login = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        hr_headers = {"Authorization": f"Bearer {hr_login.json()['access_token']}"}
        
        requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=hr_headers,
            json={"month": "2024-12"}
        )
        requests.post(
            f"{BASE_URL}/api/payroll/engine/submit-for-approval",
            headers=hr_headers,
            json={"month": "2024-12"}
        )
        
        # Admin approves
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        
        approve_resp = requests.post(
            f"{BASE_URL}/api/payroll/engine/approve",
            headers=admin_headers,
            json={"month": "2024-12", "remarks": "Approved for testing"}
        )
        
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"
        print("✓ Admin can approve payroll")


class TestLOPCalculation:
    """Test LOP calculation uses Gross / Actual Days in Month formula"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get HR token and employee"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        self.hr_token = login_resp.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        emp_resp = requests.get(f"{BASE_URL}/api/employees/all", headers=self.hr_headers)
        self.employees = emp_resp.json()
        self.test_employee = self.employees[0] if self.employees else None
    
    def test_lop_december_31_days(self):
        """Test LOP for December (31 days)"""
        if not self.test_employee:
            pytest.skip("No employees found")
        
        lop_days = 3
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/simulate",
            headers=self.hr_headers,
            json={
                "employee_id": self.test_employee["id"],
                "month": "2024-12",
                "lop_days": lop_days
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["days_in_month"] == 31, f"December should have 31 days, got {data['days_in_month']}"
        
        gross = data["gross_monthly"]
        expected_daily = gross / 31
        expected_lop = expected_daily * lop_days
        
        lop_deduction = next((d for d in data["deductions"] if d["key"] == "lop"), None)
        assert lop_deduction is not None
        assert abs(lop_deduction["amount"] - expected_lop) < 0.01
        
        print(f"✓ December LOP: ₹{gross}/31 × {lop_days} = ₹{lop_deduction['amount']:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
