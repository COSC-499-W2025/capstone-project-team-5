"""Tests for C/C++ code analysis integration with CLI and database."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from capstone_project_team_5.c_analyzer import CFileAnalyzer
from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem
from capstone_project_team_5.data.models.project import Project
from capstone_project_team_5.data.models.upload_record import UploadRecord
from capstone_project_team_5.data.models.user import User
from capstone_project_team_5.services.c_bullets import generate_c_project_bullets


@pytest.fixture
def sample_c_project(tmp_path: Path) -> Path:
    """Create a sample C project for testing."""
    project_dir = tmp_path / "test_c_project"
    project_dir.mkdir()

    # Create a simple C file
    main_c = project_dir / "main.c"
    main_c.write_text("""
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

struct Node {
    int data;
    struct Node* next;
};

void* thread_func(void* arg) {
    printf("Thread running\\n");
    return NULL;
}

int main() {
    struct Node* head = (struct Node*)malloc(sizeof(struct Node));
    if (head == NULL) {
        fprintf(stderr, "Memory allocation failed\\n");
        return 1;
    }
    
    head->data = 42;
    head->next = NULL;
    
    pthread_t thread;
    pthread_create(&thread, NULL, thread_func, NULL);
    pthread_join(thread, NULL);
    
    free(head);
    return 0;
}
""")

    # Create a header file
    utils_h = project_dir / "utils.h"
    utils_h.write_text("""
#ifndef UTILS_H
#define UTILS_H

int add(int a, int b);
int multiply(int a, int b);

#endif
""")

    # Create utils.c
    utils_c = project_dir / "utils.c"
    utils_c.write_text("""
#include "utils.h"

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}
""")

    return project_dir


def test_c_analyzer_on_sample_project(sample_c_project: Path):
    """Test that C analyzer correctly analyzes the sample project."""
    summary = CFileAnalyzer.analyze_project(sample_c_project)

    assert summary.total_files == 3
    assert summary.source_files == 2
    assert summary.header_files == 1
    assert summary.total_functions >= 3  # main, add, multiply (thread_func may be counted)
    assert summary.total_structs >= 1  # struct Node
    assert summary.has_main is True
    assert summary.uses_pointers is True
    assert summary.uses_memory_management is True
    assert summary.uses_concurrency is True
    # Note: error handling detection depends on specific patterns
    # Our simple test project may not trigger all patterns
    assert summary.total_lines_of_code > 0


def test_c_bullet_generation(sample_c_project: Path):
    """Test that local C bullets are generated correctly."""
    bullets = generate_c_project_bullets(sample_c_project, max_bullets=6)

    assert len(bullets) > 0
    assert len(bullets) <= 6

    # Check that bullets mention key features
    bullets_text = " ".join(bullets).lower()
    assert any(
        keyword in bullets_text for keyword in ["memory", "thread", "concurrent", "functions"]
    )


def test_database_integration(sample_c_project: Path):
    """Test saving and retrieving code analysis from database."""
    # Initialize database
    init_db()

    # Create test data
    with get_session() as session:
        user = User(username=f"fakeuser_{uuid.uuid4().hex}", password_hash="fakehash")
        session.add(user)
        session.flush()

        # Create upload record
        upload = UploadRecord(
            filename="test_c_project.zip",
            size_bytes=1024,
            file_count=3,
        )
        session.add(upload)
        session.flush()

        # Create project
        project = Project(
            upload_id=upload.id,
            name="test_c_project",
            rel_path="test_c_project",
            has_git_repo=False,
            file_count=3,
            is_collaborative=False,
        )
        session.add(project)
        session.flush()

        # Analyze project
        summary = CFileAnalyzer.analyze_project(sample_c_project)

        # Save analysis
        metrics = {
            "total_files": summary.total_files,
            "header_files": summary.header_files,
            "source_files": summary.source_files,
            "total_lines_of_code": summary.total_lines_of_code,
            "total_functions": summary.total_functions,
            "total_structs": summary.total_structs,
            "has_main": summary.has_main,
            "uses_pointers": summary.uses_pointers,
            "uses_memory_management": summary.uses_memory_management,
            "uses_concurrency": summary.uses_concurrency,
            "uses_error_handling": summary.uses_error_handling,
        }

        analysis = CodeAnalysis(
            project_id=project.id,
            language="C/C++",
            analysis_type="local",
            metrics_json=json.dumps(metrics),
            summary_text=f"C project with {summary.total_lines_of_code} LOC",
        )
        session.add(analysis)
        session.flush()

        # Generate and save bullets
        bullets = generate_c_project_bullets(sample_c_project, max_bullets=6)
        content = "\n".join(f"• {bullet}" for bullet in bullets)

        portfolio_item = PortfolioItem(
            project_id=project.id,
            user_id=user.id,
            title="Local C/C++ Resume Bullets - test_c_project",
            content=content,
        )
        session.add(portfolio_item)
        session.commit()

        # Verify data was saved
        saved_project_id = project.id

    # Retrieve and verify
    with get_session() as session:
        # Check project exists
        project = session.query(Project).filter(Project.id == saved_project_id).first()
        assert project is not None
        assert project.name == "test_c_project"

        # Check analysis exists
        analyses = (
            session.query(CodeAnalysis).filter(CodeAnalysis.project_id == saved_project_id).all()
        )
        assert len(analyses) == 1
        assert analyses[0].language == "C/C++"

        # Check metrics JSON
        saved_metrics = json.loads(analyses[0].metrics_json)
        assert saved_metrics["total_files"] == 3
        assert saved_metrics["uses_memory_management"] is True
        assert saved_metrics["uses_concurrency"] is True

        # Check portfolio items
        items = (
            session.query(PortfolioItem).filter(PortfolioItem.project_id == saved_project_id).all()
        )
        assert len(items) == 1
        assert "Local C/C++" in items[0].title
        assert len(items[0].content) > 0


def test_code_analysis_cascade_delete(sample_c_project: Path):
    """Test that code analyses are deleted when project is deleted."""
    init_db()

    with get_session() as session:
        # Create upload and project
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=100,
            file_count=1,
        )
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name="test",
            rel_path="test",
            has_git_repo=False,
            file_count=1,
        )
        session.add(project)
        session.flush()

        # Create analysis
        analysis = CodeAnalysis(
            project_id=project.id,
            language="C/C++",
            analysis_type="local",
            metrics_json='{"test": true}',
        )
        session.add(analysis)
        session.commit()

        project_id = project.id

    # Delete project
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        session.delete(project)
        session.commit()

    # Verify analysis was also deleted (cascade)
    with get_session() as session:
        analyses = session.query(CodeAnalysis).filter(CodeAnalysis.project_id == project_id).all()
        assert len(analyses) == 0


def test_delete_code_analysis_by_id():
    """Test deleting a code analysis by ID."""
    from capstone_project_team_5.services.code_analysis_persistence import (
        delete_code_analysis,
    )

    init_db()

    with get_session() as session:
        # Create upload and project
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=100,
            file_count=1,
        )
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name="test",
            rel_path="test",
            has_git_repo=False,
            file_count=1,
        )
        session.add(project)
        session.flush()

        # Create analysis
        analysis = CodeAnalysis(
            project_id=project.id,
            language="C/C++",
            analysis_type="local",
            metrics_json='{"test": true}',
        )
        session.add(analysis)
        session.commit()

        analysis_id = analysis.id
        project_id = project.id

    # Delete analysis
    result = delete_code_analysis(analysis_id)
    assert result is True

    # Verify analysis was deleted
    with get_session() as session:
        analysis = session.query(CodeAnalysis).filter(CodeAnalysis.id == analysis_id).first()
        assert analysis is None

        # Verify project still exists
        project = session.query(Project).filter(Project.id == project_id).first()
        assert project is not None

    # Try deleting non-existent analysis
    result = delete_code_analysis(99999)
    assert result is False


def test_delete_code_analyses_by_project():
    """Test deleting all code analyses for a project."""
    from capstone_project_team_5.services.code_analysis_persistence import (
        delete_code_analyses_by_project,
    )

    init_db()

    with get_session() as session:
        # Create upload and project
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=100,
            file_count=1,
        )
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name="test",
            rel_path="test",
            has_git_repo=False,
            file_count=1,
        )
        session.add(project)
        session.flush()

        # Create multiple analyses for the project
        analysis1 = CodeAnalysis(
            project_id=project.id,
            language="C/C++",
            analysis_type="local",
            metrics_json='{"test": 1}',
        )
        analysis2 = CodeAnalysis(
            project_id=project.id,
            language="Python",
            analysis_type="local",
            metrics_json='{"test": 2}',
        )
        session.add(analysis1)
        session.add(analysis2)
        session.commit()

        project_id = project.id

    # Delete all analyses for project
    count = delete_code_analyses_by_project(project_id)
    assert count == 2

    # Verify analyses were deleted
    with get_session() as session:
        analyses = session.query(CodeAnalysis).filter(CodeAnalysis.project_id == project_id).all()
        assert len(analyses) == 0

        # Verify project still exists
        project = session.query(Project).filter(Project.id == project_id).first()
        assert project is not None

    # Try deleting from non-existent project
    count = delete_code_analyses_by_project(99999)
    assert count == 0
