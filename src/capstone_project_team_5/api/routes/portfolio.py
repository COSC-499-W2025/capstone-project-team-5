"""Portfolio editing routes for the API."""

# ruff: noqa: E501

from __future__ import annotations

import html as _hl
import json
import re as _re
import uuid

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from capstone_project_team_5.api.schemas.portfolio import (
    PortfolioAddItemRequest,
    PortfolioCreateRequest,
    PortfolioEditRequest,
    PortfolioItemResponse,
    PortfolioItemUpdateRequest,
    PortfolioReorderRequest,
    PortfolioResponse,
    PortfolioShareResponse,
    PortfolioTextBlockRequest,
    PortfolioUpdateRequest,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import (
    CodeAnalysis,
    Portfolio,
    PortfolioItem,
    Project,
    ProjectSkill,
    Skill,
    User,
)
from capstone_project_team_5.services.project_thumbnail import has_project_thumbnail

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _extract_markdown(content: str) -> str:
    """Extract markdown text from stored portfolio content."""
    try:
        decoded = json.loads(content)
    except Exception:
        decoded = content

    if isinstance(decoded, dict):
        markdown = decoded.get("markdown")
        if isinstance(markdown, str) and markdown.strip():
            return markdown
        return ""

    if isinstance(decoded, str) and decoded.strip():
        return decoded

    return ""


def _upsert_portfolio_item_for_user(
    *,
    session: Session,
    user: User,
    project: Project,
    request: PortfolioEditRequest,
    portfolio_id: int | None,
) -> PortfolioItemResponse:
    """Create or update a portfolio item for a user/project pair."""
    if portfolio_id is not None:
        portfolio = (
            session.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
            .first()
        )
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found for user.",
            )

    encoded_content = json.dumps({"markdown": request.markdown})

    query = session.query(PortfolioItem).filter(
        PortfolioItem.user_id == user.id,
        PortfolioItem.project_id == request.project_id,
        PortfolioItem.source_analysis_id == request.source_analysis_id,
    )
    if portfolio_id is None:
        query = query.filter(PortfolioItem.portfolio_id.is_(None))
    else:
        query = query.filter(PortfolioItem.portfolio_id == portfolio_id)

    item = query.order_by(PortfolioItem.updated_at.desc()).first()

    if item is None:
        item = PortfolioItem(
            project_id=request.project_id,
            portfolio_id=portfolio_id,
            user_id=user.id,
            title=request.title or project.name,
            content=encoded_content,
            is_user_edited=True,
            source_analysis_id=request.source_analysis_id,
        )
        session.add(item)
    else:
        item.title = request.title or project.name
        item.content = encoded_content
        item.portfolio_id = portfolio_id
        item.is_user_edited = True
        item.source_analysis_id = request.source_analysis_id

    session.flush()

    markdown = _extract_markdown(item.content)

    return PortfolioItemResponse(
        id=item.id,
        project_id=item.project_id,
        title=item.title,
        markdown=markdown,
        is_user_edited=bool(item.is_user_edited),
        source_analysis_id=getattr(item, "source_analysis_id", None),
        portfolio_id=getattr(item, "portfolio_id", None),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post(
    "",
    response_model=PortfolioResponse,
    summary="Create a portfolio",
    description=(
        "Create a named portfolio for a user. A portfolio is a logical grouping of "
        "portfolio items for a user."
    ),
)
def create_portfolio(request: PortfolioCreateRequest) -> PortfolioResponse:
    """Create a new portfolio for the given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        portfolio = Portfolio(
            user_id=user.id,
            name=request.name,
        )
        session.add(portfolio)
        session.flush()
        session.refresh(portfolio)

        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            share_token=portfolio.share_token,
            template=portfolio.template or "grid",
            color_theme=portfolio.color_theme or "dark",
            description=portfolio.description,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )


@router.get(
    "/user/{username}",
    response_model=list[PortfolioResponse],
    summary="List portfolios for a user",
    description="Return all portfolios belonging to the given username.",
)
def list_portfolios(username: str) -> list[PortfolioResponse]:
    """List all portfolios for a given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        portfolios = session.query(Portfolio).filter(Portfolio.user_id == user.id).all()

        return [
            PortfolioResponse(
                id=p.id,
                name=p.name,
                share_token=p.share_token,
                template=p.template or "grid",
                color_theme=p.color_theme or "dark",
                description=p.description,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in portfolios
        ]


@router.post(
    "/{portfolio_id}/items",
    response_model=PortfolioItemResponse,
    summary="Add project to portfolio",
    description=(
        "Ensure a portfolio item exists for the given user/project and attach it to the "
        "specified portfolio. If no item exists yet, one is created with default content."
    ),
)
def add_project_to_portfolio(
    portfolio_id: int,
    request: PortfolioAddItemRequest,
) -> PortfolioItemResponse:
    """Create or reuse a portfolio item for a project in a specific portfolio."""
    with get_session() as session:
        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None or portfolio.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found for user.",
            )

        project = session.query(Project).filter(Project.id == request.project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        # Try to find an existing item for this user/project/analysis/portfolio.
        query = (
            session.query(PortfolioItem)
            .filter(
                PortfolioItem.user_id == user.id,
                PortfolioItem.project_id == request.project_id,
                PortfolioItem.source_analysis_id == request.source_analysis_id,
                PortfolioItem.portfolio_id == portfolio_id,
            )
            .order_by(PortfolioItem.updated_at.desc())
        )
        item = query.first()

        if item is None:
            # Prefer the analysis summary as default content; fall back to project name/path.
            analysis = (
                session.query(CodeAnalysis)
                .filter(CodeAnalysis.project_id == request.project_id)
                .order_by(CodeAnalysis.created_at.desc())
                .first()
            )
            if analysis and analysis.summary_text and analysis.summary_text.strip():
                default_markdown = analysis.summary_text.strip()
                source_analysis_id = analysis.id
            else:
                default_markdown = f"# {project.name}\n\n`{project.rel_path}`"
                source_analysis_id = request.source_analysis_id

            encoded_content = json.dumps({"markdown": default_markdown})

            item = PortfolioItem(
                project_id=request.project_id,
                portfolio_id=portfolio_id,
                user_id=user.id,
                title=project.name,
                content=encoded_content,
                is_user_edited=False,
                source_analysis_id=source_analysis_id,
            )
            session.add(item)
            session.flush()
            session.refresh(item)

        markdown = _extract_markdown(item.content)

        return PortfolioItemResponse(
            id=item.id,
            project_id=item.project_id,
            title=item.title,
            markdown=markdown,
            is_user_edited=bool(item.is_user_edited),
            source_analysis_id=getattr(item, "source_analysis_id", None),
            portfolio_id=getattr(item, "portfolio_id", None),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


@router.post(
    "/{portfolio_id}/share",
    response_model=PortfolioShareResponse,
    summary="Generate a share link for a portfolio",
    description=(
        "Generate a unique share token for the portfolio. Subsequent calls return the same token."
    ),
)
def generate_share_link(portfolio_id: int) -> PortfolioShareResponse:
    """Generate (or return existing) share token for a portfolio."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        if portfolio.share_token is None:
            portfolio.share_token = str(uuid.uuid4())
            session.flush()

        return PortfolioShareResponse(share_token=portfolio.share_token)


@router.delete(
    "/{portfolio_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke share link",
    description="Invalidate the share token so the public URL stops working.",
)
def revoke_share_link(portfolio_id: int) -> Response:
    """Clear the share token on a portfolio."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )
        portfolio.share_token = None
        session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _render_portfolio_for_id(portfolio_id: int, session: Session) -> HTMLResponse | None:
    """Shared helper: build the HTML response for a portfolio by its DB id.

    Returns None if the portfolio does not exist.
    """
    portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio is None:
        return None

    owner = session.query(User).filter(User.id == portfolio.user_id).first()
    owner_name = owner.username if owner else "unknown"

    items = (
        session.query(PortfolioItem)
        .filter(PortfolioItem.portfolio_id == portfolio.id)
        .order_by(PortfolioItem.display_order.asc(), PortfolioItem.updated_at.desc())
        .all()
    )

    item_list: list[dict] = []
    for item in items:
        md = _extract_markdown(item.content)
        analysis_bullets: list[str] = []
        if not item.is_user_edited and item.project_id:
            analysis = (
                session.query(CodeAnalysis)
                .filter(CodeAnalysis.project_id == item.project_id)
                .order_by(CodeAnalysis.created_at.desc())
                .first()
            )
            if analysis:
                if analysis.summary_text and analysis.summary_text.strip():
                    md = analysis.summary_text.strip()
                try:
                    metrics = json.loads(analysis.metrics_json or "{}")
                except Exception:
                    metrics = {}
                raw_bullets = metrics.get("ai_bullets") or metrics.get("resume_bullets") or []
                if isinstance(raw_bullets, list):
                    analysis_bullets = [str(b) for b in raw_bullets if b][:6]
        thumbnail_url = (
            f"/api/projects/{item.project_id}/thumbnail"
            if item.project_id and has_project_thumbnail(item.project_id)
            else None
        )
        # Fetch skills and project metadata for skill timeline + showcase ranking
        item_skills: list[dict] = []
        importance_rank: int | None = None
        is_showcase_proj: bool = False
        start_date_str: str | None = None
        if item.project_id and not getattr(item, "is_text_block", False):
            proj = session.query(Project).filter(Project.id == item.project_id).first()
            if proj:
                importance_rank = proj.importance_rank
                is_showcase_proj = bool(proj.is_showcase)
                if proj.start_date:
                    start_date_str = proj.start_date.strftime("%b %Y")
            skill_rows = (
                session.query(Skill)
                .join(ProjectSkill, ProjectSkill.skill_id == Skill.id)
                .filter(ProjectSkill.project_id == item.project_id)
                .order_by(Skill.name)
                .all()
            )
            item_skills = [{"name": s.name, "type": str(s.skill_type)} for s in skill_rows]
        item_list.append(
            {
                "title": item.title,
                "markdown": md,
                "bullets": analysis_bullets,
                "thumbnail_url": thumbnail_url,
                "is_text_block": bool(getattr(item, "is_text_block", False)),
                "is_user_edited": bool(item.is_user_edited),
                "updated_at": item.updated_at.strftime("%b %d, %Y"),
                "skills": item_skills,
                "importance_rank": importance_rank,
                "is_showcase": is_showcase_proj,
                "start_date": start_date_str,
            }
        )

    html = _render_portfolio_html(
        name=portfolio.name,
        owner=owner_name,
        description=portfolio.description or "",
        items=item_list,
        created_at=portfolio.created_at.strftime("%B %d, %Y"),
        template=portfolio.template or "grid",
        color_theme=portfolio.color_theme or "dark",
    )
    return HTMLResponse(content=html)


@router.get(
    "/{portfolio_id}/preview",
    response_class=HTMLResponse,
    summary="Preview a portfolio",
    description="Render the portfolio HTML page without requiring a share token.",
)
def preview_portfolio(portfolio_id: int) -> HTMLResponse:
    """Render a portfolio dashboard for previewing (no share token needed)."""
    with get_session() as session:
        response = _render_portfolio_for_id(portfolio_id, session)
        if response is None:
            return HTMLResponse(
                content=_render_404_html(
                    title="Portfolio not found",
                    message="This portfolio does not exist.",
                ),
                status_code=404,
            )
        return response


@router.get(
    "/shared/{share_token}",
    response_class=HTMLResponse,
    summary="View a shared portfolio",
    description="Public endpoint — renders a portfolio dashboard using a share token.",
)
def get_shared_portfolio(share_token: str) -> HTMLResponse:
    """Render a portfolio dashboard by share token (no auth required)."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.share_token == share_token).first()
        if portfolio is None:
            return HTMLResponse(
                content=_render_404_html(
                    title="Portfolio not found",
                    message="This portfolio link has been revoked or never existed.",
                ),
                status_code=404,
            )
        response = _render_portfolio_for_id(portfolio.id, session)
        return response  # type: ignore[return-value]


# ── Minimal 404 page ──────────────────────────────────────────────────────────


def _render_404_html(title: str = "Not found", message: str = "This page doesn't exist.") -> str:
    """Return a minimal self-contained 404 HTML page."""
    t = _hl.escape(title)
    m = _hl.escape(message)
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0"/>'
        f"<title>{t}</title>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{background:#0f1117;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:24px}"
        ".wrap{max-width:360px}"
        ".code{font-size:72px;font-weight:800;letter-spacing:-.04em;line-height:1;color:#252a38}"
        ".title{margin-top:16px;font-size:18px;font-weight:700}"
        ".msg{margin-top:8px;font-size:13px;color:#64748b;line-height:1.6}"
        "</style>"
        f'</head><body><div class="wrap">'
        f'<div class="code">404 :"(</div>'
        f'<div class="title">{t}</div>'
        f'<p class="msg">{m}</p>'
        f"</div></body></html>"
    )


# ── CSS and JS are plain strings (no f-string) to avoid escaping every brace ──

_PORTFOLIO_CSS = """<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1117;--surface:#181c27;--border:#252a38;--ink:#e2e8f0;--muted:#64748b;
  --accent:#6366f1;--radius:8px;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,"JetBrains Mono","Cascadia Code",monospace;
}
html[data-theme="light"]{
  --bg:#ffffff;--surface:#f8fafc;--border:#e2e8f0;--ink:#0f172a;--muted:#64748b;
  --accent:#4f46e5;
}
html[data-theme="light"] .markdown-body code{background:rgba(0,0,0,.05);border-color:#e2e8f0}
html[data-theme="light"] .markdown-body pre{background:#f1f5f9;border-color:#e2e8f0}
html[data-theme="slate"]{
  --bg:#1e293b;--surface:#273347;--border:#334155;--ink:#e2e8f0;--muted:#94a3b8;
  --accent:#818cf8;
}
body{background:var(--bg);color:var(--ink);font-family:var(--font);line-height:1.6;min-height:100vh}
/* Hero */
.hero{border-bottom:1px solid var(--border);padding:48px 24px 40px}
.hero-inner{max-width:880px;margin:0 auto}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:14px}
.hero h1{font-size:clamp(26px,5vw,44px);font-weight:800;letter-spacing:-.03em;line-height:1.1}
.hero-desc{margin-top:12px;font-size:14px;color:var(--muted);max-width:560px;line-height:1.7}
.meta-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:16px;font-size:12px;color:var(--muted);font-family:var(--mono)}
.meta-sep{opacity:.3}
.stat-pill{color:var(--accent);font-weight:600}
/* Content */
.content{max-width:880px;margin:0 auto;padding:36px 24px 80px}
.empty{text-align:center;color:var(--muted);padding:80px 0;font-size:14px}
/* Common */
.item-idx{font-size:10px;font-family:var(--mono);color:var(--muted);margin-bottom:10px;letter-spacing:.04em}
.item-title{font-size:15px;font-weight:700;letter-spacing:-.01em}
.item-date{font-size:11px;font-family:var(--mono);color:var(--muted)}
.tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:10px}
.tag{background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:4px;padding:2px 6px;font-size:11px;font-family:var(--mono);color:var(--muted)}
.bullets{list-style:none;margin-top:10px}
.bullets li{font-size:13px;color:var(--muted);padding:2px 0 2px 14px;position:relative;line-height:1.5}
.bullets li::before{content:'–';position:absolute;left:0;color:var(--muted)}
.stats-bar{display:flex;gap:14px;margin-top:12px;font-size:11px;color:var(--muted);font-family:var(--mono);padding-top:10px;border-top:1px solid var(--border)}
/* ── Thumbnail ── */
.thumb{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:4px;margin-bottom:12px;border:1px solid var(--border)}
.thumb-sm{width:100%;aspect-ratio:16/9;object-fit:cover;border-bottom:1px solid var(--border);display:block}
/* ── Grid ── */
.grid-container{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.grid-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;cursor:pointer;transition:border-color .15s,transform .15s}
.grid-card:hover{border-color:var(--accent);transform:translateY(-2px)}
.grid-card-body{padding:16px}
/* ── Modal ── */
.modal-box{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);width:100%;max-width:680px;max-height:85vh;overflow-y:auto;position:relative}
.modal-header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:24px 24px 0}
.modal-body{padding:16px 24px 24px}
.modal-title{font-size:20px;font-weight:800;letter-spacing:-.02em;line-height:1.2}
.modal-close{background:none;border:none;color:var(--muted);cursor:pointer;font-size:20px;line-height:1;padding:0;flex-shrink:0}
.modal-close:hover{color:var(--ink)}
.modal-summary{font-size:13px;color:var(--muted);line-height:1.7;margin:10px 0}
/* ── Showcase ── */
.showcase-card{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:12px}
.showcase-inner{display:grid;grid-template-columns:200px 1fr}
@media(max-width:580px){.showcase-inner{grid-template-columns:1fr}}
.showcase-sidebar{padding:22px 20px;border-right:1px solid var(--border);display:flex;flex-direction:column;gap:8px;background:var(--surface)}
.stats-col{display:flex;gap:20px;margin-top:10px}
.stat-num{font-size:16px;font-weight:700;font-family:var(--mono)}
.stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.showcase-main{padding:22px 26px;background:var(--surface)}
.showcase-summary{font-size:13px;color:var(--muted);margin-bottom:10px;line-height:1.6}
/* ── Timeline ── */
.timeline{position:relative;padding-left:36px}
.timeline::before{content:'';position:absolute;left:8px;top:0;bottom:0;width:1px;background:var(--border)}
.timeline-item{position:relative;margin-bottom:20px}
.timeline-dot{position:absolute;left:-36px;top:3px;width:18px;height:18px;border-radius:50%;border:1px solid var(--accent);background:var(--bg);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;font-family:var(--mono);color:var(--accent)}
.timeline-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 20px}
.tl-header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}
.md-expand{margin-top:12px}
.md-expand summary{font-size:11px;font-family:var(--mono);color:var(--muted);cursor:pointer;user-select:none}
.md-expand summary:hover{color:var(--ink)}
.md-expand .markdown-body{margin-top:12px;padding-top:12px;border-top:1px solid var(--border)}
/* ── Markdown ── */
.markdown-body{font-size:14px;line-height:1.75;color:var(--ink)}
.markdown-body h1,.markdown-body h2,.markdown-body h3{font-weight:700;letter-spacing:-.02em;margin:20px 0 8px;line-height:1.2}
.markdown-body h1{font-size:18px}.markdown-body h2{font-size:16px}.markdown-body h3{font-size:14px}
.markdown-body h1:first-child,.markdown-body h2:first-child,.markdown-body h3:first-child{margin-top:0}
.markdown-body p{margin:8px 0}
.markdown-body ul,.markdown-body ol{padding-left:18px;margin:8px 0}
.markdown-body li{margin:3px 0}
.markdown-body code{font-family:var(--mono);font-size:12px;background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:3px;padding:1px 5px}
.markdown-body pre{background:#0d1117;border:1px solid var(--border);border-radius:6px;padding:14px;overflow-x:auto;margin:10px 0}
.markdown-body pre code{background:none;border:none;padding:0;font-size:13px}
.markdown-body blockquote{border-left:2px solid var(--border);padding-left:12px;color:var(--muted);margin:10px 0}
.markdown-body a{color:var(--accent)}.markdown-body hr{border:none;border-top:1px solid var(--border);margin:16px 0}
/* ── Text block ── */
.text-section{margin:28px 0;padding:0 2px}
.text-section-title{font-size:16px;font-weight:700;letter-spacing:-.02em;margin-bottom:10px;color:var(--ink)}
/* ── Search ── */
.search-wrap{margin-top:20px}
.search-input{width:100%;max-width:360px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:8px 12px;font-size:13px;color:var(--ink);font-family:var(--font);outline:none}
.search-input:focus{border-color:var(--accent)}
.search-input::placeholder{color:var(--muted)}
/* ── Featured badge ── */
.featured-badge{display:inline-block;margin-left:6px;padding:1px 5px;font-size:9px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;background:rgba(99,102,241,.15);color:var(--accent);border:1px solid rgba(99,102,241,.3);border-radius:3px;vertical-align:middle}
/* ── Skills timeline ── */
.skills-section{margin-top:48px;padding-top:32px;border-top:1px solid var(--border)}
.section-title{font-size:18px;font-weight:700;letter-spacing:-.02em;margin-bottom:24px;color:var(--ink)}
.sk-timeline{position:relative;padding-left:28px}
.sk-timeline::before{content:'';position:absolute;left:6px;top:4px;bottom:4px;width:1px;background:var(--border)}
.sk-item{position:relative;display:flex;gap:14px;margin-bottom:20px}
.sk-dot{position:absolute;left:-28px;top:4px;width:13px;height:13px;border-radius:50%;border:1px solid var(--accent);background:var(--bg);flex-shrink:0}
.sk-body{flex:1}
.sk-project{font-size:13px;font-weight:600;color:var(--ink);display:flex;align-items:baseline;gap:8px;margin-bottom:8px}
.sk-date{font-size:11px;font-family:var(--mono);color:var(--muted);font-weight:400}
.sk-tags{display:flex;flex-wrap:wrap;gap:4px}
.skill-tag{font-size:11px;font-family:var(--mono);border-radius:4px;padding:2px 7px}
.skill-tool{background:rgba(99,102,241,.1);color:var(--accent);border:1px solid rgba(99,102,241,.2)}
.skill-practice{background:rgba(16,185,129,.08);color:#10b981;border:1px solid rgba(16,185,129,.2)}
/* Footer */
footer{text-align:center;padding:24px;font-size:11px;font-family:var(--mono);color:var(--muted);border-top:1px solid var(--border);margin-top:40px}
</style>"""

# ── Python-side rendering helpers (no JavaScript needed for item output) ──────


def _item_tags(md: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for m in _re.findall(r"`([^`\n]{1,30})`", md):
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result[:8]


def _item_bullets(md: str) -> list[str]:
    bulls = []
    for line in md.split("\n"):
        s = line.strip()
        if _re.match(r"^[-*+]\s", s):
            bulls.append(_re.sub(r"^[-*+]\s+", "", s).strip())
    return [b for b in bulls if b][:5]


def _item_wc(md: str) -> int:
    return len(_re.sub(r"[#*`\[\]()_~>]", "", md).split())


def _rt(wc: int) -> str:
    m = max(1, round(wc / 200))
    return f"{m} min" if m == 1 else f"{m} mins"


def _tags_el(md: str) -> str:
    tags = _item_tags(md)
    if not tags:
        return ""
    inner = "".join(f'<span class="tag">{_hl.escape(t)}</span>' for t in tags)
    return f'<div class="tags">{inner}</div>'


def _bullets_el(md: str) -> str:
    bulls = _item_bullets(md)
    if not bulls:
        return ""
    inner = "".join(f"<li>{_hl.escape(b)}</li>" for b in bulls)
    return f'<ul class="bullets">{inner}</ul>'


def _stats_el(md: str) -> str:
    wc = _item_wc(md)
    return f'<div class="stats-bar"><span>{wc} words</span><span>{_rt(wc)} read</span></div>'


def _analysis_bullets_el(bullets: list[str]) -> str:
    """Render pre-extracted analysis bullets (resume/AI bullets from metrics_json)."""
    if not bullets:
        return ""
    inner = "".join(f"<li>{_hl.escape(b)}</li>" for b in bullets)
    return f'<ul class="bullets">{inner}</ul>'


def _render_grid(items: list[dict]) -> str:
    if not items:
        return '<p class="empty">No projects in this portfolio yet.</p>'
    cards = ""
    modals = ""
    for i, item in enumerate(items):
        title, md = item["title"], item["markdown"]
        idx = str(i + 1).zfill(2)
        analysis_bullets = item.get("bullets") or []
        bullets_html = _analysis_bullets_el(analysis_bullets) or _bullets_el(md)
        thumb = item.get("thumbnail_url")
        thumb_html = (
            f'<img class="thumb" src="{_hl.escape(thumb)}" alt="" loading="lazy"/>' if thumb else ""
        )
        wc = _item_wc(md)

        # Clean summary card
        cards += (
            f'<div class="grid-card" onclick="openModal({i})">'
            + thumb_html
            + '<div class="grid-card-body">'
            + f'<div class="item-idx">{idx}</div>'
            + f'<div class="item-title">{_hl.escape(title)}</div>'
            + f'<div class="item-date">{_hl.escape(item["updated_at"])}</div>'
            + _tags_el(md)
            + f'<div class="stats-bar"><span>{wc} words</span><span>{_rt(wc)} read</span></div>'
            + "</div></div>"
        )

        # Hidden data store for modal — style="display:none" is more robust than hidden attribute
        modals += (
            f'<div id="md-{i}" style="display:none">'
            + (
                f'<img class="thumb" src="{_hl.escape(thumb)}" alt="" style="border-radius:0;margin-bottom:0"/>'
                if thumb
                else ""
            )
            + '<div class="modal-header">'
            + f'<div class="modal-title">{_hl.escape(title)}</div>'
            + '<button class="modal-close" onclick="closeModal()">&#x2715;</button>'
            + "</div>"
            + '<div class="modal-body">'
            + f'<div class="item-date" style="margin-bottom:8px">{_hl.escape(item["updated_at"])}</div>'
            + _tags_el(md)
            + (f'<p class="modal-summary">{_hl.escape(md)}</p>' if not bullets_html else "")
            + bullets_html
            + f'<div class="markdown-body md-render" data-md="{_hl.escape(md)}" style="margin-top:16px"></div>'
            + _stats_el(md)
            + "</div></div>"
        )

    # Modal data divs are hidden siblings; the overlay itself lives at body level (injected by _render_portfolio_html)
    return f'<div class="grid-container">{cards}</div>{modals}'


def _render_showcase(items: list[dict]) -> str:
    if not items:
        return '<p class="empty">No projects in this portfolio yet.</p>'
    # Determine top-3 by importance_rank (lower = more important); is_showcase as tiebreaker
    ranked = sorted(
        range(len(items)),
        key=lambda i: (
            items[i].get("importance_rank") is None,
            items[i].get("importance_rank") or 999,
            not items[i].get("is_showcase", False),
        ),
    )
    top3 = set(ranked[:3])
    cards = ""
    for i, item in enumerate(items):
        title, md = item["title"], item["markdown"]
        idx = str(i + 1).zfill(2)
        wc = _item_wc(md)
        analysis_bullets = item.get("bullets") or []
        bullets_html = _analysis_bullets_el(analysis_bullets) or _bullets_el(md)
        thumb = item.get("thumbnail_url")
        thumb_html = (
            f'<img class="thumb-sm" src="{_hl.escape(thumb)}" alt="" loading="lazy"/>'
            if thumb
            else ""
        )
        featured_badge = '<span class="featured-badge">Featured</span>' if i in top3 else ""
        # Showcase main: bullets take priority; fall back to full markdown render
        if bullets_html:
            main_html = (
                f'<div class="showcase-main">'
                f'<p class="showcase-summary">{_hl.escape(md)}</p>' + bullets_html + "</div>"
            )
        else:
            main_html = f'<div class="showcase-main markdown-body md-render" data-md="{_hl.escape(md)}"></div>'
        cards += (
            '<div class="showcase-card">' + thumb_html + '<div class="showcase-inner">'
            '<div class="showcase-sidebar">'
            f'<div class="item-idx">{idx}{featured_badge}</div>'
            f'<div class="item-title">{_hl.escape(title)}</div>'
            f'<div class="item-date">{_hl.escape(item["updated_at"])}</div>'
            + _tags_el(md)
            + '<div class="stats-col">'
            f'<div class="stat-item"><div class="stat-num">{wc}</div><div class="stat-lbl">words</div></div>'
            f'<div class="stat-item"><div class="stat-num">{_rt(wc)}</div><div class="stat-lbl">read</div></div>'
            "</div></div>" + main_html + "</div></div>"
        )
    return cards


def _render_timeline(items: list[dict]) -> str:
    if not items:
        return '<p class="empty">No projects in this portfolio yet.</p>'
    rows = ""
    for i, item in enumerate(items):
        title, md = item["title"], item["markdown"]
        analysis_bullets = item.get("bullets") or []
        bullets_html = _analysis_bullets_el(analysis_bullets) or _bullets_el(md)
        thumb = item.get("thumbnail_url")
        thumb_html = (
            f'<img class="thumb" src="{_hl.escape(thumb)}" alt="" loading="lazy"/>' if thumb else ""
        )
        rows += (
            '<div class="timeline-item">'
            f'<div class="timeline-dot">{i + 1}</div>'
            '<div class="timeline-card">'
            f'<div class="tl-header"><div class="item-title">{_hl.escape(title)}</div>'
            f'<div class="item-date">{_hl.escape(item["updated_at"])}</div></div>'
            + thumb_html
            + _tags_el(md)
            + bullets_html
            + '<details class="md-expand"><summary>view full content</summary>'
            f'<div class="markdown-body md-render" data-md="{_hl.escape(md)}"></div>'
            "</details></div></div>"
        )
    return f'<div class="timeline">{rows}</div>'


def _render_skills_timeline(items: list[dict]) -> str:
    """Render a skills-progression timeline section across portfolio projects."""
    project_items = [it for it in items if not it.get("is_text_block") and it.get("skills")]
    if not project_items:
        return ""
    seen: set[str] = set()
    rows = ""
    for item in project_items:
        new_skills = [s for s in item["skills"] if s["name"] not in seen]
        for s in new_skills:
            seen.add(s["name"])
        if not new_skills:
            continue
        date_str = item.get("start_date") or item.get("updated_at", "")
        tools_html = "".join(
            f'<span class="skill-tag skill-tool">{_hl.escape(s["name"])}</span>'
            for s in new_skills
            if s["type"] == "tool"
        )
        practices_html = "".join(
            f'<span class="skill-tag skill-practice">{_hl.escape(s["name"])}</span>'
            for s in new_skills
            if s["type"] == "practice"
        )
        rows += (
            '<div class="sk-item">'
            '<div class="sk-dot"></div>'
            '<div class="sk-body">'
            f'<div class="sk-project">{_hl.escape(item["title"])}'
            + (f'<span class="sk-date">{_hl.escape(date_str)}</span>' if date_str else "")
            + "</div>"
            f'<div class="sk-tags">{tools_html}{practices_html}</div>'
            "</div></div>"
        )
    if not rows:
        return ""
    return (
        '<section class="skills-section">'
        '<h2 class="section-title">Skills Progression</h2>'
        f'<div class="sk-timeline">{rows}</div>'
        "</section>"
    )


def _render_portfolio_html(
    *,
    name: str,
    owner: str,
    description: str,
    items: list[dict],
    created_at: str,
    template: str,
    color_theme: str = "dark",
) -> str:
    """Build a self-contained HTML dashboard for a shared portfolio."""
    name_e = _hl.escape(name)
    owner_e = _hl.escape(owner)
    created_e = _hl.escape(created_at)
    desc_block = f'<p class="hero-desc">{_hl.escape(description)}</p>' if description else ""

    # Interleave text blocks (full-width) with batches of project items
    project_items = [it for it in items if not it.get("is_text_block")]
    item_count = len(project_items)
    plural = "" if item_count == 1 else "s"

    segments: list[str] = []
    batch: list[dict] = []
    for it in items:
        if it.get("is_text_block"):
            if batch:
                if template == "showcase":
                    segments.append(_render_showcase(batch))
                elif template == "timeline":
                    segments.append(_render_timeline(batch))
                else:
                    segments.append(_render_grid(batch))
                batch = []
            title_e = _hl.escape(it.get("title", "") or "")
            md_e = _hl.escape(it.get("markdown", "") or "")
            segments.append(
                '<div class="text-section">'
                + (
                    f'<h2 class="text-section-title">{title_e}</h2>'
                    if title_e and title_e != "Text block"
                    else ""
                )
                + f'<div class="markdown-body md-render" data-md="{md_e}"></div>'
                + "</div>"
            )
        else:
            batch.append(it)
    if batch:
        if template == "showcase":
            segments.append(_render_showcase(batch))
        elif template == "timeline":
            segments.append(_render_timeline(batch))
        else:
            segments.append(_render_grid(batch))

    if not segments:
        segments.append('<p class="empty">No projects in this portfolio yet.</p>')

    items_html = "\n".join(segments)
    skills_html = _render_skills_timeline(items)

    enhance_js = (
        "<script>\n"
        # marked.js enhancement for visible md-render elements
        "if (typeof marked !== 'undefined') {\n"
        "  document.querySelectorAll('.md-render[data-md]').forEach(function(el) {\n"
        "    el.innerHTML = marked.parse(el.getAttribute('data-md') || '');\n"
        "  });\n"
        "}\n"
        # Grid modal logic
        "function openModal(i) {\n"
        "  var src = document.getElementById('md-' + i);\n"
        "  var box = document.getElementById('modal-inner');\n"
        "  if (!src) return;\n"
        "  box.innerHTML = src.innerHTML;\n"
        "  if (typeof marked !== 'undefined') {\n"
        "    box.querySelectorAll('.md-render[data-md]').forEach(function(el) {\n"
        "      el.innerHTML = marked.parse(el.getAttribute('data-md') || '');\n"
        "    });\n"
        "  }\n"
        "  var o = document.getElementById('modal-overlay');\n"
        "  o.style.display = 'flex';\n"
        "  document.body.style.overflow = 'hidden';\n"
        "}\n"
        "function closeModal() {\n"
        "  var o = document.getElementById('modal-overlay');\n"
        "  if (o) { o.style.display = 'none'; document.body.style.overflow = ''; }\n"
        "}\n"
        "document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeModal(); });\n"
        # Search/filter
        "function filterItems(q) {\n"
        "  var term = q.toLowerCase().trim();\n"
        "  var sel = '.grid-card,.showcase-card,.timeline-item,.text-section';\n"
        "  document.querySelectorAll(sel).forEach(function(el) {\n"
        "    el.style.display = (!term || el.textContent.toLowerCase().includes(term)) ? '' : 'none';\n"
        "  });\n"
        "}\n"
        "</script>"
    )

    theme_attr = _hl.escape(color_theme) if color_theme != "dark" else ""
    html_open = f'<html lang="en" data-theme="{theme_attr}">' if theme_attr else '<html lang="en">'

    head = (
        f"<!DOCTYPE html>\n{html_open}\n<head>\n"
        '  <meta charset="UTF-8"/>\n'
        '  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>\n'
        f"  <title>{name_e} \u2014 Portfolio</title>\n"
        '  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>\n'
    )

    modal_overlay = (
        '<div id="modal-overlay" style="display:none;position:fixed;inset:0;'
        "background:rgba(0,0,0,.6);align-items:center;justify-content:center;"
        'z-index:9999;padding:24px" onclick="if(event.target===this)closeModal()">'
        '<div class="modal-box" id="modal-inner"></div>'
        "</div>"
    )

    search_bar = (
        '<div class="search-wrap">'
        '<input id="portfolio-search" type="search" placeholder="Filter projects…"'
        ' oninput="filterItems(this.value)" class="search-input" autocomplete="off"/>'
        "</div>"
    )
    body = (
        f"</head>\n<body>\n"
        f'<div class="hero">\n  <div class="hero-inner">\n'
        f'    <div class="eyebrow">by {owner_e} &middot; {created_e}</div>\n'
        f"    <h1>{name_e}</h1>\n"
        f"    {desc_block}\n"
        f'    <div class="meta-row">'
        f'<span class="stat-pill">{item_count} project{plural}</span>'
        f"</div>\n"
        f"    {search_bar}\n"
        f"  </div>\n</div>\n"
        f'<div class="content">\n{items_html}\n{skills_html}\n</div>\n'
        f"{modal_overlay}\n"
        f"<footer>Shared via Zip2Job</footer>\n"
        f"{enhance_js}\n"
        f"</body>\n</html>"
    )

    return head + _PORTFOLIO_CSS + body


@router.get(
    "/{portfolio_id}/info",
    response_model=PortfolioResponse,
    summary="Get portfolio metadata",
    description="Return metadata (template, color_theme, description, share_token) for a portfolio.",
)
def get_portfolio_info(portfolio_id: int) -> PortfolioResponse:
    """Fetch portfolio metadata by ID."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )
        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            share_token=portfolio.share_token,
            template=portfolio.template or "grid",
            color_theme=portfolio.color_theme or "dark",
            description=portfolio.description,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )


@router.get(
    "/{portfolio_id}",
    response_model=list[PortfolioItemResponse],
    summary="List items in a portfolio",
    description=(
        "Return all portfolio items (and their projects) contained in the specified portfolio."
    ),
)
def list_portfolio_items(portfolio_id: int) -> list[PortfolioItemResponse]:
    """List all portfolio items associated with a specific portfolio."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        items = (
            session.query(PortfolioItem)
            .filter(PortfolioItem.portfolio_id == portfolio_id)
            .order_by(PortfolioItem.display_order.asc(), PortfolioItem.updated_at.desc())
            .all()
        )

        responses: list[PortfolioItemResponse] = []
        for item in items:
            markdown = _extract_markdown(item.content)
            if not item.is_user_edited and item.project_id:
                analysis = (
                    session.query(CodeAnalysis)
                    .filter(CodeAnalysis.project_id == item.project_id)
                    .order_by(CodeAnalysis.created_at.desc())
                    .first()
                )
                if analysis and analysis.summary_text and analysis.summary_text.strip():
                    markdown = analysis.summary_text.strip()
            responses.append(
                PortfolioItemResponse(
                    id=item.id,
                    project_id=item.project_id,
                    title=item.title,
                    markdown=markdown,
                    is_user_edited=bool(item.is_user_edited),
                    is_text_block=bool(getattr(item, "is_text_block", False)),
                    source_analysis_id=getattr(item, "source_analysis_id", None),
                    portfolio_id=getattr(item, "portfolio_id", None),
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

        return responses


@router.post(
    "/{portfolio_id}/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reorder portfolio items",
    description="Set display_order on each item according to the given ID list.",
)
def reorder_portfolio_items(portfolio_id: int, request: PortfolioReorderRequest) -> Response:
    """Update display_order for each item based on position in item_ids."""
    with get_session() as session:
        for order, item_id in enumerate(request.item_ids):
            item = (
                session.query(PortfolioItem)
                .filter(PortfolioItem.id == item_id, PortfolioItem.portfolio_id == portfolio_id)
                .first()
            )
            if item is not None:
                item.display_order = order
        session.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{portfolio_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an item from a portfolio",
    description="Delete a portfolio item by ID.",
)
def remove_portfolio_item(portfolio_id: int, item_id: int) -> Response:
    """Remove a single item from a portfolio."""
    with get_session() as session:
        item = (
            session.query(PortfolioItem)
            .filter(PortfolioItem.id == item_id, PortfolioItem.portfolio_id == portfolio_id)
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio item not found.",
            )
        session.delete(item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{portfolio_id}/blocks",
    response_model=PortfolioItemResponse,
    summary="Add a text block to a portfolio",
    description="Create a free-form text/markdown block inside a portfolio.",
)
def create_text_block(
    portfolio_id: int, request: PortfolioTextBlockRequest
) -> PortfolioItemResponse:
    """Create a text block (no project) in a portfolio."""
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found."
            )

        encoded = json.dumps({"markdown": request.markdown})
        item = PortfolioItem(
            portfolio_id=portfolio_id,
            user_id=portfolio.user_id,
            title=request.title or "Text block",
            content=encoded,
            is_user_edited=True,
            is_text_block=True,
        )
        session.add(item)
        session.flush()
        session.refresh(item)

        return PortfolioItemResponse(
            id=item.id,
            project_id=None,
            title=item.title,
            markdown=request.markdown,
            is_user_edited=True,
            is_text_block=True,
            source_analysis_id=None,
            portfolio_id=portfolio_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


@router.patch(
    "/{portfolio_id}/items/{item_id}",
    response_model=PortfolioItemResponse,
    summary="Update a portfolio item's content",
    description="Update the title and/or markdown content of any portfolio item.",
)
def update_portfolio_item(
    portfolio_id: int, item_id: int, request: PortfolioItemUpdateRequest
) -> PortfolioItemResponse:
    """Update title/content of a portfolio item (works for both project items and text blocks)."""
    with get_session() as session:
        item = (
            session.query(PortfolioItem)
            .filter(PortfolioItem.id == item_id, PortfolioItem.portfolio_id == portfolio_id)
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio item not found."
            )

        if request.title is not None:
            item.title = request.title
        if request.markdown is not None:
            item.content = json.dumps({"markdown": request.markdown})
            item.is_user_edited = True

        session.flush()
        session.refresh(item)
        markdown = _extract_markdown(item.content)

        return PortfolioItemResponse(
            id=item.id,
            project_id=item.project_id,
            title=item.title,
            markdown=markdown,
            is_user_edited=bool(item.is_user_edited),
            is_text_block=bool(item.is_text_block),
            source_analysis_id=getattr(item, "source_analysis_id", None),
            portfolio_id=item.portfolio_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a portfolio",
    description="Delete a portfolio and its associated portfolio items.",
)
def delete_portfolio(portfolio_id: int) -> Response:
    """Delete a portfolio by ID.

    Associated PortfolioItem rows are deleted via ORM cascade rules.
    """
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        session.delete(portfolio)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Update portfolio metadata",
    description="Update the template and/or description of a portfolio.",
)
def update_portfolio(portfolio_id: int, request: PortfolioUpdateRequest) -> PortfolioResponse:
    """Update a portfolio's template or description."""
    valid_templates = {"grid", "showcase", "timeline"}
    with get_session() as session:
        portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found.",
            )

        valid_themes = {"dark", "light", "slate"}

        if request.template is not None:
            if request.template not in valid_templates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid template. Choose from: {', '.join(valid_templates)}",
                )
            portfolio.template = request.template

        if request.color_theme is not None:
            if request.color_theme not in valid_themes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid color theme. Choose from: {', '.join(valid_themes)}",
                )
            portfolio.color_theme = request.color_theme

        if request.description is not None:
            portfolio.description = request.description

        session.flush()
        session.refresh(portfolio)

        return PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            share_token=portfolio.share_token,
            template=portfolio.template or "grid",
            color_theme=portfolio.color_theme or "dark",
            description=portfolio.description,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
        )


@router.post(
    "/items",
    response_model=PortfolioItemResponse,
    summary="Create or update a portfolio item",
    description=(
        "Create or update a portfolio item for a project and optional analysis. "
        "Content is stored as markdown and associated with the given username."
    ),
)
def upsert_portfolio_item(request: PortfolioEditRequest) -> PortfolioItemResponse:
    """Create or update a portfolio item for the given user and project."""
    with get_session() as session:
        project = session.query(Project).filter(Project.id == request.project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        user = session.query(User).filter(User.username == request.username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        return _upsert_portfolio_item_for_user(
            session=session,
            user=user,
            project=project,
            request=request,
            portfolio_id=request.portfolio_id,
        )
