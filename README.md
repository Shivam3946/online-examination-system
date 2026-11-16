# Online Examination System

A runnable Flask + SQLite demonstration project for an academic external viva.

## Requirements
- Python 3.9 or newer
- Internet connection for the first-time Flask installation

## Run on Windows
1. Extract this ZIP.
2. Open the extracted folder in File Explorer.
3. Double-click `run.bat` (or open CMD in this folder and run the commands below).
4. Open http://127.0.0.1:5000 in your browser.

Manual commands:
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

## Demo accounts
| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Teacher | teacher | teacher123 |
| Student | student | student123 |

Change demo passwords and SECRET_KEY before any real deployment. These credentials are for local demonstration only.

## Demonstration sequence
1. Sign in as `teacher` and create an exam; add questions.
2. Sign out and sign in as `student`; take the seeded Computer Fundamentals Quiz or the newly created exam.
3. Submit answers and show the automatically calculated score.
4. Sign in as `admin`; create user accounts, activate/deactivate exams and review recent attempts.

## Features
- Role-based Admin, Teacher and Student dashboards
- Password hashing with Werkzeug
- SQLite relational database with foreign keys
- Teacher exam and MCQ creation
- Student exam attempt and automatic scoring
- Result history and admin overview
- CSRF token validation for POST forms
- Parameterized SQL queries and Jinja auto-escaping

## Notes / limitations
- This is a local academic prototype, not a production proctoring platform.
- Exam timer is displayed as duration metadata; server-side timed auto-submit is not implemented.
- One attempt per student per exam is enforced by application logic; for a production deployment add a unique database constraint and transactional concurrency handling.
- No email/password reset, webcam proctoring, question randomization or cloud hosting.
- Run only on localhost for the demonstration. Do not expose the development server to the public internet.
