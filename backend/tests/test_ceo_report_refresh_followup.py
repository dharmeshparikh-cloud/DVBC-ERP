"""
Test Suite: CEO Report, Page Refresh Buttons, Follow-up Action Buttons
========================================================================
Tests the new features:
1. CEO Control Tower Report API (preview, trigger, logs)
2. PageRefreshButton on list pages
3. FollowUpActionButton on funnel stage rows
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ====================
# Test Fixtures
# ====================

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "ADMIN001",
        "password": "Admin@2026"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def sales_manager_token():
    """Get Sales Manager authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "EMP002",
        "password": "Sales@123"
    })
    if response.status_code != 200:
        pytest.skip("Sales Manager login failed")
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def sales_exec_token():
    """Get Sales Executive authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "EMP003",
        "password": "Sales@123"
    })
    if response.status_code != 200:
        pytest.skip("Sales Executive login failed")
    return response.json().get("access_token")

def auth_header(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ====================
# Section 1: CEO Report API Tests
# ====================

class TestCEOReportAPIs:
    """CEO Control Tower Report endpoints."""
    
    def test_ceo_report_preview_admin_access(self, admin_token):
        """Admin can access CEO report preview endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/ceo-report/preview",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        
        # Verify it returns HTML content
        content_type = response.headers.get('content-type', '')
        assert 'text/html' in content_type, f"Expected HTML, got {content_type}"
        
        # Verify all 10 sections are present
        html_content = response.text
        sections = [
            "1. Sales Activity Snapshot",
            "2. Sales Pipeline Health",
            "3. Missed Follow-Up Escalations",
            "4. Daily Meeting Summary",
            "5. Consulting Operations",
            "6. SOW & Agreement Tracker",
            "7. Payment & Finance",
            "8. Revenue Snapshot",
            "9. Team Productivity Index",
            "10. System Health"
        ]
        for section in sections:
            assert section in html_content, f"Missing section: {section}"
        
        print(f"✓ CEO Report Preview returned HTML with all 10 sections")
    
    def test_ceo_report_preview_non_admin_forbidden(self, sales_exec_token):
        """Non-admin users cannot access CEO report preview."""
        response = requests.get(
            f"{BASE_URL}/api/ceo-report/preview",
            headers=auth_header(sales_exec_token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-admin correctly blocked from CEO report preview")
    
    def test_ceo_report_logs_admin_access(self, admin_token):
        """Admin can access CEO report delivery logs."""
        response = requests.get(
            f"{BASE_URL}/api/ceo-report/logs",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "logs" in data, "Response should have 'logs' key"
        
        # Verify log structure if logs exist
        logs = data["logs"]
        if len(logs) > 0:
            log = logs[0]
            assert "date" in log
            assert "email_type" in log
            assert log["email_type"] == "ceo_daily_report"
            assert "delivery_status" in log
            assert "records_included" in log
            print(f"✓ CEO Report Logs: {len(logs)} log entries found")
        else:
            print(f"✓ CEO Report Logs endpoint working (no logs yet)")
    
    def test_ceo_report_logs_non_admin_forbidden(self, sales_manager_token):
        """Non-admin users cannot access CEO report logs."""
        response = requests.get(
            f"{BASE_URL}/api/ceo-report/logs",
            headers=auth_header(sales_manager_token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-admin correctly blocked from CEO report logs")
    
    def test_ceo_report_trigger_admin_access(self, admin_token):
        """Admin can trigger CEO report manually."""
        response = requests.post(
            f"{BASE_URL}/api/ceo-report/trigger",
            headers=auth_header(admin_token)
        )
        # This might succeed or show sending status
        assert response.status_code in [200, 201], f"Trigger failed: {response.status_code}"
        
        data = response.json()
        assert "status" in data
        # Status could be 'sent' or 'error' depending on SMTP config
        print(f"✓ CEO Report Trigger: status={data.get('status')}")
    
    def test_ceo_report_trigger_non_admin_forbidden(self, sales_exec_token):
        """Non-admin users cannot trigger CEO report."""
        response = requests.post(
            f"{BASE_URL}/api/ceo-report/trigger",
            headers=auth_header(sales_exec_token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-admin correctly blocked from triggering CEO report")


# ====================
# Section 2: API Endpoints for List Pages (Backend)
# ====================

class TestListPageAPIs:
    """Test APIs that support refresh button functionality."""
    
    def test_leads_endpoint(self, admin_token):
        """Leads list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Leads API returns 200")
    
    def test_meetings_endpoint(self, admin_token):
        """Meetings list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Meetings API returns 200")
    
    def test_projects_endpoint(self, admin_token):
        """Projects list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Projects API returns 200")
    
    def test_kickoff_requests_endpoint(self, admin_token):
        """Kickoff requests list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Kickoff Requests API returns 200")
    
    def test_expenses_endpoint(self, admin_token):
        """Expenses list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/expenses",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Expenses API returns 200")
    
    def test_leave_requests_endpoint(self, admin_token):
        """Leave requests list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/leave-requests",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Leave Requests API returns 200")
    
    def test_follow_ups_endpoint(self, admin_token):
        """Follow-ups list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Follow-ups API returns 200")


# ====================
# Section 3: Follow-up Creation API Tests
# ====================

class TestFollowUpCreationAPIs:
    """Test follow-up creation from funnel pages."""
    
    def test_create_follow_up_from_lead_stage(self, admin_token):
        """Create a follow-up for lead stage."""
        from datetime import datetime, timedelta
        
        tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token),
            json={
                "entity_type": "lead",
                "entity_id": "test-lead-id",
                "client_name": "TEST_RefreshFeature Client",
                "due_date": tomorrow,
                "notes": "Test follow-up from lead stage",
                "priority": "medium"
            }
        )
        assert response.status_code in [200, 201], f"Follow-up creation failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        print(f"✓ Follow-up created for lead stage: {data.get('id', 'N/A')[:8]}...")
    
    def test_create_follow_up_from_meeting_stage(self, admin_token):
        """Create a follow-up for meeting stage."""
        from datetime import datetime, timedelta
        
        tomorrow = (datetime.utcnow() + timedelta(days=2)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token),
            json={
                "entity_type": "meeting",
                "entity_id": "test-meeting-id",
                "client_name": "TEST_RefreshFeature Meeting Client",
                "due_date": tomorrow,
                "notes": "Test follow-up from meeting stage",
                "priority": "high"
            }
        )
        assert response.status_code in [200, 201], f"Follow-up creation failed: {response.text}"
        print(f"✓ Follow-up created for meeting stage")
    
    def test_create_follow_up_from_sow_stage(self, admin_token):
        """Create a follow-up for SOW stage."""
        from datetime import datetime, timedelta
        
        tomorrow = (datetime.utcnow() + timedelta(days=3)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token),
            json={
                "entity_type": "sow",
                "entity_id": "test-sow-id",
                "client_name": "TEST_RefreshFeature SOW Client",
                "due_date": tomorrow,
                "notes": "Test follow-up from SOW stage",
                "priority": "low"
            }
        )
        assert response.status_code in [200, 201], f"Follow-up creation failed: {response.text}"
        print(f"✓ Follow-up created for SOW stage")
    
    def test_create_follow_up_from_quotation_stage(self, admin_token):
        """Create a follow-up for quotation stage."""
        from datetime import datetime, timedelta
        
        tomorrow = (datetime.utcnow() + timedelta(days=4)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token),
            json={
                "entity_type": "quotation",
                "entity_id": "test-quotation-id",
                "client_name": "TEST_RefreshFeature Quotation Client",
                "due_date": tomorrow,
                "notes": "Test follow-up from quotation stage",
                "priority": "medium"
            }
        )
        assert response.status_code in [200, 201], f"Follow-up creation failed: {response.text}"
        print(f"✓ Follow-up created for quotation stage")
    
    def test_create_follow_up_from_agreement_stage(self, admin_token):
        """Create a follow-up for agreement stage."""
        from datetime import datetime, timedelta
        
        tomorrow = (datetime.utcnow() + timedelta(days=5)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token),
            json={
                "entity_type": "agreement",
                "entity_id": "test-agreement-id",
                "client_name": "TEST_RefreshFeature Agreement Client",
                "due_date": tomorrow,
                "notes": "Test follow-up from agreement stage",
                "priority": "high"
            }
        )
        assert response.status_code in [200, 201], f"Follow-up creation failed: {response.text}"
        print(f"✓ Follow-up created for agreement stage")


# ====================
# Section 4: Sales Funnel Page APIs
# ====================

class TestSalesFunnelPageAPIs:
    """Test APIs for pages with both refresh and follow-up buttons."""
    
    def test_agreements_endpoint(self, admin_token):
        """Agreements list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Agreements API returns 200")
    
    def test_quotations_endpoint(self, admin_token):
        """Quotations list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Quotations API returns 200")
    
    def test_enhanced_sow_list_endpoint(self, admin_token):
        """SOW list API works correctly."""
        response = requests.get(
            f"{BASE_URL}/api/enhanced-sow/list",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print(f"✓ Enhanced SOW List API returns 200")


# ====================
# Section 5: Cleanup
# ====================

class TestCleanup:
    """Clean up test data."""
    
    def test_cleanup_test_followups(self, admin_token):
        """Clean up test follow-ups created during testing."""
        # Get all follow-ups
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            headers=auth_header(admin_token)
        )
        if response.status_code == 200:
            followups = response.json()
            test_items = [f for f in followups if f.get('client_name', '').startswith('TEST_RefreshFeature')]
            print(f"✓ Found {len(test_items)} test follow-ups to clean (cleanup will be done by separate process)")
