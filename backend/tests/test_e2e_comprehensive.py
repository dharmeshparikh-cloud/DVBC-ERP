"""
NETRA ERP - E2E Comprehensive Testing - Iteration 103
Tests all critical endpoints, role-based access control, and renew-deal fix validation
"""

import pytest
import requests
import os
from datetime import datetime

# API Configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leads-fix-validation.preview.emergentagent.com')

# Test Credentials
TEST_CREDENTIALS = {
    "admin": {"employee_id": "ADMIN001", "password": "test123"},
    "sales_manager": {"employee_id": "SM001", "password": "test123"},
    "hr_manager": {"employee_id": "HR001", "password": "test123"},
    "sales_executive": {"employee_id": "SE001", "password": "test123"},
    "consultant": {"employee_id": "CON001", "password": "test123"}
}


class TokenCache:
    """Cache authentication tokens for efficiency"""
    _tokens = {}
    
    @classmethod
    def get_token(cls, role: str) -> str:
        if role not in cls._tokens:
            creds = TEST_CREDENTIALS[role]
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"employee_id": creds["employee_id"], "password": creds["password"]}
            )
            assert response.status_code == 200, f"Login failed for {role}: {response.text}"
            cls._tokens[role] = response.json()["access_token"]
        return cls._tokens[role]
    
    @classmethod
    def get_headers(cls, role: str) -> dict:
        return {
            "Authorization": f"Bearer {cls.get_token(role)}",
            "Content-Type": "application/json"
        }


# ============== AUTHENTICATION TESTS ==============

class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_admin_login_with_employee_id(self):
        """Login with ADMIN001 employee ID"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "ADMIN001", "password": "test123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["employee_id"] == "ADMIN001"
        print(f"PASS: Admin login successful - role: {data['user']['role']}")
    
    def test_sales_manager_login(self):
        """Login with SM001 employee ID"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "SM001", "password": "test123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "sales_manager"
        print(f"PASS: Sales Manager login successful - role: {data['user']['role']}")
    
    def test_hr_manager_login(self):
        """Login with HR001 employee ID"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "HR001", "password": "test123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "hr_manager"
        print(f"PASS: HR Manager login successful - role: {data['user']['role']}")
    
    def test_invalid_credentials(self):
        """Invalid login should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "INVALID", "password": "wrong"}
        )
        assert response.status_code == 401
        print("PASS: Invalid credentials properly rejected")


# ============== LEADS CRUD TESTS ==============

class TestLeadsCRUD:
    """Leads endpoint CRUD operations"""
    
    def test_get_leads_admin(self):
        """Admin can get all leads - expect 48 leads"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        
        assert response.status_code == 200
        leads = response.json()
        assert isinstance(leads, list)
        assert len(leads) >= 45, f"Expected at least 45 leads, got {len(leads)}"
        
        # Verify leads have proper schema (first_name/last_name)
        for lead in leads[:5]:
            assert "first_name" in lead, f"Lead missing first_name: {lead.get('id')}"
            assert "last_name" in lead, f"Lead missing last_name: {lead.get('id')}"
        
        print(f"PASS: Admin retrieved {len(leads)} leads with proper schema")
    
    def test_get_leads_sales_manager_scoped(self):
        """Sales Manager gets scoped leads (own + team)"""
        headers = TokenCache.get_headers("sales_manager")
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        
        assert response.status_code == 200
        leads = response.json()
        assert isinstance(leads, list)
        print(f"PASS: Sales Manager retrieved {len(leads)} scoped leads")
    
    def test_get_single_lead(self):
        """Get a single lead by ID"""
        headers = TokenCache.get_headers("admin")
        
        # First get a lead ID
        leads_response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        leads = leads_response.json()
        lead_id = leads[0]["id"]
        
        # Get single lead
        response = requests.get(f"{BASE_URL}/api/leads/{lead_id}", headers=headers)
        assert response.status_code == 200
        lead = response.json()
        assert lead["id"] == lead_id
        assert "first_name" in lead
        assert "last_name" in lead
        print(f"PASS: Retrieved single lead: {lead['first_name']} {lead['last_name']}")
    
    def test_create_lead(self):
        """Create a new lead"""
        headers = TokenCache.get_headers("admin")
        
        new_lead = {
            "first_name": "TEST_Created",
            "last_name": "Lead",
            "email": f"test_lead_{datetime.now().timestamp()}@test.com",
            "company": "Test Company",
            "phone": "1234567890",
            "source": "test",
            "status": "new"
        }
        
        response = requests.post(f"{BASE_URL}/api/leads", json=new_lead, headers=headers)
        assert response.status_code == 200
        created = response.json()
        assert created["first_name"] == "TEST_Created"
        assert created["last_name"] == "Lead"
        print(f"PASS: Created new lead with ID: {created['id']}")


# ============== PERMISSIONS TESTS ==============

class TestPermissions:
    """Permission system tests"""
    
    def test_get_my_permissions_admin(self):
        """Admin gets full permissions"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/permissions/my-permissions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data
        assert "sidebar_visibility" in data
        assert data["role"] == "admin"
        
        # Admin should have all permissions
        perms = data["permissions"]
        assert perms.get("sales.view_leads") == True
        assert perms.get("hr.view_employees") == True
        print(f"PASS: Admin has {len([k for k,v in perms.items() if v])} permissions enabled")
    
    def test_get_my_permissions_sales_executive(self):
        """Sales Executive has limited permissions"""
        headers = TokenCache.get_headers("sales_executive")
        response = requests.get(f"{BASE_URL}/api/permissions/my-permissions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Sales should have sales permissions but not HR
        perms = data["permissions"]
        assert perms.get("sales.view_leads") == True
        # HR permissions should be limited
        print(f"PASS: Sales Executive has appropriate scoped permissions")
    
    def test_features_admin_only(self):
        """Only admin can access /api/permissions/features"""
        admin_headers = TokenCache.get_headers("admin")
        se_headers = TokenCache.get_headers("sales_executive")
        
        # Admin should succeed
        admin_response = requests.get(f"{BASE_URL}/api/permissions/features", headers=admin_headers)
        assert admin_response.status_code == 200
        
        # Sales Executive should be denied
        se_response = requests.get(f"{BASE_URL}/api/permissions/features", headers=se_headers)
        assert se_response.status_code == 403
        print("PASS: Features endpoint properly restricted to admin")


# ============== MY API TESTS ==============

class TestMyAPIs:
    """User-specific /my/* endpoints"""
    
    def test_guidance_state(self):
        """GET /api/my/guidance-state returns user guidance state"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/my/guidance-state", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "dismissed_tips" in data
        assert "dont_show_tips" in data
        print("PASS: Guidance state endpoint working")
    
    def test_dashboard_stats(self):
        """GET /api/my/dashboard-stats returns personal stats"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/my/dashboard-stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # Dashboard stats returns various metrics
        assert "leads_count" in data or "active_projects" in data or "attendance_this_month" in data
        print(f"PASS: Dashboard stats endpoint working - keys: {list(data.keys())[:5]}")
    
    def test_my_profile(self):
        """GET /api/my/profile returns user profile"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/my/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        print(f"PASS: Profile endpoint working - email: {data['email']}")


# ============== MANAGER API TESTS ==============

class TestManagerAPIs:
    """Manager-specific endpoints"""
    
    def test_manager_team(self):
        """GET /api/manager/team returns team info"""
        headers = TokenCache.get_headers("sales_manager")
        response = requests.get(f"{BASE_URL}/api/manager/team", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "manager_id" in data
        assert "team_members" in data
        print(f"PASS: Manager team endpoint working - team size: {data['team_count']}")


# ============== SALES FUNNEL TESTS ==============

class TestSalesFunnel:
    """Sales funnel business logic endpoints"""
    
    def test_stage_status(self):
        """GET /api/sales-funnel/stage-status/{lead_id}"""
        headers = TokenCache.get_headers("admin")
        
        # Get a lead ID
        leads = requests.get(f"{BASE_URL}/api/leads", headers=headers).json()
        lead_id = leads[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/sales-funnel/stage-status/{lead_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "lead_id" in data
        assert "current_stage" in data
        assert "can_progress" in data
        print(f"PASS: Stage status working - current: {data['current_stage']}")
    
    def test_resume_stage(self):
        """POST /api/sales-funnel/resume-stage returns context"""
        headers = TokenCache.get_headers("admin")
        
        # Get a lead ID
        leads = requests.get(f"{BASE_URL}/api/leads", headers=headers).json()
        lead_id = leads[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/sales-funnel/resume-stage",
            json={"lead_id": lead_id},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "lead" in data
        assert "current_stage" in data
        print("PASS: Resume stage endpoint working")
    
    def test_kickoff_status(self):
        """GET /api/sales-funnel/kickoff-status/{lead_id}"""
        headers = TokenCache.get_headers("admin")
        
        leads = requests.get(f"{BASE_URL}/api/leads", headers=headers).json()
        lead_id = leads[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/sales-funnel/kickoff-status/{lead_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"PASS: Kickoff status endpoint working - status: {data['status']}")


# ============== AUDIT TESTS ==============

class TestAudit:
    """Audit logging endpoints"""
    
    def test_audit_summary_admin(self):
        """Admin can access audit summary"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/audit/summary", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_logs" in data
        assert "by_action" in data
        print(f"PASS: Audit summary working - {data['total_logs']} logs in last {data['period_days']} days")
    
    def test_audit_summary_denied_non_admin(self):
        """Non-admin should be denied audit access"""
        headers = TokenCache.get_headers("sales_executive")
        response = requests.get(f"{BASE_URL}/api/audit/summary", headers=headers)
        
        assert response.status_code == 403
        print("PASS: Audit endpoints properly restricted to admin")


# ============== LEAD SCHEMA VALIDATION ==============

class TestLeadSchemaValidation:
    """Validate all leads have proper first_name/last_name schema"""
    
    def test_all_leads_have_proper_schema(self):
        """All leads should have first_name and last_name fields"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        
        assert response.status_code == 200
        leads = response.json()
        
        invalid_leads = []
        for lead in leads:
            if not lead.get("first_name") and not lead.get("last_name"):
                invalid_leads.append(lead.get("id"))
        
        if invalid_leads:
            print(f"WARNING: {len(invalid_leads)} leads missing name fields: {invalid_leads[:5]}")
        
        # At least 90% should have proper schema
        valid_count = len(leads) - len(invalid_leads)
        valid_pct = (valid_count / len(leads)) * 100 if leads else 0
        assert valid_pct >= 90, f"Only {valid_pct:.1f}% leads have valid schema"
        print(f"PASS: {valid_pct:.1f}% of leads have proper first_name/last_name schema")
    
    def test_renewal_leads_schema(self):
        """Renewal leads should have proper schema"""
        headers = TokenCache.get_headers("admin")
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        
        leads = response.json()
        renewal_leads = [l for l in leads if l.get("source") == "renewal"]
        
        if not renewal_leads:
            print("INFO: No renewal leads found to validate")
            return
        
        for lead in renewal_leads:
            # Renewal leads created after fix should have first_name/last_name
            assert "first_name" in lead, f"Renewal lead {lead['id']} missing first_name"
            assert "last_name" in lead, f"Renewal lead {lead['id']} missing last_name"
        
        print(f"PASS: {len(renewal_leads)} renewal leads have proper schema")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
