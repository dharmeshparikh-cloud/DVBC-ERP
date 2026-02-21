"""
Tests for Chat, AI Assistant, and Email Actions APIs
- Chat API: DMs, Group conversations, Messages
- AI API: Query, Analyze reports, Quick insights
- Email API: Config management
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
HR_EMAIL = "hr.manager@dvbc.com"
HR_PASSWORD = "hr123"

# User IDs from context
ADMIN_USER_ID = "48588b92-8856-4e3a-aa6c-b9e493442761"
HR_USER_ID = "ed94c6a5-f3dd-4330-ade0-910071fb27b1"


@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def hr_auth_token():
    """Get HR authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": HR_EMAIL, "password": HR_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestChatUsers:
    """Test /api/chat/users endpoint"""
    
    def test_get_chat_users_list(self, api_client):
        """GET /api/chat/users should return list of users"""
        response = api_client.get(f"{BASE_URL}/api/chat/users")
        print(f"Chat users status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} chat users")
        
        # Should have at least some users
        if len(data) > 0:
            user = data[0]
            assert "id" in user, "User should have id"
            print(f"Sample user: {user.get('full_name', 'Unknown')}")
    
    def test_search_chat_users(self, api_client):
        """GET /api/chat/users with search param"""
        response = api_client.get(f"{BASE_URL}/api/chat/users?search=admin")
        print(f"Chat users search status: {response.status_code}")
        
        assert response.status_code == 200


class TestChatConversations:
    """Test chat conversations endpoints"""
    
    conversation_id = None
    
    def test_create_dm_conversation(self, api_client):
        """POST /api/chat/conversations - Create DM"""
        payload = {
            "type": "dm",
            "participant_ids": [ADMIN_USER_ID, HR_USER_ID]
        }
        
        response = api_client.post(f"{BASE_URL}/api/chat/conversations", json=payload)
        print(f"Create DM status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Conversation should have id"
        assert data.get("type") == "dm", "Should be DM type"
        
        TestChatConversations.conversation_id = data["id"]
        print(f"Created conversation ID: {data['id']}")
    
    def test_create_group_conversation(self, api_client):
        """POST /api/chat/conversations - Create group"""
        payload = {
            "type": "group",
            "name": "TEST_Group_Chat",
            "participant_ids": [ADMIN_USER_ID, HR_USER_ID],
            "description": "Test group for automation testing"
        }
        
        response = api_client.post(f"{BASE_URL}/api/chat/conversations", json=payload)
        print(f"Create group status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("type") == "group"
        assert data.get("name") == "TEST_Group_Chat"
        print(f"Created group: {data.get('name')}")
    
    def test_get_conversations_for_user(self, api_client):
        """GET /api/chat/conversations?user_id=xxx"""
        response = api_client.get(f"{BASE_URL}/api/chat/conversations?user_id={ADMIN_USER_ID}")
        print(f"Get conversations status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} conversations for admin user")
    
    def test_get_specific_conversation(self, api_client):
        """GET /api/chat/conversations/{id}"""
        if not TestChatConversations.conversation_id:
            pytest.skip("No conversation ID available")
        
        response = api_client.get(f"{BASE_URL}/api/chat/conversations/{TestChatConversations.conversation_id}")
        print(f"Get conversation status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("id") == TestChatConversations.conversation_id


class TestChatMessages:
    """Test chat messages endpoints"""
    
    message_id = None
    
    def test_send_message(self, api_client):
        """POST /api/chat/conversations/{id}/messages"""
        conv_id = TestChatConversations.conversation_id
        if not conv_id:
            pytest.skip("No conversation ID available")
        
        payload = {
            "content": "Hello! This is a test message from automation.",
            "message_type": "text"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/chat/conversations/{conv_id}/messages?sender_id={ADMIN_USER_ID}",
            json=payload
        )
        print(f"Send message status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Message should have id"
        assert data.get("content") == payload["content"]
        
        TestChatMessages.message_id = data["id"]
        print(f"Sent message ID: {data['id']}")
    
    def test_send_message_with_erp_record(self, api_client):
        """POST /api/chat/conversations/{id}/messages with ERP record"""
        conv_id = TestChatConversations.conversation_id
        if not conv_id:
            pytest.skip("No conversation ID available")
        
        payload = {
            "content": "Please review this leave request",
            "message_type": "action",
            "erp_record": {
                "type": "leave_request",
                "id": "test-leave-123",
                "data": {
                    "employee_name": "Test Employee",
                    "leave_type": "Casual",
                    "days": 2
                }
            },
            "action_buttons": [
                {"label": "Approve", "action": "approve"},
                {"label": "Reject", "action": "reject"}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/chat/conversations/{conv_id}/messages?sender_id={ADMIN_USER_ID}",
            json=payload
        )
        print(f"Send ERP message status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("erp_record") is not None
        assert data.get("action_buttons") is not None
        print("Message with ERP record and action buttons sent successfully")
    
    def test_get_messages(self, api_client):
        """GET /api/chat/conversations/{id}/messages"""
        conv_id = TestChatConversations.conversation_id
        if not conv_id:
            pytest.skip("No conversation ID available")
        
        response = api_client.get(f"{BASE_URL}/api/chat/conversations/{conv_id}/messages")
        print(f"Get messages status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} messages in conversation")
    
    def test_mark_messages_as_read(self, api_client):
        """POST /api/chat/conversations/{id}/read-all"""
        conv_id = TestChatConversations.conversation_id
        if not conv_id:
            pytest.skip("No conversation ID available")
        
        response = api_client.post(
            f"{BASE_URL}/api/chat/conversations/{conv_id}/read-all?user_id={ADMIN_USER_ID}"
        )
        print(f"Mark all read status: {response.status_code}")
        
        assert response.status_code == 200


class TestAIAssistant:
    """Test AI Assistant endpoints"""
    
    def test_ai_query(self, api_client):
        """POST /api/ai/query - Query AI with ERP context"""
        payload = {
            "query": "What is the sales performance summary?",
            "context": "sales"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/ai/query?user_id={ADMIN_USER_ID}",
            json=payload,
            timeout=60  # AI calls may take longer
        )
        print(f"AI query status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "response" in data, "Should have AI response"
        assert "query_type" in data, "Should have query_type"
        print(f"AI response received, type: {data.get('query_type')}")
        print(f"Response preview: {data.get('response', '')[:100]}...")
    
    def test_analyze_report(self, api_client):
        """POST /api/ai/analyze-report - Generate AI analysis"""
        payload = {
            "report_type": "hr"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/ai/analyze-report?user_id={ADMIN_USER_ID}",
            json=payload,
            timeout=60
        )
        print(f"Analyze report status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "analysis" in data, "Should have analysis"
        assert data.get("report_type") == "hr"
        print(f"Analysis generated for report type: {data.get('report_type')}")
    
    def test_quick_insights(self, api_client):
        """POST /api/ai/quick-insights - Get dashboard insights"""
        response = api_client.post(f"{BASE_URL}/api/ai/quick-insights?user_id={ADMIN_USER_ID}")
        print(f"Quick insights status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "insights" in data, "Should have insights"
        assert "generated_at" in data, "Should have timestamp"
        print(f"Found {len(data.get('insights', []))} quick insights")
    
    def test_ai_suggestions(self, api_client):
        """GET /api/ai/suggestions - Get AI suggestions"""
        response = api_client.get(
            f"{BASE_URL}/api/ai/suggestions?user_id={ADMIN_USER_ID}&context=all",
            timeout=60
        )
        print(f"AI suggestions status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "suggestions" in data or "raw_response" in data
        print("AI suggestions endpoint working")
    
    def test_chat_history(self, api_client):
        """GET /api/ai/chat-history - Get AI chat history"""
        response = api_client.get(f"{BASE_URL}/api/ai/chat-history?user_id={ADMIN_USER_ID}&limit=10")
        print(f"Chat history status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} chat history entries")


class TestEmailActions:
    """Test Email Actions configuration"""
    
    def test_get_email_config(self, api_client):
        """GET /api/email-actions/config"""
        response = api_client.get(f"{BASE_URL}/api/email-actions/config")
        print(f"Get email config status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        # Config may have header_html and footer_html (can be null)
        assert "header_html" in data or data == {} or isinstance(data, dict)
        print("Email config retrieved successfully")
    
    def test_update_email_config(self, api_client):
        """PUT /api/email-actions/config - Update template config"""
        payload = {
            "header_html": """<div style="background: #1f2937; padding: 20px; text-align: center;">
                <h1 style="color: white;">TEST Header</h1>
            </div>""",
            "footer_html": """<div style="background: #f8fafc; padding: 20px; text-align: center;">
                <p>TEST Footer - DVBC NETRA</p>
            </div>"""
        }
        
        response = api_client.put(f"{BASE_URL}/api/email-actions/config", json=payload)
        print(f"Update email config status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "updated"
        print("Email config updated successfully")
    
    def test_get_email_logs(self, api_client):
        """GET /api/email-actions/logs"""
        response = api_client.get(f"{BASE_URL}/api/email-actions/logs?limit=20")
        print(f"Get email logs status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} email logs")


class TestChatSearch:
    """Test chat search functionality"""
    
    def test_search_messages(self, api_client):
        """GET /api/chat/search"""
        response = api_client.get(f"{BASE_URL}/api/chat/search?q=test&user_id={ADMIN_USER_ID}")
        print(f"Search messages status: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Search returned {len(data)} messages")


# Run all tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
