from __future__ import annotations

import json
from pathlib import Path

from capstone_project_team_5.js_code_analyzer import (
    JSProjectSummary,
    JSTSAnalyzer,
    analyze_js_project,
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

    assert "function_count" in result
    assert "class_count" in result
    assert result["function_count"] >= 0
    assert result["class_count"] >= 0


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

    assert "function_count" in result
    assert "class_count" in result
    assert "uses_async_await" in result
    assert isinstance(result.get("function_count", 0), int)


def test_edge_case_no_package_json(tmp_path):
    """Test graceful handling when no package.json exists"""

    create_code_file(tmp_path / "index.js", "console.log('hello world');")

    context = {"language": "JavaScript"}
    analyzer = JSTSAnalyzer(str(tmp_path), context)
    result = analyzer.analyze()

    assert "tech_stack" in result
    assert "features" in result
    assert "integrations" in result
    assert "skills_demonstrated" in result
    assert isinstance(result["tech_stack"], dict)

    assert "function_count" in result
    assert "class_count" in result


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


def test_JSProjectSummary(tmp_path):
    """
    Tests that the JSProjectSummary is built correctly for the below project.
    Test React + TypeScript + Express full-stack project detection.
    """

    create_package_json(
        tmp_path / "package.json",
        dependencies={
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "express": "^4.18.0",
            "@prisma/client": "^5.0.0",
        },
        dev_dependencies={
            "typescript": "^5.0.0",
            "vite": "^4.0.0",
            "eslint": "^8.0.0",
        },
    )

    create_code_file(
        tmp_path / "src" / "App.tsx",
        """
        import React, { useState } from 'react';
        
        function App() {
            const [user, setUser] = useState(null);
            return <div>Hello World</div>;
        }
        
        export default App;
        """,
    )

    create_code_file(
        tmp_path / "server" / "index.ts",
        """
        import express from 'express';
        const app = express();
        
        app.get('/api/users', async (req, res) => {
            res.json({ users: [] });
        });
        """,
    )

    summary = analyze_js_project(tmp_path, "TypeScript", "Express")

    assert isinstance(summary, JSProjectSummary)
    assert summary.uses_typescript is True
    assert summary.total_files > 0

    assert "frontend" in summary.tech_stack
    assert "backend" in summary.tech_stack
    assert "database" in summary.tech_stack

    frontend = summary.tech_stack["frontend"]
    assert any("TypeScript" in item for item in frontend)
    assert any("React" in item for item in frontend), f"React not in frontend: {frontend}"

    backend = summary.tech_stack["backend"]
    assert "Node.js" in backend
    assert "Express" in backend

    assert summary.uses_react is True, "uses_react should be True when React is in dependencies"
    assert summary.uses_nodejs is True


def test_skills_generation(tmp_path):
    """Test that skills list is generated from tech stack."""

    create_package_json(
        tmp_path / "package.json",
        dependencies={
            "react": "^18.2.0",
            "express": "^4.18.0",
            "prisma": "^5.0.0",
            "stripe": "^12.0.0",
        },
        dev_dependencies={
            "jest": "^29.0.0",
        },
    )

    summary = analyze_js_project(tmp_path, "TypeScript", "React")

    skills = summary.skills_demonstrated
    assert "React 18" in skills or "React" in skills
    assert "Express" in skills
    assert "Node.js" in skills
    assert "Prisma" in skills
    assert "Jest" in skills


def test_integration_detection(tmp_path):
    """Test third-party integration detection."""

    create_package_json(
        tmp_path / "package.json",
        dependencies={
            "stripe": "^12.0.0",
            "aws-sdk": "^2.0.0",
            "socket.io": "^4.0.0",
        },
    )

    summary = analyze_js_project(tmp_path, "JavaScript", None)

    integrations = summary.integrations
    assert "payment" in integrations
    assert "Stripe" in integrations["payment"]
    assert "cloud" in integrations
    assert "AWS SDK" in integrations["cloud"]
    assert "realtime" in integrations
    assert "Socket.IO" in integrations["realtime"]


def test_ast_function_and_class_counting(tmp_path):
    """Test that AST accurately counts functions and classes in JavaScript."""

    create_package_json(
        tmp_path / "package.json",
        dependencies={"react": "^18.2.0"},
    )

    create_code_file(
        tmp_path / "src" / "utils.js",
        """
        function regularFunction() {
            return 'hello';
        }
        
        const arrowFunction = () => {
            return 'world';
        };
        
        async function asyncFunction() {
            return await fetch('/api/data');
        }
        
        class MyClass {
            constructor() {
                this.value = 0;
            }
            
            method() {
                return this.value;
            }
        }
        
        class AnotherClass extends MyClass {
            anotherMethod() {
                return 'extended';
            }
        }
        """,
    )

    summary = analyze_js_project(tmp_path, "JavaScript", None)

    assert summary.total_functions >= 6, (
        f"Expected at least 6 functions, got {summary.total_functions}"
    )

    assert summary.total_classes >= 2, f"Expected at least 2 classes, got {summary.total_classes}"

    assert summary.uses_async_await is True


def test_complexity_calculation(tmp_path):
    """Test that complexity metrics are calculated."""

    create_package_json(tmp_path / "package.json", dependencies={})

    create_code_file(
        tmp_path / "src" / "complex.js",
        """
        function simpleFunction() {
            return 1;
        }
        
        function complexFunction(x, y) {
            if (x > 0) {
                if (y > 0) {
                    return x + y;
                } else {
                    return x - y;
                }
            } else if (x < 0) {
                return -x;
            }
            return 0;
        }
        
        function loopFunction(arr) {
            for (let i = 0; i < arr.length; i++) {
                if (arr[i] > 10) {
                    console.log(arr[i]);
                }
            }
        }
        """,
    )

    summary = analyze_js_project(tmp_path, "JavaScript", None)

    assert summary.avg_function_complexity > 0
    assert summary.max_function_complexity >= 1
    assert summary.total_functions >= 3


def test_react_custom_hooks_detection(tmp_path):
    """Test detection of custom React hooks."""

    create_package_json(
        tmp_path / "package.json",
        dependencies={"react": "^18.2.0"},
    )

    create_code_file(
        tmp_path / "src" / "hooks.js",
        """
        import { useState, useEffect } from 'react';
        
        function useCustomHook() {
            const [state, setState] = useState(null);
            return [state, setState];
        }
        
        function useAnotherHook(value) {
            useEffect(() => {
                console.log(value);
            }, [value]);
        }
        
        function useFetchData(url) {
            const [data, setData] = useState(null);
            
            useEffect(() => {
                fetch(url).then(r => r.json()).then(setData);
            }, [url]);
            
            return data;
        }
        
        // This should NOT be counted (doesn't start with 'use')
        function notAHook() {
            return 'test';
        }
        """,
    )

    summary = analyze_js_project(tmp_path, "JavaScript", "React")

    # Should detect the 3 custom hooks (useCustomHook, useAnotherHook, useFetchData)
    assert summary.custom_hooks_count >= 3, (
        f"Expected at least 3 custom hooks, got {summary.custom_hooks_count}"
    )


def test_design_pattern_detection(tmp_path):
    """Test detection of design patterns via AST."""

    create_package_json(tmp_path / "package.json", dependencies={})

    create_code_file(
        tmp_path / "src" / "patterns.js",
        """
        // Singleton pattern
        class Singleton {
            constructor() {
                if (Singleton.instance) {
                    return Singleton.instance;
                }
                Singleton.instance = this;
            }
            
            static getInstance() {
                if (!Singleton.instance) {
                    Singleton.instance = new Singleton();
                }
                return Singleton.instance;
            }
        }
        
        // Factory pattern
        class Factory {
            createProduct(type) {
                if (type === 'A') {
                    return new ProductA();
                }
                return new ProductB();
            }
        }
        
        // Observer pattern
        const button = document.querySelector('button');
        button.addEventListener('click', () => {
            console.log('clicked');
        });
        
        // Functional patterns
        const numbers = [1, 2, 3, 4, 5];
        const doubled = numbers.map(n => n * 2);
        const filtered = numbers.filter(n => n > 2);
        """,
    )

    summary = analyze_js_project(tmp_path, "JavaScript", None)

    assert len(summary.design_patterns) > 0, "Expected design patterns to be detected"

    patterns_str = str(summary.design_patterns)

    assert any(
        pattern in patterns_str for pattern in ["Singleton", "Factory", "Observer", "Functional"]
    )


def test_oop_features_detection(tmp_path):
    """Test detection of OOP features."""

    create_package_json(tmp_path / "package.json", dependencies={})

    create_code_file(
        tmp_path / "src" / "oop.js",
        """
        class Animal {
            constructor(name) {
                this.name = name;
            }
            
            makeSound() {
                console.log('Some sound');
            }
        }
        
        class Dog extends Animal {
            constructor(name) {
                super(name);
            }
            
            makeSound() {
                console.log('Woof!');
            }
        }
        
        class Cat extends Animal {
            makeSound() {
                console.log('Meow!');
            }
        }
        """,
    )

    summary = analyze_js_project(tmp_path, "JavaScript", None)

    assert summary.total_classes >= 3
    assert len(summary.oop_features) > 0
    assert "Classes" in summary.oop_features
    assert "Inheritance" in summary.oop_features


def test_data_structures_and_algorithms(tmp_path):
    """Test detection of data structures and algorithms."""

    create_package_json(tmp_path / "package.json", dependencies={})

    create_code_file(
        tmp_path / "src" / "algorithms.js",
        """
        const map = new Map();
        map.set('key', 'value');
        
        const set = new Set([1, 2, 3]);
        
        const array = [5, 2, 8, 1, 9];
        array.sort((a, b) => a - b);
        
        const filtered = array.filter(x => x > 3);
        const doubled = array.map(x => x * 2);
        const sum = array.reduce((acc, x) => acc + x, 0);
        
        function fibonacci(n) {
            if (n <= 1) return n;
            return fibonacci(n - 1) + fibonacci(n - 2);
        }
        
        const queue = [];
        queue.push(1);
        queue.shift();
        """,
    )

    summary = analyze_js_project(tmp_path, "JavaScript", None)

    assert len(summary.data_structures) > 0
    assert "Map" in summary.data_structures
    assert "Set" in summary.data_structures

    assert len(summary.algorithms_used) > 0
    assert "Sorting" in summary.algorithms_used
    assert (
        "Filtering" in summary.algorithms_used
        or "Mapping/Transformation" in summary.algorithms_used
    )
