"""Tests for Java code analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from capstone_project_team_5.java_analyzer import analyze_java_project


@pytest.fixture
def java_simple_class(tmp_path: Path) -> Path:
    """Create a simple Java class file and return project root."""
    java_code = """
public class SimpleClass {
    private int value;
    
    public int getValue() {
        return value;
    }
    
    public void setValue(int value) {
        this.value = value;
    }
}
"""
    file_path = tmp_path / "SimpleClass.java"
    file_path.write_text(java_code, encoding="utf-8")
    return tmp_path


@pytest.fixture
def java_complex_example(tmp_path: Path) -> Path:
    """Create a complex Java class with multiple features and return project root."""
    java_code = """
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
"""
    file_path = tmp_path / "ComplexExample.java"
    file_path.write_text(java_code, encoding="utf-8")
    return tmp_path


def test_simple_class_encapsulation(java_simple_class: Path) -> None:
    """Test detection of encapsulation in simple class."""
    result = analyze_java_project(java_simple_class)

    assert result["oop_principles"]["Encapsulation"] is True
    assert result["classes_count"] == 1
    assert result["methods_count"] == 2
    assert result["files_analyzed"] == 1


def test_interface_implementation(tmp_path: Path) -> None:
    """Test detection of interface implementation."""
    java_code = """
interface Drawable { void draw(); }
public class Circle implements Drawable {
    @Override
    public void draw() { System.out.println("Drawing"); }
}
"""
    file_path = tmp_path / "Circle.java"
    file_path.write_text(java_code, encoding="utf-8")
    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True
    assert result["classes_count"] == 1
    assert result["files_analyzed"] == 1


def test_complex_example(java_complex_example: Path) -> None:
    """Test comprehensive analysis of complex class."""
    result = analyze_java_project(java_complex_example)

    assert "ArrayList" in result["data_structures"]
    assert "Array" in result["data_structures"]

    assert result["oop_principles"]["Encapsulation"] is True
    assert result["oop_principles"]["Inheritance"] is True
    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True

    assert result["classes_count"] == 2
    assert result["methods_count"] == 4
    assert result["files_analyzed"] == 1


def test_nonexistent_directory() -> None:
    """Test handling of nonexistent directory."""
    result = analyze_java_project(Path("/nonexistent/project"))

    assert "error" in result
    assert "does not exist" in result["error"]


def test_invalid_java_syntax(tmp_path: Path) -> None:
    """Test handling of invalid Java syntax."""
    invalid_code = """
public class Invalid {
    this is not valid java syntax!!!
}
"""
    file_path = tmp_path / "Invalid.java"
    file_path.write_text(invalid_code, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert "error" not in result
    assert result["classes_count"] == 1
    assert result["files_analyzed"] == 1


def test_empty_file(tmp_path: Path) -> None:
    """Test handling of empty Java file."""
    file_path = tmp_path / "Empty.java"
    file_path.write_text("", encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["classes_count"] == 0
    assert result["methods_count"] == 0
    assert not result["data_structures"]
    assert result["files_analyzed"] == 1


def test_no_oop_principles(tmp_path: Path) -> None:
    """Test class with minimal OOP features."""
    java_code = """
public class Minimal {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
"""
    file_path = tmp_path / "Minimal.java"
    file_path.write_text(java_code, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Encapsulation"] is False
    assert result["oop_principles"]["Inheritance"] is False
    assert result["oop_principles"]["Polymorphism"] is False
    assert result["oop_principles"]["Abstraction"] is False
    assert result["files_analyzed"] == 1


def test_static_fields_not_encapsulated(tmp_path: Path) -> None:
    """Test that public static fields are not considered encapsulation."""
    java_code = """
public class NotEncapsulated {
    public static int publicStatic;
    public int publicField;
    
    public void method() {
        System.out.println("test");
    }
}
"""
    file_path = tmp_path / "NotEncapsulated.java"
    file_path.write_text(java_code, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Encapsulation"] is False
    assert result["classes_count"] == 1
    assert result["methods_count"] == 1
    assert result["files_analyzed"] == 1


def test_interface_without_override(tmp_path: Path) -> None:
    """Test interface implementation without @Override annotation."""
    java_code = """
interface Printable {
    void print();
}

public class Document implements Printable {
    public void print() {
        System.out.println("Printing");
    }
}
"""
    file_path = tmp_path / "Document.java"
    file_path.write_text(java_code, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Abstraction"] is True
    assert result["oop_principles"]["Polymorphism"] is True
    assert result["classes_count"] == 1
    assert result["files_analyzed"] == 1


def test_override_annotation_only(tmp_path: Path) -> None:
    """Test polymorphism detection via @Override annotation alone."""
    java_code = """
abstract class Base {
    abstract void process();
}

public class Derived extends Base {
    @Override
    void process() {
        System.out.println("Processing");
    }
}
"""
    file_path = tmp_path / "Derived.java"
    file_path.write_text(java_code, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True
    assert result["oop_principles"]["Inheritance"] is True
    assert result["files_analyzed"] == 1


def test_multiple_files_in_project(tmp_path: Path) -> None:
    """Test analyzing multiple Java files in a project."""
    # File 1: Has inheritance
    file1 = tmp_path / "Parent.java"
    file1.write_text(
        """
public class Parent {
    protected int value;
}

public class Child extends Parent {
    public void method() { }
}
""",
        encoding="utf-8",
    )

    # File 2: Has encapsulation
    file2 = tmp_path / "Encapsulated.java"
    file2.write_text(
        """
public class Encapsulated {
    private String name;
    
    public String getName() { return name; }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["files_analyzed"] == 2
    assert result["classes_count"] == 3
    assert result["methods_count"] == 2
    assert result["oop_principles"]["Inheritance"] is True
    assert result["oop_principles"]["Encapsulation"] is True


def test_skip_build_directories(tmp_path: Path) -> None:
    """Test that build directories are skipped."""
    # Source file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "Main.java").write_text(
        "public class Main { public static void main(String[] args) { } }", encoding="utf-8"
    )

    # Build directory (should be skipped)
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "Generated.java").write_text("public class Generated { }", encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["files_analyzed"] == 1  # Only src/Main.java
    assert result["classes_count"] == 1


def test_empty_project(tmp_path: Path) -> None:
    """Test analyzing project with no Java files."""
    result = analyze_java_project(tmp_path)

    assert "error" in result
    assert "No Java files found" in result["error"]


def test_multiple_files_comprehensive(tmp_path: Path) -> None:
    """Test analyzing multiple files with various data structures and OOP patterns."""
    # File 1: Collections and interfaces
    (tmp_path / "DataManager.java").write_text(
        """
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;

interface DataStorage {
    void store(String key, Object value);
    Object retrieve(String key);
}

public class DataManager implements DataStorage {
    private HashMap<String, Object> data = new HashMap<>();
    private ArrayList<String> keys = new ArrayList<>();
    private HashSet<String> uniqueKeys = new HashSet<>();
    
    @Override
    public void store(String key, Object value) {
        data.put(key, value);
        keys.add(key);
        uniqueKeys.add(key);
    }
    
    @Override
    public Object retrieve(String key) {
        return data.get(key);
    }
}
""",
        encoding="utf-8",
    )

    # File 2: Inheritance and arrays
    (tmp_path / "Animals.java").write_text(
        """
abstract class Animal {
    protected String name;
    private int age;
    
    public abstract void makeSound();
    
    public void setAge(int age) {
        this.age = age;
    }
}

public class Dog extends Animal {
    private String[] tricks;
    
    @Override
    public void makeSound() {
        System.out.println("Woof!");
    }
    
    public void setTricks(String[] tricks) {
        this.tricks = tricks;
    }
}
""",
        encoding="utf-8",
    )

    # File 3: More collections
    (tmp_path / "TaskQueue.java").write_text(
        """
import java.util.PriorityQueue;
import java.util.LinkedList;

public class TaskQueue {
    private PriorityQueue<String> priorityTasks = new PriorityQueue<>();
    private LinkedList<String> regularTasks = new LinkedList<>();
    
    public void addPriorityTask(String task) {
        priorityTasks.offer(task);
    }
    
    public void addTask(String task) {
        regularTasks.add(task);
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    # Verify file count
    assert result["files_analyzed"] == 3

    # Verify class and method counts (interfaces don't count as classes)
    assert result["classes_count"] == 4  # DataManager, Animal, Dog, TaskQueue
    assert result["methods_count"] >= 8

    # Verify all OOP principles detected
    assert result["oop_principles"]["Encapsulation"] is True  # private fields
    assert result["oop_principles"]["Inheritance"] is True  # Dog extends Animal
    assert result["oop_principles"]["Polymorphism"] is True  # @Override, implements
    assert result["oop_principles"]["Abstraction"] is True  # interface and abstract class

    # Verify data structures detected
    detected_structures = result["data_structures"]
    assert "ArrayList" in detected_structures
    assert "HashMap" in detected_structures
    assert "HashSet" in detected_structures
    assert "PriorityQueue" in detected_structures
    assert "LinkedList" in detected_structures
    assert "Array" in detected_structures

    # Verify structures are sorted
    assert detected_structures == sorted(detected_structures)


def test_nested_directories(tmp_path: Path) -> None:
    """Test analyzing project with nested directory structure (Maven/Gradle style)."""
    # Create nested directory structure: src/main/java/com/example/
    package_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    package_dir.mkdir(parents=True)

    # Main class in package
    (package_dir / "Application.java").write_text(
        """
package com.example;

import java.util.HashMap;

public class Application {
    private HashMap<String, String> config = new HashMap<>();
    
    public static void main(String[] args) {
        System.out.println("Running");
    }
}
""",
        encoding="utf-8",
    )

    # Another class in subpackage
    service_dir = package_dir / "service"
    service_dir.mkdir()
    (service_dir / "UserService.java").write_text(
        """
package com.example.service;

public class UserService {
    private String[] users;
    
    public void addUser(String user) {
        System.out.println("Added");
    }
}
""",
        encoding="utf-8",
    )

    # Test directory (should be analyzed too)
    test_dir = tmp_path / "src" / "test" / "java" / "com" / "example"
    test_dir.mkdir(parents=True)
    (test_dir / "ApplicationTest.java").write_text(
        """
package com.example;

public class ApplicationTest {
    public void testMain() {
        System.out.println("Testing");
    }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    # Verify all files found across nested structure
    assert result["files_analyzed"] == 3
    assert result["classes_count"] == 3
    assert result["methods_count"] >= 3
    assert "HashMap" in result["data_structures"]
    assert "Array" in result["data_structures"]


def test_parser_initialization_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of parser initialization failure."""
    # Create a valid Java file
    (tmp_path / "Test.java").write_text("public class Test { }", encoding="utf-8")

    # Mock Language to raise ImportError
    def mock_language(*args, **kwargs):
        raise ImportError("tree-sitter module not available")

    from capstone_project_team_5 import java_analyzer

    monkeypatch.setattr(java_analyzer, "Language", mock_language)

    result = analyze_java_project(tmp_path)

    assert "error" in result
    assert "Failed to initialize parser" in result["error"]


def test_file_permission_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of file read permission errors."""
    # Create multiple files
    (tmp_path / "Readable.java").write_text(
        "public class Readable { private int x; }", encoding="utf-8"
    )
    (tmp_path / "Unreadable.java").write_text(
        "public class Unreadable { private int y; }", encoding="utf-8"
    )

    # Mock read_bytes to simulate permission error for second file
    original_read_bytes = Path.read_bytes
    call_count = [0]

    def mock_read_bytes(self):
        call_count[0] += 1
        if "Unreadable" in str(self):
            raise PermissionError("Permission denied")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

    result = analyze_java_project(tmp_path)

    # Should still analyze the readable file successfully
    assert "error" not in result
    assert result["files_analyzed"] == 1  # Only Readable.java succeeded
    assert result["classes_count"] == 1
    assert result["oop_principles"]["Encapsulation"] is True


def test_multiple_classes_per_file(tmp_path: Path) -> None:
    """Test file with many classes (10+)."""
    # Create file with 12 classes
    classes = "\n\n".join(
        [
            f"class Class{i} {{ private int field{i}; public void method{i}() {{}} }}"
            for i in range(12)
        ]
    )

    (tmp_path / "ManyClasses.java").write_text(classes, encoding="utf-8")

    result = analyze_java_project(tmp_path)

    assert result["files_analyzed"] == 1
    assert result["classes_count"] == 12
    assert result["methods_count"] == 12
    assert result["oop_principles"]["Encapsulation"] is True


def test_protected_fields(tmp_path: Path) -> None:
    """Test that protected and package-private fields are NOT considered encapsulation."""
    # Protected field - NOT encapsulation
    (tmp_path / "Protected.java").write_text(
        """
public class Protected {
    protected int protectedField;
    
    public void method() { }
}
""",
        encoding="utf-8",
    )

    # Package-private (default) field - NOT encapsulation
    (tmp_path / "PackagePrivate.java").write_text(
        """
public class PackagePrivate {
    int defaultField;
    
    public void method() { }
}
""",
        encoding="utf-8",
    )

    # Mix with actual private field to test detection
    (tmp_path / "Mixed.java").write_text(
        """
public class Mixed {
    private int privateField;
    protected int protectedField;
    int defaultField;
    public int publicField;
    
    public void method() { }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["files_analyzed"] == 3
    assert result["classes_count"] == 3
    # Should detect encapsulation ONLY because Mixed has a private field
    assert result["oop_principles"]["Encapsulation"] is True


def test_recursion_detection(tmp_path: Path) -> None:
    """Test detection of direct and qualified recursion."""
    (tmp_path / "Recursive.java").write_text(
        """
public class Recursive {
    public int factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);  // Direct recursion
    }
    
    public int fib(int n) {
        if (n <= 1) return n;
        return this.fib(n - 1) + this.fib(n - 2);  // Qualified recursion
    }
    
    public void nonRecursive(int x) {
        Helper h = new Helper();
        h.process(x);  // NOT recursion - different object
    }
}

class Helper {
    void process(int x) { }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["uses_recursion"] is True
    assert result["classes_count"] == 2


def test_no_recursion(tmp_path: Path) -> None:
    """Test project with no recursion."""
    (tmp_path / "Simple.java").write_text(
        """
public class Simple {
    public void method1() { method2(); }
    public void method2() { System.out.println("Done"); }
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)
    assert result["uses_recursion"] is False


def test_bfs_detection(tmp_path: Path) -> None:
    """Test detection of BFS algorithm using Queue."""
    (tmp_path / "BFS.java").write_text(
        """
import java.util.Queue;
import java.util.LinkedList;

public class BFS {
    public void breadthFirstSearch(Node root) {
        Queue<Node> queue = new LinkedList<>();
        queue.offer(root);
        
        while (!queue.isEmpty()) {
            Node current = queue.poll();
            for (Node child : current.children) {
                queue.offer(child);
            }
        }
    }
}

class Node {
    Node[] children;
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["uses_bfs"] is True
    assert "Queue" in result["data_structures"]


def test_dfs_detection(tmp_path: Path) -> None:
    """Test detection of DFS algorithm using Stack."""
    (tmp_path / "DFS.java").write_text(
        """
import java.util.Stack;

public class DFS {
    public void depthFirstSearch(Node root) {
        Stack<Node> stack = new Stack<>();
        stack.push(root);
        
        while (!stack.isEmpty()) {
            Node current = stack.pop();
        }
    }
}

class Node {
    Node[] children;
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert result["uses_dfs"] is True
    assert "Stack" in result["data_structures"]


def test_queue_without_operations(tmp_path: Path) -> None:
    """Test that declaring Queue without BFS operations doesn't trigger detection."""
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
    """Test detection of multiple design patterns."""
    (tmp_path / "Patterns.java").write_text(
        """
public class Patterns {
    private static Patterns instance;
    
    public static Patterns getInstance() { return instance; }  // Singleton
    
    public Object createObject(String type) { return new Object(); }  // Factory
    
    public Patterns builder() { return this; }  // Builder
    
    public void addListener(Object listener) { }  // Observer
    
    public void executeStrategy() { }  // Strategy
    
    public void adapt() { }  // Adapter
}
""",
        encoding="utf-8",
    )

    result = analyze_java_project(tmp_path)

    assert "Singleton" in result["coding_patterns"]
    assert "Factory" in result["coding_patterns"]
    assert "Builder" in result["coding_patterns"]
    assert "Observer" in result["coding_patterns"]
    assert "Strategy" in result["coding_patterns"]
    assert "Adapter" in result["coding_patterns"]
    assert len(result["coding_patterns"]) == 6
    assert result["coding_patterns"] == sorted(result["coding_patterns"])
