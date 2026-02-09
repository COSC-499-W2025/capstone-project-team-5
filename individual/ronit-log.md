# Ronit Buti's Weekly Logs

**GitHub:** [@Ron-it](https://github.com/Ron-it)

_Last Updated:_ February 8, 2026

---

## Week 5 | January 26-February 8, 2026

*Note: Weeks 4 and 5 are combined into a single entry.*

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1092" height="636" alt="image" src="https://github.com/user-attachments/assets/7073e90a-eecb-46e0-80c9-3328c7a8c8a5" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| **Coding Tasks** | | |
| Replaced project thumbnail URL with image upload | ✅ Done | Replaced external `thumbnail_url` with disk-based image storage, added `PUT/GET/DELETE /api/projects/{id}/thumbnail` endpoints, updated TUI with file picker ([PR #271](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/271)) |
| Implemented incremental uploads, content dedup, and fingerprint cache | ✅ Done | Re-uploaded ZIPs append to existing projects, content-addressed storage with SHA-256, merged analysis builds combined project tree from all uploads, fingerprint cache skips re-analysis when file set unchanged ([PR #297](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/297)) |
| **Testing/Debugging Tasks** | | |
| Added tests for thumbnail upload endpoints | ✅ Done | Covers upload, retrieval, deletion, and validation checks |
| Added tests for incremental upload and dedup | ✅ Done | Covers incremental append, 409 on ambiguous name, dedup of identical content, fingerprint-based analysis skip |
| **Reviewing/Collaboration Tasks** | | |
| Reviewed [PR #273](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/273) (user role API) | ✅ Done | Flagged missing assertions in test setup; suggested edge case tests for input validation |
| Reviewed [PR #292](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/292) (education CRUD) | ✅ Done | Suggested ORM-level GPA validation; noted boundary tests missing despite comments claiming coverage |
| Reviewed [PR #293](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/293) (portfolio endpoints) | ✅ Done | Found `is_showcase` present in response schema but missing from endpoint implementation |
| Reviewed [PR #275](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/275) (configuration + UX fixes) | ✅ Done | Reported CTRL+S save keybind only fixed for project editing but still broken for analysis editing; suggested improved test assertion |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Work on resume export | ❌ Not Started | TBD with team |
| Continue code reviews | | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Expand remaining API endpoints | ✅ Done | Implemented thumbnail image upload endpoints (PR #271) and incremental upload/dedup (PR #297) |
| Work on resume generation | ❌ Not Started | Deferred |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 3 | January 19-25, 2026

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1083" height="634" alt="image" src="https://github.com/user-attachments/assets/3b31aa25-5d7b-41ab-8153-864380b347a7" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| **Coding Tasks** | | |
| Implemented project analysis API endpoints with ZIP storage | ✅ Done | Added `POST /api/projects/{project_id}/analyze` and `POST /api/projects/analyze` endpoints, ZIP storage system for persisted uploads, ... ([PR #251](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/251)) |
| **Testing/Debugging Tasks** | | |
| Added tests for project analysis endpoints | ✅ Done | covering importance score updates, analyze-all, missing ZIP handling, AI fallback |
| **Reviewing/Collaboration Tasks** | | |
| Reviewed [PR #248](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/248) (consent API endpoints) | ✅ Done | Noted test isolation issue - `session.query(ConsentRecord).delete()` deletes all records regardless of user_id; suggested using nonexistent user or transaction rollback |
| Reviewed [PR #250](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/250) (R22 improvements) | ✅ Done | Noted test coverage gap - test name says failures are logged but test only verifies normal operation |
| **Other Tasks** | | |
| Prepared for peer testing | ✅ Done | |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Expand remaining API endpoints | ❌ Not Started | Further API development |
| Work on resume generation | ❌ Not Started | Aggregate all data and create API endpoint |
| Continue code reviews | | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Expand API endpoints to incorporate project analysis | ✅ Done | Implemented project analysis endpoints with ZIP storage |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 2 | January 12-18, 2026

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1083" height="635" alt="image" src="https://github.com/user-attachments/assets/6f0131b7-f9e0-4b9e-864f-19b60cf94667" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| **Coding Tasks** | | |
| Implemented project thumbnail URL support | ✅ Done | Added `thumbnail_url` field to Project model, created service layer functions, updated TUI with set/clear functionality, added URL validation ([PR #225](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/225)) |
| Implemented Projects API CRUD endpoints | ✅ Done | Added GET /api/projects, GET /api/projects/{id}, POST /api/projects/upload, PATCH /api/projects/{id}, DELETE /api/projects/{id} ([PR #229](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/229)) |
| **Testing/Debugging Tasks** | | |
| Added tests for thumbnail URL service | ✅ Done | Tests cover validation, set/get/clear operations, error handling |
| Added comprehensive API endpoint tests | ✅ Done | Full test coverage for all project CRUD operations using FastAPI TestClient |
| **Reviewing/Collaboration Tasks** | | |
| Reviewed [PR #231](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/231) (duplicate file recognition) | ✅ Done | noted potential edge case with hash collisions where different files could overwrite each other if they share same filename and 8-char hash |
| Reviewed [PR #239](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/239) (store user edits in db) | ✅ Done | suggested early return optimization when both title and content are None |
| Reviewed [PR #232](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/232) (user's role in project) | ✅ Done | suggested persisting the information in db for future api usage |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Expand API endpoints to incorporate project analysis | ❌ Not Started | Add endpoints for analysis workflows, importance scoring, etc. |
| Continue code reviews | | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Extend API functionality | ✅ Done | Implemented Projects API CRUD endpoints and thumbnail URL support |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 1 | January 5-11, 2026

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1082" height="642" alt="image" src="https://github.com/user-attachments/assets/419a5217-fac0-41ff-8758-f62e7550e0d9" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Refactored CLI and TUI to utilize new workflows.analysis_pipeline module | ✅ Done | Moved ~400 lines of analysis logic from CLI into dedicated pipeline module |
| Replaced ConsentTool usage with utility function for ignore patterns | ✅ Done | |
| Conducted code reviews | ✅ Done | Ongoing task |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Extend API functionality | ❌ Not Started | |
| Continue code reviews | | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Refactor codebase | ✅ Done | |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 14 | December 01-07, 2025

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1071" height="628" alt="image" src="https://github.com/user-attachments/assets/45940ca9-b086-44b0-a35f-703f0ebefdaa" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Recorded + Edited video demo | ✅ Done | |
| Added importance score breakdown to tui | ✅ Done | |
| Conducted code reviews | ✅ Done | Ongoing task |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Refactor codebase | | | |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Complete video demo | ✅ Done | Video work for milestone #1 |
| Complete milestone #1 submissions | ✅ Done | Video demo, team contract, self-reflection, deliverable, peer evaluation (of other teams) |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 13 | November 24-30, 2025

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1086" height="636" alt="image" src="https://github.com/user-attachments/assets/b15a1cfe-54ed-4e8e-805f-7f99bc73a10f" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Implemented language-agnostic test analysis pipeline | ✅ Done | Added pipeline that walks every project, counts unit/integration tests per language |
| Wired testing metrics into CLI/TUI flows and bullet generator | ✅ Done | |
| Added regression tests for test analyzer, bullet generation, and persistence | ✅ Done | Updated expectations to cover new UX |
| Worked on presentation materials | ✅ Done | Prepared for milestone #1 presentation |
| Conducted code reviews | ✅ Done | Ongoing task |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Complete video demo | ❌ Not Started | Video work for milestone #1 |
| Complete milestone #1 submissions | ❌ Not Started | Video demo, team contract, self-reflection, deliverable, peer evaluation (of other teams) |
| Continue code reviews | ❌ Not Started | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Prepare for presentation/video demo | 🚧 In Progress | Presentation materials done, video demo pending |
| Pending integration stuff | ❌ Not Started |  |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 12 | November 17-23, 2025

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1126" height="646" alt="image" src="https://github.com/user-attachments/assets/c5e99486-147b-4055-96a5-16b6e6fcc19c" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Implemented project importance ranking system | ✅ Done | Calculates + displays project importance scores based on contribution volume, diversity, project duration and file count |
| Added comprehensive unit tests for ranking system | ✅ Done | 14 test cases: score calculation, empty metrics, zero duration, diversity bonus, duration factor, ranking ties, edge cases and score breakdown formatting |
| Added integration test for database persistence | ✅ Done | |
| Conducted code reviews | ✅ Done |  |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Prepare for presentation/video demo | ❌ Not Started |  |
| Pending integration stuff | ❌ Not Started |  |
| Continue code reviews | ❌ Not Started | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Implement project ranking based on contributions | ✅ Done | |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 10 | November 3-9, 2025

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1377" height="810" alt="image" src="https://github.com/user-attachments/assets/b1b6424d-6244-4b66-95f3-4ea283fffba5" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Refactored CLI to display analysis per project | ✅ Done | Each project now shows individual analysis sections for Language, Framework, Skills, Tools, File Analysis, and AI bullet points |
| Implemented fallback to root-level analysis | ✅ Done | When no valid projects found or all projects skipped |
| Refactored analysis logic into helper functions | ✅ Done | Improved code maintainability and organization |
| Added comprehensive tests for per-project analysis | ✅ Done | 3 test cases: per-project display, root fallback, and single AI warning |
| Conducted code reviews | ✅ Done |  |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Implement project ranking based on contributions | ❌ Not Started |  |
| Continue code reviews | ❌ Not Started | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Implement project ranking based on contributions | ❌ Not Started | Deferred to next cycle |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 9 | October 27-November 2, 2025

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1087" height="638" alt="image" src="https://github.com/user-attachments/assets/38ea944b-44b2-4d73-a610-87acb776fbee" />
</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Refactored upload pipeline to support multiple projects in single ZIP | ✅ Done | |
| Created new `Project` ORM model with cascade delete | ✅ Done | Linked to `UploadRecord` via one-to-many relationship |
| Updated CLI to display discovered projects table | ✅ Done | Shows name, path, Git presence, file count |
| Wrote comprehensive tests for multi-project support | ✅ Done | 5 test cases covering various scenarios |
| Conducted code reviews | ✅ Done |  |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Implement project ranking based on contributions | ❌ Not Started |  |
| Continue code reviews | ❌ Not Started | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Complete extraction of projects from zip upload | ✅ Done | Implemented multi-project discovery and extraction |
| Persist extracted projects from the zip upload | ✅ Done | Projects now persisted to database with proper linkage |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 8 | October 20-26, 2025

<details>
  <summary><h3>Evaluation</h3></summary>
    <img width="1065" height="622" alt="image" src="https://github.com/user-attachments/assets/e2ab8833-c198-4586-95fd-62995ead7094" />

</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Set up SQLite database | ✅ Done |  |
| Refactored old config/CRUD operations | ✅ Done |  |
| Implemented integration to store user consent in DB | ✅ Done |  |
| Implemented integration to store metadata of zip upload | ✅ Done |  |
| Researched extracting multiple projects from a single zip upload | 🚧 In Progress | Understanding how to identify and extract individual projects from uploaded archives |
| Conducted code reviews | ✅ Done |  |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Complete extraction of projects from zip upload | ❌ Not Started | Implement logic to identify and extract multiple projects |
| Persist extracted projects from the zip upload | ❌ Not Started | Store extracted project data in database |
| Continue code reviews | ❌ Not Started | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Integrate existing functions together | 🚧 In Progress | Ongoing integration work |
| Set up proper database and integrate with existing functionality | ✅ Done | SQLite DB setup complete with user consent and upload metadata storage |
| Continue code reviews | ✅ Done | Ongoing task |

---

## Week 7 | October 13-19, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

  <img width="1066" height="618" alt="image" src="https://github.com/user-attachments/assets/854e1fd0-9c6b-4512-8d87-5c8be30f7150" />

</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Added pytest to GitHub Actions CI | ✅ Done |  |
| Implemented zip upload + extraction + handling wrong format | ✅ Done | Added validation to reject incorrect upload formats |
| Set up entrypoint to link existing functions | ✅ Done | Part of the application can now run in terminal (+GUI), not just isolated functions and tests |
| Conducted code reviews | ✅ Done |  |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Integrate existing functions together | 🚧 In Progress | Focus on connecting components |
| Set up proper database and integrate with existing functionality | ❌ Not Started | w/ team: DB schema design + integration work |
| Continue code reviews | ❌ Not Started | Ongoing task |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Define + implement zipped upload parsing spec (what to parse, output format, DB storage). | ✅ Done | Completed with extraction and validation |
| Add validation to reject wrong upload formats. | ✅ Done | Implemented format validation |



---

## Week 6 | October 6-12, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

  <img width="1339" height="783" alt="image" src="https://github.com/user-attachments/assets/832667ec-9a98-4d94-a813-7a239562af2b" />


</details>

### Current Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Initialized the codebase with `uv` and `ruff`; added pre-commit hooks (lint + format). | ✅ Done | Linting + formatting enforced via pre-commit |
| Set up `pytest` with a basic example. | ✅ Done |  |
| Populated the Kanban board with initial tasks based on the WBS. | ✅ Done |  |

### To-Dos for Next Cycle
| Task | Status | Notes |
| --- | --- | --- |
| Define + implement zipped upload parsing spec (what to parse, output format, DB storage). | ❌ Not Started |  |
| Add validation to reject wrong upload formats. | ❌ Not Started | |

### Last Cycle's To-Dos
| Task | Status | Notes |
| --- | --- | --- |
| Populate the Kanban/task board based on the Milestone 1 requirements | ✅ Done | Initial tasks created |
| Research Python integration with Tauri for our backend implementation | ❌ Not Started | Will review this later towards the end of Milestone 1 |

---


## Week 5 | September 29-October 5, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

  <img width="1070" height="623" alt="image" src="https://github.com/user-attachments/assets/15744b9f-1bda-40b1-b80b-7a4ab9fb5b9b" />

</details>

### What Went Well

- **DFD Collaboration**: Worked with the team on Monday to create a draft of the Level 0 and Level 1 DFDs
- **DFD Notation Review**: After reviewing DFD notation, identified that we were missing the file system as an entity and added it to improve the diagram
- **Level 1 Enhancement**: Expanded the Level 1 diagram with additional details to make it more comprehensive
- **Feedback Compilation**: Compiled a list of changes that need to be made based on feedback received
- **Smooth Workflow**: Everything went smoothly this week with no major issues or complications

### What Didn't Go Well

- Nothing major - overall smooth and productive week

### Planning for Next Week

- Review the system design to ensure it aligns with our current understanding
- Populate the Kanban/task board based on the Milestone 1 requirements
- Research more about Python integration with Tauri for our backend implementation

---

## Week 4 | September 22-28, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

<img width="1354" height="790" alt="image" src="https://github.com/user-attachments/assets/3b542e7b-5bdc-464f-bd78-616c7297d5a7" />

</details>

### What Went Well

- **System Architecture Design**: Created the initial draft of our system architecture diagram based on in-class discussions and previous week's requirements
- **Tech Stack Research**: Researched and decided on major parts of our tech stack for our proposal
- **Team Collaboration**: Everyone had good contributions and ideas which made discussions easier

### What Didn't Go Well

- **Decision Making Challenges**: I was personally divided in making some decisions (tech stack)
- **Architecture Modifications**: I was also a bit hesitant with modifying system architecture to go completely local
- **Resolution**: Eventually came to conclusions that everyone was happy with and met everyone's preferences

### Planning for Next Week

- Create DFDs
- Conduct more research on tech stack compatibility
  - Investigate if our chosen tech stack will work smoothly with Tauri + Python plugin for the backend

---

## Week 3 | September 15-21, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

  <img width="1064" height="618" alt="image" src="https://github.com/user-attachments/assets/18bfb86e-4d9c-4b15-aa91-bd8abc7b811d" />

</details>

### Team Activities

- **Project Requirements Discussion**: Collaborated with team members to analyze and define project requirements
- **Requirements Analysis**: Participated in comprehensive discussion of functional and non-functional requirements with other teams

### Personal Contributions

- **Cross-Platform Requirements**: Worked on defining and documenting cross-platform compatibility requirement
- **Testing Requirements**: Developed testing criteria for both functional and non-functional requirements

---
