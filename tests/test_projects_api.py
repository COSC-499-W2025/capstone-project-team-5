from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ArtifactSource, CodeAnalysis, Project, UploadRecord
from capstone_project_team_5.services.content_store import get_manifests_root, get_objects_root
from capstone_project_team_5.services.upload_storage import get_upload_zip_path


def _create_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake"


def _upload_single_project(client: TestClient, name: str) -> int:
    zip_bytes = _create_zip_bytes([(f"{name}/main.py", b"print('hello')\n")])
    response = client.post(
        "/api/projects/upload",
        files={"file": (f"{name}.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 201
    return response.json()["projects"][0]["id"]


def test_upload_projects_returns_metadata(api_db: None) -> None:
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
    assert data["created_count"] == 1
    assert data["merged_count"] == 0
    assert data["actions"][0]["action"] == "created"


def test_list_projects_pagination(api_db: None) -> None:
    """Test that GET /api/projects returns a paginated response."""
    client = TestClient(app)

    # Create some projects
    for name in ["project_a", "project_b", "project_c"]:
        zip_bytes = _create_zip_bytes([(f"{name}/main.py", b"print('x')\n")])
        response = client.post(
            "/api/projects/upload",
            files={"file": (f"{name}.zip", zip_bytes, "application/zip")},
        )
        assert response.status_code == 201

    # Test default pagination
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 3
    assert data["pagination"]["total"] == 3
    assert data["pagination"]["limit"] == 50  # default
    assert data["pagination"]["offset"] == 0
    assert data["pagination"]["has_more"] is False

    # Test custom pagination params
    response = client.get("/api/projects?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["has_more"] is True

    # Test offset
    response = client.get("/api/projects?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["pagination"]["offset"] == 2
    assert data["pagination"]["has_more"] is False


def test_list_projects_invalid_pagination_params(api_db: None) -> None:
    """Test that invalid pagination parameters return 422."""
    client = TestClient(app)
    assert client.get("/api/projects?limit=0").status_code == 422
    assert client.get("/api/projects?limit=-1").status_code == 422
    assert client.get("/api/projects?offset=-1").status_code == 422
    assert client.get("/api/projects?limit=101").status_code == 422


def test_list_projects_empty_database(api_db: None) -> None:
    """Test pagination returns correct response when no projects exist."""
    client = TestClient(app)

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []
    assert data["pagination"]["total"] == 0
    assert data["pagination"]["limit"] == 50
    assert data["pagination"]["offset"] == 0
    assert data["pagination"]["has_more"] is False


def test_list_projects_offset_beyond_total(api_db: None) -> None:
    """Test pagination when offset >= total returns empty items."""
    client = TestClient(app)

    # Create 2 projects
    for name in ["proj_offset_a", "proj_offset_b"]:
        zip_bytes = _create_zip_bytes([(f"{name}/main.py", b"print('x')\n")])
        response = client.post(
            "/api/projects/upload",
            files={"file": (f"{name}.zip", zip_bytes, "application/zip")},
        )
        assert response.status_code == 201

    # Request with offset beyond total
    response = client.get("/api/projects?offset=100")
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []
    assert data["pagination"]["total"] == 2
    assert data["pagination"]["offset"] == 100
    assert data["pagination"]["has_more"] is False


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
    list_data = list_response.json()
    list_payload = list_data["items"]
    assert "pagination" in list_data
    # Ensure project is present and has showcase flag with default False.
    project_row = next(project for project in list_payload if project["id"] == project_id)
    listed = next(project for project in list_payload if project["id"] == project_id)
    assert project_row["is_showcase"] is False
    assert listed["has_thumbnail"] is False
    assert listed["thumbnail_url"] is None

    detail_response = client.get(f"/api/projects/{project_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == project_id
    assert detail_payload["is_showcase"] is False
    assert detail_payload["has_thumbnail"] is False
    assert detail_payload["thumbnail_url"] is None


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


def test_patch_project_rejects_thumbnail_url_field() -> None:
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
    assert patch_response.status_code == 422


def test_thumbnail_get_missing_returns_404() -> None:
    client = TestClient(app)
    project_id = _upload_single_project(client, "thumb_missing")

    response = client.get(f"/api/projects/{project_id}/thumbnail")
    assert response.status_code == 404


def test_thumbnail_upload_and_get() -> None:
    client = TestClient(app)
    project_id = _upload_single_project(client, "thumb_upload")

    upload_response = client.put(
        f"/api/projects/{project_id}/thumbnail",
        files={"file": ("thumb.png", PNG_BYTES, "image/png")},
    )
    assert upload_response.status_code == 204

    get_response = client.get(f"/api/projects/{project_id}/thumbnail")
    assert get_response.status_code == 200
    assert get_response.headers["content-type"].startswith("image/png")
    assert get_response.content

    detail_response = client.get(f"/api/projects/{project_id}")
    detail_payload = detail_response.json()
    assert detail_payload["has_thumbnail"] is True
    assert detail_payload["thumbnail_url"] == f"/api/projects/{project_id}/thumbnail"

    list_response = client.get("/api/projects")
    list_data = list_response.json()
    list_payload = list_data["items"]
    listed = next(project for project in list_payload if project["id"] == project_id)
    assert listed["has_thumbnail"] is True
    assert listed["thumbnail_url"] == f"/api/projects/{project_id}/thumbnail"


def test_thumbnail_delete_removes() -> None:
    client = TestClient(app)
    project_id = _upload_single_project(client, "thumb_delete")

    upload_response = client.put(
        f"/api/projects/{project_id}/thumbnail",
        files={"file": ("thumb.png", PNG_BYTES, "image/png")},
    )
    assert upload_response.status_code == 204

    delete_response = client.delete(f"/api/projects/{project_id}/thumbnail")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/projects/{project_id}/thumbnail")
    assert get_response.status_code == 404

    detail_response = client.get(f"/api/projects/{project_id}")
    detail_payload = detail_response.json()
    assert detail_payload["has_thumbnail"] is False
    assert detail_payload["thumbnail_url"] is None


def test_upload_appends_to_existing_project_by_name(api_db: None) -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes([("proj/main.py", b"print('v1')\n")])
    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("initial.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    zip_bytes2 = _create_zip_bytes([("proj/utils.py", b"print('v2')\n")])
    upload_response2 = client.post(
        "/api/projects/upload",
        files={"file": ("second.zip", zip_bytes2, "application/zip")},
    )
    assert upload_response2.status_code == 201
    response_payload = upload_response2.json()
    returned_ids = {project["id"] for project in response_payload["projects"]}
    assert project_id in returned_ids
    assert response_payload["created_count"] == 0
    assert response_payload["merged_count"] == 1
    assert response_payload["actions"][0]["action"] == "merged"
    assert response_payload["actions"][0]["merged_into_project_id"] == project_id

    with get_session() as session:
        projects = session.query(Project).filter(Project.name == "proj").all()
        assert len(projects) == 1
        sources = session.query(ArtifactSource).filter(ArtifactSource.project_id == project_id)
        assert sources.count() == 1


def test_upload_with_project_mapping_resolves_ambiguous_name(api_db: None) -> None:
    client = TestClient(app)
    target_project_id = _upload_single_project(client, "ambig")
    second_project_id = _upload_single_project(client, "othername")
    with get_session() as session:
        second_project = session.query(Project).filter(Project.id == second_project_id).first()
        assert second_project is not None
        second_project.name = "ambig"
        session.flush()

    zip_bytes = _create_zip_bytes([("ambig/main.py", b"print('x')\n")])
    response = client.post(
        "/api/projects/upload",
        data={"project_mapping": json.dumps({"ambig": target_project_id})},
        files={"file": ("ambig.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["created_count"] == 0
    assert payload["merged_count"] == 1
    assert payload["actions"][0]["action"] == "merged"
    assert payload["actions"][0]["merged_into_project_id"] == target_project_id


def test_upload_rejects_invalid_project_mapping_json(api_db: None) -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes([("proj/main.py", b"print('x')\n")])
    response = client.post(
        "/api/projects/upload",
        data={"project_mapping": "{invalid-json"},
        files={"file": ("proj.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 400
    assert "Invalid project_mapping JSON" in response.json()["detail"]


def test_upload_rejects_unknown_project_name_in_mapping(api_db: None) -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes([("proj/main.py", b"print('x')\n")])
    response = client.post(
        "/api/projects/upload",
        data={"project_mapping": json.dumps({"different_name": 1})},
        files={"file": ("proj.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["unknown_project_names"] == ["different_name"]


def test_upload_returns_409_on_ambiguous_project_name(api_db: None) -> None:
    client = TestClient(app)
    with get_session() as session:
        upload1 = UploadRecord(filename="a.zip", size_bytes=1, file_count=1)
        upload2 = UploadRecord(filename="b.zip", size_bytes=1, file_count=1)
        session.add_all([upload1, upload2])
        session.flush()
        session.add_all(
            [
                Project(
                    upload_id=upload1.id,
                    name="ambig",
                    rel_path="ambig",
                    has_git_repo=False,
                    file_count=1,
                    is_collaborative=False,
                ),
                Project(
                    upload_id=upload2.id,
                    name="ambig",
                    rel_path="ambig",
                    has_git_repo=False,
                    file_count=1,
                    is_collaborative=False,
                ),
            ]
        )
        session.flush()

    zip_bytes = _create_zip_bytes([("ambig/main.py", b"print('x')\n")])
    response = client.post(
        "/api/projects/upload",
        files={"file": ("ambig.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["detail"]["candidates"]["ambig"]


def test_dedupes_identical_file_content_across_uploads(api_db: None, tmp_path: Path) -> None:
    client = TestClient(app)
    content = b"print('same')\n"
    zip_bytes = _create_zip_bytes([("proj/main.py", content)])
    response = client.post(
        "/api/projects/upload",
        files={"file": ("first.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 201

    zip_bytes2 = _create_zip_bytes([("proj/other.py", content)])
    response2 = client.post(
        "/api/projects/upload",
        files={"file": ("second.zip", zip_bytes2, "application/zip")},
    )
    assert response2.status_code == 201

    content_hash = hashlib.sha256(content).hexdigest()
    object_path = get_objects_root() / content_hash[:2] / content_hash
    assert object_path.exists(), "Content store should hold one object for this content (dedupe)"
    objects_root = get_objects_root()
    object_files = [p for p in objects_root.rglob("*") if p.is_file()]
    assert len(object_files) == 1


def test_analysis_skips_when_fingerprint_unchanged(api_db: None) -> None:
    client = TestClient(app)
    zip_bytes = _create_zip_bytes([("proj/main.py", b"print('v1')\n")])
    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("initial.zip", zip_bytes, "application/zip")},
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    analyze_response = client.post(f"/api/projects/{project_id}/analyze")
    assert analyze_response.status_code == 200
    with get_session() as session:
        first_count = (
            session.query(CodeAnalysis).filter(CodeAnalysis.project_id == project_id).count()
        )
    assert first_count == 1

    analyze_response2 = client.post(f"/api/projects/{project_id}/analyze")
    assert analyze_response2.status_code == 200
    with get_session() as session:
        second_count = (
            session.query(CodeAnalysis).filter(CodeAnalysis.project_id == project_id).count()
        )
    assert second_count == 1

    zip_bytes2 = _create_zip_bytes([("proj/extra.py", b"print('v2')\n")])
    upload_response2 = client.post(
        "/api/projects/upload",
        files={"file": ("second.zip", zip_bytes2, "application/zip")},
    )
    assert upload_response2.status_code == 201

    analyze_response3 = client.post(f"/api/projects/{project_id}/analyze")
    assert analyze_response3.status_code == 200
    with get_session() as session:
        third_count = (
            session.query(CodeAnalysis).filter(CodeAnalysis.project_id == project_id).count()
        )
    assert third_count == 2


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


def test_analyze_all_updates_all_projects(api_db: None) -> None:
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
    list_data = list_response.json()
    all_projects = list_data["items"]
    for project in all_projects:
        if project["id"] in project_ids:
            assert project["importance_score"] is not None


def test_analyze_all_reports_missing_zip(api_db: None) -> None:
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
    manifest_path = get_manifests_root() / f"{upload_id}.json"
    if manifest_path.exists():
        manifest_path.unlink()

    analyze_response = client.post("/api/projects/analyze")
    assert analyze_response.status_code == 200
    payload = analyze_response.json()

    analyzed_ids = {item["id"] for item in payload["analyzed"]}
    assert project_id not in analyzed_ids, f"Project {project_id} should be skipped, not analyzed"

    skipped_ids = {item["project_id"] for item in payload["skipped"]}
    assert project_id in skipped_ids, f"Project {project_id} should be in skipped list"

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


def test_score_config_endpoints_round_trip() -> None:
    client = TestClient(app)

    # Default config should have all factors enabled.
    get_resp = client.get("/api/projects/config/score")
    assert get_resp.status_code == 200
    default_cfg = get_resp.json()
    assert default_cfg == {
        "contribution": True,
        "diversity": True,
        "duration": True,
        "file_count": True,
    }

    # Update config to disable duration and file_count.
    new_cfg = {
        "contribution": True,
        "diversity": False,
        "duration": False,
        "file_count": True,
    }
    put_resp = client.put("/api/projects/config/score", json=new_cfg)
    assert put_resp.status_code == 200
    assert put_resp.json() == new_cfg

    # Subsequent GET should reflect the updated configuration.
    get_resp2 = client.get("/api/projects/config/score")
    assert get_resp2.status_code == 200
    assert get_resp2.json() == new_cfg
