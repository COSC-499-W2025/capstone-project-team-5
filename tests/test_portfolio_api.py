from __future__ import annotations

import io
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from conftest import auth_headers
from fastapi.testclient import TestClient

from capstone_project_team_5.api.main import app
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Portfolio, PortfolioItem, User


def _create_zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return buffer.getvalue()


def _unique_project_name(prefix: str) -> str:
    """Generate a unique project directory name for ZIP uploads in tests."""
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_user(username: str) -> None:
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            user = User(username=username, password_hash="hash")
            session.add(user)
            session.commit()


def _auth(username: str = "testuser") -> dict[str, str]:
    _create_user(username)
    return auth_headers(username)


def test_portfolio_edit_endpoint_creates_and_updates_item() -> None:
    client = TestClient(app, headers=_auth())

    # Create a project via upload endpoint.
    project_name = _unique_project_name("proj")
    zip_bytes = _create_zip_bytes(
        [
            (f"{project_name}/main.py", b"print('hello')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("proj.zip", zip_bytes, "application/zip")},
        headers=_auth(),
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    username = "editor"
    _create_user(username)

    # Create a portfolio to attach items to.
    portfolio_resp = client.post(
        "/api/portfolio",
        json={
            "username": username,
            "name": "Editing Portfolio",
        },
    )
    assert portfolio_resp.status_code == 200
    portfolio_id = portfolio_resp.json()["id"]

    # First edit (create portfolio item).
    first_response = client.post(
        "/api/portfolio/items",
        json={
            "username": username,
            "project_id": project_id,
            "title": "Edited Project",
            "markdown": "# First version",
            "source_analysis_id": None,
            "portfolio_id": portfolio_id,
        },
    )
    assert first_response.status_code == 200
    first_data = first_response.json()
    assert first_data["project_id"] == project_id
    assert first_data["markdown"] == "# First version"
    assert first_data["is_user_edited"] is True
    assert first_data["portfolio_id"] == portfolio_id

    item_id = first_data["id"]

    # Second edit (update same portfolio item).
    second_response = client.post(
        "/api/portfolio/items",
        json={
            "username": username,
            "project_id": project_id,
            "title": "Edited Project",
            "markdown": "# Second version",
            "source_analysis_id": None,
            "portfolio_id": portfolio_id,
        },
    )
    assert second_response.status_code == 200
    second_data = second_response.json()
    assert second_data["id"] == item_id
    assert second_data["markdown"] == "# Second version"
    assert second_data["portfolio_id"] == portfolio_id


def test_portfolio_edit_endpoint_missing_user_returns_404() -> None:
    client = TestClient(app, headers=_auth())

    project_name = _unique_project_name("proj2")
    zip_bytes = _create_zip_bytes(
        [
            (f"{project_name}/main.py", b"print('hello')\n"),
        ]
    )

    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("proj2.zip", zip_bytes, "application/zip")},
        headers=_auth(),
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    response = client.post(
        "/api/portfolio/items",
        json={
            "username": "missing",
            "project_id": project_id,
            "title": "Should fail",
            "markdown": "# No user",
        },
    )
    assert response.status_code == 404


def test_portfolio_edit_endpoint_rejects_portfolio_from_other_user() -> None:
    client = TestClient(app, headers=_auth())

    project_name = _unique_project_name("proj-ownership")
    zip_bytes = _create_zip_bytes(
        [
            (f"{project_name}/main.py", b"print('hello')\n"),
        ]
    )
    upload_response = client.post(
        "/api/projects/upload",
        files={"file": ("proj-ownership.zip", zip_bytes, "application/zip")},
        headers=_auth(),
    )
    assert upload_response.status_code == 201
    project_id = upload_response.json()["projects"][0]["id"]

    owner_username = "portfolio-owner"
    editor_username = "portfolio-editor"
    _create_user(owner_username)
    _create_user(editor_username)

    owner_portfolio_resp = client.post(
        "/api/portfolio",
        json={"username": owner_username, "name": "Owner Portfolio"},
    )
    assert owner_portfolio_resp.status_code == 200
    owner_portfolio_id = owner_portfolio_resp.json()["id"]

    response = client.post(
        "/api/portfolio/items",
        json={
            "username": editor_username,
            "project_id": project_id,
            "title": "Should fail",
            "markdown": "# Unauthorized portfolio assignment",
            "portfolio_id": owner_portfolio_id,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found for user."


def test_create_and_list_portfolios() -> None:
    client = TestClient(app)

    username = "portfolio-user"
    _create_user(username)

    # Initially, user may or may not have portfolios depending on prior tests;
    # we only assert that creating a new one adds to the list.

    # Create a new portfolio.
    create_resp = client.post(
        "/api/portfolio",
        json={
            "username": username,
            "name": "My Showcase Portfolio",
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "My Showcase Portfolio"
    portfolio_id = created["id"]

    # Listing again should include the created portfolio.
    list_resp = client.get(f"/api/portfolio/user/{username}")
    assert list_resp.status_code == 200
    portfolios = list_resp.json()
    matching = [p for p in portfolios if p["id"] == portfolio_id]
    assert matching
    assert matching[0]["name"] == "My Showcase Portfolio"

    # Ensure it's persisted in the DB.
    with get_session() as session:
        stored = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        assert stored is not None
        assert stored.name == "My Showcase Portfolio"


def test_delete_portfolio() -> None:
    client = TestClient(app)

    username = "delete-portfolio-user"
    _create_user(username)

    # Create a portfolio to delete.
    create_resp = client.post(
        "/api/portfolio",
        json={
            "username": username,
            "name": "Temporary Portfolio",
        },
    )
    assert create_resp.status_code == 200
    portfolio_id = create_resp.json()["id"]

    # Delete the portfolio.
    delete_resp = client.delete(f"/api/portfolio/{portfolio_id}")
    assert delete_resp.status_code == 204

    # Ensure it no longer appears in the user's portfolio list.
    list_resp = client.get(f"/api/portfolio/user/{username}")
    assert list_resp.status_code == 200
    portfolios = list_resp.json()
    assert all(p["id"] != portfolio_id for p in portfolios)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_portfolio(client: TestClient, username: str, name: str = "Test Portfolio") -> int:
    """Create a user and portfolio, return portfolio_id."""
    _create_user(username)
    resp = client.post("/api/portfolio", json={"username": username, "name": name})
    assert resp.status_code == 200
    return resp.json()["id"]


def _create_project(client: TestClient, username: str = "project-owner") -> int:
    """Upload a minimal project zip and return project_id."""
    _create_user(username)
    project_name = _unique_project_name("p")
    zip_bytes = _create_zip_bytes([(f"{project_name}/main.py", b"print('hi')\n")])
    resp = client.post(
        "/api/projects/upload",
        files={"file": ("p.zip", zip_bytes, "application/zip")},
        headers=auth_headers(username),
    )
    assert resp.status_code == 201
    return resp.json()["projects"][0]["id"]


# ── Share / revoke ─────────────────────────────────────────────────────────────


def test_share_portfolio_generates_token() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "share-user-1")

    resp = client.post(f"/api/portfolio/{portfolio_id}/share")
    assert resp.status_code == 200
    data = resp.json()
    assert "share_token" in data
    assert len(data["share_token"]) > 0

    with get_session() as session:
        p = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        assert p is not None
        assert p.share_token == data["share_token"]


def test_share_portfolio_is_idempotent() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "share-user-2")

    first = client.post(f"/api/portfolio/{portfolio_id}/share").json()["share_token"]
    second = client.post(f"/api/portfolio/{portfolio_id}/share").json()["share_token"]
    assert first == second


def test_revoke_portfolio_share_clears_token() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "revoke-user-1")

    client.post(f"/api/portfolio/{portfolio_id}/share")
    revoke_resp = client.delete(f"/api/portfolio/{portfolio_id}/share")
    assert revoke_resp.status_code == 204

    with get_session() as session:
        p = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        assert p is not None
        assert p.share_token is None


def test_get_shared_portfolio_returns_html() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "html-user-1", "My HTML Portfolio")

    token = client.post(f"/api/portfolio/{portfolio_id}/share").json()["share_token"]
    resp = client.get(f"/api/portfolio/shared/{token}")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "My HTML Portfolio" in resp.text


def test_get_shared_portfolio_invalid_token_returns_404() -> None:
    client = TestClient(app)
    resp = client.get("/api/portfolio/shared/nonexistent-token-xyz")
    assert resp.status_code == 404


# ── Update portfolio metadata ──────────────────────────────────────────────────


def test_update_portfolio_template() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "template-user-1")

    resp = client.patch(f"/api/portfolio/{portfolio_id}", json={"template": "timeline"})
    assert resp.status_code == 200
    assert resp.json()["template"] == "timeline"

    with get_session() as session:
        p = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        assert p is not None
        assert p.template == "timeline"


def test_update_portfolio_invalid_template_returns_400() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "template-user-2")

    resp = client.patch(f"/api/portfolio/{portfolio_id}", json={"template": "invalid"})
    assert resp.status_code == 400


def test_update_portfolio_description_and_color_theme() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "meta-user-1")

    resp = client.patch(
        f"/api/portfolio/{portfolio_id}",
        json={"description": "My description", "color_theme": "light"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "My description"
    assert data["color_theme"] == "light"


def test_get_portfolio_info_returns_metadata() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "info-user-1", "Info Portfolio")

    client.patch(
        f"/api/portfolio/{portfolio_id}",
        json={"template": "showcase", "description": "desc"},
    )
    token = client.post(f"/api/portfolio/{portfolio_id}/share").json()["share_token"]

    resp = client.get(f"/api/portfolio/{portfolio_id}/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Info Portfolio"
    assert data["template"] == "showcase"
    assert data["description"] == "desc"
    assert data["share_token"] == token


# ── Text blocks ────────────────────────────────────────────────────────────────


def test_create_text_block() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "textblock-user-1")

    resp = client.post(
        f"/api/portfolio/{portfolio_id}/blocks",
        json={"title": "About me", "markdown": "Hello world"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_text_block"] is True
    assert data["title"] == "About me"
    assert data["markdown"] == "Hello world"
    assert data["project_id"] is None

    with get_session() as session:
        item = session.query(PortfolioItem).filter(PortfolioItem.id == data["id"]).first()
        assert item is not None
        assert bool(item.is_text_block) is True


def test_text_block_appears_in_item_list() -> None:
    client = TestClient(app)
    portfolio_id = _create_portfolio(client, "textblock-user-2")

    client.post(f"/api/portfolio/{portfolio_id}/blocks", json={"title": "Intro", "markdown": "Hi"})

    items = client.get(f"/api/portfolio/{portfolio_id}").json()
    text_blocks = [i for i in items if i.get("is_text_block")]
    assert len(text_blocks) == 1
    assert text_blocks[0]["title"] == "Intro"


# ── Item update / remove / reorder ────────────────────────────────────────────


def test_update_portfolio_item_content() -> None:
    client = TestClient(app)
    username = "item-update-user-1"
    portfolio_id = _create_portfolio(client, username)
    project_id = _create_project(client)

    add_resp = client.post(
        f"/api/portfolio/{portfolio_id}/items",
        json={"username": username, "project_id": project_id},
    )
    assert add_resp.status_code == 200
    item_id = add_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/portfolio/{portfolio_id}/items/{item_id}",
        json={"title": "New title", "markdown": "Updated content"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "New title"
    assert data["markdown"] == "Updated content"


def test_remove_portfolio_item() -> None:
    client = TestClient(app)
    username = "item-remove-user-1"
    portfolio_id = _create_portfolio(client, username)
    project_id = _create_project(client)

    add_resp = client.post(
        f"/api/portfolio/{portfolio_id}/items",
        json={"username": username, "project_id": project_id},
    )
    item_id = add_resp.json()["id"]

    del_resp = client.delete(f"/api/portfolio/{portfolio_id}/items/{item_id}")
    assert del_resp.status_code == 204

    items = client.get(f"/api/portfolio/{portfolio_id}").json()
    assert all(i["id"] != item_id for i in items)

    with get_session() as session:
        assert session.query(PortfolioItem).filter(PortfolioItem.id == item_id).first() is None


def test_reorder_portfolio_items() -> None:
    client = TestClient(app)
    username = "reorder-user-1"
    portfolio_id = _create_portfolio(client, username)

    block_a = client.post(
        f"/api/portfolio/{portfolio_id}/blocks",
        json={"title": "A", "markdown": ""},
    ).json()["id"]
    block_b = client.post(
        f"/api/portfolio/{portfolio_id}/blocks",
        json={"title": "B", "markdown": ""},
    ).json()["id"]
    block_c = client.post(
        f"/api/portfolio/{portfolio_id}/blocks",
        json={"title": "C", "markdown": ""},
    ).json()["id"]

    # Reverse the order.
    reorder_resp = client.post(
        f"/api/portfolio/{portfolio_id}/reorder",
        json={"item_ids": [block_c, block_b, block_a]},
    )
    assert reorder_resp.status_code == 204

    items = client.get(f"/api/portfolio/{portfolio_id}").json()
    titles = [i["title"] for i in items]
    assert titles == ["C", "B", "A"]
