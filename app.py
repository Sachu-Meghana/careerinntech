from flask import Flask, request, redirect, session, render_template_string
import sqlite3

app = Flask(__name__)
app.secret_key = "careerinn_secure_key"
DB = "database.db"

# ======================= DB SETUP =======================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS colleges(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            location TEXT,
            fees INT,
            placements TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS mentors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            experience TEXT,
            speciality TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            salary TEXT
        )
    """)

    # ---------- REAL HYDERABAD HM COLLEGES (approx yearly fees) ----------
    colleges_seed = [
        ("IHM Hyderabad (IHMH)", "DD Colony, Hyderabad", 120000,
         "Govt. hotel management institute, national-level placements"),

        ("NITHM Hyderabad", "Gachibowli, Hyderabad", 130000,
         "Tourism & hospitality institute with campus placements"),

        ("IIHM Hyderabad", "Somajiguda, Hyderabad", 150000,
         "International hotel management network, industry tie-ups"),

        ("Regency College of Culinary Arts & Hotel Management", "Himayatnagar, Hyderabad", 120000,
         "Strong culinary focus, good city hotel placements"),

        ("IHM Shri Shakti", "Kompally, Hyderabad", 121000,
         "Affiliated to NCHM, hospitality & hotel admin"),

        ("Chennais Amirta IHM – Hyderabad", "Khairatabad, Hyderabad", 100000,
         "Diploma, UG and PG hotel management with placement assistance"),

        ("Westin College of Hotel Management", "Nizampet, Hyderabad", 100000,
         "Affiliated to Osmania University, offers national & international placements"),

        ("Malla Reddy University – Hotel Management", "Maisammaguda, Hyderabad", 110000,
         "University campus with hotel management specialisations"),

        ("SIITAM Hyderabad", "Tarnaka, Hyderabad", 103000,
         "Hotel management programmes with industry exposure"),

        ("Zest College of Hotel Management", "Hyderabad", 65000,
         "Budget-focused hotel management college"),

        ("Roots Collegium – Hotel Management", "Somajiguda, Hyderabad", 110000,
         "Hospitality, culinary & hotel management"),

        ("Aptech Aviation & Hospitality – Hyderabad", "Ameerpet, Hyderabad", 90000,
         "Aviation + hospitality courses with placement support")
    ]

    # Always refresh colleges list with the latest seed
    c.execute("DELETE FROM colleges")
    c.executemany(
        "INSERT INTO colleges(name,location,fees,placements) VALUES(?,?,?,?)",
        colleges_seed
    )

    # ----- keep your earlier demo seed for mentors & jobs -----
    c.execute("SELECT COUNT(*) FROM mentors")
    if c.fetchone()[0] == 0:
        mentors_seed = [
            ("Mentor ... A", "Experience ...", "Speciality ..."),
            ("Mentor ... B", "Experience ...", "Speciality ..."),
            ("Mentor ... C", "Experience ...", "Speciality ...")
        ]
        c.executemany(
            "INSERT INTO mentors(name,experience,speciality) VALUES(?,?,?)",
            mentors_seed
        )

    c.execute("SELECT COUNT(*) FROM jobs")
    if c.fetchone()[0] == 0:
        jobs_seed = [
            ("Job ... A", "Company ...", "Location ...", "Salary ..."),
            ("Job ... B", "Company ...", "Location ...", "Salary ..."),
            ("Job ... C", "Company ...", "Location ...", "Salary ...")
        ]
        c.executemany(
            "INSERT INTO jobs(title,company,location,salary) VALUES(?,?,?,?)",
            jobs_seed
        )

    conn.commit()
    conn.close()


# run once on import (works locally + on Render)
init_db()

# ======================= BASE LAYOUT =======================
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ title or "CareerInn" }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-[#050815] text-white">

<div class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
  <!-- NAVBAR -->
  <nav class="flex justify-between items-center px-6 md:px-10 py-4 bg-black/40 backdrop-blur-md border-b border-slate-800">
    <div class="flex items-center gap-3">
      <div class="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center shadow-lg shadow-indigo-500/40 overflow-hidden">
        <img src="/static/logo.png" class="w-11 h-11 object-contain" alt="CareerInn logo">
      </div>
      <div>
        <p class="font-bold text-lg md:text-xl tracking-tight">CareerInn</p>
        <p class="text-[11px] text-slate-400">Hospitality Careers · Courses · Jobs</p>
      </div>
    </div>

    <div class="hidden md:flex items-center gap-6 text-sm">
      <a href="/" class="hover:text-indigo-400">Home</a>
      <a href="/courses" class="hover:text-indigo-400">Courses</a>
      <a href="/mentorship" class="hover:text-indigo-400">Mentorship</a>
      <a href="/jobs" class="hover:text-indigo-400">Jobs</a>
      <a href="/support" class="hover:text-indigo-400">Support</a>

      {% if session.get('user') %}
        <a href="/dashboard" class="px-4 py-1.5 rounded-full bg-indigo-500 hover:bg-indigo-600 text-xs font-semibold shadow shadow-indigo-500/40">
          {{ session.get('user') }}
        </a>
      {% else %}
        <a href="/login" class="px-4 py-1.5 rounded-full bg-indigo-500 hover:bg-indigo-600 text-xs font-semibold shadow shadow-indigo-500/40">
          Login
        </a>
      {% endif %}
    </div>
  </nav>

  <!-- PAGE CONTENT -->
  <main class="px-5 md:px-10 py-8">
    {{ content|safe }}
  </main>
</div>

</body>
</html>
"""

def render_page(content_html, title="CareerInn"):
    return render_template_string(BASE_HTML, content=content_html, title=title)

# ======================= HOME =======================
@app.route("/")
def home():
    content = """
    <div class="max-w-5xl mx-auto mt-6 md:mt-10 space-y-12 hero-shell">

      <!-- HERO -->
      <section class="grid md:grid-cols-2 gap-10 items-center">
        <!-- LEFT SIDE -->
        <div class="space-y-4">
          <span class="pill-badge">
            <span class="dot"></span>
            Hospitality careers · CareerInn
          </span>

          <h1 class="text-3xl md:text-4xl font-extrabold leading-tight">
            Plan your <span class="gradient-text">hotel &amp; hospitality</span> career in one place.
          </h1>

          <p class="text-sm md:text-[15px] text-slate-300">
            One simple yearly pass that puts colleges, mentors and jobs in a single platform.
          </p>

          <div class="flex flex-wrap items-center gap-4 mt-3">
            <a href="/signup" class="primary-cta">
              🚀 Get started – ₹299 / year
            </a>
            <a href="/login" class="ghost-cta">
              Already have an account?
            </a>
          </div>

          <p class="hero-footnote">
            ₹299 per student (demo prototype – real data can be integrated).
          </p>
        </div>

        <!-- RIGHT: STUDENT PASS CARD -->
        <div class="hero-card rounded-3xl p-6 md:p-7 space-y-4">
          <p class="text-xs text-slate-300 uppercase tracking-[0.2em]">
            Student pass
          </p>

          <div class="flex items-end gap-2">
            <span class="text-4xl font-extrabold text-emerald-300">₹299</span>
            <span class="text-xs text-slate-300 mb-2">per student / year</span>
          </div>

          <p class="text-[12px] text-slate-300">
            Students can explore hospitality careers in one simple space.
          </p>

          <ul class="text-[12px] text-slate-200 space-y-1.5 mt-3">
            <li>• College explorer along with courses</li>
            <li>• Mentor connect flow with request form</li>
            <li>• Job &amp; internship apply flow (demo only)</li>
            <li>⭐ <b>100% Guaranteed Job & Internship Guidance</b></li>
          </ul>
        </div>
      </section>

      <!-- FEATURE MODULES (NOW 7 BOXES) -->
      <section class="space-y-4">
        <h3 class="text-sm font-semibold text-slate-200">CareerInn Spaces:</h3>

        <div class="grid md:grid-cols-7 gap-4">

          <a href="/courses" class="feature-card">📘 Courses<p class="sub">Demo course access</p></a>
          <a href="/courses" class="feature-card">🏫 Colleges<p class="sub">Search & compare</p></a>
          <a href="/mentorship" class="feature-card">🧑‍🏫 Mentorship<p class="sub">Career guidance</p></a>
          <a href="/jobs" class="feature-card">💼 Jobs<p class="sub">Job listings</p></a>
          <a href="/jobs" class="feature-card">📋 Internships<p class="sub">Training roles</p></a>

          <!-- 🔥 Newly Added -->
          <a href="/global-match" class="feature-card">
            🌎 Global Match
            <p class="sub">Worldwide college + internship pairing</p>
          </a>

          <a href="/support" class="feature-card">
            🆘 24/7 Support
            <p class="sub">Anytime student assistance</p>
          </a>

        </div>
      </section>
    </div>
    """
    return render_page(content, "CareerInn | Home")


# ======================= AUTH (SIGNUP / LOGIN) =======================
SIGNUP_FORM = """
<form method="POST" class="auth-card">
  <h2 class="text-xl font-bold mb-4">Create your CareerInn account</h2>
  <input name="name" placeholder="Full Name" required class="input-box">
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn">Signup</button>
  <p class="text-gray-400 mt-3 text-sm">
    Already registered? <a href="/login" class="text-indigo-400">Login</a>
  </p>
</form>
"""

LOGIN_FORM = """
<form method="POST" class="auth-card">
  <h2 class="text-xl font-bold mb-4">Login to CareerInn</h2>
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn">Login</button>
  <p class="text-gray-400 mt-3 text-sm">
    New here? <a href="/signup" class="text-indigo-400">Create Account</a>
  </p>
</form>
"""

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                      (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_page(
                "<p class='text-red-400 text-sm mb-3'>Email already exists.</p>" + SIGNUP_FORM,
                "Signup"
            )
        conn.close()
        return redirect("/login")

    return render_page(SIGNUP_FORM, "Signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]  # name
            return redirect("/dashboard")
        else:
            return render_page(
                "<p class='text-red-400 text-sm mb-3'>Invalid email or password.</p>" + LOGIN_FORM,
                "Login"
            )

    return render_page(LOGIN_FORM, "Login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ======================= DASHBOARD =======================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    content = f"""
    <h2 class="text-3xl font-bold mb-2">Welcome {session['user']} 👋</h2>
    <p class="text-gray-300 mb-6 text-sm">
      Subscription: <span class="text-emerald-300 font-semibold">₹299 / year</span> (demo data only ...)
    </p>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
      <div class="dash-box">Students<br><span>...</span></div>
      <div class="dash-box">Colleges<br><span>...</span></div>
      <div class="dash-box">Mentors<br><span>...</span></div>
      <div class="dash-box">Jobs<br><span>...</span></div>
      <div class="dash-box">Abroad Programs<br><span>...</span></div>
      <div class="dash-box">Avg. Package<br><span>...</span></div>
    </div>
    """
    return render_page(content, "Dashboard")

# ======================= COURSES =======================
@app.route("/courses")
def courses():
    q = request.args.get("q", "").strip()
    min_fee = request.args.get("min_fee", "").strip()
    max_fee = request.args.get("max_fee", "").strip()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    query = "SELECT * FROM colleges WHERE 1=1"
    params = []

    if q:
        like = f"%{q}%"
        query += " AND (name LIKE ? OR location LIKE ?)"
        params.extend([like, like])

    # budget filter
    try:
        if min_fee:
            query += " AND fees >= ?"
            params.append(int(min_fee))
        if max_fee:
            query += " AND fees <= ?"
            params.append(int(max_fee))
    except ValueError:
        # if user types non-numeric, just ignore fee filters
        pass

    c.execute(query, params)
    data = c.fetchall()
    conn.close()

    rows = ""
    for col in data:
        rows += f"""
        <tr>
          <td>{col[1]}</td>
          <td>{col[2]}</td>
          <td>₹{col[3]:,}</td>
          <td>{col[4]}</td>
        </tr>
        """

    if not rows:
        rows = "<tr><td colspan='4'>No colleges match this search / budget yet.</td></tr>"

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Hyderabad Hotel Management Colleges</h2>

    <form method="GET" class="mb-3 grid md:grid-cols-4 gap-2 items-center">
      <input name="q" value="{q}" placeholder="Search by college or area..." class="search-bar">
      <input name="min_fee" value="{min_fee}" type="number" placeholder="Min budget (₹)" class="search-bar">
      <input name="max_fee" value="{max_fee}" type="number" placeholder="Max budget (₹)" class="search-bar">
      <button class="px-3 py-2 bg-indigo-600 rounded text-sm">Filter</button>
    </form>

    <p class="text-[11px] text-slate-400 mt-1">
      Fees shown are approximate yearly tuition for Hyderabad hotel management programmes. Students should confirm with the college website before applying.
    </p>

    <table class="table mt-2">
      <tr><th>Name</th><th>Location</th><th>Approx. Annual Fees</th><th>Placements / Notes</th></tr>
      {rows}
    </table>
    """
    return render_page(content, "Courses & Colleges")


# ======================= MENTORSHIP =======================
@app.route("/mentorship")
def mentorship():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM mentors")
    data = c.fetchall()
    conn.close()

    cards = ""
    for m in data:
        cards += f"""
        <div class="mentor-card">
          <h3 class="text-lg font-bold mb-1">{m[1]}</h3>
          <p class="text-sm text-gray-300">{m[2]}</p>
          <p class="text-sm text-indigo-300 mb-2">{m[3]}</p>
          <a href="/book-mentor/{m[0]}" class="mt-2 inline-block text-xs px-3 py-1 bg-indigo-600 rounded">
            Book Session (demo)
          </a>
        </div>
        """

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Find Mentors</h2>
    <p class="text-gray-300 mb-4 text-sm">All mentor details are placeholders (demo only ...)</p>
    <div class="grid md:grid-cols-3 gap-6">
      {cards}
    </div>
    """
    return render_page(content, "Mentorship")

@app.route("/book-mentor/<int:mentor_id>", methods=["GET", "POST"])
def book_mentor(mentor_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM mentors WHERE id=?", (mentor_id,))
    mentor = c.fetchone()
    conn.close()

    if not mentor:
        return redirect("/mentorship")

    if request.method == "POST":
        content = f"""
        <h2 class="text-2xl font-bold mb-4">Session Request Sent</h2>
        <p class="text-gray-300 mb-3 text-sm">
          Your request to connect with <span class="text-indigo-300 font-semibold">{mentor[1]}</span> has been received (demo only).
        </p>
        <a href="/mentorship" class="px-4 py-2 bg-indigo-600 rounded text-sm">Back to mentors</a>
        """
        return render_page(content, "Mentor Booking")

    content = f"""
    <h2 class="text-2xl font-bold mb-4">Book Mentor Session</h2>
    <p class="text-gray-300 mb-4 text-sm">
      Mentor: <span class="text-indigo-300 font-semibold">{mentor[1]}</span> (details ...).
    </p>
    <form method="POST" class="auth-card">
      <input name="student_name" placeholder="Your name ..." class="input-box">
      <input name="student_email" placeholder="Your email ..." class="input-box">
      <input name="preferred_time" placeholder="Preferred time slot ..." class="input-box">
      <button class="submit-btn">Request Session (demo)</button>
    </form>
    """
    return render_page(content, "Book Mentor")

# ======================= JOBS =======================
@app.route("/jobs")
def jobs():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs")
    data = c.fetchall()
    conn.close()

    cards = ""
    for j in data:
        cards += f"""
        <div class="job-card">
          <h3 class="font-bold text-lg mb-1">{j[1]}</h3>
          <p class="text-indigo-300 text-sm">{j[2]}</p>
          <p class="text-gray-400 text-sm">{j[3]}</p>
          <p class="text-green-300 font-bold text-sm mb-2">{j[4]}</p>
          <a href="/apply-job/{j[0]}" class="mt-2 inline-block text-xs px-3 py-1 bg-emerald-600 rounded">
            Apply (demo)
          </a>
        </div>
        """

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Job Opportunities</h2>
    <p class="text-gray-300 mb-4 text-sm">All job titles and companies are placeholders (demo ...)</p>
    <div class="grid md:grid-cols-3 gap-6">
      {cards}
    </div>
    """
    return render_page(content, "Jobs & Internships")

@app.route("/apply-job/<int:job_id>", methods=["GET", "POST"])
def apply_job(job_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
    job = c.fetchone()
    conn.close()

    if not job:
        return redirect("/jobs")

    if request.method == "POST":
        content = f"""
        <h2 class="text-2xl font-bold mb-4">Application Submitted</h2>
        <p class="text-gray-300 mb-3 text-sm">
          Your demo application for <span class="text-indigo-300 font-semibold">{job[1]}</span> at {job[2]} has been recorded.
        </p>
        <a href="/jobs" class="px-4 py-2 bg-indigo-600 rounded text-sm">Back to jobs</a>
        """
        return render_page(content, "Job Application")

    content = f"""
    <h2 class="text-2xl font-bold mb-4">Apply for Job</h2>
    <p class="text-gray-300 mb-4 text-sm">
      Role: <span class="text-indigo-300 font-semibold">{job[1]}</span> at {job[2]} (details ...).
    </p>
    <form method="POST" class="auth-card" enctype="multipart/form-data">
      <input name="name" placeholder="Your name ..." class="input-box">
      <input name="email" placeholder="Your email ..." class="input-box">
      <input name="phone" placeholder="Phone number ..." class="input-box">
      <input type="file" name="resume" class="input-box">
      <button class="submit-btn">Submit Application (demo)</button>
    </form>
    """
    return render_page(content, "Apply Job")

# ======================= SUPPORT =======================
@app.route("/support")
def support():
    content = """
    <h2 class="text-3xl font-bold mb-6">Support &amp; Help</h2>
    <p class="mb-4 text-gray-300">Need assistance? Contact us anytime.</p>
    <div class="support-box">
      <p>📧 support@careerinn.com</p>
      <p>📞 +91 98... ... ...</p>
    </div>
    """
    return render_page(content, "Support")

# ======================= MAIN =======================
if __name__ == "__main__":
    app.run(debug=True)
