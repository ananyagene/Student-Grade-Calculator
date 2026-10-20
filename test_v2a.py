"""
Automated Integration and Role Security Tests for Version 2A
Student Result Management System
"""

import unittest
from werkzeug.security import generate_password_hash
from app import app, get_db_connection, init_db

class TestVersion2A(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        init_db()

        # Clean up any leftover test data
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE username IN ('prof_mathur', 'aarav301')")
        conn.execute("DELETE FROM students WHERE roll_number = 'MCA301'")
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        # Clean up test data after all tests run
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE username IN ('prof_mathur', 'aarav301')")
        conn.execute("DELETE FROM students WHERE roll_number = 'MCA301'")
        conn.commit()
        conn.close()

    def setUp(self):
        self.client = app.test_client()

    def _ensure_test_teacher(self):
        """Helper to ensure teacher prof_mathur exists."""
        conn = get_db_connection()
        t = conn.execute("SELECT * FROM users WHERE username = 'prof_mathur'").fetchone()
        if not t:
            pw_hash = generate_password_hash('teachpass123')
            conn.execute("""
                INSERT INTO users (username, password_hash, role, name, assigned_course)
                VALUES ('prof_mathur', ?, 'TEACHER', 'Prof. Mathur', 'MCA AI')
            """, (pw_hash,))
            conn.commit()
        conn.close()

    def _ensure_test_student(self):
        """Helper to ensure student aarav301 exists."""
        conn = get_db_connection()
        s = conn.execute("SELECT * FROM students WHERE roll_number = 'MCA301'").fetchone()
        if not s:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO students (name, roll_number, course, semester, academic_year)
                VALUES ('Aarav Sharma', 'MCA301', 'MCA AI', '1', '2026-2027')
            """)
            sid = cur.lastrowid
            cur.execute("INSERT INTO subjects (student_id, subject_name, marks) VALUES (?, 'Python', 85)", (sid,))
            cur.execute("INSERT INTO subjects (student_id, subject_name, marks) VALUES (?, 'Mathematics', 90)", (sid,))
            cur.execute("INSERT INTO subjects (student_id, subject_name, marks) VALUES (?, 'DBMS', 78)", (sid,))

            pw_hash = generate_password_hash('aaravpass')
            cur.execute("""
                INSERT INTO users (username, password_hash, role, name, student_id)
                VALUES ('aarav301', ?, 'STUDENT', 'Aarav Sharma', ?)
            """, (pw_hash, sid))
            conn.commit()
        conn.close()

    def test_01_default_admin_seeded(self):
        """Verify that default admin account exists in database."""
        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        conn.close()
        self.assertIsNotNone(admin, "Default admin user 'admin' must exist")
        self.assertEqual(admin['role'], 'ADMIN')

    def test_02_admin_login_and_dashboard(self):
        """Test admin login with correct and wrong credentials."""
        # 1. Invalid login
        res = self.client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'}, follow_redirects=True)
        self.assertIn(b'Invalid username or password', res.data)

        # 2. Valid admin login
        res = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertIn(b'Admin Dashboard', res.data)
        self.assertIn(b'Administrative Controls', res.data)

        # 3. Check session
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('role'), 'ADMIN')
            self.assertEqual(sess.get('username'), 'admin')

        # 4. Logout
        res = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'logged out successfully', res.data)

    def test_03_admin_creates_teacher(self):
        """Admin creates a teacher assigned to MCA AI course."""
        # Login as admin
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Remove existing prof_mathur if present before create
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE username = 'prof_mathur'")
        conn.commit()
        conn.close()

        # Create teacher
        teacher_data = {
            'name': 'Prof. Mathur',
            'username': 'prof_mathur',
            'password': 'teachpass123',
            'assigned_course': 'MCA AI'
        }
        res = self.client.post('/admin/teachers', data=teacher_data, follow_redirects=True)
        self.assertIn(b'created successfully', res.data)

        # Verify in database
        conn = get_db_connection()
        teacher = conn.execute("SELECT * FROM users WHERE username = 'prof_mathur'").fetchone()
        conn.close()
        self.assertIsNotNone(teacher)
        self.assertEqual(teacher['role'], 'TEACHER')
        self.assertEqual(teacher['assigned_course'], 'MCA AI')

        # Logout admin
        self.client.get('/logout')

    def test_04_student_self_registration(self):
        """Student registers new account and then logs in."""
        # Ensure student does not exist before registration
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE username = 'aarav301'")
        conn.execute("DELETE FROM students WHERE roll_number = 'MCA301'")
        conn.commit()
        conn.close()

        reg_data = {
            'name': 'Aarav Sharma',
            'roll_number': 'MCA301',
            'course': 'MCA AI',
            'semester': '1',
            'academic_year': '2026-2027',
            'username': 'aarav301',
            'password': 'aaravpass',
            'confirm_password': 'aaravpass'
        }
        res = self.client.post('/register', data=reg_data, follow_redirects=True)
        self.assertIn(b'Student account created successfully! Please log in.', res.data)

        # Log in as the newly registered student
        res = self.client.post('/login', data={'username': 'aarav301', 'password': 'aaravpass'}, follow_redirects=True)
        self.assertIn(b'Welcome, Aarav Sharma!', res.data)

        # Verify session is STUDENT
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('role'), 'STUDENT')
            self.assertEqual(sess.get('username'), 'aarav301')
            self.assertIsNotNone(sess.get('student_id'))

        # Logout
        self.client.get('/logout')

    def test_05_student_permissions_and_role_isolation(self):
        """Verify student cannot access admin or teacher routes or other students' data."""
        self._ensure_test_student()

        # Login as student
        res = self.client.post('/login', data={'username': 'aarav301', 'password': 'aaravpass'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 1. Allowed routes
        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Aarav Sharma', res.data)

        res = self.client.get('/student/my-result')
        self.assertEqual(res.status_code, 200)

        res = self.client.get('/student/my-performance')
        self.assertEqual(res.status_code, 200)

        # 2. Blocked routes: Admin Dashboard
        res = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # 3. Blocked routes: Teacher Dashboard
        res = self.client.get('/teacher/dashboard', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # 4. Blocked routes: Teacher mark editing
        res = self.client.get('/teacher/student/marks/1', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # 5. Blocked routes: All students list
        res = self.client.get('/students', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        self.client.get('/logout')

    def test_06_teacher_dashboard_and_marks_update(self):
        """Teacher logs in, sees assigned students, and updates marks."""
        self._ensure_test_teacher()
        self._ensure_test_student()

        # Login as teacher prof_mathur (assigned to MCA AI)
        res = self.client.post('/login', data={'username': 'prof_mathur', 'password': 'teachpass123'}, follow_redirects=True)
        self.assertIn(b'Teacher Dashboard', res.data)
        self.assertIn(b'MCA AI', res.data)
        self.assertIn(b'Aarav Sharma', res.data)

        # Teacher cannot access Admin Teachers page
        res = self.client.get('/admin/teachers', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # Find student ID for Aarav Sharma
        conn = get_db_connection()
        s = conn.execute("SELECT id FROM students WHERE roll_number = 'MCA301'").fetchone()
        conn.close()
        student_id = s['id']

        # Update Aarav's marks
        update_data = {
            'subject_name': ['Machine Learning', 'Data Structures', 'Cloud Computing'],
            'subject_marks': ['95', '98', '92']
        }
        res = self.client.post(f'/teacher/student/marks/{student_id}', data=update_data, follow_redirects=True)
        self.assertIn(b'Marks successfully updated', res.data)

        # Verify updated marks in student detail view
        res = self.client.get(f'/student/{student_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'95', res.data)
        self.assertIn(b'98', res.data)
        self.assertIn(b'92', res.data)
        self.assertIn(b'95%', res.data)

        self.client.get('/logout')

    def test_07_pdf_and_csv_exports(self):
        """Test CSV and PDF exports for authenticated roles."""
        self._ensure_test_student()

        # 1. Admin CSV export
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        res = self.client.get('/export/csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res.headers.get('Content-Type'))
        self.assertIn(b'MCA301', res.data)
        self.client.get('/logout')

        # 2. Student CSV export
        self.client.post('/login', data={'username': 'aarav301', 'password': 'aaravpass'}, follow_redirects=True)
        res = self.client.get('/student/my-export/csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res.headers.get('Content-Type'))
        self.assertIn(b'Subject Name', res.data)
        self.assertIn(b'Total Marks', res.data)

        # 3. Student PDF export
        conn = get_db_connection()
        s = conn.execute("SELECT id FROM students WHERE roll_number = 'MCA301'").fetchone()
        conn.close()
        res = self.client.get(f'/export/pdf/{s["id"]}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Type'), 'application/pdf')
        self.assertTrue(len(res.data) > 500)
        self.client.get('/logout')

    def test_08_setup_wizard_protection(self):
        """Verify that /setup-admin redirects to login if an admin already exists."""
        res = self.client.get('/setup-admin', follow_redirects=True)
        self.assertIn(b'An admin account is already configured', res.data)

if __name__ == '__main__':
    unittest.main()
