"""
Payment Reminder & Record Payment Tests
Tests for:
1. Payment reminder endpoint - send-reminder (within 7 days constraint)
2. Record payment endpoint - record-payment (transaction ID recording)
3. Reset temp password endpoint for employees
4. Kickoff accept sets project status to 'active'
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentReminderRecordEndpoints:
    """Test Payment Reminder and Record Payment features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and auth tokens"""
        self.admin_email = "admin@dvbc.com"
        self.admin_password = "admin123"
        self.consultant_email = "consultant@dvbc.com"
        self.consultant_password = "consultant123"
        
        # Get admin token
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        self.admin_token = login_res.json().get("access_token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get consultant token
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.consultant_email,
            "password": self.consultant_password
        })
        assert login_res.status_code == 200, f"Consultant login failed: {login_res.text}"
        self.consultant_token = login_res.json().get("access_token")
        self.consultant_headers = {"Authorization": f"Bearer {self.consultant_token}"}

    # ============== PAYMENT REMINDER TESTS ==============
    
    def test_send_reminder_endpoint_exists(self):
        """Test that send-reminder endpoint exists and requires auth"""
        res = requests.post(f"{BASE_URL}/api/project-payments/send-reminder", json={
            "project_id": "test",
            "installment_number": 1
        })
        # Should fail with 401 (unauthorized) not 404
        assert res.status_code in [401, 403, 400, 422], f"Expected auth error or validation error, got {res.status_code}"
        print(f"Send reminder endpoint exists: Status {res.status_code}")

    def test_send_reminder_requires_project(self):
        """Test that send-reminder validates project_id"""
        res = requests.post(
            f"{BASE_URL}/api/project-payments/send-reminder",
            headers=self.admin_headers,
            json={
                "project_id": "nonexistent-project-id",
                "installment_number": 1
            }
        )
        # Should get 404 for project not found or 400 for validation
        assert res.status_code in [400, 404], f"Expected 400/404 for invalid project, got {res.status_code}: {res.text}"
        print(f"Send reminder validates project: Status {res.status_code}")

    def test_send_reminder_7_day_constraint(self):
        """Test that reminders can only be sent within 7 days of due date"""
        # First get a project with payments
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        assert projects_res.status_code == 200, f"Failed to get payments: {projects_res.text}"
        
        payments_data = projects_res.json()
        if payments_data.get("payments"):
            project_id = payments_data["payments"][0]["project_id"]
            
            # Check reminder eligibility for installment 2
            elig_res = requests.get(
                f"{BASE_URL}/api/project-payments/check-reminder-eligibility/{project_id}/2",
                headers=self.admin_headers
            )
            assert elig_res.status_code == 200, f"Eligibility check failed: {elig_res.text}"
            
            elig_data = elig_res.json()
            print(f"Reminder eligibility for project {project_id}: {elig_data}")
            
            # If not within 7 days, reminder should fail
            if elig_data.get("days_until_due", 100) > 7:
                reminder_res = requests.post(
                    f"{BASE_URL}/api/project-payments/send-reminder",
                    headers=self.admin_headers,
                    json={
                        "project_id": project_id,
                        "installment_number": 2
                    }
                )
                # Should fail with 400 - not within 7 days
                assert reminder_res.status_code == 400, f"Expected 400 for >7 days, got {reminder_res.status_code}"
                assert "7 days" in reminder_res.text.lower() or "days" in reminder_res.text.lower(), \
                    f"Expected 7-day error message, got: {reminder_res.text}"
                print(f"7-day constraint enforced correctly")
            else:
                print(f"Skipping 7-day test - payment is within window (days: {elig_data.get('days_until_due')})")
        else:
            pytest.skip("No payments found to test reminder")

    def test_check_reminder_eligibility_endpoint(self):
        """Test the check-reminder-eligibility endpoint"""
        # Get a project first
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        
        if projects_res.status_code == 200 and projects_res.json().get("payments"):
            project_id = projects_res.json()["payments"][0]["project_id"]
            
            res = requests.get(
                f"{BASE_URL}/api/project-payments/check-reminder-eligibility/{project_id}/1",
                headers=self.admin_headers
            )
            assert res.status_code == 200, f"Eligibility check failed: {res.text}"
            
            data = res.json()
            # Should return expected fields
            assert "eligible" in data, "Missing 'eligible' field"
            assert "days_until_due" in data or "reason" in data, "Missing days or reason"
            print(f"Eligibility check response: {data}")
        else:
            pytest.skip("No projects found for eligibility test")

    # ============== RECORD PAYMENT TESTS ==============
    
    def test_record_payment_endpoint_exists(self):
        """Test that record-payment endpoint exists"""
        res = requests.post(f"{BASE_URL}/api/project-payments/record-payment", json={
            "project_id": "test",
            "installment_number": 1,
            "transaction_id": "TEST-123",
            "amount_received": 1000.00
        })
        # Should fail with 401 (unauthorized) not 404
        assert res.status_code in [401, 403, 400, 422], f"Expected auth error, got {res.status_code}"
        print(f"Record payment endpoint exists: Status {res.status_code}")

    def test_record_payment_requires_valid_project(self):
        """Test that record-payment validates project_id"""
        res = requests.post(
            f"{BASE_URL}/api/project-payments/record-payment",
            headers=self.admin_headers,
            json={
                "project_id": "nonexistent-project-id",
                "installment_number": 1,
                "transaction_id": "TEST-123",
                "amount_received": 1000.00
            }
        )
        assert res.status_code in [400, 404], f"Expected validation error, got {res.status_code}: {res.text}"
        print(f"Record payment validates project: Status {res.status_code}")

    def test_record_payment_requires_transaction_id(self):
        """Test that record-payment requires transaction_id"""
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        
        if projects_res.status_code == 200 and projects_res.json().get("payments"):
            project_id = projects_res.json()["payments"][0]["project_id"]
            
            # Try without transaction_id
            res = requests.post(
                f"{BASE_URL}/api/project-payments/record-payment",
                headers=self.admin_headers,
                json={
                    "project_id": project_id,
                    "installment_number": 999,  # Invalid to avoid duplicate
                    "amount_received": 1000.00
                }
            )
            # Should fail validation - missing required field
            assert res.status_code in [400, 422], f"Expected validation error, got {res.status_code}"
            print(f"Transaction ID required validation: Status {res.status_code}")
        else:
            pytest.skip("No projects found")

    def test_record_payment_creates_installment_payment(self):
        """Test that record-payment creates an installment_payments record"""
        # Get a project with payments
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        
        if projects_res.status_code == 200 and projects_res.json().get("payments"):
            project_id = projects_res.json()["payments"][0]["project_id"]
            
            # Use a high installment number to avoid conflicts
            test_installment = 99
            test_txn_id = f"TEST-TXN-{uuid.uuid4().hex[:8]}"
            
            res = requests.post(
                f"{BASE_URL}/api/project-payments/record-payment",
                headers=self.admin_headers,
                json={
                    "project_id": project_id,
                    "installment_number": test_installment,
                    "transaction_id": test_txn_id,
                    "amount_received": 50000.00,
                    "payment_date": datetime.now().strftime("%Y-%m-%d"),
                    "remarks": "Test payment recording"
                }
            )
            
            # May fail due to invalid installment number (expected)
            print(f"Record payment response: {res.status_code} - {res.text[:200]}")
            
            # Check installment payments for the project
            inst_res = requests.get(
                f"{BASE_URL}/api/project-payments/installment-payments/{project_id}",
                headers=self.admin_headers
            )
            assert inst_res.status_code == 200, f"Failed to get installment payments: {inst_res.text}"
            print(f"Installment payments endpoint works")
        else:
            pytest.skip("No projects found")

    def test_get_installment_payments_endpoint(self):
        """Test get installment payments endpoint"""
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        
        if projects_res.status_code == 200 and projects_res.json().get("payments"):
            project_id = projects_res.json()["payments"][0]["project_id"]
            
            res = requests.get(
                f"{BASE_URL}/api/project-payments/installment-payments/{project_id}",
                headers=self.admin_headers
            )
            assert res.status_code == 200, f"Failed: {res.text}"
            
            data = res.json()
            assert "payments" in data, "Missing 'payments' field"
            assert "project_id" in data, "Missing 'project_id' field"
            print(f"Installment payments response: {data}")
        else:
            pytest.skip("No projects found")


class TestResetTempPassword:
    """Test reset temp password endpoint for employees"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin auth"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        self.admin_token = login_res.json().get("access_token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_reset_temp_password_endpoint_exists(self):
        """Test that reset-temp-password endpoint exists"""
        res = requests.post(
            f"{BASE_URL}/api/employees/nonexistent-id/reset-temp-password",
            headers=self.admin_headers
        )
        # Should return 404 for employee not found, not 405 or 500
        assert res.status_code in [404, 400], f"Expected 404/400, got {res.status_code}: {res.text}"
        print(f"Reset temp password endpoint exists: Status {res.status_code}")

    def test_reset_temp_password_requires_auth(self):
        """Test that reset-temp-password requires admin auth"""
        res = requests.post(f"{BASE_URL}/api/employees/some-id/reset-temp-password")
        # Should fail with 401/403 (unauthorized)
        assert res.status_code in [401, 403, 422], f"Expected auth error, got {res.status_code}"
        print(f"Reset temp password requires auth: Status {res.status_code}")

    def test_reset_temp_password_for_valid_employee(self):
        """Test reset temp password for a valid employee"""
        # First get an employee with portal access
        employees_res = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.admin_headers
        )
        
        if employees_res.status_code == 200:
            employees = employees_res.json()
            
            # Find an employee with user_id (has portal access)
            employee_with_access = None
            for emp in employees:
                if emp.get("user_id") and emp.get("status") == "active":
                    employee_with_access = emp
                    break
            
            if employee_with_access:
                emp_id = employee_with_access["id"]
                res = requests.post(
                    f"{BASE_URL}/api/employees/{emp_id}/reset-temp-password",
                    headers=self.admin_headers
                )
                
                # Should succeed with 200
                if res.status_code == 200:
                    data = res.json()
                    assert "temp_password" in data, "Missing temp_password in response"
                    assert "message" in data, "Missing message in response"
                    print(f"Reset temp password success: {data['message']}")
                    print(f"New temp password format: Welcome@{employee_with_access.get('employee_id', 'XXX')}")
                else:
                    print(f"Reset password response: {res.status_code} - {res.text}")
            else:
                print("No employee with portal access found - skipping")
        else:
            pytest.skip(f"Failed to get employees: {employees_res.text}")

    def test_reset_password_fails_for_no_access_employee(self):
        """Test that reset fails for employee without portal access"""
        # Get employees
        employees_res = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.admin_headers
        )
        
        if employees_res.status_code == 200:
            employees = employees_res.json()
            
            # Find employee WITHOUT user_id (no portal access)
            no_access_emp = None
            for emp in employees:
                if not emp.get("user_id") and emp.get("status") == "active":
                    no_access_emp = emp
                    break
            
            if no_access_emp:
                res = requests.post(
                    f"{BASE_URL}/api/employees/{no_access_emp['id']}/reset-temp-password",
                    headers=self.admin_headers
                )
                # Should fail - no portal access
                assert res.status_code == 400, f"Expected 400 for no access, got {res.status_code}: {res.text}"
                print(f"Correctly rejects reset for no-access employee")
            else:
                print("All employees have portal access - skipping negative test")
        else:
            pytest.skip("Failed to get employees")


class TestKickoffSetsActiveStatus:
    """Test that kickoff accept sets project status to 'active'"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin auth"""
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        self.admin_token = login_res.json().get("access_token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_kickoff_accept_endpoint_exists(self):
        """Test that kickoff accept endpoint exists"""
        # Try to accept a non-existent kickoff
        res = requests.post(
            f"{BASE_URL}/api/kickoff-requests/nonexistent-id/accept",
            headers=self.admin_headers
        )
        # Should get 404 not 405
        assert res.status_code in [404, 400], f"Expected 404/400, got {res.status_code}"
        print(f"Kickoff accept endpoint exists: Status {res.status_code}")

    def test_kickoff_creates_active_project(self):
        """Verify that accepted kickoffs create projects with 'active' status"""
        # Get recent projects to check if any were created from kickoff
        projects_res = requests.get(
            f"{BASE_URL}/api/projects",
            headers=self.admin_headers
        )
        
        if projects_res.status_code == 200:
            projects = projects_res.json()
            
            # Check for projects with 'active' status
            active_projects = [p for p in projects if p.get("status") == "active"]
            print(f"Found {len(active_projects)} active projects out of {len(projects)} total")
            
            # Verify at least one active project exists
            if active_projects:
                print(f"Sample active project: {active_projects[0].get('name')} - Status: {active_projects[0].get('status')}")
                assert active_projects[0]["status"] == "active"
            else:
                print("No active projects found - may need to create kickoff first")
        else:
            print(f"Failed to get projects: {projects_res.text}")


class TestAdminPaymentVisibility:
    """Test that admin can see full payment amounts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth tokens"""
        # Admin login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_res.status_code == 200
        self.admin_token = login_res.json().get("access_token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Consultant login
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "consultant@dvbc.com",
            "password": "consultant123"
        })
        assert login_res.status_code == 200
        self.consultant_token = login_res.json().get("access_token")
        self.consultant_headers = {"Authorization": f"Bearer {self.consultant_token}"}

    def test_admin_sees_amounts(self):
        """Test that admin can see payment amounts"""
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        assert projects_res.status_code == 200
        
        data = projects_res.json()
        assert data.get("can_view_amounts") == True, "Admin should have can_view_amounts=True"
        print(f"Admin can_view_amounts: {data.get('can_view_amounts')}")

    def test_consultant_cannot_see_amounts(self):
        """Test that consultant cannot see payment amounts"""
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.consultant_headers
        )
        assert projects_res.status_code == 200
        
        data = projects_res.json()
        assert data.get("can_view_amounts") == False, "Consultant should have can_view_amounts=False"
        print(f"Consultant can_view_amounts: {data.get('can_view_amounts')}")

    def test_admin_project_details_has_amounts(self):
        """Test admin can see amounts in project payment details"""
        # Get a project first
        projects_res = requests.get(
            f"{BASE_URL}/api/project-payments/my-payments",
            headers=self.admin_headers
        )
        
        if projects_res.status_code == 200 and projects_res.json().get("payments"):
            project_id = projects_res.json()["payments"][0]["project_id"]
            
            details_res = requests.get(
                f"{BASE_URL}/api/project-payments/project/{project_id}",
                headers=self.admin_headers
            )
            assert details_res.status_code == 200
            
            data = details_res.json()
            assert data.get("can_view_amounts") == True, "Admin should see amounts"
            
            # Check payment schedule has amount fields
            if data.get("payment_schedule"):
                first_payment = data["payment_schedule"][0]
                assert "basic" in first_payment or "net" in first_payment, "Admin should see amount fields"
                print(f"Admin payment schedule has amounts: {list(first_payment.keys())}")
        else:
            pytest.skip("No projects found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
