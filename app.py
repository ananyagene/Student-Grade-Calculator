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

    if request.method == 'POST':
        # Retrieve form data submitted by user
        student_name = request.form.get('student_name', '').strip()
        sub1_str = request.form.get('subject1', '').strip()
        sub2_str = request.form.get('subject2', '').strip()
        sub3_str = request.form.get('subject3', '').strip()

        # Step 1: Check for empty fields
        if not student_name or not sub1_str or not sub2_str or not sub3_str:
            error = "All fields are required. Please fill in student name and all subject marks."
        else:
            try:
                # Step 2: Convert marks to numbers
                mark1 = float(sub1_str)
                mark2 = float(sub2_str)
                mark3 = float(sub3_str)

                # Step 3: Validate that marks are between 0 and 100
                if not (0 <= mark1 <= 100 and 0 <= mark2 <= 100 and 0 <= mark3 <= 100):
                    error = "Marks must be between 0 and 100 for all subjects."
                else:
                    # Step 4: Calculate total, percentage, and grade
                    total = mark1 + mark2 + mark3
                    percentage = (total / 300) * 100
                    grade = calculate_grade(percentage)

                    # Step 5: Store results in a dictionary to pass to the template
                    result = {
                        'student_name': student_name,
                        'total': int(total) if total.is_integer() else round(total, 2),
                        'percentage': f"{percentage:.2f}%",
                        'grade': grade
                    }
            except ValueError:
                # Runs if a user enters letters or symbols instead of numbers
                error = "Please enter valid numeric marks."

    return render_template('index.html', result=result, error=error)

if __name__ == '__main__':
    # Run the Flask development server
    app.run(debug=True)
