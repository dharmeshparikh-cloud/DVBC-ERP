"""
Business Rules - Add New Rule API Tests
Tests the POST /{policy_id}/rule endpoint for adding new rules to policies
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HR_CREDENTIALS = {"employee_id": "EMP002", "password": "hr123"}


class TestAddNewRule:
    """Test Add New Rule functionality"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get authenticated HR session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
            return session
        pytest.skip("HR authentication failed")
    
    @pytest.fixture(scope="class")
    def leave_policy_id(self, hr_session):
        """Get leave policy ID"""
        response = hr_session.get(f"{BASE_URL}/api/business-rules?policy_type=leave")
        if response.status_code == 200:
            policies = response.json()
            leave_policies = [p for p in policies if p.get("policy_type") == "leave"]
            if leave_policies:
                return leave_policies[0]["id"]
        pytest.skip("Leave policy not found")
    
    def test_add_new_rule_with_all_fields(self, hr_session, leave_policy_id):
        """Test adding a new rule with all fields including unit"""
        unique_id = str(uuid.uuid4())[:8]
        rule_data = {
            "rule_id": f"TEST_{unique_id}",
            "rule_name": f"Test Rule {unique_id}",
            "rule_type": "limit",
            "category": "test_category",
            "description": "Test rule created by automated test",
            "numeric_value": 10,
            "unit": "days/year",
            "value": "test_value",
            "is_enabled": True
        }
        
        response = hr_session.post(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule",
            json=rule_data
        )
        
        assert response.status_code == 200, f"Failed to add rule: {response.text}"
        result = response.json()
        assert "rule_id" in result, "Response should contain rule_id"
        print(f"Successfully added rule: {result.get('rule_id')}")
        
        # Verify rule was added by fetching the policy
        verify_response = hr_session.get(f"{BASE_URL}/api/business-rules/{leave_policy_id}")
        assert verify_response.status_code == 200
        policy = verify_response.json()
        rules = policy.get("rules", [])
        
        added_rule = next((r for r in rules if r.get("rule_id") == rule_data["rule_id"]), None)
        assert added_rule is not None, "Added rule not found in policy"
        assert added_rule.get("rule_name") == rule_data["rule_name"]
        assert added_rule.get("numeric_value") == rule_data["numeric_value"]
        assert added_rule.get("unit") == rule_data["unit"]
        print(f"Verified rule exists with unit: {added_rule.get('unit')}")
        
        # Cleanup - delete the test rule
        delete_response = hr_session.delete(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{rule_data['rule_id']}"
        )
        assert delete_response.status_code == 200, f"Failed to delete test rule: {delete_response.text}"
        print("Test rule cleaned up successfully")
    
    def test_add_rule_auto_generate_id(self, hr_session, leave_policy_id):
        """Test adding a rule without rule_id (should auto-generate)"""
        unique_id = str(uuid.uuid4())[:8]
        rule_data = {
            "rule_name": f"Auto ID Test Rule {unique_id}",
            "rule_type": "threshold",
            "description": "Test rule with auto-generated ID",
            "numeric_value": 5,
            "unit": "days",
            "is_enabled": True
        }
        
        response = hr_session.post(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule",
            json=rule_data
        )
        
        assert response.status_code == 200, f"Failed to add rule: {response.text}"
        result = response.json()
        generated_rule_id = result.get("rule_id")
        assert generated_rule_id is not None, "Should have auto-generated rule_id"
        assert generated_rule_id.startswith("LE"), f"Leave policy rule should start with LE, got {generated_rule_id}"
        print(f"Auto-generated rule_id: {generated_rule_id}")
        
        # Cleanup
        delete_response = hr_session.delete(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{generated_rule_id}"
        )
        assert delete_response.status_code == 200
        print("Test rule cleaned up successfully")
    
    def test_add_rule_with_conditions(self, hr_session, leave_policy_id):
        """Test adding a rule with conditions object"""
        unique_id = str(uuid.uuid4())[:8]
        rule_data = {
            "rule_id": f"COND_{unique_id}",
            "rule_name": f"Conditional Rule {unique_id}",
            "rule_type": "condition",
            "description": "Test rule with conditions",
            "value": "conditional_value",
            "conditions": {
                "applies_to": "all_employees",
                "requires_approval": True,
                "max_days": 10
            },
            "is_enabled": True
        }
        
        response = hr_session.post(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule",
            json=rule_data
        )
        
        assert response.status_code == 200, f"Failed to add rule: {response.text}"
        
        # Verify conditions were saved
        verify_response = hr_session.get(f"{BASE_URL}/api/business-rules/{leave_policy_id}")
        policy = verify_response.json()
        rules = policy.get("rules", [])
        
        added_rule = next((r for r in rules if r.get("rule_id") == rule_data["rule_id"]), None)
        assert added_rule is not None
        assert added_rule.get("conditions") is not None
        assert added_rule["conditions"].get("applies_to") == "all_employees"
        print(f"Conditions saved correctly: {added_rule.get('conditions')}")
        
        # Cleanup
        hr_session.delete(f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{rule_data['rule_id']}")
    
    def test_add_rule_duplicate_id_fails(self, hr_session, leave_policy_id):
        """Test that adding a rule with duplicate ID fails"""
        # First, add a rule
        unique_id = str(uuid.uuid4())[:8]
        rule_data = {
            "rule_id": f"DUP_{unique_id}",
            "rule_name": "First Rule",
            "rule_type": "limit",
            "is_enabled": True
        }
        
        response1 = hr_session.post(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule",
            json=rule_data
        )
        assert response1.status_code == 200
        
        # Try to add another rule with same ID
        rule_data["rule_name"] = "Duplicate Rule"
        response2 = hr_session.post(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule",
            json=rule_data
        )
        
        assert response2.status_code == 400, f"Should fail with duplicate ID, got {response2.status_code}"
        assert "already exists" in response2.text.lower(), f"Error message should mention duplicate: {response2.text}"
        print("Duplicate rule ID correctly rejected")
        
        # Cleanup
        hr_session.delete(f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{rule_data['rule_id']}")
    
    def test_delete_rule(self, hr_session, leave_policy_id):
        """Test deleting a rule"""
        unique_id = str(uuid.uuid4())[:8]
        rule_data = {
            "rule_id": f"DEL_{unique_id}",
            "rule_name": "Rule to Delete",
            "rule_type": "limit",
            "is_enabled": True
        }
        
        # Add rule
        add_response = hr_session.post(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule",
            json=rule_data
        )
        assert add_response.status_code == 200
        
        # Delete rule
        delete_response = hr_session.delete(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{rule_data['rule_id']}"
        )
        assert delete_response.status_code == 200, f"Failed to delete rule: {delete_response.text}"
        
        # Verify rule is gone
        verify_response = hr_session.get(f"{BASE_URL}/api/business-rules/{leave_policy_id}")
        policy = verify_response.json()
        rules = policy.get("rules", [])
        
        deleted_rule = next((r for r in rules if r.get("rule_id") == rule_data["rule_id"]), None)
        assert deleted_rule is None, "Rule should have been deleted"
        print("Rule deleted successfully")
    
    def test_update_rule_with_unit(self, hr_session, leave_policy_id):
        """Test updating a rule's unit field"""
        # Get existing rule
        response = hr_session.get(f"{BASE_URL}/api/business-rules/{leave_policy_id}")
        policy = response.json()
        rules = policy.get("rules", [])
        
        if not rules:
            pytest.skip("No rules to update")
        
        test_rule = rules[0]
        rule_id = test_rule.get("rule_id")
        original_unit = test_rule.get("unit", "")
        
        # Update with new unit
        update_data = {
            **test_rule,
            "unit": "TEST_UNIT"
        }
        
        update_response = hr_session.put(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{rule_id}",
            json=update_data
        )
        assert update_response.status_code == 200, f"Failed to update rule: {update_response.text}"
        
        # Verify update
        verify_response = hr_session.get(f"{BASE_URL}/api/business-rules/{leave_policy_id}")
        updated_policy = verify_response.json()
        updated_rule = next((r for r in updated_policy.get("rules", []) if r.get("rule_id") == rule_id), None)
        
        assert updated_rule is not None
        assert updated_rule.get("unit") == "TEST_UNIT", f"Unit not updated: {updated_rule.get('unit')}"
        print(f"Unit updated successfully to: {updated_rule.get('unit')}")
        
        # Restore original unit
        restore_data = {
            **test_rule,
            "unit": original_unit
        }
        hr_session.put(
            f"{BASE_URL}/api/business-rules/{leave_policy_id}/rule/{rule_id}",
            json=restore_data
        )
        print("Original unit restored")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
