# Student Grade Calculator

A simple beginner-friendly web application that calculates a student's total marks, percentage, grades, pass/fail status, and subject-wise remarks.

The project is being developed step-by-step to practice **Python, Flask, HTML, CSS, JavaScript, and Git/GitHub**.

## Features

### Version 1A — Basic Grade Calculator

* Enter student name
* Enter marks for 3 subjects
* Calculate total marks
* Calculate percentage
* Calculate overall grade
* Basic input validation

### Version 1B — Dynamic Subjects

* Add multiple subjects dynamically
* Remove subjects
* Start with 3 subjects
* Support any number of subjects
* Recalculate total, percentage, and overall grade automatically

### Version 1C — Individual Subject Grades

* Calculate a grade for every subject
* Display subject-wise marks and grades
* Continue displaying total marks, percentage, and overall grade

### Version 1D — Pass/Fail Status

* Display PASS/FAIL status for every subject
* 40 or above = PASS
* Below 40 = FAIL
* Calculate overall PASS/FAIL status
* Overall result is FAIL if even one subject has less than 40 marks

### Version 1E — Subject-wise Remarks

* Display a remark for every subject
* Remarks are based on the subject's marks
* 90–100 → Excellent
* 80–89 → Very Good
* 70–79 → Good
* 60–69 → Satisfactory
* 40–59 → Needs Improvement
* Below 40 → Fail

## Grading System

| Percentage | Grade |
| ---------- | ----- |
| 90–100     | A     |
| 80–89      | B     |
| 70–79      | C     |
| 60–69      | D     |
| Below 60   | F     |

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

## Tech Stack

* Python
* Flask
* HTML
* CSS
* JavaScript
* Git & GitHub

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
└── static/
    └── style.css
```

## How to Run

1. Clone the repository.

2. Open the project folder in the terminal.

3. Install Flask if it is not already installed:

```bash
pip install flask
```

4. Run the application:

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
* [ ] Version 1F — Coming Soon

## Purpose

This project is being developed as a practical learning project to understand the basics of **Python, Flask, frontend development, validation, Git, and GitHub** through gradual feature development.
