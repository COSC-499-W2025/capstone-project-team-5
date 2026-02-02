from __future__ import annotations

import io
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.services.upload_storage import get_upload_zip_path


def _create_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


def test_upload_projects_returns_metadata() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("myproject/main.py", b"print('hello')\n"),
            ("myproject/readme.md", b"# docs\n"),
        ]
    )

    response = client.post(
        "/api/projects/upload",
        files={"file": ("sample.zip", zip_bytes, "application/zip")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "sample.zip"
    assert data["file_count"] == 2
    assert data["upload_id"]
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "myproject"
    assert data["projects"][0]["is_showcase"] is False


def test_list_and_get_project() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectA/main.py", b"print('a')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("a.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    list_response = client.get("/api/projects")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    # Ensure project is present and has showcase flag with default False.
    project_row = next(project for project in list_payload if project["id"] == project_id)
    assert project_row["is_showcase"] is False

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == project_id
    assert detail_payload["is_showcase"] is False


def test_get_project_not_found_returns_404() -> None:
    client = TestClient(app)
    response = client.get("/api/projects/99999")
    assert response.status_code == 404


def test_patch_project_updates_fields() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectB/main.py", b"print('b')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("b.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    patch_response = client.patch(
        f"/api/projects/{project_id}",
        json={
            "name": "Updated Project",
            "importance_rank": 5,
            "is_showcase": True,
        },
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["id"] == project_id
    assert payload["name"] == "Updated Project"
    assert payload["importance_rank"] == 5
    assert payload["is_showcase"] is True

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["name"] == "Updated Project"
    assert detail_payload["importance_rank"] == 5
    assert detail_payload["is_showcase"] is True


def test_patch_project_not_found_returns_404() -> None:
    client = TestClient(app)
    response = client.patch("/api/projects/99999", json={"name": "Nope"})
    assert response.status_code == 404


def test_patch_project_rejects_invalid_thumbnail() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectC/main.py", b"print('c')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("c.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    patch_response = client.patch(
        f"/api/projects/{project_id}",
        json={"thumbnail_url": "not-a-url"},
    )
    assert patch_response.status_code == 400


def test_delete_project_removes_record() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectD/main.py", b"print('d')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("d.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    delete_response = client.delete(f"/api/projects/{project_id}")
    assert delete_response.status_code == 204

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 404


def test_delete_project_not_found_returns_404() -> None:
    client = TestClient(app)
    response = client.delete("/api/projects/99999")
    assert response.status_code == 404


def test_analyze_project_updates_importance_score() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectE/main.py", b"print('e')\n"),
            ("projectE/readme.md", b"# docs\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("e.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze")
    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["id"] == project_id
    assert analyze_payload["importance_score"] is not None

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["importance_score"] is not None


def test_analyze_all_updates_all_projects() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectF/main.py", b"print('f')\n"),
            ("projectG/main.py", b"print('g')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("fg.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    project_ids = {project["id"] for project in upload_payload["projects"]}

    analyze_response = client.post("/api/projects/analyze")
    assert analyze_response.status_code == 200
    payload = analyze_response.json()

    # Check that our uploaded projects are analyzed
    analyzed_ids = {item["id"] for item in payload["analyzed"]}
    assert project_ids.issubset(analyzed_ids), (
        f"Expected projects {project_ids} to be in analyzed {analyzed_ids}"
    )
    analyzed_our_projects = [item for item in payload["analyzed"] if item["id"] in project_ids]
    assert all(item["importance_score"] is not None for item in analyzed_our_projects)

    list_response = client.get("/api/projects")
    assert list_response.status_code == 200
    all_projects = list_response.json()
    for project in all_projects:
        if project["id"] in project_ids:
            assert project["importance_score"] is not None


def test_analyze_all_reports_missing_zip() -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes(
        [
            ("projectH/main.py", b"print('h')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("h.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    project_id = upload_payload["projects"][0]["id"]
    upload_id = upload_payload["upload_id"]
    filename = upload_payload["filename"]

    zip_path = get_upload_zip_path(upload_id, filename)
    if zip_path.exists():
        zip_path.unlink()

    analyze_response = client.post("/api/projects/analyze")
    assert analyze_response.status_code == 200
    payload = analyze_response.json()

    # Check that our project is skipped (not analyzed)
    analyzed_ids = {item["id"] for item in payload["analyzed"]}
    assert project_id not in analyzed_ids, f"Project {project_id} should be skipped, not analyzed"

    # Check that our project is in the skipped list
    skipped_ids = {item["project_id"] for item in payload["skipped"]}
    assert project_id in skipped_ids, f"Project {project_id} should be in skipped list"

    # Verify the skip reason
    skipped_project = next(item for item in payload["skipped"] if item["project_id"] == project_id)
    assert "Stored upload archive not found" in skipped_project["reason"]


def test_analyze_project_ai_falls_back_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    zip_bytes = _create_zip_bytes(
        [
            ("projectI/main.py", b"print('i')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("i.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze?use_ai=true")
    assert analyze_response.status_code == 200
    payload = analyze_response.json()
    assert payload["resume_bullet_source"] == "Local"
