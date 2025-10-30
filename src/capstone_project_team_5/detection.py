from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


class LanguageFrameworkDetector:
    """Detector for primary language and framework."""

    @staticmethod
    def _read_text(path: Path) -> str:
        """Read file text, tolerating failures.

        Args:
            path: Path to the file to read.

        Returns:
            File contents or an empty string when unreadable.
        """
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def _contains_any(text: str, needles: Iterable[str]) -> bool:
        """Check if the text contains any substrings.

        Args:
            text: Source text to search within.
            needles: Substrings to check for (case-insensitive).

        Returns:
            True if any needle is found, otherwise False.
        """
        lowered = text.lower()
        return any(needle.lower() in lowered for needle in needles)

    @staticmethod
    def _from_pyproject(root: Path) -> tuple[str | None, str | None]:
        """Detect Python framework from `pyproject.toml`.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        pyproject = root / "pyproject.toml"
        if not pyproject.exists():
            return None, None

        language: str | None = "Python"
        framework: str | None = None

        deps: set[str] = set()
        try:
            if tomllib is not None:
                data = tomllib.loads(LanguageFrameworkDetector._read_text(pyproject))
                project = data.get("project", {})
                for key in ("dependencies",):
                    values = project.get(key) or []
                    for dep in values:
                        name = str(dep).split(" ")[0].split("[")[0]
                        name = name.split("<")[0].split(">")[0].split("=")[0]
                        deps.add(name.lower())
        except Exception:
            content = LanguageFrameworkDetector._read_text(pyproject)
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

    @staticmethod
    def _from_requirements(root: Path) -> tuple[str | None, str | None]:
        """Detect Python framework from requirements files.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        for fname in ("requirements.txt", "requirements-dev.txt"):
            path = root / fname
            if not path.exists():
                continue

            content = LanguageFrameworkDetector._read_text(path)
            if not content:
                continue

            language: str | None = "Python"
            framework: str | None = None
            if LanguageFrameworkDetector._contains_any(content, ("fastapi",)):
                framework = "FastAPI"
            elif LanguageFrameworkDetector._contains_any(content, ("django",)):
                framework = "Django"
            elif LanguageFrameworkDetector._contains_any(content, ("flask",)):
                framework = "Flask"
            elif LanguageFrameworkDetector._contains_any(content, ("streamlit",)):
                framework = "Streamlit"

            return language, framework

        return None, None

    @staticmethod
    def _from_package_json(root: Path) -> tuple[str | None, str | None]:
        """Detect JS/TS language and framework from `package.json`.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        pkg = root / "package.json"
        if not pkg.exists():
            return None, None

        try:
            data = json.loads(LanguageFrameworkDetector._read_text(pkg) or "{}")
        except json.JSONDecodeError:
            data = {}

        deps = {
            **(data.get("dependencies") or {}),
            **(data.get("devDependencies") or {}),
        }
        deps_lower = {str(k).lower(): str(v) for k, v in deps.items()}

        # A lightweight signal for TS vs JS: presence of .ts/.tsx files
        language: str | None = (
            "TypeScript"
            if any(
                f.endswith(".ts") or f.endswith(".tsx")
                for f in (p.name for p in root.rglob("*.ts*"))
            )
            else "JavaScript"
        )
        framework: str | None = None

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

        if framework is None and (
            (root / "src-tauri" / "tauri.conf.json").exists() or (root / "tauri.conf.json").exists()
        ):
            framework = "Tauri"

        return language, framework

    @staticmethod
    def _from_rust(root: Path) -> tuple[str | None, str | None]:
        """Detect Rust and Tauri from Cargo manifests.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        cargo = root / "Cargo.toml"
        if not cargo.exists():
            return None, None

        language: str | None = "Rust"
        framework: str | None = None
        content = LanguageFrameworkDetector._read_text(cargo)
        if LanguageFrameworkDetector._contains_any(content, ("tauri",)):
            framework = "Tauri"
        return language, framework

    @staticmethod
    def _from_go(root: Path) -> tuple[str | None, str | None]:
        """Detect Go from `go.mod` presence.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        if (root / "go.mod").exists():
            return "Go", None
        return None, None

    @staticmethod
    def _from_dotnet(root: Path) -> tuple[str | None, str | None]:
        """Detect .NET/C# projects and ASP.NET Core.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        csproj = next(root.glob("*.csproj"), None)
        if csproj is None:
            return None, None
        language: str | None = "C#"
        framework: str | None = None
        program = root / "Program.cs"
        if program.exists():
            content = LanguageFrameworkDetector._read_text(program)
            if LanguageFrameworkDetector._contains_any(content, ("WebApplication.CreateBuilder",)):
                framework = ".NET ASP.NET Core"
        return language, framework

    @staticmethod
    def _from_java(root: Path) -> tuple[str | None, str | None]:
        """Detect Java projects and Spring Boot markers.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        if (
            (root / "pom.xml").exists()
            or (root / "build.gradle").exists()
            or (root / "build.gradle.kts").exists()
        ):
            language: str | None = "Java"
            framework: str | None = None
            content = (
                LanguageFrameworkDetector._read_text(root / "pom.xml")
                + LanguageFrameworkDetector._read_text(root / "build.gradle")
                + LanguageFrameworkDetector._read_text(root / "build.gradle.kts")
            )
            if LanguageFrameworkDetector._contains_any(
                content, ("spring-boot-starter", "springframework")
            ):
                framework = "Spring Boot"
            return language, framework
        return None, None

    @staticmethod
    def _from_php(root: Path) -> tuple[str | None, str | None]:
        """Detect PHP projects and Laravel markers.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        if (root / "composer.json").exists():
            language: str | None = "PHP"
            framework: str | None = None
            if (root / "artisan").exists():
                framework = "Laravel"
            return language, framework
        return None, None

    @staticmethod
    def _from_ruby(root: Path) -> tuple[str | None, str | None]:
        """Detect Ruby projects and Rails markers.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        if (root / "Gemfile").exists():
            language: str | None = "Ruby"
            framework: str | None = None
            if (root / "bin" / "rails").exists() or (root / "config" / "application.rb").exists():
                framework = "Rails"
            return language, framework
        return None, None

    @staticmethod
    def _from_c_cpp(root: Path) -> tuple[str | None, str | None]:
        """Detect C/C++ projects and CMake.

        Args:
            root: Project root directory.

        Returns:
            Tuple of detected language (or None) and framework (or None).
        """
        if (root / "CMakeLists.txt").exists():
            return "C/C++", "CMake"
        for ext in (".c", ".cpp", ".cc", ".h", ".hpp"):
            if next(root.rglob(f"*{ext}"), None) is not None:
                return "C/C++", None
        return None, None


def identify_language_and_framework(project_root: Path | str) -> tuple[str, str | None]:
    """Identify the primary language and framework for a project.

    Args:
        project_root: Path to the project directory.

    Returns:
        Tuple of (language, framework). Returns ("Unknown", None) if undetermined.
    """
    root = Path(project_root)
    if not root.exists() or not root.is_dir():
        return "Unknown", None

    detectors = (
        LanguageFrameworkDetector._from_pyproject,
        LanguageFrameworkDetector._from_requirements,
        LanguageFrameworkDetector._from_package_json,
        LanguageFrameworkDetector._from_rust,
        LanguageFrameworkDetector._from_go,
        LanguageFrameworkDetector._from_dotnet,
        LanguageFrameworkDetector._from_java,
        LanguageFrameworkDetector._from_php,
        LanguageFrameworkDetector._from_ruby,
        LanguageFrameworkDetector._from_c_cpp,
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
