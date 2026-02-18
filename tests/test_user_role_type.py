import os
import subprocess
from pathlib import Path

import pytest

from src.capstone_project_team_5.role_type_detection import (
    CategoryStats,
    FileContribution,
    analyze_file_categories,
    categorize_file,
    detect_enhanced_user_role,
    detect_specialized_role,
    get_user_file_contributions,
)


@pytest.fixture
def mock_git_repo(tmp_path: Path):
    """Initialize a Git repo with commits for different file types."""

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    files_by_category = {
        "frontend": ["src/App.tsx", "src/Button.jsx", "styles/main.css", "public/index.html"],
        "backend": ["api/routes.py", "models/user.py", "services/auth.go", "db/schema.sql"],
        "testing": ["tests/test_api.py", "src/App.test.tsx", "__tests__/auth.spec.js"],
        "documentation": ["README.md", "docs/api.md", "CONTRIBUTING.rst"],
        "devops": [".github/workflows/ci.yml", "Dockerfile", "infrastructure/main.tf"],
        "data": ["notebooks/analysis.ipynb", "data/processed.csv", "pipeline.sql"],
    }

    for category, files in files_by_category.items():
        for i, file_path in enumerate(files):
            full_path = tmp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write different amounts of content per category
            lines = 50 if category in ["frontend", "backend"] else 20
            full_path.write_text("\n".join([f"Line {j} in {file_path}" for j in range(lines)]))

            subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)

            # Sequential commit dates
            commit_date = f"2025-01-{(i + 1):02d}T12:00:00"
            env = dict(**os.environ, GIT_AUTHOR_DATE=commit_date, GIT_COMMITTER_DATE=commit_date)
            subprocess.run(
                ["git", "commit", "-m", f"Add {file_path}"],
                cwd=tmp_path,
                check=True,
                env=env,
                capture_output=True,
            )

    return tmp_path


@pytest.fixture
def mock_multi_user_repo(tmp_path: Path):
    """Create a repo with multiple contributors with different specializations."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    # Create commits from different users
    users = [
        {
            "name": "Frontend Dev",
            "email": "frontend@example.com",
            "files": ["src/App.tsx", "src/components/Button.tsx", "styles/main.css"],
        },
        {
            "name": "Backend Dev",
            "email": "backend@example.com",
            "files": ["api/routes.py", "models/user.py", "services/auth.py"],
        },
        {
            "name": "DevOps Engineer",
            "email": "devops@example.com",
            "files": [".github/workflows/ci.yml", "Dockerfile", "k8s/deployment.yaml"],
        },
    ]

    for user in users:
        for i, file_path in enumerate(user["files"]):
            full_path = tmp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("\n".join([f"Line {j}" for j in range(30)]))

            subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)

            # Set user for this commit
            subprocess.run(
                ["git", "config", "user.name", user["name"]],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", user["email"]],
                cwd=tmp_path,
                check=True,
                capture_output=True,
            )

            commit_date = f"2025-01-{(i + 1):02d}T12:00:00"
            env = dict(**os.environ, GIT_AUTHOR_DATE=commit_date, GIT_COMMITTER_DATE=commit_date)
            subprocess.run(
                ["git", "commit", "-m", f"Add {file_path}"],
                cwd=tmp_path,
                check=True,
                env=env,
                capture_output=True,
            )

    return tmp_path


class TestFileCategorization:
    """Test file categorization logic."""

    def test_frontend_categorization(self):
        """Frontend files are correctly categorized."""
        assert categorize_file("src/App.tsx") == "frontend"
        assert categorize_file("components/Button.jsx") == "frontend"
        assert categorize_file("styles/main.css") == "frontend"
        assert categorize_file("public/index.html") == "frontend"

    def test_backend_categorization(self):
        """Backend files are correctly categorized."""
        assert categorize_file("api/routes.py") == "backend"
        assert categorize_file("models/user.go") == "backend"
        assert categorize_file("db/schema.sql") == "backend"

    def test_testing_categorization(self):
        """Test files are correctly categorized."""
        assert categorize_file("tests/test_api.py") == "testing"
        assert categorize_file("src/App.test.tsx") == "testing"
        assert categorize_file("__tests__/auth.spec.js") == "testing"

    def test_devops_categorization(self):
        """DevOps files are correctly categorized."""
        assert categorize_file(".github/workflows/ci.yml") == "devops"
        assert categorize_file("Dockerfile") == "devops"
        assert categorize_file("infrastructure/main.tf") == "devops"

    def test_documentation_categorization(self):
        """Documentation files are correctly categorized."""
        assert categorize_file("README.md") == "documentation"
        assert categorize_file("docs/api.md") == "documentation"

    def test_data_categorization(self):
        """Data files are correctly categorized."""
        assert categorize_file("notebooks/analysis.ipynb") == "data"
        assert categorize_file("data/processed.csv") == "data"

    def test_directory_pattern_precedence(self):
        """Directory patterns take precedence over extensions."""
        # .py in tests directory should be testing, not backend
        assert categorize_file("tests/test_utils.py") == "testing"
        # .yml in workflows should be devops
        assert categorize_file(".github/workflows/deploy.yml") == "devops"


class TestCategoryAnalysis:
    """Test category analysis and statistics."""

    def test_analyze_single_category(self):
        """Analysis works with single category."""
        contributions = [
            FileContribution("src/App.tsx", commits=10, added=200, deleted=50),
            FileContribution("src/Button.tsx", commits=5, added=100, deleted=20),
        ]

        stats = analyze_file_categories(contributions)

        assert "frontend" in stats
        assert stats["frontend"].commits == 15
        assert stats["frontend"].files == 2
        assert stats["frontend"].lines_changed == 370
        assert stats["frontend"].percentage == 100.0

    def test_analyze_multiple_categories(self):
        """Analysis distributes percentages across categories."""
        contributions = [
            FileContribution("src/App.tsx", commits=10, added=100, deleted=0),
            FileContribution("api/routes.py", commits=10, added=100, deleted=0),
        ]

        stats = analyze_file_categories(contributions)

        assert "frontend" in stats
        assert "backend" in stats
        assert stats["frontend"].percentage == 50.0
        assert stats["backend"].percentage == 50.0

    def test_percentage_calculation(self):
        """Percentages are calculated based on lines changed."""
        contributions = [
            FileContribution("src/App.tsx", commits=1, added=300, deleted=0),  # 75%
            FileContribution("api/routes.py", commits=1, added=100, deleted=0),  # 25%
        ]

        stats = analyze_file_categories(contributions)

        assert stats["frontend"].percentage == 75.0
        assert stats["backend"].percentage == 25.0

    def test_empty_contributions(self):
        """Analysis handles empty contributions."""
        stats = analyze_file_categories([])
        assert len(stats) == 0


class TestRoleDetection:
    """Test role detection logic."""

    def test_frontend_developer_detection(self):
        """Detects frontend developer role."""
        category_breakdown = {
            "frontend": CategoryStats(commits=50, files=20, lines_changed=2000, percentage=80.0),
            "testing": CategoryStats(commits=10, files=5, lines_changed=500, percentage=20.0),
        }

        role = detect_specialized_role(category_breakdown, total_commits=60)

        assert role.primary_role == "Frontend Developer"
        assert role.confidence == "High"
        assert "frontend" in role.file_focus

    def test_backend_developer_detection(self):
        """Detects backend developer role."""
        category_breakdown = {
            "backend": CategoryStats(commits=45, files=18, lines_changed=1800, percentage=75.0),
            "data": CategoryStats(commits=10, files=5, lines_changed=600, percentage=25.0),
        }

        role = detect_specialized_role(category_breakdown, total_commits=55)

        assert role.primary_role == "Backend Developer"
        assert role.confidence == "High"

    def test_fullstack_developer_detection(self):
        """Detects full-stack developer when both frontend and backend >= 20%."""
        category_breakdown = {
            "frontend": CategoryStats(commits=30, files=15, lines_changed=1200, percentage=40.0),
            "backend": CategoryStats(commits=30, files=15, lines_changed=1200, percentage=40.0),
            "testing": CategoryStats(commits=10, files=5, lines_changed=600, percentage=20.0),
        }

        role = detect_specialized_role(category_breakdown, total_commits=70)

        assert role.primary_role == "Full Stack Developer"
        assert role.confidence == "High"

    def test_devops_engineer_detection(self):
        """Detects DevOps engineer role."""
        category_breakdown = {
            "devops": CategoryStats(commits=40, files=15, lines_changed=1600, percentage=70.0),
            "config": CategoryStats(commits=10, files=8, lines_changed=685, percentage=30.0),
        }

        role = detect_specialized_role(category_breakdown, total_commits=50)

        assert role.primary_role == "DevOps Engineer"
        assert role.confidence == "High"

    def test_qa_engineer_detection(self):
        """Detects QA engineer role."""
        category_breakdown = {
            "testing": CategoryStats(commits=35, files=20, lines_changed=1400, percentage=65.0),
            "frontend": CategoryStats(commits=10, files=5, lines_changed=750, percentage=35.0),
        }

        role = detect_specialized_role(category_breakdown, total_commits=45)

        assert role.primary_role == "QA Engineer"
        assert role.confidence == "High"

    def test_confidence_levels(self):
        """Confidence levels adjust based on commits."""
        # High confidence: 40%+ and 10+ commits
        category_breakdown_high = {
            "frontend": CategoryStats(commits=50, files=20, lines_changed=2000, percentage=80.0),
        }
        role_high = detect_specialized_role(category_breakdown_high, total_commits=50)
        assert role_high.confidence == "High"

        # Medium confidence: 40%+ but only 5 commits
        category_breakdown_medium = {
            "frontend": CategoryStats(commits=5, files=3, lines_changed=200, percentage=80.0),
        }
        role_medium = detect_specialized_role(category_breakdown_medium, total_commits=5)
        assert role_medium.confidence == "Medium"

        # Low confidence: <25% or very few commits
        category_breakdown_low = {
            "frontend": CategoryStats(commits=2, files=2, lines_changed=50, percentage=15.0),
        }
        role_low = detect_specialized_role(category_breakdown_low, total_commits=2)
        assert role_low.confidence == "Low"

    def test_secondary_roles(self):
        """Secondary roles detected when >= 15% in multiple areas."""
        category_breakdown = {
            "frontend": CategoryStats(commits=30, files=12, lines_changed=1200, percentage=50.0),
            "backend": CategoryStats(commits=15, files=8, lines_changed=600, percentage=25.0),
            "testing": CategoryStats(commits=10, files=6, lines_changed=600, percentage=25.0),
        }

        role = detect_specialized_role(category_breakdown, total_commits=55)

        # Should detect secondary roles for backend and testing (both >= 15%)
        assert len(role.secondary_roles) >= 1


class TestIntegration:
    """Integration tests with real Git repositories."""

    def test_single_user_repo_analysis(self, mock_git_repo):
        """Analyze a single-user repository."""
        from capstone_project_team_5.utils.git import get_author_contributions

        author_contributions = get_author_contributions(mock_git_repo)

        assert len(author_contributions) == 1
        assert author_contributions[0].author == "Test User"

        enhanced_role = detect_enhanced_user_role(mock_git_repo, "Test User", author_contributions)

        assert enhanced_role is not None
        assert enhanced_role.primary_role in [
            "Frontend Developer",
            "Backend Developer",
            "Full Stack Developer",
        ]
        assert enhanced_role.confidence in ["High", "Medium", "Low"]

    def test_multi_user_repo_analysis(self, mock_multi_user_repo):
        """Analyze a multi-user repository with different roles."""
        from capstone_project_team_5.utils.git import get_author_contributions

        author_contributions = get_author_contributions(mock_multi_user_repo)

        assert len(author_contributions) == 3

        # Analyze each user
        roles = {}
        for contrib in author_contributions:
            enhanced_role = detect_enhanced_user_role(
                mock_multi_user_repo, contrib.author, author_contributions
            )
            if enhanced_role:
                roles[contrib.author] = enhanced_role.primary_role

        # Verify different specializations are detected
        assert "Frontend Dev" in roles
        assert "Backend Dev" in roles
        assert "DevOps Engineer" in roles

        # Check that roles match expectations
        assert "Frontend" in roles["Frontend Dev"]
        assert "Backend" in roles["Backend Dev"]
        assert "DevOps" in roles["DevOps Engineer"]

    def test_file_contributions_extraction(self, mock_git_repo):
        """File contributions are correctly extracted from Git."""

        file_contributions = get_user_file_contributions(
            mock_git_repo,
            "Test User",
        )

        assert len(file_contributions) > 0
        assert all(isinstance(fc, FileContribution) for fc in file_contributions)
        assert all(fc.commits > 0 for fc in file_contributions)
        assert all(fc.added >= 0 for fc in file_contributions)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_user_contributions(self, mock_git_repo):
        """Handle case where user has no contributions."""
        from capstone_project_team_5.utils.git import get_author_contributions

        author_contributions = get_author_contributions(mock_git_repo)

        # Try to detect role for non-existent user
        enhanced_role = detect_enhanced_user_role(
            mock_git_repo, "Nonexistent User", author_contributions
        )

        assert enhanced_role is None

    def test_empty_author_contributions(self, mock_git_repo):
        """Handle empty author contributions list."""
        enhanced_role = detect_enhanced_user_role(mock_git_repo, "Test User", [])

        assert enhanced_role is None

    def test_uncategorized_files(self):
        """Files that don't match any category are marked as 'other'."""
        contributions = [
            FileContribution("random.xyz", commits=5, added=100, deleted=0),
        ]

        stats = analyze_file_categories(contributions)

        assert "other" in stats
        assert stats["other"].percentage == 100.0
