"""
Test suite for My Day Bar and Global Sorting features
Tests:
1. /api/my-day/summary endpoint
2. Meetings sorting (latest first)
3. Notifications sorting (latest first)
4. Invoices sorting (latest first)
5. Leave requests sorting (latest first)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CONSULTANT_CREDS = {"employee_id": "EMP004", "password": "consultant123"}
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}


@pytest.fixture(scope="module")
def consultant_token():
    """Get consultant authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CONSULTANT_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Consultant authentication failed")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def consultant_headers(consultant_token):
    """Headers with consultant auth token"""
    return {"Authorization": f"Bearer {consultant_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestMyDaySummaryAPI:
    """Tests for /api/my-day/summary endpoint"""
    
    def test_my_day_summary_returns_200(self, consultant_headers):
        """Test that my-day/summary endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary", headers=consultant_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_my_day_summary_has_greeting(self, consultant_headers):
        """Test that response contains greeting with user name"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary", headers=consultant_headers)
        assert response.status_code == 200
        data = response.json()
        assert "greeting" in data
        assert "Test Consultant" in data["greeting"] or "Good" in data["greeting"]
    
    def test_my_day_summary_has_attendance(self, consultant_headers):
        """Test that response contains attendance status"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary", headers=consultant_headers)
        assert response.status_code == 200
        data = response.json()
        assert "attendance" in data
        assert "is_checked_in" in data["attendance"]
        assert "needs_action" in data["attendance"]
    
    def test_my_day_summary_has_today_meetings(self, consultant_headers):
        """Test that response contains today's meetings info"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary", headers=consultant_headers)
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "total_meetings" in data["today"]
        assert "meetings" in data["today"]
        assert "next_meeting" in data["today"]
    
    def test_my_day_summary_has_action_required(self, consultant_headers):
        """Test that response contains action_required section"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary", headers=consultant_headers)
        assert response.status_code == 200
        data = response.json()
        assert "action_required" in data
        action = data["action_required"]
        assert "overdue_moms" in action
        assert "pending_client_send" in action
        assert "missing_expenses" in action
        assert "open_tasks" in action
        assert "pending_expenses" in action
    
    def test_my_day_summary_has_weekly_progress(self, consultant_headers):
        """Test that response contains weekly progress"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary", headers=consultant_headers)
        assert response.status_code == 200
        data = response.json()
        assert "weekly_progress" in data
        progress = data["weekly_progress"]
        assert "total_meetings" in progress
        assert "delivered" in progress
        assert "mom_recorded" in progress
        assert "completion_pct" in progress
    
    def test_my_day_summary_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/my-day/summary")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestMeetingsSorting:
    """Tests for meetings list sorting (latest first)"""
    
    def test_meetings_endpoint_returns_200(self, admin_headers):
        """Test that meetings endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/meetings", headers=admin_headers)
        assert response.status_code == 200
    
    def test_consulting_meetings_endpoint_returns_200(self, admin_headers):
        """Test that consulting meetings endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=consulting", headers=admin_headers)
        assert response.status_code == 200
    
    def test_meetings_have_date_field(self, admin_headers):
        """Test that meetings have meeting_date field for sorting"""
        response = requests.get(f"{BASE_URL}/api/meetings", headers=admin_headers)
        assert response.status_code == 200
        meetings = response.json()
        if len(meetings) > 0:
            assert "meeting_date" in meetings[0] or "created_at" in meetings[0]


class TestNotificationsSorting:
    """Tests for notifications list sorting (latest first)"""
    
    def test_notifications_endpoint_returns_200(self, admin_headers):
        """Test that notifications endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=admin_headers)
        assert response.status_code == 200
    
    def test_notifications_have_created_at(self, admin_headers):
        """Test that notifications have created_at field for sorting"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=admin_headers)
        assert response.status_code == 200
        notifications = response.json()
        if len(notifications) > 0:
            assert "created_at" in notifications[0]


class TestInvoicesSorting:
    """Tests for invoices list sorting (latest first)"""
    
    def test_invoices_endpoint_returns_200(self, admin_headers):
        """Test that invoices endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/invoices", headers=admin_headers)
        assert response.status_code == 200
    
    def test_invoices_have_created_at(self, admin_headers):
        """Test that invoices have created_at field for sorting"""
        response = requests.get(f"{BASE_URL}/api/invoices", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        invoices = data if isinstance(data, list) else data.get("invoices", [])
        if len(invoices) > 0:
            assert "created_at" in invoices[0]


class TestLeaveRequestsSorting:
    """Tests for leave requests list sorting (latest first)"""
    
    def test_leave_requests_endpoint_returns_200(self, admin_headers):
        """Test that leave requests endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/leave-requests", headers=admin_headers)
        assert response.status_code == 200
    
    def test_leave_requests_all_endpoint_returns_200(self, admin_headers):
        """Test that all leave requests endpoint returns 200 for HR/admin"""
        response = requests.get(f"{BASE_URL}/api/leave-requests/all", headers=admin_headers)
        assert response.status_code == 200
    
    def test_leave_requests_have_created_at(self, admin_headers):
        """Test that leave requests have created_at field for sorting"""
        response = requests.get(f"{BASE_URL}/api/leave-requests", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        requests_list = data.get("items", data) if isinstance(data, dict) else data
        if len(requests_list) > 0:
            assert "created_at" in requests_list[0]


class TestSortUtilsIntegration:
    """Tests to verify sorting utilities are being used correctly"""
    
    def test_meetings_page_imports_sort_utils(self):
        """Verify Meetings.js imports sortByFields from sortUtils"""
        with open("/app/frontend/src/pages/Meetings.js", "r") as f:
            content = f.read()
        assert "import { sortByFields } from '../utils/sortUtils'" in content
        assert "sortByFields(meetings" in content or "sortByFields(meetings ||" in content
    
    def test_notifications_page_imports_sort_utils(self):
        """Verify Notifications.js imports sortByLatest from sortUtils"""
        with open("/app/frontend/src/pages/Notifications.js", "r") as f:
            content = f.read()
        assert "import { sortByLatest } from '../utils/sortUtils'" in content
        assert "sortByLatest(" in content
    
    def test_invoices_page_imports_sort_utils(self):
        """Verify Invoices.js imports sortByLatest from sortUtils"""
        with open("/app/frontend/src/pages/Invoices.js", "r") as f:
            content = f.read()
        assert "import { sortByLatest } from '../utils/sortUtils'" in content
        assert "sortByLatest(" in content
    
    def test_leave_management_page_imports_sort_utils(self):
        """Verify LeaveManagement.js imports sortByLatest from sortUtils"""
        with open("/app/frontend/src/pages/LeaveManagement.js", "r") as f:
            content = f.read()
        assert "import { sortByLatest } from '../utils/sortUtils'" in content
        assert "sortByLatest(" in content
    
    def test_consulting_meetings_has_my_day_bar(self):
        """Verify ConsultingMeetings.js imports and renders MyDayBar"""
        with open("/app/frontend/src/pages/ConsultingMeetings.js", "r") as f:
            content = f.read()
        assert "import MyDayBar from '../components/MyDayBar'" in content
        assert "<MyDayBar" in content or "<MyDayBar/>" in content or "<MyDayBar />" in content
    
    def test_my_day_bar_has_navigation_handlers(self):
        """Verify MyDayBar.jsx has navigation handlers for cards"""
        with open("/app/frontend/src/components/MyDayBar.jsx", "r") as f:
            content = f.read()
        assert "useNavigate" in content
        assert "handleNavigate" in content
        assert "onClick={() => handleNavigate" in content or "onClick={onClick}" in content
    
    def test_my_day_bar_has_done_badge(self):
        """Verify MyDayBar.jsx shows Done badge for completed items"""
        with open("/app/frontend/src/components/MyDayBar.jsx", "r") as f:
            content = f.read()
        assert "isComplete" in content
        assert "Done" in content
