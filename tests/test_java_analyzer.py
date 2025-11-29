"""Tests for Java code analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from capstone_project_team_5.java_analyzer import analyze_java_file


@pytest.fixture
def java_simple_class(tmp_path: Path) -> Path:
    """Create a simple Java class file."""
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
    return file_path


@pytest.fixture
def java_complex_example(tmp_path: Path) -> Path:
    """Create a complex Java class with multiple features."""
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
    return file_path


def test_simple_class_encapsulation(java_simple_class: Path) -> None:
    """Test detection of encapsulation in simple class."""
    result = analyze_java_file(java_simple_class)

    assert result["oop_principles"]["Encapsulation"] is True
    assert result["classes_count"] == 1
    assert result["methods_count"] == 2


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
    result = analyze_java_file(file_path)

    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True
    assert result["classes_count"] == 1


def test_complex_example(java_complex_example: Path) -> None:
    """Test comprehensive analysis of complex class."""
    result = analyze_java_file(java_complex_example)

    assert "ArrayList" in result["data_structures"]
    assert "Array" in result["data_structures"]

    assert result["oop_principles"]["Encapsulation"] is True
    assert result["oop_principles"]["Inheritance"] is True
    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True

    assert result["classes_count"] == 2
    assert result["methods_count"] == 4


def test_nonexistent_file() -> None:
    """Test handling of nonexistent file."""
    result = analyze_java_file(Path("/nonexistent/file.java"))

    assert "error" in result
    assert "Failed to read file" in result["error"]


def test_invalid_java_syntax(tmp_path: Path) -> None:
    """Test handling of invalid Java syntax."""
    invalid_code = """
public class Invalid {
    this is not valid java syntax!!!
}
"""
    file_path = tmp_path / "Invalid.java"
    file_path.write_text(invalid_code, encoding="utf-8")

    result = analyze_java_file(file_path)

    assert "error" not in result
    assert result["classes_count"] == 1


def test_empty_file(tmp_path: Path) -> None:
    """Test handling of empty Java file."""
    file_path = tmp_path / "Empty.java"
    file_path.write_text("", encoding="utf-8")

    result = analyze_java_file(file_path)

    assert result["classes_count"] == 0
    assert result["methods_count"] == 0
    assert not result["data_structures"]


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

    result = analyze_java_file(file_path)

    assert result["oop_principles"]["Encapsulation"] is False
    assert result["oop_principles"]["Inheritance"] is False
    assert result["oop_principles"]["Polymorphism"] is False
    assert result["oop_principles"]["Abstraction"] is False


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

    result = analyze_java_file(file_path)

    assert result["oop_principles"]["Encapsulation"] is False
    assert result["classes_count"] == 1
    assert result["methods_count"] == 1


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

    result = analyze_java_file(file_path)

    assert result["oop_principles"]["Abstraction"] is True
    assert result["oop_principles"]["Polymorphism"] is True
    assert result["classes_count"] == 1


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

    result = analyze_java_file(file_path)

    assert result["oop_principles"]["Polymorphism"] is True
    assert result["oop_principles"]["Abstraction"] is True
    assert result["oop_principles"]["Inheritance"] is True
