# Zip2Job API

A REST API for the Zip2Job project artifact analyzer built with FastAPI.

## Setup

The API is included as part of the main project. Make sure you have dependencies installed:

```bash
uv sync
```

## Running the API

Start the development server:

```bash
uv run uvicorn capstone_project_team_5.api.main:app --reload
```

Or use the provided script:

```bash
zip2job-api
```

The server runs on `http://localhost:8000` by default.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns API status |
| GET | `/api/projects` | Lists all persisted projects |
| GET | `/api/projects/{id}` | Returns a single project by ID |
| PATCH | `/api/projects/{id}` | Updates a project by ID |
| DELETE | `/api/projects/{id}` | Deletes a project by ID |
| POST | `/api/projects/upload` | Uploads a ZIP and persists detected projects |

### Example Requests

List projects:

```bash
curl http://localhost:8000/api/projects
```

Get a project by ID:

```bash
curl http://localhost:8000/api/projects/1
```

Update a project (partial):

```bash
curl -X PATCH http://localhost:8000/api/projects/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"New name","thumbnail_url":"https://example.com/cover.png"}'
```

Delete a project:

```bash
curl -X DELETE http://localhost:8000/api/projects/1
```

Upload a ZIP file:

```bash
curl -X POST http://localhost:8000/api/projects/upload \
  -F "file=@/path/to/project.zip"
```

## Interactive Documentation

When the server is running, you can access:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
src/capstone_project_team_5/api/
├── __init__.py          # Package exports
├── main.py              # FastAPI app and configuration
└── routes/
    ├── __init__.py      # Route module exports
    ├── health.py        # Health check endpoint
    └── projects.py      # Project endpoints
└── schemas/
    ├── __init__.py      # Pydantic schemas
    └── projects.py      # Project response models
```

## Running Tests

```bash
uv run pytest tests/test_api.py -v
```

## Adding New Routes

1. Create a new file in `routes/` (e.g., `routes/projects.py`)
2. Define a router with endpoints
3. Import and include the router in `main.py`

Example:

```python
# routes/example.py
from fastapi import APIRouter

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/")
def list_items():
    return {"items": []}
```

```python
# main.py
from capstone_project_team_5.api.routes import example

app.include_router(example.router, prefix="/api")
```
