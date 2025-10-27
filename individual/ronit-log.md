# Ronit Buti's Weekly Logs

**GitHub:** [@Ron-it](https://github.com/Ron-it)

_Last Updated:_ October 26, 2025

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
