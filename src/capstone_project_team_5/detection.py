from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Tuple
import json

try:
    import tomllib
except ModuleNotFoundError: 
    tomllib = None  


def _read_text(path: Path) -> str:
    """Safely read text from a file, returning an empty string on failure.

    Args:
        path: Path to the file to read.

    Returns:
        The file contents as a string, or an empty string if unreadable.
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    """Check whether any of the substrings in needles appear in text (case-insensitive)."""
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _detect_from_pyproject(root: Path) -> Tuple[Optional[str], Optional[str]]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None, None

    language: Optional[str] = "Python"
    framework: Optional[str] = None

    deps: set[str] = set()
    try:
        if tomllib is not None:
            data = tomllib.loads(_read_text(pyproject))
            project = data.get("project", {})
            for key in ("dependencies",):
                values = project.get(key) or []
                for dep in values:
                    name = str(dep).split(" ")[0].split("[")[0]
                    name = name.split("<")[0].split(">")[0].split("=")[0]
                    deps.add(name.lower())
    except Exception:
        content = _read_text(pyproject)
        for marker in ("fastapi", "django", "flask", "streamlit", "typer"):
            if marker in content.lower():
                deps.add(marker)

    framework_priority: list[tuple[str, Iterable[str]]] = [
        ("FastAPI", ("fastapi",)),
        ("Django", ("django",)),
        ("Flask", ("flask",)),
        ("Streamlit", ("streamlit",)),
    ]

    for fw, keys in framework_priority:
        if any(k in deps for k in keys):
            framework = fw
            break

    return language, framework


def _detect_from_requirements(root: Path) -> Tuple[Optional[str], Optional[str]]:
    for fname in ("requirements.txt", "requirements-dev.txt"):
        path = root / fname
        if not path.exists():
            continue

        content = _read_text(path)
        if not content:
            continue

        language: Optional[str] = "Python"
        framework: Optional[str] = None
        if _contains_any(content, ("fastapi",)):
            framework = "FastAPI"
        elif _contains_any(content, ("django",)):
            framework = "Django"
        elif _contains_any(content, ("flask",)):
            framework = "Flask"
        elif _contains_any(content, ("streamlit",)):
            framework = "Streamlit"

        return language, framework

    return None, None


def _detect_from_package_json(root: Path) -> Tuple[Optional[str], Optional[str]]:
    pkg = root / "package.json"
    if not pkg.exists():
        return None, None

    try:
        data = json.loads(_read_text(pkg) or "{}")
    except json.JSONDecodeError:
        data = {}

    deps = {
        **(data.get("dependencies") or {}),
        **(data.get("devDependencies") or {}),
    }
    deps_lower = {str(k).lower(): str(v) for k, v in deps.items()}

    language: Optional[str] = "TypeScript" if any(
        f.endswith(".ts") or f.endswith(".tsx") for f in [p.name for p in root.rglob("*.ts*")]
    ) else "JavaScript"
    framework: Optional[str] = None

    framework_checks: list[tuple[str, Iterable[str]]] = [
        ("Next.js", ("next",)),
        ("React", ("react", "react-dom")),
        ("Vue", ("vue",)),
        ("Angular", ("@angular/core",)),
        ("Svelte", ("svelte",)),
        ("Vite", ("vite",)),
        ("Express", ("express",)),
    ]

    for fw, keys in framework_checks:
        if any(k in deps_lower for k in keys):
            framework = fw
            break

    if framework is None:
        if (root / "src-tauri" / "tauri.conf.json").exists() or (root / "tauri.conf.json").exists():
            framework = "Tauri"

    return language, framework


def _detect_from_rust(root: Path) -> Tuple[Optional[str], Optional[str]]:
    cargo = root / "Cargo.toml"
    if not cargo.exists():
        return None, None

    language: Optional[str] = "Rust"
    framework: Optional[str] = None
    content = _read_text(cargo)
    if _contains_any(content, ("tauri",)):
        framework = "Tauri"
    return language, framework


def _detect_from_go(root: Path) -> Tuple[Optional[str], Optional[str]]:
    if (root / "go.mod").exists():
        return "Go", None
    return None, None


def _detect_from_dotnet(root: Path) -> Tuple[Optional[str], Optional[str]]:
    csproj = next(root.glob("*.csproj"), None)
    if csproj is None:
        return None, None
    language: Optional[str] = "C#"
    framework: Optional[str] = None
    program = root / "Program.cs"
    if program.exists():
        content = _read_text(program)
        if _contains_any(content, ("WebApplication.CreateBuilder",)):
            framework = ".NET ASP.NET Core"
    return language, framework


def _detect_from_java(root: Path) -> Tuple[Optional[str], Optional[str]]:
    if (root / "pom.xml").exists() or (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        language: Optional[str] = "Java"
        framework: Optional[str] = None
        content = _read_text(root / "pom.xml") + _read_text(root / "build.gradle") + _read_text(root / "build.gradle.kts")
        if _contains_any(content, ("spring-boot-starter", "springframework")):
            framework = "Spring Boot"
        return language, framework
    return None, None


def _detect_from_php(root: Path) -> Tuple[Optional[str], Optional[str]]:
    if (root / "composer.json").exists():
        language: Optional[str] = "PHP"
        framework: Optional[str] = None
        if (root / "artisan").exists():
            framework = "Laravel"
        return language, framework
    return None, None


def _detect_from_ruby(root: Path) -> Tuple[Optional[str], Optional[str]]:
    if (root / "Gemfile").exists():
        language: Optional[str] = "Ruby"
        framework: Optional[str] = None
        if (root / "bin" / "rails").exists() or (root / "config" / "application.rb").exists():
            framework = "Rails"
        return language, framework
    return None, None


def _detect_from_c_cpp(root: Path) -> Tuple[Optional[str], Optional[str]]:
    if (root / "CMakeLists.txt").exists():
        return "C/C++", "CMake"
    for ext in (".c", ".cpp", ".cc", ".h", ".hpp"):
        if next(root.rglob(f"*{ext}"), None) is not None:
            return "C/C++", None
    return None, None


def identify_language_and_framework(project_root: Path | str) -> tuple[str, Optional[str]]:
    """Identify the primary programming language and, if possible, the framework.

    The detection uses simple heuristics based on common manifest files and
    dependency names. Currently supported languages include Python, JavaScript/TypeScript,
    Rust, Go, C#, Java, PHP, Ruby, and C/C++.

    Args:
        project_root: Path to the project directory.

    Returns:
        A tuple of (language, framework). If the framework cannot be determined,
        the second item is None. If the language cannot be determined, returns
        ("Unknown", None).
    """
    root = Path(project_root)
    if not root.exists() or not root.is_dir():
        return "Unknown", None

    detectors = (
        _detect_from_pyproject,
        _detect_from_requirements,
        _detect_from_package_json,
        _detect_from_rust,
        _detect_from_go,
        _detect_from_dotnet,
        _detect_from_java,
        _detect_from_php,
        _detect_from_ruby,
        _detect_from_c_cpp,
    )

    for det in detectors:
        language, framework = det(root)
        if language is not None:
            return language, framework

    # As a final fallback, infer by file extensions
    if next(root.rglob("*.py"), None) is not None:
        return "Python", None
    if next(root.rglob("*.ts"), None) is not None or next(root.rglob("*.tsx"), None) is not None:
        return "TypeScript", None
    if next(root.rglob("*.js"), None) is not None:
        return "JavaScript", None

    return "Unknown", None

