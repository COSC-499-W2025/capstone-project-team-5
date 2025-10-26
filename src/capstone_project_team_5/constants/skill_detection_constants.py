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

# ============================================================================
# TOOL DETECTION - Exact file names (case-insensitive)

TOOL_FILE_NAMES = {
    # Containerization
    "Docker": {
        "dockerfile",
        "dockerfile.dev",
        "dockerfile.prod",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".dockerignore",
    },
    "Podman": {"podman-compose.yml"},
    # Package Managers
    "npm": {"package.json", "package-lock.json"},
    "yarn": {"yarn.lock"},
    "pnpm": {"pnpm-lock.yaml"},
    "Poetry": {"poetry.lock"},
    "Cargo": {"cargo.toml", "cargo.lock"},
    "Go Modules": {"go.mod", "go.sum"},
    "Composer": {"composer.json", "composer.lock"},
    "Bundler": {"gemfile", "gemfile.lock"},
    "NuGet": {"packages.config"},
    "pip": {"requirements.txt", "requirements-dev.txt", "requirements.in"},
    # Build Tools - Frontend
    "Webpack": {"webpack.config.js", "webpack.config.ts"},
    "Vite": {"vite.config.js", "vite.config.ts"},
    "Rollup": {"rollup.config.js", "rollup.config.mjs"},
    "Parcel": {".parcelrc"},
    "esbuild": {"esbuild.config.js"},
    "Turbopack": {"turbopack.config.js"},
    # Build Tools - Backend
    "Gradle": {"build.gradle", "build.gradle.kts", "settings.gradle", "gradlew"},
    "Maven": {"pom.xml"},
    "Make": {"makefile", "gnumakefile"},
    "CMake": {"cmakelists.txt"},
    "Bazel": {".bazelrc"},
    # Testing Frameworks
    "PyTest": {"pytest.ini", ".coveragerc"},
    "Jest": {"jest.config.js", "jest.config.ts", "jest.config.json"},
    "Vitest": {"vitest.config.js", "vitest.config.ts"},
    "Mocha": {".mocharc.js", ".mocharc.json", "mocha.opts"},
    "Cypress": {"cypress.config.js", "cypress.config.ts", "cypress.json"},
    "RSpec": {".rspec"},
    # Linters & Formatters
    "Ruff": {"ruff.toml"},
    "Black": {"black.toml"},
    "isort": {".isort.cfg"},
    "Stylelint": {".stylelintrc", "stylelint.config.js"},
    "Rubocop": {".rubocop.yml"},
    "Checkstyle": {"checkstyle.xml"},
    # CI/CD Tools
    "GitHub Actions": {".github/workflows"},
    "Jenkins": {"jenkinsfile"},
    "Travis CI": {".travis.yml"},
    "Azure Pipelines": {"azure-pipelines.yml"},
    "Bitbucket Pipelines": {"bitbucket-pipelines.yml"},
    # Infrastructure as Code
    "Terraform": {"terraform.tfvars", ".terraform.lock.hcl"},
    "Ansible": {"ansible.cfg"},
    "Pulumi": {"pulumi.yaml"},
    # Database & ORM
    "Prisma": {"schema.prisma"},
    "Sequelize": {".sequelizerc"},
    "TypeORM": {"ormconfig.json", "ormconfig.js"},
    "Alembic": {"alembic.ini"},
    "Flyway": {"flyway.conf"},
    "Liquibase": {"liquibase.properties"},
    # Monorepo Tools
    "Nx": {"nx.json", "workspace.json"},
    "Turborepo": {"turbo.json"},
    "Lerna": {"lerna.json"},
    "Rush": {"rush.json"},
    # API & Documentation
    "GraphQL": {"graphql.config.js"},
    "Postman": {"postman_collection.json"},
    # Meta Frameworks
    "Next.js": {"next.config.js", "next.config.mjs"},
    "Nuxt": {"nuxt.config.js", "nuxt.config.ts"},
    "Remix": {"remix.config.js"},
    "SvelteKit": {"svelte.config.js"},
    "Astro": {"astro.config.mjs"},
    "Tauri": {"tauri.conf.json"},
    # Development Tools
    "Nodemon": {"nodemon.json"},
    "uv": {"uv.lock"},
    "EditorConfig": {".editorconfig"},
    "direnv": {".envrc"},
    # State Management
    "MobX": {".mobxrc"},
    "Apollo Client": {"apollo.config.js"},
    # Security & Dependency Management
    "Dependabot": {"dependabot.yml"},
    "Renovate": {"renovate.json", ".renovaterc"},
    "Snyk": {".snyk"},
    # Pre-commit Hooks
    "pre-commit": {".pre-commit-config.yaml"},
    "lint-staged": {".lintstagedrc", "lint-staged.config.js"},
    # Serverless
    "Serverless Framework": {"serverless.yml"},
    "AWS SAM": {"sam.template.yaml"},
    "Netlify": {"netlify.toml"},
    "Vercel": {"vercel.json"},
    # Kubernetes & Helm
    "Helm": {"chart.yaml", "values.yaml"},
}

# ============================================================================
# TOOL DETECTION - File name patterns (substring/extension match)

TOOL_FILE_PATTERNS = {
    "Docker": {"docker-compose"},  # Matches docker-compose.dev.yml, etc.
    "SQL": {".sql"},
    "Terraform": {".tf"},
    "gRPC": {".proto"},
    "GraphQL": {".graphql"},
    "Go": {"_test.go"},  # Go test files
    "Kubernetes": {".yaml", ".yml"},  # Will be refined by path patterns
    "CloudFormation": {".template.json", ".template.yaml"},
}

# ============================================================================
# TOOL DETECTION - Directory patterns (presence of specific directories)

TOOL_DIRECTORY_PATTERNS = {
    "Husky": {".husky"},
    "Insomnia": {".insomnia"},
    "Prisma": {"prisma"},
}

# ============================================================================
# PRACTICE DETECTION - Exact file names

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
        "black.toml",
        ".isort.cfg",
        ".stylelintrc",
        "stylelint.config.js",
        ".rubocop.yml",
        "checkstyle.xml",
    },
    "Environment Management": {
        "requirements.txt",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        ".nvmrc",
        ".tool-versions",
        ".env.example",
        ".env.local",
        ".envrc",
    },
    "API Design": {
        "openapi.yaml",
        "openapi.yml",
        "swagger.json",
        "swagger.yaml",
        "schema.graphql",
        "graphql.config.js",
    },
    "Version Control (Git)": {
        ".gitignore",
        ".gitattributes",
    },
    "CI/CD": {
        ".gitlab-ci.yml",
        ".gitlab-ci.yaml",
        "jenkinsfile",
        ".travis.yml",
        "azure-pipelines.yml",
        "bitbucket-pipelines.yml",
    },
    "Security Practices": {
        "dependabot.yml",
        "renovate.json",
        ".renovaterc",
        ".snyk",
    },
    "Git Hooks": {
        ".pre-commit-config.yaml",
        ".lintstagedrc",
        "lint-staged.config.js",
    },
    "Type Safety": {
        "tsconfig.json",
        "mypy.ini",
    },
    "Database Migrations": {
        "alembic.ini",
        "flyway.conf",
        "liquibase.properties",
    },
    "Containerization": {
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".dockerignore",
    },
    "Infrastructure as Code": {
        "terraform.tfvars",
        ".terraform.lock.hcl",
        "ansible.cfg",
        "pulumi.yaml",
    },
    "Serverless Architecture": {
        "serverless.yml",
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
    },
    "Team Collaboration": {
        "contributing.md",
        "code_of_conduct.md",
    },
    "Licensing": {
        "license",
        "license.md",
        "copying",
    },
}

# ============================================================================
# PRACTICE DETECTION - Path patterns (directory/path components)

PRACTICES_PATH_PATTERNS = {
    "Test-Driven Development (TDD)": {"tests", "test"},
    "Automated Testing": {"tests", "test", "__tests__"},
    "CI/CD": {".github/workflows", ".gitlab", ".circleci"},
    "Documentation Discipline": {"docs", "documentation"},
    "API Design": {"api"},
    "Modular Architecture": {"src", "core", "domain", "modules"},
    "Version Control (Git)": {".git"},
    "Team Collaboration": {"logs", "minutes"},
    "Database Migrations": {"migrations", "alembic", "db/migrate"},
    "Database Seeding": {"seeds", "seeders", "fixtures"},
    "Containerization": {"docker"},
    "Infrastructure as Code": {"terraform", "ansible", "infrastructure", "infra"},
    "Kubernetes": {"k8s", "kubernetes"},
    "Helm Charts": {"charts"},
    "Git Hooks": {".husky"},
    "Issue Templates": {".github/issue_template"},
    "Microservices": {"services"},
    "Event-Driven Architecture": {"kafka", "rabbitmq", "events"},
    "Monitoring & Observability": {"monitoring", "observability"},
    "Security Practices": {"security"},
}

# ============================================================================
# PRACTICE DETECTION - File name patterns (substring match)

PRACTICES_FILE_PATTERNS = {
    "Documentation Discipline": {"readme", "changelog", "history"},
    "Code Review": {"pull_request_template", "pr_template"},
    "Infrastructure as Code": {".tf", "playbook"},
    "API Design": {".proto"},
    "Configuration Management": {".config"},
}
