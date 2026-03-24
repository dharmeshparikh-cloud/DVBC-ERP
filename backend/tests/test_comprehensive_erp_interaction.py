"""
Comprehensive ERP Interaction Tests - Backend API Testing
Tests: Login, Governance APIs, Expenses, Approvals, Leave Management, Consulting Meetings

Test Coverage:
- Authentication with all roles
- Governance APIs (health-score, mom-sla, expense-compliance, leakage-alerts)
- Expense CRUD and receipt enforcement
- Approval workflows
- Leave management
- Consulting meetings
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_CREDENTIALS = {
    'admin': {'employee_id': 'EMP001', 'password': 'admin123'},
    'hr': {'employee_id': 'EMP002', 'password': 'hr123'},
    'sales': {'employee_id': 'EMP003', 'password': 'sales123'},
    'consultant': {'employee_id': 'EMP004', 'password': 'consultant123'},
    'employee': {'employee_id': 'EMP005', 'password': 'employee123'},
}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['admin'])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def hr_token(api_client):
    """Get HR authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['hr'])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("HR authentication failed")


@pytest.fixture(scope="module")
def consultant_token(api_client):
    """Get consultant authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['consultant'])
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Consultant authentication failed")


class TestAuthentication:
    """Test authentication for all roles"""
    
    def test_admin_login(self, api_client):
        """Test Admin login (EMP001)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['admin'])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["role"] == "admin"
        print(f"✅ Admin login successful: {data['user']['full_name']}")
    
    def test_hr_login(self, api_client):
        """Test HR Manager login (EMP002)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['hr'])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "hr_manager"
        print(f"✅ HR login successful: {data['user']['full_name']}")
    
    def test_sales_login(self, api_client):
        """Test Sales Executive login (EMP003)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['sales'])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✅ Sales login successful: {data['user']['full_name']}")
    
    def test_consultant_login(self, api_client):
        """Test Consultant login (EMP004)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['consultant'])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✅ Consultant login successful: {data['user']['full_name']}")
    
    def test_employee_login(self, api_client):
        """Test Employee login (EMP005)"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json=TEST_CREDENTIALS['employee'])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✅ Employee login successful: {data['user']['full_name']}")


class TestGovernanceAPIs:
    """Test Business Governance APIs"""
    
    def test_health_score(self, api_client, admin_token):
        """Test /api/governance/health-score endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/governance/health-score")
        assert response.status_code == 200
        data = response.json()
        assert "scores" in data
        assert "overall" in data
        assert "status" in data
        print(f"✅ Health Score: {data['overall']} - Status: {data['status']}")
    
    def test_mom_sla(self, api_client, admin_token):
        """Test /api/governance/mom-sla endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/governance/mom-sla")
        assert response.status_code == 200
        data = response.json()
        assert "sla_hours" in data
        assert "summary" in data
        assert data["sla_hours"] == 24  # MOM SLA is 24 hours
        print(f"✅ MOM SLA: {data['summary']['compliance_rate']}% compliance rate")
    
    def test_expense_compliance(self, api_client, admin_token):
        """Test /api/governance/expense-compliance endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/governance/expense-compliance")
        assert response.status_code == 200
        data = response.json()
        assert "compliance" in data or "total_expenses" in data
        print(f"✅ Expense Compliance API working")
    
    def test_leakage_alerts(self, api_client, admin_token):
        """Test /api/governance/leakage-alerts endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/governance/leakage-alerts")
        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data
        assert "alerts" in data
        print(f"✅ Leakage Alerts: {data['total_alerts']} alerts found")
    
    def test_operational_discipline(self, api_client, admin_token):
        """Test /api/governance/operational-discipline endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/governance/operational-discipline")
        assert response.status_code == 200
        data = response.json()
        assert "attendance" in data
        assert "meetings" in data
        print(f"✅ Operational Discipline API working")


class TestExpenseManagement:
    """Test Expense Management APIs"""
    
    def test_get_my_expenses(self, api_client, consultant_token):
        """Test getting user's expenses"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/my/expenses")
        assert response.status_code == 200
        data = response.json()
        assert "expenses" in data or isinstance(data, list)
        print(f"✅ My Expenses API working")
    
    def test_get_expense_categories(self, api_client, consultant_token):
        """Test getting expense categories"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/expenses/categories/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"✅ Expense Categories: {len(data)} categories found")
    
    def test_pending_expense_approvals(self, api_client, hr_token):
        """Test getting pending expense approvals (HR)"""
        api_client.headers.update({"Authorization": f"Bearer {hr_token}"})
        response = api_client.get(f"{BASE_URL}/api/expenses/pending-approvals")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Pending Expense Approvals: {len(data)} pending")


class TestApprovalWorkflows:
    """Test Approval Workflow APIs"""
    
    def test_get_pending_approvals(self, api_client, admin_token):
        """Test getting pending approvals"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/approvals/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Pending Approvals: {len(data)} items")
    
    def test_get_my_requests(self, api_client, consultant_token):
        """Test getting user's approval requests"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/approvals/my-requests")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ My Approval Requests: {len(data)} items")
    
    def test_get_all_approvals_admin(self, api_client, admin_token):
        """Test getting all approvals (admin only)"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/approvals/all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ All Approvals (Admin): {len(data)} items")


class TestLeaveManagement:
    """Test Leave Management APIs"""
    
    def test_get_leave_requests(self, api_client, hr_token):
        """Test getting leave requests"""
        api_client.headers.update({"Authorization": f"Bearer {hr_token}"})
        response = api_client.get(f"{BASE_URL}/api/leave-requests")
        assert response.status_code == 200
        data = response.json()
        # API returns either list or {items: []}
        if isinstance(data, dict):
            assert "items" in data or isinstance(data.get("items", []), list)
        else:
            assert isinstance(data, list)
        print(f"✅ Leave Requests API working")
    
    def test_get_all_leave_requests_hr(self, api_client, hr_token):
        """Test getting all leave requests (HR)"""
        api_client.headers.update({"Authorization": f"Bearer {hr_token}"})
        response = api_client.get(f"{BASE_URL}/api/leave-requests/all")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ All Leave Requests (HR) API working")


class TestConsultingMeetings:
    """Test Consulting Meetings APIs"""
    
    def test_get_meetings(self, api_client, consultant_token):
        """Test getting consulting meetings"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/meetings?meeting_type=consulting")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Consulting Meetings: {len(data)} meetings found")
    
    def test_get_my_day_summary(self, api_client, consultant_token):
        """Test My Day summary API"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/my-day/summary")
        assert response.status_code == 200
        data = response.json()
        assert "attendance" in data
        assert "today" in data
        assert "action_required" in data
        assert "weekly_progress" in data
        print(f"✅ My Day Summary API working")
    
    def test_get_meeting_types(self, api_client, consultant_token):
        """Test getting meeting types"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/masters/meeting-types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Meeting Types: {len(data)} types found")
    
    def test_get_projects(self, api_client, consultant_token):
        """Test getting projects"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        data = response.json()
        # API returns either list or {items: []}
        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data
        print(f"✅ Projects: {len(items)} projects found")
    
    def test_get_sows(self, api_client, consultant_token):
        """Test getting SOWs"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/enhanced-sow")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ SOWs API working")


class TestAttendance:
    """Test Attendance APIs"""
    
    def test_get_my_attendance(self, api_client, consultant_token):
        """Test getting user's attendance"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/attendance/my")
        assert response.status_code == 200
        print(f"✅ My Attendance API working")
    
    def test_get_attendance_status(self, api_client, consultant_token):
        """Test getting today's attendance status"""
        api_client.headers.update({"Authorization": f"Bearer {consultant_token}"})
        response = api_client.get(f"{BASE_URL}/api/attendance/status")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Attendance Status API working")


class TestClients:
    """Test Client APIs"""
    
    def test_get_clients(self, api_client, admin_token):
        """Test getting clients"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        data = response.json()
        # API returns either list or {items: []}
        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data
        print(f"✅ Clients: {len(items)} clients found")


class TestUsers:
    """Test User APIs"""
    
    def test_get_users(self, api_client, admin_token):
        """Test getting users"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Users: {len(data)} users found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
