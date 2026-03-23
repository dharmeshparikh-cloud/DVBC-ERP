"""
Test Attendance Policy Configuration APIs
Tests for:
- GET /api/business-rules/attendance/config - Get attendance configuration
- PUT /api/business-rules/attendance/config - Update attendance configuration
- GET /api/business-rules/attendance/overrides - Get all overrides
- POST /api/business-rules/attendance/override - Create override
- DELETE /api/business-rules/attendance/override/{policy_id} - Delete override
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAttendanceConfigAPIs:
    """Test Attendance Policy Configuration APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as HR user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "hr123"
        })
        assert login_response.status_code == 200, f"HR login failed: {login_response.text}"
        self.hr_token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.hr_token}"})
        
        yield
        
        self.session.close()
    
    def test_01_get_attendance_config(self):
        """Test GET /api/business-rules/attendance/config - Get attendance configuration"""
        response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        
        assert response.status_code == 200, f"Failed to get attendance config: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "policy_id" in data, "Missing policy_id"
        assert "working_days" in data, "Missing working_days"
        assert "core_hours_start" in data, "Missing core_hours_start"
        assert "core_hours_end" in data, "Missing core_hours_end"
        assert "grace_period_minutes" in data, "Missing grace_period_minutes"
        assert "wfh_days_per_week" in data, "Missing wfh_days_per_week"
        assert "grace_days_per_month" in data, "Missing grace_days_per_month"
        assert "late_penalty_amount" in data, "Missing late_penalty_amount"
        assert "all_weekdays" in data, "Missing all_weekdays"
        
        # Verify data types
        assert isinstance(data["working_days"], list), "working_days should be a list"
        assert isinstance(data["core_hours_start"], str), "core_hours_start should be a string"
        assert isinstance(data["core_hours_end"], str), "core_hours_end should be a string"
        assert isinstance(data["grace_period_minutes"], (int, float)), "grace_period_minutes should be numeric"
        assert isinstance(data["wfh_days_per_week"], (int, float)), "wfh_days_per_week should be numeric"
        
        # Verify default values are reasonable
        assert len(data["all_weekdays"]) == 7, "Should have 7 weekdays"
        assert "Monday" in data["all_weekdays"], "Should include Monday"
        assert "Sunday" in data["all_weekdays"], "Should include Sunday"
        
        print(f"✓ Attendance config retrieved successfully")
        print(f"  Working days: {data['working_days']}")
        print(f"  Core hours: {data['core_hours_start']} - {data['core_hours_end']}")
        print(f"  Grace period: {data['grace_period_minutes']} mins")
        print(f"  WFH days/week: {data['wfh_days_per_week']}")
        print(f"  Grace days/month: {data['grace_days_per_month']}")
        print(f"  Late penalty: ₹{data['late_penalty_amount']}/day")
    
    def test_02_update_attendance_config_working_days(self):
        """Test PUT /api/business-rules/attendance/config - Update working days"""
        # First get current config
        get_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        assert get_response.status_code == 200
        original_config = get_response.json()
        
        # Update working days to Mon-Fri only
        update_payload = {
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/business-rules/attendance/config",
            json=update_payload
        )
        
        assert response.status_code == 200, f"Failed to update working days: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        
        # Verify the change persisted
        verify_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        assert verify_response.status_code == 200
        updated_config = verify_response.json()
        
        assert len(updated_config["working_days"]) == 5, "Should have 5 working days"
        assert "Saturday" not in updated_config["working_days"], "Saturday should be removed"
        
        print(f"✓ Working days updated successfully to Mon-Fri")
        
        # Restore original working days
        restore_payload = {
            "working_days": original_config["working_days"]
        }
        self.session.put(f"{BASE_URL}/api/business-rules/attendance/config", json=restore_payload)
        print(f"✓ Restored original working days: {original_config['working_days']}")
    
    def test_03_update_attendance_config_core_hours(self):
        """Test PUT /api/business-rules/attendance/config - Update core hours"""
        # Get current config
        get_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        assert get_response.status_code == 200
        original_config = get_response.json()
        
        # Update core hours
        update_payload = {
            "core_hours_start": "09:30",
            "core_hours_end": "18:30"
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/business-rules/attendance/config",
            json=update_payload
        )
        
        assert response.status_code == 200, f"Failed to update core hours: {response.text}"
        
        # Verify the change
        verify_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        updated_config = verify_response.json()
        
        assert updated_config["core_hours_start"] == "09:30", "Core hours start should be 09:30"
        assert updated_config["core_hours_end"] == "18:30", "Core hours end should be 18:30"
        
        print(f"✓ Core hours updated to 09:30 - 18:30")
        
        # Restore original
        restore_payload = {
            "core_hours_start": original_config["core_hours_start"],
            "core_hours_end": original_config["core_hours_end"]
        }
        self.session.put(f"{BASE_URL}/api/business-rules/attendance/config", json=restore_payload)
        print(f"✓ Restored original core hours: {original_config['core_hours_start']} - {original_config['core_hours_end']}")
    
    def test_04_update_attendance_config_numeric_fields(self):
        """Test PUT /api/business-rules/attendance/config - Update numeric fields"""
        # Get current config
        get_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        assert get_response.status_code == 200
        original_config = get_response.json()
        
        # Update numeric fields
        update_payload = {
            "grace_period_minutes": 45,
            "wfh_days_per_week": 3,
            "grace_days_per_month": 5,
            "late_penalty_amount": 150
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/business-rules/attendance/config",
            json=update_payload
        )
        
        assert response.status_code == 200, f"Failed to update numeric fields: {response.text}"
        
        # Verify changes
        verify_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/config")
        updated_config = verify_response.json()
        
        assert updated_config["grace_period_minutes"] == 45, "Grace period should be 45"
        assert updated_config["wfh_days_per_week"] == 3, "WFH days should be 3"
        assert updated_config["grace_days_per_month"] == 5, "Grace days should be 5"
        assert updated_config["late_penalty_amount"] == 150, "Late penalty should be 150"
        
        print(f"✓ Numeric fields updated successfully")
        print(f"  Grace period: 45 mins")
        print(f"  WFH days: 3/week")
        print(f"  Grace days: 5/month")
        print(f"  Late penalty: ₹150/day")
        
        # Restore original
        restore_payload = {
            "grace_period_minutes": original_config["grace_period_minutes"],
            "wfh_days_per_week": original_config["wfh_days_per_week"],
            "grace_days_per_month": original_config["grace_days_per_month"],
            "late_penalty_amount": original_config["late_penalty_amount"]
        }
        self.session.put(f"{BASE_URL}/api/business-rules/attendance/config", json=restore_payload)
        print(f"✓ Restored original numeric values")
    
    def test_05_get_attendance_overrides(self):
        """Test GET /api/business-rules/attendance/overrides - Get all overrides"""
        response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/overrides")
        
        assert response.status_code == 200, f"Failed to get overrides: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "role_overrides" in data, "Missing role_overrides"
        assert "employee_overrides" in data, "Missing employee_overrides"
        assert "total_role_overrides" in data, "Missing total_role_overrides"
        assert "total_employee_overrides" in data, "Missing total_employee_overrides"
        
        assert isinstance(data["role_overrides"], list), "role_overrides should be a list"
        assert isinstance(data["employee_overrides"], list), "employee_overrides should be a list"
        
        print(f"✓ Attendance overrides retrieved successfully")
        print(f"  Role overrides: {data['total_role_overrides']}")
        print(f"  Employee overrides: {data['total_employee_overrides']}")
        
        # Print existing overrides
        for override in data["role_overrides"]:
            print(f"  - Role: {override.get('scope_value')}")
        for override in data["employee_overrides"]:
            print(f"  - Employee: {override.get('employee_name', override.get('scope_value'))}")
    
    def test_06_create_role_override(self):
        """Test POST /api/business-rules/attendance/override - Create role override"""
        # Create a test role override
        test_role = f"test_role_{uuid.uuid4().hex[:6]}"
        
        override_payload = {
            "scope": "role",
            "scope_value": test_role,
            "name": f"Test Override for {test_role}",
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "core_hours_start": "09:00",
            "core_hours_end": "18:00",
            "grace_period_minutes": 20,
            "wfh_days_per_week": 3,
            "reason": "Test override for automated testing"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/business-rules/attendance/override",
            json=override_payload
        )
        
        assert response.status_code == 200, f"Failed to create role override: {response.text}"
        
        data = response.json()
        assert "policy_id" in data, "Response should have policy_id"
        assert "message" in data, "Response should have message"
        
        policy_id = data["policy_id"]
        print(f"✓ Role override created successfully")
        print(f"  Policy ID: {policy_id}")
        print(f"  Role: {test_role}")
        
        # Verify it appears in overrides list
        verify_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/overrides")
        overrides = verify_response.json()
        
        found = any(o.get("id") == policy_id for o in overrides.get("role_overrides", []))
        assert found, "Created override should appear in role_overrides list"
        print(f"✓ Override verified in overrides list")
        
        # Clean up - delete the test override
        delete_response = self.session.delete(f"{BASE_URL}/api/business-rules/attendance/override/{policy_id}")
        assert delete_response.status_code == 200, f"Failed to delete test override: {delete_response.text}"
        print(f"✓ Test override cleaned up")
    
    def test_07_create_duplicate_override_fails(self):
        """Test that creating duplicate override for same role fails"""
        # First check if consultant override exists
        overrides_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/overrides")
        overrides = overrides_response.json()
        
        existing_roles = [o.get("scope_value") for o in overrides.get("role_overrides", [])]
        
        if "consultant" in existing_roles:
            # Try to create duplicate
            override_payload = {
                "scope": "role",
                "scope_value": "consultant",
                "name": "Duplicate Consultant Override",
                "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "core_hours_start": "10:00",
                "core_hours_end": "19:00",
                "reason": "Test duplicate"
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/business-rules/attendance/override",
                json=override_payload
            )
            
            # Should fail with 400
            assert response.status_code == 400, f"Duplicate override should fail: {response.text}"
            print(f"✓ Duplicate override correctly rejected")
        else:
            print(f"⚠ Skipping duplicate test - no existing consultant override")
    
    def test_08_delete_override(self):
        """Test DELETE /api/business-rules/attendance/override/{policy_id}"""
        # First create an override to delete
        test_role = f"delete_test_{uuid.uuid4().hex[:6]}"
        
        create_payload = {
            "scope": "role",
            "scope_value": test_role,
            "name": f"Override to delete",
            "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "core_hours_start": "10:00",
            "core_hours_end": "19:00",
            "reason": "Test deletion"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/business-rules/attendance/override",
            json=create_payload
        )
        assert create_response.status_code == 200
        policy_id = create_response.json()["policy_id"]
        print(f"✓ Created test override: {policy_id}")
        
        # Delete it
        delete_response = self.session.delete(f"{BASE_URL}/api/business-rules/attendance/override/{policy_id}")
        
        assert delete_response.status_code == 200, f"Failed to delete override: {delete_response.text}"
        
        data = delete_response.json()
        assert "message" in data, "Response should have message"
        
        print(f"✓ Override deleted successfully")
        
        # Verify it's gone
        verify_response = self.session.get(f"{BASE_URL}/api/business-rules/attendance/overrides")
        overrides = verify_response.json()
        
        found = any(o.get("id") == policy_id for o in overrides.get("role_overrides", []))
        assert not found, "Deleted override should not appear in list"
        print(f"✓ Verified override is removed from list")
    
    def test_09_invalid_scope_fails(self):
        """Test that invalid scope type fails"""
        override_payload = {
            "scope": "invalid_scope",
            "scope_value": "test",
            "name": "Invalid Override",
            "working_days": ["Monday"],
            "core_hours_start": "10:00",
            "core_hours_end": "19:00"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/business-rules/attendance/override",
            json=override_payload
        )
        
        assert response.status_code == 400, f"Invalid scope should fail: {response.text}"
        print(f"✓ Invalid scope correctly rejected")
    
    def test_10_employee_cannot_update_config(self):
        """Test that regular employee cannot update attendance config"""
        # Login as regular employee
        employee_session = requests.Session()
        employee_session.headers.update({"Content-Type": "application/json"})
        
        login_response = employee_session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",  # Regular employee
            "password": "employee123"
        })
        
        if login_response.status_code != 200:
            print(f"⚠ Skipping employee permission test - EMP003 login failed")
            return
        
        token = login_response.json().get("access_token")
        employee_session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to update config
        update_payload = {
            "grace_period_minutes": 60
        }
        
        response = employee_session.put(
            f"{BASE_URL}/api/business-rules/attendance/config",
            json=update_payload
        )
        
        # Should fail with 403
        assert response.status_code == 403, f"Employee should not be able to update config: {response.text}"
        print(f"✓ Regular employee correctly denied config update")
        
        employee_session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
