from __future__ import annotations

import io
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app


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
    assert any(project["id"] == project_id for project in list_payload)

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == project_id


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
        json={"name": "Updated Project", "importance_rank": 5},
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["id"] == project_id
    assert payload["name"] == "Updated Project"
    assert payload["importance_rank"] == 5

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["name"] == "Updated Project"
    assert detail_payload["importance_rank"] == 5


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
