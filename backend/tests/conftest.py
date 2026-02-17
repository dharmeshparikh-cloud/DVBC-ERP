"""
Pytest configuration and shared fixtures for API testing.
Provides authentication helpers, test data factories, and common utilities.
"""

import pytest
import httpx
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
from datetime import datetime, timezone

load_dotenv('/app/backend/.env')

# API Configuration
API_URL = os.environ.get('TEST_API_URL', 'https://trip-reimberse.preview.emergentagent.com')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test credentials
TEST_USERS = {
    "admin": {"email": "admin@company.com", "password": "admin123"},
    "manager": {"email": "manager@company.com", "password": "manager123"},
    "executive": {"email": "executive@company.com", "password": "executive123"},
}

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Set async mode for pytest-asyncio
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as async")

@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for each test function."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    """MongoDB database fixture."""
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture
def api_url():
    """API base URL fixture."""
    return API_URL


@pytest.fixture
def generate_uuid():
    """Generate a unique UUID for test data."""
    def _generate():
        return str(uuid.uuid4())
    return _generate


@pytest.fixture
def current_timestamp():
    """Get current UTC timestamp in ISO format."""
    def _timestamp():
        return datetime.now(timezone.utc).isoformat()
    return _timestamp


# ============== OWASP Test Payloads ==============

class OWASPPayloads:
    """OWASP security test payloads."""
    
    # A03:2021 - Injection
    SQL_INJECTION = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1' OR '1' = '1",
        "admin'--",
        "' UNION SELECT * FROM users --",
        "1; UPDATE users SET role='admin' WHERE email='test@test.com'",
    ]
    
    NOSQL_INJECTION = [
        {"$gt": ""},
        {"$ne": None},
        {"$where": "this.password.length > 0"},
        {"$regex": ".*"},
        {"$exists": True},
    ]
    
    # A03:2021 - XSS Payloads
    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "'\"><script>alert('XSS')</script>",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "{{constructor.constructor('alert(1)')()}}",
    ]
    
    # A04:2021 - Path Traversal
    PATH_TRAVERSAL = [
        "../../../etc/passwd",
        "....//....//....//etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "....//....//....//etc/shadow",
    ]
    
    # A07:2021 - SSRF Payloads
    SSRF_PAYLOADS = [
        "http://127.0.0.1:22",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "http://[::1]/",
    ]
    
    # Command Injection
    COMMAND_INJECTION = [
        "; ls -la",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
        "& ping -c 1 attacker.com",
    ]
    
    # LDAP Injection
    LDAP_INJECTION = [
        "*)(uid=*))(|(uid=*",
        "admin)(&)",
        "x)(|(objectClass=*)",
    ]
    
    # XXE Payloads
    XXE_PAYLOADS = [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
    ]


@pytest.fixture
def owasp_payloads():
    """OWASP security payloads fixture."""
    return OWASPPayloads()


# ============== Test Data Factories ==============

class TestDataFactory:
    """Factory for generating test data."""
    
    @staticmethod
    def lead(overrides: dict = None) -> dict:
        """Generate test lead data."""
        data = {
            "first_name": "Test",
            "last_name": "Lead",
            "company": "Test Company Ltd",
            "email": f"test_{uuid.uuid4().hex[:8]}@testcompany.com",
            "phone": "+91-9876543210",
            "job_title": "HR Manager",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "status": "new",
            "notes": "Test lead for API testing"
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def employee(overrides: dict = None) -> dict:
        """Generate test employee data."""
        data = {
            "employee_id": f"EMP-{uuid.uuid4().hex[:6].upper()}",
            "first_name": "Test",
            "last_name": "Employee",
            "email": f"test_{uuid.uuid4().hex[:8]}@dvconsulting.co.in",
            "phone": "+91-9876543210",
            "department": "Consulting",
            "designation": "Consultant",
            "employment_type": "full_time"
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def project(overrides: dict = None) -> dict:
        """Generate test project data."""
        data = {
            "name": f"Test Project {uuid.uuid4().hex[:6]}",
            "client_name": "Test Client",
            "project_type": "mixed",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "total_meetings_committed": 10,
            "notes": "Test project for API testing"
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def expense(overrides: dict = None) -> dict:
        """Generate test expense data."""
        data = {
            "employee_id": "",  # Will be set by test or API
            "employee_name": "Test Employee",
            "is_office_expense": True,
            "line_items": [
                {
                    "category": "travel",
                    "description": "Test expense for API testing",
                    "amount": 1500.00,
                    "date": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def meeting(project_id: str, overrides: dict = None) -> dict:
        """Generate test meeting data."""
        data = {
            "type": "consulting",
            "project_id": project_id,
            "meeting_date": datetime.now(timezone.utc).isoformat(),
            "mode": "online",
            "title": f"Test Meeting {uuid.uuid4().hex[:6]}",
            "duration_minutes": 60,
            "attendees": [],
            "attendee_names": ["Test Attendee"],
            "notes": "Test meeting"
        }
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def client(overrides: dict = None) -> dict:
        """Generate test client data."""
        data = {
            "company_name": f"Test Client {uuid.uuid4().hex[:6]}",
            "industry": "IT Services",
            "website": "https://testclient.com",
            "address": "Test Address, Mumbai",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India"
        }
        if overrides:
            data.update(overrides)
        return data


@pytest.fixture
def test_data():
    """Test data factory fixture."""
    return TestDataFactory()


# ============== HTTP Client Helpers ==============

class APIClient:
    """Helper class for making API requests."""
    
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
    
    def _headers(self, extra: dict = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers
    
    async def get(self, path: str, params: dict = None, headers: dict = None):
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self._headers(headers)
            )
    
    async def post(self, path: str, json: dict = None, headers: dict = None):
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.post(
                f"{self.base_url}{path}",
                json=json,
                headers=self._headers(headers)
            )
    
    async def put(self, path: str, json: dict = None, headers: dict = None):
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.put(
                f"{self.base_url}{path}",
                json=json,
                headers=self._headers(headers)
            )
    
    async def patch(self, path: str, json: dict = None, headers: dict = None):
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.patch(
                f"{self.base_url}{path}",
                json=json,
                headers=self._headers(headers)
            )
    
    async def delete(self, path: str, headers: dict = None):
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.delete(
                f"{self.base_url}{path}",
                headers=self._headers(headers)
            )


async def _get_token(api_url: str, role: str) -> str:
    """Get authentication token for a role."""
    creds = TEST_USERS[role]
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/api/auth/login",
            json=creds
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        raise Exception(f"Login failed for {role}: {response.status_code}")


@pytest.fixture
def api_client(api_url):
    """Unauthenticated API client fixture."""
    return APIClient(api_url)


@pytest.fixture
async def token_manager(api_url):
    """Simple token provider."""
    class TokenProvider:
        def __init__(self, url):
            self.url = url
            self._cache = {}
        
        async def get_token(self, role: str) -> str:
            if role not in self._cache:
                self._cache[role] = await _get_token(self.url, role)
            return self._cache[role]
    
    return TokenProvider(api_url)


@pytest.fixture
async def admin_client(api_url):
    """Admin-authenticated API client fixture."""
    token = await _get_token(api_url, "admin")
    return APIClient(api_url, token)


@pytest.fixture
async def manager_client(api_url):
    """Manager-authenticated API client fixture."""
    token = await _get_token(api_url, "manager")
    return APIClient(api_url, token)


@pytest.fixture
async def executive_client(api_url):
    """Executive-authenticated API client fixture."""
    token = await _get_token(api_url, "executive")
    return APIClient(api_url, token)
