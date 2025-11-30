"""Tests for unified project analysis integration."""

from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.services.project_analysis import analyze_project


class TestProjectAnalysisJavaIntegration:
    """Test Java analyzer integration with project analysis."""

    def test_java_project_analysis_integration(self, tmp_path: Path) -> None:
        """Test that Java projects are correctly analyzed through project_analysis."""
        # Create a Java project with build file
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.test</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0</version>
</project>
"""
        )

        # Create a Java class with OOP features
        java_file = tmp_path / "Calculator.java"
        java_file.write_text(
            """
public class Calculator {
    private int result;
    
    public Calculator() {
        this.result = 0;
    }
    
    public int add(int a, int b) {
        result = a + b;
        return result;
    }
    
    public int factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }
}
"""
        )

        # Analyze the project
        analysis = analyze_project(tmp_path)

        # Verify language detection
        assert analysis.language == "Java"

        # Verify Java analyzer ran
        assert "java_result" in analysis.language_analysis

        # Verify metrics were populated
        assert analysis.total_files == 1
        assert analysis.class_count == 1
        assert analysis.function_count == 2  # add + factorial (constructors not counted)
        assert analysis.lines_of_code > 0

        # Verify OOP features detected
        assert "Encapsulation" in analysis.oop_features
        assert analysis.oop_score > 0

        # Verify recursion detected
        assert "Recursion" in analysis.algorithms


class TestProjectAnalysisCppIntegration:
    """Test C++ analyzer integration with project analysis."""

    def test_cpp_project_analysis_integration(self, tmp_path: Path) -> None:
        """Test that C++ projects are correctly analyzed through project_analysis."""
        # Create a C++ source file
        cpp_file = tmp_path / "main.cpp"
        cpp_file.write_text(
            """
#include <iostream>
#include <memory>

class Shape {
public:
    virtual double area() = 0;
    virtual ~Shape() {}
};

class Circle : public Shape {
private:
    double radius;
    
public:
    Circle(double r) : radius(r) {}
    
    double area() override {
        return 3.14159 * radius * radius;
    }
};

int main() {
    auto circle = std::make_unique<Circle>(5.0);
    std::cout << "Area: " << circle->area() << std::endl;
    return 0;
}
"""
        )

        # Analyze the project
        analysis = analyze_project(tmp_path)

        # Verify language detection
        assert analysis.language == "C/C++"

        # Verify C++ analyzer ran
        assert "c_cpp_summary" in analysis.language_analysis

        # Verify metrics were populated
        assert analysis.total_files == 1
        assert analysis.class_count >= 2  # Shape and Circle
        assert analysis.function_count > 0
        assert analysis.lines_of_code > 0

        # Verify OOP features detected
        assert "Inheritance" in analysis.oop_features
        assert "Polymorphism" in analysis.oop_features
        assert analysis.oop_score > 0

        # Verify technical features
        assert "Modern C++" in analysis.oop_features or analysis.oop_score > 5

        # Verify complexity score is set (C++ specific)
        assert analysis.complexity_score >= 0
