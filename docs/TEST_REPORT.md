# Test Report

Overview of all test files and testing strategies used across the Zip2Job project.

---

## Running Tests

**Backend tests** (pytest):

```bash
# Run all backend tests
uv run pytest

# Run a single test file
uv run pytest tests/test_users_api.py

# Run a specific test function
uv run pytest tests/test_users_api.py::test_login

# Run with verbose output
uv run pytest -v
```

**Frontend tests** (Jest):

```bash
cd frontend
npm test
```

---

## Test Strategies

The project uses several complementary testing strategies to ensure correctness across the full stack:

### 1. API Integration Tests
- **What:** Test full HTTP request/response cycles against the real FastAPI application.
- **How:** Uses FastAPI's `TestClient` to send requests to API endpoints. An `api_db` fixture (defined in `conftest.py`) provides each test with an isolated temporary SQLite database. The `auth_headers()` helper generates valid JWT tokens for authenticated requests.
- **Why:** Verifies that routes, authentication, request validation, service logic, and database persistence all work together end-to-end.

### 2. Unit Tests with File System Fixtures
- **What:** Test individual functions and classes (analyzers, detection logic, upload parsing) in isolation.
- **How:** Uses pytest's `tmp_path` fixture to create temporary directories with test files (e.g., Python scripts, Java files, `package.json`). Analyzers process these files and results are verified with assertions.
- **Why:** Ensures each language analyzer, skill detector, and utility function produces correct output for known inputs without needing a running server or database.

### 3. Unit Tests with Mocking
- **What:** Test service-layer code that depends on external systems (LLM APIs, database sessions).
- **How:** Uses `unittest.mock` (`MagicMock`, `patch`) and custom mock classes (e.g., `MockProvider` for LLM tests). Database-dependent tests use in-memory SQLAlchemy sessions.
- **Why:** Isolates business logic from external dependencies, making tests fast and deterministic.

### 4. Frontend DOM / Component Tests
- **What:** Test React component rendering, user interactions, and state management.
- **How:** Uses Jest with `jsdom` environment and React Testing Library (`render`, `screen`, `waitFor`, `fireEvent`). API calls are mocked with `jest.fn()`. Components are wrapped in `AppContext` providers with controlled state.
- **Why:** Validates that the UI renders correctly, responds to user input, and displays data from the backend as expected.

### 5. Frontend API Utility Tests
- **What:** Test the frontend's API helper functions (fetch wrappers, response parsing).
- **How:** Mocks `global.fetch` with `jest.fn()` and uses helper functions (`mockJson`, `mockBinary`) to simulate server responses.
- **Why:** Ensures the API layer correctly handles success, error, and edge-case responses before they reach components.

---

## Test Infrastructure

| Component | Implementation |
|-----------|---------------|
| **Test isolation** | Each test gets a fresh temporary SQLite database via `api_db` fixture (`conftest.py`) |
| **Auto-fixture injection** | `pytest_collection_modifyitems` in `conftest.py` automatically applies `api_db` to any test file with "api" in its name |
| **Authentication** | `auth_headers()` generates valid JWT Bearer tokens for protected endpoint tests |
| **Temporary files** | `tmp_path` fixture creates disposable directories for file-based tests |
| **Frontend mocking** | `jest.fn()` on `window.api` and `global.fetch` for API simulation |

---

## Backend Test Files

| Test File | What It Tests | Strategy |
|-----------|---------------|----------|
| `test_api.py` | API health/status endpoints | API Integration |
| `test_users_api.py` | User registration, login, profile CRUD | API Integration |
| `test_consent_api.py` | AI consent management endpoints | API Integration |
| `test_portfolio_api.py` | Portfolio creation and item management | API Integration |
| `test_projects_api.py` | Project listing and retrieval | API Integration |
| `test_resumes_api.py` | Resume CRUD and generation endpoints | API Integration |
| `test_resume_details_api.py` | Resume detail retrieval | API Integration |
| `test_role_api.py` | Role detection API endpoints | API Integration |
| `test_skills_api.py` | Skills listing API endpoints | API Integration |
| `test_setup_api.py` | First-time setup flow endpoints | API Integration |
| `test_tutorial_api.py` | Tutorial state management endpoints | API Integration |
| `test_proficiency_api.py` | Skill proficiency endpoints | API Integration |
| `test_user_profile_api.py` (cached) | User profile API edge cases | API Integration |
| `test_python_analyzer.py` | Python AST analysis (OOP, inheritance, classes) | Unit (file fixtures) |
| `test_java_analyzer.py` | Java code analysis (encapsulation, OOP) | Unit (file fixtures) |
| `test_c_analyzer.py` | C/C++ file analysis (comments, stats, summaries) | Unit (file fixtures) |
| `test_js_code_analyzer.py` | JavaScript project analysis (deps, code files) | Unit (file fixtures) |
| `test_skill_detection.py` | Skill extraction from config files | Unit (file fixtures) |
| `test_detection.py` | General detection logic | Unit |
| `test_role_detector.py` | Role classification (solo dev, architect, etc.) | Unit (mock objects) |
| `test_role_constants.py` | Role definition constants | Unit |
| `test_role_persistence.py` | Role data persistence | Unit |
| `test_upload.py` | ZIP upload parsing and tree structure | Unit (file fixtures) |
| `test_upload_multi_project.py` | Multi-project ZIP upload handling | Unit (file fixtures) |
| `test_incremental_upload.py` | Incremental upload (v1 then v2) processing | Unit (file fixtures) |
| `test_file_walker.py` | File tree traversal logic | Unit |
| `test_file_diff.py` | File diff computation between uploads | Unit |
| `test_code_analysis_persistence.py` | Analysis result storage/retrieval | Unit |
| `test_code_analysis_integration.py` | End-to-end code analysis pipeline | Integration |
| `test_bullet_generator.py` | Resume bullet point generation | Unit |
| `test_local_bullets.py` | Local (non-AI) bullet generation | Unit |
| `test_js_bullets.py` | JavaScript-specific bullet generation | Unit |
| `test_ai_bullets.py` (cached) | AI-powered bullet generation | Unit (mocked) |
| `test_resume_generator.py` | PDF resume rendering pipeline | Unit (mocked) |
| `test_templates.py` | Resume template rendering | Unit |
| `test_llm_service.py` | LLM provider initialization and calls | Unit (mocked) |
| `test_llm_providers.py` | LLM provider configuration | Unit |
| `test_consent.py` | Consent model logic | Unit |
| `test_portfolio_persistence.py` | Portfolio data persistence | Unit |
| `test_portfolio_deletion.py` | Portfolio cascade deletion | Unit |
| `test_portfolio_service.py` | Portfolio business logic | Unit |
| `test_project_analysis.py` | Project-level analysis aggregation | Unit |
| `test_project_chronology.py` | Project timeline ordering | Unit |
| `test_project_rerank.py` | Project ranking algorithm | Unit |
| `test_project_summary.py` | Project summary generation | Unit |
| `test_project_thumbnail_url_service.py` | Thumbnail URL resolution | Unit |
| `test_top_projects.py` | Top project selection logic | Unit |
| `test_contribution_metrics.py` | Contribution metric calculations | Unit |
| `test_collab_detect.py` | Collaboration detection | Unit |
| `test_skill_persistence.py` | Skill data persistence | Unit |
| `test_user_config.py` | User configuration management | Unit |
| `test_user_profile.py` | User profile model logic | Unit |
| `test_user_profile_service.py` | User profile service layer | Unit |
| `test_user_role_type.py` | User role type definitions | Unit |
| `test_users_skill_list.py` | User skill list management | Unit |
| `test_user_skill_list_proficiency.py` | Skill proficiency scoring | Unit |
| `test_user_skill_model.py` | User skill ORM model | Unit |
| `test_education_service.py` | Education CRUD service | Unit |
| `test_work_experience_service.py` | Work experience CRUD service | Unit |
| `test_export.py` | Data export functionality | Unit |
| `test_git_utils.py` | Git utility functions | Unit |
| `test_item_retriever.py` | Item retrieval logic | Unit |
| `test_artifact_miner_schema.py` | Artifact miner data schema | Unit |
| `test_cli_per_project.py` | CLI per-project mode | Unit |
| `test_main.py` | Application main entrypoint | Unit |
| `test_tui_rendering.py` | TUI component rendering | Unit |
| `test_db_integration.py` | Database connection and schema setup | Integration |
| `test_test_analysis.py` | Test file detection in uploads | Unit |

---

## Frontend Test Files

| Test File | What It Tests | Strategy |
|-----------|---------------|----------|
| `App.dom.test.jsx` | App component boot states, consent flow, navigation, auth errors | DOM / Component |
| `Resumes.dom.test.jsx` | Resumes page rendering and interactions | DOM / Component |
| `Dashboard.dom.test.jsx` | Dashboard page rendering | DOM / Component |
| `Portfolio.dom.test.jsx` | Portfolio page rendering | DOM / Component |
| `Projects.dom.test.jsx` | Projects page rendering | DOM / Component |
| `Skills.dom.test.jsx` | Skills page rendering | DOM / Component |
| `Profile.dom.test.jsx` | Profile page rendering | DOM / Component |
| `Education.dom.test.jsx` | Education page rendering | DOM / Component |
| `Experience.dom.test.jsx` | Work experience page rendering | DOM / Component |
| `ConsentSetup.dom.test.jsx` | AI consent setup flow | DOM / Component |
| `GuidedSetup.dom.test.jsx` | Guided setup wizard | DOM / Component |
| `ZippyMenu.dom.test.jsx` | Navigation menu component | DOM / Component |
| `api.test.js` | Frontend API fetch wrappers | Unit (mocked fetch) |
| `rendererUtils.dom.test.js` | Renderer utility functions | Unit |
| `useCrudList.dom.test.jsx` | useCrudList custom hook | DOM / Hook |
| `DashboardPage.pulse.test.jsx` | Dashboard pulse animation | DOM / Component |
