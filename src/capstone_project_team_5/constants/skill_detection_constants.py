"""
Constants for skill detection in project directories.
"""

from enum import Enum


class SkillType(str, Enum):
    """Enum for skill types used in ProjectSkill table."""

    TOOL = "tool"
    PRACTICE = "practice"


# Directories and files to skip during scanning (case-insensitive)
SKIP_DIRS = {
    # Dependencies
    "node_modules",
    "vendor",
    "packages",
    "bower_components",
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
    ".tox",
    ".nox",
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
    ".gradle",
    # Caches
    ".cache",
    "coverage",
    ".nyc_output",
    # OS files
    ".ds_store",
    "thumbs.db",
}

# ============================================================================
# TOOL DETECTION - Exact file names (CASE-SENSITIVE)
# Included common variants where projects differ in casing conventions

TOOL_FILE_NAMES = {
    # Containerization
    "Docker": {
        # Standard case
        "Dockerfile",
        "Dockerfile.dev",
        "Dockerfile.prod",
        "Dockerfile.test",
        # Lowercase
        "dockerfile",
        "dockerfile.dev",
        "dockerfile.prod",
        "dockerfile.test",
        ".dockerignore",
    },
    "Podman": {
        "podman-compose.yml",
        "podman-compose.yaml",
    },
    # Package Managers (mostly lowercase by convention)
    "npm": {
        "package.json",
        "package-lock.json",
    },
    "yarn": {
        "yarn.lock",
    },
    "pnpm": {
        "pnpm-lock.yaml",
    },
    "Poetry": {
        "poetry.lock",
    },
    "Cargo": {
        "Cargo.toml",
        "Cargo.lock",
        "cargo.toml",  # Support lowercase variant
        "cargo.lock",
    },
    "Go Modules": {
        "go.mod",
        "go.sum",
    },
    "Composer": {
        "composer.json",
        "composer.lock",
    },
    "Bundler": {
        "Gemfile.lock",
        "Gemfile",
        "gemfile",
        "gemfile.lock",
    },
    "NuGet": {
        "packages.config",
        ".csproj",
        ".vbproj",
        ".fsproj",
    },
    "pip": {
        "requirements.txt",
        "requirements-dev.txt",
        "requirements.in",
        "requirements-test.txt",
        "requirements-prod.txt",
    },
    # Build Tools - Frontend (config files are lowercase by convention)
    "Webpack": {
        "webpack.config.js",
        "webpack.config.ts",
        "webpack.config.mjs",
    },
    "Vite": {
        "vite.config.js",
        "vite.config.ts",
        "vite.config.mjs",
    },
    "Rollup": {
        "rollup.config.js",
        "rollup.config.mjs",
        "rollup.config.ts",
    },
    "Parcel": {
        ".parcelrc",
    },
    "esbuild": {
        "esbuild.config.js",
    },
    "Turbopack": {
        "turbopack.config.js",
    },
    # Build Tools - Backend
    "Gradle": {
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "gradlew",
    },
    "Maven": {
        "pom.xml",
    },
    "Make": {
        "Makefile",
        "makefile",
        "GNUmakefile",
        "gnumakefile",
        "Makefile.am",
        "Makefile.in",
        "makefile.am",
        "makefile.in",
    },
    "CMake": {
        "CMakeLists.txt",
        "cmakelists.txt",
    },
    "Bazel": {
        "BUILD",
        "BUILD.bazel",
        "WORKSPACE",
        "WORKSPACE.bazel",
        ".bazelrc",
        # Support lowercase
        "build",
        "build.bazel",
        "workspace",
        "workspace.bazel",
    },
    # Testing Frameworks (config files are lowercase by convention)
    "PyTest": {
        "pytest.ini",
        ".pytest.ini",
    },
    "coverage.py": {
        ".coveragerc",
    },
    "Jest": {
        "jest.config.js",
        "jest.config.ts",
        "jest.config.json",
        "jest.config.mjs",
    },
    "Vitest": {
        "vitest.config.js",
        "vitest.config.ts",
        "vitest.config.mjs",
    },
    "Mocha": {
        ".mocharc.js",
        ".mocharc.json",
        ".mocharc.yaml",
        ".mocharc.yml",
        "mocha.opts",
    },
    "Cypress": {
        "cypress.config.js",
        "cypress.config.ts",
        "cypress.json",
    },
    "RSpec": {
        ".rspec",
    },
    # Linters & Formatters (config files are lowercase by convention)
    "Ruff": {
        "ruff.toml",
    },
    "Black": {
        "black.toml",
    },
    "isort": {
        ".isort.cfg",
    },
    "Stylelint": {
        ".stylelintrc",
        ".stylelintrc.json",
        ".stylelintrc.yaml",
        ".stylelintrc.yml",
        "stylelint.config.js",
    },
    "Rubocop": {
        ".rubocop.yml",
    },
    "Checkstyle": {
        "checkstyle.xml",
    },
    "TSLint": {
        "tslint.json",
    },
    # CI/CD Tools
    "Jenkins": {
        "Jenkinsfile",
        "jenkinsfile",
    },
    "Travis CI": {
        ".travis.yml",
        ".travis.yaml",
    },
    "Azure Pipelines": {
        "azure-pipelines.yml",
        "azure-pipelines.yaml",
    },
    "Bitbucket Pipelines": {
        "bitbucket-pipelines.yml",
    },
    "CircleCI": {
        "circle.yml",
    },
    # Infrastructure as Code (config files are lowercase by convention)
    "Terraform": {
        "terraform.tfvars",
        ".terraform.lock.hcl",
    },
    "Ansible": {
        "ansible.cfg",
    },
    "Pulumi": {
        "pulumi.yaml",
        "pulumi.yml",
        "Pulumi.yaml",
        "Pulumi.yml",
    },
    # Database & ORM (config files are lowercase by convention)
    "Prisma": {
        "schema.prisma",
    },
    "Sequelize": {
        ".sequelizerc",
    },
    "TypeORM": {
        "ormconfig.json",
        "ormconfig.js",
        "ormconfig.yml",
        "ormconfig.env",
    },
    "Alembic": {
        "alembic.ini",
    },
    "Flyway": {
        "flyway.conf",
    },
    "Liquibase": {
        "liquibase.properties",
    },
    "Nx": {
        "nx.json",
        "workspace.json",
    },
    "Turborepo": {
        "turbo.json",
    },
    "Lerna": {
        "lerna.json",
    },
    "Rush": {
        "rush.json",
    },
    "pnpm Workspaces": {
        "pnpm-workspace.yaml",
    },
    "GraphQL": {
        "graphql.config.js",
    },
    "Next.js": {
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
    },
    "Nuxt": {
        "nuxt.config.js",
        "nuxt.config.ts",
    },
    "Remix": {
        "remix.config.js",
        "remix.config.ts",
    },
    "SvelteKit": {
        "svelte.config.js",
    },
    "Astro": {
        "astro.config.mjs",
        "astro.config.js",
        "astro.config.ts",
    },
    "Tauri": {
        "tauri.conf.json",
    },
    # Development Tools (config files are lowercase by convention)
    "Nodemon": {
        "nodemon.json",
    },
    "uv": {
        "uv.lock",
    },
    "EditorConfig": {
        ".editorconfig",
    },
    "direnv": {
        ".envrc",
    },
    # State Management (config files are lowercase by convention)
    "MobX": {
        ".mobxrc",
    },
    "Apollo Client": {
        "apollo.config.js",
    },
    # Security & Dependency Management (config files are lowercase by convention)
    "Renovate": {
        "renovate.json",
        ".renovaterc",
        ".renovaterc.json",
    },
    "Snyk": {
        ".snyk",
    },
    # Pre-commit Hooks (config files are lowercase by convention)
    "pre-commit": {
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
    },
    "lint-staged": {
        ".lintstagedrc",
        ".lintstagedrc.json",
        ".lintstagedrc.js",
        "lint-staged.config.js",
    },
    "commitlint": {
        "commitlint.config.js",
    },
    # Serverless (config files can vary)
    "Serverless Framework": {
        "serverless.yml",
        "serverless.yaml",
        "serverless.json",
    },
    "AWS SAM": {
        "sam.template.yaml",
        "template.yaml",
    },
    "Netlify": {
        "netlify.toml",
    },
    "Vercel": {
        "vercel.json",
    },
    # Helm
    "Helm": {
        "Chart.yaml",
        "chart.yaml",
    },
}

# ============================================================================
# TOOL DETECTION - File name patterns
# These are checked case-insensitively since they're patterns

TOOL_FILE_NAME_PATTERNS = {
    "Docker": {"docker-compose"},
    "SQL": {".sql"},
    "Terraform": {".tf"},
    "gRPC": {".proto"},
    "GraphQL": {".graphql", ".gql"},
    "Go": {"_test.go"},
    "CloudFormation": {".template.json", ".template.yaml"},
    "Postman": {"postman_collection.json"},
}

# ============================================================================
# TOOL DETECTION - File path patterns
# These are checked case-insensitively since they're patterns

TOOL_FILE_PATH_PATTERNS = {
    "Dependabot": {".github/dependabot.yml"},
}

# ============================================================================
# TOOL DETECTION - Directory patterns (case-insensitive)
# Directory names are matched case-insensitively for flexibility

TOOL_DIRECTORY_PATTERNS = {
    "Husky": {".husky"},
    "Insomnia": {".insomnia"},
    "Prisma": {"prisma"},
    "GitHub Actions": {".github/workflows"},
    "CircleCI": {".circleci"},
}

# ============================================================================
# PRACTICE DETECTION - Exact file names (case-insensitive for flexibility)

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
        ".eslintrc.yaml",
        ".eslintrc.yml",
        "prettier.config.js",
        ".prettierrc",
        ".prettierrc.js",
        ".prettierrc.json",
        ".prettierrc.yaml",
        "black.toml",
        ".isort.cfg",
        ".stylelintrc",
        "stylelint.config.js",
        ".rubocop.yml",
        "checkstyle.xml",
        "tslint.json",
        ".editorconfig",
    },
    "Environment Management": {
        "requirements.txt",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        ".nvmrc",
        ".node-version",
        ".ruby-version",
        ".python-version",
        ".tool-versions",
        ".env.example",
        ".env.local",
        ".env.development",
        ".env.production",
        ".env.test",
        ".envrc",
    },
    "API Design": {
        "openapi.yaml",
        "openapi.yml",
        "swagger.json",
        "swagger.yaml",
        "swagger.yml",
        "api.yaml",
        "api.yml",
        "schema.graphql",
        "graphql.config.js",
    },
    "Version Control (Git)": {
        ".gitignore",
        ".gitattributes",
        ".gitmodules",
        ".mailmap",
    },
    "CI/CD": {
        ".gitlab-ci.yml",
        ".gitlab-ci.yaml",
        "jenkinsfile",
        ".travis.yml",
        ".travis.yaml",
        "azure-pipelines.yml",
        "azure-pipelines.yaml",
        "bitbucket-pipelines.yml",
        "circle.yml",
    },
    "Security Practices": {
        "renovate.json",
        ".renovaterc",
        ".snyk",
        "security.md",
        "security.txt",
    },
    "Git Hooks": {
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        ".lintstagedrc",
        "lint-staged.config.js",
        ".huskyrc",
        ".huskyrc.js",
        ".huskyrc.json",
        "commitlint.config.js",
    },
    "Type Safety": {
        "tsconfig.json",
        "tsconfig.build.json",
        "jsconfig.json",
        "mypy.ini",
        "pyrightconfig.json",
    },
    "Database Migrations": {
        "alembic.ini",
        "flyway.conf",
        "liquibase.properties",
    },
    "Infrastructure as Code": {
        "terraform.tfvars",
        ".terraform.lock.hcl",
        "ansible.cfg",
        "pulumi.yaml",
    },
    "Serverless Architecture": {
        "serverless.yml",
        "serverless.yaml",
        "serverless.json",
        "sam.template.yaml",
        "netlify.toml",
        "vercel.json",
    },
    "Monorepo Management": {
        "nx.json",
        "workspace.json",
        "turbo.json",
        "lerna.json",
        "rush.json",
        "pnpm-workspace.yaml",
    },
    "Team Collaboration": {
        "contributing.md",
        "contributors.md",
        "code_of_conduct.md",
        "codeowners",
        "authors.md",
        "authors.txt",
    },
    "Licensing": {
        "license",
        "license.md",
        "license.txt",
        "copying",
        "unlicense",
        "copying.lesser",
    },
}

# ============================================================================
# PRACTICE DETECTION - Path patterns (case-insensitive)
# Directory names are matched case-insensitively

PRACTICES_PATH_PATTERNS = {
    "Test-Driven Development (TDD)": {"tests", "test"},
    "Automated Testing": {"tests", "test", "__tests__"},
    "CI/CD": {".github/workflows", ".gitlab", ".circleci", ".buildkite"},
    "Documentation Discipline": {"docs", "documentation", "wiki", "guides"},
    "API Design": {"api"},
    "Modular Architecture": {
        "src",
        "core",
        "domain",
        "modules",
        "lib",
        "libs",
        "packages",
        "components",
    },
    "Team Collaboration": {"minutes"},
    "Database Migrations": {"migrations", "alembic", "db/migrate", "migrate"},
    "Database Seeding": {"seeds", "seeders", "fixtures", "db/seeds", "db/fixtures"},
    "Infrastructure as Code": {
        "terraform",
        "ansible",
        "infrastructure",
        "infra",
        "tf",
        "iac",
        "cloudformation",
    },
    "Kubernetes": {"k8s", "kubernetes"},
    "Helm Charts": {"charts"},
    "Git Hooks": {".husky"},
    "Issue Templates": {".github/issue_template", ".gitlab/issue_templates"},
    "Event-Driven Architecture": {"kafka", "rabbitmq", "queues", "streams", "message-broker"},
    "Monitoring & Observability": {
        "monitoring",
        "observability",
        "metrics",
        "telemetry",
        "tracing",
    },
    "Security Practices": {"security", "auth", "authentication"},
}

# ============================================================================
# PRACTICE DETECTION - File name patterns (case-insensitive substring)
# These are checked case-insensitively to catch README, Readme, readme, etc.

PRACTICES_FILE_PATTERNS = {
    "Documentation Discipline": {"readme", "changelog", "history", "changes", "news"},
    "Code Review": {"pull_request_template", "pr_template"},
    "Infrastructure as Code": {"playbook"},
}
