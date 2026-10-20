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
    """Initializes tables for students, subjects, users, courses, semesters, and course_subjects."""
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

    # Subjects table (student marks per subject)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            marks REAL NOT NULL,
            subject_code TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # Migration check: Ensure column 'subject_code' exists on 'subjects'
    cursor.execute('PRAGMA table_info(subjects)')
    sub_cols = [col['name'] for col in cursor.fetchall()]
    if 'subject_code' not in sub_cols:
        cursor.execute('ALTER TABLE subjects ADD COLUMN subject_code TEXT')

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

    # Courses table (Version 2B)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT UNIQUE NOT NULL,
            course_name TEXT NOT NULL,
            total_semesters INTEGER DEFAULT 4,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Semesters table (Version 2B)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS semesters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            semester_number INTEGER NOT NULL,
            semester_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            UNIQUE(course_id, semester_number)
        )
    ''')

    # Course Subjects / Curriculum table (Version 2B)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS course_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            semester INTEGER NOT NULL,
            teacher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL,
            UNIQUE(course_id, semester, subject_code)
        )
    ''')

    # Seed Default Courses if table is empty
    course_count = cursor.execute('SELECT COUNT(*) as cnt FROM courses').fetchone()['cnt']
    if course_count == 0:
        default_courses = [
            ('MCA AI', 'Master of Computer Applications (Artificial Intelligence)', 4, 'Advanced MCA program specialized in AI and Data Science'),
            ('BCA', 'Bachelor of Computer Applications', 6, 'Undergraduate computer applications and software foundation'),
            ('MCA', 'Master of Computer Applications (General)', 4, 'Postgraduate core computer applications and engineering'),
            ('B.Tech', 'Bachelor of Technology (Computer Science)', 8, 'Four-year engineering degree in computer science')
        ]
        for c_code, c_name, c_sems, c_desc in default_courses:
            cursor.execute('''
                INSERT INTO courses (course_code, course_name, total_semesters, description)
                VALUES (?, ?, ?, ?)
            ''', (c_code, c_name, c_sems, c_desc))
            c_id = cursor.lastrowid
            # Seed semesters for this course
            for sem_num in range(1, c_sems + 1):
                cursor.execute('''
                    INSERT OR IGNORE INTO semesters (course_id, semester_number, semester_name)
                    VALUES (?, ?, ?)
                ''', (c_id, sem_num, f'Semester {sem_num}'))

    # Seed Default Curriculum Subjects if course_subjects is empty
    subj_count = cursor.execute('SELECT COUNT(*) as cnt FROM course_subjects').fetchone()['cnt']
    if subj_count == 0:
        # Fetch course IDs
        courses_dict = {r['course_code']: r['id'] for r in cursor.execute('SELECT id, course_code FROM courses').fetchall()}

        # Subjects for MCA AI Sem 1
        if 'MCA AI' in courses_dict:
            mca_ai_id = courses_dict['MCA AI']
            mca_ai_subs = [
                ('MCA101', 'Python', 1),
                ('MCA102', 'Mathematics', 1),
                ('MCA103', 'DBMS', 1),
                ('MCA104', 'OS', 1),
                ('MCA105', 'Networking', 1),
                ('MCA201', 'Machine Learning', 2),
                ('MCA202', 'Data Structures', 2),
                ('MCA203', 'Cloud Computing', 2)
            ]
            for s_code, s_name, s_sem in mca_ai_subs:
                cursor.execute('''
                    INSERT OR IGNORE INTO course_subjects (subject_code, subject_name, course_id, semester)
                    VALUES (?, ?, ?, ?)
                ''', (s_code, s_name, mca_ai_id, s_sem))

        # Subjects for BCA Sem 2
        if 'BCA' in courses_dict:
            bca_id = courses_dict['BCA']
            bca_subs = [
                ('BCA101', 'C Programming', 1),
                ('BCA102', 'Digital Electronics', 1),
                ('BCA201', 'Python', 2),
                ('BCA202', 'Mathematics', 2),
                ('BCA203', 'DBMS', 2)
            ]
            for s_code, s_name, s_sem in bca_subs:
                cursor.execute('''
                    INSERT OR IGNORE INTO course_subjects (subject_code, subject_name, course_id, semester)
                    VALUES (?, ?, ?, ?)
                ''', (s_code, s_name, bca_id, s_sem))

        # Subjects for MCA Sem 1
        if 'MCA' in courses_dict:
            mca_id = courses_dict['MCA']
            mca_subs = [
                ('MCA101', 'Physics', 1),
                ('MCA102', 'Chemistry', 1),
                ('MCA103', 'Biology', 1)
            ]
            for s_code, s_name, s_sem in mca_subs:
                cursor.execute('''
                    INSERT OR IGNORE INTO course_subjects (subject_code, subject_name, course_id, semester)
                    VALUES (?, ?, ?, ?)
                ''', (s_code, s_name, mca_id, s_sem))

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

    # Link teacher prof_mathur to MCA101 (Python) if both exist
    prof_mathur = cursor.execute("SELECT id FROM users WHERE username = 'prof_mathur'").fetchone()
    if prof_mathur:
        cursor.execute("UPDATE course_subjects SET teacher_id = ? WHERE subject_code = 'MCA101'", (prof_mathur['id'],))

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

def get_all_courses_with_stats():
    """Fetches all courses with enrolled student count, semester count, and subject count."""
    conn = get_db_connection()
    courses = [dict(c) for c in conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()]
    for c in courses:
        c_code = c['course_code'].strip()
        c['student_count'] = conn.execute('SELECT COUNT(*) as cnt FROM students WHERE LOWER(TRIM(course)) = LOWER(TRIM(?))', (c_code,)).fetchone()['cnt']
        c['subject_count'] = conn.execute('SELECT COUNT(*) as cnt FROM course_subjects WHERE course_id = ?', (c['id'],)).fetchone()['cnt']
        c['semester_count'] = conn.execute('SELECT COUNT(*) as cnt FROM semesters WHERE course_id = ?', (c['id'],)).fetchone()['cnt']
    conn.close()
    return courses

def get_course_details_with_semesters(course_id):
    """Fetches course details and its associated semesters."""
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        return None, []
    semesters = conn.execute('SELECT * FROM semesters WHERE course_id = ? ORDER BY semester_number ASC', (course_id,)).fetchall()
    conn.close()
    return dict(course), [dict(s) for s in semesters]

def get_student_academic_profile_data(student_id):
    """Fetches student profile along with enrolled curriculum subjects and assigned faculty."""
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not student:
        conn.close()
        return None
    student_dict = dict(student)

    # Match course from courses table
    course_row = conn.execute('SELECT * FROM courses WHERE LOWER(TRIM(course_code)) = LOWER(TRIM(?))', (student_dict['course'],)).fetchone()
    if course_row:
        student_dict['course_name'] = course_row['course_name']
        student_dict['total_semesters'] = course_row['total_semesters']
        course_id = course_row['id']
    else:
        student_dict['course_name'] = student_dict['course']
        student_dict['total_semesters'] = 4
        course_id = None

    # Fetch curriculum subjects for this course & semester
    enrolled_subjects = []
    if course_id:
        curr_rows = conn.execute('''
            SELECT cs.*, u.name as teacher_name, u.username as teacher_username
            FROM course_subjects cs
            LEFT JOIN users u ON cs.teacher_id = u.id
            WHERE cs.course_id = ? AND cs.semester = ?
            ORDER BY cs.subject_code ASC
        ''', (course_id, student_dict['semester'])).fetchall()

        # Fetch student marks for mapping
        mark_rows = conn.execute('SELECT subject_name, marks, subject_code FROM subjects WHERE student_id = ?', (student_id,)).fetchall()
        mark_map_by_code = {r['subject_code'].upper(): r['marks'] for r in mark_rows if r['subject_code']}
        mark_map_by_name = {r['subject_name'].strip().lower(): r['marks'] for r in mark_rows if r['subject_name']}

        for cr in curr_rows:
            c_dict = dict(cr)
            s_code = (c_dict['subject_code'] or '').strip().upper()
            s_name = (c_dict['subject_name'] or '').strip().lower()

            mark_val = None
            if s_code in mark_map_by_code:
                mark_val = mark_map_by_code[s_code]
            elif s_name in mark_map_by_name:
                mark_val = mark_map_by_name[s_name]

            if mark_val is not None:
                c_dict['marks'] = int(mark_val) if float(mark_val).is_integer() else round(float(mark_val), 2)
                c_dict['grade'] = calculate_grade(float(mark_val))
                c_dict['status'] = 'PASS' if float(mark_val) >= 40 else 'FAIL'
                c_dict['remark'] = calculate_remark(float(mark_val))
            else:
                c_dict['marks'] = None
                c_dict['grade'] = 'N/A'
                c_dict['status'] = 'Pending'
                c_dict['remark'] = 'Not Evaluated'

            enrolled_subjects.append(c_dict)

    # Fallback to existing student subjects if no curriculum subjects defined yet
    if not enrolled_subjects:
        existing_subs = conn.execute('SELECT * FROM subjects WHERE student_id = ?', (student_id,)).fetchall()
        for idx, es in enumerate(existing_subs, 1):
            mark_val = float(es['marks'])
            enrolled_subjects.append({
                'id': es['id'],
                'subject_code': es['subject_code'] or f'SUB{idx:02d}',
                'subject_name': es['subject_name'],
                'teacher_name': 'Assigned Faculty',
                'marks': int(mark_val) if mark_val.is_integer() else round(mark_val, 2),
                'grade': calculate_grade(mark_val),
                'status': 'PASS' if mark_val >= 40 else 'FAIL',
                'remark': calculate_remark(mark_val)
            })

    student_dict['enrolled_subjects'] = enrolled_subjects
    conn.close()
    return student_dict

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

                # Enroll student in curriculum subjects if defined for this course & semester
                curr_subs = conn.execute('''
                    SELECT cs.subject_name, cs.subject_code
                    FROM course_subjects cs
                    JOIN courses c ON cs.course_id = c.id
                    WHERE LOWER(TRIM(c.course_code)) = LOWER(TRIM(?)) AND cs.semester = ?
                ''', (student_form['course'], student_form['semester'])).fetchall()

                if curr_subs:
                    for sub in curr_subs:
                        cur.execute('''
                            INSERT INTO subjects (student_id, subject_name, marks, subject_code)
                            VALUES (?, ?, 0, ?)
                        ''', (student_id, sub['subject_name'], sub['subject_code']))
                else:
                    # Fallback default subjects for grading
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

    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()
    conn.close()
    return render_template('register.html', error=error, student=student_form, courses=courses)

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
    total_courses = conn.execute("SELECT COUNT(*) as cnt FROM courses").fetchone()['cnt']
    total_subjects = conn.execute("SELECT COUNT(*) as cnt FROM course_subjects").fetchone()['cnt']
    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        class_avg=class_avg,
        highest_student=highest_student,
        lowest_student=lowest_student,
        passed_students=passed_students,
        failed_students=failed_students,
        total_teachers=total_teachers,
        total_courses=total_courses,
        total_subjects=total_subjects
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
    courses = [r['course_code'] for r in conn.execute('SELECT course_code FROM courses ORDER BY course_code ASC').fetchall()]
    if not courses:
        courses = [r['course'] for r in conn.execute('SELECT DISTINCT course FROM students').fetchall() if r['course']]
    conn.close()
    return render_template('admin_teachers.html', teachers=teachers, courses=courses, error=error)

# -------------------------------------------------------------
# Version 2B: Academic Management Routes (Admin)
# -------------------------------------------------------------
@app.route('/admin/courses', methods=['GET', 'POST'])
@admin_required
def admin_courses():
    """Course Management: Add and view all academic courses."""
    conn = get_db_connection()
    error = None

    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        total_sems_raw = request.form.get('total_semesters', '4').strip()
        description = request.form.get('description', '').strip()

        if not course_code or not course_name:
            error = "Course Code and Course Name are required."
        else:
            try:
                total_sems = int(total_sems_raw)
                if not (1 <= total_sems <= 12):
                    error = "Total semesters must be between 1 and 12."
            except ValueError:
                error = "Total semesters must be a valid number."

            if not error:
                existing = conn.execute('SELECT 1 FROM courses WHERE UPPER(course_code) = ?', (course_code,)).fetchone()
                if existing:
                    error = f"Course code '{course_code}' already exists."
                else:
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO courses (course_code, course_name, total_semesters, description)
                        VALUES (?, ?, ?, ?)
                    ''', (course_code, course_name, total_sems, description))
                    course_id = cur.lastrowid
                    for s_num in range(1, total_sems + 1):
                        cur.execute('''
                            INSERT INTO semesters (course_id, semester_number, semester_name)
                            VALUES (?, ?, ?)
                        ''', (course_id, s_num, f'Semester {s_num}'))
                    conn.commit()
                    flash(f"Course '{course_code} - {course_name}' added successfully!", "success")
                    conn.close()
                    return redirect(url_for('admin_courses'))

    courses = get_all_courses_with_stats()
    conn.close()
    return render_template('admin_courses.html', courses=courses, error=error)

@app.route('/admin/course/edit/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def admin_course_edit(course_id):
    """Edit existing course details."""
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect(url_for('admin_courses'))

    error = None
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_name = request.form.get('course_name', '').strip()
        total_sems_raw = request.form.get('total_semesters', '4').strip()
        description = request.form.get('description', '').strip()

        if not course_code or not course_name:
            error = "Course Code and Course Name are required."
        else:
            try:
                total_sems = int(total_sems_raw)
                if not (1 <= total_sems <= 12):
                    error = "Total semesters must be between 1 and 12."
            except ValueError:
                error = "Total semesters must be a valid number."

            if not error:
                existing = conn.execute('SELECT 1 FROM courses WHERE UPPER(course_code) = ? AND id != ?', (course_code, course_id)).fetchone()
                if existing:
                    error = f"Course code '{course_code}' is already used by another course."
                else:
                    old_code = course['course_code']
                    cur = conn.cursor()
                    cur.execute('''
                        UPDATE courses
                        SET course_code = ?, course_name = ?, total_semesters = ?, description = ?
                        WHERE id = ?
                    ''', (course_code, course_name, total_sems, description, course_id))

                    if old_code != course_code:
                        cur.execute('UPDATE students SET course = ? WHERE course = ?', (course_code, old_code))
                        cur.execute('UPDATE users SET assigned_course = ? WHERE assigned_course = ?', (course_code, old_code))

                    current_sems = conn.execute('SELECT semester_number FROM semesters WHERE course_id = ?', (course_id,)).fetchall()
                    existing_nums = {r['semester_number'] for r in current_sems}
                    for s_num in range(1, total_sems + 1):
                        if s_num not in existing_nums:
                            cur.execute('''
                                INSERT INTO semesters (course_id, semester_number, semester_name)
                                VALUES (?, ?, ?)
                            ''', (course_id, s_num, f'Semester {s_num}'))

                    conn.commit()
                    flash(f"Course '{course_code}' updated successfully!", "success")
                    conn.close()
                    return redirect(url_for('admin_courses'))

    conn.close()
    return render_template('admin_course_edit.html', course=course, error=error)

@app.route('/admin/course/delete/<int:course_id>', methods=['POST'])
@admin_required
def admin_course_delete(course_id):
    """Safely delete course if no students are enrolled."""
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect(url_for('admin_courses'))

    enrolled = conn.execute('SELECT COUNT(*) as cnt FROM students WHERE LOWER(TRIM(course)) = LOWER(TRIM(?))', (course['course_code'],)).fetchone()['cnt']
    if enrolled > 0:
        conn.close()
        flash(f"Cannot delete course '{course['course_code']}' because {enrolled} student(s) are currently enrolled. Reassign or delete those students first.", "danger")
        return redirect(url_for('admin_courses'))

    cur = conn.cursor()
    cur.execute('DELETE FROM course_subjects WHERE course_id = ?', (course_id,))
    cur.execute('DELETE FROM semesters WHERE course_id = ?', (course_id,))
    cur.execute('DELETE FROM courses WHERE id = ?', (course_id,))
    conn.commit()
    conn.close()
    flash(f"Course '{course['course_code']}' and its curriculum deleted successfully.", "info")
    return redirect(url_for('admin_courses'))

@app.route('/admin/course/<int:course_id>/students')
@admin_required
def admin_course_students(course_id):
    """Display course-wise student list."""
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    conn.close()
    if not course:
        flash("Course not found.", "danger")
        return redirect(url_for('admin_courses'))

    all_students = fetch_all_students_analyzed()
    course_students = [s for s in all_students if s['course'].strip().lower() == course['course_code'].strip().lower()]
    return render_template('admin_course_students.html', course=course, students=course_students)

@app.route('/admin/semesters', methods=['GET', 'POST'])
@admin_required
def admin_semesters():
    """Semester Management: View and manage semesters per course."""
    conn = get_db_connection()
    error = None

    if request.method == 'POST':
        course_id_raw = request.form.get('course_id', '').strip()
        sem_num_raw = request.form.get('semester_number', '').strip()
        sem_name = request.form.get('semester_name', '').strip()

        if not course_id_raw or not sem_num_raw:
            error = "Course and Semester Number are required."
        else:
            try:
                course_id = int(course_id_raw)
                sem_num = int(sem_num_raw)
                if not (1 <= sem_num <= 12):
                    error = "Semester number must be between 1 and 12."
            except ValueError:
                error = "Invalid course or semester number."

            if not error:
                existing = conn.execute('SELECT 1 FROM semesters WHERE course_id = ? AND semester_number = ?', (course_id, sem_num)).fetchone()
                if existing:
                    error = f"Semester {sem_num} already exists for this course."
                else:
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO semesters (course_id, semester_number, semester_name)
                        VALUES (?, ?, ?)
                    ''', (course_id, sem_num, sem_name or f'Semester {sem_num}'))
                    conn.commit()
                    flash(f"Semester {sem_num} added successfully!", "success")
                    conn.close()
                    return redirect(url_for('admin_semesters'))

    courses = [dict(c) for c in conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()]
    all_students = fetch_all_students_analyzed()

    semester_rows = []
    sem_db_rows = conn.execute('''
        SELECT s.*, c.course_code, c.course_name
        FROM semesters s
        JOIN courses c ON s.course_id = c.id
        ORDER BY c.course_code ASC, s.semester_number ASC
    ''').fetchall()

    for s in sem_db_rows:
        s_dict = dict(s)
        c_code = s_dict['course_code'].strip().lower()
        s_num = str(s_dict['semester_number'])
        s_dict['student_count'] = sum(1 for st in all_students if st['course'].strip().lower() == c_code and str(st['semester']).strip() == s_num)
        s_dict['subject_count'] = conn.execute('SELECT COUNT(*) as cnt FROM course_subjects WHERE course_id = ? AND semester = ?', (s_dict['course_id'], s_dict['semester_number'])).fetchone()['cnt']
        semester_rows.append(s_dict)

    conn.close()
    return render_template('admin_semesters.html', courses=courses, semesters=semester_rows, error=error)

@app.route('/admin/subjects', methods=['GET', 'POST'])
@admin_required
def admin_subjects():
    """Subject Management: Add, view, and organize subjects semester-wise with duplicate prevention."""
    conn = get_db_connection()
    error = None

    if request.method == 'POST':
        subject_code = request.form.get('subject_code', '').strip().upper()
        subject_name = request.form.get('subject_name', '').strip()
        course_id_raw = request.form.get('course_id', '').strip()
        semester_raw = request.form.get('semester', '').strip()
        teacher_id_raw = request.form.get('teacher_id', '').strip()

        if not subject_code or not subject_name or not course_id_raw or not semester_raw:
            error = "Subject Code, Subject Name, Course, and Semester are all required."
        else:
            try:
                course_id = int(course_id_raw)
                semester = int(semester_raw)
                teacher_id = int(teacher_id_raw) if teacher_id_raw else None
            except ValueError:
                error = "Invalid course, semester, or teacher selected."

            if not error:
                # Prevent duplicate subject codes within the same course and semester!
                duplicate = conn.execute('''
                    SELECT 1 FROM course_subjects
                    WHERE course_id = ? AND semester = ? AND UPPER(subject_code) = ?
                ''', (course_id, semester, subject_code)).fetchone()

                if duplicate:
                    error = f"Duplicate subject code: Subject code '{subject_code}' already exists in Semester {semester} for this course."
                else:
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO course_subjects (subject_code, subject_name, course_id, semester, teacher_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (subject_code, subject_name, course_id, semester, teacher_id))
                    conn.commit()
                    flash(f"Subject '{subject_code} - {subject_name}' created successfully!", "success")
                    conn.close()
                    return redirect(url_for('admin_subjects'))

    subjects = conn.execute('''
        SELECT cs.*, c.course_code, c.course_name, u.name as teacher_name, u.username as teacher_username
        FROM course_subjects cs
        JOIN courses c ON cs.course_id = c.id
        LEFT JOIN users u ON cs.teacher_id = u.id
        ORDER BY c.course_code ASC, cs.semester ASC, cs.subject_code ASC
    ''').fetchall()

    courses = conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()
    teachers = conn.execute("SELECT * FROM users WHERE role = 'TEACHER' ORDER BY name ASC").fetchall()
    conn.close()

    return render_template('admin_subjects.html', subjects=subjects, courses=courses, teachers=teachers, error=error)

@app.route('/admin/subject/edit/<int:subject_id>', methods=['GET', 'POST'])
@admin_required
def admin_subject_edit(subject_id):
    """Edit curriculum subject details and teacher assignment."""
    conn = get_db_connection()
    subject = conn.execute('SELECT * FROM course_subjects WHERE id = ?', (subject_id,)).fetchone()
    if not subject:
        conn.close()
        flash("Subject not found.", "danger")
        return redirect(url_for('admin_subjects'))

    error = None
    if request.method == 'POST':
        subject_code = request.form.get('subject_code', '').strip().upper()
        subject_name = request.form.get('subject_name', '').strip()
        course_id_raw = request.form.get('course_id', '').strip()
        semester_raw = request.form.get('semester', '').strip()
        teacher_id_raw = request.form.get('teacher_id', '').strip()

        if not subject_code or not subject_name or not course_id_raw or not semester_raw:
            error = "Subject Code, Subject Name, Course, and Semester are required."
        else:
            try:
                course_id = int(course_id_raw)
                semester = int(semester_raw)
                teacher_id = int(teacher_id_raw) if teacher_id_raw else None
            except ValueError:
                error = "Invalid course, semester, or teacher."

            if not error:
                # Prevent duplicate subject codes within the same course and semester (excluding self)
                duplicate = conn.execute('''
                    SELECT 1 FROM course_subjects
                    WHERE course_id = ? AND semester = ? AND UPPER(subject_code) = ? AND id != ?
                ''', (course_id, semester, subject_code, subject_id)).fetchone()

                if duplicate:
                    error = f"Subject code '{subject_code}' already exists in Semester {semester} for this course."
                else:
                    cur = conn.cursor()
                    cur.execute('''
                        UPDATE course_subjects
                        SET subject_code = ?, subject_name = ?, course_id = ?, semester = ?, teacher_id = ?
                        WHERE id = ?
                    ''', (subject_code, subject_name, course_id, semester, teacher_id, subject_id))
                    conn.commit()
                    flash(f"Subject '{subject_code}' updated successfully!", "success")
                    conn.close()
                    return redirect(url_for('admin_subjects'))

    courses = conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()
    teachers = conn.execute("SELECT * FROM users WHERE role = 'TEACHER' ORDER BY name ASC").fetchall()
    conn.close()
    return render_template('admin_subject_edit.html', subject=subject, courses=courses, teachers=teachers, error=error)

@app.route('/admin/subject/delete/<int:subject_id>', methods=['POST'])
@admin_required
def admin_subject_delete(subject_id):
    """Delete a curriculum subject."""
    conn = get_db_connection()
    sub = conn.execute('SELECT * FROM course_subjects WHERE id = ?', (subject_id,)).fetchone()
    if sub:
        conn.execute('DELETE FROM course_subjects WHERE id = ?', (subject_id,))
        conn.commit()
        flash(f"Subject '{sub['subject_code']} - {sub['subject_name']}' deleted.", "info")
    conn.close()
    return redirect(url_for('admin_subjects'))

@app.route('/admin/assign-teachers', methods=['GET', 'POST'])
@admin_required
def admin_assign_teachers():
    """Assign teachers to specific subjects."""
    conn = get_db_connection()

    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        teacher_id_raw = request.form.get('teacher_id')
        teacher_id = int(teacher_id_raw) if teacher_id_raw else None

        cur = conn.cursor()
        cur.execute('UPDATE course_subjects SET teacher_id = ? WHERE id = ?', (teacher_id, subject_id))
        conn.commit()
        flash("Faculty assignment updated successfully!", "success")
        conn.close()
        return redirect(url_for('admin_assign_teachers'))

    subjects = conn.execute('''
        SELECT cs.*, c.course_code, c.course_name, u.name as teacher_name, u.username as teacher_username
        FROM course_subjects cs
        JOIN courses c ON cs.course_id = c.id
        LEFT JOIN users u ON cs.teacher_id = u.id
        ORDER BY c.course_code ASC, cs.semester ASC, cs.subject_code ASC
    ''').fetchall()

    teachers = conn.execute("SELECT * FROM users WHERE role = 'TEACHER' ORDER BY name ASC").fetchall()
    conn.close()
    return render_template('admin_assign_teachers.html', subjects=subjects, teachers=teachers)

@app.route('/admin/academic-view')
@admin_required
def admin_academic_view():
    """Filter students by Course and Semester."""
    course_filter = request.args.get('course', '').strip()
    semester_filter = request.args.get('semester', '').strip()

    all_students = fetch_all_students_analyzed()
    filtered = all_students

    if course_filter:
        filtered = [s for s in filtered if s['course'].strip().lower() == course_filter.lower()]
    if semester_filter:
        filtered = [s for s in filtered if str(s['semester']).strip() == semester_filter]

    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()
    conn.close()

    return render_template('admin_academic_view.html', students=filtered, courses=courses, selected_course=course_filter, selected_semester=semester_filter)

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

    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()
    conn.close()
    return render_template('student_add.html', result=result, error=error, subjects=subjects_input, student=student_form, courses=courses)

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

    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses ORDER BY course_code ASC').fetchall()
    conn.close()
    return render_template('student_edit.html', student=student, error=error, courses=courses)

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
    """Teacher Dashboard: view assigned subjects, students in each subject, and manage marks."""
    user_id = session.get('user_id')
    assigned_course = session.get('assigned_course', '')
    conn = get_db_connection()

    # Query subjects assigned specifically to this teacher
    assigned_subjects_rows = conn.execute('''
        SELECT cs.*, c.course_code, c.course_name
        FROM course_subjects cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.teacher_id = ?
        ORDER BY c.course_code ASC, cs.semester ASC, cs.subject_code ASC
    ''', (user_id,)).fetchall()

    assigned_subjects = [dict(r) for r in assigned_subjects_rows]

    # If teacher has assigned_course from Version 2A and no subject assignments yet, include course subjects
    if not assigned_subjects and assigned_course:
        if assigned_course.upper() == 'ALL':
            course_sub_rows = conn.execute('''
                SELECT cs.*, c.course_code, c.course_name
                FROM course_subjects cs
                JOIN courses c ON cs.course_id = c.id
                ORDER BY c.course_code ASC, cs.semester ASC, cs.subject_code ASC
            ''').fetchall()
        else:
            course_sub_rows = conn.execute('''
                SELECT cs.*, c.course_code, c.course_name
                FROM course_subjects cs
                JOIN courses c ON cs.course_id = c.id
                WHERE LOWER(TRIM(c.course_code)) = LOWER(TRIM(?))
                ORDER BY cs.semester ASC, cs.subject_code ASC
            ''', (assigned_course,)).fetchall()
        assigned_subjects = [dict(r) for r in course_sub_rows]

    # For each assigned subject, calculate enrolled student count and subject average mark
    for sub in assigned_subjects:
        c_code = sub['course_code'].strip().lower()
        s_num = str(sub['semester']).strip()
        sub['student_count'] = conn.execute(
            'SELECT COUNT(*) as cnt FROM students WHERE LOWER(TRIM(course)) = ? AND TRIM(semester) = ?',
            (c_code, s_num)
        ).fetchone()['cnt']

        avg_row = conn.execute('''
            SELECT AVG(sub.marks) as avg_mark
            FROM subjects sub
            JOIN students s ON sub.student_id = s.id
            WHERE LOWER(TRIM(s.course)) = ? AND TRIM(s.semester) = ?
              AND (sub.subject_code = ? OR LOWER(TRIM(sub.subject_name)) = LOWER(TRIM(?)))
        ''', (c_code, s_num, sub['subject_code'], sub['subject_name'])).fetchone()
        sub['avg_mark'] = round(avg_row['avg_mark'], 1) if (avg_row and avg_row['avg_mark'] is not None) else 'N/A'

    # Compute course-level assigned students for the teacher
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

    conn.close()

    return render_template(
        'teacher_dashboard.html',
        assigned_course=assigned_course,
        assigned_subjects=assigned_subjects,
        students=assigned_students,
        total_students=total_students,
        class_avg=class_avg,
        highest_student=highest_student,
        lowest_student=lowest_student,
        passed_students=passed_students,
        failed_students=failed_students,
        pass_pct=pass_pct
    )

@app.route('/teacher/subject/<int:subject_id>/marks', methods=['GET', 'POST'])
@teacher_required
def teacher_subject_marks(subject_id):
    """
    Teachers manage marks strictly for their assigned subjects.
    Displays all students enrolled in that subject's course & semester.
    """
    conn = get_db_connection()
    subject = conn.execute('''
        SELECT cs.*, c.course_code, c.course_name
        FROM course_subjects cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.id = ?
    ''', (subject_id,)).fetchone()

    if not subject:
        conn.close()
        flash("Subject not found.", "danger")
        return redirect(url_for('teacher_dashboard'))

    # Security check: verify this teacher is assigned to this subject (or is admin or has course match)
    user_id = session.get('user_id')
    assigned_course = session.get('assigned_course', '')
    is_assigned = (subject['teacher_id'] == user_id)
    if not is_assigned and assigned_course and assigned_course.upper() != 'ALL':
        is_assigned = (assigned_course.strip().lower() == subject['course_code'].strip().lower())
    if session.get('role') == 'ADMIN':
        is_assigned = True

    if not is_assigned:
        conn.close()
        flash("Access denied. You are only authorized to manage marks for your assigned subjects.", "danger")
        return redirect(url_for('teacher_dashboard'))

    error = None
    if request.method == 'POST':
        student_ids = request.form.getlist('student_id')
        marks_list = request.form.getlist('marks')

        cur = conn.cursor()
        updated_count = 0
        for sid_raw, m_raw in zip(student_ids, marks_list):
            m_str = m_raw.strip()
            if m_str != '':
                try:
                    mark_val = float(m_str)
                    if 0 <= mark_val <= 100:
                        sid = int(sid_raw)
                        existing = cur.execute('''
                            SELECT id FROM subjects
                            WHERE student_id = ? AND (subject_code = ? OR LOWER(TRIM(subject_name)) = LOWER(TRIM(?)))
                        ''', (sid, subject['subject_code'], subject['subject_name'])).fetchone()

                        if existing:
                            cur.execute('UPDATE subjects SET marks = ?, subject_code = ?, subject_name = ? WHERE id = ?',
                                        (mark_val, subject['subject_code'], subject['subject_name'], existing['id']))
                        else:
                            cur.execute('''
                                INSERT INTO subjects (student_id, subject_name, marks, subject_code)
                                VALUES (?, ?, ?, ?)
                            ''', (sid, subject['subject_name'], mark_val, subject['subject_code']))
                        updated_count += 1
                except ValueError:
                    pass

        conn.commit()
        flash(f"Marks for '{subject['subject_code']} - {subject['subject_name']}' updated successfully ({updated_count} student record(s) processed)!", "success")
        conn.close()
        return redirect(url_for('teacher_subject_marks', subject_id=subject_id))

    # Fetch students enrolled in this course & semester
    c_code = subject['course_code']
    sem_val = str(subject['semester'])

    student_rows = conn.execute('''
        SELECT s.*, sub.marks as current_marks
        FROM students s
        LEFT JOIN subjects sub ON sub.student_id = s.id AND (sub.subject_code = ? OR LOWER(TRIM(sub.subject_name)) = LOWER(TRIM(?)))
        WHERE LOWER(TRIM(s.course)) = LOWER(TRIM(?)) AND TRIM(s.semester) = ?
        ORDER BY s.roll_number ASC
    ''', (subject['subject_code'], subject['subject_name'], c_code, sem_val)).fetchall()

    conn.close()
    return render_template('teacher_subject_marks.html', subject=subject, students=student_rows, error=error)

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

    profile = get_student_academic_profile_data(student_id)
    return render_template('student_dashboard.html', student=student, profile=profile)

@app.route('/student/academic-profile')
@login_required
def student_academic_profile():
    """Student Academic Profile: display Name, Roll No, Course, Semester, Academic Year, and Enrolled Subjects."""
    if session.get('role') != 'STUDENT':
        flash("Academic profile is available for students.", "info")
        return redirect(url_for('index'))

    student_id = session.get('student_id')
    profile = get_student_academic_profile_data(student_id)
    if not profile:
        flash("Student profile not found.", "danger")
        return redirect(url_for('logout'))

    analyzed_student = fetch_single_student_analyzed(student_id)
    return render_template('student_academic_profile.html', profile=profile, student=analyzed_student)

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
