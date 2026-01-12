# Incremental Upload Feature Implementation Guide

## Overview

This document describes the implementation of **incremental uploads** for the capstone project. This feature allows users to add additional zipped folders of files to existing portfolios or résumés, rather than replacing all content with each new upload.

## Motivation

Previously, the system followed a "create new project per upload" model:
- Each ZIP upload created a new `UploadRecord` with new `Project` records
- There was no way to append files to an existing project
- Users who needed to incrementally add more project files had to re-upload everything

The incremental upload feature enables a workflow where:
1. User uploads initial portfolio/résumé files (creates Project records)
2. User later uploads additional files for the same projects
3. New files are added to the existing project instead of creating duplicates

## Architecture

### 1. New Database Model: `ArtifactSource`

**File:** [`src/capstone_project_team_5/data/models/artifact_source.py`](src/capstone_project_team_5/data/models/artifact_source.py)

```python
class ArtifactSource(Base):
    """Tracks which upload contributed which artifacts to a project."""
    project_id: int  # Foreign key to Project
    upload_id: int   # Foreign key to UploadRecord
    artifact_count: int  # Number of artifacts added in this upload
    created_at: datetime  # When this contribution was recorded
```

**Purpose:** Maintains an audit trail of which `UploadRecord` contributed artifacts to which `Project`. This enables:
- Tracking incremental contributions
- Distinguishing between "initial upload" and "incremental uploads"
- Determining which uploads share the same project
- Potential future rollback or version history capabilities

**Relationships:**
- `Project` has many `ArtifactSource` records (one for each incremental upload)
- `UploadRecord` has many `ArtifactSource` records (if shared across multiple projects)

### 2. Updated Database Models

**Files Modified:**
- [`src/capstone_project_team_5/data/models/project.py`](src/capstone_project_team_5/data/models/project.py)
- [`src/capstone_project_team_5/data/models/upload_record.py`](src/capstone_project_team_5/data/models/upload_record.py)

**Changes:**
- Added `artifact_sources` relationship to both models
- Enables bidirectional navigation: `Project.artifact_sources` and `UploadRecord.artifact_sources`
- All `ArtifactSource` records cascade-delete with their parent records

### 3. New Service Module: Incremental Upload

**File:** [`src/capstone_project_team_5/services/incremental_upload.py`](src/capstone_project_team_5/services/incremental_upload.py)

Provides four main functions:

#### `incremental_upload_zip(zip_path, project_mapping=None)`
- Main function for uploading with optional incremental behavior
- Performs standard ZIP upload first (via `upload_zip()`)
- If `project_mapping` provided, associates new upload with existing projects
- Returns `(ZipUploadResult, associations_list)`
- Automatically updates project file counts

**Usage:**
```python
from capstone_project_team_5.services import incremental_upload_zip

mapping = {"myproject": 5}  # Project name -> existing project ID
result, associations = incremental_upload_zip(
    "new_files.zip",
    project_mapping=mapping
)
# associations = [(5, 42)]  # (existing_project_id, new_upload_id)
```

#### `find_matching_projects(detected_names)`
- Searches database for existing projects matching detected project names
- Returns dict mapping project names to lists of matching project IDs
- Useful for auto-detection of which projects to update

**Usage:**
```python
matches = find_matching_projects(["myproject", "other_proj"])
# Returns: {"myproject": [5, 12], "other_proj": [8]}
```

#### `get_project_uploads(project_id)`
- Retrieves all uploads that contributed to a project
- Returns list of dicts with upload metadata
- Distinguishes between initial and incremental uploads

**Usage:**
```python
uploads = get_project_uploads(5)
# [
#   {upload_id: 1, filename: "initial.zip", artifact_count: None, is_incremental: False},
#   {upload_id: 42, filename: "additional.zip", artifact_count: 3, is_incremental: True}
# ]
```

#### `extract_and_merge_files(zip_path, target_dir, project_name)`
- Extracts ZIP files and merges them into a target directory
- Useful for preparing files for analysis after incremental upload
- Returns count of extracted files

**Usage:**
```python
file_count = extract_and_merge_files(
    "new_files.zip",
    Path("/projects"),
    "myproject"
)
```

### 4. CLI Enhancements

**File Modified:** [`src/capstone_project_team_5/cli.py`](src/capstone_project_team_5/cli.py)

New functions added:

#### `run_incremental_upload_flow()`
- Complete workflow for incremental uploads
- Prompts user for project mapping
- Performs incremental upload with user guidance
- Displays summary of updates

**Usage:**
```python
from capstone_project_team_5.cli import run_incremental_upload_flow
exit_code = run_incremental_upload_flow()
```

#### Helper Functions
- `prompt_for_incremental_upload()` - Yes/No prompt for incremental mode
- `list_existing_projects()` - Display all projects with file/upload counts
- `prompt_for_project_selection()` - Let user choose project by number
- `prompt_for_project_mapping()` - Interactive mapping of detected projects to existing ones

## Usage Workflow

### For End Users

**Scenario 1: Fresh Upload**
```
1. Run the CLI application
2. Consent → Select ZIP file
3. New projects created automatically
4. Analysis runs, results displayed
```

**Scenario 2: Incremental Upload (Manual)**
```
1. Call run_incremental_upload_flow()
2. Consent → Select ZIP file
3. System detects projects in new ZIP
4. User manually maps to existing projects
   - "project_name" → Select existing project #2
5. Files added to existing project
6. File count updated in database
7. ArtifactSource record created
8. Summary displayed
```

### For Developers

**Programmatic Incremental Upload:**
```python
from capstone_project_team_5.services import incremental_upload_zip

# Get existing project ID (from database or user input)
mapping = {"myproject": existing_project_id}

# Upload with incremental behavior
result, associations = incremental_upload_zip(
    "additional_files.zip",
    project_mapping=mapping
)

# Process results
for existing_id, upload_id in associations:
    print(f"Linked upload {upload_id} to project {existing_id}")
```

**Query Upload History:**
```python
from capstone_project_team_5.services import get_project_uploads

uploads = get_project_uploads(project_id)
for upload_info in uploads:
    print(f"{upload_info['filename']}: {upload_info['file_count']} files")
    if upload_info['is_incremental']:
        print(f"  (incremental contribution: {upload_info['artifact_count']} artifacts)")
```

## Database Schema Impact

### New Table: `artifact_sources`
```sql
CREATE TABLE artifact_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    upload_id INTEGER NOT NULL,
    artifact_count INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (upload_id) REFERENCES upload_records(id) ON DELETE CASCADE
);
```

### Modified Tables
- **projects**: New relationship `artifact_sources` (cascade delete)
- **upload_records**: New relationship `artifact_sources` (cascade delete)

### Backward Compatibility
- Existing projects have no `ArtifactSource` records (they only have the initial `UploadRecord`)
- Queries that don't use `ArtifactSource` continue to work unchanged
- `Project.file_count` is updated consistently for both initial and incremental uploads

## Testing

**Test File:** [`tests/test_incremental_upload.py`](tests/test_incremental_upload.py)

**Coverage:**
- Finding matching projects by name
- Creating ArtifactSource records on incremental upload
- Updating project file counts
- Retrieving complete upload history
- Handling uploads without mapping (creates new projects)
- Multiple incremental rounds
- Cascade deletion of ArtifactSource records
- File extraction and merging

**Run Tests:**
```bash
uv run --frozen pytest tests/test_incremental_upload.py -v
```

## Integration Points

### With Existing Code
1. **upload_zip()** - Still works unchanged; used internally by incremental_upload_zip()
2. **Project Analysis** - Can analyze merged files from incremental uploads
3. **Ranking System** - File counts now include incremental additions
4. **Database** - Uses existing session management and Base model

### Future Enhancements
1. **Conflict Resolution** - Handle duplicate files across uploads
2. **Version History** - Track file versions from different uploads
3. **Rollback** - Ability to remove incremental uploads
4. **UI Integration** - Add incremental upload button to web/TUI interface
5. **Smart Matching** - Auto-detect projects using fuzzy matching instead of exact names

## Example: Complete Incremental Upload Workflow

```python
from pathlib import Path
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project
from capstone_project_team_5.services import (
    find_matching_projects,
    incremental_upload_zip,
    get_project_uploads,
)

# Step 1: User uploads initial portfolio
initial_result = upload_zip("portfolio_2025.zip")
print(f"Created {len(initial_result.projects)} projects")

# Step 2: 3 months later, user wants to add more files
new_zip = "portfolio_updates_spring.zip"

# Step 3: Find which existing projects could be updated
detected_names = [p.name for p in initial_result.projects]
matches = find_matching_projects(detected_names)
print(f"Found matches: {matches}")

# Step 4: Build mapping (could be automatic or user-selected)
mapping = {}
for name, ids in matches.items():
    mapping[name] = ids[0]  # Use first match

# Step 5: Perform incremental upload
result, associations = incremental_upload_zip(new_zip, mapping)
print(f"Updated {len(associations)} projects with new artifacts")

# Step 6: Display upload history
with get_session() as session:
    for proj_id, _ in associations:
        project = session.query(Project).filter(Project.id == proj_id).first()
        uploads = get_project_uploads(proj_id)
        print(f"\n{project.name}:")
        print(f"  Total uploads: {len(uploads)}")
        print(f"  Total files: {project.file_count}")
        for upload in uploads:
            print(f"    - {upload['filename']}: {upload['artifact_count'] or upload['file_count']} files")
```

## Summary

The incremental upload feature:
- ✅ Allows multiple ZIPs to contribute to the same project
- ✅ Tracks upload history with ArtifactSource model
- ✅ Updates project file counts automatically
- ✅ Provides query functions for upload history
- ✅ Maintains backward compatibility with existing code
- ✅ Includes comprehensive test coverage
- ✅ Follows project code style guidelines (ruff, type hints)
- ✅ Ready for CLI integration and UI enhancement

## Files Modified/Created

| File | Type | Changes |
|------|------|---------|
| `src/capstone_project_team_5/data/models/artifact_source.py` | NEW | New ArtifactSource ORM model |
| `src/capstone_project_team_5/data/models/project.py` | MODIFIED | Added artifact_sources relationship |
| `src/capstone_project_team_5/data/models/upload_record.py` | MODIFIED | Added artifact_sources relationship |
| `src/capstone_project_team_5/data/models/__init__.py` | MODIFIED | Export ArtifactSource |
| `src/capstone_project_team_5/services/incremental_upload.py` | NEW | Incremental upload service functions |
| `src/capstone_project_team_5/services/__init__.py` | MODIFIED | Export incremental upload functions |
| `src/capstone_project_team_5/cli.py` | MODIFIED | Added incremental upload CLI functions |
| `tests/test_incremental_upload.py` | NEW | Comprehensive test suite |

