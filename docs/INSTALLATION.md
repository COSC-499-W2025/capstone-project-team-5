# Installation Guide

Step-by-step instructions for setting up the Zip2Job development environment.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | >= 3.13 | Backend runtime |
| **uv** | Latest | Python package manager (replaces pip) |
| **Node.js** | >= 18 | Frontend runtime |
| **npm** | >= 9 | Frontend package manager |
| **Git** | Latest | Version control |
| **LaTeX** (optional) | Any TeX distribution (e.g. MiKTeX on Windows, TeX Live on Linux/macOS) | Required only for PDF resume generation |

> **Important:** This project uses **`uv`** exclusively for Python dependency management. Do **not** use `pip` or `uv pip install`.

---

## Backend Setup

1. **Install uv** (if not already installed):
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/COSC-499-W2025/capstone-project-team-5.git
   cd capstone-project-team-5
   ```

3. **Install Python dependencies:**
   ```bash
   uv sync
   ```

4. **Install pre-commit hooks** (runs linting/formatting automatically on each commit):
   ```bash
   uv run pre-commit install
   ```

---

## Frontend Setup

1. **Install Node.js dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

---

## Environment Variables

1. **Copy the example env file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** and fill in your values:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=<your-gemini-api-key>
   LLM_MODEL=gemini-2.5-flash
   JWT_SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
   ```

   - `GEMINI_API_KEY` — required for AI-powered resume bullet generation. Get one from [Google AI Studio](https://aistudio.google.com/apikey).
   - `JWT_SECRET_KEY` — used to sign authentication tokens. Generate a strong random value.

---

## Running the Application

**Full development environment** (starts the API server, Vite dev server, and Electron window):

```bash
cd frontend
npm run dev
```

This runs three processes concurrently:
- **FastAPI** backend on `http://localhost:8000`
- **Vite** dev server on `http://localhost:5173`
- **Electron** window loading the Vite renderer

**Backend only** (useful for API development/testing):

```bash
uv run python -m uvicorn capstone_project_team_5.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Linting and Formatting

```bash
# Format code
uv run ruff format .

# Lint (check only)
uv run ruff check .

# Lint and auto-fix
uv run ruff check . --fix
```

Pre-commit hooks run these automatically on every commit.
