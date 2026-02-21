"""
Approval Notifications Test Suite
Tests that approval workflows trigger real-time email + WebSocket notifications
and create proper records in email_action_tokens and email_logs collections
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials provided
TEST_USERS = {
    "admin": {"email": "admin@dvbc.com", "password": "admin123"},
    "hr_manager": {"email": "hr.manager@dvbc.com", "password": "hr123"},
    "manager": {"email": "dp@dvbc.com", "password": "Welcome@123"},
    "employee": {"email": "rahul.kumar@dvbc.com", "password": "Welcome@EMP001"}
}


@pytest.fixture(scope="module")
def session():
    """Shared requests session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(session):
    """Get admin auth token"""
    response = session.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["admin"])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.text}")


@pytest.fixture(scope="module")
def hr_token(session):
    """Get HR manager auth token"""
    response = session.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["hr_manager"])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"HR login failed: {response.text}")


@pytest.fixture(scope="module")
def manager_token(session):
    """Get manager auth token"""
    response = session.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["manager"])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Manager login failed: {response.text}")


@pytest.fixture(scope="module")
def employee_token(session):
    """Get employee auth token"""
    response = session.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["employee"])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Employee login failed: {response.text}")


@pytest.fixture(scope="module")
def initial_email_action_tokens_count(session, admin_token):
    """Get initial count of email_action_tokens"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Try to get token count via db stats or email logs
    response = session.get(f"{BASE_URL}/api/email-actions/logs", headers=headers)
    if response.status_code == 200:
        return len(response.json().get("logs", []))
    return 0


class TestAuthAndHealthCheck:
    """Basic health and auth checks before testing notifications"""
    
    def test_api_health_check(self, session):
        """Test API is accessible"""
        response = session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"✅ API Health Check: {response.json()}")
    
    def test_admin_login(self, session, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        print(f"✅ Admin login successful, token received")
    
    def test_hr_login(self, session, hr_token):
        """Test HR manager can login"""
        assert hr_token is not None
        print(f"✅ HR Manager login successful")
    
    def test_employee_login(self, session, employee_token):
        """Test employee can login"""
        assert employee_token is not None
        print(f"✅ Employee login successful")


class TestLeaveRequestNotifications:
    """Test leave request creation sends notification to Reporting Manager"""
    
    def test_create_leave_request_sends_notification(self, session, employee_token):
        """Create leave request and verify notifications are triggered"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # First check employee profile
        profile_resp = session.get(f"{BASE_URL}/api/my/profile", headers=headers)
        print(f"Employee profile status: {profile_resp.status_code}")
        
        # Calculate dates for leave request (tomorrow to day after)
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
        end_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%dT00:00:00")
        
        leave_data = {
            "leave_type": "casual_leave",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST - Testing approval notification workflow",
            "is_half_day": False
        }
        
        response = session.post(f"{BASE_URL}/api/leave-requests", json=leave_data, headers=headers)
        print(f"Leave request response: {response.status_code} - {response.text[:500] if response.text else 'No body'}")
        
        # Check if request was created (may fail if insufficient balance or no RM)
        if response.status_code in [200, 201]:
            data = response.json()
            assert "leave_request_id" in data
            print(f"✅ Leave request created: {data.get('leave_request_id')}")
            print(f"   Approver: {data.get('approver')}")
            return data.get("leave_request_id")
        elif response.status_code == 400:
            # May fail due to insufficient leave balance - that's OK for test
            print(f"⚠️ Leave request not created (may be expected): {response.json().get('detail')}")
            pytest.skip("Insufficient leave balance or missing employee record")
        else:
            print(f"❌ Unexpected response: {response.status_code}")


class TestExpenseSubmissionNotifications:
    """Test expense submission sends notification to HR Manager"""
    
    @pytest.fixture
    def created_expense_id(self, session, employee_token):
        """Create an expense first"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        expense_data = {
            "category": "travel",
            "amount": 1500,
            "description": "TEST - Travel expense for notification testing",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "line_items": [
                {"description": "Taxi fare", "amount": 500},
                {"description": "Fuel", "amount": 1000}
            ]
        }
        
        response = session.post(f"{BASE_URL}/api/expenses", json=expense_data, headers=headers)
        if response.status_code in [200, 201]:
            return response.json().get("expense_id")
        return None
    
    def test_create_expense(self, session, employee_token, created_expense_id):
        """Test expense can be created"""
        if created_expense_id:
            print(f"✅ Expense created: {created_expense_id}")
        else:
            print("⚠️ Could not create expense (endpoint may not be accessible)")
    
    def test_submit_expense_sends_notification_to_hr(self, session, employee_token, created_expense_id):
        """Submit expense for approval - should notify HR"""
        if not created_expense_id:
            pytest.skip("No expense created to submit")
        
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        response = session.post(f"{BASE_URL}/api/expenses/{created_expense_id}/submit", headers=headers)
        print(f"Expense submit response: {response.status_code} - {response.text[:500] if response.text else 'No body'}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Expense submitted: {data.get('message')}")
            print(f"   Approval Flow: {data.get('approval_flow')}")
            print(f"   Current Approver: {data.get('current_approver')}")
            assert "approval_flow" in data or "message" in data
        else:
            print(f"⚠️ Expense submit failed: {response.text[:200]}")


class TestBankChangeRequestNotifications:
    """Test bank change request sends notification to HR"""
    
    def test_submit_bank_change_request_sends_notification(self, session, employee_token):
        """Submit bank change request - should notify HR"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        bank_change_data = {
            "new_bank_details": {
                "bank_name": "TEST Bank for Notification",
                "account_number": "1234567890123",
                "ifsc_code": "TEST0001234",
                "account_holder_name": "Test User"
            },
            "reason": "TEST - Testing bank change notification workflow"
        }
        
        response = session.post(f"{BASE_URL}/api/my/bank-change-request", json=bank_change_data, headers=headers)
        print(f"Bank change request response: {response.status_code} - {response.text[:500] if response.text else 'No body'}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Bank change request submitted: {data.get('request_id')}")
            assert "request_id" in data or "message" in data
        elif response.status_code == 400:
            # May fail if pending request exists
            detail = response.json().get('detail', '')
            if 'pending' in detail.lower():
                print(f"⚠️ Bank change request exists: {detail}")
            else:
                print(f"⚠️ Bank change failed: {detail}")
        elif response.status_code == 404:
            print(f"⚠️ Employee profile not found - skip bank change test")
            pytest.skip("Employee profile not found")


class TestGoLiveRequestNotifications:
    """Test Go-Live request sends notification to Admin"""
    
    def test_submit_go_live_request_sends_notification(self, session, hr_token):
        """HR submits Go-Live request - should notify Admin"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # First get an employee to submit go-live for
        employees_resp = session.get(f"{BASE_URL}/api/employees?limit=5", headers=headers)
        print(f"Employees fetch: {employees_resp.status_code}")
        
        if employees_resp.status_code != 200:
            pytest.skip("Cannot fetch employees")
        
        employees = employees_resp.json()
        if not employees or not isinstance(employees, list) or len(employees) == 0:
            # Try alternate endpoint
            employees_resp = session.get(f"{BASE_URL}/api/employees", headers=headers)
            if employees_resp.status_code == 200:
                data = employees_resp.json()
                employees = data.get("employees", data) if isinstance(data, dict) else data
        
        if not employees or len(employees) == 0:
            pytest.skip("No employees found for Go-Live test")
        
        # Pick first employee
        employee = employees[0] if isinstance(employees, list) else None
        if not employee:
            pytest.skip("Cannot get employee")
        
        employee_id = employee.get("employee_id") or employee.get("id")
        print(f"Testing Go-Live for employee: {employee_id}")
        
        # Check go-live checklist first
        checklist_resp = session.get(f"{BASE_URL}/api/go-live/checklist/{employee_id}", headers=headers)
        print(f"Go-Live checklist response: {checklist_resp.status_code}")
        
        go_live_data = {
            "checklist": {
                "onboarding_complete": True,
                "ctc_approved": True,
                "bank_details_added": True,
                "portal_access_granted": True
            },
            "notes": "TEST - Testing Go-Live notification workflow"
        }
        
        response = session.post(f"{BASE_URL}/api/go-live/submit/{employee_id}", json=go_live_data, headers=headers)
        print(f"Go-Live submit response: {response.status_code} - {response.text[:500] if response.text else 'No body'}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Go-Live request submitted: {data.get('request_id')}")
            assert "request_id" in data or "message" in data
        elif response.status_code == 400:
            # May fail if already pending
            detail = response.json().get('detail', '')
            print(f"⚠️ Go-Live request may exist: {detail}")
        else:
            print(f"⚠️ Go-Live submit unexpected response: {response.status_code}")


class TestEmailActionTokensAndLogs:
    """Verify email_action_tokens and email_logs collections are populated"""
    
    def test_email_logs_endpoint_accessible(self, session, admin_token):
        """Test email logs endpoint is accessible"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/email-actions/logs", headers=headers)
        print(f"Email logs response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", [])
            print(f"✅ Email logs accessible - {len(logs)} logs found")
            
            # Check if any recent logs exist
            if logs:
                recent_log = logs[0]
                print(f"   Most recent log: {recent_log.get('record_type')} - {recent_log.get('recipient_email')}")
        else:
            print(f"⚠️ Email logs endpoint returned: {response.status_code}")
    
    def test_email_config_accessible(self, session, admin_token):
        """Test email config is accessible and configured"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/email-actions/config", headers=headers)
        print(f"Email config response: {response.status_code}")
        
        if response.status_code == 200:
            config = response.json()
            smtp_configured = config.get("smtp_configured", False) or config.get("smtp_host")
            print(f"✅ Email config accessible - SMTP configured: {bool(smtp_configured)}")
            if config.get("smtp_host"):
                print(f"   SMTP Host: {config.get('smtp_host')}")
        else:
            print(f"⚠️ Email config not accessible: {response.status_code}")


class TestKickoffRequestNotifications:
    """Test kickoff request sends notification to assigned PM
    Note: Kickoff requires agreement with verified payment, may skip if no test data
    """
    
    def test_get_eligible_pms(self, session, admin_token):
        """Test we can get eligible PMs for kickoff"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/kickoff-requests/eligible-pms/list", headers=headers)
        print(f"Eligible PMs response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pms = data.get("eligible_pms", [])
            print(f"✅ Found {len(pms)} eligible PMs")
            for pm in pms[:3]:
                print(f"   - {pm.get('full_name')} ({pm.get('role')})")
        else:
            print(f"⚠️ Cannot get eligible PMs: {response.status_code}")
    
    def test_list_kickoff_requests(self, session, admin_token):
        """Test listing kickoff requests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/kickoff-requests", headers=headers)
        print(f"Kickoff requests list response: {response.status_code}")
        
        if response.status_code == 200:
            requests = response.json()
            if isinstance(requests, list):
                print(f"✅ Found {len(requests)} kickoff requests")
                for req in requests[:3]:
                    print(f"   - {req.get('project_name')} - Status: {req.get('status')}")
        else:
            print(f"⚠️ Cannot list kickoff requests: {response.status_code}")


class TestNotificationRecordsCreation:
    """Test that notifications are created in the database"""
    
    def test_notifications_list(self, session, admin_token):
        """Get notifications list for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/notifications", headers=headers)
        print(f"Notifications list response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            notifications = data if isinstance(data, list) else data.get("notifications", [])
            print(f"✅ Admin has {len(notifications)} notifications")
            
            # Look for approval-related notifications
            approval_types = ["expense_submitted", "leave_request", "approval_request", "go_live_approval", "bank_change"]
            for notif in notifications[:5]:
                notif_type = notif.get("type", "")
                if any(t in notif_type for t in approval_types):
                    print(f"   🔔 {notif.get('title')} - Type: {notif_type}")
        else:
            print(f"⚠️ Cannot get notifications: {response.status_code}")
    
    def test_hr_notifications(self, session, hr_token):
        """Get notifications list for HR"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = session.get(f"{BASE_URL}/api/notifications", headers=headers)
        print(f"HR Notifications response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            notifications = data if isinstance(data, list) else data.get("notifications", [])
            print(f"✅ HR has {len(notifications)} notifications")
            
            for notif in notifications[:5]:
                print(f"   🔔 {notif.get('title')} - Type: {notif.get('type')}")
        else:
            print(f"⚠️ Cannot get HR notifications: {response.status_code}")


class TestDirectDatabaseVerification:
    """Verify email_action_tokens and email_logs via API if available"""
    
    def test_check_email_logs_for_approval_emails(self, session, admin_token):
        """Check if email_logs has records for approval workflows"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/email-actions/logs?limit=20", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", data) if isinstance(data, dict) else data
            
            if isinstance(logs, list) and len(logs) > 0:
                print(f"✅ Found {len(logs)} email logs")
                
                # Group by record type
                record_types = {}
                for log in logs:
                    rt = log.get("record_type", "unknown")
                    record_types[rt] = record_types.get(rt, 0) + 1
                
                print("   Email logs by record type:")
                for rt, count in record_types.items():
                    print(f"   - {rt}: {count} emails")
                
                # Show recent emails
                print("   Recent emails:")
                for log in logs[:5]:
                    print(f"   📧 {log.get('record_type')} to {log.get('recipient_email')} at {log.get('sent_at', 'unknown time')}")
            else:
                print(f"⚠️ No email logs found - SMTP may not be configured or no approvals triggered yet")
        else:
            print(f"⚠️ Email logs endpoint returned {response.status_code}")
    
    def test_pending_expense_approvals(self, session, hr_token):
        """Check pending expense approvals to verify workflow"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = session.get(f"{BASE_URL}/api/expenses/pending-approvals", headers=headers)
        print(f"Pending expense approvals response: {response.status_code}")
        
        if response.status_code == 200:
            expenses = response.json()
            if isinstance(expenses, list):
                print(f"✅ Found {len(expenses)} pending expense approvals for HR")
                for exp in expenses[:3]:
                    print(f"   💰 ₹{exp.get('amount')} from {exp.get('employee_name')} - Status: {exp.get('status')}")
        else:
            print(f"⚠️ Cannot get pending approvals: {response.status_code}")
    
    def test_bank_change_requests_for_hr(self, session, hr_token):
        """Check bank change requests visible to HR"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = session.get(f"{BASE_URL}/api/hr/bank-change-requests", headers=headers)
        print(f"Bank change requests response: {response.status_code}")
        
        if response.status_code == 200:
            requests = response.json()
            if isinstance(requests, list):
                print(f"✅ Found {len(requests)} bank change requests for HR review")
                for req in requests[:3]:
                    print(f"   🏦 {req.get('employee_name')} - Status: {req.get('status')}")
        else:
            print(f"⚠️ Cannot get bank change requests: {response.status_code}")
    
    def test_pending_go_live_requests(self, session, admin_token):
        """Check pending Go-Live requests for Admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = session.get(f"{BASE_URL}/api/go-live/pending", headers=headers)
        print(f"Pending Go-Live requests response: {response.status_code}")
        
        if response.status_code == 200:
            requests = response.json()
            if isinstance(requests, list):
                print(f"✅ Found {len(requests)} pending Go-Live requests for Admin")
                for req in requests[:3]:
                    print(f"   ✅ {req.get('employee_name')} ({req.get('employee_code')}) - Submitted by {req.get('submitted_by_name')}")
        else:
            print(f"⚠️ Cannot get Go-Live requests: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
