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
    └── health.py        # Health check endpoint
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
