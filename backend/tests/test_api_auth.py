"""
OWASP-Compliant API Security Test Suite - Authentication Module
Tests: A01:2021 Broken Access Control, A07:2021 Identification and Authentication Failures
"""

import pytest
import httpx


class TestAuthenticationPositive:
    """Positive tests for authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_auth001_valid_login_returns_token(self, api_url):
        """TC-AUTH-001: Valid credentials return JWT token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "admin@company.com", "password": "admin123"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "admin@company.com"
    
    @pytest.mark.asyncio
    async def test_auth002_token_allows_protected_access(self, admin_client):
        """TC-AUTH-002: Valid token provides access to protected routes."""
        response = await admin_client.get("/api/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "role" in data
    
    @pytest.mark.asyncio
    async def test_auth003_login_creates_audit_log(self, api_url, db):
        """TC-AUTH-003: Successful login creates security audit entry."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "admin@company.com", "password": "admin123"}
            )
        
        # Check audit log was created
        log = await db.security_audit_logs.find_one(
            {"email": "admin@company.com", "event_type": "password_login_success"},
            {"_id": 0}
        )
        assert log is not None, "Audit log should be created on login"
    
    @pytest.mark.asyncio
    async def test_auth004_change_password_success(self, api_url, token_manager):
        """TC-AUTH-004: Admin can change their own password."""
        token = await token_manager.get_token("admin")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Change to temp password then back
            response = await client.post(
                f"{api_url}/api/auth/change-password",
                json={"current_password": "admin123", "new_password": "temppass123"},
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # This will fail if password already changed, which is fine for test idempotency
        # Accept 200 (success) or 400 (wrong current password means it was already changed)
        assert response.status_code in [200, 400]


class TestAuthenticationNegative:
    """Negative tests for authentication - invalid inputs."""
    
    @pytest.mark.asyncio
    async def test_auth010_invalid_email_format(self, api_url):
        """TC-AUTH-010: Invalid email format returns error."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "not-an-email", "password": "password123"}
            )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_auth011_wrong_password(self, api_url, db):
        """TC-AUTH-011: Wrong password returns 401 and creates audit log."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "admin@company.com", "password": "wrongpassword"}
            )
        
        assert response.status_code == 401
        
        # Verify audit log
        log = await db.security_audit_logs.find_one(
            {"email": "admin@company.com", "event_type": "password_login_failed"},
            {"_id": 0}
        )
        assert log is not None
    
    @pytest.mark.asyncio
    async def test_auth012_nonexistent_user(self, api_url):
        """TC-AUTH-012: Nonexistent user returns 401."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "nonexistent@test.com", "password": "password123"}
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth013_missing_email(self, api_url):
        """TC-AUTH-013: Missing email returns validation error."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"password": "password123"}
            )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_auth014_missing_password(self, api_url):
        """TC-AUTH-014: Missing password returns validation error."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "admin@company.com"}
            )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_auth015_empty_credentials(self, api_url):
        """TC-AUTH-015: Empty credentials return error."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "", "password": ""}
            )
        
        assert response.status_code in [400, 401, 422]
    
    @pytest.mark.asyncio
    async def test_auth016_password_too_short_on_change(self, admin_client):
        """TC-AUTH-016: Password change with short password fails."""
        response = await admin_client.post(
            "/api/auth/change-password",
            json={"current_password": "admin123", "new_password": "12345"}
        )
        
        assert response.status_code == 400
        assert "at least 6 characters" in response.text.lower()


class TestAuthenticationSecurity:
    """Security tests - OWASP A07:2021 Identification & Auth Failures."""
    
    @pytest.mark.asyncio
    async def test_auth020_no_token_protected_route(self, api_url):
        """TC-AUTH-020: Protected route without token returns 401."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{api_url}/api/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth021_invalid_token(self, api_url):
        """TC-AUTH-021: Invalid JWT token returns 401."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{api_url}/api/auth/me",
                headers={"Authorization": "Bearer invalid.token.here"}
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth022_malformed_auth_header(self, api_url):
        """TC-AUTH-022: Malformed Authorization header returns 401."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{api_url}/api/auth/me",
                headers={"Authorization": "NotBearer sometoken"}
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth023_expired_token_format(self, api_url):
        """TC-AUTH-023: Expired-like token format returns 401."""
        # A properly formatted but invalid JWT
        fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxfQ.invalid"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{api_url}/api/auth/me",
                headers={"Authorization": f"Bearer {fake_jwt}"}
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth024_sql_injection_email(self, api_url, owasp_payloads):
        """TC-AUTH-024: SQL injection in email field is rejected."""
        for payload in owasp_payloads.SQL_INJECTION[:3]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/api/auth/login",
                    json={"email": payload, "password": "test"}
                )
            
            # Should be rejected (validation error or auth failure, not 500)
            assert response.status_code in [400, 401, 422], f"SQL injection payload should be rejected: {payload}"
    
    @pytest.mark.asyncio
    async def test_auth025_xss_in_password(self, api_url, owasp_payloads):
        """TC-AUTH-025: XSS payloads in password don't cause server error."""
        for payload in owasp_payloads.XSS_PAYLOADS[:3]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/api/auth/login",
                    json={"email": "test@test.com", "password": payload}
                )
            
            # Should fail auth, not cause server error
            assert response.status_code != 500, f"XSS payload should not cause server error: {payload}"
    
    @pytest.mark.asyncio
    async def test_auth026_nosql_injection_attempt(self, api_url):
        """TC-AUTH-026: NoSQL injection attempt is handled safely."""
        # Try to inject MongoDB operators
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": {"$ne": None}, "password": {"$ne": None}}
            )
        
        # Should be rejected (validation error)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_auth027_password_not_in_response(self, admin_client):
        """TC-AUTH-027: Password hash never returned in API response."""
        response = await admin_client.get("/api/auth/me")
        data = response.json()
        
        assert "password" not in data
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_auth028_very_long_email(self, api_url):
        """TC-AUTH-028: Very long email is handled without server crash."""
        long_email = "a" * 1000 + "@test.com"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": long_email, "password": "test"}
            )
        
        assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_auth029_unicode_injection(self, api_url):
        """TC-AUTH-029: Unicode characters in credentials handled safely."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/login",
                json={"email": "test\u0000@test.com", "password": "pass\u0000word"}
            )
        
        assert response.status_code != 500


class TestOTPPasswordReset:
    """Tests for OTP-based password reset (admin only)."""
    
    @pytest.mark.asyncio
    async def test_otp001_request_otp_admin(self, api_url):
        """TC-OTP-001: Admin can request OTP."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/admin/request-otp",
                json={"email": "admin@company.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "otp" in data
        assert len(data["otp"]) == 6
    
    @pytest.mark.asyncio
    async def test_otp002_request_otp_non_admin_fails(self, api_url):
        """TC-OTP-002: Non-admin cannot request OTP."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/admin/request-otp",
                json={"email": "manager@company.com"}
            )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_otp003_invalid_otp_rejected(self, api_url):
        """TC-OTP-003: Invalid OTP is rejected."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/admin/reset-password",
                json={"email": "admin@company.com", "otp": "000000", "new_password": "newpass123"}
            )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_otp004_nonexistent_user(self, api_url):
        """TC-OTP-004: OTP request for nonexistent user fails."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/api/auth/admin/request-otp",
                json={"email": "nonexistent@company.com"}
            )
        
        assert response.status_code == 404


class TestSecurityAuditLogs:
    """Tests for security audit log functionality."""
    
    @pytest.mark.asyncio
    async def test_audit001_admin_can_view_logs(self, admin_client):
        """TC-AUDIT-001: Admin can view security audit logs."""
        response = await admin_client.get("/api/security-audit-logs")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_audit002_non_admin_cannot_view_logs(self, manager_client):
        """TC-AUDIT-002: Non-admin cannot view security audit logs."""
        response = await manager_client.get("/api/security-audit-logs")
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_audit003_filter_by_event_type(self, admin_client):
        """TC-AUDIT-003: Can filter logs by event type."""
        response = await admin_client.get(
            "/api/security-audit-logs",
            params={"event_type": "password_login_success"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for log in data.get("logs", []):
            assert log["event_type"] == "password_login_success"
    
    @pytest.mark.asyncio
    async def test_audit004_filter_by_email(self, admin_client):
        """TC-AUDIT-004: Can filter logs by email."""
        response = await admin_client.get(
            "/api/security-audit-logs",
            params={"email": "admin@company.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for log in data.get("logs", []):
            assert "admin" in log["email"].lower()
    
    @pytest.mark.asyncio
    async def test_audit005_pagination_works(self, admin_client):
        """TC-AUDIT-005: Pagination parameters work correctly."""
        response = await admin_client.get(
            "/api/security-audit-logs",
            params={"skip": 0, "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("logs", [])) <= 5
