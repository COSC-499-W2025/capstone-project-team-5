FROM python:3.13-slim

# Install system deps: Node.js, texlive for LaTeX PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc g++ make \
    texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Install Python dependencies (cached layer — only reruns when deps change)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Install frontend dependencies (cached layer)
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

# Copy all source code
COPY . .

# Install the project package itself
RUN uv sync --no-dev

# Build frontend (must run from frontend/ so Tailwind finds its config)
RUN cd frontend && VITE_API_URL='' npx vite build renderer \
    && mkdir -p /app/frontend_dist \
    && cp -r /app/frontend/dist/renderer/* /app/frontend_dist/

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

EXPOSE 8000

CMD ["python", "-u", "-m", "capstone_project_team_5.api.main"]
