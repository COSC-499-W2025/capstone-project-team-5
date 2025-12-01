"""
Test cases for JS/TS bullet point generation.

Tests the bullet generation from JSProjectSummary objects.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from capstone_project_team_5.js_code_analyzer import JSProjectSummary
from capstone_project_team_5.services.js_bullets import (
    _format_list,
    generate_js_bullets,
    generate_js_project_bullets,
)


def create_package_json(path: Path, dependencies=None, dev_dependencies=None):
    """Helper to create a package.json file"""

    package_data = {
        "name": "test-project",
        "version": "1.0.0",
        "dependencies": dependencies or {},
        "devDependencies": dev_dependencies or {},
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(package_data, f, indent=2)


def create_code_file(path: Path, content: str):
    """Helper to create a code file"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


class TestFormatList:
    """Test the _format_list helper function."""

    def test_empty_list(self):
        assert _format_list([]) == ""

    def test_single_item(self):
        assert _format_list(["React"]) == "React"

    def test_two_items(self):
        assert _format_list(["React", "TypeScript"]) == "React and TypeScript"

    def test_three_items(self):
        result = _format_list(["React", "TypeScript", "Node.js"])
        assert result == "React, TypeScript, and Node.js"

    def test_four_items(self):
        result = _format_list(["React", "Redux", "TypeScript", "Material-UI"])
        assert result == "React, Redux, TypeScript, and Material-UI"


class TestGenerateJSBullets:
    """Test suite for generate_js_bullets()."""

    def test_react_fullstack_project(self):
        """Test bullets for React + Node.js full-stack project."""

        summary = JSProjectSummary(
            total_files=45,
            total_lines_of_code=5000,
            tech_stack={
                "frontend": ["TypeScript", "React 18", "Material-UI"],
                "backend": ["Node.js", "Express"],
                "database": ["Prisma", "PostgreSQL"],
                "testing": ["Jest", "React Testing Library"],
                "tooling": ["Vite", "ESLint", "Prettier"],
            },
            features=[
                "User Authentication",
                "File Upload Handling",
                "Real-time Updates",
                "CRUD Operations",
                "State Management",
            ],
            integrations={
                "payment": ["Stripe"],
                "auth": ["Auth0"],
            },
            uses_typescript=True,
            uses_react=True,
            uses_nodejs=True,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        assert len(bullets) == 6

        assert any("full-stack" in b.lower() for b in bullets)
        assert any("TypeScript" in b for b in bullets)
        assert any("React" in b for b in bullets)
        assert any("Node.js" in b for b in bullets)
        assert any("45 files" in b for b in bullets)

        assert any("User Authentication" in b for b in bullets)
        assert any("5 key features" in b or "features including" in b.lower() for b in bullets)

        assert any(
            "React" in b and ("component" in b.lower() or "hooks" in b.lower()) for b in bullets
        )

        assert any("Prisma" in b and "PostgreSQL" in b for b in bullets)
        assert any("RESTful" in b or "API" in b for b in bullets)

        assert any("Stripe" in b or "Auth0" in b for b in bullets)

        has_testing = any("Jest" in b for b in bullets)
        has_tooling = any("Vite" in b and "ESLint" in b for b in bullets)
        has_typescript = any("TypeScript" in b and "static typing" in b.lower() for b in bullets)
        assert has_testing or has_tooling or has_typescript

    def test_backend_only_nodejs(self):
        """Test bullets for backend-only Node.js project."""

        summary = JSProjectSummary(
            total_files=30,
            tech_stack={
                "frontend": ["TypeScript"],
                "backend": ["Node.js", "Express"],
                "database": ["Prisma", "PostgreSQL"],
                "tooling": ["ESLint"],
            },
            features=[
                "User Authentication",
                "CRUD Operations",
                "External API Integration",
            ],
            uses_typescript=True,
            uses_nodejs=True,
            uses_react=False,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        assert len(bullets) <= 6

        assert any("backend" in b.lower() for b in bullets)
        assert any("Node.js" in b and "Express" in b for b in bullets)

        assert any("modular" in b.lower() or "middleware" in b.lower() for b in bullets)

        assert any("Prisma" in b and "PostgreSQL" in b for b in bullets)

        assert any("TypeScript" in b for b in bullets)

    def test_react_frontend_only(self):
        """Test bullets for frontend-only React project."""

        summary = JSProjectSummary(
            total_files=25,
            tech_stack={
                "frontend": ["TypeScript", "React 18", "Redux", "Tailwind CSS"],
                "testing": ["Jest", "Cypress"],
                "tooling": ["Vite"],
            },
            features=[
                "State Management",
                "Client-side Routing",
                "Responsive Design",
                "Form Validation",
            ],
            integrations={
                "visualization": ["Chart.js"],
            },
            uses_typescript=True,
            uses_react=True,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        assert any("React" in b for b in bullets)
        assert any("Redux" in b for b in bullets)

        assert any("component" in b.lower() for b in bullets)

        assert any("responsive" in b.lower() or "Tailwind" in b for b in bullets)

    def test_vue_project(self):
        """Test bullets for Vue.js project."""

        summary = JSProjectSummary(
            total_files=20,
            tech_stack={
                "frontend": ["JavaScript", "Vue", "Vuex"],
                "tooling": ["Vite"],
            },
            features=["State Management", "Client-side Routing"],
            uses_vue=True,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        assert any("Vue" in b for b in bullets)
        assert any("reactive" in b.lower() or "component" in b.lower() for b in bullets)

    def test_angular_project(self):
        """Test bullets for Angular project."""

        summary = JSProjectSummary(
            total_files=35,
            tech_stack={
                "frontend": ["TypeScript", "Angular"],
            },
            uses_typescript=True,
            uses_angular=True,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        assert any("Angular" in b for b in bullets)
        assert any("dependency injection" in b.lower() or "module" in b.lower() for b in bullets)

    def test_minimal_project(self):
        """Test bullets for minimal/basic project."""

        summary = JSProjectSummary(
            total_files=5,
            tech_stack={
                "frontend": ["JavaScript"],
            },
            features=[],
            uses_typescript=False,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        # Should still generate at least 1 bullet
        assert len(bullets) >= 1
        assert any("JavaScript" in b for b in bullets)

        has_file_count = any(
            re.search(r"\b5\b", b) and ("file" in b.lower() or "component" in b.lower())
            for b in bullets
        )
        assert has_file_count, f"Expected file count in bullets. Got: {bullets}"

    def test_max_bullets_limit(self):
        """Test that max_bullets parameter is respected."""

        summary = JSProjectSummary(
            total_files=50,
            tech_stack={
                "frontend": ["TypeScript", "React 18", "Redux"],
                "backend": ["Node.js", "Express"],
                "database": ["PostgreSQL"],
                "testing": ["Jest"],
                "tooling": ["Vite", "ESLint"],
            },
            features=["User Authentication", "CRUD Operations", "State Management"],
            integrations={"payment": ["Stripe"]},
            uses_typescript=True,
            uses_react=True,
            uses_nodejs=True,
        )

        # Test different limits
        bullets_3 = generate_js_bullets(summary, max_bullets=3)
        bullets_6 = generate_js_bullets(summary, max_bullets=6)
        bullets_10 = generate_js_bullets(summary, max_bullets=10)

        assert len(bullets_3) <= 3
        assert len(bullets_6) <= 6
        assert len(bullets_10) <= 10

    def test_integration_priorities(self):
        """Test that integrations are prioritized correctly."""

        summary = JSProjectSummary(
            total_files=20,
            tech_stack={"frontend": ["React"]},
            integrations={
                "payment": ["Stripe", "PayPal"],
                "auth": ["Auth0"],
                "cloud": ["AWS SDK"],
                "realtime": ["Socket.io"],
                "database": ["Prisma"],  # Lower priority
            },
            uses_react=True,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        # Should prioritize payment/auth/cloud/realtime over database
        integration_bullets = [b for b in bullets if "Integrat" in b]
        if integration_bullets:
            # Should mention high-priority integrations
            has_priority = any(
                "Stripe" in b or "PayPal" in b or "Auth0" in b or "AWS" in b or "Socket.io" in b
                for b in integration_bullets
            )
            assert has_priority

    def test_no_duplicate_information(self):
        """Test that bullets don't repeat the same information."""

        summary = JSProjectSummary(
            total_files=30,
            tech_stack={
                "frontend": ["TypeScript", "React 18"],
                "backend": ["Node.js", "Express"],
            },
            features=["User Authentication"],
            uses_typescript=True,
            uses_react=True,
            uses_nodejs=True,
        )

        bullets = generate_js_bullets(summary, max_bullets=6)

        # Check that React isn't mentioned in every single bullet (some variation)
        react_count = sum(1 for b in bullets if "React" in b)
        assert react_count < len(bullets)  # Not every bullet mentions React

        # Check that "TypeScript" appears but not excessively
        typescript_count = sum(1 for b in bullets if "TypeScript" in b)
        assert 1 <= typescript_count <= 4  # Reasonable range


class TestGenerateJSProjectBullets:
    """Test suite for generate_js_project_bullets() end-to-end."""

    def test_end_to_end_react_project(self, tmp_path):
        """Test full pipeline from project directory to bullets."""

        create_package_json(
            tmp_path / "package.json",
            dependencies={
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "express": "^4.18.0",
            },
            dev_dependencies={
                "typescript": "^5.0.0",
                "vite": "^4.0.0",
            },
        )

        create_code_file(
            tmp_path / "src" / "App.tsx",
            """
            import React, { useState } from 'react';
            
            function App() {
                return <div>Hello World</div>;
            }
            """,
        )

        create_code_file(
            tmp_path / "server" / "index.ts",
            """
            import express from 'express';
            const app = express();
            """,
        )

        bullets = generate_js_project_bullets(tmp_path, max_bullets=6)

        assert len(bullets) >= 3  # Should generate multiple bullets
        assert len(bullets) <= 6  # Should respect max limit

        all_text = " ".join(bullets)
        assert "React" in all_text
        assert "TypeScript" in all_text
        assert "Node.js" in all_text or "Express" in all_text

    def test_end_to_end_backend_project(self, tmp_path):
        """Test full pipeline for backend-only project."""

        create_package_json(
            tmp_path / "package.json",
            dependencies={
                "express": "^4.18.0",
                "@prisma/client": "^5.0.0",
            },
            dev_dependencies={
                "typescript": "^5.0.0",
            },
        )

        create_code_file(
            tmp_path / "src" / "server.ts",
            """
            import express from 'express';
            import { PrismaClient } from '@prisma/client';
            
            const app = express();
            const prisma = new PrismaClient();
            
            app.get('/api/users', async (req, res) => {
                const users = await prisma.user.findMany();
                res.json(users);
            });
            """,
        )

        bullets = generate_js_project_bullets(tmp_path, max_bullets=6)

        assert len(bullets) >= 2
        all_text = " ".join(bullets)
        assert "backend" in all_text.lower() or "API" in all_text
        assert "Express" in all_text
        assert "Prisma" in all_text

    def test_empty_project_directory(self, tmp_path):
        """Test handling of empty project directory."""

        # Just create an empty directory, no package.json
        bullets = generate_js_project_bullets(tmp_path, max_bullets=6)

        # Should handle gracefully, even if minimal bullets
        assert isinstance(bullets, list)
        # May be empty or have generic bullets
