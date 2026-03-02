# Zip2Job — Milestone 2 API Documentation

> **Team 5** · COSC 499 · February 2026
>
> Base URL: `http://localhost:8000`
>
> Interactive docs: `/docs` (Swagger UI) · `/redoc` (ReDoc)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Technology Stack](#2-architecture--technology-stack)
3. [Milestone 2 Requirements Traceability](#3-milestone-2-requirements-traceability)
4. [API Endpoint Documentation](#4-api-endpoint-documentation)
   - [Health](#41-health)
   - [Users & Profiles](#42-users--profiles)
   - [Work Experiences](#43-work-experiences)
   - [Educations](#44-educations)
   - [Projects](#45-projects)
   - [Skills](#46-skills)
   - [Portfolio](#47-portfolio)
   - [Consent & Privacy](#48-consent--privacy)
   - [Resumes](#49-resumes)
5. [Testing Strategy](#5-testing-strategy)
6. [Test Data](#6-test-data)
7. [Frontend Plan](#7-frontend-plan)
8. [Quick Reference — All 49 Endpoints](#8-quick-reference--all-49-endpoints)

---

## 1. Project Overview

**Zip2Job** transforms a user's coding project artifacts into professional portfolio showcases and résumé content. Users upload ZIP archives of their projects; the system analyzes code structure, detects skills, identifies collaboration patterns, determines the user's role, and generates résumé-ready bullet points — optionally enhanced by Gemini AI.

### Unique Features

- **Multi-language code analysis** — Analyzers for Python, JavaScript, Java, and C/C++ extract OOP patterns, design patterns, algorithms, and test metrics.
- **Role detection** — Automatically determines the user's role (Lead Developer, Contributor, etc.) and contribution percentage from Git history.
- **AI-enhanced bullet generation** — Gemini 2.0 Flash produces résumé bullet points; local generation is the fallback when AI consent is not given.
- **Incremental upload with deduplication** — Users can upload updated ZIPs over time; the system fingerprints files and merges new content without duplicates.
- **Human-in-the-loop customization** — Every auto-generated piece (bullets, skills, rankings, project selection) can be reviewed, reordered, and edited by the user.

---

## 2. Architecture & Technology Stack

| Layer | Technology |
|-------|-----------|
| API Framework | **FastAPI** |
| ORM | **SQLAlchemy 2.x** |
| Database | **SQLite** (file-based, zero-config) |
| Validation | **Pydantic v2** (request/response schemas) |
| Authentication | Header-based (`X-Username`) — placeholder for JWT |
| AI Integration | **Google Gemini 2.0 Flash** (optional, consent-gated) |
| Testing | **Pytest** + FastAPI `TestClient` (HTTP-level, no server needed) |
| Package Manager | **uv** |

### High-Level Flow

```
User → Frontend (planned) → FastAPI REST API → Service Layer → SQLAlchemy ORM → SQLite
                                    ↓
                          Analysis Pipeline
                    (Code Analyzers, Skill Detection,
                     Role Detection, Bullet Generation)
                                    ↓
                          Gemini AI (if consented)
```

All routes are mounted under `/api` in `main.py`, except the health endpoint at the root.

---

## 3. Milestone 2 Requirements Traceability

This section maps every Milestone 2 requirement to the specific API endpoint(s) that fulfill it.

### Functional Requirements

| # | Requirement | How We Address It | Endpoint(s) |
|---|-------------|-------------------|-------------|
| 1 | Allow incremental information by adding another zipped folder | Upload endpoint accepts multiple ZIPs over time. `project_mapping` param lets users explicitly map uploaded project names to existing project IDs for merging. Content-addressed fingerprinting detects changes. | `POST /api/projects/upload` |
| 2 | Recognize duplicate files and maintain only one | The content store computes per-file fingerprints during ingest. On incremental uploads, only new/modified files are stored. `compute_project_fingerprint()` ensures analysis is skipped when content hasn't changed. | `POST /api/projects/upload` (automatic) |
| 3 | Allow users to choose which information is represented (re-ranking, corrections, skills, showcase selection) | Projects can be reranked, marked as showcase, and have their metadata edited. Skills are detected per-project and displayed. | `POST /api/projects/rerank`, `PATCH /api/projects/{id}` (`is_showcase`, `importance_rank`), `GET /api/projects/{id}/skills/` |
| 4 | Incorporate a key role of the user in a given project | Role detection analyzes Git commit history to determine role (Lead Developer, Contributor, etc.) and contribution percentage. Users can override via PATCH. | `POST /api/projects/{id}/analyze` (auto-detects), `PATCH /api/projects/{id}` (`user_role`, `user_contribution_percentage`, `role_justification`) |
| 5 | Incorporate evidence of success (metrics, feedback) | Analysis produces code metrics (lines of code, file count, function/class count, test count), contribution data, score breakdown, and Git activity charts. | `POST /api/projects/{id}/analyze` (returns `score_breakdown`, `contribution`, `file_summary`, `git`) |
| 6 | Allow user to associate a portfolio image (thumbnail) | Full thumbnail CRUD — upload, retrieve, and delete image files per project. Validated media types (PNG, JPEG, etc.). | `PUT /api/projects/{id}/thumbnail`, `GET /api/projects/{id}/thumbnail`, `DELETE /api/projects/{id}/thumbnail` |
| 7 | Customize and save information about a portfolio showcase project | Portfolio items store editable markdown content per project. Users can modify titles, content, and associate items with named portfolios. `is_user_edited` flag tracks manual changes. | `POST /api/portfolio/items`, `POST /api/portfolio/{id}/items`, `GET /api/portfolio/{id}` |
| 8 | Customize and save the wording of a project used for a résumé item | Analysis generates `resume_bullets` (local) and `ai_bullets` (Gemini). Resume project entries have editable `bullet_points`, `title`, and `description` fields. Work experience entries have editable `bullets` and `description` fields. | `POST /api/projects/{id}/analyze` (generates bullets), `PATCH /api/users/{username}/resumes/{project_id}` (user edits wording), `PATCH /api/users/{username}/work-experiences/{id}` |
| 9 | Display textual information about a project as a portfolio showcase | Portfolio items contain rendered markdown with project name, path, and user-customized content. | `GET /api/portfolio/{id}` (returns list of `PortfolioItemResponse` with `markdown`, `title`) |
| 10 | Display textual information about a project as a résumé item | Analysis results include `resume_bullets`, `resume_bullet_source`, `ai_bullets`, and full project metadata. Resume project entries and work experiences store the final résumé text. | `POST /api/projects/{id}/analyze`, `GET /api/users/{username}/resumes`, `GET /api/users/{username}/work-experiences` |
| 11 | Use FastAPI to facilitate backend–frontend communication | Entire system is built on FastAPI with Pydantic schemas, auto-generated OpenAPI docs, and CORS middleware configured for frontend integration. | All endpoints; Swagger at `/docs` |

### Required API Endpoints

| Required Endpoint | Our Implementation | Status |
|-------------------|--------------------|--------|
| `POST /projects/upload` | `POST /api/projects/upload` — Accepts ZIP, auto-detects sub-projects, supports incremental `project_mapping` | ✅ Implemented |
| `POST /privacy-consent` | `POST /api/consent` — Creates/updates (upserts) consent record with external service, LLM, and ignore pattern preferences | ✅ Implemented |
| `GET /projects` | `GET /api/projects/` — Lists all projects ordered by most recently updated | ✅ Implemented |
| `GET /projects/{id}` | `GET /api/projects/{id}` — Returns single project with metadata, scores, role, thumbnail URL | ✅ Implemented |
| `GET /skills` | `GET /api/projects/{id}/skills/` — Returns tools + practices per project. Also `GET /api/skills/` for global skill catalog. | ✅ Implemented |
| `GET /resume/{id}` | `GET /api/users/{username}/resumes/{project_id}` — Returns a single résumé project entry with bullets. Also `GET /api/users/{username}/work-experiences/{id}` for work experience entries. | ✅ Implemented |
| `POST /resume/generate` | `POST /api/projects/{id}/analyze` — Generates `resume_bullets` and `ai_bullets` as part of project analysis. `POST /api/users/{username}/resumes/generate` — Generates PDF résumé. | ✅ Implemented |
| `POST /resume/{id}/edit` | `PATCH /api/users/{username}/resumes/{project_id}` — Partial-update résumé project entry. `PATCH /api/users/{username}/work-experiences/{id}` — Partial-update work experience (bullets, description, title, dates). | ✅ Implemented |
| `GET /portfolio/{id}` | `GET /api/portfolio/{portfolio_id}` — Lists all items in a portfolio with markdown content | ✅ Implemented |
| `POST /portfolio/generate` | `POST /api/portfolio/{portfolio_id}/items` — Adds a project to a portfolio, auto-generates default markdown content from analysis | ✅ Implemented |
| `POST /portfolio/{id}/edit` | `POST /api/portfolio/items` — Upserts portfolio item with custom markdown, title, and analysis reference | ✅ Implemented |

### Additional Endpoints (Beyond Requirements)

We implemented **49 total endpoints** (vs. 11 required), including:

- **User profile CRUD** (5 endpoints) — Contact info for résumé headers (name, email, phone, LinkedIn, GitHub, etc.)
- **Education CRUD** (5 endpoints) — Degree, institution, GPA, dates for résumé education section
- **Resume project CRUD** (6 endpoints) — Per-project résumé entries with bullets, title, description, and PDF generation
- **Consent management** (4 endpoints) — Upsert + LLM config check + available services listing
- **Project thumbnails** (3 endpoints) — Image upload/retrieve/delete for portfolio presentation
- **Project re-ranking** (1 endpoint) — Batch update display order
- **Batch analysis** (1 endpoint) — Analyze all projects in one call
- **Global skills catalog** (1 endpoint) — List all skills across projects
- **Health check** (1 endpoint) — Liveness probe

---

## 4. API Endpoint Documentation

### 4.1 Health

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/health` | Returns `{"status": "healthy"}`. Liveness/readiness probe. | 200 |

---

### 4.2 Users & Profiles

**Prefix:** `/api/users` · **Auth:** `X-Username` header (401 if missing)

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/api/users/me` | Get current authenticated user info (id, username, created_at). | 200, 401, 404 |
| `GET` | `/api/users/{username}/profile` | Get user's profile (contact info for résumé header). Own profile only. | 200, 403, 404 |
| `POST` | `/api/users/{username}/profile` | Create profile. 409 if already exists. | 201, 403, 404, 409 |
| `PATCH` | `/api/users/{username}/profile` | Upsert profile (create or partial-update). | 200, 403, 404 |
| `DELETE` | `/api/users/{username}/profile` | Delete profile. | 204, 403, 404 |

**Profile fields:** `first_name`, `last_name`, `email`, `phone`, `address`, `city`, `state`, `zip_code`, `linkedin_url`, `github_username`, `website`

---

### 4.3 Work Experiences

**Prefix:** `/api/users/{username}/work-experiences` · **Auth:** `X-Username`

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `.../work-experiences` | List all, ordered by rank. | 200, 403, 404 |
| `GET` | `.../work-experiences/{id}` | Get single entry. | 200, 403, 404 |
| `POST` | `.../work-experiences` | Create entry. Date validation enforced. | 201, 400, 403, 404 |
| `PATCH` | `.../work-experiences/{id}` | Partial-update (edit résumé bullet wording). | 200, 400, 403, 404 |
| `DELETE` | `.../work-experiences/{id}` | Delete entry. | 204, 403, 404 |

**Key fields:** `company`, `title`, `location`, `start_date`, `end_date`, `description`, `bullets` (JSON string), `is_current`, `rank`

---

### 4.4 Educations

**Prefix:** `/api/users/{username}/educations` · **Auth:** `X-Username`

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `.../educations` | List all, ordered by rank. | 200, 403, 404 |
| `GET` | `.../educations/{id}` | Get single entry. | 200, 403, 404 |
| `POST` | `.../educations` | Create entry. GPA validated 0.0–5.0. | 201, 400, 403, 404 |
| `PATCH` | `.../educations/{id}` | Partial-update. | 200, 400, 403, 404 |
| `DELETE` | `.../educations/{id}` | Delete entry. | 204, 403, 404 |

**Key fields:** `institution`, `degree`, `field_of_study`, `gpa`, `start_date`, `end_date`, `achievements`, `is_current`, `rank`

---

### 4.5 Projects

**Prefix:** `/api/projects`

#### Core CRUD

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/api/projects/` | List all projects, most recently updated first. Paginated. | 200 |
| `GET` | `/api/projects/{id}` | Get project by ID (includes role, score, thumbnail URL). | 200, 404 |
| `PATCH` | `/api/projects/{id}` | Update editable fields (name, role, rank, is_showcase, contribution %). | 200, 404 |
| `DELETE` | `/api/projects/{id}` | Delete a project. | 204, 404 |

#### Upload & Analysis

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `POST` | `/api/projects/upload` | Upload ZIP archive. Auto-detects sub-projects, handles incremental merges via `project_mapping`. Returns created/merged actions. | 201, 400, 409, 500 |
| `POST` | `/api/projects/{id}/analyze` | Analyze single project. Returns language, framework, skills, résumé bullets, AI bullets, role, score breakdown, Git stats. `?use_ai=true`, `?force=true`. | 200, 400, 404, 409 |
| `POST` | `/api/projects/analyze` | Batch analyze all projects. Skips unchanged fingerprints unless `force=true`. | 200 |

#### Thumbnails

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `PUT` | `/api/projects/{id}/thumbnail` | Upload thumbnail image. | 204, 400, 404 |
| `GET` | `/api/projects/{id}/thumbnail` | Retrieve thumbnail image file. | 200, 404 |
| `DELETE` | `/api/projects/{id}/thumbnail` | Remove thumbnail. | 204, 404 |

#### Scoring & Ranking

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/api/projects/config/score` | Get score factor configuration (contribution, diversity, duration, file_count). | 200 |
| `PUT` | `/api/projects/config/score` | Update score factor configuration. | 200 |
| `POST` | `/api/projects/rerank` | Batch update `importance_rank` for multiple projects. Validates uniqueness. | 200, 400, 404 |

---

### 4.6 Skills

**Prefix:** `/api/projects/{project_id}/skills` (per-project) and `/api/skills` (global)

#### Per-Project Skills

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/api/projects/{project_id}/skills/` | Get all skills (tools + practices) for a project. | 200, 404 |
| `GET` | `/api/projects/{project_id}/skills/tools` | Get only tools. Paginated (`?limit=`, `?offset=`). | 200, 404 |
| `GET` | `/api/projects/{project_id}/skills/practices` | Get only practices. Paginated. | 200, 404 |

#### Global Skills Catalog

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/api/skills/` | List all skills in the catalog. Filter by `?skill_type=`. Paginated. | 200 |

**Examples:** Tools — Docker, React, PostgreSQL. Practices — CI/CD, Unit Testing, Code Review.

---

### 4.7 Portfolio

**Prefix:** `/api/portfolio`

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `POST` | `/api/portfolio` | Create a named portfolio for a user. | 200, 404 |
| `GET` | `/api/portfolio/user/{username}` | List all portfolios for a user. | 200, 404 |
| `GET` | `/api/portfolio/{portfolio_id}` | List all items in a portfolio (with markdown content). | 200, 404 |
| `DELETE` | `/api/portfolio/{portfolio_id}` | Delete portfolio and items (cascade). | 204, 404 |
| `POST` | `/api/portfolio/{portfolio_id}/items` | Add project to portfolio (auto-generates default content). | 200, 404 |
| `POST` | `/api/portfolio/items` | Upsert portfolio item (create or update custom markdown). | 200, 404 |

---

### 4.8 Consent & Privacy

**Prefix:** `/api/consent`

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/api/consent/available-services` | List available external services, AI models, and ignore patterns. | 200 |
| `POST` | `/api/consent` | Create or update (upsert) consent record. Authenticated (user-specific) or anonymous (global). | 200, 201, 404 |
| `GET` | `/api/consent/latest` | Get most recent consent (with optional global fallback via `?fallback_to_global=`). | 200, 404 |
| `GET` | `/api/consent/llm/config` | Check LLM availability based on latest consent. Returns `is_allowed` and `model_preferences`. | 200 |

---

### 4.9 Resumes

**Prefix:** `/api/users/{username}/resumes` · **Auth:** `X-Username`

Manages per-project résumé entries containing bullet points, titles, and descriptions for résumé generation.

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `.../resumes` | List all résumé project entries for a user. | 200, 403, 404 |
| `GET` | `.../resumes/{project_id}` | Get résumé entry for a specific project. | 200, 403, 404 |
| `POST` | `.../resumes` | Create or upsert a résumé project entry. | 201, 400, 403, 404 |
| `POST` | `.../resumes/generate` | Generate and download a PDF résumé. Requires LaTeX (pdflatex). | 200 (PDF), 403, 404, 502 |
| `PATCH` | `.../resumes/{project_id}` | Partial-update résumé entry (title, description, bullet_points). | 200, 400, 403, 404 |
| `DELETE` | `.../resumes/{project_id}` | Delete résumé entry for a project. | 204, 403, 404 |

**Key fields:** `project_id`, `title`, `description`, `bullet_points` (list), `analysis_snapshot` (JSON)

---

## 5. Testing Strategy

### Approach

All API endpoints are tested using **FastAPI's `TestClient`**, which calls endpoints over HTTP semantics **without running a real server** — exactly as required by the milestone specification. Tests verify:

- ✅ **Correct HTTP status codes** (200, 201, 204, 400, 401, 403, 404, 409, 502)
- ✅ **Response body structure** (schema validation via Pydantic)
- ✅ **Business logic** (permission checks, duplicate detection, date validation, cascade deletes)
- ✅ **Edge cases** (missing auth, nonexistent resources, duplicate creates, forbidden access)

### Test Coverage by Module

| Test File | Module Tested | Test Count | What's Tested |
|-----------|--------------|------------|---------------|
| `test_api.py` | Health + core app | 7 | Health check, app metadata, CORS, 404 handling |
| `test_projects_api.py` | Upload, analyze, thumbnails, rerank | 27 | ZIP upload, incremental merge, analysis caching, thumbnail CRUD, batch rerank, delete |
| `test_consent_api.py` | Consent upsert + LLM config | 21 | Create/update consent, auth/ownership checks, LLM config, available services, fallback |
| `test_users_api.py` | User info + profile CRUD | 12 | GET /me, profile create/get/upsert/delete, auth enforcement |
| `test_skills_api.py` | Skills per project + global | 12 | Tools listing, practices listing, pagination, 404 handling, global skills |
| `test_portfolio_api.py` | Portfolio CRUD | 4 | Create portfolio, add items, edit items, delete |
| `test_role_api.py` | Role detection + PATCH | 10 | Set/update user_role, contribution %, boundary validation |
| `test_resumes_api.py` | Resume project CRUD | 25 | List/get/create/update/delete résumé entries, auth, PDF generation |
| `test_resume_details_api.py` | Work experiences + educations | 33 | CRUD for work experiences and educations, date validation |
| **Total API tests** | | **151** | |

### Additional Non-API Tests

Beyond the API layer, the full test suite includes **713 total tests** covering:
- Code analyzers (Python, JavaScript, Java, C/C++)
- Skill detection (local + LLM-enhanced)
- Contribution metrics and collaboration detection
- File diffing and deduplication
- Bullet generation (local and AI)
- Upload and incremental upload logic
- Service layer (user profile, work experience, education, portfolio persistence)
- Database schema and integration tests
- LLM providers and service layer

### Running Tests

```bash
# Run all tests
uv run pytest

# Run only API tests
uv run pytest tests/test_api.py tests/test_projects_api.py tests/test_consent_api.py \
  tests/test_users_api.py tests/test_skills_api.py tests/test_portfolio_api.py \
  tests/test_role_api.py tests/test_resumes_api.py tests/test_resume_details_api.py -v

# Run with coverage
uv run pytest --cov=capstone_project_team_5
```

---

## 6. Test Data

As required by the milestone specification, we provide test data archives:

### Incremental Upload Test Data (Same Project, Two Snapshots)

Two ZIP files for the same project at different points in time, demonstrating incremental upload and deduplication:

```
snapshot-v1.zip:                    snapshot-v2.zip:
  ./code_collab_proj/                 ./code_collab_proj/
    app/                                app/
      main.py                             main.py        (modified)
      utils.py                            utils.py       (unchanged → deduped)
                                          api.py         (new file)
    test/                               test/
      test_main.py                        test_main.py   (modified)
                                          test_api.py    (new file)
    doc/                                doc/
      README.md                           README.md      (modified)
```

### Multi-Project Test Data (Individual + Collaborative)

One ZIP containing multiple projects of different types:

```
test-data.zip:
  ./code_indiv_proj/          # Individual Python project (single author)
  ./code_collab_proj/         # Collaborative project (multiple Git authors)
  ./text_indiv_proj/          # Non-code text project (documentation)
```

These archives are used by `test_upload.py`, `test_upload_multi_project.py`, and `test_incremental_upload.py` to verify:
- Sub-project auto-detection
- Collaboration flag detection (`is_collaborative`)
- Incremental merge with `project_mapping`
- Duplicate file fingerprinting

---

## 7. Frontend Plan

### Current Status

The system currently operates as a **fully functional REST API** (49 endpoints). All backend functionality is accessible via HTTP calls. The API has CORS middleware configured (`allow_origins=["*"]`) for frontend integration.

### Planned Frontend Stack

| Technology | Purpose |
|-----------|---------|
| **React** | UI framework |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Styling |
| **Axios / Fetch** | API client |

### Planned Frontend Pages / Views

| Page | Description | Key API Calls |
|------|-------------|---------------|
| **Login / Signup** | User authentication | `POST /api/users` (planned), `GET /api/users/me` |
| **Dashboard** | Overview of uploaded projects with scores and rankings | `GET /api/projects/`, `POST /api/projects/rerank` |
| **Upload** | Drag-and-drop ZIP upload with progress | `POST /api/projects/upload` |
| **Project Detail** | Analysis results, skills, role, contribution chart, editable fields | `GET /api/projects/{id}`, `POST /api/projects/{id}/analyze`, `GET /api/projects/{id}/skills/`, `PATCH /api/projects/{id}` |
| **Résumé Builder** | Profile info + work experiences + education + per-project résumé entries, reorderable with editable bullet points | `GET/PATCH /api/users/{u}/profile`, `GET/POST/PATCH /api/users/{u}/work-experiences`, `GET/POST/PATCH /api/users/{u}/educations`, `GET/POST/PATCH /api/users/{u}/resumes` |
| **Portfolio Editor** | Select projects for showcase, edit markdown content, manage thumbnails | `POST /api/portfolio`, `POST /api/portfolio/{id}/items`, `POST /api/portfolio/items`, `PUT /api/projects/{id}/thumbnail` |
| **Settings / Consent** | Privacy consent, AI feature toggle, ignore patterns | `POST /api/consent`, `GET /api/consent/available-services`, `GET /api/consent/llm/config` |

### Human-in-the-Loop UX Flow

```
Upload ZIP → Auto-analyze → Review results → Customize:
                                                ├─ Re-rank projects
                                                ├─ Edit role / contribution %
                                                ├─ Select showcase projects
                                                ├─ Edit résumé bullets
                                                ├─ Add thumbnails
                                                └─ Build portfolio → Export
```

Every auto-generated piece is editable. The frontend will present auto-detected values as defaults that the user can accept, modify, or override.

---

## 8. Quick Reference — All 49 Endpoints

```
GET    /health                                          # Liveness probe

GET    /api/users/me                                    # Current user info
GET    /api/users/{username}/profile                    # Get profile
POST   /api/users/{username}/profile                    # Create profile
PATCH  /api/users/{username}/profile                    # Upsert profile
DELETE /api/users/{username}/profile                    # Delete profile

GET    /api/users/{username}/work-experiences            # List work experiences
GET    /api/users/{username}/work-experiences/{id}       # Get work experience
POST   /api/users/{username}/work-experiences            # Create work experience
PATCH  /api/users/{username}/work-experiences/{id}       # Update work experience
DELETE /api/users/{username}/work-experiences/{id}       # Delete work experience

GET    /api/users/{username}/educations                  # List educations
GET    /api/users/{username}/educations/{id}             # Get education
POST   /api/users/{username}/educations                  # Create education
PATCH  /api/users/{username}/educations/{id}             # Update education
DELETE /api/users/{username}/educations/{id}             # Delete education

GET    /api/users/{username}/resumes                     # List résumé projects
GET    /api/users/{username}/resumes/{project_id}        # Get résumé project
POST   /api/users/{username}/resumes                     # Create résumé project
POST   /api/users/{username}/resumes/generate            # Generate PDF résumé
PATCH  /api/users/{username}/resumes/{project_id}        # Update résumé project
DELETE /api/users/{username}/resumes/{project_id}        # Delete résumé project

GET    /api/projects/                                    # List projects
GET    /api/projects/{id}                                # Get project
PATCH  /api/projects/{id}                                # Update project
DELETE /api/projects/{id}                                # Delete project
POST   /api/projects/upload                              # Upload ZIP archive
POST   /api/projects/{id}/analyze                        # Analyze single project
POST   /api/projects/analyze                             # Analyze all projects
PUT    /api/projects/{id}/thumbnail                      # Upload thumbnail
GET    /api/projects/{id}/thumbnail                      # Get thumbnail
DELETE /api/projects/{id}/thumbnail                      # Delete thumbnail
GET    /api/projects/config/score                        # Get score config
PUT    /api/projects/config/score                        # Update score config
POST   /api/projects/rerank                              # Batch rerank projects

GET    /api/projects/{id}/skills/                        # Get all skills for project
GET    /api/projects/{id}/skills/tools                   # Get tools (paginated)
GET    /api/projects/{id}/skills/practices               # Get practices (paginated)
GET    /api/skills/                                      # List global skill catalog

POST   /api/portfolio                                    # Create portfolio
GET    /api/portfolio/user/{username}                    # List user's portfolios
GET    /api/portfolio/{portfolio_id}                     # List portfolio items
DELETE /api/portfolio/{portfolio_id}                     # Delete portfolio
POST   /api/portfolio/{portfolio_id}/items               # Add project to portfolio
POST   /api/portfolio/items                              # Upsert portfolio item

GET    /api/consent/available-services                   # List available services
POST   /api/consent                                      # Upsert consent record
GET    /api/consent/latest                               # Get latest consent
GET    /api/consent/llm/config                           # LLM config status
```

### Endpoint Count Summary

| Module | Endpoints | Auth | CRUD Complete? |
|--------|-----------|------|----------------|
| Health | 1 | — | N/A |
| Users & Profiles | 5 | ✅ `X-Username` | ✅ Full CRUD |
| Work Experiences | 5 | ✅ `X-Username` | ✅ Full CRUD |
| Educations | 5 | ✅ `X-Username` | ✅ Full CRUD |
| Resumes | 6 | ✅ `X-Username` | ✅ Full CRUD + PDF |
| Projects | 13 | — | ✅ Full CRUD + Upload + Analyze + Thumbnails + Rerank |
| Skills | 4 | — | Read-only (by design — auto-detected) |
| Portfolio | 6 | — | ✅ Create + Read + Delete + Edit |
| Consent | 4 | Optional `X-Username` | ✅ Upsert + Read + LLM Config |
| **Total** | **49** | | |
