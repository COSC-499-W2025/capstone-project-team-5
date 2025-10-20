[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20510514&assignment_repo_type=AssignmentRepo)
# Project-Starter
Please use the provided folder structure for your project. You are free to organize any additional internal folder structure as required by the project. 

```
.
├── docs                    # Documentation files
│   ├── contract            # Team contract
│   ├── proposal            # Project proposal 
│   ├── design              # UI mocks
│   ├── minutes             # Minutes from team meetings
│   ├── logs                # Team and individual Logs
│   └── ...          
├── src                     # Source files (alternatively `app`)
├── tests                   # Automated tests 
├── utils                   # Utility files
└── README.md
```

Please use a branching workflow, and once an item is ready, do remember to issue a PR, review, and merge it into the master branch.
Be sure to keep your docs and README.md up-to-date.

## System Design Updates

### System Architecture Diagram
<img alt="SAD" src="https://github.com/user-attachments/assets/359730c1-3bd8-4397-a6fc-67b4bc08e843" />

**Explanation of Changes:**  
After feedback from the class discussions we added a direct connection between the data extraction and data analysis components to ensure that analysis is triggered automatically after data is extracted. Previously, data was only stored in the database without a defined process to initiate analysis, so this change establishes a clearer and more functional workflow. We also added a direct connection from the user to data analysis, skipping data extraction, in the event that a user wants to analyze data that has already been extracted.

These changes were made before our intial submission, and we have not received any other feedback. Because of this, we did not make any changes from our initial submission to now.

---

### 🔄 Data Flow Diagram
<img alt="DFD" src="https://github.com/user-attachments/assets/68f99928-e1ee-4887-a0a9-2f6fbb5caac5" />

After feedback from the class discussions we reorganized the diagram to flow in a clockwise direction, reducing clutter and minimizing overlapping data flow arrows. Several data flow directions were corrected for accuracy, and the Analysis process was decomposed into smaller, more detailed subprocesses to better illustrate its internal operations.

These changes were made before our intial submission, and we have not received any other feedback. Because of this, we did not make any changes from our initial submission to now.

---

### 🧱 Work Breakdown Structure (WBS)
![Work Breakdown Structure](./images/work_breakdown_structure.png)

---
