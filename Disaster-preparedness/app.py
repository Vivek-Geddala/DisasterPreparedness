from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = "mysecretkey"  # needed for session management

DB_NAME = "database.db"

# -----------------------------
# Initialize Database
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Students table
    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )''')

    # Admin table (only one admin for now)
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )''')

    # Insert default admin if not exists
    cursor.execute("SELECT * FROM admin WHERE email=?", ("admin@example.com",))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO admin (email, password) VALUES (?, ?)", ("admin@example.com", "admin123"))

    conn.commit()
    conn.close()

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("login.html")

# ---- Student Login ----
@app.route("/student_login", methods=["POST"])
def student_login():
    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE email=? AND password=?", (email, password))
    student = cursor.fetchone()
    conn.close()

    if student:
        session["student"] = student[1]  # store student name
        return redirect(url_for("student_dashboard"))
    else:
        flash("Invalid student credentials")
        return redirect(url_for("home"))

# ---- Admin Login ----
@app.route("/admin_login", methods=["POST"])
def admin_login():
    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin WHERE email=? AND password=?", (email, password))
    admin = cursor.fetchone()
    conn.close()

    if admin:
        session["admin"] = email
        return redirect(url_for("admin_dashboard"))
    else:
        flash("Invalid admin credentials")
        return redirect(url_for("home"))

# ---- Admin Dashboard ----
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        try:
            cursor.execute("INSERT INTO students (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            flash("Student added successfully!")
        except:
            flash("Student with this email already exists!")

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", students=students)

# ---- Student Dashboard ----
@app.route("/student_dashboard")
def student_dashboard():
    if "student" not in session:
        return redirect(url_for("home"))
    return render_template("student_dashboard.html", student_name=session["student"])

@app.route("/course/<int:course_id>")
def course(course_id):
    if course_id == 1:
        return render_template("course.html", title="Earthquake")
    else:
        return "Course not found"

# ---- Logout ----
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

QUESTION_POOL = [
    {
        "prompt": "What is an earthquake?",
        "options": [
            "A sudden shaking of the ground caused by movement of the Earth's plates",
            "A storm system with heavy rain",
            "A long period of calm weather",
            "A type of volcanic eruption"
        ],
        "answer_index": 0,
        "explanation": "An earthquake is sudden shaking of the ground caused by the movement of tectonic plates or volcanic activity."
    },
    {
        "prompt": "Which scale is commonly used to measure earthquake magnitude?",
        "options": ["Beaufort scale", "Richter scale", "Fahrenheit scale", "Saffir-Simpson scale"],
        "answer_index": 1,
        "explanation": "The Richter scale is a common measure of earthquake magnitude (strength)."
    },
    {
        "prompt": "Which of these is the safest immediate action during strong shaking indoors?",
        "options": [
            "Run outside immediately",
            "Drop, Cover, and Hold On (take cover under a table)",
            "Stand under a window",
            "Climb onto a shelf"
        ],
        "answer_index": 1,
        "explanation": "Drop, Cover, and Hold On: drop to the floor, take cover under sturdy furniture, and hold on until the shaking stops."
    },
    {
        "prompt": "If you are outside when an earthquake starts, what should you do?",
        "options": [
            "Stand next to buildings",
            "Move to an open area away from buildings, trees and power lines",
            "Hide inside your car under the dashboard",
            "Go inside the nearest building"
        ],
        "answer_index": 1,
        "explanation": "Outside, move to an open area away from buildings, trees, streetlights and power lines."
    },
    {
        "prompt": "Which of the following is a secondary hazard caused by earthquakes?",
        "options": ["Tsunami", "Solar eclipse", "Blizzard", "Heatwave"],
        "answer_index": 0,
        "explanation": "Earthquakes, especially undersea ones, can trigger tsunamis as a secondary hazard."
    },
    {
        "prompt": "What should you avoid using immediately after an earthquake if you smell gas?",
        "options": ["A flashlight", "A candle or open flame", "Calling emergency numbers", "Checking for injuries"],
        "answer_index": 1,
        "explanation": "Avoid open flames or anything that can ignite gas leaks. Turn off gas at the main if you know how and it's safe to do so."
    },
    {
        "prompt": "What is an aftershock?",
        "options": [
            "A small tremor that follows a larger earthquake",
            "A type of rainfall",
            "A tectonic plate boundary",
            "A measure of earthquake depth"
        ],
        "answer_index": 0,
        "explanation": "Aftershocks are smaller tremors that follow the main earthquake event."
    },
    {
        "prompt": "Where is it usually safest to take cover while indoors during shaking?",
        "options": [
            "Under a heavy bookshelf",
            "Near tall windows",
            "Under a sturdy table or desk",
            "In a doorway in modern buildings"
        ],
        "answer_index": 2,
        "explanation": "Under a sturdy table or desk is safer; modern doorways are not necessarily stronger."
    },
    {
        "prompt": "Which thing should you secure in advance to reduce earthquake damage at home?",
        "options": [
            "Heavy furniture and appliances to walls",
            "Decorative pillows",
            "Curtains",
            "Rugs"
        ],
        "answer_index": 0,
        "explanation": "Securing heavy furniture and appliances to the wall reduces falling hazards."
    },
    {
        "prompt": "If you are trapped under debris, what should you do first?",
        "options": [
            "Shout loudly without conserving breath",
            "Light a candle to get rescuers' attention",
            "Stay calm, cover your mouth to reduce dust inhalation, and try to make noise or use a whistle",
            "Immediately try to dig your way out"
        ],
        "answer_index": 2,
        "explanation": "Stay calm, protect your airway from dust, make noise or use a whistle; avoid actions that may cause more collapse."
    },
    # add more to pool so sampling is varied
    {
        "prompt": "What is 'liquefaction' in earthquake terms?",
        "options": [
            "Solid ground turning watery under shaking, causing buildings to sink",
            "Formation of lava",
            "Wind damage due to tremors",
            "A measurement of earthquake frequency"
        ],
        "answer_index": 0,
        "explanation": "Liquefaction is when saturated soils lose strength during shaking, behaving like a liquid."
    },
    {
        "prompt": "Before an earthquake, a good preparedness step is:",
        "options": [
            "Store emergency supplies and make a family plan",
            "Wait until a quake happens to think about supplies",
            "Only rely on your phone battery",
            "Never discuss escape routes"
        ],
        "answer_index": 0,
        "explanation": "Storing emergency supplies and making a family plan is key to preparedness."
    },
    {
        "prompt": "During an earthquake, elevators should:",
        "options": [
            "Be used to evacuate quickly",
            "Be avoided; get out at the nearest floor and use stairs",
            "Be the safest place",
            "Be used only if power is stable"
        ],
        "answer_index": 1,
        "explanation": "Avoid elevators during quakes; they may fail; use stairs once safe."
    }
]

# ---- helper: create a quiz of 10 random questions ----
def create_quiz():
    pool = QUESTION_POOL.copy()
    # if pool < 10, shuffle and use as many as available
    random.shuffle(pool)
    selected = pool[:10]
    # create ids for questions
    quiz = []
    for i, q in enumerate(selected):
        quiz.append({
            "qid": i+1,
            "prompt": q["prompt"],
            "options": q["options"],
            "answer_index": q["answer_index"],
            "explanation": q["explanation"]
        })
    return quiz

# ----- API endpoints -----

@app.route("/quiz/earthquake")
def quiz_page():
    # serves the chat UI HTML
    return render_template("quiz_chat.html")

@app.route("/api/quiz/new", methods=["POST"])
def api_quiz_new():
    # create new quiz round and store in session
    quiz = create_quiz()
    session['quiz'] = quiz
    session['qidx'] = 0       # index of next question to ask
    session['score'] = 0
    session['asked'] = 0
    return jsonify({"status": "ok", "message": "quiz started", "total": len(quiz)})

@app.route("/api/quiz/next", methods=["GET"])
def api_quiz_next():
    # return the next question (no answer)
    quiz = session.get('quiz')
    qidx = session.get('qidx', 0)
    if not quiz:
        return jsonify({"status":"error","message":"no quiz. call /api/quiz/new first"}), 400
    if qidx >= len(quiz):
        return jsonify({"status":"finished","score": session.get('score',0), "total": len(quiz)})
    q = quiz[qidx]
    # do NOT send answer_index here
    return jsonify({
        "status":"ok",
        "question": {
            "qid": q["qid"],
            "prompt": q["prompt"],
            "options": q["options"]
        },
        "progress": {"asked": session.get('asked',0), "total": len(quiz)}
    })

@app.route("/api/quiz/answer", methods=["POST"])
def api_quiz_answer():
    data = request.json
    if not data:
        return jsonify({"status":"error","message":"no data"}), 400
    qid = data.get("qid")
    chosen = data.get("chosen")  # integer index
    quiz = session.get('quiz')
    qidx = session.get('qidx', 0)
    if not quiz:
        return jsonify({"status":"error","message":"no quiz in session"}), 400

    # find current question by session qidx (must match qid)
    if qidx >= len(quiz):
        return jsonify({"status":"finished","score": session.get('score',0), "total": len(quiz)})

    current = quiz[qidx]
    if current['qid'] != qid:
        # mismatch, find by qid
        found = None
        for ix, qq in enumerate(quiz):
            if qq['qid'] == qid:
                found = (ix, qq)
                break
        if found is None:
            return jsonify({"status":"error","message":"question id not found"}), 400
        idx_in_list, current = found
        qidx = idx_in_list

    correct = (chosen == current['answer_index'])
    explanation = current.get('explanation', '')
    # update score and counters
    if correct:
        session['score'] = session.get('score',0) + 1
    session['asked'] = session.get('asked',0) + 1
    # advance qidx
    session['qidx'] = qidx + 1

    finished = session['qidx'] >= len(quiz)
    resp = {
        "status": "ok",
        "correct": correct,
        "explanation": explanation,
        "score": session.get('score',0),
        "asked": session.get('asked',0),
        "finished": finished,
        "total": len(quiz)
    }
    return jsonify(resp)

@app.route("/api/quiz/restart", methods=["POST"])
def api_quiz_restart():
    # simply create a new quiz
    quiz = create_quiz()
    session['quiz'] = quiz
    session['qidx'] = 0
    session['score'] = 0
    session['asked'] = 0
    return jsonify({"status":"ok","message":"quiz restarted","total":len(quiz)})


# -----------------------------
if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        init_db()
    else:
        try:
            init_db()
        except:
            os.remove(DB_NAME)
            init_db()
    app.run(debug=True)
