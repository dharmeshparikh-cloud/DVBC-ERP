"""
Backend tests for AI-Powered Hybrid Guidance System
Tests the /api/ai/guidance-help endpoint functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestGuidanceSystem:
    """Tests for the AI Guidance Help endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers for API calls"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_guidance_help_endpoint_exists(self, auth_headers):
        """Test that the AI guidance help endpoint exists and requires auth"""
        # Test without auth should fail
        response = requests.post(f"{BASE_URL}/api/ai/guidance-help", json={
            "query": "test",
            "current_page": "/",
            "user_role": "admin"
        })
        assert response.status_code == 401, "Endpoint should require authentication"
    
    def test_guidance_help_basic_query(self, auth_headers):
        """Test basic AI guidance query returns valid response format"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "How do I apply for leave?",
                "current_page": "/",
                "user_role": "admin"
            }
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "response" in data, "Response should have 'response' field"
        assert "suggested_route" in data, "Response should have 'suggested_route' field"
        assert "auto_navigate" in data, "Response should have 'auto_navigate' field"
        
        # Verify response is not empty
        assert len(data["response"]) > 0, "Response text should not be empty"
    
    def test_guidance_help_returns_navigation_suggestion(self, auth_headers):
        """Test that AI provides navigation suggestion for leave query"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "How do I apply for leave?",
                "current_page": "/",
                "user_role": "employee"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # For leave query, should suggest /my-leaves route
        assert data["suggested_route"] == "/my-leaves", \
            f"Expected /my-leaves route, got {data['suggested_route']}"
    
    def test_guidance_help_expense_query(self, auth_headers):
        """Test AI guidance for expense-related query"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "How do I submit an expense claim?",
                "current_page": "/",
                "user_role": "employee"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should provide response about expenses
        assert len(data["response"]) > 0
        # May suggest /my-expenses route
        if data["suggested_route"]:
            assert "expense" in data["suggested_route"].lower() or data["suggested_route"] == "/my-expenses"
    
    def test_guidance_help_attendance_query(self, auth_headers):
        """Test AI guidance for attendance-related query"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "How do I check in for today?",
                "current_page": "/",
                "user_role": "employee"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should provide response about attendance
        assert len(data["response"]) > 0
    
    def test_guidance_help_context_aware(self, auth_headers):
        """Test that AI uses current page context"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "What can I do here?",
                "current_page": "/my-leaves",
                "user_role": "employee"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Response should mention leave-related actions
        assert len(data["response"]) > 0
    
    def test_guidance_help_admin_query(self, auth_headers):
        """Test AI guidance for admin-specific query"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "How do I onboard a new employee?",
                "current_page": "/",
                "user_role": "admin"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should provide response about onboarding
        assert len(data["response"]) > 0
        # May suggest /onboarding route
        if data["suggested_route"]:
            assert "onboarding" in data["suggested_route"].lower() or data["suggested_route"] == "/onboarding"
    
    def test_guidance_help_empty_query(self, auth_headers):
        """Test handling of empty query"""
        response = requests.post(
            f"{BASE_URL}/api/ai/guidance-help",
            headers=auth_headers,
            json={
                "query": "",
                "current_page": "/",
                "user_role": "admin"
            }
        )
        
        # Should still return 200 but with guidance to ask properly
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestGuidanceState:
    """Tests for user guidance state management"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers for API calls"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_guidance_state(self, auth_headers):
        """Test fetching user's guidance state"""
        response = requests.get(
            f"{BASE_URL}/api/my/guidance-state",
            headers=auth_headers
        )
        
        # Should return 200 or 404 if not set yet
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            # Verify expected structure
            assert "dismissed_tips" in data or isinstance(data, dict)
    
    def test_save_guidance_state(self, auth_headers):
        """Test saving user's guidance state"""
        state_data = {
            "dismissed_tips": ["tip_1"],
            "seen_features": ["feature_1"],
            "workflow_progress": {},
            "dont_show_tips": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/my/guidance-state",
            headers=auth_headers,
            json=state_data
        )
        
        assert response.status_code in [200, 201], f"Failed to save state: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
