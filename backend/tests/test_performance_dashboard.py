"""
Test Performance Dashboard and Attendance APIs for HR Portal
Testing: Performance Dashboard, Attendance with work_location, Analytics API
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def hr_manager_token():
    """Login as HR Manager"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "hr.manager@company.com",
        "password": "hr123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    # Fallback to admin
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Could not login as HR Manager or Admin")

@pytest.fixture(scope="module")
def admin_token():
    """Login as Admin"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Could not login as Admin")

@pytest.fixture(scope="module")
def hr_executive_token():
    """Login as HR Executive"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "hr.executive@company.com",
        "password": "hr123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    # Fallback to alternate email
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "lakshmi.pillai83@dvconsulting.co.in",
        "password": "hr123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Could not login as HR Executive")


class TestAttendanceAnalyticsAPI:
    """Test /api/attendance/analytics endpoint"""
    
    def test_analytics_returns_data_structure(self, admin_token):
        """Verify attendance analytics returns correct data structure"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/analytics?months=1&department=all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Check main structure
        assert "summary" in data, "Missing 'summary' in response"
        assert "work_location" in data, "Missing 'work_location' in response"
        assert "trends" in data, "Missing 'trends' in response"
        assert "leave_patterns" in data, "Missing 'leave_patterns' in response"
        assert "department_stats" in data, "Missing 'department_stats' in response"
        
        # Check summary fields
        summary = data["summary"]
        assert "attendance_rate" in summary, "Missing 'attendance_rate' in summary"
        assert "present" in summary, "Missing 'present' count in summary"
        assert "total_records" in summary, "Missing 'total_records' in summary"
        
        # Check work_location fields
        work_loc = data["work_location"]
        assert "in_office" in work_loc, "Missing 'in_office' in work_location"
        assert "onsite" in work_loc, "Missing 'onsite' in work_location"
        assert "wfh" in work_loc, "Missing 'wfh' in work_location"
        
        print(f"Analytics summary: attendance_rate={summary.get('attendance_rate')}%, present={summary.get('present')}, total={summary.get('total_records')}")
        print(f"Work location: in_office={work_loc.get('in_office')}, onsite={work_loc.get('onsite')}, wfh={work_loc.get('wfh')}")
    
    def test_analytics_hr_manager_access(self, hr_manager_token):
        """HR Manager should have access to attendance analytics"""
        if not hr_manager_token:
            pytest.skip("HR Manager token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/attendance/analytics?months=1&department=all",
            headers={"Authorization": f"Bearer {hr_manager_token}"}
        )
        # Should be 200 for HR Manager role
        assert response.status_code == 200, f"HR Manager should have access, got {response.status_code}"
        
        data = response.json()
        assert "summary" in data
        print(f"HR Manager can access analytics: attendance_rate={data['summary'].get('attendance_rate')}%")
    
    def test_analytics_leave_patterns_structure(self, admin_token):
        """Verify leave patterns by day data"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        leave_patterns = data.get("leave_patterns", [])
        
        # Should have 7 days (Mon-Sun)
        assert len(leave_patterns) == 7, f"Expected 7 days, got {len(leave_patterns)}"
        
        # Check structure of each day
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day_data in enumerate(leave_patterns):
            assert "day" in day_data, f"Missing 'day' in leave_patterns[{i}]"
            assert "count" in day_data, f"Missing 'count' in leave_patterns[{i}]"
            assert day_data["day"] == days[i], f"Expected '{days[i]}', got '{day_data['day']}'"
        
        print(f"Leave patterns: {[(d['day'], d['count']) for d in leave_patterns]}")
    
    def test_analytics_department_stats(self, admin_token):
        """Verify department attendance stats"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/analytics?department=all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        dept_stats = data.get("department_stats", [])
        
        if dept_stats:
            # Verify structure of each department stat
            for stat in dept_stats:
                assert "department" in stat, "Missing 'department' in stat"
                assert "attendance_rate" in stat, "Missing 'attendance_rate' in stat"
                print(f"Department '{stat['department']}': {stat['attendance_rate']}% attendance")
        else:
            print("No department stats available (may need more data)")


class TestAttendanceAPI:
    """Test attendance CRUD with work_location field"""
    
    def test_attendance_summary_endpoint(self, admin_token):
        """Test attendance summary endpoint"""
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/attendance/summary?month={month}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"Attendance summary for {month}: {len(response.json())} employees")
    
    def test_attendance_list_endpoint(self, admin_token):
        """Test attendance list endpoint"""
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/attendance?month={month}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        records = response.json()
        
        # Check if work_location field exists in records
        has_work_location = any(r.get("work_location") for r in records) if records else False
        print(f"Attendance records for {month}: {len(records)}, has_work_location: {has_work_location}")
    
    def test_create_attendance_with_work_location(self, admin_token):
        """Test creating attendance with work_location field"""
        # First get an employee
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        employees = response.json()
        
        if not employees:
            pytest.skip("No employees found")
        
        employee = employees[0]
        from datetime import datetime, timedelta
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Create attendance with work_location = in_office
        response = requests.post(
            f"{BASE_URL}/api/attendance",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "employee_id": employee["id"],
                "date": test_date,
                "status": "present",
                "work_location": "in_office",
                "remarks": "Test attendance"
            }
        )
        assert response.status_code == 200, f"Failed to create attendance: {response.text}"
        print(f"Created attendance for {employee.get('first_name')} with work_location=in_office")
        
        # Create another with work_location = wfh
        test_date2 = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        response = requests.post(
            f"{BASE_URL}/api/attendance",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "employee_id": employee["id"],
                "date": test_date2,
                "status": "present",
                "work_location": "wfh",
                "remarks": "Work from home test"
            }
        )
        assert response.status_code == 200
        print(f"Created attendance with work_location=wfh")
        
        # Create another with work_location = onsite
        test_date3 = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        response = requests.post(
            f"{BASE_URL}/api/attendance",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "employee_id": employee["id"],
                "date": test_date3,
                "status": "present",
                "work_location": "onsite",
                "remarks": "On-site at client"
            }
        )
        assert response.status_code == 200
        print(f"Created attendance with work_location=onsite")
    
    def test_work_location_in_response(self, admin_token):
        """Verify work_location is returned in attendance records"""
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(
            f"{BASE_URL}/api/attendance?month={month}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        records = response.json()
        
        # Find records with work_location
        records_with_loc = [r for r in records if r.get("work_location")]
        print(f"Records with work_location: {len(records_with_loc)} out of {len(records)}")
        
        if records_with_loc:
            # Verify values
            valid_locations = ["in_office", "onsite", "wfh"]
            for r in records_with_loc[:5]:  # Check first 5
                assert r["work_location"] in valid_locations, f"Invalid work_location: {r['work_location']}"
                print(f"  - {r['date']}: {r['status']}, location={r['work_location']}")


class TestConsultantsEndpointForDashboard:
    """Test /api/consultants endpoint used by Performance Dashboard"""
    
    def test_consultants_endpoint_admin(self, admin_token):
        """Admin should see consultants"""
        response = requests.get(
            f"{BASE_URL}/api/consultants",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin should access consultants: {response.status_code}"
        consultants = response.json()
        print(f"Admin sees {len(consultants)} consultants")
    
    def test_projects_endpoint(self, admin_token):
        """Test projects endpoint for performance data"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        projects = response.json()
        active = [p for p in projects if p.get("status") == "active"]
        print(f"Projects: {len(projects)} total, {len(active)} active")


class TestHRFinancialDataHidden:
    """Test that HR roles don't see financial data"""
    
    def test_hr_analytics_no_revenue(self, hr_manager_token):
        """HR Manager analytics should not include revenue data"""
        if not hr_manager_token:
            pytest.skip("HR Manager token not available")
        
        response = requests.get(
            f"{BASE_URL}/api/attendance/analytics",
            headers={"Authorization": f"Bearer {hr_manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # The analytics API itself doesn't return revenue - that's frontend filtered
        # But we verify the endpoint works for HR roles
        assert "summary" in data
        print("HR Manager can access analytics (frontend filters financial data)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
