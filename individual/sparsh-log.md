# Sparsh Khanna's Weekly Logs

**GitHub:** [@Sparshkhannaa](https://github.com/Sparshkhannaa)

---


# TERM2 Logs - Sparsh Khanna
---
## Week 6-8 | February 8 - March 1, 2026

<details>
  <summary><h3>Evaluation</h3></summary>

</details>

### Tasks worked on

- User API Endpoints Introduction [PR#311](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/311)
- User API Amends and Improvements [PR#321](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/321)
- Consent API Cleanup and Refactoring [PR#330](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/330)
- Worked on System Architecture Design and DFD for M2.
- Worked with the team on the M2 Presentation.
- Wrote UTs to ensure code correctness and good coverage.
- Reviewed Teammates code


### Personal Contributions

- User API Endpoints Introduction
In this pull request I added new user management API endpoints, including the route handlers, Pydantic schemas for request/response validation, and a comprehensive test suite. The changes included adding user routes, user schemas, and registering the new router in the main API application.

- User API Endpoint Improvements
In this pull request I made amendments and improvements to the user API endpoints introduced earlier. This involved refactoring the user routes for better code quality and adding additional test cases to improve coverage and edge case handling.

- Consent API Cleanup
In this pull request I refactored and cleaned up the consent API routes, schemas and tests. The changes involved introducing a shared API dependencies module, simplifying the consent route handlers, updating the consent schema definitions, and extending the consent record model. The test suite was also significantly cleaned up and streamlined to remove redundancy and improve maintainability.

- System Architecture Design & DFD
Worked on updating our system architecture design and DFD diagrams for the M2 milestone to reflect the current state and direction of the project.

- M2 Presentation
Collaborated with the team to prepare and deliver the M2 presentation.

### Tests Added
- [PR#311](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/311)
- tests/test_users_api.py
- [PR#321](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/321)
- tests/test_users_api.py (additional test cases)
- [PR#330](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/330)
- tests/test_consent_api.py

### PRs Reviewed
- [PR#331](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/331)
- [PR#320](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/320)
- [PR#318](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/318)
- [PR#316](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/316)
- [PR#314](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/314)
- [PR#310](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/310)
- [PR#298](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/298)

### Additional Details

These weeks' contributions spanned building out the user management API endpoints, iterating on them based on feedback, and cleaning up the consent API to reduce technical debt. Additionally, I contributed to the system architecture design and DFD for M2 and worked with the team on the M2 presentation.

---
## Week 4-5 | January 26- February 8, 2026

<details>
  <summary><h3>Evaluation</h3></summary>
<img width="2940" height="1912" alt="image" src="https://github.com/user-attachments/assets/50bcf387-42fd-443d-a74f-21b0ca672d42" />
</details>
### Tasks worked on

- Consent Api endpoints Introduction [PR#303](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/303)
- Wrote UTs to ensure code correctness and good coverage.
- Reviewed Teammates code


### Personal Contributions

- Project Re Ranking Logic Introduction 
In this pull request I added a new batch reranking API endpoint for projects, allowing users to update the importance ranks of multiple projects in a single operation. It includes input validation, updates to the API schema, and comprehensive tests to ensure correct behavior and error handling.

### Tests Added
- [PR#303](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/303)
- tests/test_project_rerank.py

### PRs Reviewed
- [PR#292](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/292)
- [PR#291](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/291)
- [PR#283](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/283)
- [PR#276](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/276)
- [PR#271](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/271)

### Additional Details

This week's contributions were focused on adding project features . M2 work seems to be coming to an end so might start work on M3.

---
## Week 3 | January  18-25, 2026

<details>
  <summary><h3>Evaluation</h3></summary>

<img width="1139" height="636" alt="image" src="https://github.com/user-attachments/assets/d02cfd18-9d55-4ff4-92ee-132abdfdf5cb" />


</details>

### Tasks worked on

- Consent Api endpoints Introduction [PR#248](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/248)
- Made the above change have authorisation and authentication based off feedback from my teammate Ethan. (SAME PR)
- Wrote UTs to ensure code correctness and good coverage.
- Reviewed Teammates code


### Personal Contributions

- Key-role-user Logic Introduction 
This pull request introduces a new consent management API to the project, allowing clients to manage user consent records, query available external services and AI models, and check LLM (Large Language Model) configuration status. The main changes include the addition of new API endpoints for consent, the implementation of related business logic, and the introduction of Pydantic schemas for request and response validation.

### Tests Added
- [PR#248](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/248)
- tests/test_consent_api.py

### PRs Reviewed
- [PR#252](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/252)
- [PR#251](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/251)
- [PR#250](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/250)

### Additional Details

This week's contributions were focused on adding api endpoints for my consent tool that i had worked upon earlier for milestone 1.


## Week 2 | January  11-18, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

<img width="1123" height="621" alt="image" src="https://github.com/user-attachments/assets/7b0066a8-9dec-40f2-9cfa-0a314dab39bc" />



</details>

### Tasks worked on

- Key-role-user Logic Introduction [PR#232](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/232)
- Made the above change Persistent based off feedback from my teammate Ronit. (SAME PR)
- Wrote UTs to ensure code correctness and good coverage.
- Reviewed Teammates code


### Personal Contributions

- Key-role-user Logic Introduction [PR#232](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/232)
This change introduces a user role detection feature based on Git contribution analysis. It adds a new module to determine a user's role (e.g., Lead Developer, Contributor) in a project, integrates this information into the analysis pipeline, and displays the detected role in project summaries and bullet points. 

### Tests Added
- [PR#232](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/232)
- tests/test_role_detector.py : comprehensive test suite for the user role detection logic, covering various scenarios and edge cases to ensure robust and accurate classification.
- tests/test_role_persistence.py: comprehensive test suite that checks for persistence of added db entries for role detections

### PRs Reviewed
- [PR#231](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/231)
- [PR#229](https://github.com/COSC-499-W2025/capstone-project-team-5/pull/229)

### Additional Details

This week's contributions were not based of last week's contributions which were centred around the innit structure for the API CRUD endpoints logic. This was worked upon further by my teammate Ronit this week. I focused on another requirement based off which we are required to narrow down the key role of the user in the relevant projects. The logic for the same is mentioned above. I will have a further discussions with my teammates about upcoming week's work plan and proceed accordingly.

## Week 1 | January  4-11, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

<img width="1470" height="956" alt="Screenshot 2026-01-11 at 8 18 52 AM" src="https://github.com/user-attachments/assets/d883b145-8748-4022-acea-2c41388b3cb0" />


</details>

### Team Activities
- **Requirements Analysis**: Had discussions about Term 2 work structure.

### Personal Contributions
- **API Skeleton**: Made basic API skeleton for API endpoint work in the future.

---
# TERM1 Logs - Sparsh Khanna

## Week 3 | September 15-21, 2025

<details>
  <summary><h3>Evaluation</h3></summary>

![E71811CD-4677-4DC1-BE84-21A49EC3229B](https://github.com/user-attachments/assets/995a966b-8f6a-428f-9ba1-327201ed5232)


</details>

### Team Activities
- **Project Requirements Discussion**: Worked with the team to review and establish project requirements.  
- **Requirements Analysis**: Engaged in detailed discussions with other teams to clarify functional and non-functional needs.  

### Personal Contributions
- **Communication Coordination**: Setup a discord channel and a google doc for requirements looginga dn communication.  
- **Requirements**: Decided on a functional and non functional requirements.



## Week #4 (21 September 2025 - 28 September 2025)
<details>
  <summary><h3>Evaluation</h3></summary>
  
---![9C9A62FC-929A-4852-AC3B-1A2BD66E10E5](https://github.com/user-attachments/assets/5cb2e290-764d-47c9-8f93-9110210ea25b)

</details>

### What Went Well
  - **System Architecture Design**: Built upon initial draft of our system architecture diagram based on in-class discussions and previous week's requirements.
  - **Tech Stack Contribution**: Provided considerable input and ideas during tech stack discussion.
  - **Team Collaboration**: Everyone had good ideas which made discussions more productive and healthy.

  ### What Didn't Go Well
  - **Decision Making Challenges**: I personally felt the team had some issues in coming to an agreement in the cloud vs completly local aspect of our project.
  - **Resolution**: Eventually the team had a healthy discussion to decide what works ^_^ .

  ### Planning for Next Week
  - Create DFDs timely with the team.
  - Study more about python libraries and multithreading.
  - Look more into data mining and file scraping.
### Team Activities
- **System Architecture**: Worked with the team to narrow down our existing ideas to get the best possible architecture diagram for our use case.  
- **Project Proposal**: Engaged in detailed discussion with team to finalise and communicate regarding the project proposal.  

### Personal Contributions
- **Orignal System Architecture Design**: Spent a good amount of time on the orignal system architecture we presented in Class on Wednesday. We decided as a team to not go forward with the same.  
- **Tech Stack Requirements**: Provided inputs and suggetions for relevant libraries and tech staxk we could use.


## Week #5 (28 September 2025 - October 05 2025)
<details>
  <summary><h3>Evaluation</h3></summary>


![99D1327B-6DFA-468A-B910-537E28AEBB96](https://github.com/user-attachments/assets/0929edc8-c0cd-41cc-a686-e2c6a08d8088)
</details>

### What Went Well
  - DFD Level 0 and 1 diagrams were discussed and decided upon in time.
  - **DFD Contribution**: Provided considerable input and ideas during DFD discussion.
  - **Multiprocessing**: Studided more about multiprocessing in python.

  ### What Didn't Go Well
N/A
  ### Planning for Next Week
  - Assigning tasks with a good constructed discussion.
  - Study more about python libraries.

### Team Activities
- **DFD**: Worked with the team to narrow down our existing ideas to get the best possible DFD diagram for our use case.  

### Personal Contributions
- **DFD Contributions**: Provided considerable input and ideas during DFD discussion. 
- **Project Board Contributions**: Created a few user stories to start project board tracking.

## Week #6 (October 05 2025 - October 12 2025)
<details>
  <summary><h3>Evaluation</h3></summary>
<img width="1108" height="625" alt="image" src="https://github.com/user-attachments/assets/fe99909d-563e-4efe-a40d-759b79a2f5d9" />

</details>

### Team Activities
- **Work Distribution**: Worked with the team to discuss and distribute work amongst all of us.  

### Personal Contributions
- **Code Contributions**: Provided code changes and UTS for consent input. 

## Week #7 (October 12 2025 - October 19 2025)
<details>
  <summary><h3>Evaluation</h3></summary>
  
<img width="662" height="706" alt="image" src="https://github.com/user-attachments/assets/225a3179-d099-4222-9071-e4b0f34121c5" />


</details>

### Team Activities
- **Project Structure Discussion**: Reviewed PRs and provided any feedback/suggestions necessary.  

It was a busy week for me due to heavy midterm load and I was unable to be as involved as I could be :(

### Personal Contributions
- **Code Contributions**: Provided further code changes and UTS for consent input, including a small new Feature

### TODOs for NExt week 
- **Parser Tool**: Provide input and code for further improving the Parser tool while distributing work amongst me and Ronit who will be working on this part of the tool.


## Week #8 (October 19 2025 - October 26 2025)
<details>
  <summary><h3>Evaluation</h3></summary>
  <img width="1114" height="645" alt="image" src="https://github.com/user-attachments/assets/873fd2d2-0bb3-466c-89f8-deabfb6c5094" />

</details>

### Team Activities
- **PR Actions**: Reviewed PRs and provided any feedback/suggestions necessary.  
- **Project work Discussion**: Discussed possible overlaps in functionality in working.


### Personal Contributions
- **Code Contributions**: Provided further code changes and UTS for our File parser with a dedicated walker which can be further modified to have a centralised walker instance. I initially worked and spent most of my time on collaborative vs individual projects , however it was assigned to someone else so I had to scrap my PR and work on the walker instead.

### TODOs for NExt week 
- **Parser Tool**:  Discuss Centralisation of File walker and look into any missing gaps in functionality to try and pickup some tasks.

## Week #9 (October 26 2025 - November 02 2025)
<details>
  <summary><h3>Evaluation</h3></summary>
  <img width="1082" height="629" alt="image" src="https://github.com/user-attachments/assets/7f51e2db-8445-4814-9a9a-91b36439018b" />


</details>

### Team Activities
- **PR Actions**: Reviewed PRs and provided any feedback/suggestions necessary.  
- **Project work Discussion**: Discussed about suggested migration srom sqllite to sqlalchemy which will impact my PR.


### Personal Contributions
- **Code Contributions**: Provided further code changes and UTS for getting rid of existing portfolio/resumee entries if a user wishes to.
### TODOs for Next week 
- **Sql Migration**:  modify this week's PR to better reflect and work with the latest suggested infra for db.
- **Multithreading** Look into multithreading and wherever possible implement it without breaking existing functionality.

## Week #10 (November 02 2025 - November 09 2025)
<details>
  <summary><h3>Evaluation</h3></summary
<img width="1198" height="630" alt="image" src="https://github.com/user-attachments/assets/61c3777c-e5f0-4e5d-9198-c9722acd56d1" />


</details>

### Team Activities
- **PR Actions**: Reviewed PRs and provided any feedback/suggestions necessary.  


### Personal Contributions
- **Code Contributions**: Provided further code changes and UT changes to migrate from sqllite to ORM sqlalchemy to keep the logic and approach across the project consistent.
### TODOs for Next week 
- **Backlog Tasks**: Discuss with the team and pick up any free tasks.
- **Multithreading** Look into multithreading and wherever possible implement it without breaking existing functionality.
- 
## Week #12 (November 16 2025 - November 23 2025)
<details>
  <summary><h3>Evaluation</h3></summary

<img width="2940" height="1912" alt="image" src="https://github.com/user-attachments/assets/69cd170d-dae0-4163-a4e1-4bf87da326f0" />

</details>

### Team Activities
- **PR Actions**: Reviewed PRs and provided any feedback/suggestions necessary.  

### Personal Contributions
- **Code Contributions**: Provided code for local C and C++ code analysis in the absence of a llm model , also provided small updates to the consent tool to allow for more ignore patterns. 
### TODOs for Next week 
- **Backlog Tasks**: Discuss with the team and pick up any free tasks.
- **Integration**: Work with the team on integrating any modules that arent already connected and do any code cleanups if necessary.

## Week #13 (November 23 2025 - November 30 2025)
<details>
  <summary><h3>Evaluation</h3></summary
<img width="2940" height="1912" alt="image" src="https://github.com/user-attachments/assets/582957dc-3997-42ad-b802-6ccae43972d2" />
</details>

### Team Activities
- **PR Actions**: Reviewed PRs and provided any feedback/suggestions necessary.  

### Personal Contributions

- **Code Contributions**: Integrated Code analysis logic flow and made local resume bullet points nore robust.
### TODOs for Next week 
- **Finishing Touches**: Discuss with the team and work on any final remaining bugs or features before milestone 1 submission.

## Week #14 (November 30 2025 - December 07 2025)
<details>
  <summary><h3>Evaluation</h3></summary
<img width="1062" height="604" alt="image" src="https://github.com/user-attachments/assets/f0c6918b-5025-459a-a364-a54f8df40dbd" />

</details>

### Team Activities
- **PR Actions**: Reviewed PRs and provided any feedback/suggestions necessary.
- **Team Contract**: Worked and reviewed the team contract
- **Presentation**: Did the final Presentation in Class

### Personal Contributions

- **Code Contributions**: Cleaned up consent tool code to better reflect the AI models being used.

---
