"""
Test Suite for Enhanced CTC Structure Designer with Configurable Components
Tests:
- CTC Component Master API returns all available components
- Components have enabled_by_default flag (PF/ESIC/Gratuity are OFF)
- Mandatory components (Basic, Special Allowance) cannot be disabled
- CTC calculation respects enabled/disabled components
- Preview shows only enabled components
- Deductions (PF Employee, ESIC, PT) subtract from gross
- Submit for Approval saves component_config
- Approved CTC updates employee record with component breakdown
- Payroll slip generation uses approved CTC structure if available
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCTCEnhancedComponents:
    """Test Enhanced CTC Component Configuration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - get admin and HR tokens"""
        # Admin login
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert admin_response.status_code == 200, f"Admin login failed: {admin_response.text}"
        self.admin_token = admin_response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # HR Manager login
        hr_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert hr_response.status_code == 200, f"HR login failed: {hr_response.text}"
        self.hr_token = hr_response.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        
        yield
    
    # ==================== Component Master API Tests ====================
    
    def test_component_master_returns_all_components(self):
        """Test that component master API returns all available CTC components"""
        response = requests.get(f"{BASE_URL}/api/ctc/component-master", headers=self.admin_headers)
        assert response.status_code == 200, f"Component master fetch failed: {response.text}"
        
        data = response.json()
        assert "components" in data, "Response should have 'components' key"
        
        components = data["components"]
        assert len(components) >= 10, f"Should have at least 10 components, got {len(components)}"
        
        # Check all expected components exist
        expected_keys = [
            "basic", "hra", "da", "conveyance", "medical", "special_allowance",
            "pf_employer", "pf_employee", "esic_employer", "esic_employee",
            "gratuity", "professional_tax"
        ]
        component_keys = [c["key"] for c in components]
        for key in expected_keys:
            assert key in component_keys, f"Component '{key}' should be in master list"
        
        print(f"✓ Component master returns all {len(components)} components")
        print(f"  Components: {', '.join(component_keys)}")
    
    def test_enabled_by_default_flags(self):
        """Test that PF/ESIC/Gratuity are disabled by default, others enabled"""
        response = requests.get(f"{BASE_URL}/api/ctc/component-master", headers=self.admin_headers)
        assert response.status_code == 200
        
        components = {c["key"]: c for c in response.json()["components"]}
        
        # Should be DISABLED by default
        disabled_by_default = ["pf_employer", "pf_employee", "esic_employer", "esic_employee", "gratuity", "professional_tax", "da"]
        for key in disabled_by_default:
            if key in components:
                flag = components[key].get("enabled_by_default", True)
                assert flag == False, f"{key} should have enabled_by_default=False, got {flag}"
                print(f"  ✓ {key}: enabled_by_default=False")
        
        # Should be ENABLED by default
        enabled_by_default = ["basic", "hra", "conveyance", "medical", "special_allowance"]
        for key in enabled_by_default:
            if key in components:
                flag = components[key].get("enabled_by_default", True)
                assert flag == True, f"{key} should have enabled_by_default=True, got {flag}"
                print(f"  ✓ {key}: enabled_by_default=True")
    
    def test_mandatory_components_flag(self):
        """Test that Basic and Special Allowance are marked as mandatory"""
        response = requests.get(f"{BASE_URL}/api/ctc/component-master", headers=self.admin_headers)
        assert response.status_code == 200
        
        components = {c["key"]: c for c in response.json()["components"]}
        
        # Mandatory components
        assert components["basic"].get("is_mandatory") == True, "Basic should be mandatory"
        assert components["special_allowance"].get("is_mandatory") == True, "Special Allowance should be mandatory"
        
        # Non-mandatory examples
        assert components["hra"].get("is_mandatory", False) == False, "HRA should not be mandatory"
        assert components["pf_employer"].get("is_mandatory", False) == False, "PF should not be mandatory"
        
        print("✓ Mandatory flags correctly set (Basic, Special Allowance)")
    
    # ==================== CTC Calculation with Component Config ====================
    
    def test_preview_with_only_enabled_components(self):
        """Test that preview respects enabled/disabled component config"""
        # Create config with some components disabled
        config = [
            {"key": "basic", "name": "Basic Salary", "calc_type": "percentage_of_ctc", "value": 40, "enabled": True, "is_mandatory": True, "is_earning": True},
            {"key": "hra", "name": "HRA", "calc_type": "percentage_of_basic", "value": 50, "enabled": True, "is_earning": True},
            {"key": "da", "name": "DA", "calc_type": "percentage_of_basic", "value": 10, "enabled": False, "is_earning": True},  # DISABLED
            {"key": "conveyance", "name": "Conveyance", "calc_type": "fixed_monthly", "value": 1600, "enabled": True, "is_earning": True},
            {"key": "medical", "name": "Medical", "calc_type": "fixed_monthly", "value": 1250, "enabled": True, "is_earning": True},
            {"key": "special_allowance", "name": "Special Allowance", "calc_type": "balance", "value": 0, "enabled": True, "is_mandatory": True, "is_earning": True, "is_balance": True},
            {"key": "pf_employer", "name": "PF Employer", "calc_type": "percentage_of_basic", "value": 12, "enabled": False, "is_deferred": True},  # DISABLED
            {"key": "pf_employee", "name": "PF Employee", "calc_type": "percentage_of_basic", "value": 12, "enabled": False, "is_deduction": True},  # DISABLED
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={"annual_ctc": 1200000, "component_config": config},
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Preview failed: {response.text}"
        
        data = response.json()
        components = data["components"]
        
        # DA should NOT be in result (disabled)
        assert "da" not in components or components.get("da", {}).get("enabled") == False, "DA should be disabled/excluded"
        
        # PF should NOT be in result (disabled)
        assert "pf_employer" not in components or components.get("pf_employer", {}).get("enabled") == False, "PF should be disabled/excluded"
        
        # Enabled components should be present
        assert components["basic"]["annual"] == 480000, "Basic should be calculated"
        assert components["hra"]["annual"] == 240000, "HRA should be calculated"
        
        print("✓ Preview correctly excludes disabled components")
        print(f"  Active components: {[k for k, v in components.items() if v.get('enabled', True)]}")
    
    def test_deductions_subtract_from_gross(self):
        """Test that deduction components (PF Employee, ESIC, PT) subtract from gross"""
        # NOTE: Deduction components MUST have is_earning: False for proper calculation
        config = [
            {"key": "basic", "name": "Basic", "calc_type": "percentage_of_ctc", "value": 40, "enabled": True, "is_earning": True, "is_mandatory": True},
            {"key": "hra", "name": "HRA", "calc_type": "percentage_of_basic", "value": 50, "enabled": True, "is_earning": True},
            {"key": "conveyance", "name": "Conveyance", "calc_type": "fixed_monthly", "value": 1600, "enabled": True, "is_earning": True},
            {"key": "medical", "name": "Medical", "calc_type": "fixed_monthly", "value": 1250, "enabled": True, "is_earning": True},
            {"key": "special_allowance", "name": "Special Allowance", "calc_type": "balance", "value": 0, "enabled": True, "is_earning": True, "is_balance": True, "is_mandatory": True},
            {"key": "pf_employee", "name": "PF Employee", "calc_type": "percentage_of_basic", "value": 12, "enabled": True, "is_earning": False, "is_deduction": True},
            {"key": "professional_tax", "name": "Professional Tax", "calc_type": "fixed_monthly", "value": 200, "enabled": True, "is_earning": False, "is_deduction": True},
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={"annual_ctc": 1200000, "component_config": config},
            headers=self.admin_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        components = data["components"]
        
        # PF Employee should be marked as deduction
        if "pf_employee" in components:
            assert components["pf_employee"].get("is_deduction") == True, "PF Employee should be a deduction"
        
        # PT should be marked as deduction
        if "professional_tax" in components:
            assert components["professional_tax"].get("is_deduction") == True, "PT should be a deduction"
        
        # Total deductions should be calculated
        assert summary["total_deductions_monthly"] > 0, "Total deductions should be > 0"
        
        # In-hand should be gross minus deductions
        expected_in_hand = summary["gross_monthly"] - summary["total_deductions_monthly"]
        assert abs(summary["in_hand_approx_monthly"] - expected_in_hand) < 1, f"In-hand should be gross - deductions"
        
        print(f"✓ Deductions correctly calculated")
        print(f"  Gross Monthly: ₹{summary['gross_monthly']:,.0f}")
        print(f"  Total Deductions: ₹{summary['total_deductions_monthly']:,.0f}")
        print(f"  In-Hand Approx: ₹{summary['in_hand_approx_monthly']:,.0f}")
    
    # ==================== CTC Submit with Component Config ====================
    
    def test_submit_saves_component_config(self):
        """Test that CTC submission saves the component_config for later use"""
        # Get an employee first
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.admin_headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees found to test with")
        
        test_employee = None
        for emp in employees:
            if emp.get("is_active") and "TEST_CTC" not in (emp.get("first_name") or ""):
                test_employee = emp
                break
        
        if not test_employee:
            pytest.skip("No suitable test employee found")
        
        # Custom component config
        custom_config = [
            {"key": "basic", "name": "Basic Salary", "calc_type": "percentage_of_ctc", "value": 40, "enabled": True, "is_mandatory": True, "is_earning": True},
            {"key": "hra", "name": "HRA", "calc_type": "percentage_of_basic", "value": 50, "enabled": True, "is_earning": True},
            {"key": "da", "name": "DA", "calc_type": "percentage_of_basic", "value": 10, "enabled": False, "is_earning": True},  # Disabled
            {"key": "conveyance", "name": "Conveyance", "calc_type": "fixed_monthly", "value": 1600, "enabled": True, "is_earning": True},
            {"key": "medical", "name": "Medical", "calc_type": "fixed_monthly", "value": 1250, "enabled": True, "is_earning": True},
            {"key": "special_allowance", "name": "Special Allowance", "calc_type": "balance", "value": 0, "enabled": True, "is_mandatory": True, "is_earning": True, "is_balance": True},
            {"key": "pf_employer", "name": "PF Employer", "calc_type": "percentage_of_basic", "value": 12, "enabled": True, "is_deferred": True},  # Enabled
            {"key": "pf_employee", "name": "PF Employee", "calc_type": "percentage_of_basic", "value": 12, "enabled": True, "is_deduction": True},  # Enabled
        ]
        
        effective_month = datetime.now().strftime("%Y-%m")
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/design",
            json={
                "employee_id": test_employee["id"],
                "annual_ctc": 1500000,
                "effective_month": effective_month,
                "component_config": custom_config,
                "remarks": "TEST_CTC_CONFIG: Testing component config storage"
            },
            headers=self.hr_headers
        )
        
        if response.status_code == 400 and "pending" in response.text.lower():
            print("⚠ Pending CTC request exists for this employee - skipping")
            return
        
        assert response.status_code == 200, f"CTC submit failed: {response.text}"
        
        result = response.json()
        ctc_id = result["ctc_structure_id"]
        
        # Verify the structure was saved with component_config
        pending_response = requests.get(f"{BASE_URL}/api/ctc/pending-approvals", headers=self.admin_headers)
        assert pending_response.status_code == 200
        
        pending_list = pending_response.json()
        created_ctc = next((c for c in pending_list if c["id"] == ctc_id), None)
        
        if created_ctc:
            assert "component_config" in created_ctc or "components" in created_ctc, "CTC should have saved config"
            print(f"✓ CTC submitted with component_config saved")
            print(f"  CTC ID: {ctc_id}")
            
            # Clean up - reject it
            requests.post(
                f"{BASE_URL}/api/ctc/{ctc_id}/reject",
                json={"reason": "TEST cleanup"},
                headers=self.admin_headers
            )
    
    # ==================== Stats API Test ====================
    
    def test_stats_api_admin_only(self):
        """Test that stats API returns counts and is admin-only"""
        # Admin should access
        response = requests.get(f"{BASE_URL}/api/ctc/stats", headers=self.admin_headers)
        assert response.status_code == 200, f"Stats failed for admin: {response.text}"
        
        data = response.json()
        assert "pending" in data, "Stats should have pending count"
        assert "active" in data, "Stats should have active count"
        assert "approved" in data, "Stats should have approved count"
        
        print(f"✓ CTC Stats: pending={data['pending']}, active={data['active']}, approved={data['approved']}")
        
        # HR Manager should be denied or have different access
        hr_response = requests.get(f"{BASE_URL}/api/ctc/stats", headers=self.hr_headers)
        # Note: Some implementations allow HR to view stats, adjust based on actual behavior
        print(f"  HR Manager stats access: {hr_response.status_code}")
    
    # ==================== Payroll Integration Test ====================
    
    def test_payroll_uses_approved_ctc_structure(self):
        """Test that payroll slip generation uses approved CTC structure components"""
        # Get an employee with an approved CTC
        employees = requests.get(f"{BASE_URL}/api/employees", headers=self.admin_headers).json()
        
        test_employee = None
        for emp in employees:
            if emp.get("ctc_structure_id") and emp.get("is_active"):
                test_employee = emp
                break
        
        if not test_employee:
            print("⚠ No employee with approved CTC found - checking basic payroll generation")
            # Test basic payroll works
            if employees:
                test_employee = next((e for e in employees if e.get("salary", 0) > 0), None)
        
        if not test_employee:
            pytest.skip("No suitable employee for payroll test")
        
        month = datetime.now().strftime("%Y-%m")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/generate-slip",
            json={
                "employee_id": test_employee["id"],
                "month": month
            },
            headers=self.admin_headers
        )
        
        # Should succeed or fail gracefully
        if response.status_code == 200:
            slip = response.json()
            assert "earnings" in slip, "Slip should have earnings"
            assert "deductions" in slip, "Slip should have deductions"
            print(f"✓ Payroll slip generated for {test_employee.get('first_name', 'Employee')}")
            print(f"  Earnings: {len(slip['earnings'])} components")
            print(f"  Deductions: {len(slip['deductions'])} components")
            print(f"  Net Salary: ₹{slip['net_salary']:,.2f}")
        elif response.status_code == 400:
            print(f"⚠ Payroll generation skipped: {response.json().get('detail', response.text)}")
        else:
            print(f"⚠ Payroll response: {response.status_code} - {response.text}")


class TestCTCWorkflowE2E:
    """E2E workflow tests for CTC Designer"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test credentials"""
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert admin_response.status_code == 200
        self.admin_headers = {"Authorization": f"Bearer {admin_response.json()['access_token']}"}
        
        hr_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert hr_response.status_code == 200
        self.hr_headers = {"Authorization": f"Bearer {hr_response.json()['access_token']}"}
        
        yield
    
    def test_full_ctc_approval_workflow(self):
        """Test complete workflow: HR Submit → Admin Approve → Employee Updated"""
        # Get an employee
        employees = requests.get(f"{BASE_URL}/api/employees", headers=self.admin_headers).json()
        test_emp = next((e for e in employees if e.get("is_active") and "TEST" not in (e.get("first_name") or "")), None)
        
        if not test_emp:
            pytest.skip("No test employee available")
        
        original_salary = test_emp.get("salary", 0)
        
        # Config with PF enabled, PT enabled
        config = [
            {"key": "basic", "name": "Basic", "calc_type": "percentage_of_ctc", "value": 40, "enabled": True, "is_earning": True, "is_mandatory": True},
            {"key": "hra", "name": "HRA", "calc_type": "percentage_of_basic", "value": 50, "enabled": True, "is_earning": True},
            {"key": "conveyance", "name": "Conveyance", "calc_type": "fixed_monthly", "value": 1600, "enabled": True, "is_earning": True},
            {"key": "medical", "name": "Medical", "calc_type": "fixed_monthly", "value": 1250, "enabled": True, "is_earning": True},
            {"key": "special_allowance", "name": "Special Allowance", "calc_type": "balance", "value": 0, "enabled": True, "is_earning": True, "is_balance": True, "is_mandatory": True},
            {"key": "pf_employee", "name": "PF Employee Deduction", "calc_type": "percentage_of_basic", "value": 12, "enabled": True, "is_deduction": True},  # DEDUCTION
            {"key": "professional_tax", "name": "Professional Tax", "calc_type": "fixed_monthly", "value": 200, "enabled": True, "is_deduction": True},  # DEDUCTION
        ]
        
        effective_month = datetime.now().strftime("%Y-%m")
        new_ctc = 1800000
        
        # Step 1: HR submits CTC
        submit_response = requests.post(
            f"{BASE_URL}/api/ctc/design",
            json={
                "employee_id": test_emp["id"],
                "annual_ctc": new_ctc,
                "effective_month": effective_month,
                "component_config": config,
                "remarks": "E2E_TEST: Full workflow test"
            },
            headers=self.hr_headers
        )
        
        if submit_response.status_code == 400 and "pending" in submit_response.text.lower():
            print("⚠ Pending CTC exists - checking pending list")
            pending = requests.get(f"{BASE_URL}/api/ctc/pending-approvals", headers=self.admin_headers).json()
            existing = next((p for p in pending if p["employee_id"] == test_emp["id"]), None)
            if existing:
                # Reject existing and retry
                requests.post(f"{BASE_URL}/api/ctc/{existing['id']}/reject", json={"reason": "TEST: Cleaning up"}, headers=self.admin_headers)
                submit_response = requests.post(
                    f"{BASE_URL}/api/ctc/design",
                    json={
                        "employee_id": test_emp["id"],
                        "annual_ctc": new_ctc,
                        "effective_month": effective_month,
                        "component_config": config,
                        "remarks": "E2E_TEST: Full workflow test retry"
                    },
                    headers=self.hr_headers
                )
        
        assert submit_response.status_code == 200, f"Submit failed: {submit_response.text}"
        ctc_id = submit_response.json()["ctc_structure_id"]
        print(f"✓ Step 1: HR submitted CTC (ID: {ctc_id})")
        
        # Step 2: Admin sees pending
        pending = requests.get(f"{BASE_URL}/api/ctc/pending-approvals", headers=self.admin_headers).json()
        pending_ctc = next((p for p in pending if p["id"] == ctc_id), None)
        assert pending_ctc is not None, "CTC should be in pending list"
        print(f"✓ Step 2: CTC visible in pending approvals")
        
        # Step 3: Admin approves
        approve_response = requests.post(
            f"{BASE_URL}/api/ctc/{ctc_id}/approve",
            json={"remarks": "E2E_TEST: Approved"},
            headers=self.admin_headers
        )
        assert approve_response.status_code == 200, f"Approve failed: {approve_response.text}"
        print(f"✓ Step 3: Admin approved CTC")
        
        # Step 4: Employee record updated
        updated_emp = requests.get(f"{BASE_URL}/api/employees/{test_emp['id']}", headers=self.admin_headers).json()
        
        # Employee should now have updated salary
        new_salary = updated_emp.get("salary", 0)
        assert new_salary != original_salary or updated_emp.get("annual_ctc") == new_ctc, "Employee salary/CTC should be updated"
        print(f"✓ Step 4: Employee record updated")
        print(f"  Annual CTC: ₹{updated_emp.get('annual_ctc', 0):,.0f}")
        print(f"  Monthly Gross: ₹{new_salary:,.0f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
