"""Tests for project reranking API endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, UploadRecord


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_projects(api_db: None) -> list[int]:
    """Create test projects and return their IDs."""
    with get_session() as session:
        # Create an upload record first
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=1000,
            file_count=50,
        )
        session.add(upload)
        session.flush()

        projects = [
            Project(
                upload_id=upload.id,
                name=f"Project {i}",
                rel_path=f"project{i}",
                file_count=10,
                has_git_repo=False,
                is_collaborative=False,
                importance_rank=None,
            )
            for i in range(1, 6)
        ]
        session.add_all(projects)
        session.flush()
        project_ids = [p.id for p in projects]

    return project_ids


class TestProjectReRank:
    """Tests for POST /api/projects/rerank endpoint."""

    def test_rerank_projects_success(self, client: TestClient, test_projects: list[int]) -> None:
        """Test successful reranking of multiple projects."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 3},
            {"project_id": test_projects[1], "importance_rank": 1},
            {"project_id": test_projects[2], "importance_rank": 5},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 3
        assert len(data["projects"]) == 3

        # Verify ranks were applied
        rank_map = {p["id"]: p["importance_rank"] for p in data["projects"]}
        assert rank_map[test_projects[0]] == 3
        assert rank_map[test_projects[1]] == 1
        assert rank_map[test_projects[2]] == 5

    def test_rerank_all_projects(self, client: TestClient, test_projects: list[int]) -> None:
        """Test reranking all projects in one operation."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 5},
            {"project_id": test_projects[1], "importance_rank": 4},
            {"project_id": test_projects[2], "importance_rank": 3},
            {"project_id": test_projects[3], "importance_rank": 2},
            {"project_id": test_projects[4], "importance_rank": 1},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 5

    def test_rerank_single_project(self, client: TestClient, test_projects: list[int]) -> None:
        """Test reranking a single project."""
        rankings = [{"project_id": test_projects[0], "importance_rank": 10}]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 1
        assert data["projects"][0]["importance_rank"] == 10

    def test_rerank_persists_to_database(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that rank updates are persisted to the database."""
        rankings = [{"project_id": test_projects[0], "importance_rank": 7}]

        client.post("/api/projects/rerank", json={"rankings": rankings})

        # Verify persistence by fetching the project
        response = client.get(f"/api/projects/{test_projects[0]}")
        assert response.status_code == 200
        assert response.json()["importance_rank"] == 7

    def test_rerank_empty_list_fails(self, client: TestClient) -> None:
        """Test that empty rankings list returns 400."""
        response = client.post("/api/projects/rerank", json={"rankings": []})

        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_rerank_duplicate_ranks_fails(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that duplicate ranks are rejected."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 5},
            {"project_id": test_projects[1], "importance_rank": 5},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 400
        assert "Duplicate ranks" in response.json()["detail"]

    def test_rerank_negative_rank_fails(self, client: TestClient, test_projects: list[int]) -> None:
        """Test that negative ranks are rejected."""
        rankings = [{"project_id": test_projects[0], "importance_rank": -1}]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 400
        assert "positive integers" in response.json()["detail"]

    def test_rerank_zero_rank_fails(self, client: TestClient, test_projects: list[int]) -> None:
        """Test that zero rank is rejected."""
        rankings = [{"project_id": test_projects[0], "importance_rank": 0}]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 400
        assert "positive integers" in response.json()["detail"]

    def test_rerank_nonexistent_project_fails(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that reranking non-existent project returns 404."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 1},
            {"project_id": 99999, "importance_rank": 2},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        assert "99999" in response.json()["detail"]

    def test_rerank_duplicate_project_ids_fails(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that duplicate project IDs are rejected."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 1},
            {"project_id": test_projects[0], "importance_rank": 2},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 400
        assert "Duplicate project IDs" in response.json()["detail"]

    def test_rerank_large_rank_values(self, client: TestClient, test_projects: list[int]) -> None:
        """Test that large rank values are accepted."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 1000},
            {"project_id": test_projects[1], "importance_rank": 9999},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 200
        data = response.json()
        rank_map = {p["id"]: p["importance_rank"] for p in data["projects"]}
        assert rank_map[test_projects[0]] == 1000
        assert rank_map[test_projects[1]] == 9999

    def test_rerank_non_sequential_ranks(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that non-sequential ranks are allowed (gaps are OK)."""
        rankings = [
            {"project_id": test_projects[0], "importance_rank": 1},
            {"project_id": test_projects[1], "importance_rank": 10},
            {"project_id": test_projects[2], "importance_rank": 100},
        ]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 200
        assert response.json()["updated"] == 3

    def test_rerank_overwrites_existing_ranks(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that reranking overwrites existing importance_rank values."""
        # Set initial ranks
        initial_rankings = [
            {"project_id": test_projects[0], "importance_rank": 5},
            {"project_id": test_projects[1], "importance_rank": 10},
        ]
        client.post("/api/projects/rerank", json={"rankings": initial_rankings})

        # Overwrite with new ranks
        new_rankings = [
            {"project_id": test_projects[0], "importance_rank": 20},
            {"project_id": test_projects[1], "importance_rank": 30},
        ]
        response = client.post("/api/projects/rerank", json={"rankings": new_rankings})

        assert response.status_code == 200
        rank_map = {p["id"]: p["importance_rank"] for p in response.json()["projects"]}
        assert rank_map[test_projects[0]] == 20
        assert rank_map[test_projects[1]] == 30

    def test_rerank_partial_update_leaves_others_unchanged(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that reranking some projects doesn't affect others."""
        # Set initial ranks for all
        initial_rankings = [
            {"project_id": test_projects[0], "importance_rank": 1},
            {"project_id": test_projects[1], "importance_rank": 2},
            {"project_id": test_projects[2], "importance_rank": 3},
        ]
        client.post("/api/projects/rerank", json={"rankings": initial_rankings})

        # Update only first project
        new_rankings = [{"project_id": test_projects[0], "importance_rank": 100}]
        client.post("/api/projects/rerank", json={"rankings": new_rankings})

        # Verify others unchanged
        response = client.get(f"/api/projects/{test_projects[1]}")
        assert response.json()["importance_rank"] == 2

        response = client.get(f"/api/projects/{test_projects[2]}")
        assert response.json()["importance_rank"] == 3

    def test_rerank_response_includes_all_project_fields(
        self, client: TestClient, test_projects: list[int]
    ) -> None:
        """Test that response includes complete project summaries."""
        rankings = [{"project_id": test_projects[0], "importance_rank": 1}]

        response = client.post("/api/projects/rerank", json={"rankings": rankings})

        assert response.status_code == 200
        project = response.json()["projects"][0]

        # Verify all expected fields are present
        assert "id" in project
        assert "name" in project
        assert "rel_path" in project
        assert "file_count" in project
        assert "has_git_repo" in project
        assert "importance_rank" in project
        assert "created_at" in project
        assert "updated_at" in project
