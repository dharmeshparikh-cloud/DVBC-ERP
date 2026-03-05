"""
WebSocket API Tests for NETRA ERP
==================================
Tests WebSocket connection endpoints, stats, broadcast, and connections endpoints.
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWebSocketAPI:
    """WebSocket-related HTTP endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.user_id = login_response.json().get("user", {}).get("id")
        else:
            pytest.skip("Login failed - skipping WebSocket tests")
    
    def test_01_websocket_stats_endpoint(self):
        """Test GET /api/ws/stats - returns WebSocket manager statistics"""
        response = self.session.get(f"{BASE_URL}/api/ws/stats")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "active_connections" in data, "Missing 'active_connections' field"
        assert "subscriptions" in data, "Missing 'subscriptions' field"
        assert "stats" in data, "Missing 'stats' field"
        
        # Verify stats sub-fields
        stats = data.get("stats", {})
        assert "total_connections" in stats, "Missing 'total_connections' in stats"
        assert "total_messages" in stats, "Missing 'total_messages' in stats"
        assert "total_broadcasts" in stats, "Missing 'total_broadcasts' in stats"
        
        # Verify values are non-negative integers
        assert isinstance(data["active_connections"], int), "active_connections should be int"
        assert data["active_connections"] >= 0, "active_connections should be >= 0"
        
        print(f"WebSocket stats: active={data['active_connections']}, total_connections={stats['total_connections']}, total_messages={stats['total_messages']}")
    
    def test_02_websocket_connections_endpoint(self):
        """Test GET /api/ws/connections - returns list of connected users"""
        response = self.session.get(f"{BASE_URL}/api/ws/connections")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "connected_users" in data, "Missing 'connected_users' field"
        assert "count" in data, "Missing 'count' field"
        
        # Verify connected_users is a list
        assert isinstance(data["connected_users"], list), "connected_users should be a list"
        
        # Count should match list length
        assert data["count"] == len(data["connected_users"]), "count should match connected_users length"
        
        print(f"Connected users: {data['count']} - {data['connected_users']}")
    
    def test_03_websocket_broadcast_endpoint(self):
        """Test POST /api/ws/broadcast - broadcasts a message to all clients"""
        # Test basic broadcast
        response = self.session.post(f"{BASE_URL}/api/ws/broadcast?message=TestBroadcast")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Missing 'success' field"
        assert data["success"] == True, "Broadcast should return success=true"
        assert "message" in data, "Missing 'message' field"
        
        print(f"Broadcast result: {data}")
    
    def test_04_websocket_broadcast_with_topic(self):
        """Test POST /api/ws/broadcast with topic parameter"""
        # Test broadcast to specific topic
        response = self.session.post(f"{BASE_URL}/api/ws/broadcast?message=TopicTestMessage&topic=dashboard")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, "Topic broadcast should succeed"
        
        print(f"Topic broadcast result: {data}")
    
    def test_05_login_endpoint_works(self):
        """Verify login endpoint returns expected user data for WebSocket connection"""
        # Create new session for clean login test
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        
        assert response.status_code == 200, f"Login failed: {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify login response has required fields for WebSocket
        assert "access_token" in data, "Missing 'access_token' field"
        assert "user" in data, "Missing 'user' field"
        
        user = data["user"]
        assert "id" in user, "Missing 'id' in user - required for WebSocket connection"
        assert "employee_id" in user, "Missing 'employee_id' in user"
        assert "role" in user, "Missing 'role' in user"
        assert "full_name" in user, "Missing 'full_name' in user"
        
        print(f"Login successful - user_id: {user['id']}, employee_id: {user['employee_id']}, role: {user['role']}")
    
    def test_06_api_health_check(self):
        """Verify API health endpoint works"""
        response = self.session.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", "API should be healthy"
        
        print(f"API health: {data}")


class TestDashboardDataEndpoints:
    """Test dashboard endpoints that would receive real-time updates"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Login failed - skipping dashboard tests")
    
    def test_01_dashboard_stats_endpoint(self):
        """Test dashboard stats endpoint that would be updated via WebSocket"""
        response = self.session.get(f"{BASE_URL}/api/stats/dashboard")
        
        # Dashboard stats should return 200
        assert response.status_code == 200, f"Dashboard stats failed: {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify some expected fields exist (structure may vary)
        assert isinstance(data, dict), "Dashboard stats should return a dict"
        
        print(f"Dashboard stats keys: {list(data.keys())}")
    
    def test_02_employees_list_endpoint(self):
        """Test employees list endpoint that would be updated via WebSocket"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        
        assert response.status_code == 200, f"Employees list failed: {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response is a list or has items
        if isinstance(data, list):
            print(f"Employees count: {len(data)}")
        elif isinstance(data, dict) and "items" in data:
            print(f"Employees count: {len(data.get('items', []))}")
    
    def test_03_notifications_endpoint(self):
        """Test notifications endpoint that would receive WebSocket updates"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        
        assert response.status_code == 200, f"Notifications failed: {response.status_code}: {response.text}"
        
        data = response.json()
        
        if isinstance(data, list):
            print(f"Notifications count: {len(data)}")
        elif isinstance(data, dict):
            print(f"Notifications response: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
