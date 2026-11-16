import os, sqlite3, secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "exam_system.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-demo-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','teacher','student'))
        );
        CREATE TABLE IF NOT EXISTS exams(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
          description TEXT, duration INTEGER NOT NULL DEFAULT 20,
          created_by INTEGER, active INTEGER NOT NULL DEFAULT 1,
          FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS questions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER NOT NULL,
          question TEXT NOT NULL, option_a TEXT NOT NULL, option_b TEXT NOT NULL,
          option_c TEXT NOT NULL, option_d TEXT NOT NULL, correct_option TEXT NOT NULL,
          FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS attempts(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          exam_id INTEGER NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL,
          submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(user_id) REFERENCES users(id),
          FOREIGN KEY(exam_id) REFERENCES exams(id)
        );
        """)
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            users=[
              ("System Admin","admin","admin123","admin"),
              ("Demo Teacher","teacher","teacher123","teacher"),
              ("Demo Student","student","student123","student")
            ]
            con.executemany("INSERT INTO users(name,username,password_hash,role) VALUES(?,?,?,?)",
              [(n,u,generate_password_hash(p),r) for n,u,p,r in users])
        if con.execute("SELECT COUNT(*) FROM exams").fetchone()[0] == 0:
            teacher_id=con.execute("SELECT id FROM users WHERE username='teacher'").fetchone()[0]
            cur=con.execute("INSERT INTO exams(title,description,duration,created_by) VALUES(?,?,?,?)",
              ("Computer Fundamentals Quiz","A short demonstration exam covering basic computer science.",15,teacher_id))
            eid=cur.lastrowid
            qs=[
             ("Which component is known as the brain of the computer?","RAM","CPU","Monitor","Keyboard","B"),
             ("Which language is primarily used to structure web pages?","HTML","Python","C","SQL","A"),
             ("Which of these is a database management system?","Linux","MySQL","Chrome","Git","B"),
             ("What does HTTP stand for?","High Transfer Text Protocol","HyperText Transfer Protocol","Hyper Tool Transfer Program","Host Text Transfer Process","B"),
             ("Which data structure follows FIFO?","Stack","Tree","Queue","Graph","C")
            ]
            con.executemany("""INSERT INTO questions(exam_id,question,option_a,option_b,option_c,option_d,correct_option)
                               VALUES(?,?,?,?,?,?,?)""",[(eid,*q) for q in qs])

def login_required(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args,**kwargs)
    return wrapped

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args,**kwargs):
            if session.get("role") not in roles:
                abort(403)
            return fn(*args,**kwargs)
        return wrapped
    return deco

@app.before_request
def csrf_guard():
    if request.method == "POST":
        token=session.get("_csrf")
        sent=request.form.get("_csrf")
        if not token or not sent or not secrets.compare_digest(token,sent):
            abort(400, "Invalid or missing CSRF token")

@app.context_processor
def inject_globals():
    if "_csrf" not in session:
        session["_csrf"]=secrets.token_urlsafe(24)
    return {"csrf_token":session["_csrf"]}

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        with db() as con:
            user=con.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session["user_id"]=user["id"]; session["name"]=user["name"]
            session["role"]=user["role"]; session["_csrf"]=secrets.token_urlsafe(24)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.","error")
    return render_template("login.html")

@app.route("/logout",methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        if session["role"]=="student":
            exams=con.execute("SELECT * FROM exams WHERE active=1 ORDER BY id DESC").fetchall()
            attempts=con.execute("""SELECT a.*,e.title FROM attempts a JOIN exams e ON e.id=a.exam_id
                                    WHERE a.user_id=? ORDER BY a.id DESC""",(session["user_id"],)).fetchall()
            return render_template("student_dashboard.html",exams=exams,attempts=attempts)
        if session["role"]=="teacher":
            exams=con.execute("""SELECT e.*,COUNT(q.id) qcount FROM exams e LEFT JOIN questions q ON q.exam_id=e.id
                                 WHERE e.created_by=? GROUP BY e.id ORDER BY e.id DESC""",(session["user_id"],)).fetchall()
            return render_template("teacher_dashboard.html",exams=exams)
        users=con.execute("SELECT id,name,username,role FROM users ORDER BY id").fetchall()
        exams=con.execute("SELECT * FROM exams ORDER BY id DESC").fetchall()
        attempts=con.execute("""SELECT a.*,u.name student,e.title FROM attempts a JOIN users u ON u.id=a.user_id
                                JOIN exams e ON e.id=a.exam_id ORDER BY a.id DESC LIMIT 20""").fetchall()
    return render_template("admin_dashboard.html",users=users,exams=exams,attempts=attempts)

@app.route("/exam/<int:exam_id>")
@role_required("student")
def take_exam(exam_id):
    with db() as con:
        exam=con.execute("SELECT * FROM exams WHERE id=? AND active=1",(exam_id,)).fetchone()
        if not exam: abort(404)
        questions=con.execute("SELECT id,question,option_a,option_b,option_c,option_d FROM questions WHERE exam_id=?",(exam_id,)).fetchall()
        previous=con.execute("SELECT id FROM attempts WHERE user_id=? AND exam_id=?",(session["user_id"],exam_id)).fetchone()
    if previous:
        flash("You have already submitted this exam. Re-attempts are disabled in this demo.","error")
        return redirect(url_for("dashboard"))
    return render_template("take_exam.html",exam=exam,questions=questions)

@app.route("/exam/<int:exam_id>/submit",methods=["POST"])
@role_required("student")
def submit_exam(exam_id):
    with db() as con:
        exam=con.execute("SELECT * FROM exams WHERE id=? AND active=1",(exam_id,)).fetchone()
        if not exam: abort(404)
        already=con.execute("SELECT id FROM attempts WHERE user_id=? AND exam_id=?",(session["user_id"],exam_id)).fetchone()
        if already:
            flash("An attempt for this exam already exists.","error")
            return redirect(url_for("dashboard"))
        questions=con.execute("SELECT id,correct_option FROM questions WHERE exam_id=?",(exam_id,)).fetchall()
        score=sum(1 for q in questions if request.form.get(str(q["id"]))==q["correct_option"])
        cur=con.execute("INSERT INTO attempts(user_id,exam_id,score,total) VALUES(?,?,?,?)",
                        (session["user_id"],exam_id,score,len(questions)))
        attempt_id=cur.lastrowid
    return redirect(url_for("result",attempt_id=attempt_id))

@app.route("/result/<int:attempt_id>")
@login_required
def result(attempt_id):
    with db() as con:
        a=con.execute("""SELECT a.*,e.title,u.name FROM attempts a JOIN exams e ON e.id=a.exam_id
                         JOIN users u ON u.id=a.user_id WHERE a.id=?""",(attempt_id,)).fetchone()
    if not a: abort(404)
    if session["role"]=="student" and a["user_id"]!=session["user_id"]: abort(403)
    return render_template("result.html",attempt=a)

@app.route("/teacher/exam/new",methods=["GET","POST"])
@role_required("teacher","admin")
def new_exam():
    if request.method=="POST":
        title=request.form.get("title","").strip()
        desc=request.form.get("description","").strip()
        try: duration=max(1,min(180,int(request.form.get("duration","20"))))
        except ValueError: duration=20
        if not title:
            flash("Exam title is required.","error")
        else:
            with db() as con:
                cur=con.execute("INSERT INTO exams(title,description,duration,created_by) VALUES(?,?,?,?)",
                                (title,desc,duration,session["user_id"]))
                exam_id=cur.lastrowid
            return redirect(url_for("add_questions",exam_id=exam_id))
    return render_template("new_exam.html")

@app.route("/teacher/exam/<int:exam_id>/questions",methods=["GET","POST"])
@role_required("teacher","admin")
def add_questions(exam_id):
    with db() as con:
        exam=con.execute("SELECT * FROM exams WHERE id=?",(exam_id,)).fetchone()
        if not exam: abort(404)
        if session["role"]=="teacher" and exam["created_by"]!=session["user_id"]: abort(403)
        if request.method=="POST":
            q=request.form.get("question","").strip()
            opts=[request.form.get(k,"").strip() for k in ["a","b","c","d"]]
            correct=request.form.get("correct","")
            if not q or not all(opts) or correct not in ["A","B","C","D"]:
                flash("Complete the question and all four options.","error")
            else:
                con.execute("""INSERT INTO questions(exam_id,question,option_a,option_b,option_c,option_d,correct_option)
                               VALUES(?,?,?,?,?,?,?)""",(exam_id,q,*opts,correct))
                flash("Question added successfully.","success")
        questions=con.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id",(exam_id,)).fetchall()
    return render_template("add_questions.html",exam=exam,questions=questions)

@app.route("/admin/user/new",methods=["POST"])
@role_required("admin")
def create_user():
    name=request.form.get("name","").strip(); username=request.form.get("username","").strip()
    password=request.form.get("password",""); role=request.form.get("role","student")
    if role not in ["student","teacher","admin"] or not name or not username or len(password)<6:
        flash("Enter valid details. Password must be at least 6 characters.","error")
    else:
        try:
            with db() as con:
                con.execute("INSERT INTO users(name,username,password_hash,role) VALUES(?,?,?,?)",
                            (name,username,generate_password_hash(password),role))
            flash("User created.","success")
        except sqlite3.IntegrityError:
            flash("Username already exists.","error")
    return redirect(url_for("dashboard"))

@app.route("/admin/exam/<int:exam_id>/toggle",methods=["POST"])
@role_required("admin")
def toggle_exam(exam_id):
    with db() as con:
        con.execute("UPDATE exams SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(exam_id,))
    return redirect(url_for("dashboard"))

@app.errorhandler(403)
def forbidden(e): return render_template("error.html",code=403,message="You do not have permission to access this page."),403
@app.errorhandler(404)
def not_found(e): return render_template("error.html",code=404,message="The requested page was not found."),404

if __name__=="__main__":
    init_db()
    app.run(debug=os.environ.get("FLASK_DEBUG")=="1",host="127.0.0.1",port=5000)
