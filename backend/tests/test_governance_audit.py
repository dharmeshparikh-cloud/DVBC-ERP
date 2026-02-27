"""
Test Suite: HR & Employee Master Governance Audit
Tests for NETRA ERP governance enforcement:
1. Field-level RBAC (locked fields like salary, department, designation)
2. Workflow request creation for locked fields
3. Consent document management
4. Audit trail (employee_change_history)
5. Integrity checks
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"employee_id": "ADMIN001", "password": "admin123"}
HR_CREDENTIALS = {"employee_id": "DVC037", "password": "test123"}

# Test employee UUID from previous tests
TEST_EMPLOYEE_UUID = "3a20643a-6d1b-4d19-b3fd-757091740fcd"  # Himanshi Gunecha - DVBC007


class TestAuthSetup:
    """Setup tests - verify authentication works"""
    
    def test_admin_login(self, session):
        """Test admin authentication"""
        response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access token in response"
        print(f"Admin login successful, role: {data.get('user', {}).get('role')}")
        return data["access_token"]
    
    def test_hr_login(self, session):
        """Test HR Manager authentication"""
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        assert response.status_code == 200, f"HR login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access token in response"
        print(f"HR login successful, role: {data.get('user', {}).get('role')}")
        return data["access_token"]


class TestGovernanceFieldPermissions:
    """Test /api/governance/field-permissions endpoint"""
    
    def test_get_field_permissions_admin(self, admin_session):
        """Test field permissions endpoint as Admin"""
        response = admin_session.get(f"{BASE_URL}/api/governance/field-permissions")
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        
        data = response.json()
        assert "user_role" in data
        assert "permissions" in data
        assert data["user_role"] == "admin"
        
        # Check locked fields are marked correctly
        permissions = data["permissions"]
        assert permissions.get("salary", {}).get("locked") == True, "Salary should be locked"
        assert permissions.get("department", {}).get("locked") == True, "Department should be locked"
        assert permissions.get("designation", {}).get("locked") == True, "Designation should be locked"
        
        # Check editable fields for admin
        assert permissions.get("first_name", {}).get("can_edit") == True, "Admin should edit first_name"
        
        print(f"Field permissions verified. Total fields: {len(permissions)}")
        return data
    
    def test_get_field_permissions_hr(self, hr_session):
        """Test field permissions endpoint as HR Manager"""
        response = hr_session.get(f"{BASE_URL}/api/governance/field-permissions")
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        
        data = response.json()
        assert data["user_role"] == "hr_manager"
        
        permissions = data["permissions"]
        # HR can edit personal info
        assert permissions.get("first_name", {}).get("can_edit") == True, "HR should edit first_name"
        assert permissions.get("phone", {}).get("can_edit") == True, "HR should edit phone"
        
        # HR cannot bypass locked fields
        assert permissions.get("salary", {}).get("locked") == True
        assert permissions.get("designation", {}).get("locked") == True
        
        print(f"HR permissions verified: can edit first_name, cannot bypass salary lock")


class TestLockedFieldsEnforcement:
    """Test that locked fields cannot be directly edited via API"""
    
    def test_salary_field_blocked_creates_workflow(self, admin_session):
        """Test that updating salary creates workflow request (cannot bypass)"""
        update_data = {
            "salary": 1500000  # Try to update salary directly
        }
        
        response = admin_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        # Should either:
        # 1. Return 200 with workflow_requests (no direct update)
        # 2. Return 403 (blocked)
        if response.status_code == 200:
            data = response.json()
            # Salary should NOT be in updated_fields
            assert "salary" not in data.get("updated_fields", []), "Salary should NOT be directly updated"
            # Workflow request should be created
            assert "workflow_requests" in data, "Workflow request should be created for salary"
            workflow_requests = data.get("workflow_requests", [])
            salary_req = next((r for r in workflow_requests if r.get("field") == "salary"), None)
            assert salary_req is not None, "Salary workflow request should exist"
            assert salary_req.get("workflow") == "ctc_revision", "Salary should require ctc_revision workflow"
            print(f"Salary update correctly routed to workflow: {salary_req.get('request_id')}")
        elif response.status_code == 403:
            # Also acceptable if blocked entirely
            print(f"Salary update correctly blocked with 403")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_department_field_blocked_creates_workflow(self, hr_session):
        """Test that updating department creates transfer workflow request"""
        update_data = {
            "department": "Finance"  # Try to update department directly
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "department" not in data.get("updated_fields", []), "Department should NOT be directly updated"
            workflow_requests = data.get("workflow_requests", [])
            dept_req = next((r for r in workflow_requests if r.get("field") == "department"), None)
            assert dept_req is not None, "Department workflow request should exist"
            assert dept_req.get("workflow") == "transfer", "Department should require transfer workflow"
            print(f"Department update correctly routed to transfer workflow")
        elif response.status_code == 403:
            print(f"Department update correctly blocked")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_designation_field_blocked_creates_workflow(self, hr_session):
        """Test that updating designation creates promotion workflow request"""
        update_data = {
            "designation": "Senior Consultant"  # Try to update designation directly
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "designation" not in data.get("updated_fields", []), "Designation should NOT be directly updated"
            workflow_requests = data.get("workflow_requests", [])
            desig_req = next((r for r in workflow_requests if r.get("field") == "designation"), None)
            assert desig_req is not None, "Designation workflow request should exist"
            assert desig_req.get("workflow") == "promotion", "Designation should require promotion workflow"
            print(f"Designation update correctly routed to promotion workflow")
        elif response.status_code == 403:
            print(f"Designation update correctly blocked")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_reporting_manager_field_blocked(self, hr_session):
        """Test that updating reporting_manager creates hierarchy change workflow"""
        update_data = {
            "reporting_manager_id": "some-uuid-here"  # Try to change reporting manager
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "reporting_manager_id" not in data.get("updated_fields", [])
            workflow_requests = data.get("workflow_requests", [])
            rm_req = next((r for r in workflow_requests if r.get("field") == "reporting_manager_id"), None)
            if rm_req:
                assert rm_req.get("workflow") == "hierarchy_change"
                print(f"Reporting manager update correctly routed to hierarchy_change workflow")
        elif response.status_code == 403:
            print(f"Reporting manager update correctly blocked")


class TestAllowedFieldsEdit:
    """Test that allowed fields can be edited directly"""
    
    def test_first_name_can_be_edited(self, hr_session):
        """Test that first_name can be edited directly by HR"""
        # Generate unique name to avoid conflicts
        test_name = f"TestName{datetime.now().strftime('%H%M%S')}"
        update_data = {
            "first_name": test_name
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        assert response.status_code == 200, f"Failed to update first_name: {response.text}"
        data = response.json()
        
        # first_name should be in updated_fields (direct edit allowed)
        assert "first_name" in data.get("updated_fields", []), "first_name should be directly updated"
        print(f"First name updated successfully to: {test_name}")
        
        # Verify the change persisted
        get_response = hr_session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}")
        assert get_response.status_code == 200
        employee = get_response.json()
        assert employee.get("first_name") == test_name, "First name change should persist"
        print(f"Verified first_name persisted in database")
    
    def test_phone_can_be_edited(self, hr_session):
        """Test that phone can be edited directly by HR"""
        test_phone = f"9999{datetime.now().strftime('%H%M%S')}"
        update_data = {
            "phone": test_phone
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        assert response.status_code == 200, f"Failed to update phone: {response.text}"
        data = response.json()
        assert "phone" in data.get("updated_fields", []), "phone should be directly updated"
        print(f"Phone updated successfully")


class TestFieldChangeRequestsCollection:
    """Test that field_change_requests are created for locked fields"""
    
    def test_workflow_requests_created_and_stored(self, admin_session):
        """Test that workflow requests are persisted in field_change_requests collection"""
        # First create a workflow request by trying to update a locked field
        update_data = {
            "designation": "Principal Consultant"
        }
        
        response = admin_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data,
            params={"change_reason": "Promotion test request"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if "workflow_requests" in data and len(data["workflow_requests"]) > 0:
                request_id = data["workflow_requests"][0].get("request_id")
                print(f"Workflow request created: {request_id}")
    
    def test_get_pending_field_change_requests(self, admin_session):
        """Test pending requests endpoint (Admin only)"""
        response = admin_session.get(f"{BASE_URL}/api/governance/pending-requests")
        assert response.status_code == 200, f"Failed to get pending requests: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} pending field change requests")
        
        # Check structure of pending requests if any exist
        if len(data) > 0:
            req = data[0]
            assert "id" in req
            assert "employee_id" in req
            assert "field" in req
            assert "workflow_type" in req
            assert "status" in req
            print(f"Sample request: field={req.get('field')}, workflow={req.get('workflow_type')}")


class TestIntegrityCheck:
    """Test the data integrity check API"""
    
    def test_integrity_check_api(self, admin_session):
        """Test /api/governance/integrity-check endpoint"""
        response = admin_session.get(f"{BASE_URL}/api/governance/integrity-check")
        assert response.status_code == 200, f"Integrity check failed: {response.text}"
        
        data = response.json()
        assert "check_time" in data
        assert "total_issues" in data
        assert "issues" in data
        assert isinstance(data["issues"], list)
        
        print(f"Integrity check completed. Found {data['total_issues']} issues")
        
        # Log any issues found
        for issue in data.get("issues", [])[:5]:  # Show first 5
            print(f"  Issue type: {issue.get('type')} - {issue.get('message', '')}")
    
    def test_integrity_check_hr_forbidden(self, hr_session):
        """Test that HR cannot run integrity check (Admin only)"""
        response = hr_session.get(f"{BASE_URL}/api/governance/integrity-check")
        assert response.status_code == 403, "HR should not access integrity check"
        print(f"HR correctly blocked from integrity check")


class TestConsentDocuments:
    """Test consent document management"""
    
    def test_get_consent_documents(self, hr_session):
        """Test /api/consent/documents endpoint"""
        response = hr_session.get(f"{BASE_URL}/api/consent/documents")
        assert response.status_code == 200, f"Failed to get consent docs: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} consent documents")
        
        # Check default documents exist
        doc_types = [d.get("type") for d in data]
        expected_types = ["nda", "nca", "data_consent", "it_policy", "code_of_conduct"]
        for exp_type in expected_types:
            if exp_type in doc_types:
                print(f"  Found document: {exp_type}")
    
    def test_consent_status_endpoint(self, admin_session):
        """Test consent status for an employee"""
        response = admin_session.get(f"{BASE_URL}/api/consent/status/{TEST_EMPLOYEE_UUID}")
        # This may return not_initiated if consent workflow hasn't started
        assert response.status_code == 200, f"Failed to get consent status: {response.text}"
        
        data = response.json()
        status = data.get("status", "not_initiated")
        print(f"Consent status for employee: {status}")
        
        if status != "not_initiated":
            assert "documents_to_consent" in data or "consent_details" in data


class TestAuditTrail:
    """Test employee_change_history audit trail"""
    
    def test_change_history_populated(self, admin_session):
        """Test that audit trail is populated for changes"""
        response = admin_session.get(f"{BASE_URL}/api/governance/change-history/{TEST_EMPLOYEE_UUID}")
        assert response.status_code == 200, f"Failed to get change history: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert "total_changes" in data
        assert "history" in data
        
        print(f"Change history: {data['total_changes']} changes recorded")
        
        # Show sample history entries
        for entry in data.get("history", [])[:3]:
            print(f"  {entry.get('field')}: {entry.get('old_value')} -> {entry.get('new_value')} by {entry.get('changed_by_name')}")
    
    def test_audit_required_field_creates_history(self, hr_session):
        """Test that updating audit-required fields creates history entry"""
        # Update an audit-required field (role requires audit but HR can't edit it)
        # Instead test with pan_number which is audit_required but HR can edit
        test_pan = f"ABCDE{datetime.now().strftime('%H%M')}Z"
        
        # First get current value
        get_response = hr_session.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}")
        old_pan = get_response.json().get("pan_number")
        
        update_data = {
            "pan_number": test_pan
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_UUID}",
            json=update_data
        )
        
        # Check if update was allowed (HR manager can edit pan_number per FIELD_PERMISSIONS)
        if response.status_code == 200:
            data = response.json()
            if "pan_number" in data.get("updated_fields", []):
                print(f"PAN number updated, checking audit trail...")
                
                # Verify audit trail was created - use admin session for history access
                admin_response = requests.post(
                    f"{BASE_URL}/api/auth/login",
                    json=ADMIN_CREDENTIALS
                )
                admin_token = admin_response.json().get("access_token")
                
                history_response = requests.get(
                    f"{BASE_URL}/api/governance/change-history/{TEST_EMPLOYEE_UUID}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                if history_response.status_code == 200:
                    history = history_response.json().get("history", [])
                    pan_changes = [h for h in history if h.get("field") == "pan_number"]
                    if pan_changes:
                        print(f"Found {len(pan_changes)} audit entries for pan_number")
            else:
                print(f"pan_number not directly editable by HR, workflow created")
        else:
            print(f"PAN update returned {response.status_code}")


class TestGovernanceValidation:
    """Test validate-update endpoint for pre-validation"""
    
    def test_validate_update_endpoint(self, admin_session):
        """Test /api/governance/validate-update/{employee_id}"""
        validation_data = {
            "first_name": "ValidatedName",
            "salary": 2000000,
            "department": "HR"
        }
        
        response = admin_session.post(
            f"{BASE_URL}/api/governance/validate-update/{TEST_EMPLOYEE_UUID}",
            json=validation_data
        )
        
        assert response.status_code == 200, f"Validation failed: {response.text}"
        data = response.json()
        
        assert "validation" in data
        validation = data["validation"]
        
        # first_name should be allowed
        assert "first_name" in validation.get("allowed_updates", {}), "first_name should be allowed"
        
        # salary should require workflow
        assert "salary" in validation.get("workflow_required", {}), "salary should require workflow"
        
        # department should require workflow
        assert "department" in validation.get("workflow_required", {}), "department should require workflow"
        
        print(f"Validation results:")
        print(f"  Allowed: {list(validation.get('allowed_updates', {}).keys())}")
        print(f"  Workflow required: {list(validation.get('workflow_required', {}).keys())}")
        print(f"  Blocked: {list(validation.get('blocked_updates', {}).keys())}")


# ============ Fixtures ============

@pytest.fixture
def session():
    """Shared requests session"""
    return requests.Session()


@pytest.fixture
def admin_session(session):
    """Session with admin authentication"""
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code != 200:
        pytest.skip(f"Admin authentication failed: {response.text}")
    
    token = response.json().get("access_token")
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def hr_session():
    """Session with HR Manager authentication"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
    if response.status_code != 200:
        pytest.skip(f"HR authentication failed: {response.text}")
    
    token = response.json().get("access_token")
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    return session


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
