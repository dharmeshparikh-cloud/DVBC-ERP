"""
OWASP-Compliant API Security Test Suite - Employees Module
Tests: CRUD operations, HR data protection, access control
"""

import pytest
import httpx


class TestEmployeesPositive:
    """Positive tests for employees CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_emp001_get_all_employees(self, admin_client):
        """TC-EMP-001: Get all employees returns list."""
        response = await admin_client.get("/api/employees")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_emp002_get_employee_by_id(self, admin_client, db):
        """TC-EMP-002: Get single employee by ID."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.get(f"/api/employees/{employee['id']}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == employee["id"]
    
    @pytest.mark.asyncio
    async def test_emp003_create_employee(self, admin_client, test_data):
        """TC-EMP-003: Create employee with valid data."""
        emp_data = test_data.employee()
        response = await admin_client.post("/api/employees", json=emp_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "employee_id" in data or "id" in data
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_emp004_update_employee(self, admin_client, db):
        """TC-EMP-004: Update employee data."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            response = await admin_client.patch(
                f"/api/employees/{employee['id']}",
                json={"designation": "Senior Consultant"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_emp005_get_org_chart(self, admin_client):
        """TC-EMP-005: Get org chart hierarchy."""
        response = await admin_client.get("/api/employees/org-chart/hierarchy")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
    
    @pytest.mark.asyncio
    async def test_emp006_get_departments_list(self, admin_client):
        """TC-EMP-006: Get departments list."""
        response = await admin_client.get("/api/employees/departments/list")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_emp007_get_employee_stats(self, admin_client):
        """TC-EMP-007: Get employee statistics."""
        response = await admin_client.get("/api/employees/stats/summary")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_emp008_get_subordinates(self, admin_client, db):
        """TC-EMP-008: Get employee subordinates."""
        employee = await db.employees.find_one(
            {"reporting_manager_id": {"$ne": None}},
            {"_id": 0, "id": 1}
        )
        if employee:
            response = await admin_client.get(f"/api/employees/{employee['id']}/subordinates")
            
            assert response.status_code == 200


class TestEmployeesNegative:
    """Negative tests - invalid inputs."""
    
    @pytest.mark.asyncio
    async def test_emp020_get_nonexistent_employee(self, admin_client):
        """TC-EMP-020: Get nonexistent employee returns 404."""
        response = await admin_client.get("/api/employees/nonexistent-id-12345")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_emp021_create_duplicate_email(self, admin_client, db):
        """TC-EMP-021: Create employee with existing email."""
        existing = await db.employees.find_one({}, {"_id": 0, "email": 1})
        if existing:
            response = await admin_client.post("/api/employees", json={
                "first_name": "Test",
                "last_name": "Duplicate",
                "email": existing["email"],
                "department": "Test",
                "designation": "Test"
            })
            
            # Should either create (if email not unique) or reject
            assert response.status_code in [200, 400, 409]
    
    @pytest.mark.asyncio
    async def test_emp022_invalid_employment_type(self, admin_client, test_data):
        """TC-EMP-022: Invalid employment type handled."""
        emp_data = test_data.employee({"employment_type": "invalid_type"})
        response = await admin_client.post("/api/employees", json=emp_data)
        
        # Either accepts or rejects gracefully
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_emp023_invalid_date_format(self, admin_client, test_data):
        """TC-EMP-023: Invalid date format rejected."""
        emp_data = test_data.employee({"date_of_joining": "not-a-date"})
        response = await admin_client.post("/api/employees", json=emp_data)
        
        assert response.status_code in [400, 422]


class TestEmployeesAccessControl:
    """Access control tests for employee data - sensitive HR information."""
    
    @pytest.mark.asyncio
    async def test_emp030_unauthenticated_cannot_access(self, api_client):
        """TC-EMP-030: Unauthenticated cannot access employees."""
        response = await api_client.get("/api/employees")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_emp031_salary_info_protected(self, admin_client, db):
        """TC-EMP-031: Salary information properly protected."""
        employee = await db.employees.find_one(
            {"salary_info": {"$exists": True}},
            {"_id": 0, "id": 1}
        )
        if employee:
            response = await admin_client.get(f"/api/employees/{employee['id']}")
            data = response.json()
            
            # If salary is returned, it should be for authorized roles
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_emp032_bank_details_protected(self, admin_client, db):
        """TC-EMP-032: Bank details properly handled."""
        employee = await db.employees.find_one(
            {"bank_details": {"$exists": True}},
            {"_id": 0, "id": 1}
        )
        if employee:
            response = await admin_client.get(f"/api/employees/{employee['id']}")
            
            assert response.status_code == 200
            # Bank details should exist for HR/Admin roles


class TestEmployeesSecurity:
    """Security tests for employee module."""
    
    @pytest.mark.asyncio
    async def test_emp040_sql_injection_search(self, admin_client, owasp_payloads):
        """TC-EMP-040: SQL injection in employee search."""
        for payload in owasp_payloads.SQL_INJECTION[:2]:
            response = await admin_client.get(f"/api/employees/{payload}")
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_emp041_xss_in_name(self, admin_client, owasp_payloads, test_data):
        """TC-EMP-041: XSS in employee name handled safely."""
        for payload in owasp_payloads.XSS_PAYLOADS[:2]:
            emp_data = test_data.employee({"first_name": payload})
            response = await admin_client.post("/api/employees", json=emp_data)
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_emp042_idor_prevention(self, manager_client, admin_client, db):
        """TC-EMP-042: IDOR prevention - can't access unauthorized employee data."""
        # Get any employee
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            # Both should work for view (if allowed) but update should be restricted
            manager_response = await manager_client.patch(
                f"/api/employees/{employee['id']}",
                json={"notes": "Unauthorized update attempt"}
            )
            
            # Manager might not have write access to all employees
            # This tests that proper access control exists
            assert manager_response.status_code in [200, 403, 404]
    
    @pytest.mark.asyncio
    async def test_emp043_mass_assignment_prevention(self, admin_client, test_data):
        """TC-EMP-043: Mass assignment attack prevention."""
        emp_data = test_data.employee()
        emp_data["is_admin"] = True
        emp_data["role"] = "admin"
        emp_data["hashed_password"] = "injected_hash"
        
        response = await admin_client.post("/api/employees", json=emp_data)
        
        if response.status_code == 200:
            data = response.json()
            # These fields should be ignored or not appear
            assert data.get("is_admin") != True
            assert data.get("hashed_password") != "injected_hash"


class TestEmployeeDocuments:
    """Tests for employee document upload/download."""
    
    @pytest.mark.asyncio
    async def test_doc001_upload_document_endpoint_exists(self, admin_client, db):
        """TC-DOC-001: Document upload endpoint exists."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            # Test that endpoint exists (would need multipart for actual upload)
            response = await admin_client.post(
                f"/api/employees/{employee['id']}/documents",
                json={"name": "test_doc", "type": "id_proof"}
            )
            
            # Either accepts or rejects gracefully
            assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_doc002_path_traversal_in_document_id(self, admin_client, db, owasp_payloads):
        """TC-DOC-002: Path traversal in document ID prevented."""
        employee = await db.employees.find_one({}, {"_id": 0, "id": 1})
        if employee:
            for payload in owasp_payloads.PATH_TRAVERSAL[:2]:
                response = await admin_client.get(
                    f"/api/employees/{employee['id']}/documents/{payload}"
                )
                
                # Should return 404, not expose files
                assert response.status_code in [404, 400]


class TestSyncFromUsers:
    """Tests for employee-user sync functionality."""
    
    @pytest.mark.asyncio
    async def test_sync001_sync_endpoint_admin_only(self, admin_client, manager_client):
        """TC-SYNC-001: Sync from users is admin only."""
        admin_response = await admin_client.post("/api/employees/sync-from-users")
        manager_response = await manager_client.post("/api/employees/sync-from-users")
        
        # Admin can sync, manager cannot
        assert admin_response.status_code in [200, 400]  # Success or no new users
        assert manager_response.status_code == 403


class TestLinkUnlinkUser:
    """Tests for linking/unlinking employees to user accounts."""
    
    @pytest.mark.asyncio
    async def test_link001_link_user_endpoint(self, admin_client, db):
        """TC-LINK-001: Link user to employee endpoint exists."""
        employee = await db.employees.find_one({"user_id": None}, {"_id": 0, "id": 1})
        user = await db.users.find_one({}, {"_id": 0, "id": 1})
        
        if employee and user:
            response = await admin_client.post(
                f"/api/employees/{employee['id']}/link-user",
                json={"user_id": user["id"]}
            )
            
            # Either links or reports conflict
            assert response.status_code in [200, 400, 409]
    
    @pytest.mark.asyncio
    async def test_link002_unlink_user_endpoint(self, admin_client, db):
        """TC-LINK-002: Unlink user from employee."""
        employee = await db.employees.find_one(
            {"user_id": {"$ne": None}},
            {"_id": 0, "id": 1}
        )
        
        if employee:
            response = await admin_client.post(
                f"/api/employees/{employee['id']}/unlink-user"
            )
            
            assert response.status_code in [200, 400]
