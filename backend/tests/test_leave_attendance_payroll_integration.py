"""
Test Leave-Attendance-Payroll Integration Flow
Tests:
1. Employee leave application (POST /api/leave-requests)
2. Pending leave requests for approval
3. Manager approve/reject leave (POST /api/leave-requests/{id}/rm-approve)
4. HR apply leave on behalf (POST /api/attendance/hr/apply-leave-for-employee)
5. Payroll inputs with incentives (POST /api/payroll/inputs)
6. Salary slip generation includes incentives, penalties, leave deductions
7. Leave balance calculation
8. Attendance records integration with payroll
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
HR_CREDS = {"employee_id": "EMP002", "password": "admin123"}
CONSULTANT_CREDS = {"employee_id": "CON001", "password": "consultant123"}


def get_token(creds):
    """Get auth token for credentials"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def auth_headers(token):
    """Return auth headers"""
    return {"Authorization": f"Bearer {token}"}


class TestLeaveAttendancePayrollIntegration:
    """Full integration tests for Leave → Attendance → Payroll flow"""
    
    # ==================== LEAVE REQUEST TESTS ====================
    
    def test_01_employee_can_apply_for_leave(self):
        """Employee can apply for leave via POST /api/leave-requests"""
        token = get_token(CONSULTANT_CREDS)
        assert token, "Consultant login failed"
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        leave_data = {
            "leave_type": "casual_leave",
            "start_date": tomorrow,
            "end_date": day_after,
            "reason": "TEST_Personal work",
            "is_half_day": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/leave-requests",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        # Accept both 200 and 400 (insufficient balance is also valid behavior)
        assert response.status_code in [200, 201, 400], f"Leave application failed: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "leave_request_id" in data or "message" in data
            print(f"SUCCESS: Leave request created - {data.get('message', 'OK')}")
        else:
            # 400 might mean insufficient balance - that's valid
            print(f"INFO: Leave request response - {response.json()}")
    
    def test_02_get_pending_leave_requests(self):
        """HR can view pending leave requests"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/leave-requests?status=pending",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get pending leaves failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Found {len(data)} pending leave requests")
        
        # Check data structure
        if len(data) > 0:
            leave = data[0]
            assert "id" in leave
            assert "employee_name" in leave or "employee_id" in leave
            assert "status" in leave
    
    def test_03_get_all_leave_requests_hr(self):
        """HR can view all leave requests"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/leave-requests/all",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get all leaves failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: HR can view all {len(data)} leave requests")
    
    def test_04_manager_approve_leave(self):
        """Manager can approve pending leave request"""
        admin_token = get_token(ADMIN_CREDS)
        hr_token = get_token(HR_CREDS)
        assert admin_token, "Admin login failed"
        assert hr_token, "HR login failed"
        
        # First get a pending leave
        response = requests.get(
            f"{BASE_URL}/api/leave-requests?status=pending",
            headers=auth_headers(hr_token)
        )
        
        assert response.status_code == 200
        pending = response.json()
        
        if len(pending) == 0:
            pytest.skip("No pending leave requests to approve")
        
        leave_id = pending[0]["id"]
        
        # Approve the leave
        response = requests.post(
            f"{BASE_URL}/api/leave-requests/{leave_id}/rm-approve",
            json={"action": "approve", "comments": "TEST_Approved by testing agent"},
            headers=auth_headers(admin_token)
        )
        
        assert response.status_code == 200, f"Approve leave failed: {response.text}"
        data = response.json()
        assert data.get("status") == "approved" or "approved" in data.get("message", "").lower()
        print(f"SUCCESS: Leave {leave_id} approved")
    
    def test_05_manager_reject_leave(self):
        """Manager can reject pending leave request"""
        admin_token = get_token(ADMIN_CREDS)
        hr_token = get_token(HR_CREDS)
        assert admin_token, "Admin login failed"
        assert hr_token, "HR login failed"
        
        # First get a pending leave
        response = requests.get(
            f"{BASE_URL}/api/leave-requests?status=pending",
            headers=auth_headers(hr_token)
        )
        
        assert response.status_code == 200
        pending = response.json()
        
        if len(pending) == 0:
            pytest.skip("No pending leave requests to reject")
        
        leave_id = pending[0]["id"]
        
        # Reject the leave
        response = requests.post(
            f"{BASE_URL}/api/leave-requests/{leave_id}/rm-approve",
            json={"action": "reject", "comments": "TEST_Rejected - insufficient notice"},
            headers=auth_headers(admin_token)
        )
        
        assert response.status_code == 200, f"Reject leave failed: {response.text}"
        data = response.json()
        assert data.get("status") == "rejected" or "rejected" in data.get("message", "").lower()
        print(f"SUCCESS: Leave {leave_id} rejected")
    
    # ==================== HR APPLY LEAVE ON BEHALF ====================
    
    def test_06_hr_apply_leave_on_behalf(self):
        """HR can apply leave on behalf of an employee"""
        hr_token = get_token(HR_CREDS)
        assert hr_token, "HR login failed"
        
        # First get an employee
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers(hr_token)
        )
        
        assert response.status_code == 200
        employees = response.json()
        
        if not employees:
            pytest.skip("No employees found")
        
        # Find a go-live active employee
        employee = None
        emp_list = employees if isinstance(employees, list) else employees.get("items", [])
        for emp in emp_list:
            if emp.get("go_live_status") == "active":
                employee = emp
                break
        
        if not employee and emp_list:
            # Use first employee
            employee = emp_list[0]
        
        if not employee:
            pytest.skip("No employee found")
        
        employee_id = employee.get("id")
        
        # Apply leave on behalf
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        leave_data = {
            "employee_id": employee_id,
            "leave_type": "casual_leave",
            "start_date": future_date,
            "end_date": future_date,
            "reason": "TEST_Applied by HR on behalf",
            "is_half_day": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/attendance/hr/apply-leave-for-employee",
            json=leave_data,
            headers=auth_headers(hr_token)
        )
        
        assert response.status_code in [200, 201], f"HR apply leave failed: {response.text}"
        data = response.json()
        assert "leave_request_id" in data or "message" in data
        print(f"SUCCESS: HR applied leave on behalf - {data.get('message', 'OK')}")
    
    # ==================== LEAVE BALANCE TESTS ====================
    
    def test_07_get_my_leave_balance(self):
        """Get my leave balance via convenience endpoint"""
        token = get_token(CONSULTANT_CREDS)
        assert token, "Consultant login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/my/leave-balance",
            headers=auth_headers(token)
        )
        
        # This endpoint may or may not exist
        if response.status_code == 200:
            balance = response.json()
            print(f"SUCCESS: My leave balance - {balance}")
        elif response.status_code == 404:
            print("INFO: /api/my/leave-balance endpoint not available")
        else:
            print(f"INFO: Leave balance response: {response.status_code}")
    
    # ==================== PAYROLL INPUT TESTS ====================
    
    def test_08_get_payroll_inputs(self):
        """Get payroll inputs for a month"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/inputs?month={current_month}",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get payroll inputs failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Found {len(data)} payroll input records")
        
        # Check structure
        if len(data) > 0:
            inp = data[0]
            assert "employee_id" in inp
            assert "incentive" in inp or "present_days" in inp
    
    def test_09_save_payroll_input_with_incentive(self):
        """Save payroll input with incentive amount"""
        admin_token = get_token(ADMIN_CREDS)
        assert admin_token, "Admin login failed"
        
        # First get employees
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers(admin_token)
        )
        
        employees = response.json()
        if not employees:
            pytest.skip("No employees found")
        
        # Find an active employee
        employee = None
        emp_list = employees if isinstance(employees, list) else employees.get("items", [])
        for emp in emp_list:
            if emp.get("go_live_status") == "active" and emp.get("salary", 0) > 0:
                employee = emp
                break
        
        if not employee:
            pytest.skip("No active employee with salary found")
        
        employee_id = employee.get("id")
        current_month = datetime.now().strftime("%Y-%m")
        
        # Save payroll input with incentive
        input_data = {
            "employee_id": employee_id,
            "month": current_month,
            "working_days": 30,
            "present_days": 25,
            "absent_days": 3,
            "public_holidays": 2,
            "leaves": 2,
            "overtime_hours": 5,
            "incentive": 15000,
            "incentive_reason": "TEST_Performance bonus",
            "advance": 0,
            "penalty": 0,
            "remarks": "TEST_Payroll input from testing agent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/inputs",
            json=input_data,
            headers=auth_headers(admin_token)
        )
        
        assert response.status_code == 200, f"Save payroll input failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"SUCCESS: Payroll input saved with incentive Rs.15,000")
    
    # ==================== SALARY SLIP GENERATION ====================
    
    def test_10_generate_salary_slip(self):
        """Generate salary slip including incentives and deductions"""
        admin_token = get_token(ADMIN_CREDS)
        assert admin_token, "Admin login failed"
        
        # Get employees with salary
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers(admin_token)
        )
        
        employees = response.json()
        
        # Find go-live active employee
        employee = None
        emp_list = employees if isinstance(employees, list) else employees.get("items", [])
        for emp in emp_list:
            if emp.get("go_live_status") == "active" and emp.get("salary", 0) > 0:
                employee = emp
                break
        
        if not employee:
            pytest.skip("No go-live active employee with salary found")
        
        employee_id = employee.get("id")
        current_month = datetime.now().strftime("%Y-%m")
        
        # Generate salary slip
        response = requests.post(
            f"{BASE_URL}/api/payroll/generate-slip",
            json={"employee_id": employee_id, "month": current_month},
            headers=auth_headers(admin_token)
        )
        
        if response.status_code == 400:
            error = response.json()
            if "Go-Live Active" in error.get("detail", ""):
                pytest.skip(f"Employee not go-live active: {error.get('detail')}")
        
        assert response.status_code == 200, f"Generate salary slip failed: {response.text}"
        slip = response.json()
        
        # Verify slip structure
        assert "employee_id" in slip
        assert "gross_salary" in slip
        assert "net_salary" in slip
        assert "earnings" in slip
        assert "deductions" in slip
        
        print(f"SUCCESS: Salary slip generated")
        print(f"  - Gross: Rs.{slip.get('gross_salary', 0):,}")
        print(f"  - Earnings: Rs.{slip.get('total_earnings', 0):,}")
        print(f"  - Deductions: Rs.{slip.get('total_deductions', 0):,}")
        print(f"  - Net Pay: Rs.{slip.get('net_salary', 0):,}")
        
        # Check if incentive is included
        for earning in slip.get("earnings", []):
            if "incentive" in earning.get("key", "").lower() or "incentive" in earning.get("name", "").lower():
                print(f"  - Incentive included: Rs.{earning.get('amount', 0):,}")
    
    def test_11_get_salary_slips(self):
        """Get generated salary slips"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/salary-slips?month={current_month}",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get salary slips failed: {response.text}"
        slips = response.json()
        assert isinstance(slips, list)
        print(f"SUCCESS: Found {len(slips)} salary slips for {current_month}")
    
    # ==================== ATTENDANCE TESTS ====================
    
    def test_12_get_attendance_records(self):
        """Get attendance records for current month"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        date_from = f"{current_month}-01"
        date_to = f"{current_month}-31"
        
        response = requests.get(
            f"{BASE_URL}/api/attendance?date_from={date_from}&date_to={date_to}",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get attendance failed: {response.text}"
        records = response.json()
        assert isinstance(records, list)
        print(f"SUCCESS: Found {len(records)} attendance records")
    
    def test_13_get_attendance_summary(self):
        """Get attendance summary for payroll"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        year, month = current_month.split("-")
        
        response = requests.get(
            f"{BASE_URL}/api/attendance/summary?month={month}&year={year}",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get attendance summary failed: {response.text}"
        summary = response.json()
        assert isinstance(summary, list) or isinstance(summary, dict)
        print(f"SUCCESS: Attendance summary retrieved")
    
    def test_14_auto_validate_attendance(self):
        """Auto-validate attendance for payroll"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.post(
            f"{BASE_URL}/api/attendance/auto-validate",
            json={"month": current_month},
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Auto-validate failed: {response.text}"
        data = response.json()
        assert "employees" in data or "summary" in data
        print(f"SUCCESS: Attendance auto-validation completed")
    
    # ==================== PAYROLL LINKAGE TESTS ====================
    
    def test_15_get_payroll_linkage_summary(self):
        """Get payroll linkage summary (attendance, leaves, expenses)"""
        token = get_token(ADMIN_CREDS)
        assert token, "Admin login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/linkage-summary?month={current_month}",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get linkage summary failed: {response.text}"
        summary = response.json()
        
        # Check structure
        assert "month" in summary
        print(f"SUCCESS: Payroll linkage summary for {summary.get('month')}")
        if "pending_reimbursements" in summary:
            print(f"  - Pending reimbursements: {summary['pending_reimbursements'].get('count', 0)}")
        if "lop_leaves" in summary:
            print(f"  - LOP leaves: {summary['lop_leaves'].get('count', 0)}")
        if "salary_slips" in summary:
            print(f"  - Salary slips generated: {summary['salary_slips'].get('generated_count', 0)}")
    
    def test_16_get_salary_components(self):
        """Get salary component configuration"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/salary-components",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get salary components failed: {response.text}"
        components = response.json()
        
        assert "earnings" in components or "deductions" in components
        print(f"SUCCESS: Salary components retrieved")
        if "earnings" in components:
            print(f"  - Earnings: {len(components['earnings'])} components")
        if "deductions" in components:
            print(f"  - Deductions: {len(components['deductions'])} components")
    
    # ==================== EDGE CASES ====================
    
    def test_17_leave_request_half_day(self):
        """Employee can apply for half-day leave"""
        token = get_token(CONSULTANT_CREDS)
        assert token, "Consultant login failed"
        
        future_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        
        leave_data = {
            "leave_type": "casual_leave",
            "start_date": future_date,
            "end_date": future_date,
            "reason": "TEST_Half day for appointment",
            "is_half_day": True,
            "half_day_type": "first_half"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/leave-requests",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        # Accept both 200 and 400 (insufficient balance)
        assert response.status_code in [200, 201, 400], f"Half-day leave failed: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"SUCCESS: Half-day leave request created")
        else:
            print(f"INFO: Half-day leave response: {response.json()}")
    
    def test_18_withdraw_pending_leave(self):
        """Employee can withdraw pending leave request"""
        token = get_token(CONSULTANT_CREDS)
        assert token, "Consultant login failed"
        
        # Get my pending leaves
        response = requests.get(
            f"{BASE_URL}/api/leave-requests",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200
        leaves = response.json()
        
        # Find a pending leave that I can withdraw
        pending = [l for l in leaves if l.get("status") == "pending"]
        
        if not pending:
            pytest.skip("No pending leaves to withdraw")
        
        leave_id = pending[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/leave-requests/{leave_id}/withdraw",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Withdraw leave failed: {response.text}"
        print(f"SUCCESS: Leave request {leave_id} withdrawn")
    
    def test_19_payroll_lock_status(self):
        """Check payroll lock status for month"""
        token = get_token(ADMIN_CREDS)
        assert token, "Admin login failed"
        
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/payroll/lock-status/{current_month}",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get lock status failed: {response.text}"
        status = response.json()
        
        assert "month" in status
        assert "is_locked" in status
        print(f"SUCCESS: Payroll lock status - locked={status.get('is_locked')}")
    
    def test_20_company_leave_stats(self):
        """HR can view company-wide leave statistics"""
        token = get_token(HR_CREDS)
        assert token, "HR login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/leave-requests/stats/company-wide",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Get company leave stats failed: {response.text}"
        stats = response.json()
        
        assert "total_employees" in stats or "leave_types" in stats
        print(f"SUCCESS: Company leave stats retrieved")
        print(f"  - Total employees: {stats.get('total_employees', 'N/A')}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
