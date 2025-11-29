from capstone_project_team_5.python_analyzer import PythonAnalyzer

# ---------------------------------------------------------
# TEST 1 — Basic OOP Detection
# ---------------------------------------------------------


def test_oop_detection(tmp_path):
    file = tmp_path / "animals.py"
    file.write_text(
        """
class Base:
    def speak(self): pass

class Dog(Base):
    def speak(self):
        return "woof"

class Cat(Base):
    def speak(self):
        return "meow"
"""
    )

    result = PythonAnalyzer(str(tmp_path)).analyze()
    oop = result["oop"]

    assert oop["inheritance"] is True
    assert oop["polymorphism"] is True
    assert "Base" in oop["classes"]
    assert "Dog" in oop["classes"]


# ---------------------------------------------------------
# TEST 2 — Encapsulation Detection
# ---------------------------------------------------------


def test_encapsulation(tmp_path):
    file = tmp_path / "user.py"
    file.write_text(
        """
class User:
    def __init__(self):
        self._password = "secret"
"""
    )

    result = PythonAnalyzer(str(tmp_path)).analyze()
    assert result["oop"]["encapsulation"] is True


# ---------------------------------------------------------
# TEST 3 — Framework + DB + Tooling Detection
# ---------------------------------------------------------


def test_tech_stack_detection(tmp_path):
    file = tmp_path / "app.py"
    file.write_text(
        """
import flask
import sqlalchemy
import pytest
import pydantic
"""
    )

    result = PythonAnalyzer(str(tmp_path)).analyze()
    tech = result["tech_stack"]

    assert "frameworks" in tech and "Flask" in tech["frameworks"]
    assert "database" in tech and "SQLAlchemy ORM" in tech["database"]
    assert "testing" in tech and "PyTest" in tech["testing"]
    assert "tooling" in tech and "Pydantic" in tech["tooling"]


# ---------------------------------------------------------
# TEST 4 — Integration Detection
# ---------------------------------------------------------


def test_integrations(tmp_path):
    file = tmp_path / "integrations.py"
    file.write_text(
        """
import requests
import boto3
import redis
import pandas
"""
    )

    result = PythonAnalyzer(str(tmp_path)).analyze()
    integ = result["integrations"]

    assert "http" in integ and "Requests" in integ["http"]
    assert "aws" in integ and "Boto3" in integ["aws"]
    assert "cache" in integ and "Redis" in integ["cache"]
    assert "data" in integ and "Pandas" in integ["data"]


# ---------------------------------------------------------
# TEST 5 — Feature Detection (async, OOP, threading)
# ---------------------------------------------------------


def test_feature_detection(tmp_path):
    file = tmp_path / "features.py"
    file.write_text(
        """
import threading

async def fetch_data():
    pass

class Foo:
    def __init__(self):
        pass
"""
    )

    result = PythonAnalyzer(str(tmp_path)).analyze()
    features = result["features"]

    assert "Asynchronous Programming" in features
    assert "Multithreading" in features
    assert "Object-Oriented Design" in features


# ---------------------------------------------------------
# TEST 6 — Skill Generation
# ---------------------------------------------------------


def test_skill_generation(tmp_path):
    file = tmp_path / "main.py"
    file.write_text(
        """
import flask
import requests

class A:
    def x(self): pass
"""
    )

    result = PythonAnalyzer(str(tmp_path)).analyze()
    skills = result["skills_demonstrated"]

    assert "Flask" in skills
    assert "HTTP API Integration" in skills
    assert "Object-Oriented Design" in skills


# ---------------------------------------------------------
# TEST 7 — No Python Files
# ---------------------------------------------------------


def test_no_python_files(tmp_path):
    (tmp_path / "README.md").write_text("# no python here")

    result = PythonAnalyzer(str(tmp_path)).analyze()

    # Should return error when no Python files found
    assert "error" in result
    assert "No Python files found" in result["error"]


# ---------------------------------------------------------
# TEST 8 — Empty Directory
# ---------------------------------------------------------


def test_empty_directory(tmp_path):
    result = PythonAnalyzer(str(tmp_path)).analyze()

    # Should return error when no Python files found
    assert "error" in result
    assert "No Python files found" in result["error"]


def test_abstraction_detection(tmp_path):
    """Test detection of abstraction through @abstractmethod and NotImplementedError."""
    # Test with @abstractmethod decorator
    file1 = tmp_path / "abstract1.py"
    file1.write_text(
        """
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self):
        pass
"""
    )

    result1 = PythonAnalyzer(str(tmp_path)).analyze()
    assert result1["oop"]["abstraction"] is True

    # Test with NotImplementedError
    tmp_path2 = tmp_path / "subdir"
    tmp_path2.mkdir()
    file2 = tmp_path2 / "abstract2.py"
    file2.write_text(
        """
class Base:
    def must_override(self):
        raise NotImplementedError("Subclasses must implement")
"""
    )

    result2 = PythonAnalyzer(str(tmp_path)).analyze()
    assert result2["oop"]["abstraction"] is True

    # Verify it appears in skills
    assert "Abstraction" in result2["skills_demonstrated"]
