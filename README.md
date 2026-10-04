# Student Grade Calculator

A beginner-friendly Student Result Management System built using Python, Flask, HTML, CSS, JavaScript, and SQLite.

The project started as a simple grade calculator and is being gradually developed into a complete student result management application.

## Features

### Version 1A — Basic Grade Calculator

* Enter student name
* Enter marks for subjects
* Calculate total marks
* Calculate percentage
* Calculate overall grade
* Basic input validation

### Version 1B — Dynamic Subjects

* Add subjects dynamically
* Remove subjects
* Support any number of subjects
* Recalculate results automatically

### Version 1C — Individual Subject Grades

* Calculate grade for every subject
* Display subject-wise marks and grades

### Version 1D — Pass/Fail Status

* Subject-wise PASS/FAIL status
* 40 or above = PASS
* Below 40 = FAIL
* Overall PASS/FAIL status

### Version 1E — Subject-wise Remarks

* Subject-wise performance remarks
* 90–100 → Excellent
* 80–89 → Very Good
* 70–79 → Good
* 60–69 → Satisfactory
* 40–59 → Needs Improvement
* Below 40 → Fail

### Version 1F — Student Result Management System

#### Result Analysis

* Result Summary Card
* Highest Scoring Subject
* Lowest Scoring Subject
* Average Marks
* Automatic Performance Message
* Passed Subjects Count
* Failed Subjects Count
* Grade Distribution
* Performance Category
* Strong Subjects
* Subjects Needing Improvement
* Pass Percentage
* Fail-safe Result Message

#### Student Details

* Student Name
* Roll Number
* Course/Class
* Semester
* Academic Year

#### Multiple Students

* Add multiple students
* Store multiple student results
* View saved students
* View individual student results

#### Search & Filter

* Search by student name
* Search by roll number
* Filter by PASS/FAIL
* Filter by grade

#### Sorting

* Sort by percentage
* Highest to lowest percentage
* Lowest to highest percentage
* Sort by name
* A–Z and Z–A

#### Class Analytics

* Total students
* Class average percentage
* Highest scoring student
* Lowest scoring student
* Number of passed students
* Number of failed students
* Class pass percentage

#### Charts

* Grade distribution chart
* Subject performance chart
* Pass/fail chart

#### Export

* Export student results as CSV
* Export student result as PDF

#### UI Improvements

* Responsive design
* Mobile-friendly layout
* Result summary cards
* Improved tables
* Better spacing
* Clear PASS/FAIL indicators
* Improved error messages
* User-friendly empty states

#### Data Persistence

* SQLite database
* Save student information
* Save subject information
* Save marks
* Retrieve saved students after restarting the application

## Grading System

| Marks/Percentage | Grade |
| ---------------- | ----- |
| 90–100           | A     |
| 80–89            | B     |
| 70–79            | C     |
| 60–69            | D     |
| Below 60         | F     |

## Pass/Fail System

* Marks ≥ 40 → PASS
* Marks < 40 → FAIL
* All subjects must pass for the overall result to be PASS

## Subject-wise Remarks

| Marks    | Remark            |
| -------- | ----------------- |
| 90–100   | Excellent         |
| 80–89    | Very Good         |
| 70–79    | Good              |
| 60–69    | Satisfactory      |
| 40–59    | Needs Improvement |
| Below 40 | Fail              |

## Performance Categories

| Percentage | Category          |
| ---------- | ----------------- |
| 90–100     | Excellent         |
| 80–89      | Very Good         |
| 70–79      | Good              |
| 60–69      | Average           |
| Below 60   | Needs Improvement |

## Tech Stack

* Python
* Flask
* HTML
* CSS
* JavaScript
* SQLite
* Git
* GitHub

## Project Structure

```text
student-grade-calculator/
│
├── app.py
├── README.md
│
├── templates/
│   └── index.html
│
├── static/
│   └── style.css
│
└── database/
    └── students.db
```

## How to Run

1. Clone the repository.

2. Open the project folder in the terminal.

3. Install the required dependencies.

```bash
pip install flask
```

Install any additional libraries required for CSV/PDF/chart functionality if they are used by the project.

4. Run the Flask application.

```bash
python app.py
```

5. Open the local URL shown in the terminal, usually:

```text
http://127.0.0.1:5000/
```

## Development Progress

* [x] Version 1A — Basic Grade Calculator
* [x] Version 1B — Add/Remove Subjects
* [x] Version 1C — Individual Subject Grades
* [x] Version 1D — Pass/Fail Status
* [x] Version 1E — Subject-wise Remarks
* [x] Version 1F — Student Result Management System

## Future Improvements

Possible future improvements may include:

* User authentication
* Admin dashboard
* Role-based access
* Cloud database
* Online deployment improvements
* Advanced analytics
* AI-based performance insights
* Automated recommendations
* Student login portal

## Purpose

This project is being developed as a practical learning project to strengthen skills in:

* Python
* Flask
* Backend development
* Frontend development
* JavaScript
* SQL and databases
* Data analysis
* Git and GitHub
* Application development

The project is intentionally developed step-by-step so that each version introduces new concepts while keeping the application practical and understandable.
