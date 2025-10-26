"""
Constants for skill detection in project directories.
"""

# Directories and files to skip during scanning
SKIP_DIRS = {
    # Dependencies
    "node_modules",
    "vendor",
    "packages",
    # Python environments
    "venv",
    ".venv",
    "env",
    ".env",
    "virtualenv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # Version control
    ".git",
    ".svn",
    ".hg",
    # IDEs
    ".idea",
    ".vscode",
    ".vs",
    # Build outputs
    "build",
    "dist",
    "out",
    "target",
    ".next",
    ".nuxt",
    # Caches
    ".cache",
    "coverage",
    ".nyc_output",
    # OS files
    ".ds_store",
    "thumbs.db",
}

# Tool detection based on exact file names (case-insensitive)
TOOL_FILE_NAMES = {
    "Docker": {"dockerfile", "dockerfile.dev", "dockerfile.prod"},
    "PyTest": {"pytest.ini"},
    "Jest": {"jest.config.js", "jest.config.ts", "jest.config.json"},
    "Cypress": {"cypress.config.js", "cypress.config.ts", "cypress.json"},
    "Ruff": {"ruff.toml"},
    "Tauri": {"tauri.conf.json"},
    "uv": {"uv.lock"},
    "npm": {"package.json", "package-lock.json"},
    "yarn": {"yarn.lock"},
    "pnpm": {"pnpm-lock.yaml"},
}

# Tool detection based on file name patterns (substring or extension match)
TOOL_FILE_PATTERNS = {
    "Docker": {"docker-compose"},  # Matches docker-compose.yml, docker-compose.yaml, etc.
    "SQL": {".sql"},  # Extension match
}

# Practice detection based on exact file names
PRACTICES_FILE_NAMES = {
    "Code Quality Enforcement": {
        ".flake8",
        "pylintrc",
        ".pylintrc",
        "mypy.ini",
        "ruff.toml",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.json",
        "prettier.config.js",
        ".prettierrc",
    },
    "Environment Management": {
        "requirements.txt",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        ".nvmrc",
        ".tool-versions",
    },
    "API Design": {"openapi.yaml", "openapi.yml", "swagger.json", "swagger.yaml"},
    "Version Control (Git)": {".gitignore", ".gitattributes"},
    "CI/CD": {".gitlab-ci.yml", ".gitlab-ci.yaml"},
}

# Practice detection based on path patterns (use Path parts, not separators)
PRACTICES_PATH_PATTERNS = {
    "Test-Driven Development (TDD)": {"tests", "test"},
    "Automated Testing": {"tests", "test", "__tests__"},
    "CI/CD": {".github/workflows", ".gitlab"},
    "Documentation Discipline": {"docs", "documentation"},
    "API Design": {"api"},
    "Modular Architecture": {"src", "core", "domain", "modules"},
}

# Practice detection based on file name patterns
PRACTICES_FILE_PATTERNS = {
    "Documentation Discipline": {"readme"},  # Matches README.md, readme.txt, etc.
    "Code Review": {"pull_request_template", "pr_template"},
}
