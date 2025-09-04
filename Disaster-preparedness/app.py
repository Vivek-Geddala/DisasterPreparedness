from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify,json
import sqlite3
import os
import random
import uuid
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/uploads"


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
    cursor.execute('''CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    text TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id)
)''')


    # Admin table (only one admin for now)
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )''')

    # In app.py, inside init_db()
    cursor.execute('''CREATE TABLE IF NOT EXISTS student_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    course_name TEXT,
    progress_percentage INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id)
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
        session["student_id"] = student[0]
        session["student"] = student[1]  # store student name
        session["student_email"] = student[2]

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
    elif course_id == 2:
        return render_template("flood_course.html", title="Floods")
    elif course_id == 3:
        return render_template("fire_course.html", title="Fire Safety")
    else:
        return "Course not found"
    
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload_profile_photo", methods=["POST"])
def upload_profile_photo():
    if "student_id" not in session:
        return redirect(url_for("home"))
    file = request.files["photo"]
    if file:
        filename = secure_filename(file.filename)
        unique_name = str(uuid.uuid4()) + "_" + filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)

        # Save filename in DB (add a profile_photo column if needed)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET profile_photo=? WHERE id=?",
                       (unique_name, session["student_id"]))
        conn.commit()
        conn.close()

        flash("Profile photo updated successfully!")
    return redirect(url_for("student_dashboard"))

@app.route("/add_achievement", methods=["POST"])
def add_achievement():
    if "student_id" not in session:
        return redirect(url_for("home"))
    achievement = request.form["achievement"]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO achievements (student_id, text) VALUES (?, ?)",
                   (session["student_id"], achievement))
    conn.commit()
    conn.close()
    return redirect(url_for("student_dashboard"))



# ---- Logout ----
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
# -------------------------------
# Quiz Question Pools
# -------------------------------

EARTHQUAKE_QUESTIONS = [
    {
        "prompt": "What is an earthquake?",
        "options": [
            "A sudden shaking of the ground caused by movement of the Earth's plates",
            "A storm system with heavy rain",
            "A long period of calm weather",
            "A type of volcanic eruption"
        ],
        "answer_index": 0,
        "explanation": "An earthquake is sudden shaking of the ground caused by tectonic plate movement or volcanic activity."
    },
    # ... (your existing questions here)
]

FLOOD_QUESTIONS = [
    {
        "prompt": "What should you do first during a flood warning?",
        "options": [
            "Go for a walk near the river",
            "Move to higher ground immediately",
            "Stay in the basement",
            "Ignore the warning"
        ],
        "answer_index": 1,
        "explanation": "The safest first action during a flood warning is to move to higher ground immediately."
    },
    {
        "prompt": "What does 'Turn Around, Don’t Drown' mean?",
        "options": [
            "Drive faster through floodwaters",
            "Never attempt to drive through flooded roads",
            "Swim across flooded streets",
            "Stay in your car if water rises"
        ],
        "answer_index": 1,
        "explanation": "It means: never drive through flooded roads, as water depth and currents are deceptive."
    },
    # add ~8 more
]

FIRE_QUESTIONS = [
    {
        "prompt": "What should you never use during a fire evacuation?",
        "options": [
            "Stairs",
            "Elevators",
            "Fire exits",
            "Alarm systems"
        ],
        "answer_index": 1,
        "explanation": "Elevators should never be used during a fire; always use stairs."
    },
    {
        "prompt": "What is the correct action if your clothes catch fire?",
        "options": [
            "Run outside quickly",
            "Stop, Drop, and Roll",
            "Pour water over yourself immediately",
            "Hide under a blanket"
        ],
        "answer_index": 1,
        "explanation": "Stop, Drop, and Roll is the best way to extinguish flames on clothing."
    },
    # add ~8 more
]


# ---- helper: create a quiz of 10 random questions ----
def create_quiz(topic="earthquake"):
    if topic == "earthquake":
        pool = EARTHQUAKE_QUESTIONS.copy()
    elif topic == "flood":
        pool = FLOOD_QUESTIONS.copy()
    elif topic == "fire":
        pool = FIRE_QUESTIONS.copy()
    else:
        pool = []

    random.shuffle(pool)
    selected = pool[:10]
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

@app.route("/quiz/<topic>")
def quiz_page(topic):
    if topic in ["earthquake", "flood", "fire"]:
        return render_template("quiz_chat.html", topic=topic)
    return "Quiz not found", 404

@app.route("/api/quiz/new/<topic>", methods=["POST"])
def api_quiz_new(topic):
    quiz = create_quiz(topic)
    if not quiz:
        return jsonify({"status": "error", "message": "Invalid topic"}), 400
    session['quiz'] = quiz
    session['qidx'] = 0
    session['score'] = 0
    session['asked'] = 0
    return jsonify({"status": "ok", "message": f"{topic} quiz started", "total": len(quiz)})


# ----- API endpoints ----

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

# In app.py
COURSE_STRUCTURE = {
    "Earthquake Course": {
        "total_trackable_elements": 2, # e.g., 2 videos
        "elements": {
            "What Is an Earthquake?": {"id": "video1", "weight": 1},
            "What to Do If You’re Stuck in an Earthquake": {"id": "video2", "weight": 1}
        }
    }
    # Add other courses here
}

# You would also need to store student_id in session upon login
# In student_login() and admin_login()
# session["student_id"] = student[0] # Assuming student[0] is the ID

@app.route("/delete_student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if "admin" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()

    flash("Student removed successfully!")
    return redirect(url_for("admin_dashboard"))

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
