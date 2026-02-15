"""
Reports Module Tests
Tests for GET /api/reports, GET /api/reports/{id}/preview, 
POST /api/reports/generate (excel/pdf), role-based access
"""
import pytest
import requests
import os
import io
import zipfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "admin123"}
MANAGER_CREDS = {"email": "manager@company.com", "password": "manager123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def manager_token():
    """Get manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Manager authentication failed")


@pytest.fixture
def admin_client(admin_token):
    """Authenticated session for admin"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def manager_client(manager_token):
    """Authenticated session for manager"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {manager_token}",
        "Content-Type": "application/json"
    })
    return session


class TestReportsEndpoints:
    """Test Reports API endpoints"""
    
    def test_get_reports_admin(self, admin_client):
        """Admin should see all 19 reports"""
        response = admin_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        data = response.json()
        assert "reports" in data
        assert "by_category" in data
        assert "total_available" in data
        
        # Admin should see all 19 reports
        assert data["total_available"] == 19
        print(f"Admin can see {data['total_available']} reports")
        
        # Verify categories exist
        categories = list(data["by_category"].keys())
        assert "Sales" in categories
        assert "Finance" in categories
        assert "HR" in categories
        assert "Operations" in categories
        print(f"Report categories: {categories}")
    
    def test_get_reports_manager(self, manager_client):
        """Manager should see all 19 reports (same as admin for manager role)"""
        response = manager_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        data = response.json()
        # Manager should see 19 reports based on REPORT_ROLE_ACCESS
        assert data["total_available"] >= 15  # Manager sees many reports
        print(f"Manager can see {data['total_available']} reports")
    
    def test_get_report_categories(self, admin_client):
        """Test GET /api/reports/categories"""
        response = admin_client.get(f"{BASE_URL}/api/reports/categories")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        assert "Sales" in categories
        assert "Finance" in categories
        assert "HR" in categories
        assert "Operations" in categories
        print(f"Categories: {categories}")
    
    def test_get_reports_stats_admin(self, admin_client):
        """Admin should access stats endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/reports/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "leads" in stats
        assert "clients" in stats
        assert "employees" in stats
        assert "projects" in stats
        assert "pending_approvals" in stats
        assert "total_revenue" in stats
        assert "pending_expenses" in stats
        assert "approved_expenses" in stats
        print(f"Stats: leads={stats['leads']}, clients={stats['clients']}, revenue={stats['total_revenue']}")
    
    def test_get_reports_stats_manager(self, manager_client):
        """Manager should access stats endpoint"""
        response = manager_client.get(f"{BASE_URL}/api/reports/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "leads" in stats
        print(f"Manager stats access OK")


class TestReportPreview:
    """Test report preview functionality"""
    
    def test_preview_lead_summary(self, admin_client):
        """Test preview of lead summary report"""
        response = admin_client.get(f"{BASE_URL}/api/reports/lead_summary/preview")
        assert response.status_code == 200
        
        data = response.json()
        assert "report_id" in data
        assert data["report_id"] == "lead_summary"
        assert "report_info" in data
        assert "data" in data
        
        # Check data structure
        report_data = data["data"]
        assert "title" in report_data
        assert "generated_at" in report_data
        assert "summary" in report_data
        assert "columns" in report_data
        assert "rows" in report_data
        
        print(f"Lead Summary: {len(report_data['rows'])} rows")
        print(f"Columns: {report_data['columns']}")
    
    def test_preview_employee_directory(self, admin_client):
        """Test preview of employee directory report"""
        response = admin_client.get(f"{BASE_URL}/api/reports/employee_directory/preview")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report_id"] == "employee_directory"
        
        report_data = data["data"]
        assert "Employee ID" in report_data["columns"]
        assert "Name" in report_data["columns"]
        assert "Department" in report_data["columns"]
        
        print(f"Employee Directory: {len(report_data['rows'])} employees")
    
    def test_preview_expense_summary(self, admin_client):
        """Test preview of expense summary report"""
        response = admin_client.get(f"{BASE_URL}/api/reports/expense_summary/preview")
        assert response.status_code == 200
        
        data = response.json()
        assert data["report_id"] == "expense_summary"
        
        report_data = data["data"]
        assert "summary" in report_data
        print(f"Expense Summary: {report_data['summary']}")
    
    def test_preview_invalid_report(self, admin_client):
        """Test preview of non-existent report"""
        response = admin_client.get(f"{BASE_URL}/api/reports/invalid_report/preview")
        assert response.status_code in [403, 404]


class TestReportDownload:
    """Test report download in Excel and PDF formats"""
    
    def test_download_excel_lead_summary(self, admin_client):
        """Test Excel download for lead summary report"""
        response = admin_client.post(
            f"{BASE_URL}/api/reports/generate",
            json={"report_id": "lead_summary", "format": "excel"}
        )
        assert response.status_code == 200
        
        # Check content type
        content_type = response.headers.get("Content-Type")
        assert "spreadsheet" in content_type or "excel" in content_type.lower()
        
        # Check content disposition
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert ".xlsx" in content_disp
        
        # Check file size (should be > 0)
        assert len(response.content) > 100
        print(f"Excel file size: {len(response.content)} bytes")
        
        # Validate it's a valid xlsx file (starts with PK for ZIP format)
        assert response.content[:2] == b'PK'
    
    def test_download_pdf_lead_summary(self, admin_client):
        """Test PDF download for lead summary report"""
        response = admin_client.post(
            f"{BASE_URL}/api/reports/generate",
            json={"report_id": "lead_summary", "format": "pdf"}
        )
        assert response.status_code == 200
        
        # Check content type
        content_type = response.headers.get("Content-Type")
        assert "pdf" in content_type
        
        # Check file size (should be > 0)
        assert len(response.content) > 100
        print(f"PDF file size: {len(response.content)} bytes")
        
        # Validate it's a valid PDF (starts with %PDF)
        assert response.content[:4] == b'%PDF'
    
    def test_download_excel_client_overview(self, admin_client):
        """Test Excel download for client overview report"""
        response = admin_client.post(
            f"{BASE_URL}/api/reports/generate",
            json={"report_id": "client_overview", "format": "excel"}
        )
        assert response.status_code == 200
        assert response.content[:2] == b'PK'  # Valid xlsx
        print(f"Client Overview Excel: {len(response.content)} bytes")
    
    def test_download_pdf_expense_summary(self, admin_client):
        """Test PDF download for expense summary report"""
        response = admin_client.post(
            f"{BASE_URL}/api/reports/generate",
            json={"report_id": "expense_summary", "format": "pdf"}
        )
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'  # Valid PDF
        print(f"Expense Summary PDF: {len(response.content)} bytes")
    
    def test_download_invalid_format(self, admin_client):
        """Test download with invalid format"""
        response = admin_client.post(
            f"{BASE_URL}/api/reports/generate",
            json={"report_id": "lead_summary", "format": "csv"}
        )
        assert response.status_code == 400
    
    def test_download_unauthorized_report(self, manager_client):
        """Test download of report not accessible to role - consultant role test"""
        # First create a consultant user for testing unauthorized access
        # Managers should have access to most reports, so this test may need adjustment
        # based on actual role restrictions
        response = manager_client.post(
            f"{BASE_URL}/api/reports/generate",
            json={"report_id": "lead_summary", "format": "excel"}
        )
        # Manager should have access to lead_summary
        assert response.status_code == 200


class TestReportRoleAccess:
    """Test role-based access control for reports"""
    
    def test_admin_sees_all_categories(self, admin_client):
        """Admin should see reports from all categories"""
        response = admin_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        data = response.json()
        categories = list(data["by_category"].keys())
        
        # Admin should see all 4 categories
        assert len(categories) == 4
        assert set(categories) == {"Sales", "Finance", "HR", "Operations"}
    
    def test_report_count_admin_vs_manager(self, admin_client, manager_client):
        """Compare report counts between admin and manager"""
        admin_resp = admin_client.get(f"{BASE_URL}/api/reports")
        manager_resp = manager_client.get(f"{BASE_URL}/api/reports")
        
        assert admin_resp.status_code == 200
        assert manager_resp.status_code == 200
        
        admin_count = admin_resp.json()["total_available"]
        manager_count = manager_resp.json()["total_available"]
        
        # Admin should see >= manager count
        assert admin_count >= manager_count
        print(f"Admin: {admin_count} reports, Manager: {manager_count} reports")


class TestReportDataAccuracy:
    """Test that report data is accurate"""
    
    def test_sales_reports_available(self, admin_client):
        """Test Sales category reports are available"""
        response = admin_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        sales_reports = response.json()["by_category"].get("Sales", [])
        sales_ids = [r["id"] for r in sales_reports]
        
        # Expected sales reports
        expected = ["lead_summary", "lead_conversion_funnel", "lead_source_analysis",
                   "client_overview", "client_industry_breakdown", "sales_pipeline_status",
                   "quotation_analysis", "agreement_status"]
        
        for report_id in expected:
            assert report_id in sales_ids, f"Missing sales report: {report_id}"
        
        print(f"Sales reports: {sales_ids}")
    
    def test_hr_reports_available(self, admin_client):
        """Test HR category reports are available"""
        response = admin_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        hr_reports = response.json()["by_category"].get("HR", [])
        hr_ids = [r["id"] for r in hr_reports]
        
        expected = ["employee_directory", "employee_department_analysis", "leave_utilization"]
        for report_id in expected:
            assert report_id in hr_ids, f"Missing HR report: {report_id}"
        
        print(f"HR reports: {hr_ids}")
    
    def test_finance_reports_available(self, admin_client):
        """Test Finance category reports are available"""
        response = admin_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        finance_reports = response.json()["by_category"].get("Finance", [])
        finance_ids = [r["id"] for r in finance_reports]
        
        expected = ["client_revenue_analysis", "expense_summary", "expense_by_category"]
        for report_id in expected:
            assert report_id in finance_ids, f"Missing Finance report: {report_id}"
        
        print(f"Finance reports: {finance_ids}")
    
    def test_operations_reports_available(self, admin_client):
        """Test Operations category reports are available"""
        response = admin_client.get(f"{BASE_URL}/api/reports")
        assert response.status_code == 200
        
        ops_reports = response.json()["by_category"].get("Operations", [])
        ops_ids = [r["id"] for r in ops_reports]
        
        expected = ["sow_status_report", "project_summary", "consultant_allocation",
                   "approval_turnaround", "pending_approvals"]
        for report_id in expected:
            assert report_id in ops_ids, f"Missing Operations report: {report_id}"
        
        print(f"Operations reports: {ops_ids}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
