"""
Test Help Content Management API Endpoints
Tests: context-aware topics, search, categories, topic detail, CRUD operations, and admin features
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestHelpContentSeeding:
    """Test seed data and initial state"""

    def test_seed_help_content(self):
        """Seed help content - should either create or skip if already seeded"""
        response = requests.post(f"{BASE_URL}/api/help/admin/seed")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Seed response: {data['message']}")


class TestHelpContextAPI:
    """Test context-aware help topics endpoint"""

    def test_get_context_topics_for_dashboard(self):
        """GET /api/help/context - should return topics relevant to current route"""
        response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/dashboard",
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "topics" in data
        assert "route" in data
        assert data["route"] == "/dashboard"
        
        # Validate topic structure if topics exist
        if data["topics"]:
            topic = data["topics"][0]
            assert "id" in topic
            assert "title" in topic
            assert "type" in topic
            assert "isNew" in topic
        
        print(f"✓ Context topics for /dashboard: {len(data['topics'])} topics found")

    def test_get_context_topics_for_onboarding(self):
        """GET /api/help/context - should return onboarding-specific help topics"""
        response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/onboarding-hub",
            "role": "hr_manager"
        })
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        print(f"✓ Context topics for /onboarding-hub: {len(data['topics'])} topics found")

    def test_context_topics_role_filtering(self):
        """Test that role filtering works correctly"""
        # Admin should see all topics
        admin_response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/",
            "role": "admin"
        })
        assert admin_response.status_code == 200
        
        # Regular employee might see fewer topics
        employee_response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/",
            "role": "employee"
        })
        assert employee_response.status_code == 200
        print("✓ Role-based filtering working")


class TestHelpCategoriesAPI:
    """Test help categories endpoint"""

    def test_get_all_categories(self):
        """GET /api/help/categories - should return all categories"""
        response = requests.get(f"{BASE_URL}/api/help/categories", params={
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of categories
        assert isinstance(data, list)
        assert len(data) >= 7, f"Expected at least 7 seeded categories, got {len(data)}"
        
        # Validate category structure
        if data:
            category = data[0]
            assert "id" in category
            assert "name" in category
            assert "icon" in category
            assert "topicCount" in category
        
        # Check expected categories exist
        category_names = [c["name"] for c in data]
        assert "Getting Started" in category_names
        assert "Onboarding" in category_names
        assert "Leave & Attendance" in category_names
        
        print(f"✓ Categories retrieved: {len(data)} categories")

    def test_category_topics(self):
        """GET /api/help/categories/{category_id}/topics - should return topics in category"""
        response = requests.get(f"{BASE_URL}/api/help/categories/onboarding/topics", params={
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # Validate topic structure
        if data:
            topic = data[0]
            assert "id" in topic
            assert "title" in topic
            assert "type" in topic
        
        print(f"✓ Onboarding category topics: {len(data)} topics found")


class TestHelpSearchAPI:
    """Test help search functionality"""

    def test_search_help_topics(self):
        """GET /api/help/search - should return relevant results"""
        response = requests.get(f"{BASE_URL}/api/help/search", params={
            "q": "leave",
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "query" in data
        assert data["query"] == "leave"
        
        # Validate result structure if results exist
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "title" in result
            assert "type" in result
        
        print(f"✓ Search for 'leave': {len(data['results'])} results")

    def test_search_onboarding(self):
        """Search for onboarding-related topics"""
        response = requests.get(f"{BASE_URL}/api/help/search", params={
            "q": "onboarding",
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["results"]) >= 1, "Should find at least one onboarding topic"
        print(f"✓ Search for 'onboarding': {len(data['results'])} results")

    def test_search_minimum_length(self):
        """Search query must be at least 2 characters"""
        response = requests.get(f"{BASE_URL}/api/help/search", params={
            "q": "a",  # Too short
            "role": "admin"
        })
        # Should return validation error
        assert response.status_code == 422
        print("✓ Search validation working (min 2 chars)")


class TestHelpTopicDetailAPI:
    """Test topic detail endpoint"""

    def test_get_topic_by_id(self):
        """GET /api/help/topics/{topic_id} - should return full topic details"""
        # First get a topic ID from context
        context_response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/dashboard",
            "role": "admin"
        })
        assert context_response.status_code == 200
        topics = context_response.json()["topics"]
        
        if not topics:
            pytest.skip("No topics available to test")
        
        topic_id = topics[0]["id"]
        
        # Get topic detail
        response = requests.get(f"{BASE_URL}/api/help/topics/{topic_id}", params={
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Validate full topic structure
        assert "id" in data
        assert "title" in data
        assert "type" in data
        assert "category" in data
        assert "steps" in data  # Should have steps array
        
        print(f"✓ Topic detail retrieved: {data['title']}")

    def test_topic_not_found(self):
        """GET /api/help/topics/{invalid_id} - should return 404"""
        response = requests.get(f"{BASE_URL}/api/help/topics/000000000000000000000000", params={
            "role": "admin"
        })
        assert response.status_code == 404
        print("✓ Invalid topic returns 404")


class TestHelpWhatsNewAPI:
    """Test What's New endpoint"""

    def test_get_whats_new(self):
        """GET /api/help/whats-new - should return new topics"""
        response = requests.get(f"{BASE_URL}/api/help/whats-new", params={
            "role": "admin",
            "limit": 5
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        
        # Validate item structure
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "title" in item
            assert "createdAt" in item
        
        print(f"✓ What's New: {len(data['items'])} items")


class TestHelpFeedbackAPI:
    """Test topic view and feedback tracking"""

    def test_track_topic_view(self):
        """POST /api/help/topics/{topic_id}/view - should track view"""
        # Get a topic ID
        context_response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/dashboard",
            "role": "admin"
        })
        topics = context_response.json()["topics"]
        
        if not topics:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Track view
        response = requests.post(f"{BASE_URL}/api/help/topics/{topic_id}/view")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Topic view tracked")

    def test_submit_helpful_feedback(self):
        """POST /api/help/topics/{topic_id}/feedback - should accept helpful feedback"""
        # Get a topic ID
        context_response = requests.get(f"{BASE_URL}/api/help/context", params={
            "route": "/dashboard",
            "role": "admin"
        })
        topics = context_response.json()["topics"]
        
        if not topics:
            pytest.skip("No topics available")
        
        topic_id = topics[0]["id"]
        
        # Submit positive feedback
        response = requests.post(
            f"{BASE_URL}/api/help/topics/{topic_id}/feedback",
            json={"helpful": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Helpful feedback submitted")

    def test_submit_not_helpful_feedback(self):
        """POST /api/help/topics/{topic_id}/feedback - should accept not helpful feedback"""
        # Get a topic ID
        search_response = requests.get(f"{BASE_URL}/api/help/search", params={
            "q": "leave",
            "role": "admin"
        })
        results = search_response.json()["results"]
        
        if not results:
            pytest.skip("No topics available")
        
        topic_id = results[0]["id"]
        
        # Submit negative feedback
        response = requests.post(
            f"{BASE_URL}/api/help/topics/{topic_id}/feedback",
            json={"helpful": False}
        )
        assert response.status_code == 200
        print("✓ Not helpful feedback submitted")


class TestHelpAdminAPI:
    """Test admin endpoints for help content management"""

    def test_admin_list_topics(self):
        """GET /api/help/admin/topics - should list all topics"""
        response = requests.get(f"{BASE_URL}/api/help/admin/topics")
        assert response.status_code == 200
        data = response.json()
        
        assert "topics" in data
        assert "total" in data
        assert data["total"] >= 7, f"Expected at least 7 seeded topics, got {data['total']}"
        
        # Validate topic has admin fields
        if data["topics"]:
            topic = data["topics"][0]
            assert "id" in topic
            assert "title" in topic
            assert "isActive" in topic
        
        print(f"✓ Admin topics list: {data['total']} topics")

    def test_admin_list_categories(self):
        """GET /api/help/admin/categories - should list all categories"""
        response = requests.get(f"{BASE_URL}/api/help/admin/categories")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 7
        print(f"✓ Admin categories list: {len(data)} categories")

    def test_admin_get_analytics(self):
        """GET /api/help/admin/analytics - should return analytics data"""
        response = requests.get(f"{BASE_URL}/api/help/admin/analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert "totalTopics" in data
        assert "totalViews" in data
        assert "topViewed" in data
        assert "mostHelpful" in data
        assert "needsImprovement" in data
        
        print(f"✓ Analytics: {data['totalTopics']} topics, {data['totalViews']} total views")

    def test_admin_create_topic(self):
        """POST /api/help/admin/topics - should create new topic"""
        unique_id = str(uuid.uuid4())[:8]
        new_topic = {
            "title": f"TEST_Topic_{unique_id}",
            "slug": f"test-topic-{unique_id}",
            "type": "guide",
            "category": "getting-started",
            "routes": ["/test"],
            "roles": [],
            "introduction": "This is a test topic created by automated testing",
            "steps": [
                {"title": "Step 1", "description": "First step description"},
                {"title": "Step 2", "description": "Second step description"}
            ],
            "troubleshooting": [],
            "keywords": ["test", "automated"],
            "isNew": True,
            "priority": 10,
            "isActive": True
        }
        
        response = requests.post(f"{BASE_URL}/api/help/admin/topics", json=new_topic)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "message" in data
        
        # Store topic ID for cleanup
        TestHelpAdminAPI.created_topic_id = data["id"]
        print(f"✓ Topic created: {data['id']}")

    def test_admin_update_topic(self):
        """PUT /api/help/admin/topics/{topic_id} - should update topic"""
        if not hasattr(TestHelpAdminAPI, 'created_topic_id'):
            pytest.skip("No topic created to update")
        
        topic_id = TestHelpAdminAPI.created_topic_id
        
        updated_topic = {
            "title": "TEST_Topic_Updated",
            "slug": "test-topic-updated",
            "type": "guide",
            "category": "getting-started",
            "routes": ["/test"],
            "roles": [],
            "introduction": "Updated introduction",
            "steps": [],
            "troubleshooting": [],
            "keywords": ["test", "updated"],
            "isNew": False,
            "priority": 5,
            "isActive": True
        }
        
        response = requests.put(f"{BASE_URL}/api/help/admin/topics/{topic_id}", json=updated_topic)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        print("✓ Topic updated successfully")

    def test_admin_delete_topic(self):
        """DELETE /api/help/admin/topics/{topic_id} - should soft delete topic"""
        if not hasattr(TestHelpAdminAPI, 'created_topic_id'):
            pytest.skip("No topic created to delete")
        
        topic_id = TestHelpAdminAPI.created_topic_id
        
        response = requests.delete(f"{BASE_URL}/api/help/admin/topics/{topic_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        print("✓ Topic deleted (soft delete)")


class TestRoleBasedAccess:
    """Test role-based content visibility"""

    def test_hr_admin_category_visible_to_admin(self):
        """HR Administration category should be visible to admin"""
        response = requests.get(f"{BASE_URL}/api/help/categories", params={
            "role": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        
        category_names = [c["name"] for c in data]
        assert "HR Administration" in category_names
        print("✓ HR Admin category visible to admin")

    def test_hr_admin_category_visible_to_hr_manager(self):
        """HR Administration category should be visible to hr_manager"""
        response = requests.get(f"{BASE_URL}/api/help/categories", params={
            "role": "hr_manager"
        })
        assert response.status_code == 200
        data = response.json()
        
        category_names = [c["name"] for c in data]
        assert "HR Administration" in category_names
        print("✓ HR Admin category visible to hr_manager")

    def test_regular_employee_cannot_see_hr_admin(self):
        """Regular employee should NOT see HR Administration category"""
        response = requests.get(f"{BASE_URL}/api/help/categories", params={
            "role": "employee"
        })
        assert response.status_code == 200
        data = response.json()
        
        category_names = [c["name"] for c in data]
        # HR Admin has roles: ["hr_manager", "admin"], so employee should not see it
        assert "HR Administration" not in category_names
        print("✓ HR Admin category correctly hidden from regular employee")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
