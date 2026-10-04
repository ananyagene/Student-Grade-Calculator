# Student Grade Calculator

A simple beginner-friendly web application built with Python and Flask to calculate student marks, percentage, and grades.

This project is being developed gradually, with new features added step by step to keep the code simple and easy to understand.

## Features

### Version 1A — Basic Grade Calculator

* Enter student name
* Enter marks for subjects
* Calculate total marks
* Calculate percentage
* Calculate overall grade
* Basic input validation
* Simple and clean interface

### Version 1B — Dynamic Subjects

* Add new subjects dynamically
* Remove subjects
* Enter any number of subjects
* Calculate total and percentage based on subjects entered
* Validate subject names and marks

### Version 1C — Individual Subject Grades

* Calculate a grade for each subject
* Display subject name, marks, and individual grade
* Continue displaying total marks, percentage, and overall grade
* Works with any number of subjects

## Grade System

| Percentage | Grade |
| ---------- | ----- |
| 90–100     | A     |
| 80–89      | B     |
| 70–79      | C     |
| 60–69      | D     |
| Below 60   | F     |

## Tech Stack

* Python
* Flask
* HTML
* CSS
* JavaScript

## Project Structure

```text
student-grade-calculator/
│
├── app.py
├── templates/
│   └── index.html
└── static/
    └── style.css
```

## How to Run Locally

Install Flask:

```bash
pip install flask
```

Run the application:

```bash
python app.py
```

Then open the local URL provided by Flask in your browser.

## Development Progress

* [x] Version 1A — Basic Grade Calculator
* [x] Version 1B — Add/Remove Subjects
* [x] Version 1C — Individual Subject Grades
* [ ] Version 1D — Coming Soon
* [ ] More features coming

## Purpose

This is a learning project focused on understanding how a simple Python backend and frontend work together.

The application is being built incrementally, with each version introducing one new feature while keeping the code beginner-friendly and easy to understand.
