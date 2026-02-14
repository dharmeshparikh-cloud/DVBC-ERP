"""
Tests for Project Roadmap and Consultant Performance features.
- Roadmap CRUD: POST /roadmaps, GET /roadmaps, GET /roadmaps/{id}, PATCH /roadmaps/{id}/items/{item_id}/status, POST /roadmaps/{id}/submit-to-client
- Performance Metrics: POST /performance-metrics, POST /performance-metrics/{id}/approve, POST /performance-metrics/{id}/reject, Non-admin 403 test
- Performance Scores: POST /performance-scores, GET /performance-scores, GET /performance-scores/summary
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
MANAGER_EMAIL = "manager@company.com"
MANAGER_PASSWORD = "manager123"

@pytest.fixture(scope="module")
def admin_token():
    """Get admin token for authenticated tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def manager_token():
    """Get manager token for non-admin tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def manager_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def test_project(admin_headers):
    """Create or get a project for testing"""
    # First try to get existing projects
    response = requests.get(f"{BASE_URL}/api/projects", headers=admin_headers)
    assert response.status_code == 200
    projects = response.json()
    
    if projects:
        return projects[0]  # Use first available project
    
    # If no project exists, create one
    project_data = {
        "name": "TEST_Roadmap_Project",
        "client_name": "TEST Client",
        "start_date": "2025-01-01T00:00:00Z",
        "project_type": "mixed"
    }
    response = requests.post(f"{BASE_URL}/api/projects", headers=admin_headers, json=project_data)
    assert response.status_code == 200
    return response.json()

@pytest.fixture(scope="module")
def test_consultant(admin_headers):
    """Get a consultant user for scoring tests"""
    response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    
    # Find any user to rate (preferably a consultant)
    consultant = next((u for u in users if u.get("role") in ["consultant", "lean_consultant", "senior_consultant"]), None)
    if not consultant and users:
        consultant = users[0]  # Fall back to any user
    return consultant


class TestProjectRoadmap:
    """Tests for Project Roadmap feature"""
    
    def test_create_roadmap(self, admin_headers, test_project):
        """POST /api/roadmaps creates a project roadmap with monthly phases and items"""
        roadmap_data = {
            "project_id": test_project["id"],
            "title": "TEST_Q1 Roadmap",
            "phases": [
                {
                    "month": "2025-01",
                    "title": "Discovery Phase",
                    "items": [
                        {"title": "Stakeholder Interviews", "assigned_to": "Admin Demo", "status": "not_started", "due_date": "2025-01-15"},
                        {"title": "Current State Analysis", "assigned_to": "Admin Demo", "status": "not_started", "due_date": "2025-01-20"}
                    ]
                },
                {
                    "month": "2025-02",
                    "title": "Design Phase",
                    "items": [
                        {"title": "Solution Design", "assigned_to": "Admin Demo", "status": "not_started", "due_date": "2025-02-10"}
                    ]
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/api/roadmaps", headers=admin_headers, json=roadmap_data)
        
        assert response.status_code == 200, f"Create roadmap failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["title"] == "TEST_Q1 Roadmap"
        assert data["project_id"] == test_project["id"]
        assert len(data.get("phases", [])) == 2
        assert data["status"] == "draft"
        assert data["submitted_to_client"] == False
        
        # Verify phases have IDs
        for phase in data["phases"]:
            assert "id" in phase
            for item in phase.get("items", []):
                assert "id" in item
                assert item.get("status") == "not_started"
        
        print(f"SUCCESS: Created roadmap with ID {data['id']}")
        return data["id"]
    
    def test_get_roadmaps_list(self, admin_headers):
        """GET /api/roadmaps returns list of roadmaps"""
        response = requests.get(f"{BASE_URL}/api/roadmaps", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Found {len(data)} roadmaps")
    
    def test_get_roadmaps_filtered_by_project(self, admin_headers, test_project):
        """GET /api/roadmaps?project_id= returns filtered list"""
        response = requests.get(f"{BASE_URL}/api/roadmaps", headers=admin_headers, params={"project_id": test_project["id"]})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for rm in data:
            assert rm.get("project_id") == test_project["id"]
        print(f"SUCCESS: Filtered roadmaps for project, found {len(data)}")
    
    def test_get_roadmap_detail(self, admin_headers):
        """GET /api/roadmaps/{id} returns roadmap detail with phases and items"""
        # First get a roadmap
        response = requests.get(f"{BASE_URL}/api/roadmaps", headers=admin_headers)
        assert response.status_code == 200
        roadmaps = response.json()
        
        if not roadmaps:
            pytest.skip("No roadmaps available to test detail view")
        
        roadmap_id = roadmaps[0]["id"]
        response = requests.get(f"{BASE_URL}/api/roadmaps/{roadmap_id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == roadmap_id
        assert "phases" in data
        assert "project_name" in data
        print(f"SUCCESS: Retrieved roadmap detail for {data.get('title')}")
    
    def test_update_roadmap_item_status(self, admin_headers):
        """PATCH /api/roadmaps/{id}/items/{item_id}/status updates item status"""
        # Get a roadmap with items
        response = requests.get(f"{BASE_URL}/api/roadmaps", headers=admin_headers)
        assert response.status_code == 200
        roadmaps = response.json()
        
        # Find a roadmap with items
        roadmap = None
        item_id = None
        for rm in roadmaps:
            for phase in rm.get("phases", []):
                if phase.get("items"):
                    roadmap = rm
                    item_id = phase["items"][0]["id"]
                    break
            if item_id:
                break
        
        if not roadmap or not item_id:
            pytest.skip("No roadmap with items found to test status update")
        
        # Update status to in_progress
        response = requests.patch(
            f"{BASE_URL}/api/roadmaps/{roadmap['id']}/items/{item_id}/status",
            headers=admin_headers,
            json={"status": "in_progress"}
        )
        
        assert response.status_code == 200
        assert response.json().get("message") == "Item status updated"
        
        # Verify change persisted
        response = requests.get(f"{BASE_URL}/api/roadmaps/{roadmap['id']}", headers=admin_headers)
        assert response.status_code == 200
        updated_roadmap = response.json()
        
        found = False
        for phase in updated_roadmap.get("phases", []):
            for item in phase.get("items", []):
                if item["id"] == item_id:
                    assert item["status"] == "in_progress"
                    found = True
                    break
        
        assert found, "Item not found after update"
        print(f"SUCCESS: Updated item status to 'in_progress'")
    
    def test_submit_roadmap_to_client(self, admin_headers, test_project):
        """POST /api/roadmaps/{id}/submit-to-client submits roadmap to client"""
        # Create a new roadmap for this test
        roadmap_data = {
            "project_id": test_project["id"],
            "title": "TEST_Submit_Roadmap",
            "phases": [{"month": "2025-03", "title": "Test Phase", "items": [{"title": "Test Item"}]}]
        }
        create_response = requests.post(f"{BASE_URL}/api/roadmaps", headers=admin_headers, json=roadmap_data)
        assert create_response.status_code == 200
        roadmap_id = create_response.json()["id"]
        
        # Submit to client
        response = requests.post(f"{BASE_URL}/api/roadmaps/{roadmap_id}/submit-to-client", headers=admin_headers)
        
        assert response.status_code == 200
        assert response.json().get("message") == "Roadmap submitted to client"
        
        # Verify status changed
        detail_response = requests.get(f"{BASE_URL}/api/roadmaps/{roadmap_id}", headers=admin_headers)
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["submitted_to_client"] == True
        assert detail["status"] == "submitted_to_client"
        print(f"SUCCESS: Roadmap submitted to client (notification queued - MOCKED)")
    
    def test_roadmap_not_found(self, admin_headers):
        """GET /api/roadmaps/{invalid_id} returns 404"""
        response = requests.get(f"{BASE_URL}/api/roadmaps/invalid-roadmap-id-123", headers=admin_headers)
        assert response.status_code == 404


class TestPerformanceMetrics:
    """Tests for Performance Metrics configuration feature"""
    
    def test_create_performance_metrics(self, admin_headers, test_project):
        """POST /api/performance-metrics creates metrics config (pending approval)"""
        metrics_data = {
            "project_id": test_project["id"],
            "project_name": test_project.get("name", "Test Project"),
            "metrics": [
                {"name": "SOW Timely Delivery", "key": "sow_delivery", "weight": 20, "description": "SOW items delivered on time"},
                {"name": "Roadmap Achievement", "key": "roadmap_achievement", "weight": 20, "description": "Roadmap milestones completed"},
                {"name": "Records Timeliness", "key": "records_timeliness", "weight": 15, "description": "Timely update of records"},
                {"name": "SOW Quality Score", "key": "sow_quality", "weight": 25, "description": "Quality rating"},
                {"name": "Meeting Adherence", "key": "meeting_adherence", "weight": 20, "description": "Meeting schedule adherence"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/performance-metrics", headers=admin_headers, json=metrics_data)
        
        assert response.status_code == 200, f"Create metrics failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["status"] == "pending_approval"
        assert len(data.get("metrics", [])) == 5
        
        # Verify weights sum to 100
        total_weight = sum(m.get("weight", 0) for m in data["metrics"])
        assert total_weight == 100
        
        print(f"SUCCESS: Created performance metrics config (pending approval) with ID {data['id']}")
        return data["id"]
    
    def test_get_performance_metrics_list(self, admin_headers):
        """GET /api/performance-metrics returns list"""
        response = requests.get(f"{BASE_URL}/api/performance-metrics", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Found {len(data)} performance metrics configs")
    
    def test_get_metrics_filtered_by_status(self, admin_headers):
        """GET /api/performance-metrics?status= filters by status"""
        response = requests.get(f"{BASE_URL}/api/performance-metrics", headers=admin_headers, params={"status": "pending_approval"})
        
        assert response.status_code == 200
        data = response.json()
        for cfg in data:
            assert cfg.get("status") == "pending_approval"
        print(f"SUCCESS: Filtered metrics by status 'pending_approval', found {len(data)}")
    
    def test_approve_metrics_admin(self, admin_headers, test_project):
        """POST /api/performance-metrics/{id}/approve (admin only) approves config"""
        # Create a new metrics config to approve
        metrics_data = {
            "project_id": test_project["id"],
            "project_name": test_project.get("name", "Test Project"),
            "metrics": [
                {"name": "Metric A", "weight": 50, "description": "Test metric A"},
                {"name": "Metric B", "weight": 50, "description": "Test metric B"}
            ]
        }
        create_response = requests.post(f"{BASE_URL}/api/performance-metrics", headers=admin_headers, json=metrics_data)
        assert create_response.status_code == 200
        config_id = create_response.json()["id"]
        
        # Approve as admin
        response = requests.post(f"{BASE_URL}/api/performance-metrics/{config_id}/approve", headers=admin_headers)
        
        assert response.status_code == 200
        assert response.json().get("message") == "Performance metrics approved"
        
        # Verify status changed
        detail_response = requests.get(f"{BASE_URL}/api/performance-metrics/{config_id}", headers=admin_headers)
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["status"] == "approved"
        assert detail["approved_by"] is not None
        print(f"SUCCESS: Admin approved metrics config")
    
    def test_reject_metrics_admin(self, admin_headers, test_project):
        """POST /api/performance-metrics/{id}/reject (admin only) rejects config"""
        # Create another metrics config to reject
        metrics_data = {
            "project_id": test_project["id"],
            "project_name": "Reject Test",
            "metrics": [{"name": "Reject Metric", "weight": 100, "description": "To be rejected"}]
        }
        create_response = requests.post(f"{BASE_URL}/api/performance-metrics", headers=admin_headers, json=metrics_data)
        assert create_response.status_code == 200
        config_id = create_response.json()["id"]
        
        # Reject as admin
        response = requests.post(f"{BASE_URL}/api/performance-metrics/{config_id}/reject", headers=admin_headers)
        
        assert response.status_code == 200
        assert response.json().get("message") == "Performance metrics rejected"
        
        # Verify status changed
        detail_response = requests.get(f"{BASE_URL}/api/performance-metrics/{config_id}", headers=admin_headers)
        assert detail_response.status_code == 200
        assert detail_response.json()["status"] == "rejected"
        print(f"SUCCESS: Admin rejected metrics config")
    
    def test_non_admin_cannot_approve(self, manager_headers, admin_headers, test_project):
        """Non-admin cannot approve metrics (403)"""
        # Create a config as admin
        metrics_data = {
            "project_id": test_project["id"],
            "project_name": "Non-Admin Test",
            "metrics": [{"name": "Test", "weight": 100, "description": "Test"}]
        }
        create_response = requests.post(f"{BASE_URL}/api/performance-metrics", headers=admin_headers, json=metrics_data)
        assert create_response.status_code == 200
        config_id = create_response.json()["id"]
        
        # Try to approve as manager (non-admin)
        response = requests.post(f"{BASE_URL}/api/performance-metrics/{config_id}/approve", headers=manager_headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        assert "admin" in response.json().get("detail", "").lower() or "Admin" in response.json().get("detail", "")
        print(f"SUCCESS: Non-admin correctly denied approval (403)")


class TestPerformanceScores:
    """Tests for Performance Scoring feature"""
    
    def get_or_create_approved_config(self, admin_headers, test_project):
        """Helper: Get or create approved metrics config for a project"""
        # Check if approved config already exists for this project
        response = requests.get(
            f"{BASE_URL}/api/performance-metrics",
            headers=admin_headers,
            params={"project_id": test_project["id"], "status": "approved"}
        )
        assert response.status_code == 200
        configs = response.json()
        
        if configs:
            return configs[0]
        
        # Create new config
        metrics_data = {
            "project_id": test_project["id"],
            "project_name": test_project.get("name", "Score Test Project"),
            "metrics": [
                {"name": "SOW Delivery", "key": "sow_delivery", "weight": 30, "description": "Delivery metric"},
                {"name": "Quality", "key": "quality", "weight": 40, "description": "Quality metric"},
                {"name": "Timeliness", "key": "timeliness", "weight": 30, "description": "Time metric"}
            ]
        }
        create_response = requests.post(f"{BASE_URL}/api/performance-metrics", headers=admin_headers, json=metrics_data)
        assert create_response.status_code == 200
        config_id = create_response.json()["id"]
        
        # Approve it
        approve_response = requests.post(f"{BASE_URL}/api/performance-metrics/{config_id}/approve", headers=admin_headers)
        assert approve_response.status_code == 200
        
        # Return the full config
        detail_response = requests.get(f"{BASE_URL}/api/performance-metrics/{config_id}", headers=admin_headers)
        assert detail_response.status_code == 200
        return detail_response.json()
    
    def test_create_performance_score(self, admin_headers, test_project, test_consultant, approved_metrics_config):
        """POST /api/performance-scores creates weighted consultant score"""
        if not test_consultant:
            pytest.skip("No consultant user found for scoring test")
        
        metrics = approved_metrics_config.get("metrics", [])
        if len(metrics) == 0:
            pytest.skip("No metrics in approved config")
        
        # Build scores dynamically based on available metrics
        scores_data = []
        expected_weighted = 0
        total_weight = 0
        for i, metric in enumerate(metrics):
            score_value = 85 + (i * 5) % 15  # Vary scores: 85, 90, 80, etc.
            scores_data.append({
                "metric_id": metric["id"],
                "metric_name": metric["name"],
                "score": score_value,
                "comments": f"Score for {metric['name']}"
            })
            expected_weighted += score_value * metric.get("weight", 0)
            total_weight += metric.get("weight", 0)
        
        score_data = {
            "project_id": test_project["id"],
            "consultant_id": test_consultant["id"],
            "month": "2025-01",
            "scores": scores_data
        }
        response = requests.post(f"{BASE_URL}/api/performance-scores", headers=admin_headers, json=score_data)
        
        assert response.status_code == 200, f"Create score failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert "overall_score" in data
        assert data["consultant_id"] == test_consultant["id"]
        assert data["month"] == "2025-01"
        
        # Verify weighted calculation
        if total_weight > 0:
            expected = expected_weighted / total_weight
            assert abs(data["overall_score"] - expected) < 2, f"Expected ~{expected}, got {data['overall_score']}"
        
        print(f"SUCCESS: Created performance score with overall_score={data['overall_score']}")
    
    def test_get_performance_scores_list(self, admin_headers):
        """GET /api/performance-scores returns scores with overall_score calculated"""
        response = requests.get(f"{BASE_URL}/api/performance-scores", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify each score has overall_score
        for score in data:
            assert "overall_score" in score
            assert "consultant_id" in score
            assert "month" in score
        
        print(f"SUCCESS: Found {len(data)} performance scores")
    
    def test_get_performance_scores_filtered(self, admin_headers, test_project):
        """GET /api/performance-scores?project_id= returns filtered scores"""
        response = requests.get(
            f"{BASE_URL}/api/performance-scores",
            headers=admin_headers,
            params={"project_id": test_project["id"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        for score in data:
            assert score.get("project_id") == test_project["id"]
        print(f"SUCCESS: Filtered scores by project, found {len(data)}")
    
    def test_get_performance_summary(self, admin_headers):
        """GET /api/performance-scores/summary returns aggregated per-consultant summary"""
        response = requests.get(f"{BASE_URL}/api/performance-scores/summary", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify summary structure
        for summary in data:
            assert "consultant_id" in summary
            assert "consultant_name" in summary
            assert "months_rated" in summary
            assert "avg_score" in summary
        
        print(f"SUCCESS: Got summary for {len(data)} consultants")
    
    def test_create_score_requires_approved_metrics(self, admin_headers, test_project, test_consultant):
        """POST /api/performance-scores fails if no approved metrics for project"""
        # Create a new project without metrics
        new_project_data = {
            "name": "TEST_NoMetrics_Project",
            "client_name": "No Metrics Client",
            "start_date": "2025-01-01T00:00:00Z"
        }
        proj_response = requests.post(f"{BASE_URL}/api/projects", headers=admin_headers, json=new_project_data)
        assert proj_response.status_code == 200
        new_project_id = proj_response.json()["id"]
        
        # Try to create score without approved metrics
        score_data = {
            "project_id": new_project_id,
            "consultant_id": test_consultant["id"] if test_consultant else "test-id",
            "month": "2025-01",
            "scores": []
        }
        response = requests.post(f"{BASE_URL}/api/performance-scores", headers=admin_headers, json=score_data)
        
        assert response.status_code == 400
        assert "approved" in response.json().get("detail", "").lower()
        print(f"SUCCESS: Correctly rejected score creation without approved metrics")


class TestKanbanStatusValues:
    """Verify the 4 Kanban column statuses work correctly"""
    
    def test_all_status_values(self, admin_headers, test_project):
        """Verify all 4 statuses: not_started, in_progress, completed, delayed"""
        # Create roadmap with items in different statuses
        roadmap_data = {
            "project_id": test_project["id"],
            "title": "TEST_Kanban_Status_Roadmap",
            "phases": [{
                "month": "2025-04",
                "title": "Kanban Test Phase",
                "items": [
                    {"title": "Not Started Item", "status": "not_started"},
                    {"title": "In Progress Item", "status": "in_progress"},
                    {"title": "Completed Item", "status": "completed"},
                    {"title": "Delayed Item", "status": "delayed"}
                ]
            }]
        }
        response = requests.post(f"{BASE_URL}/api/roadmaps", headers=admin_headers, json=roadmap_data)
        assert response.status_code == 200
        roadmap = response.json()
        
        items = roadmap["phases"][0]["items"]
        statuses = [item["status"] for item in items]
        
        assert "not_started" in statuses
        assert "in_progress" in statuses
        assert "completed" in statuses
        assert "delayed" in statuses
        
        print(f"SUCCESS: All 4 Kanban statuses verified: {statuses}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
