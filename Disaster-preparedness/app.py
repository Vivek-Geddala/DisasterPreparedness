from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify,json
import sqlite3
import os
import random
import uuid
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = "static/uploads"


app = Flask(__name__)
app.secret_key = "mysecretkey"  # needed for session management

COURSE_STRUCTURE = {
    "Earthquake": {
        "elements": {
            "video1": {"title": "What Is an Earthquake?", "weight": 30},
            "video2": {"title": "What to Do During an Earthquake", "weight": 30},
            "quiz": {"title": "Earthquake Quiz", "weight": 40}
        }
    },
    "Flood": {
        "elements": {
            "video1": {"title": "Causes of Floods", "weight": 30},
            "video2": {"title": "Flood Safety Measures", "weight": 30},
            "quiz": {"title": "Flood Quiz", "weight": 40}
        }
    },
    "Fire": {
        "elements": {
            "video1": {"title": "Common Fire Hazards", "weight": 30},
            "video2": {"title": "Fire Safety Drills", "weight": 30},
            "quiz": {"title": "Fire Safety Quiz", "weight": 40}
        }
    }
}

DB_NAME = "database.db"

# -----------------------------
# Initialize Database
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    course_name TEXT,
    progress_percentage INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id)
)''')


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
            cursor.execute("INSERT INTO students (name, email, password) VALUES (?, ?, ?)", 
                           (name, email, password))
            conn.commit()
            flash("Student added successfully!")
        except:
            flash("Student with this email already exists!")

    # Fetch students
    cursor.execute("SELECT id, name, email FROM students")
    students = cursor.fetchall()

    # Fetch progress per student
    student_progress = {}
    for s in students:
        sid = s[0]
        cursor.execute("SELECT course_name, progress_percentage FROM student_progress WHERE student_id=?", (sid,))
        progress = cursor.fetchall()
        student_progress[sid] = progress

    conn.close()

    # ✅ Now pass student_progress to the template
    return render_template("admin_dashboard.html", students=students, student_progress=student_progress)


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
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))  # or url_for("home") if homepage is your landing


# -------------------------------
# Quiz Question Pools
# -------------------------------
EARTHQUAKE_QUESTIONS = [
    {
        "prompt": "What is an earthquake?",
        "options": [
            "A sudden shaking of the ground caused by movement of Earth's plates",
            "A strong windstorm",
            "A volcanic eruption",
            "A long period of rainfall"
        ],
        "answer_index": 0,
        "explanation": "Earthquakes occur due to sudden tectonic plate movement or volcanic activity."
    },
    {
        "prompt": "Which instrument is used to record earthquake vibrations?",
        "options": ["Seismograph", "Barometer", "Anemometer", "Hygrometer"],
        "answer_index": 0,
        "explanation": "A seismograph records earthquake vibrations."
    },
    {
        "prompt": "Which scale is commonly used to measure earthquake magnitude?",
        "options": ["Richter scale", "Beaufort scale", "Fujita scale", "Mercalli scale"],
        "answer_index": 0,
        "explanation": "The Richter scale measures earthquake magnitude."
    },
    {
        "prompt": "What is the epicenter of an earthquake?",
        "options": [
            "Point inside Earth where quake starts",
            "Point on Earth’s surface directly above the focus",
            "The largest city affected",
            "The aftershock location"
        ],
        "answer_index": 1,
        "explanation": "Epicenter is the point on the surface directly above the earthquake focus."
    },
    {
        "prompt": "Which waves are the fastest seismic waves?",
        "options": ["P-waves", "S-waves", "Surface waves", "Rayleigh waves"],
        "answer_index": 0,
        "explanation": "P-waves (primary waves) are the fastest seismic waves."
    },
    {
        "prompt": "What do S-waves stand for?",
        "options": ["Surface waves", "Secondary waves", "Side waves", "Shock waves"],
        "answer_index": 1,
        "explanation": "S-waves are secondary waves that arrive after P-waves."
    },
    {
        "prompt": "Which type of boundary is most associated with earthquakes?",
        "options": ["Transform", "Divergent", "Convergent", "All of these"],
        "answer_index": 3,
        "explanation": "All plate boundaries (transform, divergent, convergent) can produce earthquakes."
    },
    {
        "prompt": "Which earthquake is considered the largest in recorded history?",
        "options": ["2004 Indian Ocean", "1960 Chile", "2011 Japan", "1906 San Francisco"],
        "answer_index": 1,
        "explanation": "The 1960 Valdivia earthquake in Chile was the largest ever recorded (magnitude 9.5)."
    },
    {
        "prompt": "Which building design is safer in earthquake-prone areas?",
        "options": [
            "Flexible structures with base isolation",
            "Very tall and rigid buildings",
            "Unreinforced brick buildings",
            "Glass-heavy skyscrapers"
        ],
        "answer_index": 0,
        "explanation": "Flexible structures with base isolation resist shaking better."
    },
    {
        "prompt": "What should you do indoors during an earthquake?",
        "options": [
            "Run outside immediately",
            "Hide in the basement",
            "Drop, Cover, and Hold On",
            "Stand near windows"
        ],
        "answer_index": 2,
        "explanation": "The safest action is Drop, Cover, and Hold On until shaking stops."
    },
    {
        "prompt": "What should you do if you are outside during an earthquake?",
        "options": [
            "Move to an open area away from buildings",
            "Hide under trees",
            "Run into a building",
            "Stand near power lines"
        ],
        "answer_index": 0,
        "explanation": "Stay in an open area away from buildings, trees, and power lines."
    },
    {
        "prompt": "Which earthquake caused the Fukushima nuclear disaster?",
        "options": [
            "2004 Indian Ocean",
            "2010 Haiti",
            "2011 Tōhoku, Japan",
            "1976 Tangshan, China"
        ],
        "answer_index": 2,
        "explanation": "The 2011 Tōhoku earthquake triggered a tsunami that caused the Fukushima disaster."
    },
    {
        "prompt": "What is liquefaction in earthquakes?",
        "options": [
            "Solid ground turning into quicksand-like state",
            "Volcanic lava flow",
            "Melting glaciers",
            "Collapse of buildings"
        ],
        "answer_index": 0,
        "explanation": "Liquefaction occurs when water-saturated soil temporarily behaves like liquid."
    },
    {
        "prompt": "What is an aftershock?",
        "options": [
            "A smaller earthquake following the main one",
            "A volcanic eruption",
            "The foreshock",
            "A tsunami"
        ],
        "answer_index": 0,
        "explanation": "Aftershocks are smaller quakes that follow a major earthquake."
    },
    {
        "prompt": "Which of these is a man-made cause of earthquakes?",
        "options": ["Plate tectonics", "Volcanic activity", "Mining blasts", "Tsunamis"],
        "answer_index": 2,
        "explanation": "Mining explosions and reservoir-induced seismicity are human causes."
    },
    {
        "prompt": "What does the Modified Mercalli Intensity (MMI) scale measure?",
        "options": ["Magnitude", "Damage and shaking felt", "Speed of waves", "Energy release"],
        "answer_index": 1,
        "explanation": "MMI measures intensity of shaking and damage as felt by people."
    },
    {
        "prompt": "Which layer of the Earth is most involved in earthquakes?",
        "options": ["Inner core", "Mantle", "Crust", "Outer core"],
        "answer_index": 2,
        "explanation": "Most earthquakes originate in the Earth's crust."
    },
    {
        "prompt": "What is the hypocenter of an earthquake?",
        "options": [
            "The surface rupture",
            "The point inside Earth where quake starts",
            "The epicenter",
            "The shockwave"
        ],
        "answer_index": 1,
        "explanation": "The hypocenter (focus) is the actual underground origin of the earthquake."
    },
    {
        "prompt": "Which U.S. state is most earthquake-prone?",
        "options": ["Texas", "California", "Florida", "Ohio"],
        "answer_index": 1,
        "explanation": "California lies along the San Andreas Fault and is highly earthquake-prone."
    },
    {
        "prompt": "Which country has the most earthquakes annually?",
        "options": ["Japan", "India", "Australia", "South Africa"],
        "answer_index": 0,
        "explanation": "Japan experiences frequent earthquakes due to its tectonic location."
    },
    {
        "prompt": "What is a tsunami?",
        "options": [
            "A giant ocean wave caused by underwater earthquakes",
            "A tidal wave",
            "A strong wind",
            "A river flood"
        ],
        "answer_index": 0,
        "explanation": "Tsunamis are giant waves triggered by undersea earthquakes or landslides."
    },
    {
        "prompt": "Which Indian city was most affected by the 2001 Bhuj earthquake?",
        "options": ["Ahmedabad", "Surat", "Bhuj", "Mumbai"],
        "answer_index": 2,
        "explanation": "The 2001 Gujarat earthquake had its epicenter near Bhuj."
    },
    {
        "prompt": "What is the safest place in a house during an earthquake?",
        "options": [
            "Near windows",
            "Under a sturdy table",
            "In an elevator",
            "Next to tall shelves"
        ],
        "answer_index": 1,
        "explanation": "Taking cover under a sturdy table or desk is safest indoors."
    },
    {
        "prompt": "Which of the following is NOT a seismic hazard?",
        "options": ["Ground shaking", "Tsunamis", "Landslides", "Snowfall"],
        "answer_index": 3,
        "explanation": "Snowfall is not caused by earthquakes."
    },
    {
        "prompt": "What does earthquake 'magnitude' measure?",
        "options": ["Energy released", "Damage caused", "Deaths", "Aftershocks"],
        "answer_index": 0,
        "explanation": "Magnitude measures energy released at the source of the earthquake."
    },
    {
        "prompt": "What should drivers do if an earthquake occurs while driving?",
        "options": [
            "Stop in a safe open area",
            "Speed up to escape",
            "Park under a bridge",
            "Stop on railway tracks"
        ],
        "answer_index": 0,
        "explanation": "Drivers should stop safely in an open area, away from buildings and bridges."
    },
    {
        "prompt": "Which country experienced the 2004 Indian Ocean earthquake?",
        "options": ["Indonesia", "India", "Sri Lanka", "All of these"],
        "answer_index": 3,
        "explanation": "The earthquake and tsunami affected multiple countries including Indonesia, India, and Sri Lanka."
    },
    {
        "prompt": "What should be in an earthquake emergency kit?",
        "options": [
            "Water, food, flashlight, first-aid kit",
            "Extra clothes only",
            "Musical instruments",
            "Smartphone charger only"
        ],
        "answer_index": 0,
        "explanation": "An emergency kit should include water, food, flashlight, and first-aid supplies."
    },
    {
        "prompt": "What is retrofitting in earthquake safety?",
        "options": [
            "Adding decorations",
            "Strengthening existing buildings",
            "Painting houses",
            "Demolishing structures"
        ],
        "answer_index": 1,
        "explanation": "Retrofitting strengthens old buildings to resist earthquakes."
    },
    {
        "prompt": "Which South Asian country experienced a deadly earthquake in 2015?",
        "options": ["India", "Pakistan", "Nepal", "Bangladesh"],
        "answer_index": 2,
        "explanation": "Nepal suffered a devastating earthquake in April 2015."
    },
    {
        "prompt": "What is a foreshock?",
        "options": [
            "The main earthquake",
            "A smaller earthquake before the main one",
            "An aftershock",
            "A volcanic eruption"
        ],
        "answer_index": 1,
        "explanation": "Foreshocks are smaller quakes that sometimes precede the main shock."
    }
]

FLOOD_QUESTIONS = [
    {
        "prompt": "What should you do first during a flood warning?",
        "options": ["Stay in the basement", "Move to higher ground immediately", "Go near rivers", "Ignore it"],
        "answer_index": 1,
        "explanation": "The safest first action during a flood warning is to move to higher ground immediately."
    },
    {
        "prompt": "Which slogan warns drivers not to enter floodwaters?",
        "options": [
            "Run Fast, Stay Safe",
            "Turn Around, Don’t Drown",
            "Floods Come Slow",
            "Drive Through Quickly"
        ],
        "answer_index": 1,
        "explanation": "The National Weather Service uses 'Turn Around, Don’t Drown'."
    },
    {
        "prompt": "Which of these is NOT a direct cause of floods?",
        "options": ["Heavy rainfall", "Dam failure", "Storm surge", "Earthquake"],
        "answer_index": 3,
        "explanation": "Earthquakes do not directly cause floods, although they can lead to dam failures."
    },
    {
        "prompt": "Why is urban flooding common?",
        "options": ["Large parks", "Blocked or poor drainage systems", "Wide roads", "Cold weather"],
        "answer_index": 1,
        "explanation": "Poor drainage and paved surfaces prevent water absorption in urban areas."
    },
    {
        "prompt": "What is the best action if trapped in a car during a flood?",
        "options": [
            "Stay inside and wait",
            "Abandon the car and move to higher ground",
            "Drive faster",
            "Call friends"
        ],
        "answer_index": 1,
        "explanation": "It is safest to abandon the car and move to higher ground."
    },
    {
        "prompt": "Which natural disaster often follows flash floods?",
        "options": ["Earthquakes", "Landslides", "Volcanic eruptions", "Droughts"],
        "answer_index": 1,
        "explanation": "Floods can destabilize slopes and trigger landslides."
    },
    {
        "prompt": "Which of these is a common health risk after floods?",
        "options": ["Malaria and cholera", "Broken bones", "Sunburn", "Frostbite"],
        "answer_index": 0,
        "explanation": "Floods create stagnant water and poor sanitation, spreading diseases like malaria and cholera."
    },
    {
        "prompt": "What is a flash flood?",
        "options": [
            "A flood that develops within minutes or hours of heavy rain",
            "A flood that lasts for months",
            "A flood caused by snow",
            "A flood caused by ocean tides"
        ],
        "answer_index": 0,
        "explanation": "Flash floods develop very quickly and are extremely dangerous."
    },
    {
        "prompt": "Which region in India is most prone to annual floods?",
        "options": ["Rajasthan", "Assam and Bihar", "Punjab", "Kerala"],
        "answer_index": 1,
        "explanation": "The Brahmaputra and Ganga basins in Assam and Bihar flood annually."
    },
    {
        "prompt": "What should you do if advised to evacuate during a flood?",
        "options": [
            "Delay and wait for confirmation",
            "Leave immediately and follow official routes",
            "Pack slowly",
            "Ignore and stay home"
        ],
        "answer_index": 1,
        "explanation": "Leaving immediately is the safest choice."
    },
    {
        "prompt": "What is the main purpose of levees and embankments?",
        "options": ["To grow crops", "To prevent flooding", "To store water", "To generate power"],
        "answer_index": 1,
        "explanation": "Levees and embankments are built to contain rivers and prevent flooding."
    },
    {
        "prompt": "Which of these is a sign of possible flash flooding?",
        "options": ["Clear skies", "Sudden heavy rainfall", "Strong winds only", "Snowfall"],
        "answer_index": 1,
        "explanation": "Sudden heavy rainfall is a major cause of flash floods."
    },
    {
        "prompt": "What should you avoid drinking after floods?",
        "options": ["Tap water unless boiled or treated", "Bottled water", "Rainwater", "Coconut water"],
        "answer_index": 0,
        "explanation": "Tap water is often contaminated after floods and should be boiled or treated."
    },
    {
        "prompt": "Which satellite system helps predict floods?",
        "options": ["Weather satellites", "Communication satellites", "Navigation satellites", "Spy satellites"],
        "answer_index": 0,
        "explanation": "Weather satellites help predict heavy rainfall and floods."
    },
    {
        "prompt": "Which river’s flooding in 1931 caused millions of deaths?",
        "options": ["Amazon", "Mississippi", "Yangtze River, China", "Nile"],
        "answer_index": 2,
        "explanation": "The 1931 Yangtze River floods were among the deadliest in history."
    },
    {
        "prompt": "What is the safest way to walk through floodwater if unavoidable?",
        "options": [
            "Barefoot",
            "With a stick to check depth",
            "Quickly running",
            "Holding an electric wire"
        ],
        "answer_index": 1,
        "explanation": "Always use a stick to check depth and stability when walking through floodwater."
    },
    {
        "prompt": "What is the main cause of flash floods in hilly areas?",
        "options": ["Glacier melting", "Cloudbursts", "Low rainfall", "Forest fires"],
        "answer_index": 1,
        "explanation": "Cloudbursts in hilly areas can trigger sudden flash floods."
    },
    {
        "prompt": "Which household items should be unplugged during a flood?",
        "options": ["All electrical appliances", "Only lights", "Only fridge", "None"],
        "answer_index": 0,
        "explanation": "Unplugging all electrical appliances prevents electrocution."
    },
    {
        "prompt": "Which is NOT a flood safety tip?",
        "options": [
            "Move to higher ground",
            "Avoid floodwaters",
            "Drive through water to save time",
            "Follow official updates"
        ],
        "answer_index": 2,
        "explanation": "Never drive through floodwaters; it is extremely dangerous."
    },
    {
        "prompt": "Which device measures rainfall to predict floods?",
        "options": ["Seismograph", "Rain gauge", "Thermometer", "Wind vane"],
        "answer_index": 1,
        "explanation": "A rain gauge measures rainfall levels."
    },
    {
        "prompt": "What should you carry in a flood emergency kit?",
        "options": [
            "Water, food, torch, radio, first-aid kit",
            "Smartphone only",
            "Books",
            "Sports equipment"
        ],
        "answer_index": 0,
        "explanation": "A flood kit must include essentials like water, food, torch, and first-aid supplies."
    },
    {
        "prompt": "What is the main danger of moving floodwater?",
        "options": [
            "It is very cold",
            "It has strong currents",
            "It has fish",
            "It causes dust"
        ],
        "answer_index": 1,
        "explanation": "Strong currents in floodwaters can sweep away people and vehicles."
    },
    {
        "prompt": "Which Indian river is known for frequent devastating floods?",
        "options": ["Yamuna", "Brahmaputra", "Godavari", "Mahanadi"],
        "answer_index": 1,
        "explanation": "The Brahmaputra regularly causes floods in Assam."
    },
    {
        "prompt": "What should farmers do to minimize flood damage?",
        "options": ["Plant crops in lowlands", "Build raised platforms", "Leave fields unprotected", "Ignore warnings"],
        "answer_index": 1,
        "explanation": "Raised platforms and embankments reduce crop losses."
    },
    {
        "prompt": "Which of these is a human activity that worsens flooding?",
        "options": ["Deforestation", "Planting trees", "Rainwater harvesting", "Building reservoirs"],
        "answer_index": 0,
        "explanation": "Deforestation reduces soil absorption, increasing runoff and flooding."
    },
    {
        "prompt": "Which season in India is most associated with floods?",
        "options": ["Summer", "Winter", "Monsoon", "Spring"],
        "answer_index": 2,
        "explanation": "Monsoon rains cause widespread floods in India."
    },
    {
        "prompt": "What is the safest shelter during floods?",
        "options": ["A house on stilts", "Basement", "Underground tunnel", "Near river bank"],
        "answer_index": 0,
        "explanation": "Houses on stilts or raised ground provide safer shelter."
    },
    {
        "prompt": "What is a floodplain?",
        "options": [
            "Flat land near a river that floods regularly",
            "Desert area",
            "Mountain slope",
            "Coastal sand dune"
        ],
        "answer_index": 0,
        "explanation": "Floodplains are low-lying flat lands that naturally flood when rivers overflow."
    },
    {
        "prompt": "Which international body helps in flood disaster relief?",
        "options": ["UNICEF", "WHO", "Red Cross", "UNESCO"],
        "answer_index": 2,
        "explanation": "The Red Cross provides emergency relief during floods worldwide."
    }
]

FIRE_QUESTIONS = [
    {
        "prompt": "What should you never use during a fire evacuation?",
        "options": ["Stairs", "Elevators", "Fire exits", "Alarm"],
        "answer_index": 1,
        "explanation": "Never use elevators; always use stairs in a fire."
    },
    {
        "prompt": "If your clothes catch fire, what should you do?",
        "options": ["Run outside quickly", "Stop, Drop, and Roll", "Pour water immediately", "Hide under a blanket"],
        "answer_index": 1,
        "explanation": "Stop, Drop, and Roll is the recommended safety technique."
    },
    {
        "prompt": "Which class of fire extinguisher is used for electrical fires?",
        "options": ["Class A", "Class B", "Class C", "Class D"],
        "answer_index": 2,
        "explanation": "Class C extinguishers are designed for electrical fires."
    },
    {
        "prompt": "What is the first step when you see a fire?",
        "options": ["Raise the alarm", "Run away silently", "Collect belongings", "Hide under a desk"],
        "answer_index": 0,
        "explanation": "Always raise the alarm first so others are warned."
    },
    {
        "prompt": "What does the acronym PASS stand for in fire extinguisher use?",
        "options": [
            "Pull, Aim, Squeeze, Sweep",
            "Push, Alert, Stop, Spray",
            "Pull, Attack, Spray, Stop",
            "Push, Aim, Sweep, Stop"
        ],
        "answer_index": 0,
        "explanation": "PASS = Pull, Aim, Squeeze, Sweep."
    },
    {
        "prompt": "Which type of fire is caused by flammable liquids like petrol?",
        "options": ["Class A", "Class B", "Class C", "Class D"],
        "answer_index": 1,
        "explanation": "Class B fires involve flammable liquids."
    },
    {
        "prompt": "What should you do if you see smoke filling a room?",
        "options": [
            "Stand tall and breathe normally",
            "Crawl low under the smoke",
            "Run quickly upright",
            "Wait in the smoke"
        ],
        "answer_index": 1,
        "explanation": "Smoke rises, so crawling low helps you breathe cleaner air."
    },
    {
        "prompt": "What should be kept clear at all times for fire safety?",
        "options": ["Windows", "Fire exits and escape routes", "Parking lots", "Balconies"],
        "answer_index": 1,
        "explanation": "Fire exits and escape routes must always be clear."
    },
    {
        "prompt": "Which fire is caused by ordinary combustibles like wood and paper?",
        "options": ["Class A", "Class B", "Class C", "Class D"],
        "answer_index": 0,
        "explanation": "Class A fires involve materials like wood, paper, and cloth."
    },
    {
        "prompt": "Why should you avoid opening hot doors during a fire?",
        "options": [
            "They may break",
            "Fire or smoke may rush through",
            "They may be locked",
            "They may release gas"
        ],
        "answer_index": 1,
        "explanation": "If a door feels hot, fire is likely behind it."
    },
    {
        "prompt": "What should be installed in every home to detect fires early?",
        "options": ["Security cameras", "Smoke detectors", "Sprinklers only", "CO2 sensors"],
        "answer_index": 1,
        "explanation": "Smoke detectors are essential for early fire detection."
    },
    {
        "prompt": "Which of these is the safest fire escape practice?",
        "options": [
            "Use stairs, not elevators",
            "Break windows immediately",
            "Jump from high floors",
            "Hide in the bathroom"
        ],
        "answer_index": 0,
        "explanation": "Always use stairs for evacuation during fire emergencies."
    },
    {
        "prompt": "What is the purpose of a fire drill?",
        "options": [
            "To practice safe evacuation",
            "To test firefighting skills only",
            "To check attendance",
            "To inspect uniforms"
        ],
        "answer_index": 0,
        "explanation": "Fire drills prepare people to evacuate safely and quickly."
    },
    {
        "prompt": "What is the common cause of kitchen fires?",
        "options": ["Overheated cooking oil", "Too much salt", "Cold utensils", "Microwave beeping"],
        "answer_index": 0,
        "explanation": "Overheated oil and unattended cooking cause most kitchen fires."
    },
    {
        "prompt": "What is the safest way to extinguish a small pan fire?",
        "options": ["Pour water", "Cover with a lid", "Blow on it", "Use paper"],
        "answer_index": 1,
        "explanation": "Smother the flames by covering with a lid; never pour water on oil fires."
    },
    {
        "prompt": "What type of fire extinguisher is used for metal fires?",
        "options": ["Class A", "Class B", "Class C", "Class D"],
        "answer_index": 3,
        "explanation": "Class D extinguishers are used for flammable metal fires."
    },
    {
        "prompt": "Which material is most fire-resistant?",
        "options": ["Cotton", "Wool", "Asbestos", "Plastic"],
        "answer_index": 2,
        "explanation": "Asbestos is highly fire-resistant (though hazardous to health)."
    },
    {
        "prompt": "Which emergency number should you dial in most countries for fire help?",
        "options": ["911 or local fire service", "123", "9999", "411"],
        "answer_index": 0,
        "explanation": "Dial 911 in the US, or local fire emergency numbers elsewhere."
    },
    {
        "prompt": "What should schools and colleges practice regularly?",
        "options": ["Fire drills", "Sports only", "Exams", "Stage shows"],
        "answer_index": 0,
        "explanation": "Regular fire drills ensure students know evacuation procedures."
    },
    {
        "prompt": "What does a fire triangle consist of?",
        "options": ["Heat, fuel, oxygen", "Water, smoke, gas", "Fire, ash, wind", "Wood, air, sun"],
        "answer_index": 0,
        "explanation": "The fire triangle consists of heat, fuel, and oxygen."
    },
    {
        "prompt": "What is the first thing to do when a fire alarm rings?",
        "options": ["Continue working", "Evacuate immediately", "Wait for confirmation", "Call a friend"],
        "answer_index": 1,
        "explanation": "Always evacuate immediately when the alarm rings."
    },
    {
        "prompt": "What is a fire hydrant used for?",
        "options": [
            "Decorating roads",
            "Providing water for firefighting",
            "Drinking water",
            "Washing cars"
        ],
        "answer_index": 1,
        "explanation": "Fire hydrants supply water to firefighters."
    },
    {
        "prompt": "What should you never use to put out an electrical fire?",
        "options": ["CO2 extinguisher", "Dry chemical extinguisher", "Water", "Fire blanket"],
        "answer_index": 2,
        "explanation": "Water conducts electricity and worsens electrical fires."
    },
    {
        "prompt": "Why should fire extinguishers be checked regularly?",
        "options": [
            "To look shiny",
            "To ensure they are charged and functional",
            "For decoration",
            "To keep them clean"
        ],
        "answer_index": 1,
        "explanation": "Extinguishers must be ready to use in an emergency."
    },
    {
        "prompt": "What is a sprinkler system designed to do?",
        "options": [
            "Cool rooms",
            "Detect intruders",
            "Release water to control fires",
            "Decorate ceilings"
        ],
        "answer_index": 2,
        "explanation": "Sprinklers automatically release water when fire is detected."
    },
    {
        "prompt": "Which workplace item is mandatory for fire safety?",
        "options": ["Fire extinguisher", "Printer", "Coffee machine", "Decorative lights"],
        "answer_index": 0,
        "explanation": "Workplaces must have accessible fire extinguishers."
    },
    {
        "prompt": "Which action helps prevent electrical fires?",
        "options": [
            "Avoid overloading sockets",
            "Use damaged wires",
            "Keep appliances plugged in always",
            "Ignore sparks"
        ],
        "answer_index": 0,
        "explanation": "Never overload sockets and replace damaged wires."
    },
    {
        "prompt": "Which symbol indicates a fire extinguisher location?",
        "options": ["Flame with red box", "Cross mark", "Green running man", "Circle with arrow"],
        "answer_index": 0,
        "explanation": "A red flame symbol marks extinguisher locations."
    },
    {
        "prompt": "Which emergency response should you follow if trapped in smoke?",
        "options": [
            "Open windows fully",
            "Stay low, cover nose with cloth",
            "Run randomly",
            "Climb to the roof immediately"
        ],
        "answer_index": 1,
        "explanation": "Stay low and cover nose to avoid inhaling toxic smoke."
    },
    {
        "prompt": "Which common holiday item increases fire risk?",
        "options": ["Candles and fireworks", "Books", "Shoes", "Television"],
        "answer_index": 0,
        "explanation": "Candles and fireworks increase fire risk during holidays."
    }
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
        return jsonify({"status": "error", "message": "no data"}), 400

    qid = data.get("qid")
    chosen = data.get("chosen")  # integer index
    quiz = session.get("quiz")
    qidx = session.get("qidx", 0)

    if not quiz:
        return jsonify({"status": "error", "message": "no quiz in session"}), 400

    if qidx >= len(quiz):
        return jsonify({"status": "finished", "score": session.get("score", 0), "total": len(quiz)})

    current = quiz[qidx]
    answer_index = current["answer_index"]

    # ✅ Evaluate answer
    correct = (chosen == answer_index)
    explanation = current.get("explanation", "")

    if correct:
        session["score"] = session.get("score", 0) + 1

    session["asked"] = session.get("asked", 0) + 1
    session["qidx"] = qidx + 1
    finished = session["qidx"] >= len(quiz)

    # ✅ Update course progress if quiz finished
    if finished and "student_id" in session:
        update_progress(session["student_id"], session.get("topic", "").capitalize(), "quiz")

    resp = {
        "status": "ok",
        "correct": correct,
        "explanation": explanation,
        "score": session.get("score", 0),
        "asked": session.get("asked", 0),
        "finished": finished,
        "total": len(quiz),
    }
    return jsonify(resp)


def update_progress(student_id, course, element_id):
    weight = COURSE_STRUCTURE[course]["elements"][element_id]["weight"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Get current progress
    cursor.execute("SELECT progress_percentage FROM student_progress WHERE student_id=? AND course_name=?", 
                   (student_id, course))
    row = cursor.fetchone()
    current_progress = row[0] if row else 0

    new_progress = min(100, current_progress + weight)

    if row:
        cursor.execute("UPDATE student_progress SET progress_percentage=?, last_updated=CURRENT_TIMESTAMP WHERE student_id=? AND course_name=?", 
                       (new_progress, student_id, course))
    else:
        cursor.execute("INSERT INTO student_progress (student_id, course_name, progress_percentage) VALUES (?,?,?)", 
                       (student_id, course, weight))
    conn.commit()
    conn.close()
@app.route("/update_progress", methods=["POST"])
def api_update_progress():
    if "student_id" not in session:
        return jsonify({"status": "error", "message": "not logged in"}), 403
    
    data = request.json
    course = data.get("course")
    element = data.get("element")

    update_progress(session["student_id"], course, element)
    return jsonify({"status": "ok", "message": f"{element} marked complete for {course}"})
@app.route("/student_progress/<int:student_id>")
def student_progress(student_id):
    if "admin" not in session:
        return redirect(url_for("home"))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT course_name, progress_percentage, last_updated FROM student_progress WHERE student_id=?", (student_id,))
    progress = cursor.fetchall()
    conn.close()

    return render_template("student_progress.html", progress=progress, student_id=student_id)


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
