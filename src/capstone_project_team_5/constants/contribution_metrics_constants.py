"""
Constants for categorizing file contributions by type
(code, tests, design, documentation, data, etc.)
"""

# === CODE FILES ===
CODE_FILE_PATTERNS = [
    r"\.py$",
    r"\.ipynb$",
    r"\.js$",
    r"\.ts$",
    r"\.jsx$",
    r"\.tsx$",
    r"\.java$",
    r"\.kt$",
    r"\.cpp$",
    r"\.c$",
    r"\.cs$",
    r"\.go$",
    r"\.rb$",
    r"\.php$",
    r"\.swift$",
    r"\.rs$",
    r"\.scala$",
    r"\.dart$",
    r"\.lua$",
    r"\.pl$",
    r"\.pm$",
    r"\.sh$",
    r"\.bash$",
    r"\.ps1$",
    r"\.r$",
    r"\.R$",
    r"\.jl$",
    r"\.ini$",
    r"\.json$",  # app configs
    r"\.vue$",
    r"\.svelte$",
    r"\.astro$",
    r"\.erl$",
    r"\.ex$",
    r"\.exs$",
]

# === TEST FILES ===
# Includes directories (e.g. tests/, __tests__/, specs/) and filenames
TEST_FILE_PATTERNS = [
    r"(^|/|\\)tests?(/|\\)",  # e.g. tests/, test/
    r"(^|/|\\)__tests__(/|\\)",  # JS/TS convention
    r"test_",  # test_ prefix (Python)
    r"_test\.",  # _test suffix (Go)
    r"spec\.",  # spec. convention
]

# === DESIGN / MEDIA FILES ===
DESIGN_FILE_PATTERNS = [
    r"\.png$",
    r"\.jpg$",
    r"\.jpeg$",
    r"\.svg$",
    r"\.gif$",
    r"\.bmp$",
    r"\.fig$",
    r"\.xd$",
    r"\.psd$",
    r"\.ai$",
    r"\.sketch$",
    r"\.mp4$",
    r"\.mov$",
    r"\.avi$",
    r"\.webm$",
]

# === DOCUMENTATION FILES ===y
DOCUMENTATION_FILE_PATTERNS = [
    r"\.md$",
    r"\.rst$",
    r"\.txt$",
    r"\.pdf$",
    r"\.docx?$",
    r"(^|/|\\)docs?(/|\\)",  # e.g. docs/ folder
    r"README",
    r"CHANGELOG",
    r"CONTRIBUTING",
    r"LICENSE",
]

# === DATA / CONFIG FILES ===
DATA_FILE_PATTERNS = [
    r"\.csv$",
    r"\.tsv$",
    r"\.xlsx?$",
    r"\.parquet$",
    r"\.feather$",
    r"\.sav$",
    r"\.dta$",
    r"\.jsonl$",
    r"\.pkl$",
    r"\.rds$",
    r"\.npz?$",
    r".sql",
    r".db",
]

# === MISC / BUILD / INFRASTRUCTURE ===
DEVOPS_FILE_PATTERNS = [
    r"(^|/)(Dockerfile|Makefile)$",
    r"\.dockerignore$",
    r"\.gitignore$",
    r"\.env(\.example)?$",
    r"\.yaml$",
    r"\.yml$",
    r"\.tf$",
    r"\.tfvars$",
    r"\.hcl$",  # Terraform / infra
    r"\.cfg$",
    r"\.ini$",  # generic configs
    r"\.lock$",
    r"\.toml$",
    r"\.mk$",  # dependency mgmt, make scripts
    r"\.workflow$",
    r"^\.github/",
    r"^\.gitlab-ci",  # CI/CD
    r".python-version",
]

# === CATEGORY DEFINITIONS ===
CONTRIBUTION_CATEGORIES = {
    "test": TEST_FILE_PATTERNS,
    "code": CODE_FILE_PATTERNS,
    "design": DESIGN_FILE_PATTERNS,
    "document": DOCUMENTATION_FILE_PATTERNS,
    "data": DATA_FILE_PATTERNS,
    "devops": DEVOPS_FILE_PATTERNS,
}

SKIP_DIRS = {
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    "build",
    "dist",
}
