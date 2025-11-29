from __future__ import annotations

import json
from pathlib import Path

from capstone_project_team_5.js_code_analyzer import JSTSAnalyzer


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


def test_fullstack_react_express_project(tmp_path):
    """
    Test a typical full-stack project with React frontend and Express backend.
    """

    create_package_json(tmp_path / "package.json", dependencies={"react-router-dom": "^6.23.0"})

    create_package_json(
        tmp_path / "frontend" / "package.json",
        dependencies={"react": "^19.1.0", "react-dom": "^19.1.0", "@mui/material": "^5.14.0"},
        dev_dependencies={"vite": "^7.0.0", "eslint": "^9.0.0", "typescript": "^5.0.0"},
    )

    create_package_json(
        tmp_path / "backend" / "package.json",
        dependencies={
            "express": "^5.1.0",
            "@prisma/client": "^6.14.0",
            "pg": "^8.16.3",
            "jsonwebtoken": "^9.0.2",
            "bcrypt": "^6.0.0",
            "cors": "^2.8.5",
        },
        dev_dependencies={"prisma": "^6.14.0", "nodemon": "^3.1.10"},
    )

    create_code_file(
        tmp_path / "backend" / "auth.js",
        """
        const jwt = require('jsonwebtoken');
        const bcrypt = require('bcrypt');
        
        async function login(req, res) {
            const token = jwt.sign({ userId: user.id }, process.env.JWT_SECRET);
            res.json({ token });
        }
        """,
    )

    create_code_file(
        tmp_path / "backend" / "routes.js",
        """
        app.post('/api/users', async (req, res) => {
            const user = await prisma.user.create({ data: req.body });
            res.json(user);
        });
        
        app.get('/api/users', async (req, res) => {
            const users = await prisma.user.findMany();
            res.json(users);
        });
        """,
    )

    create_code_file(
        tmp_path / "frontend" / "App.tsx",
        """
        import React from 'react';
        import { BrowserRouter, Routes, Route } from 'react-router-dom';
        
        function App() {
            return <div>App</div>;
        }
        """,
    )

    context = {"language": "TypeScript", "framework": "React"}
    analyzer = JSTSAnalyzer(str(tmp_path), context)
    result = analyzer.analyze()

    assert "frontend" in result["tech_stack"]
    assert "TypeScript" in result["tech_stack"]["frontend"]
    assert "React" in result["tech_stack"]["frontend"]
    assert "Material-UI" in result["tech_stack"]["frontend"]

    assert "backend" in result["tech_stack"]
    assert "Node.js" in result["tech_stack"]["backend"]
    assert "Express" in result["tech_stack"]["backend"]

    assert "database" in result["tech_stack"]
    assert "Prisma" in result["tech_stack"]["database"]
    assert "PostgreSQL" in result["tech_stack"]["database"]

    assert "tooling" in result["tech_stack"]
    assert "Vite" in result["tech_stack"]["tooling"]
    assert "ESLint" in result["tech_stack"]["tooling"]

    assert "User Authentication" in result["features"]
    assert "CRUD Operations" in result["features"]

    assert "database" in result["integrations"]
    assert "Prisma" in result["integrations"]["database"]

    skills = result["skills_demonstrated"]
    assert any("TypeScript" in skill or "React" in skill for skill in skills)
    assert any("Node.js" in skill or "Express" in skill for skill in skills)
    assert any(
        "Database" in skill or "PostgreSQL" in skill or "Prisma" in skill for skill in skills
    )
    assert "Authentication & Authorization" in skills


def test_nextjs_project_with_integrations(tmp_path):
    """
    Test a Next.js project with third-party integrations (Stripe, Auth0).
    Represents modern full-stack applications.
    """

    create_package_json(
        tmp_path / "package.json",
        dependencies={
            "next": "^14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "@auth0/auth0-react": "^2.0.0",
            "stripe": "^12.0.0",
            "@aws-sdk/client-s3": "^3.0.0",
            "socket.io": "^4.5.0",
            "axios": "^1.4.0",
        },
        dev_dependencies={"typescript": "^5.0.0", "jest": "^29.0.0", "cypress": "^12.0.0"},
    )

    create_code_file(
        tmp_path / "pages" / "api" / "payment.ts",
        """
        import Stripe from 'stripe';
        const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
        
        export default async function handler(req, res) {
            const paymentIntent = await stripe.paymentIntents.create({
                amount: 1000,
                currency: 'usd',
            });
            res.json(paymentIntent);
        }
        """,
    )

    create_code_file(
        tmp_path / "lib" / "socket.ts",
        """
        import { io } from 'socket.io-client';
        
        const socket = io('http://localhost:3000');
        
        socket.on('message', (data) => {
            console.log(data);
        });
        """,
    )

    create_code_file(
        tmp_path / "lib" / "api.ts",
        """
        import axios from 'axios';
        
        export async function fetchData() {
            const response = await axios.get('https://api.example.com/data');
            return response.data;
        }
        """,
    )

    context = {"language": "TypeScript", "framework": "Next.js"}
    analyzer = JSTSAnalyzer(str(tmp_path), context)
    result = analyzer.analyze()

    assert "frontend" in result["tech_stack"]
    assert "TypeScript" in result["tech_stack"]["frontend"]
    assert "Next.js" in result["tech_stack"]["frontend"]

    assert "backend" in result["tech_stack"]
    assert "Node.js" in result["tech_stack"]["backend"]
    assert "Next.js API Routes" in result["tech_stack"]["backend"]

    assert "testing" in result["tech_stack"]
    assert "Jest" in result["tech_stack"]["testing"]
    assert "Cypress" in result["tech_stack"]["testing"]

    assert "Real-time Updates" in result["features"]
    assert "External API Integration" in result["features"]

    assert "payment" in result["integrations"]
    assert "Stripe" in result["integrations"]["payment"]

    assert "auth" in result["integrations"]
    assert "Auth0" in result["integrations"]["auth"]

    assert "cloud" in result["integrations"]
    assert "AWS S3" in result["integrations"]["cloud"]

    assert "realtime" in result["integrations"]
    assert "Socket.IO" in result["integrations"]["realtime"]

    skills = result["skills_demonstrated"]
    assert "Payment Integration" in skills
    assert "Real-time Communication" in skills
    assert "Cloud Services" in skills


def test_edge_case_no_package_json(tmp_path):
    """Test graceful handling when no package.json exists"""

    create_code_file(tmp_path / "index.js", "console.log('hello world');")

    context = {"language": "JavaScript"}
    analyzer = JSTSAnalyzer(str(tmp_path), context)
    result = analyzer.analyze()

    # Should return empty but valid structure
    assert "tech_stack" in result
    assert "features" in result
    assert "integrations" in result
    assert "skills_demonstrated" in result
    assert isinstance(result["tech_stack"], dict)


def test_node_modules_ignored(tmp_path):
    """Test that package.json files in node_modules are ignored"""

    create_package_json(tmp_path / "package.json", dependencies={"react": "^18.2.0"})

    create_code_file(
        tmp_path / "App.jsx",
        "import React from 'react';\nfunction App() { return <div>Hello</div>; }",
    )

    create_package_json(
        tmp_path / "node_modules" / "some-package" / "package.json",
        dependencies={"should-not-appear": "^1.0.0"},
    )

    context = {"language": "JavaScript", "framework": "React"}
    analyzer = JSTSAnalyzer(str(tmp_path), context)
    result = analyzer.analyze()

    assert "frontend" in result["tech_stack"]
    assert "React" in result["tech_stack"]["frontend"]

    all_output = str(result)
    assert "should-not-appear" not in all_output
