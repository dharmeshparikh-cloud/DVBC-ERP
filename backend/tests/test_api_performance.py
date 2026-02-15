"""
API Performance Benchmarking Test Suite
Tests: Response times, concurrent load handling, rate limiting
"""

import pytest
import httpx
import time
import asyncio
from statistics import mean, stdev


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical API endpoints."""
    
    @pytest.mark.asyncio
    async def test_perf001_login_response_time(self, api_url):
        """TC-PERF-001: Login endpoint response time."""
        times = []
        
        for _ in range(5):
            start = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{api_url}/api/auth/login",
                    json={"email": "admin@company.com", "password": "admin123"}
                )
            times.append(time.time() - start)
        
        avg_time = mean(times)
        print(f"\nLogin avg response time: {avg_time:.3f}s")
        
        # Should respond within 2 seconds
        assert avg_time < 2.0, f"Login too slow: {avg_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_perf002_leads_list_response_time(self, admin_client):
        """TC-PERF-002: Leads list endpoint response time."""
        times = []
        
        for _ in range(5):
            start = time.time()
            await admin_client.get("/api/leads")
            times.append(time.time() - start)
        
        avg_time = mean(times)
        print(f"\nLeads list avg response time: {avg_time:.3f}s")
        
        assert avg_time < 3.0, f"Leads list too slow: {avg_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_perf003_dashboard_stats_response_time(self, admin_client):
        """TC-PERF-003: Dashboard stats response time."""
        times = []
        
        for _ in range(5):
            start = time.time()
            await admin_client.get("/api/stats/dashboard")
            times.append(time.time() - start)
        
        avg_time = mean(times)
        print(f"\nDashboard stats avg response time: {avg_time:.3f}s")
        
        assert avg_time < 2.0, f"Dashboard too slow: {avg_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_perf004_employees_list_response_time(self, admin_client):
        """TC-PERF-004: Employees list response time."""
        times = []
        
        for _ in range(5):
            start = time.time()
            await admin_client.get("/api/employees")
            times.append(time.time() - start)
        
        avg_time = mean(times)
        print(f"\nEmployees list avg response time: {avg_time:.3f}s")
        
        assert avg_time < 3.0, f"Employees list too slow: {avg_time:.3f}s"


class TestConcurrentLoad:
    """Concurrent load handling tests."""
    
    @pytest.mark.asyncio
    async def test_load001_concurrent_logins(self, api_url):
        """TC-LOAD-001: Handle concurrent login requests."""
        async def single_login():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/api/auth/login",
                    json={"email": "admin@company.com", "password": "admin123"}
                )
                return response.status_code
        
        # Run 10 concurrent logins
        tasks = [single_login() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r == 200)
        print(f"\nConcurrent logins: {success_count}/10 successful")
        
        # At least 80% should succeed
        assert success_count >= 8
    
    @pytest.mark.asyncio
    async def test_load002_concurrent_reads(self, api_url, token_manager):
        """TC-LOAD-002: Handle concurrent read requests."""
        token = await token_manager.get_token("admin")
        
        async def single_read():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_url}/api/leads",
                    headers={"Authorization": f"Bearer {token}"}
                )
                return response.status_code
        
        # Run 20 concurrent reads
        tasks = [single_read() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r == 200)
        print(f"\nConcurrent reads: {success_count}/20 successful")
        
        assert success_count >= 18
    
    @pytest.mark.asyncio
    async def test_load003_mixed_operations(self, api_url, token_manager, test_data):
        """TC-LOAD-003: Handle mixed read/write operations."""
        token = await token_manager.get_token("admin")
        
        async def read_op():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{api_url}/api/leads",
                    headers={"Authorization": f"Bearer {token}"}
                )
                return ("read", response.status_code)
        
        async def write_op():
            lead_data = test_data.lead()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/api/leads",
                    json=lead_data,
                    headers={"Authorization": f"Bearer {token}"}
                )
                return ("write", response.status_code)
        
        # Mix of reads and writes
        tasks = [read_op() if i % 3 == 0 else write_op() for i in range(15)]
        results = await asyncio.gather(*tasks)
        
        read_success = sum(1 for op, code in results if op == "read" and code == 200)
        write_success = sum(1 for op, code in results if op == "write" and code == 200)
        
        print(f"\nMixed ops - Reads: {read_success}, Writes: {write_success}")
        
        # Most operations should succeed
        total_success = read_success + write_success
        assert total_success >= 12


class TestResponseConsistency:
    """Tests for response consistency and reliability."""
    
    @pytest.mark.asyncio
    async def test_consist001_repeated_reads_same_result(self, admin_client):
        """TC-CONSIST-001: Repeated reads return consistent data."""
        responses = []
        
        for _ in range(3):
            response = await admin_client.get("/api/stats/dashboard")
            if response.status_code == 200:
                responses.append(response.json())
        
        # All responses should have same structure
        if len(responses) >= 2:
            keys1 = set(responses[0].keys())
            keys2 = set(responses[1].keys())
            assert keys1 == keys2, "Response structure should be consistent"
    
    @pytest.mark.asyncio
    async def test_consist002_pagination_stability(self, admin_client):
        """TC-CONSIST-002: Pagination returns stable results."""
        # Get first page
        response1 = await admin_client.get("/api/leads")
        
        # Get same page again
        response2 = await admin_client.get("/api/leads")
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            
            # Same number of results
            assert len(data1) == len(data2)


class TestResourceLimits:
    """Tests for resource limit handling."""
    
    @pytest.mark.asyncio
    async def test_limit001_large_payload_handling(self, admin_client, test_data):
        """TC-LIMIT-001: Large payload is handled gracefully."""
        # Create lead with very long notes
        lead_data = test_data.lead({"notes": "A" * 50000})
        response = await admin_client.post("/api/leads", json=lead_data)
        
        # Should handle gracefully (accept or reject, not crash)
        assert response.status_code in [200, 400, 413, 422]
    
    @pytest.mark.asyncio
    async def test_limit002_many_query_params(self, admin_client):
        """TC-LIMIT-002: Many query parameters handled."""
        params = {f"param_{i}": f"value_{i}" for i in range(50)}
        response = await admin_client.get("/api/leads", params=params)
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 414]
    
    @pytest.mark.asyncio
    async def test_limit003_deeply_nested_json(self, admin_client, test_data):
        """TC-LIMIT-003: Deeply nested JSON handled."""
        def create_nested(depth):
            if depth == 0:
                return "value"
            return {"nested": create_nested(depth - 1)}
        
        lead_data = test_data.lead({"metadata": create_nested(50)})
        response = await admin_client.post("/api/leads", json=lead_data)
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]


class TestEndpointAvailability:
    """Tests to verify all critical endpoints are available."""
    
    @pytest.mark.asyncio
    async def test_avail001_auth_endpoints(self, api_url):
        """TC-AVAIL-001: Auth endpoints are available."""
        endpoints = [
            ("/api/auth/login", "POST"),
            ("/api/auth/register", "POST"),
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for path, method in endpoints:
                if method == "POST":
                    response = await client.post(
                        f"{api_url}{path}",
                        json={}
                    )
                else:
                    response = await client.get(f"{api_url}{path}")
                
                # Should respond (not 404 for endpoint not found)
                # 422/400 is okay (validation error means endpoint exists)
                assert response.status_code != 404, f"{path} should exist"
    
    @pytest.mark.asyncio
    async def test_avail002_protected_endpoints(self, admin_client):
        """TC-AVAIL-002: Protected endpoints are available."""
        endpoints = [
            "/api/leads",
            "/api/employees",
            "/api/projects",
            "/api/clients",
            "/api/expenses",
            "/api/meetings",
            "/api/users",
            "/api/roles",
        ]
        
        for endpoint in endpoints:
            response = await admin_client.get(endpoint)
            assert response.status_code == 200, f"{endpoint} should be accessible"


class TestHealthCheck:
    """Health check and status endpoint tests."""
    
    @pytest.mark.asyncio
    async def test_health001_api_responsive(self, api_url):
        """TC-HEALTH-001: API is responsive."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{api_url}/api/")
        
        # Some response (even 404) means server is up
        assert response.status_code < 500
    
    @pytest.mark.asyncio
    async def test_health002_database_connected(self, admin_client):
        """TC-HEALTH-002: Database is connected (via data fetch)."""
        response = await admin_client.get("/api/stats/dashboard")
        
        # Successful stats retrieval means DB is working
        assert response.status_code == 200
