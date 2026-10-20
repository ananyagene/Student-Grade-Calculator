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

### Version 2A — Basic Authentication and Role Management

#### Three User Roles & Access Control
* **Admin**:
  * Full administrative access to student records (Add, Edit, Delete).
  * Create Teacher accounts and assign specific courses/classes (e.g., `MCA AI`, `BCA`, or `ALL`).
  * Class Analytics, Grade Distribution, and System Overview.
  * Class CSV spreadsheet export.
* **Teacher**:
  * Scoped dashboard displaying only students assigned to their designated course/class.
  * Enter and update subject marks for assigned students with automatic recalculation.
  * View detailed student result scorecards and download student PDF reports.
* **Student**:
  * Self-registration portal with auto-provisioned student account.
  * Dedicated student dashboard, personal result card, and interactive performance charts.
  * Download personal official PDF report card and personal CSV scorecard.
  * Strict security isolation: Cannot view other students' records, modify marks, or access Admin/Teacher routes.

#### Security & Authentication
* Password hashing using Werkzeug (`generate_password_hash` and `check_password_hash`).
* Session-based login management with role decorators (`@login_required`, `@admin_required`, `@teacher_required`).
* Initial Admin Setup Wizard (`/setup-admin`) for initial configuration.
* Flash alert system for user notifications and permission denials.

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
├── app.py                      # Flask backend, auth logic, role routing, database operations
├── test_v2a.py                 # Automated integration and security test suite
├── README.md                   # Complete documentation
├── student_results.db          # SQLite database (students, subjects, users)
│
├── static/
│   └── style.css               # Clean, responsive CSS styling and role badges
│
└── templates/
    ├── base.html               # Base layout with role-aware navigation and flash alerts
    ├── login.html              # Unified login page for Admin, Teacher, and Student
    ├── register.html           # Student self-registration form
    ├── setup_admin.html        # Initial Admin setup wizard
    ├── admin_dashboard.html    # Admin management overview & statistics
    ├── admin_teachers.html     # Teacher account creation & course assignment
    ├── admin_student_add.html  # Admin student entry form
    ├── admin_student_edit.html # Admin student edit form
    ├── teacher_dashboard.html  # Teacher scoped dashboard for assigned classes
    ├── teacher_update_marks.html # Teacher marks update and recalculation
    ├── student_dashboard.html  # Student personal dashboard
    ├── student_my_result.html  # Student detailed result scorecard
    ├── student_my_performance.html # Student visual performance analytics
    ├── students.html           # Admin directory of all students with search & filters
    ├── student_detail.html     # Detailed student scorecard view
    ├── analytics.html          # Class-wide analytics with Chart.js charts
    └── index.html              # Grade calculator landing page
```

## Default Accounts & Testing Credentials

| Role | Username / Identifier | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Full system access, teacher creation, student CRUD, analytics, CSV export |
| **Teacher** | Created by Admin | Set by Admin | Students in assigned course (e.g. `MCA AI`), mark editing, PDF download |
| **Student** | Roll Number (e.g. `101`) or custom username | `student123` or registered password | Personal scorecard, performance charts, personal PDF and CSV downloads |

## How to Run

1. Clone or open the repository.
2. Open the project folder in the terminal.
3. Install required dependencies:
   ```bash
   pip install flask reportlab
   ```
4. Run the Flask application:
   ```bash
   python app.py
   ```
5. Open `http://127.0.0.1:5000/` in your browser.
6. To run the automated test suite:
   ```bash
   python test_v2a.py
   ```

## Development Progress

* [x] Version 1A — Basic Grade Calculator
* [x] Version 1B — Add/Remove Subjects
* [x] Version 1C — Individual Subject Grades
* [x] Version 1D — Pass/Fail Status
* [x] Version 1E — Subject-wise Remarks
* [x] Version 1F — Student Result Management System
* [x] Version 2A — Basic Authentication and Role Management (Admin, Teacher, Student)

## Future Improvements

Possible future improvements may include:

* Cloud database deployment (PostgreSQL / MySQL)
* Multi-semester GPA / CGPA transcript calculation
* Automated email notifications / result publishing
* Attendance tracking integration
* AI-based performance insights and study tips

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
