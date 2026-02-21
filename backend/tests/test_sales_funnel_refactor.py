"""
Test file for Sales Funnel Refactor with:
- Target Management UI (Create, Edit, Delete yearly sales targets)
- Sales Targets API (POST /api/sales-targets with employee_id, year, monthly_targets)
- Agreement E-Sign (POST /api/agreements/{id}/send-to-client)
- Agreement Upload Signed (POST /api/agreements/{id}/upload-signed)
- Kickoff Request flow (Create and approve)
- Manager Dashboard (/manager-leads)
"""

import pytest
import requests
import os
import uuid
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        """Get manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dp@dvbc.com",
            "password": "Welcome@123"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert response.status_code == 200, f"HR login failed: {response.text}"
        return response.json().get("access_token")

    def test_admin_login(self):
        """Test admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print("Admin login successful")

    def test_manager_login(self):
        """Test manager can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dp@dvbc.com",
            "password": "Welcome@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("Manager login successful")


class TestSalesTargetsAPI:
    """Test Sales Targets API - Create, Read, Update, Delete yearly sales targets"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_employee_id(self, admin_headers):
        """Get a valid employee ID for testing"""
        # First get employees list
        response = requests.get(f"{BASE_URL}/api/employees", headers=admin_headers)
        assert response.status_code == 200
        employees = response.json()
        if employees and len(employees) > 0:
            return employees[0].get('employee_id') or employees[0].get('id')
        # If no employee found, skip
        pytest.skip("No employees found for testing sales targets")
    
    def test_get_sales_targets_empty(self, admin_headers):
        """Test GET /api/sales-targets with no filters"""
        response = requests.get(f"{BASE_URL}/api/sales-targets", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET sales-targets returned {len(data)} targets")
    
    def test_get_sales_targets_with_year_filter(self, admin_headers):
        """Test GET /api/sales-targets with year filter"""
        response = requests.get(f"{BASE_URL}/api/sales-targets?year=2026", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET sales-targets with year=2026 returned {len(data)} targets")
    
    def test_create_yearly_sales_target(self, admin_headers, test_employee_id):
        """Test POST /api/sales-targets - Create yearly target with monthly_targets"""
        target_data = {
            "employee_id": test_employee_id,
            "year": 2026,
            "monthly_targets": {
                "1": 100000, "2": 120000, "3": 130000,
                "4": 140000, "5": 150000, "6": 160000,
                "7": 170000, "8": 180000, "9": 190000,
                "10": 200000, "11": 210000, "12": 220000
            },
            "target_type": "revenue"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales-targets",
            json=target_data,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Create target failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "id" in data
        print(f"Created sales target: {data}")
        return data.get("id")
    
    def test_get_sales_target_by_employee(self, admin_headers, test_employee_id):
        """Test GET /api/sales-targets with employee_id filter"""
        response = requests.get(
            f"{BASE_URL}/api/sales-targets?employee_id={test_employee_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET sales-targets for employee {test_employee_id} returned {len(data)} targets")
    
    def test_update_sales_target(self, admin_headers, test_employee_id):
        """Test PATCH /api/sales-targets/{id} - Update existing target"""
        # First get existing target
        response = requests.get(
            f"{BASE_URL}/api/sales-targets?employee_id={test_employee_id}&year=2026",
            headers=admin_headers
        )
        assert response.status_code == 200
        targets = response.json()
        
        if not targets:
            # Create a target first
            target_data = {
                "employee_id": test_employee_id,
                "year": 2026,
                "monthly_targets": {"1": 50000, "2": 50000, "3": 50000, "4": 50000, "5": 50000, "6": 50000,
                                   "7": 50000, "8": 50000, "9": 50000, "10": 50000, "11": 50000, "12": 50000},
                "target_type": "revenue"
            }
            create_resp = requests.post(f"{BASE_URL}/api/sales-targets", json=target_data, headers=admin_headers)
            assert create_resp.status_code == 200
            target_id = create_resp.json().get("id")
        else:
            target_id = targets[0].get('id')
        
        # Update the target
        update_data = {
            "employee_id": test_employee_id,
            "year": 2026,
            "monthly_targets": {
                "1": 200000, "2": 200000, "3": 200000, "4": 200000, "5": 200000, "6": 200000,
                "7": 200000, "8": 200000, "9": 200000, "10": 200000, "11": 200000, "12": 200000
            },
            "target_type": "closures"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/sales-targets/{target_id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        print(f"Updated sales target {target_id}")
    
    def test_delete_sales_target(self, admin_headers, test_employee_id):
        """Test DELETE /api/sales-targets/{id}"""
        # Create a target specifically for deletion
        target_data = {
            "employee_id": test_employee_id,
            "year": 2027,  # Use different year to avoid conflict
            "monthly_targets": {"1": 10000, "2": 10000, "3": 10000, "4": 10000, "5": 10000, "6": 10000,
                               "7": 10000, "8": 10000, "9": 10000, "10": 10000, "11": 10000, "12": 10000},
            "target_type": "meetings"
        }
        create_resp = requests.post(f"{BASE_URL}/api/sales-targets", json=target_data, headers=admin_headers)
        assert create_resp.status_code == 200
        target_id = create_resp.json().get("id")
        
        # Delete the target
        response = requests.delete(
            f"{BASE_URL}/api/sales-targets/{target_id}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Delete failed: {response.text}"
        print(f"Deleted sales target {target_id}")
        
        # Verify deletion
        get_resp = requests.get(f"{BASE_URL}/api/sales-targets?year=2027&employee_id={test_employee_id}", headers=admin_headers)
        targets = get_resp.json()
        assert all(t.get('id') != target_id for t in targets), "Target was not deleted"


class TestAgreementESign:
    """Test Agreement E-Sign endpoints: send-to-client, upload-signed, sign"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def test_agreement_id(self, admin_headers):
        """Get an existing agreement ID for testing"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        assert response.status_code == 200
        agreements = response.json()
        if agreements and len(agreements) > 0:
            # Find an agreement that isn't signed yet, or use any agreement
            for agr in agreements:
                if agr.get('status') != 'signed':
                    return agr.get('id')
            return agreements[0].get('id')
        pytest.skip("No agreements found for testing")
    
    def test_get_agreements(self, admin_headers):
        """Test GET /api/agreements"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET agreements returned {len(data)} agreements")
    
    def test_send_agreement_to_client(self, admin_headers, test_agreement_id):
        """Test POST /api/agreements/{id}/send-to-client"""
        send_data = {
            "client_email": "test.client@example.com",
            "client_name": "Test Client"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/agreements/{test_agreement_id}/send-to-client",
            json=send_data,
            headers=admin_headers
        )
        # This should work or return 400 if already sent
        assert response.status_code in [200, 400], f"Send to client failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            print(f"Agreement sent to client: {data}")
        else:
            print(f"Agreement already processed: {response.text}")
    
    def test_upload_signed_agreement(self, admin_headers, test_agreement_id):
        """Test POST /api/agreements/{id}/upload-signed"""
        # Create a dummy PDF file for testing
        file_content = b"%PDF-1.4 Test signed agreement document"
        files = {
            'file': ('signed_agreement.pdf', io.BytesIO(file_content), 'application/pdf')
        }
        
        # Remove Content-Type from headers for multipart upload
        upload_headers = {"Authorization": admin_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/agreements/{test_agreement_id}/upload-signed",
            files=files,
            headers=upload_headers
        )
        # Should succeed or return appropriate error
        assert response.status_code in [200, 400], f"Upload failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            print(f"Uploaded signed agreement: {data}")
        else:
            print(f"Upload response: {response.text}")
    
    def test_get_agreement_full_details(self, admin_headers, test_agreement_id):
        """Test GET /api/agreements/{id}/full"""
        response = requests.get(
            f"{BASE_URL}/api/agreements/{test_agreement_id}/full",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Get full agreement failed: {response.text}"
        data = response.json()
        assert "agreement" in data
        print(f"Got full agreement details: {data.get('agreement', {}).get('agreement_number')}")


class TestKickoffRequests:
    """Test Kickoff Request flow: Create and approve"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    def test_get_kickoff_requests(self, admin_headers):
        """Test GET /api/kickoff-requests"""
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET kickoff-requests returned {len(data)} requests")
    
    def test_create_kickoff_request(self, admin_headers):
        """Test POST /api/kickoff-requests"""
        # First get a consultant/PM to assign
        emp_resp = requests.get(f"{BASE_URL}/api/employees/consultants", headers=admin_headers)
        consultants = emp_resp.json() if emp_resp.status_code == 200 else []
        
        pm_id = None
        pm_name = "Test PM"
        if consultants and len(consultants) > 0:
            pm_id = consultants[0].get('user_id') or consultants[0].get('id')
            pm_name = f"{consultants[0].get('first_name', '')} {consultants[0].get('last_name', '')}".strip()
        
        kickoff_data = {
            "client_name": "TEST_Kickoff_Client",
            "project_name": "TEST_Project_Kickoff",
            "project_type": "mixed",
            "total_meetings": 12,
            "meeting_frequency": "Monthly",
            "project_tenure_months": 12,
            "expected_start_date": "2026-03-01",
            "assigned_pm_id": pm_id,
            "assigned_pm_name": pm_name,
            "notes": "Test kickoff request created by automation"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            json=kickoff_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201], f"Create kickoff failed: {response.text}"
        data = response.json()
        print(f"Created kickoff request: {data}")
        return data
    
    def test_approve_kickoff_request(self, admin_headers):
        """Test POST /api/kickoff-requests/{id}/approve"""
        # Get pending kickoff requests
        response = requests.get(f"{BASE_URL}/api/kickoff-requests?status=pending", headers=admin_headers)
        if response.status_code == 200:
            requests_list = response.json()
            if requests_list and len(requests_list) > 0:
                kickoff_id = requests_list[0].get('id')
                
                approve_response = requests.post(
                    f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/approve",
                    json={"notes": "Approved by automation test"},
                    headers=admin_headers
                )
                # May succeed or already approved
                assert approve_response.status_code in [200, 400], f"Approve failed: {approve_response.text}"
                print(f"Approve kickoff response: {approve_response.json()}")
            else:
                print("No pending kickoff requests to approve")
        else:
            print(f"Could not get kickoff requests: {response.text}")


class TestManagerDashboard:
    """Test Manager Dashboard and manager-leads endpoint"""
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dp@dvbc.com",
            "password": "Welcome@123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def manager_headers(self, manager_token):
        return {"Authorization": f"Bearer {manager_token}", "Content-Type": "application/json"}
    
    def test_manager_subordinate_leads(self, manager_headers):
        """Test GET /api/manager/subordinate-leads"""
        response = requests.get(f"{BASE_URL}/api/manager/subordinate-leads", headers=manager_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "subordinates" in data or isinstance(data, dict)
        print(f"Manager subordinate leads response keys: {data.keys() if isinstance(data, dict) else 'list'}")
    
    def test_manager_leads_dashboard_access(self, manager_headers):
        """Test manager can access leads for their subordinates"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=manager_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Manager can access {len(data)} leads")


class TestLeadsAndAgreementsListView:
    """Test that Leads and Agreements pages default to list view"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    def test_leads_api(self, admin_headers):
        """Test GET /api/leads returns data"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET leads returned {len(data)} leads")
    
    def test_leads_with_status_filter(self, admin_headers):
        """Test GET /api/leads with status filter (Stage dropdown filter)"""
        # Test various status filters
        statuses = ['new', 'meeting', 'pricing_plan', 'sow', 'quotation', 'agreement', 'closed']
        for status in statuses[:3]:  # Test first 3 statuses
            response = requests.get(f"{BASE_URL}/api/leads?status={status}", headers=admin_headers)
            assert response.status_code == 200, f"Failed for status {status}: {response.text}"
            data = response.json()
            print(f"Leads with status '{status}': {len(data)}")
    
    def test_agreements_api(self, admin_headers):
        """Test GET /api/agreements returns data"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"GET agreements returned {len(data)} agreements")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_cleanup_test_data(self, admin_headers):
        """Cleanup any TEST_ prefixed data"""
        # Cleanup kickoff requests with TEST_ prefix
        kickoff_resp = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=admin_headers)
        if kickoff_resp.status_code == 200:
            for kr in kickoff_resp.json():
                if kr.get('client_name', '').startswith('TEST_') or kr.get('project_name', '').startswith('TEST_'):
                    requests.delete(f"{BASE_URL}/api/kickoff-requests/{kr.get('id')}", headers=admin_headers)
                    print(f"Cleaned up kickoff request: {kr.get('id')}")
        
        print("Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
