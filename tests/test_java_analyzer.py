"""Tests for Java code analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from capstone_project_team_5.java_analyzer import analyze_java_project


def test_simple_class_encapsulation(tmp_path: Path) -> None:
    """Test detection of encapsulation in simple class."""
    (tmp_path / "SimpleClass.java").write_text(
        """
public class SimpleClass {
    private int value;
    
    public int getValue() {
        return value;
    }
    
    public void setValue(int value) {
        this.value = value;
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Encapsulation"] is True
    assert result["classes_count"] == 1
    assert result["methods_count"] == 2
    assert result["files_analyzed"] == 1


def test_all_oop_principles(tmp_path: Path) -> None:
    """Test comprehensive detection of all OOP principles and data structures."""
    (tmp_path / "ComplexExample.java").write_text(
        """
import java.util.ArrayList;

abstract class Shape { abstract void draw(); }
interface Drawable { void render(); }

public class ComplexExample extends Shape implements Drawable {
    private ArrayList<String> items = new ArrayList<>();
    private int[] numbers;
    
    @Override
    void draw() { for (String item : items) System.out.println(item); }
    
    @Override
    public void render() { System.out.println("render"); }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert "ArrayList" in result["data_structures"]
    assert "Array" in result["data_structures"]
    assert result["oop_principles"]["Encapsulation"] is True
    assert result["oop_principles"]["Inheritance"] is True
    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True
    assert result["classes_count"] == 2
    assert result["methods_count"] == 4


def test_no_oop_principles(tmp_path: Path) -> None:
    """Test class with minimal OOP features."""
    (tmp_path / "Minimal.java").write_text(
        """
public class Minimal {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Encapsulation"] is False
    assert result["oop_principles"]["Inheritance"] is False
    assert result["oop_principles"]["Polymorphism"] is False
    assert result["oop_principles"]["Abstraction"] is False


def test_error_handling(tmp_path: Path) -> None:
    """Test various error conditions."""
    # Nonexistent directory
    result = analyze_java_project(Path("/nonexistent/project"))
    assert "error" in result
    assert "does not exist" in result["error"]

    # Empty project
    result = analyze_java_project(tmp_path)
    assert "error" in result
    assert "No Java files found" in result["error"]

    # Invalid syntax is parsed anyway
    (tmp_path / "Invalid.java").write_text(
        "public class Invalid { this is not valid; }", encoding="utf-8"
    )
    result = analyze_java_project(tmp_path)
    assert "error" not in result
    assert result["classes_count"] == 1


def test_multiple_files_and_structures(tmp_path: Path) -> None:
    """Test analyzing multiple files with various data structures."""
    (tmp_path / "DataManager.java").write_text(
        """
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;

public class DataManager {
    private HashMap<String, Object> data = new HashMap<>();
    private ArrayList<String> keys = new ArrayList<>();
    private HashSet<String> uniqueKeys = new HashSet<>();
    
    public void store(String key, Object value) {
        data.put(key, value);
    }
}
""",
        encoding="utf-8",
    )

    (tmp_path / "Animals.java").write_text(
        """
abstract class Animal {
    private int age;
    public abstract void makeSound();
}

public class Dog extends Animal {
    private String[] tricks;
    
    @Override
    public void makeSound() {
        System.out.println("Woof!");
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["files_analyzed"] == 2
    assert result["classes_count"] == 3
    assert result["oop_principles"]["Encapsulation"] is True
    assert result["oop_principles"]["Inheritance"] is True
    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True

    detected = result["data_structures"]
    assert "ArrayList" in detected
    assert "HashMap" in detected
    assert "HashSet" in detected
    assert "Array" in detected
    assert detected == sorted(detected)


def test_nested_directories(tmp_path: Path) -> None:
    """Test analyzing nested directory structure and build directory skipping."""
    # Create Maven-style structure
    package_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    package_dir.mkdir(parents=True)

    (package_dir / "Application.java").write_text(
        "public class Application { private int x; }", encoding="utf-8"
    )

    # Build directory (should be skipped)
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "Generated.java").write_text("public class Generated { }", encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["files_analyzed"] == 1  # Only src file
    assert result["classes_count"] == 1


def test_recursion_detection(tmp_path: Path) -> None:
    """Test detection of recursion in methods."""
    (tmp_path / "Recursive.java").write_text(
        """
public class Recursive {
    public int factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }
    
    public int fib(int n) {
        if (n <= 1) return n;
        return this.fib(n - 1) + this.fib(n - 2);
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)
    assert result["uses_recursion"] is True

    # Test no recursion case
    (tmp_path / "NoRecursion.java").write_text(
        "public class Simple { public void method() { } }", encoding="utf-8"
    )
    result = analyze_java_project(tmp_path)
    assert result["uses_recursion"] is True  # Still has Recursive.java


def test_bfs_and_dfs_detection(tmp_path: Path) -> None:
    """Test detection of BFS and DFS algorithms."""
    (tmp_path / "BFS.java").write_text(
        """
import java.util.Queue;
import java.util.LinkedList;

public class BFS {
    public void search(Node root) {
        Queue<Node> queue = new LinkedList<>();
        queue.offer(root);
        while (!queue.isEmpty()) {
            Node current = queue.poll();
        }
    }
}
class Node { Node[] children; }
""",
        encoding="utf-8",
    )

    (tmp_path / "DFS.java").write_text(
        """
import java.util.Stack;

public class DFS {
    public void search(Node root) {
        Stack<Node> stack = new Stack<>();
        stack.push(root);
        while (!stack.isEmpty()) {
            Node current = stack.pop();
        }
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)
    assert result["uses_bfs"] is True
    assert result["uses_dfs"] is True
    assert "Queue" in result["data_structures"]
    assert "Stack" in result["data_structures"]


def test_queue_without_bfs_operations(tmp_path: Path) -> None:
    """Test that Queue without operations doesn't trigger BFS detection."""
    (tmp_path / "QueueOnly.java").write_text(
        """
import java.util.Queue;
import java.util.LinkedList;

public class QueueOnly {
    private Queue<String> queue = new LinkedList<>();
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)
    assert result["uses_bfs"] is False
    assert "Queue" in result["data_structures"]


def test_coding_patterns_detection(tmp_path: Path) -> None:
    """Test detection of design patterns."""
    (tmp_path / "Patterns.java").write_text(
        """
public class Patterns {
    private static Patterns instance;
    
    public static Patterns getInstance() { return instance; }
    public Object createObject(String type) { return new Object(); }
    public Patterns builder() { return this; }
    public void addListener(Object listener) { }
    public void executeStrategy() { }
    public void adapt() { }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    patterns = result["coding_patterns"]
    assert "Singleton" in patterns
    assert "Factory" in patterns
    assert "Builder" in patterns
    assert "Observer" in patterns
    assert "Strategy" in patterns
    assert "Adapter" in patterns
    assert patterns == sorted(patterns)


def test_total_files_and_lines_of_code(tmp_path: Path) -> None:
    """Test total_files counting and LOC calculation via AST."""
    (tmp_path / "File1.java").write_text(
        """
public class File1 {
    private int x;
    public void method() {
        System.out.println("test");
    }
}
""",
        encoding="utf-8",
    )

    (tmp_path / "File2.java").write_text("public class File2 { }", encoding="utf-8")
    (tmp_path / "Empty.java").write_text("", encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["total_files"] == 3
    assert result["files_analyzed"] == 3
    assert result["lines_of_code"] > 0


def test_file_permission_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test graceful handling of file read permission errors."""
    (tmp_path / "Readable.java").write_text("public class Test { }", encoding="utf-8")
    (tmp_path / "Unreadable.java").write_text("public class Test2 { }", encoding="utf-8")

    original_read_bytes = Path.read_bytes

    def mock_read_bytes(self):
        if "Unreadable" in str(self):
            raise PermissionError("Permission denied")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

    result = analyze_java_project(tmp_path)

    assert "error" not in result
    assert result["total_files"] == 2
    assert result["files_analyzed"] == 1


def test_parser_initialization_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of parser initialization failure."""
    (tmp_path / "Test.java").write_text("public class Test { }", encoding="utf-8")

    def mock_language(*args, **kwargs):
        raise ImportError("tree-sitter module not available")

    from capstone_project_team_5 import java_analyzer

    monkeypatch.setattr(java_analyzer, "Language", mock_language)

    result = analyze_java_project(tmp_path)

    assert "error" in result
    assert "Failed to initialize parser" in result["error"]


def test_encapsulation_requires_private_fields(tmp_path: Path) -> None:
    """Test that only private fields are considered encapsulation."""
    (tmp_path / "NotEncapsulated.java").write_text(
        """
public class NotEncapsulated {
    public int publicField;
    protected int protectedField;
    int packageField;
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)
    assert result["oop_principles"]["Encapsulation"] is False

    (tmp_path / "Encapsulated.java").write_text(
        "public class Encapsulated { private int x; }", encoding="utf-8"
    )

    result = analyze_java_project(tmp_path)
    assert result["oop_principles"]["Encapsulation"] is True


def test_multiple_classes_per_file(tmp_path: Path) -> None:
    """Test file with many classes."""
    classes = "\n\n".join(
        [f"class Class{i} {{ private int x; public void m() {{}} }}" for i in range(10)]
    )

    (tmp_path / "ManyClasses.java").write_text(classes, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["classes_count"] == 10
    assert result["methods_count"] == 10
    assert result["oop_principles"]["Encapsulation"] is True
