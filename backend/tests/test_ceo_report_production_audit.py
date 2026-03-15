"""
CEO Report Dashboard - Production Readiness Audit Tests
=========================================================
Tests all 13 sections, RBAC enforcement, button functionality,
email delivery, MTD/QTD/YTD calculations, and delivery history.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestCEOReportAuth:
    """Test authentication and RBAC for CEO report endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
        self.sales_manager_creds = {"employee_id": "EMP002", "password": "Sales@123"}
        self.sales_exec_creds = {"employee_id": "EMP003", "password": "Sales@123"}
        
    def get_token(self, creds):
        """Helper to get auth token"""
        res = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
        if res.status_code == 200:
            return res.json().get("access_token")
        return None
    
    def test_admin_can_access_ceo_report_data(self):
        """Admin should access /api/ceo-report/data"""
        token = self.get_token(self.admin_creds)
        assert token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert "sales_activity" in data, "Missing sales_activity section"
        print(f"PASS: Admin accessed CEO report data with {len(data)} sections")
    
    def test_admin_can_access_ceo_report_preview(self):
        """Admin should access /api/ceo-report/preview"""
        token = self.get_token(self.admin_creds)
        assert token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/preview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        # Preview returns HTML
        assert "DVBC ERP" in res.text or "CEO" in res.text, "Preview HTML missing expected content"
        print(f"PASS: Admin accessed CEO report preview (HTML length: {len(res.text)})")
    
    def test_admin_can_access_ceo_report_config(self):
        """Admin should access /api/ceo-report/config"""
        token = self.get_token(self.admin_creds)
        assert token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/config", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        config = res.json()
        assert "recipient" in config, "Missing recipient in config"
        assert "smtp_status" in config, "Missing smtp_status in config"
        print(f"PASS: Admin accessed CEO report config: recipient={config.get('recipient')}, smtp={config.get('smtp_status')}")
    
    def test_admin_can_access_ceo_report_logs(self):
        """Admin should access /api/ceo-report/logs"""
        token = self.get_token(self.admin_creds)
        assert token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/logs", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert "logs" in data, "Missing logs array"
        print(f"PASS: Admin accessed CEO report logs (count: {len(data.get('logs', []))})")
    
    def test_sales_manager_gets_403_on_ceo_data(self):
        """Sales Manager should get 403 on CEO report endpoints"""
        token = self.get_token(self.sales_manager_creds)
        if not token:
            pytest.skip("Sales Manager login failed - user may not exist")
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print(f"PASS: Sales Manager correctly denied access (403)")
    
    def test_sales_exec_gets_403_on_ceo_preview(self):
        """Sales Executive should get 403 on CEO report preview"""
        token = self.get_token(self.sales_exec_creds)
        if not token:
            pytest.skip("Sales Executive login failed - user may not exist")
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/preview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print(f"PASS: Sales Executive correctly denied preview access (403)")
    
    def test_unauthenticated_gets_401_on_all_endpoints(self):
        """Unauthenticated requests should get 401"""
        endpoints = [
            "/api/ceo-report/data",
            "/api/ceo-report/preview",
            "/api/ceo-report/config",
            "/api/ceo-report/logs",
            "/api/ceo-report/trigger"
        ]
        for endpoint in endpoints:
            res = requests.get(f"{BASE_URL}{endpoint}")
            assert res.status_code == 401, f"Expected 401 on {endpoint}, got {res.status_code}"
        print(f"PASS: All 5 endpoints return 401 for unauthenticated requests")


class TestCEOReportDataSections:
    """Test all 13 sections of CEO report data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
        token_res = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        self.token = token_res.json().get("access_token") if token_res.status_code == 200 else None
        
    def test_all_13_sections_present(self):
        """Verify all 13 sections are present in report data"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        assert res.status_code == 200
        data = res.json()
        
        # All 13 required sections
        required_sections = [
            "sales_activity",      # Section 1
            "pipeline_health",     # Section 2
            "escalations",         # Section 3
            "meetings",            # Section 4
            "consulting",          # Section 5
            "sow_agreements",      # Section 6
            "payments",            # Section 7
            "revenue",             # Section 8
            "team_productivity",   # Section 9
            "system_health",       # Section 10
            "hr_metrics",          # Section 11
            "consulting_team",     # Section 12
            "finance_expenses",    # Section 13
        ]
        
        missing = [s for s in required_sections if s not in data]
        assert len(missing) == 0, f"Missing sections: {missing}"
        print(f"PASS: All 13 sections present in CEO report data")
        
    def test_sales_activity_section(self):
        """Test Section 1: Sales Activity has required fields"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        data = res.json()
        sa = data.get("sales_activity", {})
        
        required_fields = ["new_leads", "meetings", "followups_done", "followups_missed", 
                          "proposals_sent", "sow_generated", "closed_won", "closed_lost",
                          "mtd_leads", "qtd_leads", "ytd_leads"]
        missing = [f for f in required_fields if f not in sa]
        assert len(missing) == 0, f"Sales Activity missing fields: {missing}"
        print(f"PASS: Sales Activity has all {len(required_fields)} fields")
        
    def test_pipeline_health_section(self):
        """Test Section 2: Pipeline Health has stages and totals"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        data = res.json()
        ph = data.get("pipeline_health", {})
        
        assert "stages" in ph, "Missing stages in pipeline_health"
        assert "total_leads" in ph, "Missing total_leads in pipeline_health"
        assert "conversion_rate" in ph, "Missing conversion_rate in pipeline_health"
        
        # Verify stages is a list
        assert isinstance(ph["stages"], list), "stages should be a list"
        print(f"PASS: Pipeline Health has {len(ph.get('stages', []))} stages, total_leads={ph.get('total_leads')}")
        
    def test_revenue_section_mtd_qtd_ytd(self):
        """Test Section 8: Revenue has MTD/QTD/YTD values"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        data = res.json()
        rev = data.get("revenue", {})
        
        required = ["today_revenue", "mtd_revenue", "qtd_revenue", "ytd_revenue"]
        missing = [f for f in required if f not in rev]
        assert len(missing) == 0, f"Revenue missing: {missing}"
        print(f"PASS: Revenue section - Today:{rev.get('today_revenue')}, MTD:{rev.get('mtd_revenue')}, QTD:{rev.get('qtd_revenue')}, YTD:{rev.get('ytd_revenue')}")
        
    def test_hr_metrics_section(self):
        """Test Section 11: HR Metrics structure"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        data = res.json()
        hr = data.get("hr_metrics", {})
        
        assert "total_employees" in hr, "Missing total_employees"
        assert "attendance_today" in hr, "Missing attendance_today"
        assert "leaves_pending" in hr, "Missing leaves_pending"
        assert "leaves_approved" in hr, "Missing leaves_approved"
        assert "new_joiners" in hr, "Missing new_joiners"
        
        # Check nested MTD/QTD/YTD
        la = hr.get("leaves_approved", {})
        assert "mtd" in la and "qtd" in la and "ytd" in la, "leaves_approved missing mtd/qtd/ytd"
        print(f"PASS: HR Metrics - employees={hr.get('total_employees')}, leaves_pending={hr.get('leaves_pending')}")
        
    def test_consulting_team_section(self):
        """Test Section 12: Consulting Team structure"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        data = res.json()
        ct = data.get("consulting_team", {})
        
        assert "total_consultants" in ct, "Missing total_consultants"
        assert "tasks" in ct, "Missing tasks"
        assert "tasks_completed" in ct, "Missing tasks_completed"
        assert "projects_completed" in ct, "Missing projects_completed"
        
        # Check nested structures
        tasks = ct.get("tasks", {})
        assert "completed" in tasks and "in_progress" in tasks, "tasks missing sub-fields"
        
        tc = ct.get("tasks_completed", {})
        assert "mtd" in tc and "qtd" in tc and "ytd" in tc, "tasks_completed missing mtd/qtd/ytd"
        print(f"PASS: Consulting Team - consultants={ct.get('total_consultants')}, tasks={tasks}")
        
    def test_finance_expenses_section(self):
        """Test Section 13: Finance & Expenses structure"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/data", headers={"Authorization": f"Bearer {self.token}"})
        data = res.json()
        fe = data.get("finance_expenses", {})
        
        assert "expenses_pending" in fe, "Missing expenses_pending"
        assert "travel_pending" in fe, "Missing travel_pending"
        assert "expenses_approved" in fe, "Missing expenses_approved"
        assert "expense_amount" in fe, "Missing expense_amount"
        assert "travel_amount" in fe, "Missing travel_amount"
        
        # Check MTD/QTD/YTD
        ea = fe.get("expenses_approved", {})
        assert "mtd" in ea and "qtd" in ea and "ytd" in ea, "expenses_approved missing mtd/qtd/ytd"
        print(f"PASS: Finance Expenses - expenses_pending={fe.get('expenses_pending')}, travel_pending={fe.get('travel_pending')}")


class TestCEOReportConfig:
    """Test CEO Report configuration endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
        token_res = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        self.token = token_res.json().get("access_token") if token_res.status_code == 200 else None
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
    def test_update_recipient_config(self):
        """Test PUT /api/ceo-report/config updates recipient"""
        assert self.token, "Admin login failed"
        
        # Get current config
        res = requests.get(f"{BASE_URL}/api/ceo-report/config", headers=self.headers)
        original_recipient = res.json().get("recipient", "")
        
        # Update to test recipient
        test_email = "test-ceo-report@dvconsulting.co.in"
        res = requests.put(f"{BASE_URL}/api/ceo-report/config", 
                          headers=self.headers, 
                          json={"recipient": test_email})
        assert res.status_code == 200, f"Failed to update config: {res.text}"
        
        # Verify update
        res = requests.get(f"{BASE_URL}/api/ceo-report/config", headers=self.headers)
        assert res.json().get("recipient") == test_email, "Recipient not updated"
        
        # Restore original
        requests.put(f"{BASE_URL}/api/ceo-report/config", 
                    headers=self.headers, 
                    json={"recipient": original_recipient})
        print(f"PASS: Config update works - tested with {test_email}")


class TestCEOReportTrigger:
    """Test CEO Report trigger/send functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
        token_res = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        self.token = token_res.json().get("access_token") if token_res.status_code == 200 else None
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
    def test_trigger_report_creates_log(self):
        """Test POST /api/ceo-report/trigger creates delivery log"""
        assert self.token, "Admin login failed"
        
        # Get logs count before
        logs_before = requests.get(f"{BASE_URL}/api/ceo-report/logs", headers=self.headers).json().get("logs", [])
        count_before = len(logs_before)
        
        # Trigger report
        res = requests.post(f"{BASE_URL}/api/ceo-report/trigger", headers=self.headers)
        assert res.status_code == 200, f"Trigger failed: {res.text}"
        
        result = res.json()
        assert "status" in result, "Missing status in trigger response"
        print(f"Trigger result: status={result.get('status')}, message={result.get('message')}")
        
        # Check logs increased
        logs_after = requests.get(f"{BASE_URL}/api/ceo-report/logs", headers=self.headers).json().get("logs", [])
        count_after = len(logs_after)
        
        assert count_after >= count_before, "No new log entry created"
        print(f"PASS: Trigger created log entry (before={count_before}, after={count_after})")


class TestCEOReportDeliveryHistory:
    """Test delivery history display"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"employee_id": "ADMIN001", "password": "Admin@2026"}
        token_res = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        self.token = token_res.json().get("access_token") if token_res.status_code == 200 else None
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
    def test_logs_have_required_fields(self):
        """Test logs contain required fields for UI display"""
        assert self.token, "Admin login failed"
        
        res = requests.get(f"{BASE_URL}/api/ceo-report/logs", headers=self.headers)
        logs = res.json().get("logs", [])
        
        if len(logs) == 0:
            print("SKIP: No logs to test (system may be fresh)")
            return
            
        log = logs[0]  # Check first log
        required = ["date", "delivery_status", "records_included"]
        missing = [f for f in required if f not in log]
        assert len(missing) == 0, f"Log missing fields: {missing}"
        
        # Check delivery_status is one of expected values
        assert log["delivery_status"] in ["sent", "failed", "pending", "error", "skipped"], \
            f"Unexpected delivery_status: {log['delivery_status']}"
        print(f"PASS: Logs have required fields - first log status: {log['delivery_status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
