# Ojus Sharma's Weekly Logs

**GitHub:** [@ojusharma](https://github.com/ojusharma)


<!-- <details> -->
  <summary><h3>T2 Week 10</h3></summary>

  <img width="1363" height="793" alt="image" src="https://github.com/user-attachments/assets/60000cb6-6285-4a28-8e2e-8eec4634f644" />


#### What Went Well
- Prepped for peer testing #2. excited! :)
- Merged:
  - [PR #378 - Refactor Education & Experience Pages](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/378): Extracted duplicated CRUD state management logic from `EducationPage` and `ExperiencePage` into a reusable `useCrudList` custom hook, eliminating ~250 lines of duplicate code. Each page now only defines its own API mappings, validation rules, and payload builders, while delegating all list management, form handling, and deletion to the shared hook. This is a code-only refactor with no visual changes.
  
  - [PR #379 - Refactor + Tests for Experience Page](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/379): Built on #378 by adding bullet point support to experience entries across forms, JSON serialization, and card displays. Introduced comprehensive unit tests for the `useCrudList` hook (16 test cases covering loading, listing, creating, updating, deleting, form state, validation, and error handling) as well as integration tests for bullet point workflows. All tests pass locally via Jest.
  
  - [PR #389 - Create User Profile UI](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/389): Introduced the User Profile page enabling users to manage personal and contact information (name, email, phone, address, LinkedIn, GitHub, website). Introduced a `useSingletonForm` hook, a reusable abstraction for managing single-resource forms, complementing the existing `useCrudList` pattern. DOM tests were added covering empty states, create/edit workflows, validation errors, API error surfacing, and 404 handling.

- Reviewed and approved:
  - [PR #377 - refactor(frontend): reorganize renderer structure](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/377):
  My review: Praised the decomposition of the monolithic `app.jsx` into dedicated pages, components, and helpers were a massive win for following best practices and enabling parallel development. Confirmed regression test coverage and approved.

  - [PR #383 - feat: resumes workspace shell (1/4)](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/383):
  My review: Highlighted the clean use of `Promise.allSettled` with a cancellation flag in `useEffect` to prevent state updates on unmounted components. Noted the well-structured helper extraction into `lib/resumes.js`.

  - [PR #384 - feat: resume entry editor (2/4)](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/384):
  My review: Praised the clean separation of concerns with utility functions in `resumes.js`, the thoughtful AI-assist integration with privacy consent handling, and the complete inline CRUD workflow. Flagged a potential issue where the AI Assist toggle UI state might not propagate backend parameters.

  - [PR #386 - test: resume frontend coverage (4/4)](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/386):
  My review: Testing is comprehensive and hits every important test case: covering navigation, AI-assisted draft generation, preview rendering, and binary response handling. Good to merge!

  - [PR #390 - Dashboard stat cards](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/390):
  My review: Commended the data consistency fix and the defensive coding for count helpers. Noted the cache path fix in `analyze_all_projects` as a solid reliability improvement.

  - [PR #392 - Progress Change](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/392):
  My review: Praised the "super clean" multi-phase progress UI updates and the massive improvement to progress calculation accuracy. Approved the backend observability enhancements via detailed timing logs.

  - Reviewed and approved individual logs

#### What Didn't Go Well
- All good

#### Planning for Next Week
- Complete Peer Testing #2, gather feedback and implement changes
- Work towards milestone 3
- Continue reviewing teammates' PRs to support code collaboration

<!-- </details> -->



 <details>
  <summary><h3>T2 Week 9</h3></summary>

<img width="750" height="300" alt="image" src="https://github.com/user-attachments/assets/922323eb-829c-4878-8322-80ec9adf817a" />


#### What Went Well
- Pivoted to frontend development this week, building out the resume-related UI pages in the Electron app
  - [PR #362 - Create Work Experience UI](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/362): Built a full CRUD `ExperiencePage` component for managing work experience entries in the frontend. Supports creating, editing, and deleting entries via an inline form with fields for company, title, location, date range, an "I currently work here" toggle, and description. Includes loading/empty/error states and a two-step delete confirmation to prevent accidental data loss. Added router integration (`'experience'` case in `PageRouter` in `App.jsx`), mock API stubs (`createWorkExperience`, `updateWorkExperience`, `deleteWorkExperience`), and 10 DOM tests covering navigation, empty state, card rendering, form open/cancel, create/edit/delete flows, validation, and API error handling.
  - [PR #364 - Create Education UI](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/364): Added a new `EducationPage` component following the same pattern as the Experience page. Education cards display degree, institution, field of study, GPA, date range, and a "Current" tag for ongoing entries. Includes inline delete confirmation (Yes/No), registration in `App.jsx` (import + route in `PageRouter`), and 12 DOM tests in `Education.dom.test.jsx` covering empty state, card rendering, form open/close, create, edit, delete, and validation errors.

- Reviewed and approved:
  - [PR #359 - feat: (frontend) add portfolio functionality](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/359):
  My review:  The PortfolioPage follows the exact same patterns as ProjectsPage with cancelled refs, useApp(), and Tailwind classes, making the codebase easy for the team to navigate. Highlighted the massive test coverage. Brownie points for the `bootToPortfolioPage` helper. Also pointed out a code chunck that could lead api spams due to re-rendering.

  - [PR #358 - fix: set auth username header on login and restore from localStorage](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/358):
  My review: Reviewed the bug fix for file upload and auth username header population using `setAuthUsername`. Quick targeted fix that unblocked the upload workflow.

  - Reviewed and approved Individual logs

#### What Didn't Go Well
- All good

#### Planning for Next Week
- Continue building out remaining frontend UI pages (skills, projects detail views)
- Confirm Milestone req
- Continue reviewing teammates' PRs to support code collaboration
- Coordinate with team on integration testing across the full frontend-backend pipeline

</details>

<details>
  <summary><h3>T2 Week 6,7,8</h3></summary>

<img width="700" height="350" alt="image" src="https://github.com/user-attachments/assets/a8f24f7e-50ba-41dd-a556-e7cb975969c0" />

#### What Went Well
- Succesfully gave the milestone 2 presentation
- Successfully recorded the milestone demo video
- [PR #309 - Create Resume Generator Service](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/309): Introduced the first iteration of the resume generation tool. It pulls user data (contact info, education, work experience, projects, skills) from existing DB services and renders it into a professionally formatted LaTeX resume using the Jake Gutierrez ATS-friendly template. Includes template-agnostic data contracts (`resume_data.py`), an abstract base class enabling a pluggable template architecture (`templates/base.py`), the full Jake template implementation (`templates/jake.py`), and a service layer (`resume_generator.py`) that aggregates all user data and exposes public APIs for `.tex` and `.pdf` generation.
>[!IMPORTANT]
> **Justification for PR size:**
> The team was consulted and agreed that the resume generator is a foundational, tightly coupled feature - the data contracts, template engine, LaTeX rendering, and service layer are all interdependent. Splitting this across multiple PRs would have left the feature in an untestable, incomplete state where no single piece could be verified in isolation. Without the full pipeline (data fetching → template rendering → PDF compilation) present together, it would have been impossible to run meaningful end-to-end tests or validate that the generated resumes are correct.
- [PR #339 - Implement Projects Pagination](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/339): Added pagination support to the `GET /api/projects` endpoint, replacing the previous plain list response with a structured `PaginatedProjectsResponse` containing `items` and `pagination` metadata (`total`, `limit`, `offset`, `has_more`). This is an important scalability improvement as the number of user projects grows, returning all projects in a single unbounded response becomes inefficient and degrades performance. Pagination ensures the API remains responsive by allowing clients to fetch projects in controlled chunks. The PR also refactored the shared `PaginationMeta` schema and related constants into a reusable `common.py` module, eliminating duplication that previously existed in `skills.py`. Comprehensive tests were added covering default pagination, custom `limit`/`offset` parameters, invalid parameter validation (422 errors), empty database handling, and offset-beyond-total edge cases.

- Reviewed and approved:
  - [PR #331 - Role type integration](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/331): 
  My review: Praised the clean end-to-end integration and solid edge-case test coverage. Brownie points for using `nullable=True` on the JSON column for backward compatibility.
  
  - [PR #321 - User API endpoints Improvements](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/321): 
  My review: Code follows current structure and the decided-upon sprint changes.
  
  - [PR #316 - test: Add tests for resume API endpoints](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/316): 
  My review: Tests are holistic, follow codebase standards, and verified locally. Brownie points for breadth of coverage.
  
  - [PR #315 - feat(api): Add resume project CRUD and PDF generation endpoints](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/315): 
  My review: Eendpoints follow existing patterns from work exp/education, keeping the codebase cohesive. Solid auth enforcement critical for real user data.
  
  - [PR #313 - test: work experience and education API endpoints](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/313): 
  My review: Praised the comprehensive test coverage across all major workflows.
  
  - [PR #312 - feat(api): work exp and education endpoints](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/312): 
  My review: Commended the simplified auth integration and confirmed the code follows codebase standards and patterns.
  
  - [PR #311 - User API endpoints](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/311): 
  My review: Endpoints follow best practices, suggested exploring integration with resume generation next week. Verified locally.
  
   - Reviewed and approved Individual logs
  
#### What Didn't Go Well
- All good

#### Planning for Next Week
- Analyze mileston2 feedback
- Speak to team about UI choices
- Continue reviewing teammates' PRs to support code collaboration
- Review more PRs :)
  
</details>


---


<details>
  <summary><h3>January</h3></summary>
  
<details>
  <summary><h3>Week 1</h3></summary>
  
<img width="1018" height="671" alt="image" src="https://github.com/user-attachments/assets/34f8f13a-e3b6-4dee-b85e-f1927c47368b" />

### What Went Well
  - Decided API stack (FASTAPI)
  - Created a Diff checker tool that will allow faster scanning times
  - Reviewed PRs

  ### What Didn't Go Well
  - All good  

  ### Planning for Next Week
  - Work on integrating diff checker into codebase and add functionality to it
  - Start migrating skill detector as REST API
</details>

---

<details>
  <summary><h3>Week 2</h3></summary>
  <img width="920" height="735" alt="image" src="https://github.com/user-attachments/assets/df4ec2c9-1278-44e1-a79a-bb0acb5a922c" />

### What Went Well

#### Coding Tasks:
- Successfully completed and merged [PR #240](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/240) : Create Skills Endpoint, adding API endpoint functionality for the Skills feature
- Reviewed and approved [PR #233](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/233): Resume models + services by @xvardenx - adding user resume storage functionality
- Reviewed and approved [PR #239](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/239) : feat: store user edits in db by @ribhavsharma - enabling portfolio edit persistence
- Reviewed and approved Individual logs
  
### What Didn't Go Well
- Everything went smoothly

### Planning for Next Week
- Build on the Skills Endpoint based on feedback
- Continue reviewing teammates' PRs to support code collaboration
- Continue enhancing the Diff Checker Tool functionality and connect it to broader project features as needed
</details>

---

<details>
  <summary><h3>Week 3</h3></summary>

<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/cb533892-3c37-4b5e-9512-4a331534fc77" />


#### What Went Well
- Successfully completed and merged [PR #257](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/257) : Export Saved Analysis as PDF/TXT
- Reviewed and approved [PR #256](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/256): feat: add endpoint for portfolio edit by Ribhav. Added suggested improvements (persisting sessions)
- Reviewed and approved [PR #251](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/251) : feat(api): add project analysis endpoints with ZIP storage by Ronit
- Reviewed and approved Individual logs
- Prepared for Peer Testing
  
#### What Didn't Go Well
- Had to attend check-in online due to a (horribly inconvenient) infection

#### Planning for Next Week
- Work with team to cover any missed/incomplete requirements (from my end, I will bring up the diff checker tool and how we can integrate it)
- Continue reviewing teammates' PRs to support code collaboration
- Enhance the PDF/TXT analysis export to support better styling
- Do Peer Testing
</details>

---

<details>
  <summary><h3>Week X</h3></summary>

### What Went Well
  - 

  ### What Didn't Go Well
  - 

  ### Planning for Next Week
  - 
</details>

</details>



---
<details>
  <summary><h3>Term 1</summary>
    
<details>
  <summary><h3>September</summary>

<details>
  <summary><h3>Week 3</summary>

<img width="1068" height="626" alt="image" src="https://github.com/user-attachments/assets/4aaa76bd-bd43-4903-bfaf-4ca2ef5a0dcb" />

### Team Activities
- **Project Requirements Discussion**: Discussed and finalized project requirements with the team members.
- **Requirements Analysis**: Spoke to 4 different teams and compared their requirements with ours, and eventually improved our requirements. 

### Personal Contributions
- **Folder Structure**: Created the initial folder structure of the repo, following the format highlighted by the project-starter
- **Non-functional requirements**: Decided on 2 non-functional requirements for the project

</details>

---

<details>
  <summary><h3>Week 4</h3></summary>

<img width="2109" height="1215" alt="image" src="https://github.com/user-attachments/assets/d11d6faf-bb24-47a2-9f26-df09a67dd8ef" />

### What Went Well
  - Created the initial system architecture diagram with Sparsh (based on Ronit's draft with Ribhav) and got it ready for the Wednesday in-class activity.
  - Spoke to 4 teams on Wednesday about our proposed system architecture diagram, with a split between cloud and local processing
  - Proposed that the team meet twice a week to stay on the same page. Set up a when2meet instance to decide on meeting times.
  - Had a team meeting to finalise project requirements :)

  ### What Didn't Go Well
  - Sparsh and I had to stay pretty late on Tuesday to get the system architecture ready for the in-class activity. To prevent this from happening, we pitched the idea of having a short team meeting on Mon/Tue to get the team on the same page. The team was happy and understanding

  ### Planning for Next Week
  - Working on DFDs for the upcoming week
  - Doing research and having group Knowledge Transfers
  - Meeting twice during the week
</details>
</details>

---
<details>
  <summary><h3>October</h3></summary>
<details>
  <summary><h3>Week 5</h3></summary>

<img width="863" height="659" alt="image" src="https://github.com/user-attachments/assets/b77f6160-aa52-4eb0-ad89-a5ad9a391696" />


### What Went Well
  - Team worked efficiently to get the DFDs ready for class
  - Had insightful conversations within the team, with other teams and Dr Bowen
  - Iterated on initial designs and made a good final design

  ### What Didn't Go Well
  - No problems :)

  ### Planning for Next Week
  - Given the project requirements, we will divide tasks based on previous discussions
  - Doing more research w.r.t finalized requirements and continuing group Knowledge Transfers
</details>


---

<details>
  <summary><h3>Week 6</h3></summary>

<img width="1117" height="642" alt="image" src="https://github.com/user-attachments/assets/e19ff0d6-1d69-42d1-b126-b5e1d9562169" />

### What Went Well
  - Completed workload distribution smoothly with team
  - Created a new tool to extract skills (tools+ Software Eng practices)
  - Tested and merged tool
  - Reviewd PRs
  - Researched into Tauri imnlementation

  ### What Didn't Go Well
  - No problems :)

  ### Planning for Next Week
  - Iterate over current iplementation of skills_detection.py tool
  - Start working on integration of LLMs into skill extraction
  - Review more PRs than this week
</details>

---

<details>
  <summary><h3>Week 7</h3></summary>

<img width="1085" height="639" alt="image" src="https://github.com/user-attachments/assets/bda81a30-5b62-4b5a-b044-4d89ee46b4a7" />

### What Went Well
  - Refactored skill detection tool to follow best practices
  - Altered tests and merged changes
  - Reviewed more PRs :)
  - It was a midterm-heavy week for everyone so we spoke over Discord instead of doing a meeting. 

  ### What Didn't Go Well
  - All positive

  ### Planning for Next Week
  - Get more input on my tools, and plan ahead with the team
  - Start working on integration of LLMs into skill extraction
  - Review even more PRs 
</details>

---

<details>
  <summary><h3>Week 8</h3></summary>

<img width="1075" height="636" alt="image" src="https://github.com/user-attachments/assets/195e3566-e499-4a9b-818b-7cb00cfbb67d" />


### What Went Well
  - Skill detection: Added more mappings for skills (tools and practices) in the constants file
  - Skill detection: Implemented suggested changes from last week (skipping certain files/dirs), removed redundant vars, improved docustrings, etc)
  - Skill detection: Added more tests 🧪
  - LLM Integration: Synced up w/ Ribhav to discuss our plan for the LLM integration tool. We decided it would be best for Ribhav to start with the foundation of the service, and I could built on it next week.
  - Reviewed even more PRs :)

  ### What Didn't Go Well
  - All positive

  ### Planning for Next Week
  - Get started on LLM integration tool
  - Review even more PRs :)
</details>

</details>

---
<details>
  <summary><h3>November</h3></summary>
<details>
  <summary><h3>Week 9</h3></summary>
  
<img width="1095" height="637" alt="image" src="https://github.com/user-attachments/assets/cf136a63-30d8-47e4-9e48-fb2e8cc79ae3" />

### What Went Well
  - Centralized LLM Service: Created service from scratch and integrated it into existing code
  - Reviewed PRs
  - Implemented requested changes on my PRs
  - Had a discussion with Ribhav (as our tools have simmilar behaviour) about the LLM integration and how it would work with our tools
  - Skill Detetctor: Moved the LLM integration for this tool to next week as I worked on creating a centralized LLM service 

  ### What Didn't Go Well
  - All good

  ### Planning for Next Week
  - Work on the LLM integration for the Skill Detetcor (finally)
  - Review more PRs :)
</details>


---

<details>
  <summary><h3>Week 10</h3></summary>

  <img width="1131" height="630" alt="image" src="https://github.com/user-attachments/assets/b6db910a-0f00-419e-9cf7-5af69a0737cc" />


### What Went Well
  - (FINALLY) Fully intgerated LLM service into the skill detection tool
  - Enhanced functionality of LLM tool to handle json extractino from llm response
  - Reviewed PRs :)

  ### What Didn't Go Well
  - All good

  ### Planning for Next Week
  - Need to make small teaks in prompt for skill detection tool
  - Discuss with team about the new analysis requirements laid (time complexity, data structures, etc)
  - Review more PRs :)
</details>

---

<details>
  <summary><h3>Week 12</h3></summary>
<img width="642" height="771" alt="image" src="https://github.com/user-attachments/assets/35f21254-5d7e-42c7-85c7-6f8fcbd3c695" />

### What Went Well
  - Created Java File analyzer for OOP prinicples, and other attributes
  - Reviewed more PRs
  - Got started on new OpenAI provider (next week's PR)

  ### What Didn't Go Well
  - All good

  ### Planning for Next Week
  - Integrate all components and tools for the milestone
  - Complete OpenAI Provider implementation
</details>

---

<details>
  <summary><h3>Week 14</h3></summary>
<img width="1325" height="774" alt="image" src="https://github.com/user-attachments/assets/b67b9633-10de-4d4e-8870-bab8c981a8a1" />

### What Went Well
  - Enhanced Java Analyzer and Python analyzer to prepare them for integration
  - Integrated Java and python analyzer into cli workflow
  - Added deletion logic to code anlaysis persistence layer
  - Opened PR for OpenAI LLM Provider integration (will be closed next week)

  ### What Didn't Go Well
  - ALl good :)

  ### Planning for Next Week
  - Improve TUI integration in the project
  - Fix OpenAI LLM merge conflicts
  - Code cleanup + Cover Edge cases in code logic + Complete remiaing Todos

</details>

</details>

---

<details>
  <summary><h3>December</h3></summary>

<details>
  <summary><h3>Week 14</h3></summary>

  <img width="1146" height="625" alt="image" src="https://github.com/user-attachments/assets/ddc3bb6e-e068-4ad7-8819-67bfdd2a5d67" />


### What Went Well
  - Presented Milestone 1
  - Integrated consent tool check ebfore using LLM for skill detetction
  - Refactored "Skills" section in TUI to split it into tools and practices, for better UX
  - Implemenetd Skills ORM to track skills over time
  - Reviewed PRs :)

  ### What Didn't Go Well
  - All good :)

  ### Planning for Next Term
  - Review more PRs
  - Discuss sugegstions from milestone 1 with team
</details>

</details>
</details>

---


