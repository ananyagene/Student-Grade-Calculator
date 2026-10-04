from flask import Flask, render_template, request

app = Flask(__name__)

# Function to determine the letter grade based on percentage
def calculate_grade(percentage):
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

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None

    # Default to 3 subjects for initial page load
    subjects = [
        {'name': 'Subject 1', 'marks': ''},
        {'name': 'Subject 2', 'marks': ''},
        {'name': 'Subject 3', 'marks': ''}
    ]

    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        
        # Get list of all submitted subject names and marks
        names = request.form.getlist('subject_name')
        marks_raw = request.form.getlist('subject_marks')

        # Keep user inputs to re-display them in the form
        subjects = [{'name': n, 'marks': m} for n, m in zip(names, marks_raw)]

        # Step 1: Validate student name
        if not student_name:
            error = "Student name is required."
        # Step 2: Validate that at least one subject row exists
        elif not names:
            error = "At least one subject is required."
        else:
            parsed_marks = []
            # Step 3: Validate each subject row
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
                    parsed_marks.append(mark_val)
                except ValueError:
                    error = f"Please enter valid numeric marks for '{name_clean}'."
                    break

            # Step 4: If all validations pass, calculate results
            if not error:
                num_subjects = len(parsed_marks)
                total = sum(parsed_marks)
                max_marks = num_subjects * 100
                percentage = (total / max_marks) * 100
                grade = calculate_grade(percentage)

                result = {
                    'student_name': student_name,
                    'total': int(total) if total.is_integer() else round(total, 2),
                    'max_marks': max_marks,
                    'percentage': f"{percentage:.2f}%",
                    'grade': grade
                }

    return render_template('index.html', result=result, error=error, subjects=subjects)

if __name__ == '__main__':
    # Run the Flask development server
    app.run(debug=True)
