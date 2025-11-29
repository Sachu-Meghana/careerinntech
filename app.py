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

    # seed placeholder data
    c.execute("SELECT COUNT(*) FROM colleges")
    if c.fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO colleges(name,location,fees,placements) VALUES(?,?,?,?)",
            [
                ("College ... A", "Location ...", 299000, "Placement ..."),
                ("College ... B", "Location ...", 310000, "Placement ..."),
                ("College ... C", "Location ...", 280000, "Placement ...")
            ]
        )

    c.execute("SELECT COUNT(*) FROM mentors")
    if c.fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO mentors(name,experience,speciality) VALUES(?,?,?)",
            [
                ("Mentor ... A", "Experience ...", "Speciality ..."),
                ("Mentor ... B", "Experience ...", "Speciality ..."),
                ("Mentor ... C", "Experience ...", "Speciality ...")
            ]
        )

    c.execute("SELECT COUNT(*) FROM jobs")
    if c.fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO jobs(title,company,location,salary) VALUES(?,?,?,?)",
            [
                ("Job ... A", "Company ...", "Location ...", "Salary ..."),
                ("Job ... B", "Company ...", "Location ...", "Salary ..."),
                ("Job ... C", "Company ...", "Location ...", "Salary ...")
            ]
        )

    conn.commit()
    conn.close()

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


# ======================= HOME (CLEAN V2) =======================
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
            ₹299 per student.
          </p>
        </div>

        <!-- RIGHT: SIMPLE CARD -->
        <div class="hero-card rounded-3xl p-6 md:p-7 space-y-4">
          <p class="text-xs text-slate-300 uppercase tracking-[0.2em]">
            Student pass
          </p>
          <div class="flex items-end gap-2">
            <span class="text-4xl font-extrabold text-emerald-300">₹299</span>
            <span class="text-xs text-slate-300 mb-2">per student / year</span>
          </div>
          <p class="text-[12px] text-slate-300">
            Students can explore hospitality careers at one place.
          </p>
          <ul class="text-[12px] text-slate-200 space-y-1.5 mt-3">
            <li>• College explorer along with courses</li>
            <li>• Mentor connect flow with request form</li>
            <li>• Job &amp; internship apply form</li>
          </ul>
        </div>
      </section>

      <!-- 3 FEATURE CARDS -->
      <section class="space-y-4">
        <h3 class="text-sm font-semibold text-slate-200">Core spaces inside CareerInn:</h3>
        <div class="grid md:grid-cols-3 gap-4">
          <a href="/courses" class="feature-card">
            🎓 Courses &amp; Colleges
            <p class="sub">Browse hotel management colleges.</p>
          </a>
          <a href="/mentorship" class="feature-card">
            🧑‍🏫 Mentors
            <p class="sub">View mentors &amp; try the booking request.</p>
          </a>
          <a href="/jobs" class="feature-card">
            💼 Jobs &amp; Internships
            <p class="sub">Open roles &amp; go through the apply form.</p>
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
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if q:
        like = f"%{q}%"
        c.execute("SELECT * FROM colleges WHERE name LIKE ? OR location LIKE ?", (like, like))
    else:
        c.execute("SELECT * FROM colleges")
    data = c.fetchall()
    conn.close()

    rows = ""
    for col in data:
        rows += f"""
        <tr>
          <td>{col[1]}</td>
          <td>{col[2]}</td>
          <td>₹{col[3]}</td>
          <td>{col[4]}</td>
        </tr>
        """

    content = f"""
    <h2 class="text-3xl font-bold mb-4">College &amp; Course Explorer</h2>
    <form method="GET" class="mb-3 flex gap-2 items-center">
      <input name="q" value="{q}" placeholder="Search by name or location..." class="search-bar">
      <button class="px-3 py-2 bg-indigo-600 rounded text-sm">Search</button>
    </form>
    <table class="table">
      <tr><th>Name</th><th>Location</th><th>Fees</th><th>Placements</th></tr>
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
# ------------------- MAIN -------------------
# ======================= MAIN =======================

from flask import Flask

@app.before_first_request
def setup_db():
    init_db()       # Ensures DB & tables exist on Render + Local

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


