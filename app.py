import os
import io
import csv
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, make_response, send_file, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.secret_key = 'super-secret-key-student-grade-calculator-v2a'

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'student_results.db')

# -------------------------------------------------------------
# Database Setup & Initialization
# -------------------------------------------------------------
def get_db_connection():
    """Connects to SQLite database and returns rows as dictionaries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables for students, subjects, and users with three roles."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            course TEXT NOT NULL,
            semester TEXT NOT NULL,
            academic_year TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Subjects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            marks REAL NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # Users table for Authentication & RBAC (Supports ADMIN, TEACHER, STUDENT)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,           -- 'ADMIN', 'TEACHER', 'STUDENT'
            name TEXT,                    -- Display name
            student_id INTEGER,          -- FK to students(id) for STUDENT role
            assigned_course TEXT,         -- Course/Class for TEACHER role (e.g. 'MCA AI', 'BCA', or 'ALL')
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # Migration check: Ensure columns 'name' and 'assigned_course' exist on 'users'
    cursor.execute('PRAGMA table_info(users)')
    columns = [col['name'] for col in cursor.fetchall()]
    if 'name' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN name TEXT')
    if 'assigned_course' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN assigned_course TEXT')

    # Seed Default Admin Account if no admin exists
    admin_user = cursor.execute("SELECT * FROM users WHERE role = 'ADMIN'").fetchone()
    if not admin_user:
        admin_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, name, student_id, assigned_course)
            VALUES (?, ?, 'ADMIN', 'System Admin', NULL, NULL)
        ''', ('admin', admin_hash))

    # Seed User Accounts for any existing student records that lack one
    students = cursor.execute('SELECT * FROM students').fetchall()
    for s in students:
        existing_user = cursor.execute('SELECT * FROM users WHERE student_id = ?', (s['id'],)).fetchone()
        if not existing_user:
            student_hash = generate_password_hash('student123')
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password_hash, role, name, student_id, assigned_course)
                VALUES (?, ?, 'STUDENT', ?, ?, NULL)
            ''', (str(s['roll_number']), student_hash, s['name'], s['id']))

    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# -------------------------------------------------------------
# Role-Based Access Control (RBAC) Decorators
# -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        if session.get('role') != 'ADMIN':
            flash("Access denied. You do not have permission to access this page.", "danger")
            if session.get('role') == 'TEACHER':
                return redirect(url_for('teacher_dashboard'))
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        if session.get('role') != 'TEACHER':
            flash("Access denied. You do not have permission to access this page.", "danger")
            if session.get('role') == 'ADMIN':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        if session.get('role') not in ['ADMIN', 'TEACHER']:
            flash("Access denied. You do not have permission to access this page.", "danger")
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def check_student_access(student_id, student_course):
    """
    Checks if currently logged in user has authorization to view or download
    the given student's record.
    """
    role = session.get('role')
    if role == 'ADMIN':
        return True
    if role == 'TEACHER':
        assigned = session.get('assigned_course', '')
        return (not assigned or assigned.upper() == 'ALL' or assigned.strip().lower() == student_course.strip().lower())
    if role == 'STUDENT':
        return session.get('student_id') == student_id
    return False

# -------------------------------------------------------------
# Core Calculation & Analysis Logic
# -------------------------------------------------------------
def calculate_grade(percentage):
    """Calculates letter grade based on percentage or mark."""
    if percentage >= 90:
        return 'A'
    elif percentage >= 80:
        return 'B'
    elif percentage >= 70:
        return 'C'
    elif percentage >= 60:
        return 'D'
    else:
        return 'F'

def calculate_remark(marks):
    """Calculates descriptive remark based on subject marks."""
    if marks >= 90:
        return 'Excellent'
    elif marks >= 80:
        return 'Very Good'
    elif marks >= 70:
        return 'Good'
    elif marks >= 60:
        return 'Satisfactory'
    elif marks >= 40:
        return 'Needs Improvement'
    else:
        return 'Fail'

def calculate_performance_message(percentage):
    """Returns overall performance feedback message based on percentage."""
    if percentage >= 90:
        return "Excellent overall performance!"
    elif percentage >= 80:
        return "Very good performance!"
    elif percentage >= 70:
        return "Good performance!"
    elif percentage >= 60:
        return "Satisfactory performance."
    else:
        return "Keep practicing and improve your performance."

def calculate_performance_category(percentage):
    """Returns separate performance category distinct from letter grade."""
    if percentage >= 90:
        return "Excellent"
    elif percentage >= 80:
        return "Very Good"
    elif percentage >= 70:
        return "Good"
    elif percentage >= 60:
        return "Average"
    else:
        return "Needs Improvement"

def analyze_student_data(student_info, raw_subjects):
    """
    Computes all 12 analytical metrics for a student.
    student_info: dict with keys (id, name, roll_number, course, semester, academic_year)
    raw_subjects: list of dicts with (subject_name/name, marks)
    """
    processed_subjects = []
    grade_dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    strong_subjects = []
    weak_subjects = []

    for sub in raw_subjects:
        name = sub.get('subject_name') or sub.get('name')
        mark_val = float(sub.get('marks', 0))
        grade = calculate_grade(mark_val)
        status = 'PASS' if mark_val >= 40 else 'FAIL'
        remark = calculate_remark(mark_val)

        grade_dist[grade] += 1
        if mark_val >= 70:
            strong_subjects.append(name)
        else:
            weak_subjects.append(name)

        processed_subjects.append({
            'name': name,
            'marks': int(mark_val) if mark_val.is_integer() else round(mark_val, 2),
            'grade': grade,
            'status': status,
            'remark': remark
        })

    num_subjects = len(processed_subjects)
    total_marks = sum(s['marks'] for s in processed_subjects)
    max_marks = num_subjects * 100
    percentage = (total_marks / max_marks * 100) if max_marks > 0 else 0
    overall_grade = calculate_grade(percentage)
    
    passed_count = sum(1 for s in processed_subjects if s['status'] == 'PASS')
    failed_count = sum(1 for s in processed_subjects if s['status'] == 'FAIL')
    overall_status = 'PASS' if failed_count == 0 else 'FAIL'
    
    pass_percentage = (passed_count / num_subjects * 100) if num_subjects > 0 else 0
    avg_marks = (total_marks / num_subjects) if num_subjects > 0 else 0

    # Highest and lowest scoring subjects (supporting ties)
    if processed_subjects:
        max_score = max(s['marks'] for s in processed_subjects)
        min_score = min(s['marks'] for s in processed_subjects)
        highest_subjects = [s for s in processed_subjects if s['marks'] == max_score]
        lowest_subjects = [s for s in processed_subjects if s['marks'] == min_score]
    else:
        highest_subjects = []
        lowest_subjects = []

    # Fail-safe result message
    if failed_count > 0:
        fail_safe_msg = f"You need to improve in {failed_count} subject{'s' if failed_count > 1 else ''} before achieving an overall pass."
    else:
        fail_safe_msg = "All subjects passed. Great job!"

    # Clean percentage formatting
    pct_formatted = f"{int(percentage)}%" if percentage.is_integer() else (f"{percentage:.1f}%" if f"{percentage:.2f}".endswith('0') else f"{percentage:.2f}%")

    return {
        'id': student_info.get('id'),
        'student_name': student_info.get('name', ''),
        'roll_number': student_info.get('roll_number', ''),
        'course': student_info.get('course', ''),
        'semester': student_info.get('semester', ''),
        'academic_year': student_info.get('academic_year', ''),
        'subjects': processed_subjects,
        'total_subjects': num_subjects,
        'total': int(total_marks) if isinstance(total_marks, float) and total_marks.is_integer() else round(total_marks, 2),
        'max_marks': max_marks,
        'percentage': round(percentage, 2),
        'percentage_formatted': pct_formatted,
        'grade': overall_grade,
        'status': overall_status,
        'average_marks': round(avg_marks, 2),
        'passed_count': passed_count,
        'failed_count': failed_count,
        'pass_percentage': round(pass_percentage, 2),
        'highest_subjects': highest_subjects,
        'lowest_subjects': lowest_subjects,
        'grade_distribution': grade_dist,
        'performance_category': calculate_performance_category(percentage),
        'performance_message': calculate_performance_message(percentage),
        'strong_subjects': strong_subjects,
        'weak_subjects': weak_subjects,
        'fail_safe_message': fail_safe_msg
    }

def fetch_all_students_analyzed():
    """Fetches all students from the SQLite database with full analysis."""
    conn = get_db_connection()
    students_rows = conn.execute('SELECT * FROM students ORDER BY id DESC').fetchall()
    results = []
    for s_row in students_rows:
        sub_rows = conn.execute('SELECT subject_name, marks FROM subjects WHERE student_id = ?', (s_row['id'],)).fetchall()
        analysis = analyze_student_data(dict(s_row), [dict(r) for r in sub_rows])
        results.append(analysis)
    conn.close()
    return results

def fetch_single_student_analyzed(student_id):
    """Fetches one student by ID with full analysis."""
    conn = get_db_connection()
    s_row = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not s_row:
        conn.close()
        return None
    sub_rows = conn.execute('SELECT subject_name, marks FROM subjects WHERE student_id = ?', (student_id,)).fetchall()
    conn.close()
    return analyze_student_data(dict(s_row), [dict(r) for r in sub_rows])

# -------------------------------------------------------------
# Authentication Routes (Login, Register, Setup Admin, Logout)
# -------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        elif role == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            error = "Invalid username or password."
        else:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                # Valid login: set session
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['name'] = user['name'] or user['username']
                session['student_id'] = user['student_id']
                session['assigned_course'] = user['assigned_course']

                if user['role'] == 'ADMIN':
                    return redirect(url_for('admin_dashboard'))
                elif user['role'] == 'TEACHER':
                    return redirect(url_for('teacher_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            else:
                error = "Invalid username or password."

    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Allows students to self-register their account."""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        elif role == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    error = None
    student_form = {
        'name': '',
        'roll_number': '',
        'course': '',
        'semester': '',
        'academic_year': '',
        'username': ''
    }

    if request.method == 'POST':
        student_form['name'] = request.form.get('name', '').strip()
        student_form['roll_number'] = request.form.get('roll_number', '').strip()
        student_form['course'] = request.form.get('course', '').strip()
        student_form['semester'] = request.form.get('semester', '').strip()
        student_form['academic_year'] = request.form.get('academic_year', '').strip()
        student_form['username'] = request.form.get('username', '').strip() or student_form['roll_number']
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not student_form['name'] or not student_form['roll_number'] or not student_form['course'] or not student_form['semester'] or not student_form['academic_year'] or not password:
            error = "All fields marked with * are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters long."
        else:
            conn = get_db_connection()
            existing_user = conn.execute('SELECT 1 FROM users WHERE username = ?', (student_form['username'],)).fetchone()
            existing_student = conn.execute('SELECT 1 FROM students WHERE roll_number = ?', (student_form['roll_number'],)).fetchone()

            if existing_user:
                error = f"Username '{student_form['username']}' is already registered."
                conn.close()
            elif existing_student:
                error = f"Roll Number '{student_form['roll_number']}' already exists in student records."
                conn.close()
            else:
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO students (name, roll_number, course, semester, academic_year)
                    VALUES (?, ?, ?, ?, ?)
                ''', (student_form['name'], student_form['roll_number'], student_form['course'], student_form['semester'], student_form['academic_year']))
                student_id = cur.lastrowid

                # Initialize default subjects for grading
                default_subs = ['Python', 'Mathematics', 'DBMS']
                for sub_name in default_subs:
                    cur.execute('''
                        INSERT INTO subjects (student_id, subject_name, marks)
                        VALUES (?, ?, 0)
                    ''', (student_id, sub_name))

                student_hash = generate_password_hash(password)
                cur.execute('''
                    INSERT INTO users (username, password_hash, role, name, student_id, assigned_course)
                    VALUES (?, ?, 'STUDENT', ?, ?, NULL)
                ''', (student_form['username'], student_hash, student_form['name'], student_id))
                conn.commit()
                conn.close()

                flash("Student account created successfully! Please log in.", "success")
                return redirect(url_for('login'))

    return render_template('register.html', error=error, student=student_form)

@app.route('/setup-admin', methods=['GET', 'POST'])
def setup_admin():
    """Initial Admin creation setup wizard. Accessible only when no admin exists."""
    conn = get_db_connection()
    admin_exists = conn.execute("SELECT 1 FROM users WHERE role = 'ADMIN'").fetchone()
    conn.close()

    if admin_exists:
        flash("An admin account is already configured. Please log in.", "info")
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not password or not confirm_password:
            error = "All fields marked with * are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters long."
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            admin_hash = generate_password_hash(password)
            cur.execute('''
                INSERT INTO users (username, password_hash, role, name, student_id, assigned_course)
                VALUES (?, ?, 'ADMIN', ?, NULL, NULL)
            ''', (username, admin_hash, name or 'System Admin'))
            conn.commit()
            conn.close()
            flash("Admin account created successfully! Please log in.", "success")
            return redirect(url_for('login'))

    return render_template('setup_admin.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        elif role == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

# -------------------------------------------------------------
# Admin Routes
# -------------------------------------------------------------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    all_students = fetch_all_students_analyzed()
    total_students = len(all_students)

    if total_students > 0:
        class_avg = round(sum(s['percentage'] for s in all_students) / total_students, 2)
        highest_student = max(all_students, key=lambda s: s['percentage'])
        lowest_student = min(all_students, key=lambda s: s['percentage'])
        passed_students = sum(1 for s in all_students if s['status'] == 'PASS')
        failed_students = sum(1 for s in all_students if s['status'] == 'FAIL')
    else:
        class_avg = 0
        highest_student = None
        lowest_student = None
        passed_students = 0
        failed_students = 0

    conn = get_db_connection()
    total_teachers = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'TEACHER'").fetchone()['cnt']
    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        class_avg=class_avg,
        highest_student=highest_student,
        lowest_student=lowest_student,
        passed_students=passed_students,
        failed_students=failed_students,
        total_teachers=total_teachers
    )

@app.route('/admin/teachers', methods=['GET', 'POST'])
@admin_required
def admin_teachers():
    """Allows Admin to create and view Teacher accounts with assigned courses."""
    conn = get_db_connection()
    error = None

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        assigned_course = request.form.get('assigned_course', '').strip()

        if not name or not username or not password or not assigned_course:
            error = "All fields are required."
        elif len(password) < 4:
            error = "Password must be at least 4 characters long."
        else:
            existing_user = conn.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone()
            if existing_user:
                error = f"Username '{username}' is already in use."
            else:
                pwd_hash = generate_password_hash(password)
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO users (username, password_hash, role, name, student_id, assigned_course)
                    VALUES (?, ?, 'TEACHER', ?, NULL, ?)
                ''', (username, pwd_hash, name, assigned_course))
                conn.commit()
                flash(f"Teacher account for '{name}' created successfully!", "success")
                conn.close()
                return redirect(url_for('admin_teachers'))

    teachers = conn.execute("SELECT * FROM users WHERE role = 'TEACHER' ORDER BY id DESC").fetchall()
    courses = [r['course'] for r in conn.execute('SELECT DISTINCT course FROM students').fetchall() if r['course']]
    conn.close()
    return render_template('admin_teachers.html', teachers=teachers, courses=courses, error=error)

@app.route('/admin/student/add', methods=['GET', 'POST'])
@admin_required
def admin_student_add():
    result = None
    error = None

    subjects_input = [
        {'name': 'Python', 'marks': ''},
        {'name': 'Mathematics', 'marks': ''},
        {'name': 'DBMS', 'marks': ''}
    ]

    student_form = {
        'name': '',
        'roll_number': '',
        'course': '',
        'semester': '',
        'academic_year': ''
    }

    if request.method == 'POST':
        student_form['name'] = request.form.get('student_name', '').strip()
        student_form['roll_number'] = request.form.get('roll_number', '').strip()
        student_form['course'] = request.form.get('course', '').strip()
        student_form['semester'] = request.form.get('semester', '').strip()
        student_form['academic_year'] = request.form.get('academic_year', '').strip()

        names = request.form.getlist('subject_name')
        marks_raw = request.form.getlist('subject_marks')
        subjects_input = [{'name': n, 'marks': m} for n, m in zip(names, marks_raw)]

        if not student_form['name']:
            error = "Student name cannot be empty."
        elif not student_form['roll_number']:
            error = "Roll number cannot be empty."
        elif not student_form['course']:
            error = "Course/Class cannot be empty."
        elif not student_form['semester']:
            error = "Semester cannot be empty."
        elif not student_form['academic_year']:
            error = "Academic year cannot be empty."
        elif not names or len(names) == 0:
            error = "At least one subject is required."
        else:
            raw_subjects_to_save = []
            for n, m in zip(names, marks_raw):
                name_clean = n.strip()
                mark_clean = m.strip()

                if not name_clean:
                    error = "Subject name cannot be empty."
                    break
                if not mark_clean:
                    error = f"Please enter marks for '{name_clean}'."
                    break

                try:
                    mark_val = float(mark_clean)
                    if not (0 <= mark_val <= 100):
                        error = f"Marks for '{name_clean}' must be between 0 and 100."
                        break
                    raw_subjects_to_save.append({'name': name_clean, 'marks': mark_val})
                except ValueError:
                    error = f"Please enter valid numeric marks for '{name_clean}'."
                    break

            if not error:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO students (name, roll_number, course, semester, academic_year)
                    VALUES (?, ?, ?, ?, ?)
                ''', (student_form['name'], student_form['roll_number'], student_form['course'], student_form['semester'], student_form['academic_year']))
                student_id = cur.lastrowid

                for sub in raw_subjects_to_save:
                    cur.execute('''
                        INSERT INTO subjects (student_id, subject_name, marks)
                        VALUES (?, ?, ?)
                    ''', (student_id, sub['name'], sub['marks']))

                # Create student login account (username: roll_number, default password: student123)
                student_hash = generate_password_hash('student123')
                cur.execute('''
                    INSERT OR REPLACE INTO users (username, password_hash, role, name, student_id, assigned_course)
                    VALUES (?, ?, 'STUDENT', ?, ?, NULL)
                ''', (student_form['roll_number'], student_hash, student_form['name'], student_id))

                conn.commit()
                conn.close()

                student_info = {
                    'id': student_id,
                    'name': student_form['name'],
                    'roll_number': student_form['roll_number'],
                    'course': student_form['course'],
                    'semester': student_form['semester'],
                    'academic_year': student_form['academic_year']
                }
                result = analyze_student_data(student_info, raw_subjects_to_save)
                flash(f"Student '{student_form['name']}' saved successfully! Login account created (Username: {student_form['roll_number']}, Password: student123)", "success")

    return render_template('student_add.html', result=result, error=error, subjects=subjects_input, student=student_form)

@app.route('/admin/student/edit/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def admin_student_edit(student_id):
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for('student_list'))

    error = None
    if request.method == 'POST':
        name = request.form.get('student_name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        course = request.form.get('course', '').strip()
        semester = request.form.get('semester', '').strip()
        academic_year = request.form.get('academic_year', '').strip()

        names = request.form.getlist('subject_name')
        marks_raw = request.form.getlist('subject_marks')

        if not name or not roll_number or not course or not semester or not academic_year:
            error = "All student detail fields are required."
        elif not names or len(names) == 0:
            error = "At least one subject is required."
        else:
            raw_subjects = []
            for n, m in zip(names, marks_raw):
                name_clean = n.strip()
                mark_clean = m.strip()
                if not name_clean:
                    error = "Subject name cannot be empty."
                    break
                try:
                    mark_val = float(mark_clean)
                    if not (0 <= mark_val <= 100):
                        error = f"Marks for '{name_clean}' must be between 0 and 100."
                        break
                    raw_subjects.append({'name': name_clean, 'marks': mark_val})
                except ValueError:
                    error = f"Please enter valid numeric marks for '{name_clean}'."
                    break

            if not error:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('''
                    UPDATE students
                    SET name = ?, roll_number = ?, course = ?, semester = ?, academic_year = ?
                    WHERE id = ?
                ''', (name, roll_number, course, semester, academic_year, student_id))

                # Update username & name in users table
                cur.execute('''
                    UPDATE users
                    SET username = ?, name = ?
                    WHERE student_id = ?
                ''', (roll_number, name, student_id))

                # Replace subjects
                cur.execute('DELETE FROM subjects WHERE student_id = ?', (student_id,))
                for sub in raw_subjects:
                    cur.execute('''
                        INSERT INTO subjects (student_id, subject_name, marks)
                        VALUES (?, ?, ?)
                    ''', (student_id, sub['name'], sub['marks']))

                conn.commit()
                conn.close()

                flash("Student record updated successfully.", "success")
                return redirect(url_for('student_detail', student_id=student_id))

    return render_template('student_edit.html', student=student, error=error)

@app.route('/admin/student/delete/<int:student_id>', methods=['POST'])
@admin_required
def admin_student_delete(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM students WHERE id = ?', (student_id,))
    cur.execute('DELETE FROM users WHERE student_id = ?', (student_id,))
    cur.execute('DELETE FROM subjects WHERE student_id = ?', (student_id,))
    conn.commit()
    conn.close()

    flash("Student record deleted successfully.", "info")
    return redirect(url_for('student_list'))

@app.route('/students')
@admin_required
def student_list():
    all_students = fetch_all_students_analyzed()

    q = request.args.get('q', '').strip().lower()
    if q:
        all_students = [
            s for s in all_students
            if q in s['student_name'].lower() or q in str(s['roll_number']).lower()
        ]

    status_filter = request.args.get('status', '').strip().upper()
    if status_filter in ['PASS', 'FAIL']:
        all_students = [s for s in all_students if s['status'] == status_filter]

    grade_filter = request.args.get('grade', '').strip().upper()
    if grade_filter in ['A', 'B', 'C', 'D', 'F']:
        all_students = [s for s in all_students if s['grade'] == grade_filter]

    sort_by = request.args.get('sort_by', 'percentage_desc')
    if sort_by == 'percentage_desc':
        all_students.sort(key=lambda s: s['percentage'], reverse=True)
    elif sort_by == 'percentage_asc':
        all_students.sort(key=lambda s: s['percentage'])
    elif sort_by == 'name_asc':
        all_students.sort(key=lambda s: s['student_name'].lower())
    elif sort_by == 'name_desc':
        all_students.sort(key=lambda s: s['student_name'].lower(), reverse=True)

    return render_template(
        'students.html',
        students=all_students,
        q=q,
        status_filter=status_filter,
        grade_filter=grade_filter,
        sort_by=sort_by
    )

@app.route('/analytics')
@admin_required
def analytics():
    all_students = fetch_all_students_analyzed()
    total_students = len(all_students)

    if total_students > 0:
        class_avg = round(sum(s['percentage'] for s in all_students) / total_students, 2)
        highest_student = max(all_students, key=lambda s: s['percentage'])
        lowest_student = min(all_students, key=lambda s: s['percentage'])
        passed_students = sum(1 for s in all_students if s['status'] == 'PASS')
        failed_students = sum(1 for s in all_students if s['status'] == 'FAIL')
        class_pass_pct = round((passed_students / total_students) * 100, 2)
    else:
        class_avg = 0
        highest_student = None
        lowest_student = None
        passed_students = 0
        failed_students = 0
        class_pass_pct = 0

    grade_distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    for s in all_students:
        grade_distribution[s['grade']] += 1

    return render_template(
        'analytics.html',
        total_students=total_students,
        class_avg=class_avg,
        highest_student=highest_student,
        lowest_student=lowest_student,
        passed_students=passed_students,
        failed_students=failed_students,
        class_pass_pct=class_pass_pct,
        grade_distribution=grade_distribution,
        all_students=all_students
    )

@app.route('/export/csv')
@admin_required
def export_csv():
    all_students = fetch_all_students_analyzed()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Student ID', 'Student Name', 'Roll Number', 'Course', 'Semester', 'Academic Year',
        'Total Subjects', 'Total Marks', 'Max Marks', 'Percentage', 'Overall Grade',
        'Overall Status', 'Average Marks', 'Passed Subjects', 'Failed Subjects',
        'Pass Percentage', 'Strong Subjects', 'Needs Improvement Subjects', 'Subjects Breakdown'
    ])

    for s in all_students:
        subjects_str = "; ".join([f"{sub['name']}: {sub['marks']} ({sub['grade']}, {sub['status']})" for sub in s['subjects']])
        writer.writerow([
            s['id'],
            s['student_name'],
            s['roll_number'],
            s['course'],
            s['semester'],
            s['academic_year'],
            s['total_subjects'],
            s['total'],
            s['max_marks'],
            s['percentage_formatted'],
            s['grade'],
            s['status'],
            s['average_marks'],
            s['passed_count'],
            s['failed_count'],
            f"{s['pass_percentage']}%",
            ", ".join(s['strong_subjects']),
            ", ".join(s['weak_subjects']),
            subjects_str
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=all_student_results.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# -------------------------------------------------------------
# Teacher Routes
# -------------------------------------------------------------
@app.route('/teacher/dashboard')
@teacher_required
def teacher_dashboard():
    """Teacher Dashboard: view assigned students and analytics."""
    assigned_course = session.get('assigned_course', '')
    all_students = fetch_all_students_analyzed()

    if assigned_course and assigned_course.upper() != 'ALL':
        assigned_students = [s for s in all_students if s['course'].strip().lower() == assigned_course.strip().lower()]
    else:
        assigned_students = all_students

    total_students = len(assigned_students)
    if total_students > 0:
        class_avg = round(sum(s['percentage'] for s in assigned_students) / total_students, 2)
        highest_student = max(assigned_students, key=lambda s: s['percentage'])
        lowest_student = min(assigned_students, key=lambda s: s['percentage'])
        passed_students = sum(1 for s in assigned_students if s['status'] == 'PASS')
        failed_students = sum(1 for s in assigned_students if s['status'] == 'FAIL')
        pass_pct = round((passed_students / total_students) * 100, 2)
    else:
        class_avg = 0
        highest_student = None
        lowest_student = None
        passed_students = 0
        failed_students = 0
        pass_pct = 0

    return render_template(
        'teacher_dashboard.html',
        assigned_course=assigned_course,
        students=assigned_students,
        total_students=total_students,
        class_avg=class_avg,
        highest_student=highest_student,
        lowest_student=lowest_student,
        passed_students=passed_students,
        failed_students=failed_students,
        pass_pct=pass_pct
    )

@app.route('/teacher/student/marks/<int:student_id>', methods=['GET', 'POST'])
@teacher_required
def teacher_update_marks(student_id):
    """Allows teachers to add, remove, and update marks for assigned students."""
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for('teacher_dashboard'))

    # Verify student is in teacher's assigned course
    assigned_course = session.get('assigned_course', '')
    if assigned_course and assigned_course.upper() != 'ALL' and student['course'].strip().lower() != assigned_course.strip().lower():
        flash("Access denied. You do not have permission to manage this student.", "danger")
        return redirect(url_for('teacher_dashboard'))

    error = None
    if request.method == 'POST':
        names = request.form.getlist('subject_name')
        marks_raw = request.form.getlist('subject_marks')

        if not names or len(names) == 0:
            error = "At least one subject is required."
        else:
            raw_subjects = []
            for n, m in zip(names, marks_raw):
                name_clean = n.strip()
                mark_clean = m.strip()
                if not name_clean:
                    error = "Subject name cannot be empty."
                    break
                try:
                    mark_val = float(mark_clean)
                    if not (0 <= mark_val <= 100):
                        error = f"Marks for '{name_clean}' must be between 0 and 100."
                        break
                    raw_subjects.append({'name': name_clean, 'marks': mark_val})
                except ValueError:
                    error = f"Please enter valid numeric marks for '{name_clean}'."
                    break

            if not error:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('DELETE FROM subjects WHERE student_id = ?', (student_id,))
                for sub in raw_subjects:
                    cur.execute('''
                        INSERT INTO subjects (student_id, subject_name, marks)
                        VALUES (?, ?, ?)
                    ''', (student_id, sub['name'], sub['marks']))
                conn.commit()
                conn.close()

                flash(f"Marks successfully updated for {student['student_name']}.", "success")
                return redirect(url_for('teacher_dashboard'))

    return render_template('teacher_update_marks.html', student=student, error=error)

# -------------------------------------------------------------
# Student Role Routes
# -------------------------------------------------------------
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'STUDENT':
        if session.get('role') == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('teacher_dashboard'))

    student_id = session.get('student_id')
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for('logout'))

    return render_template('student_dashboard.html', student=student)

@app.route('/student/my-result')
@login_required
def student_my_result():
    if session.get('role') != 'STUDENT':
        if session.get('role') == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('teacher_dashboard'))

    student_id = session.get('student_id')
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for('logout'))

    return render_template('student_my_result.html', student=student)

@app.route('/student/my-performance')
@login_required
def student_my_performance():
    if session.get('role') != 'STUDENT':
        if session.get('role') == 'ADMIN':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('teacher_dashboard'))

    student_id = session.get('student_id')
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for('logout'))

    return render_template('student_my_performance.html', student=student)

@app.route('/student/my-export/csv')
@login_required
def student_export_csv():
    if session.get('role') != 'STUDENT':
        return redirect(url_for('export_csv'))

    student_id = session.get('student_id')
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for('student_dashboard'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Subject Name', 'Marks', 'Grade', 'Status', 'Remark'])
    for sub in student['subjects']:
        writer.writerow([sub['name'], sub['marks'], sub['grade'], sub['status'], sub['remark']])
    writer.writerow([])
    writer.writerow(['Total Marks', f"{student['total']} / {student['max_marks']}"])
    writer.writerow(['Percentage', student['percentage_formatted']])
    writer.writerow(['Overall Grade', student['grade']])
    writer.writerow(['Overall Status', student['status']])
    writer.writerow(['Average Marks', f"{student['average_marks']} / 100"])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=my_result_{student['roll_number']}.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# -------------------------------------------------------------
# Protected Shared Detail & PDF Routes (with RBAC enforcement)
# -------------------------------------------------------------
@app.route('/student/<int:student_id>')
@login_required
def student_detail(student_id):
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student not found.", "danger")
        if session.get('role') == 'ADMIN':
            return redirect(url_for('student_list'))
        elif session.get('role') == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_dashboard'))

    # Strict Authorization check
    if not check_student_access(student_id, student['course']):
        flash("Access denied. You do not have permission to access this page.", "danger")
        if session.get('role') == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_dashboard'))

    return render_template('student_detail.html', student=student)

@app.route('/export/pdf/<int:student_id>')
@login_required
def export_pdf(student_id):
    student = fetch_single_student_analyzed(student_id)
    if not student:
        flash("Student not found.", "danger")
        if session.get('role') == 'ADMIN':
            return redirect(url_for('student_list'))
        elif session.get('role') == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_dashboard'))

    # Strict Authorization check
    if not check_student_access(student_id, student['course']):
        flash("Access denied. You do not have permission to access this page.", "danger")
        if session.get('role') == 'TEACHER':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_dashboard'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, alignment=1, spaceAfter=14, textColor=colors.HexColor("#2c3e50"))
    sub_title = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, alignment=1, spaceAfter=20, textColor=colors.HexColor("#7f8c8d"))
    section_title = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=14, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#2980b9"))
    normal_style = styles['Normal']

    # Header
    elements.append(Paragraph("Student Result Management System", title_style))
    elements.append(Paragraph(f"Official Grade Card & Performance Report", sub_title))
    elements.append(Spacer(1, 10))

    # Student Details Table
    details_data = [
        [Paragraph("<b>Student Name:</b>", normal_style), Paragraph(student['student_name'], normal_style),
         Paragraph("<b>Roll Number:</b>", normal_style), Paragraph(student['roll_number'], normal_style)],
        [Paragraph("<b>Course:</b>", normal_style), Paragraph(student['course'], normal_style),
         Paragraph("<b>Semester:</b>", normal_style), Paragraph(str(student['semester']), normal_style)],
        [Paragraph("<b>Academic Year:</b>", normal_style), Paragraph(student['academic_year'], normal_style),
         Paragraph("<b>Date:</b>", normal_style), Paragraph("2026-10-05", normal_style)]
    ]
    details_table = Table(details_data, colWidths=[110, 160, 110, 160])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#bdc3c7")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ecf0f1")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 15))

    # Subject Results Table
    elements.append(Paragraph("Subject-Wise Performance", section_title))
    table_data = [["Subject Name", "Marks", "Grade", "Status", "Remark"]]
    for sub in student['subjects']:
        table_data.append([
            sub['name'],
            str(sub['marks']),
            sub['grade'],
            sub['status'],
            sub['remark']
        ])
    
    sub_table = Table(table_data, colWidths=[180, 70, 70, 80, 140])
    sub_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#3498db")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (3,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#fdfefe")]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(sub_table)
    elements.append(Spacer(1, 15))

    # Result Summary & Analysis Table
    elements.append(Paragraph("Result Summary & Analytical Highlights", section_title))
    highest_str = ", ".join([f"{s['name']} ({s['marks']})" for s in student['highest_subjects']])
    lowest_str = ", ".join([f"{s['name']} ({s['marks']})" for s in student['lowest_subjects']])
    strong_str = ", ".join(student['strong_subjects']) if student['strong_subjects'] else "None"
    weak_str = ", ".join(student['weak_subjects']) if student['weak_subjects'] else "None"

    summary_data = [
        [Paragraph("<b>Total Marks:</b>", normal_style), Paragraph(f"{student['total']} / {student['max_marks']}", normal_style),
         Paragraph("<b>Percentage:</b>", normal_style), Paragraph(student['percentage_formatted'], normal_style)],
        [Paragraph("<b>Overall Grade:</b>", normal_style), Paragraph(student['grade'], normal_style),
         Paragraph("<b>Overall Status:</b>", normal_style), Paragraph(f"<b>{student['status']}</b>", normal_style)],
        [Paragraph("<b>Average Marks:</b>", normal_style), Paragraph(f"{student['average_marks']} / 100", normal_style),
         Paragraph("<b>Pass Percentage:</b>", normal_style), Paragraph(f"{student['pass_percentage']}%", normal_style)],
        [Paragraph("<b>Subjects Passed:</b>", normal_style), Paragraph(f"{student['passed_count']} / {student['total_subjects']}", normal_style),
         Paragraph("<b>Subjects Failed:</b>", normal_style), Paragraph(f"{student['failed_count']} / {student['total_subjects']}", normal_style)],
        [Paragraph("<b>Highest Scoring:</b>", normal_style), Paragraph(highest_str, normal_style),
         Paragraph("<b>Lowest Scoring:</b>", normal_style), Paragraph(lowest_str, normal_style)],
        [Paragraph("<b>Strong Subjects (>=70):</b>", normal_style), Paragraph(strong_str, normal_style),
         Paragraph("<b>Needs Improvement:</b>", normal_style), Paragraph(weak_str, normal_style)],
        [Paragraph("<b>Performance Category:</b>", normal_style), Paragraph(student['performance_category'], normal_style),
         Paragraph("<b>Performance Message:</b>", normal_style), Paragraph(student['performance_message'], normal_style)]
    ]
    summary_table = Table(summary_data, colWidths=[140, 130, 140, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#fcf3cf") if student['status'] == 'PASS' else colors.HexColor("#fadbd8")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#f39c12") if student['status'] == 'PASS' else colors.HexColor("#e74c3c")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#edbb99")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=result_{student['roll_number']}.pdf"
    response.headers["Content-type"] = "application/pdf"
    return response

if __name__ == '__main__':
    app.run(debug=True)
