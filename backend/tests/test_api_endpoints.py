import uuid
from fastapi.testclient import TestClient
from app.main import app

def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "NEXUS AI" in data["application"]
        assert "chat_model" in data

def test_project_lifecycle_and_isolation():
    with TestClient(app) as client:
        # Create Project 1
        p1_name = f"Workspace Alpha {uuid.uuid4().hex[:6]}"
        res1 = client.post("/api/projects", json={"name": p1_name, "description": "Primary workspace"})
        assert res1.status_code == 200
        p1_id = res1.json()["id"]

        # Create Project 2
        p2_name = f"Workspace Beta {uuid.uuid4().hex[:6]}"
        res2 = client.post("/api/projects", json={"name": p2_name, "description": "Secondary workspace"})
        assert res2.status_code == 200
        p2_id = res2.json()["id"]

        # Verify both exist in list
        list_res = client.get("/api/projects")
        assert list_res.status_code == 200
        project_ids = [p["id"] for p in list_res.json()]
        assert p1_id in project_ids
        assert p2_id in project_ids

        # Datasets for p1 should be empty and isolated from p2
        d1_res = client.get(f"/api/projects/{p1_id}/datasets")
        assert d1_res.status_code == 200
        assert d1_res.json() == []

        # Conversations for p1 should be isolated
        c1_res = client.get(f"/api/projects/{p1_id}/conversations")
        assert c1_res.status_code == 200
        assert c1_res.json() == []

        # Clean up projects
        client.delete(f"/api/projects/{p1_id}")
        client.delete(f"/api/projects/{p2_id}")
