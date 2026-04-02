"""
Test Suite for Payroll Engine Export Features and Exit Management
Tests:
1. Payroll Engine - Excel Download
2. Payroll Engine - Email for Approval
3. Exit Management - List all exits
4. Exit Settlement - List settlements
5. Exit Settlement - Initiate exit
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://role-security-2.preview.emergentagent.com')


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR Manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "hr123"
        })
        assert response.status_code == 200, f"HR login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]


class TestPayrollEngineExport(TestAuth):
    """Payroll Engine Export Features Tests"""
    
    def test_run_payroll_for_month(self, hr_token):
        """Run payroll to ensure data exists for export"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/run",
            headers=headers,
            json={"month": "2026-01"}
        )
        # Accept both 200 (success) and 400 (already exists)
        assert response.status_code in [200, 400], f"Run payroll failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert data.get("total_employees") > 0
            print(f"Payroll run for {data.get('total_employees')} employees")
    
    def test_export_excel_endpoint(self, hr_token):
        """Test Excel export endpoint returns valid xlsx file"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/export-excel?month=2026-01",
            headers=headers
        )
        assert response.status_code == 200, f"Excel export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "octet-stream" in content_type, f"Invalid content type: {content_type}"
        
        # Check file size (should be > 0)
        assert len(response.content) > 0, "Excel file is empty"
        print(f"Excel file size: {len(response.content)} bytes")
    
    def test_export_excel_no_data(self, hr_token):
        """Test Excel export returns 404 for month with no data"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/export-excel?month=2020-01",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404 for no data: {response.text}"
    
    def test_send_for_approval_endpoint(self, hr_token):
        """Test email approval endpoint"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/send-for-approval",
            headers=headers,
            json={
                "month": "2026-01",
                "recipient_email": "test@example.com",
                "cc_emails": [],
                "message": "Test approval request"
            }
        )
        # Accept 200 (success) or 500 (SMTP not configured in test env)
        assert response.status_code in [200, 500], f"Send for approval failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            print(f"Email sent to: {data.get('details', {}).get('recipient')}")
    
    def test_send_for_approval_no_data(self, hr_token):
        """Test email approval returns 404 for month with no data"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.post(
            f"{BASE_URL}/api/payroll/engine/send-for-approval",
            headers=headers,
            json={
                "month": "2020-01",
                "recipient_email": "test@example.com",
                "cc_emails": [],
                "message": "Test"
            }
        )
        assert response.status_code == 404, f"Expected 404 for no data: {response.text}"


class TestExitManagement(TestAuth):
    """Exit Management API Tests"""
    
    def test_get_all_exits(self, hr_token):
        """Test getting all exit requests"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/exit/all",
            headers=headers
        )
        assert response.status_code == 200, f"Get all exits failed: {response.text}"
        
        data = response.json()
        assert "requests" in data, "Response should have 'requests' key"
        print(f"Found {len(data['requests'])} exit requests")
    
    def test_get_exits_with_status_filter(self, hr_token):
        """Test getting exits with status filter"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/exit/all?status=pending",
            headers=headers
        )
        assert response.status_code == 200, f"Get exits with filter failed: {response.text}"
        
        data = response.json()
        assert "requests" in data


class TestExitSettlement(TestAuth):
    """Exit Settlement API Tests"""
    
    def test_list_settlements(self, hr_token):
        """Test listing exit settlements"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/exit-settlement/list",
            headers=headers
        )
        assert response.status_code == 200, f"List settlements failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} exit settlements")
        
        # Check settlement structure if any exist
        if len(data) > 0:
            settlement = data[0]
            assert "id" in settlement
            assert "employee_id" in settlement
            assert "status" in settlement
    
    def test_initiate_exit_validation(self, hr_token):
        """Test exit initiation validation - missing employee_id"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.post(
            f"{BASE_URL}/api/exit-settlement/initiate",
            headers=headers,
            json={
                "exit_type": "resignation",
                "last_working_date": "2026-04-30"
            }
        )
        assert response.status_code == 400, f"Expected 400 for missing employee_id: {response.text}"
    
    def test_get_settlement_details(self, hr_token):
        """Test getting settlement details"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # First get list to find an existing settlement
        list_response = requests.get(
            f"{BASE_URL}/api/exit-settlement/list",
            headers=headers
        )
        
        if list_response.status_code == 200:
            settlements = list_response.json()
            if len(settlements) > 0:
                exit_id = settlements[0]["id"]
                
                # Get details
                response = requests.get(
                    f"{BASE_URL}/api/exit-settlement/{exit_id}",
                    headers=headers
                )
                assert response.status_code == 200, f"Get settlement details failed: {response.text}"
                
                data = response.json()
                assert data.get("id") == exit_id
                print(f"Settlement details retrieved for: {data.get('employee_name')}")


class TestPayrollRegister(TestAuth):
    """Payroll Register API Tests"""
    
    def test_get_payroll_register(self, hr_token):
        """Test getting payroll register"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/register",
            headers=headers
        )
        assert response.status_code == 200, f"Get register failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} payroll registers")
    
    def test_get_payroll_register_details(self, hr_token):
        """Test getting detailed payroll register for a month"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(
            f"{BASE_URL}/api/payroll/engine/register/2026-01/details",
            headers=headers
        )
        # Accept 200 or 404 (if no data)
        assert response.status_code in [200, 404], f"Get register details failed: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "register" in data
            assert "calculations" in data
            print(f"Register has {len(data.get('calculations', []))} calculations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
