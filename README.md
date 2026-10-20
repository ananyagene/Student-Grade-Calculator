# Student Grade Calculator

A Student Result Management System built using Python, Flask, HTML, CSS, JavaScript, and SQLite.

I started this project as a basic grade calculator where users could enter marks and calculate their percentage and grade. Over time, I kept adding features to make it more useful.

The project now includes student result management, performance analysis, separate dashboards for admins, teachers and students, and academic management features.

I've divided the development into versions so that I can add new features while learning how different parts of a web application work together.

## Features

### Version 1A — Basic Grade Calculator

The first version focused on basic result calculations.

- Enter student name and subject marks
- Calculate total marks and percentage
- Calculate overall grade
- Validate marks entered by the user

### Version 1B — Dynamic Subjects

Instead of having a fixed number of subjects, users can now:

- Add subjects dynamically
- Remove subjects
- Enter marks for any number of subjects
- Recalculate results automatically

### Version 1C — Individual Subject Grades

- Calculate grades for each subject separately
- Display subject-wise marks and grades

### Version 1D — Pass/Fail Status

Added pass/fail calculation for individual subjects and the overall result.

- Marks of 40 or above are considered PASS
- Marks below 40 are considered FAIL
- Students must pass every subject to receive an overall PASS

### Version 1E — Subject-wise Remarks

Added automatic remarks based on marks obtained in each subject.

| Marks | Remark |
|---|---|
| 90–100 | Excellent |
| 80–89 | Very Good |
| 70–79 | Good |
| 60–69 | Satisfactory |
| 40–59 | Needs Improvement |
| Below 40 | Fail |

### Version 1F — Student Result Management System

This was a major update where the project moved beyond calculating results for one student.

#### Student Management

- Add multiple students
- Store student information and results
- View individual student records
- Edit and delete student records
- Save roll number, course, semester and academic year

#### Result Analysis

Each student result includes:

- Total marks and percentage
- Overall grade and pass/fail status
- Highest and lowest scoring subjects
- Average marks
- Number of passed and failed subjects
- Grade distribution
- Strong subjects and subjects needing improvement
- Performance category and automatic remarks
- Pass percentage
- Result messages for different performance levels

#### Search, Filter and Sort

- Search students by name or roll number
- Filter students by grade or pass/fail status
- Sort students by percentage
- Sort names alphabetically (A–Z and Z–A)

#### Class Analytics

Added a separate section to understand overall class performance.

- Total number of students
- Class average percentage
- Highest and lowest scoring students
- Number of passed and failed students
- Overall class pass percentage

#### Charts and Reports

- Grade distribution chart
- Subject performance chart
- Pass/fail chart
- CSV export
- Individual PDF result reports

#### Database

Initially, the application handled results without permanent storage. SQLite was later added to save student details, subjects and marks.

This allows previously saved records to remain available after restarting the application.

#### Interface Improvements

- Responsive layout
- Result summary cards
- Improved tables and navigation
- Clear pass/fail indicators
- Better form validation and error messages
- Empty-state messages when no records are available

---

### Version 2A — Authentication and Role Management

In this version, I added a login system with three different user roles: Admin, Teacher and Student.

Each role has its own dashboard and access permissions.

#### Admin

- View and manage student records
- Add, edit and delete students
- Create teacher accounts
- Assign teachers to courses/classes
- View class analytics
- Manage student results
- Export student data as CSV

#### Teacher

- Access a separate teacher dashboard
- View students from assigned courses/classes
- Enter and update marks
- View student results
- Download student PDF reports

#### Student

- Register and log in
- Access a personal dashboard
- View subject-wise marks and grades
- Check percentage and pass/fail status
- View performance charts
- Download personal PDF and CSV reports

Students can only view their own results and cannot edit marks or access other student records.

#### Authentication and Security

- Password hashing using Werkzeug
- Flask session-based login
- Role-based access control
- Protected routes
- Logout functionality
- Initial Admin setup
- Error and notification messages

---

### Version 2B — Academic Management System

Version 2B focuses on organizing the academic side of the application.

Previously, the system mainly worked with student records and their results. This update connects students with courses, semesters, subjects and teachers.

#### Course Management

- Add new courses such as MCA, BCA and B.Tech
- Edit and delete courses
- Assign students to courses
- View students belonging to a particular course

#### Semester Management

- Manage semesters for different courses
- Assign students to semesters
- View semester-wise student records
- Display current semester details

#### Subject Management

- Add subjects with names and subject codes
- Assign subjects to courses and semesters
- Edit and remove subjects
- Prevent duplicate subject assignments
- View subjects for a selected course and semester

#### Teacher Assignment

- Assign teachers to subjects
- Display assigned subjects on the teacher dashboard
- View students enrolled in assigned subjects
- Allow teachers to manage marks for authorized subjects

#### Student Academic Profile

Student profiles now include:

- Name and roll number
- Course
- Semester
- Academic year
- Enrolled subjects

#### Dashboard Updates

**Admin Dashboard**
- Manage courses, semesters and subjects
- Assign teachers
- Manage student academic details
- View course-wise and semester-wise students

**Teacher Dashboard**
- View assigned subjects
- View students enrolled in those subjects
- Enter and update marks

**Student Dashboard**
- View course and semester
- View enrolled subjects
- Access academic details
- View results and performance reports

Academic information is stored in the existing SQLite database.

---

## Grading System

The application currently uses the following grading system:

| Marks / Percentage | Grade |
|---|---|
| 90–100 | A |
| 80–89 | B |
| 70–79 | C |
| 60–69 | D |
| Below 60 | F |

### Pass/Fail Rules

- 40 or above: PASS
- Below 40: FAIL
- All subjects must be passed for the overall result to be PASS

Grades and pass/fail status are calculated separately.

### Performance Categories

| Percentage | Category |
|---|---|
| 90–100 | Excellent |
| 80–89 | Very Good |
| 70–79 | Good |
| 60–69 | Average |
| Below 60 | Needs Improvement |

---

## Tech Stack

| Technology | Used For |
|---|---|
| Python | Backend logic and calculations |
| Flask | Web application |
| HTML | Page structure |
| CSS | Styling and responsive design |
| JavaScript | Dynamic forms and interactions |
| SQLite | Storing student and academic data |
| Werkzeug | Password hashing |
| Chart.js | Charts and visualizations |
| ReportLab | PDF reports |
| Git & GitHub | Version control |

## Project Structure

Main files and templates used in the project:

```text
student-grade-calculator/
│
├── app.py
├── README.md
├── test_v2a.py
├── .gitignore
├── student_results.db
│
├── static/
│   └── style.css
│
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── setup_admin.html
    ├── admin_dashboard.html
    ├── admin_teachers.html
    ├── teacher_dashboard.html
    ├── teacher_update_marks.html
    ├── student_dashboard.html
    ├── student_my_result.html
    ├── student_my_performance.html
    ├── student_add.html
    ├── student_edit.html
    ├── student_detail.html
    ├── students.html
    └── analytics.html
```

Additional academic management templates may be included in Version 2B.

## How to Run

### 1. Clone the Repository

```bash
git clone https://github.com/ananyagene/Student-Grade-Calculator.git
```

### 2. Open the Project Folder

```bash
cd Student-Grade-Calculator
```

### 3. Install Dependencies

```bash
pip install flask reportlab
```

### 4. Run the Application

```bash
python app.py
```

### 5. Open in Browser

Open:

`http://127.0.0.1:5000/`

For a new installation, complete the initial Admin setup before using the role-based dashboards.

### Run Tests

```bash
python test_v2a.py
```

## Development Progress

- [x] Version 1A — Basic Grade Calculator
- [x] Version 1B — Dynamic Subjects
- [x] Version 1C — Individual Subject Grades
- [x] Version 1D — Pass/Fail Status
- [x] Version 1E — Subject-wise Remarks
- [x] Version 1F — Student Result Management System
- [x] Version 2A — Authentication and Role Management
- [x] Version 2B — Academic Management System
- [ ] Version 3 — Examination Management System

## What's Next?

### Version 3 — Examination Management System

The next version will focus on handling examinations and semester results.

Planned features:

- Internal and external examination marks
- Assignment and practical marks
- Subject credits
- Semester-wise result calculation
- SGPA and CGPA calculation
- Backlog and reappear management
- Result publishing and locking

### Other Features I May Add Later

- Advanced performance analytics
- AI-based study suggestions
- Student performance trends
- Email notifications
- REST APIs
- Cloud database
- Online deployment

## What I'm Learning From This Project

I'm using this project to get hands-on experience with:

- Python and Flask
- Frontend and backend development
- HTML, CSS and JavaScript
- SQL and databases
- Authentication and user roles
- CRUD operations
- Data analysis and visualization
- Git and GitHub
- Building and improving a full-stack application

## About the Project

This is an ongoing learning project.

My main aim is to understand how a web application is developed, starting from basic calculations and gradually adding features like database storage, authentication, academic management and analytics.

Instead of building everything at once, I'm working on it version by version so that I can understand the code and improve the application as I learn.

---

**Current Version:** 2B — Academic Management System

**Next Version:** 3 — Examination Management System

**Status:** In Development
