"""
Test Suite for Domain-Specific Dashboards and Kickoff Requests
Tests:
- Sales Dashboard API (/api/stats/sales-dashboard)
- Consulting Dashboard API (/api/stats/consulting-dashboard)
- HR Dashboard API (/api/stats/hr-dashboard)
- Kickoff Requests CRUD (/api/kickoff-requests)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthSetup:
    """Authentication and setup tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def executive_token(self):
        """Get executive (sales role) auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        assert response.status_code == 200, f"Executive login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        """Get manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]


class TestSalesDashboardAPI(TestAuthSetup):
    """Test Sales Dashboard API endpoint"""
    
    def test_sales_dashboard_returns_200(self, admin_token):
        """Test sales dashboard returns 200 status"""
        response = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_sales_dashboard_has_pipeline_data(self, admin_token):
        """Test sales dashboard returns pipeline data with correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        # Verify pipeline structure
        assert "pipeline" in data
        pipeline = data["pipeline"]
        assert "total" in pipeline
        assert "new" in pipeline
        assert "contacted" in pipeline
        assert "qualified" in pipeline
        assert "proposal" in pipeline
        assert "closed" in pipeline
        
        # Verify all values are integers
        for key, value in pipeline.items():
            assert isinstance(value, int), f"Pipeline {key} should be int"
    
    def test_sales_dashboard_has_client_data(self, admin_token):
        """Test sales dashboard returns client counts"""
        response = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "clients" in data
        assert "my_clients" in data["clients"]
        assert "total_clients" in data["clients"]
    
    def test_sales_dashboard_has_quotations_agreements(self, admin_token):
        """Test sales dashboard returns quotation and agreement counts"""
        response = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "quotations" in data
        assert "pending" in data["quotations"]
        
        assert "agreements" in data
        assert "pending" in data["agreements"]
        assert "approved" in data["agreements"]
    
    def test_sales_dashboard_has_kickoff_revenue(self, admin_token):
        """Test sales dashboard returns kickoff and revenue data"""
        response = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "kickoffs" in data
        assert "pending" in data["kickoffs"]
        
        assert "revenue" in data
        assert "total" in data["revenue"]
        
        assert "conversion_rate" in data
    
    def test_sales_dashboard_executive_access(self, executive_token):
        """Test executive role can access sales dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {executive_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "pipeline" in data
    
    def test_sales_dashboard_unauthorized_without_token(self):
        """Test sales dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/stats/sales-dashboard")
        assert response.status_code == 401


class TestConsultingDashboardAPI(TestAuthSetup):
    """Test Consulting Dashboard API endpoint"""
    
    def test_consulting_dashboard_returns_200(self, admin_token):
        """Test consulting dashboard returns 200 status"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_consulting_dashboard_has_project_stats(self, admin_token):
        """Test consulting dashboard returns project statistics"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "projects" in data
        projects = data["projects"]
        assert "active" in projects
        assert "completed" in projects
        assert "on_hold" in projects
        assert "at_risk" in projects
    
    def test_consulting_dashboard_has_meeting_stats(self, admin_token):
        """Test consulting dashboard returns meeting delivery stats"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "meetings" in data
        meetings = data["meetings"]
        assert "delivered" in meetings
        assert "pending" in meetings
        assert "committed" in meetings
    
    def test_consulting_dashboard_has_efficiency_score(self, admin_token):
        """Test consulting dashboard returns efficiency score"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "efficiency_score" in data
        assert isinstance(data["efficiency_score"], (int, float))
    
    def test_consulting_dashboard_has_incoming_kickoffs(self, admin_token):
        """Test consulting dashboard returns incoming kickoff count for PMs"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "incoming_kickoffs" in data
        assert isinstance(data["incoming_kickoffs"], int)
    
    def test_consulting_dashboard_has_workload(self, admin_token):
        """Test consulting dashboard returns consultant workload data"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "consultant_workload" in data
        assert "average" in data["consultant_workload"]


class TestHRDashboardAPI(TestAuthSetup):
    """Test HR Dashboard API endpoint"""
    
    def test_hr_dashboard_returns_200(self, admin_token):
        """Test HR dashboard returns 200 for authorized users"""
        response = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
    
    def test_hr_dashboard_has_employee_stats(self, admin_token):
        """Test HR dashboard returns employee statistics"""
        response = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "employees" in data
        employees = data["employees"]
        assert "total" in employees
        assert "new_this_month" in employees
        assert "by_department" in employees
        assert isinstance(employees["by_department"], dict)
    
    def test_hr_dashboard_has_attendance_stats(self, admin_token):
        """Test HR dashboard returns attendance statistics"""
        response = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "attendance" in data
        attendance = data["attendance"]
        assert "present_today" in attendance
        assert "absent_today" in attendance
        assert "wfh_today" in attendance
        assert "attendance_rate" in attendance
    
    def test_hr_dashboard_has_leave_stats(self, admin_token):
        """Test HR dashboard returns leave request statistics"""
        response = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "leaves" in data
        assert "pending_requests" in data["leaves"]
    
    def test_hr_dashboard_has_payroll_stats(self, admin_token):
        """Test HR dashboard returns payroll statistics"""
        response = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        assert "payroll" in data
        payroll = data["payroll"]
        assert "processed_this_month" in payroll
        assert "pending" in payroll
    
    def test_hr_dashboard_denied_for_non_hr_roles(self, executive_token):
        """Test HR dashboard returns 403 for non-HR users"""
        response = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {executive_token}"}
        )
        assert response.status_code == 403


class TestKickoffRequestsAPI(TestAuthSetup):
    """Test Kickoff Requests CRUD operations"""
    
    @pytest.fixture(scope="class")
    def approved_agreement_id(self, admin_token):
        """Get an approved agreement ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            agreements = response.json()
            if agreements:
                return agreements[0]["id"]
        return None
    
    @pytest.fixture(scope="class")
    def project_manager_id(self, admin_token):
        """Get a project manager ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/users?role=project_manager",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            pms = response.json()
            if pms:
                return pms[0]["id"]
        return None
    
    def test_get_kickoff_requests_returns_list(self, admin_token):
        """Test GET /kickoff-requests returns a list"""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_kickoff_request(self, admin_token, approved_agreement_id, project_manager_id):
        """Test creating a kickoff request"""
        if not approved_agreement_id:
            pytest.skip("No approved agreement found for testing")
        
        unique_name = f"TEST_Kickoff_{uuid.uuid4().hex[:8]}"
        payload = {
            "agreement_id": approved_agreement_id,
            "client_name": "Test Client",
            "project_name": unique_name,
            "project_type": "mixed",
            "total_meetings": 12,
            "project_value": 1000000,
            "expected_start_date": "2026-04-01T00:00:00Z",
            "assigned_pm_id": project_manager_id,
            "notes": "Created by pytest"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload
        )
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "message" in data
        
        # Return the ID for other tests
        return data["id"]
    
    def test_get_specific_kickoff_request(self, admin_token, approved_agreement_id, project_manager_id):
        """Test getting a specific kickoff request"""
        if not approved_agreement_id:
            pytest.skip("No approved agreement found")
        
        # First create one
        unique_name = f"TEST_Kickoff_Get_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": approved_agreement_id,
                "client_name": "Test Client Get",
                "project_name": unique_name,
                "project_type": "online",
                "total_meetings": 8,
                "notes": "For GET test"
            }
        )
        assert create_response.status_code == 200
        kickoff_id = create_response.json()["id"]
        
        # Then GET it
        get_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == kickoff_id
        assert data["project_name"] == unique_name
        assert data["status"] == "pending"
    
    def test_accept_kickoff_request(self, admin_token, approved_agreement_id):
        """Test accepting a kickoff request creates a project"""
        if not approved_agreement_id:
            pytest.skip("No approved agreement found")
        
        unique_name = f"TEST_Kickoff_Accept_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": approved_agreement_id,
                "client_name": "Test Accept Client",
                "project_name": unique_name,
                "project_type": "mixed",
                "total_meetings": 10,
                "expected_start_date": "2026-05-01T00:00:00Z"
            }
        )
        assert create_response.status_code == 200
        kickoff_id = create_response.json()["id"]
        
        # Accept the request
        accept_response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/accept",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert accept_response.status_code == 200
        data = accept_response.json()
        assert "project_id" in data
        assert "message" in data
        
        # Verify status changed to converted
        get_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.json()["status"] == "converted"
        assert get_response.json()["project_id"] is not None
    
    def test_reject_kickoff_request(self, admin_token, approved_agreement_id):
        """Test rejecting a kickoff request"""
        if not approved_agreement_id:
            pytest.skip("No approved agreement found")
        
        unique_name = f"TEST_Kickoff_Reject_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": approved_agreement_id,
                "client_name": "Test Reject Client",
                "project_name": unique_name,
                "project_type": "offline",
                "total_meetings": 6
            }
        )
        assert create_response.status_code == 200
        kickoff_id = create_response.json()["id"]
        
        # Reject the request
        reject_response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reject_response.status_code == 200
        
        # Verify status changed to rejected
        get_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.json()["status"] == "rejected"
        assert get_response.json()["project_id"] is None
    
    def test_cannot_accept_already_processed_request(self, admin_token, approved_agreement_id):
        """Test that processed requests cannot be accepted again"""
        if not approved_agreement_id:
            pytest.skip("No approved agreement found")
        
        unique_name = f"TEST_Kickoff_Double_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": approved_agreement_id,
                "client_name": "Test Double Process",
                "project_name": unique_name,
                "project_type": "mixed",
                "total_meetings": 5
            }
        )
        kickoff_id = create_response.json()["id"]
        
        # Accept first time
        requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/accept",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Try to accept again - should fail
        second_accept = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/accept",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert second_accept.status_code == 400
    
    def test_executive_can_create_kickoff_request(self, executive_token, approved_agreement_id):
        """Test that executive (sales role) can create kickoff requests"""
        if not approved_agreement_id:
            pytest.skip("No approved agreement found")
        
        unique_name = f"TEST_Kickoff_Exec_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {executive_token}"},
            json={
                "agreement_id": approved_agreement_id,
                "client_name": "Executive Test Client",
                "project_name": unique_name,
                "project_type": "mixed",
                "total_meetings": 15
            }
        )
        assert response.status_code == 200
        assert "id" in response.json()


class TestDashboardIntegration(TestAuthSetup):
    """Test dashboard integration scenarios"""
    
    def test_admin_sees_all_dashboard_types(self, admin_token):
        """Test admin can access all three domain dashboards"""
        # Sales
        sales_resp = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert sales_resp.status_code == 200
        
        # Consulting
        consulting_resp = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert consulting_resp.status_code == 200
        
        # HR
        hr_resp = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert hr_resp.status_code == 200
    
    def test_manager_access_to_dashboards(self, manager_token):
        """Test manager role can access all dashboards"""
        # Sales
        sales_resp = requests.get(
            f"{BASE_URL}/api/stats/sales-dashboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert sales_resp.status_code == 200
        
        # Consulting
        consulting_resp = requests.get(
            f"{BASE_URL}/api/stats/consulting-dashboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert consulting_resp.status_code == 200
        
        # HR (manager should have access)
        hr_resp = requests.get(
            f"{BASE_URL}/api/stats/hr-dashboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert hr_resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
