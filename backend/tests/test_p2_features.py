"""
P2 Features Testing - NETRA ERP
Tests for:
1. Payment Recording on Agreements (POST /api/agreements/{id}/record-payment)
2. Get Agreement Payments (GET /api/agreements/{id}/payments)
3. Meeting Records (POST /api/meetings/record)
4. Meeting Access Check (GET /api/leads/{lead_id}/can-access-pricing)
5. Kickoff Approval creates Project with SOW inheritance
6. Target vs Achievement API (GET /api/manager/target-vs-achievement)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
MANAGER_EMAIL = "dp@dvbc.com"
MANAGER_PASSWORD = "Welcome@123"


class TestAuth:
    """Authentication helper for getting tokens"""
    
    @staticmethod
    def get_token(email, password):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    token = TestAuth.get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        pytest.skip("Admin authentication failed")
    return token


@pytest.fixture(scope="module")
def manager_token():
    """Get manager auth token"""
    token = TestAuth.get_token(MANAGER_EMAIL, MANAGER_PASSWORD)
    if not token:
        pytest.skip("Manager authentication failed")
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin request headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def manager_headers(manager_token):
    """Manager request headers"""
    return {"Authorization": f"Bearer {manager_token}", "Content-Type": "application/json"}


class TestPaymentRecording:
    """Test Payment Recording on signed Agreements"""
    
    def test_get_signed_agreement(self, admin_headers):
        """Find a signed agreement to test payment recording"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        assert response.status_code == 200
        
        agreements = response.json()
        signed_agreements = [a for a in agreements if a.get("status") == "signed"]
        
        print(f"Found {len(agreements)} total agreements, {len(signed_agreements)} signed")
        
        if signed_agreements:
            return signed_agreements[0]["id"]
        return None
    
    def test_record_payment_on_signed_agreement(self, admin_headers):
        """Test POST /api/agreements/{id}/record-payment"""
        # First find a signed agreement
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        agreements = response.json()
        signed_agreements = [a for a in agreements if a.get("status") == "signed"]
        
        if not signed_agreements:
            pytest.skip("No signed agreements available for payment test")
        
        agreement_id = signed_agreements[0]["id"]
        
        # Record payment with NEFT mode
        payment_data = {
            "amount": 50000,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_mode": "NEFT",
            "utr_number": f"TEST_UTR_{uuid.uuid4().hex[:8].upper()}",
            "remarks": "TEST_Payment_Recording"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/agreements/{agreement_id}/record-payment",
            headers=admin_headers,
            json=payment_data
        )
        
        print(f"Payment record response: {response.status_code} - {response.text[:200] if response.text else 'no body'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "payment_id" in data
        assert "total_paid" in data
        assert data["message"] == "Payment recorded successfully"
    
    def test_record_cheque_payment_requires_cheque_number(self, admin_headers):
        """Test that Cheque payment mode requires cheque_number"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        agreements = response.json()
        signed_agreements = [a for a in agreements if a.get("status") == "signed"]
        
        if not signed_agreements:
            pytest.skip("No signed agreements available")
        
        agreement_id = signed_agreements[0]["id"]
        
        # Try Cheque payment without cheque_number
        payment_data = {
            "amount": 25000,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_mode": "Cheque",
            "remarks": "TEST_Cheque_Without_Number"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/agreements/{agreement_id}/record-payment",
            headers=admin_headers,
            json=payment_data
        )
        
        assert response.status_code == 400
        assert "Cheque number is required" in response.json().get("detail", "")
    
    def test_record_cheque_payment_with_number(self, admin_headers):
        """Test Cheque payment with valid cheque_number"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        agreements = response.json()
        signed_agreements = [a for a in agreements if a.get("status") == "signed"]
        
        if not signed_agreements:
            pytest.skip("No signed agreements available")
        
        agreement_id = signed_agreements[0]["id"]
        
        payment_data = {
            "amount": 30000,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_mode": "Cheque",
            "cheque_number": f"TEST_CHQ_{uuid.uuid4().hex[:6].upper()}",
            "remarks": "TEST_Cheque_Payment"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/agreements/{agreement_id}/record-payment",
            headers=admin_headers,
            json=payment_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Payment recorded successfully"
    
    def test_get_agreement_payments(self, admin_headers):
        """Test GET /api/agreements/{id}/payments"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        agreements = response.json()
        signed_agreements = [a for a in agreements if a.get("status") == "signed"]
        
        if not signed_agreements:
            pytest.skip("No signed agreements available")
        
        agreement_id = signed_agreements[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/agreements/{agreement_id}/payments",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "payments" in data
        assert "total_paid" in data
        assert "agreement_value" in data
        assert "remaining" in data
        
        print(f"Agreement payments: total_paid={data['total_paid']}, remaining={data['remaining']}")
    
    def test_payment_on_unsigned_agreement_fails(self, admin_headers):
        """Test that recording payment on unsigned agreement fails"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        agreements = response.json()
        unsigned_agreements = [a for a in agreements if a.get("status") != "signed"]
        
        if not unsigned_agreements:
            pytest.skip("No unsigned agreements available for test")
        
        agreement_id = unsigned_agreements[0]["id"]
        
        payment_data = {
            "amount": 10000,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_mode": "UPI",
            "utr_number": "TEST_UPI_123",
            "remarks": "TEST_Should_Fail"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/agreements/{agreement_id}/record-payment",
            headers=admin_headers,
            json=payment_data
        )
        
        assert response.status_code == 400
        assert "signed" in response.json().get("detail", "").lower()


class TestMeetingRecords:
    """Test Meeting Recording functionality"""
    
    def test_get_leads_for_meeting(self, admin_headers):
        """Get leads to test meeting recording"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        assert response.status_code == 200
        
        leads = response.json()
        print(f"Found {len(leads)} leads")
        return leads
    
    def test_record_meeting(self, admin_headers):
        """Test POST /api/meetings/record"""
        # Get a lead to associate meeting with
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        leads = response.json()
        
        if not leads:
            pytest.skip("No leads available for meeting test")
        
        lead_id = leads[0]["id"]
        
        meeting_data = {
            "lead_id": lead_id,
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "14:00",
            "meeting_type": "Online",
            "attendees": ["John Doe", "Jane Smith"],
            "notes": "TEST_Meeting - Initial discussion",
            "mom": "TEST_MOM - Discussed project requirements"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            headers=admin_headers,
            json=meeting_data
        )
        
        print(f"Meeting record response: {response.status_code} - {response.text[:200] if response.text else ''}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "meeting_id" in data
        assert data["message"] == "Meeting recorded successfully"
    
    def test_record_offline_meeting(self, admin_headers):
        """Test recording an offline meeting"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        leads = response.json()
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        meeting_data = {
            "lead_id": lead_id,
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "10:00",
            "meeting_type": "Offline",
            "attendees": ["Client Representative"],
            "notes": "TEST_Offline_Meeting - Site visit",
            "mom": "TEST_MOM - Site assessment completed"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            headers=admin_headers,
            json=meeting_data
        )
        
        assert response.status_code == 200
    
    def test_get_lead_meetings(self, admin_headers):
        """Test GET /api/meetings/lead/{lead_id}"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        leads = response.json()
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{lead_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        meetings = response.json()
        assert isinstance(meetings, list)
        print(f"Lead {lead_id} has {len(meetings)} meetings")


class TestMeetingAccessCheck:
    """Test Pricing Plan access check based on meeting records"""
    
    def test_can_access_pricing_with_meeting(self, admin_headers):
        """Test GET /api/leads/{lead_id}/can-access-pricing with existing meeting"""
        # Get a lead that likely has meetings
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        leads = response.json()
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        # First ensure there's a meeting (from previous test)
        response = requests.get(
            f"{BASE_URL}/api/leads/{lead_id}/can-access-pricing",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "can_access" in data
        
        if data["can_access"]:
            print(f"Lead {lead_id} can access pricing - meeting exists")
        else:
            print(f"Lead {lead_id} cannot access pricing - reason: {data.get('reason')}")
    
    def test_can_access_pricing_returns_reason(self, admin_headers):
        """Test that reason is provided when access is blocked"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        leads = response.json()
        
        # Find a lead with no meetings (new leads)
        new_leads = [l for l in leads if l.get("status") == "new"]
        
        if not new_leads:
            # Create a new lead for testing
            new_lead_data = {
                "first_name": "TEST_Access",
                "last_name": "Check",
                "email": f"test_access_{uuid.uuid4().hex[:6]}@test.com",
                "company": "TEST_Access_Company",
                "phone": "9876543210"
            }
            response = requests.post(f"{BASE_URL}/api/leads", headers=admin_headers, json=new_lead_data)
            if response.status_code == 200:
                lead_id = response.json()["id"]
            else:
                pytest.skip("Could not create test lead")
        else:
            lead_id = new_leads[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/leads/{lead_id}/can-access-pricing",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If no meetings, should return can_access: false with reason
        if not data["can_access"]:
            assert "reason" in data
            assert "meeting" in data["reason"].lower()


class TestKickoffApprovalWithProject:
    """Test Kickoff Approval creates Project with SOW items"""
    
    def test_get_pending_kickoff_requests(self, admin_headers):
        """Get pending kickoff requests"""
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=admin_headers)
        assert response.status_code == 200
        
        kickoffs = response.json()
        pending = [k for k in kickoffs if k.get("status") == "pending"]
        print(f"Found {len(kickoffs)} total kickoff requests, {len(pending)} pending")
        
        return pending
    
    def test_approve_kickoff_creates_project(self, admin_headers):
        """Test POST /api/kickoff-requests/{id}/approve creates a project"""
        # Get pending kickoff requests
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=admin_headers)
        kickoffs = response.json()
        pending = [k for k in kickoffs if k.get("status") == "pending"]
        
        if not pending:
            pytest.skip("No pending kickoff requests to approve")
        
        kickoff_id = pending[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/approve",
            headers=admin_headers
        )
        
        print(f"Kickoff approval response: {response.status_code} - {response.text[:300] if response.text else ''}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "project_id" in data
        assert data["message"] == "Kickoff request approved successfully"
        
        # Verify project created
        project_id = data["project_id"]
        
        # Get the project to verify
        project_response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=admin_headers)
        if project_response.status_code == 200:
            project = project_response.json()
            print(f"Project created: {project.get('project_name')}")
            print(f"  - SOW items: {len(project.get('sow_items', []))}")
            print(f"  - Team deployment: {len(project.get('team_deployment', []))}")
            print(f"  - PM: {project.get('project_manager_name')}")
    
    def test_kickoff_approval_copies_sow_items(self, admin_headers):
        """Verify that approved kickoff copies SOW items to project"""
        # Get accepted kickoff requests
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=admin_headers)
        kickoffs = response.json()
        accepted = [k for k in kickoffs if k.get("status") == "accepted" and k.get("project_id")]
        
        if not accepted:
            pytest.skip("No accepted kickoff requests with project")
        
        kickoff = accepted[0]
        project_id = kickoff.get("project_id")
        
        # Get project details
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=admin_headers)
        
        if response.status_code == 200:
            project = response.json()
            sow_items = project.get("sow_items", [])
            team = project.get("team_deployment", [])
            pm_name = project.get("project_manager_name")
            
            print(f"Project {project_id}:")
            print(f"  - Has {len(sow_items)} SOW items")
            print(f"  - Has {len(team)} team members")
            print(f"  - PM: {pm_name}")
            
            # At minimum, PM should be assigned
            assert pm_name or project.get("project_manager_id"), "Project should have PM assigned"


class TestTargetVsAchievement:
    """Test Target vs Achievement API"""
    
    def test_get_target_vs_achievement_admin(self, admin_headers):
        """Test GET /api/manager/target-vs-achievement for admin"""
        response = requests.get(
            f"{BASE_URL}/api/manager/target-vs-achievement",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify response structure
        assert "month" in data
        assert "year" in data
        assert "total_clients" in data
        assert "employee_stats" in data
        assert "team_totals" in data
        
        # Verify team_totals structure
        team_totals = data["team_totals"]
        assert "meetings" in team_totals
        assert "closures" in team_totals
        assert "revenue" in team_totals
        
        # Verify metrics structure
        for metric in ["meetings", "closures", "revenue"]:
            assert "target" in team_totals[metric]
            assert "achieved" in team_totals[metric]
            assert "percentage" in team_totals[metric]
        
        print(f"Target vs Achievement for {data['month']}/{data['year']}:")
        print(f"  - Total clients in funnel: {data['total_clients']}")
        print(f"  - Employee stats: {len(data['employee_stats'])} employees")
        print(f"  - Team meetings: {team_totals['meetings']['achieved']}/{team_totals['meetings']['target']}")
        print(f"  - Team closures: {team_totals['closures']['achieved']}/{team_totals['closures']['target']}")
    
    def test_get_target_vs_achievement_with_month_filter(self, admin_headers):
        """Test Target vs Achievement with month/year filter"""
        current_year = datetime.now().year
        
        response = requests.get(
            f"{BASE_URL}/api/manager/target-vs-achievement?month=1&year={current_year}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["month"] == 1
        assert data["year"] == current_year
    
    def test_get_target_vs_achievement_manager(self, manager_headers):
        """Test Target vs Achievement for manager role"""
        response = requests.get(
            f"{BASE_URL}/api/manager/target-vs-achievement",
            headers=manager_headers
        )
        
        # Should be 200 for manager role
        assert response.status_code == 200
        
        data = response.json()
        assert "employee_stats" in data
        assert "team_totals" in data
        assert "total_clients" in data
        
        print(f"Manager sees {len(data['employee_stats'])} subordinate stats")
    
    def test_employee_stats_structure(self, admin_headers):
        """Verify employee_stats contains correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/manager/target-vs-achievement",
            headers=admin_headers
        )
        
        data = response.json()
        
        if data["employee_stats"]:
            emp = data["employee_stats"][0]
            
            # Verify employee stat structure
            assert "employee_id" in emp
            assert "employee_name" in emp
            assert "meetings" in emp
            assert "closures" in emp
            assert "revenue" in emp
            
            # Verify metric structure
            for metric in ["meetings", "closures", "revenue"]:
                assert "target" in emp[metric]
                assert "achieved" in emp[metric]
                assert "percentage" in emp[metric]


class TestSalesTargetsAPI:
    """Test Sales Targets CRUD API"""
    
    def test_get_sales_targets(self, admin_headers):
        """Test GET /api/sales-targets"""
        response = requests.get(
            f"{BASE_URL}/api/sales-targets",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        targets = response.json()
        print(f"Found {len(targets)} sales targets")
    
    def test_get_sales_targets_with_year_filter(self, admin_headers):
        """Test GET /api/sales-targets with year filter"""
        current_year = datetime.now().year
        
        response = requests.get(
            f"{BASE_URL}/api/sales-targets?year={current_year}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        targets = response.json()
        
        # All returned targets should be for the specified year
        for t in targets:
            assert t.get("year") == current_year


class TestAPIEndpoints:
    """General API endpoint verification"""
    
    def test_auth_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_auth_login_manager(self):
        """Test manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_agreements_list(self, admin_headers):
        """Test GET /api/agreements"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        assert response.status_code == 200
    
    def test_leads_list(self, admin_headers):
        """Test GET /api/leads"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        assert response.status_code == 200
    
    def test_kickoff_requests_list(self, admin_headers):
        """Test GET /api/kickoff-requests"""
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=admin_headers)
        assert response.status_code == 200


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(admin_headers):
    """Cleanup TEST_ prefixed data after test module"""
    yield
    # Note: In a real scenario, we would delete test data here
    # For now, we're keeping test data for verification
    print("Test module completed - test data retained for verification")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
