import os
from werkzeug.security import generate_password_hash, check_password_hash

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
)
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from groq import Groq

# -------------------- FLASK + GROQ SETUP --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "careerinn_secure_key")


def get_groq_client():
    """Create a Groq client when needed."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


# -------------------- DB SETUP (POSTGRES / SQLITE) --------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careerinn.db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # unique + index so we can’t have same email twice
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)


class College(Base):
    __tablename__ = "colleges"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    fees = Column(Integer, nullable=False)
    course = Column(String(255), nullable=False)
    rating = Column(Float, nullable=False)


class Mentor(Base):
    __tablename__ = "mentors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    experience = Column(Text, nullable=False)
    speciality = Column(String(255), nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    salary = Column(String(255), nullable=False)


class AiUsage(Base):
    """
    Tracks if a user has already used their free AI chat.
    One row per user_id.
    """
    __tablename__ = "ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    ai_used = Column(Integer, nullable=False, default=0)


class UserProfile(Base):
    """
    Simple user dashboard profile:
    - skills_text: what they know
    - target_roles: what they want
    - self_rating: 0–5 rating
    - resume_link: Drive / resume URL
    - notes: extra notes
    """
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    skills_text = Column(Text, nullable=True)
    target_roles = Column(Text, nullable=True)
    self_rating = Column(Integer, nullable=False, default=0)
    resume_link = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)


def get_db():
    return SessionLocal()


def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    # -------- seed colleges if empty --------
    if db.query(College).count() == 0:
        colleges_seed = [
            ("IHM Hyderabad (IHMH)", "DD Colony, Hyderabad", 320000,
             "BSc in Hospitality & Hotel Administration", 4.6),
            ("NITHM Hyderabad", "Gachibowli, Hyderabad", 280000,
             "BBA in Tourism & Hospitality", 4.3),
            ("IIHM Hyderabad", "Somajiguda, Hyderabad", 350000,
             "BA in Hospitality Management", 4.5),
            ("Regency College of Culinary Arts & Hotel Management", "Himayatnagar, Hyderabad", 240000,
             "BHM & Culinary Arts", 4.4),
            ("IHM Shri Shakti", "Kompally, Hyderabad", 260000,
             "BSc Hotel Management & Catering", 4.2),
            ("Chennais Amirta IHM – Hyderabad", "Khairatabad, Hyderabad", 180000,
             "Diploma in Hotel Management", 4.0),
            ("Westin College of Hotel Management", "Nizampet, Hyderabad", 190000,
             "Bachelor of Hotel Management (BHM)", 3.9),
            ("Malla Reddy University – Hotel Management", "Maisammaguda, Hyderabad", 210000,
             "BSc Hotel Management", 4.1),
            ("SIITAM Hyderabad", "Tarnaka, Hyderabad", 170000,
             "BHM", 3.8),
            ("Zest College of Hotel Management", "Hyderabad", 90000,
             "Diploma in Hotel Management", 3.7),
            ("Roots Collegium – Hotel Management", "Somajiguda, Hyderabad", 200000,
             "BBA in Hotel Management", 4.0),
            ("Aptech Aviation & Hospitality – Hyderabad", "Ameerpet, Hyderabad", 85000,
             "Diploma in Aviation & Hospitality", 3.6),
            ("St. Mary’s College – Hospitality", "Yousufguda, Hyderabad", 140000,
             "BVoc Hospitality & Tourism", 3.9),
            ("Aurora’s Degree College – Hotel Management", "Chikkadpally, Hyderabad", 160000,
             "BHM", 3.8),
            ("Global College of Hotel Management", "Kukatpally, Hyderabad", 95000,
             "Diploma in Hotel Operations", 3.7),
        ]
        for name, loc, fees, course, rating in colleges_seed:
            db.add(College(
                name=name,
                location=loc,
                fees=fees,
                course=course,
                rating=rating
            ))

    # -------- seed mentors if empty (demo) --------
    if db.query(Mentor).count() == 0:
        mentors_seed = [
            ("Mentor ... A", "Industry experience ...", "Hotel Ops / Front Office"),
            ("Mentor ... B", "Industry experience ...", "Culinary / F&B"),
            ("Mentor ... C", "Industry experience ...", "Abroad & Cruise guidance"),
        ]
        for n, exp, spec in mentors_seed:
            db.add(Mentor(name=n, experience=exp, speciality=spec))

    # -------- seed jobs as placements snapshot --------
    if db.query(Job).count() == 0:
        jobs_seed = [
            ("IHM Hyderabad – Management Trainee (Hotel Ops)",
             "Taj / IHCL", "Pan India", "Avg package ~₹4.5–5.5 LPA"),
            ("IHM Hyderabad – F&B Associate",
             "Marriott Hotels", "Hyderabad / Bengaluru", "Avg package ~₹3–4 LPA"),
            ("NITHM – Guest Relations Executive",
             "ITC Hotels", "Hyderabad", "Avg package ~₹3.5–4.5 LPA"),
            ("IIHM Hyderabad – Hospitality Management Trainee",
             "Accor Hotels", "Pan India / Overseas", "Avg package ~₹4–6 LPA (varies)"),
            ("Regency College – Commis Chef",
             "5-star Hotels & QSR chains", "Hyderabad", "Avg package ~₹2.5–3.5 LPA"),
            ("IHM Shri Shakti – Front Office Associate",
             "Oberoi / Trident", "Metro cities", "Avg package ~₹3.5–4.5 LPA"),
            ("Westin College – Hotel Operations Trainee",
             "Hyatt Hotels", "Pan India", "Avg package ~₹3–4 LPA"),
            ("Malla Reddy Univ – Hospitality Roles",
             "Resorts & Cruise Lines", "India / Overseas", "Avg package ~₹3–6 LPA (role based)"),
            ("Roots Collegium – Hospitality Placement",
             "Retail & Hospitality Chains", "Hyderabad", "Avg package ~₹2.5–3.5 LPA"),
        ]
        for t, c_, loc, sal in jobs_seed:
            db.add(Job(title=t, company=c_, location=loc, salary=sal))

    db.commit()
    db.close()


@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()


# initialize db on startup
init_db()

# -------------------- AI SYSTEM PROMPT --------------------
AI_SYSTEM_PROMPT = """
You are CareerInn's AI career guide for hospitality and hotel management in Hyderabad.

Your job:
- Talk like a friendly senior / mentor.
- Ask the student structured questions step by step, not all at once.

Ask in this order (one or two at a time, in separate turns):
1) Name and current education (10th/12th/degree, stream, completion year).
2) Marks / percentage in 10th and 12th (or diploma).
3) Budget per year for fees (approx) and whether they are okay with loans.
4) Preference: Hyderabad only, Telangana, India, or abroad later.
5) Interest area: front office, F&B service, culinary/chef, bakery, housekeeping, cruise, aviation, tourism, etc.
6) Comfort with long working hours, shifts, and relocations.
7) If they want quick job after 3 years or long-term growth / abroad.

Then:
- Use their budget + preference to suggest 3–5 suitable college/path options.
- Focus on hospitality / hotel management in Hyderabad and similar.
- Talk in ranges for fees (low / mid / high), not exact rupees.
- Mention general college examples like:
  IHM Hyderabad, NITHM, IIHM Hyderabad, Regency, IHM Shri Shakti, Westin, Malla Reddy University, etc.
- You do NOT need exact course details, only guidance-level advice.

Very important:
- Make it clear this is guidance, not final admission advice.
- At the end of a recommendation block, clearly say:
  "To turn this into a clear plan for you, please connect to a CareerInn mentor from the Mentorship section."

Style:
- Short paragraphs, simple English, friendly tone.
- Do NOT talk about being an AI model.
"""

# -------------------- BASE LAYOUT --------------------
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
      
      <!-- LOGO + TITLE -->
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center shadow-lg shadow-indigo-500/40 overflow-hidden">
          <img src="/static/logo.png" class="w-11 h-11 object-contain" alt="CareerInn logo">
        </div>
        <div>
          <p class="font-bold text-lg md:text-xl tracking-tight">CareerInn</p>
          <p class="text-[11px] text-slate-400">Hospitality Careers · Colleges · Jobs</p>
        </div>
      </div>

      <!-- NAV LINKS -->
      <div class="hidden md:flex items-center gap-6 text-sm">
          <a href="/" class="hover:text-indigo-400">Home</a>
          <a href="/courses" class="hover:text-indigo-400">Courses</a>
          <a href="/mentorship" class="hover:text-indigo-400">Mentorship</a>
          <a href="/jobs" class="hover:text-indigo-400">Jobs</a>
          <a href="/global-match" class="hover:text-indigo-400">Global Match</a>
          <a href="/chatbot" class="hover:text-indigo-400">AI Career Bot</a>
          <a href="/support" class="hover:text-indigo-400">Support</a>

          {% if session.get('user') %}
            <a href="/dashboard" class="px-3 py-1.5 text-[13px] text-slate-300 border border-slate-700 rounded-full hover:bg-slate-800">
              Hi, {{ session.get('user') }}
            </a>
            <a href="/logout" class="px-4 py-1.5 rounded-full bg-rose-500 hover:bg-rose-600 text-xs font-semibold shadow shadow-rose-500/40">
              Logout
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


# -------------------- HOME (dynamic CTA using DB usage) --------------------
@app.route("/")
def home():
    # default: AI not used
    ai_used = False

    # If logged in, read from DB so it works across devices
    user_id = session.get("user_id")
    if user_id:
        db = get_db()
        usage = db.query(AiUsage).filter_by(user_id=user_id).first()
        db.close()
        if usage and usage.ai_used >= 1:
            ai_used = True
            session["ai_used"] = True

    if not ai_used:
        cta_html = """
          <div class="flex flex-wrap items-center gap-3 mt-3">
            <a href="/signup" class="primary-cta">Create free account</a>
            <a href="/login" class="ghost-cta">Sign in</a>
            <a href="/chatbot" class="px-4 py-2 rounded-full border border-emerald-400/70 text-xs md:text-sm hover:bg-emerald-500/10">
              🤖 Try free AI career chat
            </a>
          </div>
          <p class="hero-footnote">First AI chat is free after login. After that, guidance continues inside the ₹299/year pass.</p>
        """
    else:
        cta_html = """
          <div class="flex flex-wrap items-center gap-4 mt-3">
            <a href="/signup" class="primary-cta">
              🚀 Get started – ₹299 / year
            </a>
            <a href="/login" class="ghost-cta">
              Already have an account?
            </a>
            <a href="/chatbot" class="px-4 py-2 rounded-full border border-emerald-400/70 text-xs md:text-sm hover:bg-emerald-500/10">
              🤖 Continue with AI guidance
            </a>
          </div>
          <p class="hero-footnote">
            ₹299 per student (prototype – real data & payments can plug in later).
          </p>
        """

    content = f"""
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
            One simple yearly pass that puts colleges, mentors, jobs and an AI career guide in a single platform.
          </p>

          {cta_html}
        </div>

        <!-- RIGHT: BIGGER STUDENT PASS CARD -->
        <div class="hero-card rounded-3xl p-7 md:p-9 space-y-5">
          <p class="text-sm text-slate-300 uppercase tracking-[0.22em]">
            Student pass
          </p>

          <div class="flex items-end gap-3">
            <span class="text-5xl font-extrabold text-emerald-300">₹299</span>
            <span class="text-sm text-slate-300 mb-2">per student / year</span>
          </div>

          <p class="text-[13px] md:text-sm text-slate-300">
            Students can explore hospitality careers, compare colleges, and get mentor &amp; AI guidance in one simple space.
          </p>

          <ul class="text-sm text-slate-200 space-y-1.5 mt-3">
            <li>• Hyderabad hotel-management courses &amp; colleges</li>
            <li>• Mentor connect flow with request form</li>
            <li>• Job &amp; internship placements snapshot</li>
            <li>• AI-based college &amp; path suggestion chat</li>
            <li>⭐ <b>100% Job &amp; Internship Guidance (with mentors)</b></li>
          </ul>
        </div>
      </section>

      <!-- FEATURE CARDS -->
      <section class="space-y-4">
        <h3 class="text-sm font-semibold text-slate-200">CareerInn Spaces:</h3>

        <div class="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <a href="/courses" class="feature-card">
            📘 Courses
            <p class="sub">See key hospitality courses.</p>
          </a>

          <a href="/courses" class="feature-card">
            🏫 Colleges
            <p class="sub">Hyderabad hotel-management colleges.</p>
          </a>

          <a href="/mentorship" class="feature-card">
            🧑‍🏫 Mentorship
            <p class="sub">Talk to hospitality mentors (demo).</p>
          </a>

          <a href="/jobs" class="feature-card">
            💼 Jobs &amp; Placements
            <p class="sub">Avg packages &amp; recruiters snapshot.</p>
          </a>

          <a href="/global-match" class="feature-card">
            🌍 Global Match
            <p class="sub">Abroad colleges &amp; internships overview.</p>
          </a>

          <a href="/chatbot" class="feature-card">
            🤖 AI Career Bot
            <p class="sub">Chat to get a suggested path.</p>
          </a>
        </div>
      </section>
    </div>
    """
    return render_page(content, "CareerInn | Home")


# -------------------- CHATBOT TEMPLATE --------------------
CHATBOT_HTML = """
<div class="max-w-3xl mx-auto space-y-6">
  <h1 class="text-3xl font-bold mb-2">CareerInn AI Mentor</h1>

  {% if not locked %}
    <p class="text-sm text-slate-300 mb-4">
      This AI bot will ask about your marks, budget, interests and city preference,
      suggest a hospitality path &amp; colleges in Hyderabad, and finally ask you
      to connect with a human mentor. You get <b>one free full chat session.</b>
    </p>
  {% else %}
    <p class="text-sm text-slate-300 mb-4">
      Your <b>free AI career chat is finished</b> for this account.
      Please purchase the ₹299/year Student Pass and connect with a mentor
      for more guidance.
    </p>
  {% endif %}

  <!-- Reset view (only resets messages on screen, not the free lock) -->
  <form method="GET" action="/chatbot" class="mb-3">
    <input type="hidden" name="reset" value="1">
    <button class="px-3 py-1 rounded-full border border-slate-600 text-[11px] hover:bg-slate-800">
      🔄 Clear chat on screen
    </button>
  </form>

  <div class="bg-slate-900/80 border border-slate-700 rounded-2xl p-4 h-[420px] overflow-y-auto mb-4">
    {% if history %}
      {% for m in history %}
        <div class="mb-3">
          {% if m.role == 'user' %}
            <div class="text-xs text-slate-400 mb-0.5">You</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-indigo-600 text-xs md:text-sm max-w-[90%]">
              {{ m.content }}
            </div>
          {% else %}
            <div class="text-xs text-slate-400 mb-0.5">CareerInn AI</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-slate-800 text-xs md:text-sm max-w-[90%]">
              {{ m.content }}
            </div>
          {% endif %}
        </div>
      {% endfor %}
    {% else %}
      <p class="text-sm text-slate-400">
        👋 Hi! I’m CareerInn AI. Tell me your name and your latest class (10th / 12th / degree),
        and approximate marks. I’ll ask a few quick questions and suggest a path + college for you.
      </p>
    {% endif %}
  </div>

  {% if not locked %}
    <!-- Chat input when free session is active -->
    <form method="POST" class="flex gap-2">
      <input
        name="message"
        autocomplete="off"
        placeholder="Type your message here..."
        class="flex-1 input-box"
        required
      >
      <button class="px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold">
        Send
      </button>
    </form>

    <!-- End & lock button (POST) -->
    <form method="POST" action="/chatbot/end" class="mt-3">
      <button class="px-3 py-1.5 text-[11px] rounded-full border border-rose-500/70 text-rose-200 hover:bg-rose-500/10">
        🔒 End &amp; lock free AI chat
      </button>
    </form>
  {% else %}
    <!-- After lock -->
    <p class="text-xs text-slate-400 mt-2">
      Tip: Go back to the Home page to see the Student Pass and connect with mentors.
    </p>
  {% endif %}
</div>
"""

# -------------------- AUTH (SIGNUP / LOGIN) --------------------
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

        if not name or not email or not password:
            return render_page(
                "<p class='text-red-400 text-sm mb-3'>All fields are required.</p>" + SIGNUP_FORM,
                "Signup"
            )

        db = get_db()

        # block duplicate emails
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.close()
            return render_page(
                "<p class='text-red-400 text-sm mb-3'>An account with this email already exists. Please login.</p>"
                + SIGNUP_FORM,
                "Signup"
            )

        # store hashed password, NOT plain text
        hashed_password = generate_password_hash(
            password,
            method="pbkdf2:sha256",
            salt_length=16
        )

        user = User(name=name, email=email, password=hashed_password)
        db.add(user)
        db.commit()
        db.close()

        return redirect("/login")

    return render_page(SIGNUP_FORM, "Signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.query(User).filter(User.email == email).first()
        db.close()

        authenticated = False
        if user:
            # try hashed first
            try:
                authenticated = check_password_hash(user.password, password)
            except ValueError:
                # fallback if old plain-text passwords exist
                authenticated = (user.password == password)

        if authenticated:
            session["user"] = user.name
            session["user_id"] = user.id
            session["ai_history"] = []  # reset chat history
            return redirect("/dashboard")  # go to DASHBOARD after login

        return render_page(
            "<p class='text-red-400 text-sm mb-3'>Invalid email or password.</p>" + LOGIN_FORM,
            "Login"
        )

    return render_page(LOGIN_FORM, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------- USER DASHBOARD (PROFILE) --------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    user_name = session["user"]

    # which tab?
    tab = request.args.get("tab")
    if request.method == "POST":
        tab = request.form.get("tab", tab)
    if not tab:
        tab = "home"

    db = get_db()
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile is None:
        profile = UserProfile(
            user_id=user_id,
            skills_text="",
            target_roles="",
            self_rating=0,
            resume_link="",
            notes=""
        )
        db.add(profile)
        db.commit()

    # handle form saves
    if request.method == "POST":
        if tab == "skills":
            profile.skills_text = request.form.get("skills_text", "").strip()
            profile.target_roles = request.form.get("target_roles", "").strip()
            rating_val = request.form.get("self_rating", "").strip()
            try:
                profile.self_rating = int(rating_val) if rating_val else 0
            except ValueError:
                profile.self_rating = 0
            db.commit()
            db.close()
            return redirect("/dashboard?tab=skills")

        if tab == "resume":
            profile.resume_link = request.form.get("resume_link", "").strip()
            profile.notes = request.form.get("notes", "").strip()
            db.commit()
            db.close()
            return redirect("/dashboard?tab=resume")

    skills_text = profile.skills_text or ""
    target_roles = profile.target_roles or ""
    self_rating = profile.self_rating or 0
    resume_link = profile.resume_link or ""
    notes = profile.notes or ""
    db.close()

    base_tab_cls = "px-4 py-2 rounded-full text-xs md:text-sm border border-slate-700 hover:bg-slate-800"
    def cls(name):
        return (
            base_tab_cls + " bg-indigo-600 text-white border-indigo-500"
            if tab == name
            else base_tab_cls + " text-slate-300"
        )

    # panels
    home_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Welcome back, {user_name} 👋</h2>
        <p class="text-sm text-slate-300">
          This is your personal hospitality dashboard. Track your skills, upload your resume link,
          and see how ready you are for hotel &amp; hospitality careers.
        </p>

        <div class="grid md:grid-cols-3 gap-4 mt-4">
          <div class="dash-box">
            <p class="text-xs text-slate-400">Career readiness rating</p>
            <p class="text-2xl font-bold mt-1">{self_rating}/5</p>
          </div>
          <div class="dash-box">
            <p class="text-xs text-slate-400">Target roles set</p>
            <p class="text-2xl font-bold mt-1">
              {"Yes" if target_roles else "No"}
            </p>
          </div>
          <div class="dash-box">
            <p class="text-xs text-slate-400">Resume link added</p>
            <p class="text-2xl font-bold mt-1">
              {"Yes" if resume_link else "No"}
            </p>
          </div>
        </div>

        <div class="mt-6 bg-slate-900/70 border border-slate-700 rounded-2xl p-4">
          <h3 class="font-semibold mb-2">Quick tips</h3>
          <ul class="text-xs md:text-sm text-slate-300 space-y-1.5">
            <li>• Use the <b>Skills</b> tab to list your current skills and areas to improve.</li>
            <li>• Paste your <b>Google Drive / PDF resume link</b> inside the <b>Resume</b> tab.</li>
            <li>• Chat with the <b>AI Career Bot</b> once, then talk to mentors for final guidance.</li>
          </ul>
        </div>
      </div>
    """

    mentors_panel = """
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Mentor connections 🧑‍🏫</h2>
        <p class="text-sm text-slate-300">
          CareerInn mentors help you understand real hotel shifts, growth paths and how to build a strong CV.
        </p>

        <div class="grid md:grid-cols-2 gap-4 mt-4">
          <div class="support-box">
            <h3 class="font-semibold mb-2">How mentors help</h3>
            <ul class="text-xs md:text-sm text-slate-200 space-y-1.5">
              <li>• Reviewing your resume and skills.</li>
              <li>• Suggesting best-fit colleges for your budget.</li>
              <li>• Mock interview prep for hotel roles.</li>
              <li>• Abroad / cruise and internship guidance.</li>
            </ul>
          </div>
          <div class="support-box">
            <h3 class="font-semibold mb-2">Next step</h3>
            <p class="text-xs md:text-sm text-slate-200 mb-2">
              Once your Skills and Resume tabs look ready, book a demo mentor slot from the Mentorship page.
            </p>
            <a href="/mentorship" class="inline-block mt-2 px-4 py-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold">
              View mentors
            </a>
          </div>
        </div>
      </div>
    """

    skills_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Skills &amp; strengths ⭐</h2>
        <p class="text-sm text-slate-300">
          Be honest here. This helps mentors and yourself see where you stand for hospitality careers.
        </p>

        <form method="POST" class="space-y-4 mt-4">
          <input type="hidden" name="tab" value="skills">

          <div>
            <label class="block text-xs text-slate-300 mb-1">Current skills (English, communication, cooking, customer service, etc.)</label>
            <textarea name="skills_text" rows="4" class="input-box h-auto" placeholder="Example: Good English speaking, basic MS Office, love cooking, some event management at college.">{skills_text}</textarea>
          </div>

          <div>
            <label class="block text-xs text-slate-300 mb-1">Target roles in hospitality</label>
            <textarea name="target_roles" rows="3" class="input-box h-auto" placeholder="Example: Front office executive, F&amp;B service, commis chef, cruise jobs.">{target_roles}</textarea>
          </div>

          <div class="grid md:grid-cols-2 gap-4 items-center">
            <div>
              <label class="block text-xs text-slate-300 mb-1">Rate your overall readiness (0–5)</label>
              <input name="self_rating" type="number" min="0" max="5" value="{self_rating}" class="input-box" />
            </div>
            <p class="text-[11px] text-slate-400">
              This is just a self-check. Mentors can adjust this after talking with you.
            </p>
          </div>

          <button class="submit-btn mt-2">Save skills</button>
        </form>
      </div>
    """

    rating_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Career rating overview 📊</h2>
        <p class="text-sm text-slate-300">
          This is a simple snapshot of how ready you feel right now for hospitality education and jobs.
        </p>

        <div class="mt-4 bg-slate-900/70 border border-slate-700 rounded-2xl p-4 space-y-3">
          <p class="text-xs text-slate-400">Self-rating (0–5)</p>
          <div class="flex items-center gap-3">
            <div class="flex gap-1">
              {''.join('<span>⭐</span>' for _ in range(self_rating))}
              {''.join('<span class="text-slate-600">⭐</span>' for _ in range(5 - self_rating))}
            </div>
            <span class="text-sm text-slate-200">{self_rating}/5</span>
          </div>
          <p class="text-xs text-slate-400 mt-2">
            Tip: If your rating is below 3, focus on English, grooming and basic communication.
            If 3 or above, start short internships, hotel visits and part-time exposure.
          </p>
        </div>
      </div>
    """

    resume_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Resume &amp; profile link 📄</h2>
        <p class="text-sm text-slate-300">
          Upload your resume to Google Drive / any cloud, keep it public or shareable, and paste the link here.
        </p>

        <form method="POST" class="space-y-4 mt-4">
          <input type="hidden" name="tab" value="resume">

          <div>
            <label class="block text-xs text-slate-300 mb-1">Resume link (Google Drive / PDF link)</label>
            <input name="resume_link" class="input-box" placeholder="https://drive.google.com/..." value="{resume_link}">
          </div>

          <div>
            <label class="block text-xs text-slate-300 mb-1">Notes for mentor (optional)</label>
            <textarea name="notes" rows="3" class="input-box h-auto" placeholder="Anything important mentors should know about your situation, gaps, or goals.">{notes}</textarea>
          </div>

          <button class="submit-btn mt-2">Save resume details</button>
        </form>

        {"<p class='text-xs text-emerald-300 mt-2'>Current resume link: <a href='" + resume_link + "' target='_blank' class='underline'>" + resume_link + "</a></p>" if resume_link else ""}
      </div>
    """

    faqs_panel = """
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">FAQs ❓</h2>
        <div class="space-y-3 text-sm text-slate-200">
          <div>
            <p class="font-semibold">1. Is ₹299 / year a real payment?</p>
            <p class="text-slate-300 text-xs">
              Right now this is a prototype. The amount is shown as a sample subscription and payment is not live yet.
            </p>
          </div>
          <div>
            <p class="font-semibold">2. Are these college details 100% official?</p>
            <p class="text-slate-300 text-xs">
              No. Fees, ratings and packages here are approximate guidance for hospitality planning.
              Always confirm directly with each college before applying.
            </p>
          </div>
          <div>
            <p class="font-semibold">3. Will mentors guarantee a job?</p>
            <p class="text-slate-300 text-xs">
              No one can guarantee a job. Mentors help with clarity, profile building and connecting you
              to better opportunities and preparation.
            </p>
          </div>
          <div>
            <p class="font-semibold">4. Can I use the AI bot multiple times?</p>
            <p class="text-slate-300 text-xs">
              Right now, each account gets <b>one</b> free AI career chat session.
              After that you’ll need to upgrade to a paid plan once it is live.
            </p>
          </div>
        </div>
      </div>
    """

    about_panel = """
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">About CareerInn 🏨</h2>
        <p class="text-sm text-slate-300">
          CareerInn is built for students who are serious about hospitality and hotel careers,
          but feel lost between colleges, agents and random advice.
        </p>

        <div class="grid md:grid-cols-2 gap-4 mt-3">
          <div class="support-box">
            <h3 class="font-semibold mb-2">What we want to solve</h3>
            <ul class="text-xs md:text-sm text-slate-200 space-y-1.5">
              <li>• Confusion about which hotel management college to choose.</li>
              <li>• No clear view of fees, packages and recruiters.</li>
              <li>• Lack of honest guidance on real hotel work life.</li>
              <li>• Random decisions about abroad and internships.</li>
            </ul>
          </div>
          <div class="support-box">
            <h3 class="font-semibold mb-2">What this dashboard gives you</h3>
            <ul class="text-xs md:text-sm text-slate-200 space-y-1.5">
              <li>• One place to track your skills and goals.</li>
              <li>• A simple resume link that mentors can review.</li>
              <li>• AI plus human guidance for hospitality planning.</li>
            </ul>
          </div>
        </div>
      </div>
    """

    if tab == "home":
        panel_html = home_panel
    elif tab == "mentors":
        panel_html = mentors_panel
    elif tab == "skills":
        panel_html = skills_panel
    elif tab == "rating":
        panel_html = rating_panel
    elif tab == "resume":
        panel_html = resume_panel
    elif tab == "faqs":
        panel_html = faqs_panel
    else:
        panel_html = about_panel

    content = f"""
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="text-xs text-slate-400">Profile · Hotel &amp; Hospitality</p>
          <h1 class="text-2xl md:text-3xl font-bold">Student Dashboard</h1>
        </div>
      </div>

      <!-- DASHBOARD TABS -->
      <div class="flex flex-wrap gap-2 mt-2">
        <a href="/dashboard?tab=home" class="{cls('home')}">Home</a>
        <a href="/dashboard?tab=mentors" class="{cls('mentors')}">Mentors</a>
        <a href="/dashboard?tab=skills" class="{cls('skills')}">Skills</a>
        <a href="/dashboard?tab=rating" class="{cls('rating')}">Rating</a>
        <a href="/dashboard?tab=resume" class="{cls('resume')}">Resume</a>
        <a href="/dashboard?tab=faqs" class="{cls('faqs')}">FAQs</a>
        <a href="/dashboard?tab=about" class="{cls('about')}">About us</a>
      </div>

      <div class="mt-4 bg-slate-900/70 border border-slate-800 rounded-2xl p-5 md:p-6">
        {panel_html}
      </div>
    </div>
    """
    return render_page(content, "Dashboard")


# -------------------- COURSES (budget + rating filters) --------------------
@app.route("/courses")
def courses():
    budget = request.args.get("budget", "").strip()
    rating_min = request.args.get("rating", "").strip()

    db = get_db()
    query = db.query(College)

    if budget == "lt1":
        query = query.filter(College.fees < 100000)
    elif budget == "b2_3":
        query = query.filter(College.fees.between(200000, 300000))
    elif budget == "gt3":
        query = query.filter(College.fees > 300000)

    if rating_min:
        try:
            rating_val = float(rating_min)
            query = query.filter(College.rating >= rating_val)
        except ValueError:
            pass

    data = query.order_by(College.rating.desc()).all()
    db.close()

    rows = ""
    for col in data:
        rows += f"""
        <tr>
          <td>{col.name}</td>
          <td>{col.course}</td>
          <td>{col.location}</td>
          <td>₹{col.fees:,}</td>
          <td>{col.rating:.1f}★</td>
        </tr>
        """

    if not rows:
        rows = "<tr><td colspan='5'>No colleges match this budget / rating yet.</td></tr>"

    sel_lt1   = "selected" if budget == "lt1" else ""
    sel_b2_3  = "selected" if budget == "b2_3" else ""
    sel_gt3   = "selected" if budget == "gt3" else ""
    sel_any_b = "selected" if budget == "" else ""

    sel_r_any = "selected" if rating_min == "" else ""
    sel_r_35  = "selected" if rating_min == "3.5" else ""
    sel_r_40  = "selected" if rating_min == "4.0" else ""
    sel_r_45  = "selected" if rating_min == "4.5" else ""

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Hyderabad Hotel Management – Courses &amp; Colleges</h2>

    <form method="GET" class="mb-3 grid md:grid-cols-3 gap-3 items-center">

      <!-- Budget filter -->
      <select name="budget" class="search-bar">
        <option value="" {sel_any_b}>Any budget</option>
        <option value="lt1" {sel_lt1}>Below ₹1,00,000</option>
        <option value="b2_3" {sel_b2_3}>₹2,00,000 – ₹3,00,000</option>
        <option value="gt3" {sel_gt3}>Above ₹3,00,000</option>
      </select>

      <!-- Rating filter -->
      <select name="rating" class="search-bar">
        <option value="" {sel_r_any}>Any rating</option>
        <option value="3.5" {sel_r_35}>3.5★ &amp; above</option>
        <option value="4.0" {sel_r_40}>4.0★ &amp; above</option>
        <option value="4.5" {sel_r_45}>4.5★ &amp; above</option>
      </select>

      <button class="px-3 py-2 bg-indigo-600 rounded text-sm">Filter</button>
    </form>

    <p class="text-[11px] text-slate-400 mt-1">
      Fees are approximate yearly tuition for hotel management / hospitality programmes in Hyderabad.
      Students should confirm with the college directly before applying.
    </p>

    <table class="table mt-2">
      <tr>
        <th>College</th>
        <th>Key Course</th>
        <th>Location</th>
        <th>Approx. Annual Fees</th>
        <th>Rating</th>
      </tr>
      {rows}
    </table>
    """
    return render_page(content, "Courses & Colleges")


# -------------------- MENTORSHIP --------------------
@app.route("/mentorship")
def mentorship():
    db = get_db()
    data = db.query(Mentor).all()
    db.close()

    cards = ""
    for m in data:
        cards += f"""
        <div class="mentor-card">
          <h3 class="text-lg font-bold mb-1">{m.name}</h3>
          <p class="text-sm text-gray-300">{m.experience}</p>
          <p class="text-sm text-indigo-300 mb-2">{m.speciality}</p>
          <a href="/book-mentor/{m.id}" class="mt-2 inline-block text-xs px-3 py-1 bg-indigo-600 rounded">
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
    db = get_db()
    mentor = db.query(Mentor).get(mentor_id)
    db.close()

    if not mentor:
        return redirect("/mentorship")

    if request.method == "POST":
        content = f"""
        <h2 class="text-2xl font-bold mb-4">Session Request Sent</h2>
        <p class="text-gray-300 mb-3 text-sm">
          Your request to connect with <span class="text-indigo-300 font-semibold">{mentor.name}</span> has been received (demo only).
        </p>
        <a href="/mentorship" class="px-4 py-2 bg-indigo-600 rounded text-sm">Back to mentors</a>
        """
        return render_page(content, "Mentor Booking")

    content = f"""
    <h2 class="text-2xl font-bold mb-4">Book Mentor Session</h2>
    <p class="text-gray-300 mb-4 text-sm">
      Mentor: <span class="text-indigo-300 font-semibold">{mentor.name}</span> (details ...).
    </p>
    <form method="POST" class="auth-card">
      <input name="student_name" placeholder="Your name ..." class="input-box">
      <input name="student_email" placeholder="Your email ..." class="input-box">
      <input name="preferred_time" placeholder="Preferred time slot ..." class="input-box">
      <button class="submit-btn">Request Session (demo)</button>
    </form>
    """
    return render_page(content, "Book Mentor")


# -------------------- JOBS = PLACEMENTS SNAPSHOT --------------------
@app.route("/jobs")
def jobs():
    db = get_db()
    data = db.query(Job).all()
    db.close()

    cards = ""
    for j in data:
        cards += f"""
        <div class="job-card">
          <h3 class="font-bold text-sm md:text-base mb-1">{j.title}</h3>
          <p class="text-indigo-300 text-xs md:text-sm">Top recruiter: {j.company}</p>
          <p class="text-gray-400 text-xs md:text-sm">Location: {j.location}</p>
          <p class="text-green-300 font-semibold text-xs md:text-sm mt-1">{j.salary}</p>
        </div>
        """

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Placements &amp; Recruiters Snapshot</h2>
    <p class="text-gray-300 mb-4 text-sm">
      This section shows sample placement outcomes and recruiter names connected to Hyderabad hotel-management colleges.
      All packages are indicative and for demo only – actual numbers depend on college, year and role.
    </p>
    <div class="grid md:grid-cols-3 gap-6">
      {cards}
    </div>
    """
    return render_page(content, "Jobs & Placements")


# -------------------- GLOBAL COLLEGE & INTERNSHIP MATCH --------------------
@app.route("/global-match")
def global_match():
    content = """
    <h2 class="text-3xl font-bold mb-4">Global College &amp; Internship Match</h2>
    <p class="text-gray-300 mb-4 text-sm">
      Many hospitality students from Hyderabad explore <b>abroad options</b> after their base degree or diploma.
      This section gives a broad idea of where students usually go and what kind of internships they target.
      These are <b>examples only</b> – always confirm directly with each college or agency.
    </p>

    <div class="grid md:grid-cols-3 gap-5 mb-6">
      <div class="support-box">
        <h3 class="font-semibold mb-2 text-lg">Popular Countries</h3>
        <ul class="text-sm text-slate-200 space-y-1.5">
          <li>• Switzerland – hotel schools + paid internships</li>
          <li>• Dubai / UAE – luxury hotels, F&amp;B internships</li>
          <li>• Singapore – structured hospitality diplomas</li>
          <li>• Canada – 2-year hospitality diplomas + work route</li>
        </ul>
      </div>

      <div class="support-box">
        <h3 class="font-semibold mb-2 text-lg">Typical Requirements</h3>
        <ul class="text-sm text-slate-200 space-y-1.5">
          <li>• Strong 10th &amp; 12th marks (especially English)</li>
          <li>• IELTS / language test for many programmes</li>
          <li>• Clear SOP explaining your hospitality goals</li>
          <li>• Budget planning for fees + living expenses</li>
        </ul>
      </div>

      <div class="support-box">
        <h3 class="font-semibold mb-2 text-lg">Internship Patterns</h3>
        <ul class="text-sm text-slate-200 space-y-1.5">
          <li>• 6–12 month internships in hotels / resorts</li>
          <li>• Roles in front office, F&amp;B, culinary, housekeeping</li>
          <li>• Mix of stipend + accommodation in many cases</li>
          <li>• Often used as a pathway to full-time roles</li>
        </ul>
      </div>
    </div>

    <p class="text-xs text-slate-400 mb-4">
      Data above is a generic pattern seen in hospitality education. Exact fees, visa rules and internship
      structures change every year and depend on each college, hotel group and country.
    </p>

    <p class="text-sm text-slate-200">
      To match you with a realistic abroad pathway based on your <b>marks, budget and country preference</b>,
      first talk to the <b>AI Career Bot</b>, then share that summary with a <b>CareerInn mentor</b> from the
      Mentorship section.
    </p>
    """
    return render_page(content, "Global College & Internship Match")


# -------------------- AI CAREER BOT (ONE FREE CHAT / USER) --------------------
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    # Login required
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    locked = bool(usage and usage.ai_used == 1)

    # Reset chat but should NOT reset free usage
    if request.args.get("reset") == "1":
        session["ai_history"] = []
        db.close()
        return redirect("/chatbot")

    # Load history
    history = session.get("ai_history", [])
    if not isinstance(history, list):
        history = []
    session["ai_history"] = history

    if request.method == "POST":
        if locked:
            history.append({
                "role": "assistant",
                "content": (
                    "⚠ Your free AI career chat session has ended.\n"
                    "Please check the Student Pass (₹299/year) on the home page and talk to mentors for more guidance."
                ),
            })
            session["ai_history"] = history
            db.close()
            html = render_template_string(CHATBOT_HTML, history=history, locked=True)
            return render_page(html, "CareerInn AI Mentor")

        user_msg = request.form.get("message", "").strip()
        if user_msg:
            history.append({"role": "user", "content": user_msg})

            messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}] + history
            groq_client = get_groq_client()

            if groq_client is None:
                reply = (
                    "AI is not configured yet. Please ask the admin to set GROQ_API_KEY "
                    "in the server environment."
                )
            else:
                try:
                    resp = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages,
                        temperature=0.7,
                    )
                    reply = resp.choices[0].message.content
                except Exception as e:
                    reply = f"AI error: {e}"

            history.append({"role": "assistant", "content": reply})
            session["ai_history"] = history

    db.close()
    html = render_template_string(CHATBOT_HTML, history=history, locked=locked)
    return render_page(html, "CareerInn AI Mentor")


@app.route("/finish")
def finish():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()

    if usage is None:
        usage = AiUsage(user_id=user_id, ai_used=1)
        db.add(usage)
    else:
        usage.ai_used = 1

    db.commit()
    db.close()
    return redirect("/chatbot")


# -------------------- END & LOCK CHAT (POST BUTTON) --------------------
@app.route("/chatbot/end", methods=["POST"])
def end_chatbot():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    db = get_db()
    try:
        usage = db.query(AiUsage).filter_by(user_id=user_id).first()
        if usage is None:
            usage = AiUsage(user_id=user_id, ai_used=1)
            db.add(usage)
        else:
            usage.ai_used = 1
        db.commit()
    finally:
        db.close()

    session["ai_history"] = []
    session["ai_used"] = True
    return redirect("/chatbot")


# -------------------- SUPPORT --------------------
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


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True)
