# Unified Analysis and Bullet Generation System

## Architecture Overview

The system now follows a proper analysis → aggregation → generation flow that is:
- **Language-agnostic**: Works for any language, easy to extend
- **Analyzer-first**: Always runs all analyzers before generating bullets
- **AI with fallback**: Tries AI first, automatically falls back to local
- **Aggregated data**: Single source of truth for all analysis

## Flow Diagram

```
User Uploads Project
        ↓
┌───────────────────────────────────────────────────────────────┐
│  ANALYSIS PHASE (Always Runs)                                 │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Language/Framework Detection                             │
│     - identify_language_and_framework()                      │
│     → "C/C++", "Python", "JavaScript", etc.                  │
│                                                               │
│  2. Skill Detection (Tools & Practices)                      │
│     - extract_project_tools_practices()                      │
│     → Git, Docker, CI/CD, Testing, etc.                      │
│                                                               │
│  3. Language-Specific Analyzers (if available)               │
│     ┌─────────────────────────────────────┐                  │
│     │ C/C++: analyze_c_project()         │                  │
│     │  - OOP features                    │                  │
│     │  - Design patterns                 │                  │
│     │  - Data structures                 │                  │
│     │  - Algorithms                      │                  │
│     │  - Modern C++ features             │                  │
│     │  - Code metrics (LOC, functions)   │                  │
│     └─────────────────────────────────────┘                  │
│     ┌─────────────────────────────────────┐                  │
│     │ Python: (Future)                   │                  │
│     │  - Type hints usage                │                  │
│     │  - Async/await patterns            │                  │
│     │  - Frameworks (Django/Flask)       │                  │
│     └─────────────────────────────────────┘                  │
│                                                               │
│  4. Aggregation                                              │
│     All analysis results → ProjectAnalysis object            │
│     → Single unified view of the project                     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────────────┐
│  BULLET GENERATION PHASE                                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Decision: use_ai AND ai_available?                          │
│                                                               │
│  ┌─────YES──────┐              ┌──────NO───────┐             │
│  │              ↓              ↓               │             │
│  │   Try AI Generation   Local Generation     │             │
│  │   (Gemini API)        (Pattern-based)      │             │
│  │                                            │             │
│  │   Success?                                 │             │
│  │   ├─ YES → Return AI bullets               │             │
│  │   └─ NO  → Fall back to Local ─────────────┘             │
│  │                                                           │
│  └─────────────────────────────────────────────────────────  │
│                                                               │
│  Local Generation Strategy:                                  │
│  1. Check if language-specific generator exists              │
│     - C/C++: Use c_bullets.py (enhanced with OOP/patterns)   │
│     - Python: Use python_bullets.py (future)                 │
│  2. Fall back to generic_local_bullets if no specific one    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
        ↓
    Resume Bullets + Source ("AI" or "Local")
```

## Key Components

### 1. `project_analysis.py` - Unified Analysis
**Purpose**: Single entry point for all project analysis

```python
from capstone_project_team_5.services.project_analysis import analyze_project

# Runs ALL analyzers and returns aggregated results
analysis = analyze_project(project_path)

# Access aggregated data
print(f"Language: {analysis.language}")
print(f"OOP Score: {analysis.oop_score}/10")
print(f"Design Patterns: {analysis.design_patterns}")
print(f"Tools: {analysis.tools}")
```

**What it does**:
- Detects language/framework
- Runs skill detection (always)
- Runs language-specific analyzer if available (C++, Python, etc.)
- Aggregates all results into single `ProjectAnalysis` object

### 2. `bullet_generator.py` - Unified Generation with Fallback
**Purpose**: Main entry point for bullet generation with proper AI/local fallback

```python
from capstone_project_team_5.services.bullet_generator import generate_resume_bullets

# Automatically handles analysis + AI/local fallback
bullets, source = generate_resume_bullets(
    project_path,
    max_bullets=6,
    use_ai=True,  # User consent
    ai_available=True,  # API key configured
)

print(f"Generated by: {source}")  # "AI" or "Local"
for bullet in bullets:
    print(f"- {bullet}")
```

**Flow**:
1. Calls `analyze_project()` → Complete analysis
2. If `use_ai` and `ai_available`: Try AI generation
3. If AI fails or not available: Use local generation
4. Local generation:
   - First tries language-specific generator (e.g., C++ bullets)
   - Falls back to generic local bullets if no specific generator

### 3. CLI Integration
The CLI now uses the unified system:

```python
# OLD (problematic):
# - Only called AI bullets, no local fallback
# - Skill detection separate from language analysis
# - No integration with C++ analyzer

# NEW (correct):
bullets, source = generate_resume_bullets(
    project_path,
    use_ai=consent_tool.allows_gemini,
    ai_available=has_api_key,
)
print(f"Resume Bullet Points ({source} Generation)")
```

## Design Principles

### 1. **Language-Agnostic Extension**
Adding a new language is straightforward:

```python
# Step 1: Create analyzer (python_analyzer.py)
def analyze_python_project(project_path: Path) -> PythonProjectSummary:
    # Detect Python-specific features
    pass

# Step 2: Register in project_analysis.py
def _analyze_python_project(analysis: ProjectAnalysis) -> None:
    summary = analyze_python_project(analysis.project_path)
    analysis.language_analysis["python_summary"] = summary
    # Update aggregated fields...

# Step 3: Create bullet generator (python_bullets.py)
def generate_python_bullets(summary, max_bullets=6) -> list[str]:
    # Generate Python-specific bullets
    pass

# Step 4: Register in bullet_generator.py
def _generate_local_bullets(analysis, max_bullets):
    if analysis.language == "Python":
        return _generate_python_local_bullets(analysis, max_bullets)
```

### 2. **Always Analyze, Conditionally Generate**
- Analysis ALWAYS runs (it's fast and free)
- Bullet generation respects user consent and API availability
- Local generation uses the same analysis as AI

### 3. **Proper Fallback Chain**
```
AI (if consent + API) → Language-specific local → Generic local
```

### 4. **Single Source of Truth**
The `ProjectAnalysis` object contains ALL analysis data:
- From skill detection
- From language-specific analyzers
- Aggregated and normalized

Both AI and local generators use the same data.

## Benefits

### For Users
✅ **Always get bullets**: Local fallback ensures users always get output
✅ **Best quality**: Language-specific analyzers provide detailed, accurate bullets
✅ **Consistent**: Same analysis used whether AI or local
✅ **Offline capable**: Local analysis works without internet

### For Developers
✅ **Portable**: Easy to add new languages
✅ **Maintainable**: Clear separation of concerns
✅ **Testable**: Each component can be tested independently
✅ **Extensible**: New analyzers plug in without changing core logic

## Current Language Support

| Language | Analyzer | Local Bullets | Features Detected |
|----------|----------|---------------|-------------------|
| C/C++ | ✅ `c_analyzer.py` | ✅ `c_bullets.py` | OOP, Patterns, Data Structures, Algorithms, Modern C++ |
| Python | ⏳ Future | ⏳ Future | Type hints, Async, Frameworks |
| JavaScript | ⏳ Future | ⏳ Future | React/Vue, Async, Node.js |
| All others | N/A | ✅ Generic | Tools, Practices, Basic metrics |

## Testing

```bash
# Test C++ analysis
uv run --frozen pytest tests/test_c_analyzer.py -v

# Test bullet generation
uv run --frozen pytest tests/test_local_bullets.py -v

# Test unified system
uv run --frozen python -c "
from pathlib import Path
from capstone_project_team_5.services.bullet_generator import generate_resume_bullets
bullets, source = generate_resume_bullets(Path('.'), use_ai=False)
print(f'Source: {source}')
for b in bullets: print(f'- {b}')
"
```

## Migration Notes

### What Changed
1. **CLI now uses `generate_resume_bullets()`** instead of calling AI directly
2. **Analysis always runs first** via `analyze_project()`
3. **Automatic fallback**: No need to manually check if AI failed
4. **C++ analyzer integrated**: Automatically used for C/C++ projects

### What Didn't Change
- Skill detection still works the same
- Language/framework detection unchanged
- Contribution metrics unchanged
- AI generation unchanged (just wrapped with fallback)

### Breaking Changes
**None for end users**. The CLI interface is identical.

For developers: If you were calling `generate_ai_bullets_for_project()` or `generate_local_bullets()` directly, you should now use `generate_resume_bullets()` instead.

## Future Enhancements

1. **Python Analyzer**: Detect type hints, async patterns, frameworks
2. **JavaScript Analyzer**: Detect React/Vue, Node.js patterns
3. **Java Analyzer**: Detect Spring, Maven patterns
4. **Caching**: Cache analysis results for faster re-runs
5. **Configurable analyzers**: Let users enable/disable specific analyzers
