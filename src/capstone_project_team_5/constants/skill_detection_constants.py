TOOL_FILE_NAMES = {
    "Docker": ["dockerfile"],
    "PyTest": ["pytest.ini"],
    "Jest": ["jest"],
    "Cypress": ["cypress"],
    "Ruff": ["ruff.toml"],
    "Tauri": ["tauri.conf.json"],
    "uv": ["uv.lock"],
}

TOOL_FILE_PATTERNS = {
    "Docker": ["docker-compose"],
    "SQL": [".sql"],
}

PRACTICES_FILE_NAMES = {
    "Code Quality Enforcement": [
        ".flake8",
        "pylintrc",
        "mypy.ini",
        "ruff.toml",
        ".eslintrc",
        "prettier.config.js",
    ],
    "Environment Management": [
        "requirements.txt",
        "poetry.lock",
        "Pipfile",
        ".nvmrc",
        ".tool-versions",
    ],
    "API Design": ["openapi.yaml", "swagger.json"],
    "Version Control (Git)": [".gitignore"],
}

PRACTICES_PATH_PATTERNS = {
    "Test-Driven Development (TDD)": ["tests"],
    "Automated Testing": ["tests"],
    "CI/CD": [".github/workflows", ".github\\workflows"],
    "Documentation Discipline": ["docs"],
    "API Design": ["/api/", "\\api\\"],
    "Modular Architecture": ["src", "core", "domain", "modules"],
    "Version Control (Git)": [".git"],
    "Team Collaboration": ["logs", "minutes"],
}

PRACTICES_FILE_PATTERNS = {
    "CI/CD": ["gitlab-ci.yml"],
    "Documentation Discipline": ["readme"],
    "Code Review": ["pull_request_template"],
}
