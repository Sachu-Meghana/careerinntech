import os
from datetime import datetime

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    url_for,
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from groq import Groq

# -------------------- CONFIG --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "careerinn_super_secret")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careerinn.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()


def get_db():
    return SessionLocal()


@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()


# -------------------- MODELS --------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    __tablename__ = "ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    ai_used = Column(Integer, nullable=False, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=False)
    paid_at = Column(DateTime, nullable=True)
    order_id = Column(String(255), nullable=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    skills_text = Column(Text, nullable=True)
    target_roles = Column(Text, nullable=True)
    self_rating = Column(Integer, nullable=False, default=0)
    resume_link = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)


# -------------------- DB INIT & SEED --------------------
def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    if db.query(College).count() == 0:
        colleges_seed = [
            ("IHM Hyderabad (IHMH)", "DD Colony, Hyderabad", 320000,
             "BSc in Hospitality & Hotel Administration", 4.6),
            ("NITHM Hyderabad", "Gachibowli, Hyderabad", 280000,
             "BBA in Tourism & Hospitality", 4.3),
            ("IIHM Hyderabad", "Somajiguda, Hyderabad", 350000,
             "BA in Hospitality Management", 4.5),
            ("Regency College of Culinary Arts & Hotel Management", "Himayatnagar, Hyderabad",
             240000, "BHM & Culinary Arts", 4.4),
            ("IHM Shri Shakti", "Kompally, Hyderabad", 260000,
             "BSc Hotel Management & Catering", 4.2),
            ("Westin College of Hotel Management", "Nizampet, Hyderabad", 190000,
             "Bachelor of Hotel Management (BHM)", 3.9),
        ]
        for name, loc, fees, course, rating in colleges_seed:
            db.add(College(name=name, location=loc, fees=fees, course=course, rating=rating))

    if db.query(Mentor).count() == 0:
        mentors_seed = [
            ("Senior Mentor A", "10+ years in 5-star hotels (front office & training).",
             "Front Office / Hotel Ops"),
            ("Chef Mentor B", "Executive chef with cruise & luxury hotel background.",
             "Culinary / Bakery"),
            ("Abroad Guide C", "Hospitality abroad, internships, cruise & Dubai guidance.",
             "Abroad / Cruise / Internships"),
        ]
        for n, exp, spec in mentors_seed:
            db.add(Mentor(name=n, experience=exp, speciality=spec))

    if db.query(Job).count() == 0:
        jobs_seed = [
            ("Management Trainee – Hotel Operations",
             "Taj / IHCL", "Pan India", "₹4.5–5.5 LPA (avg)"),
            ("F&B Associate",
             "Marriott Hotels", "Hyderabad / Bengaluru", "₹3–4 LPA"),
            ("Guest Relations Executive",
             "ITC Hotels", "Hyderabad", "₹3.5–4.5 LPA"),
        ]
        for t, c_, loc, sal in jobs_seed:
            db.add(Job(title=t, company=c_, location=loc, salary=sal))

    db.commit()
    db.close()


init_db()


# -------------------- HELPERS --------------------
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def user_is_subscribed(user_id: int | None) -> bool:
    if not user_id:
        return False
    db = get_db()
    sub = db.query(Subscription).filter_by(user_id=user_id, active=True).first()
    db.close()
    return bool(sub)


# -------------------- AI SYSTEM PROMPT --------------------
AI_SYSTEM_PROMPT = """
You are CareerInn's AI career guide for hospitality and hotel management in Hyderabad.

Behave like a friendly senior:
- Ask questions step-by-step about marks, budget, interests, city preference.
- Then suggest 3–5 college + path options (mostly Hyderabad hotel-management).
- Mention examples like IHM Hyderabad, NITHM, IIHM, Regency, IHM Shri Shakti, Westin, etc.
- Be clear this is guidance, not final admission decision.
- At the end ask the student to connect with a CareerInn mentor.

Write in simple English, short paragraphs.
"""


# -------------------- BASE LAYOUT --------------------
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{% if title %}{{ title }}{% else %}CareerInn{% endif %}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body class="bg-slate-950 text-white">
  <div class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">

    <!-- NAVBAR -->
    <nav class="flex justify-between items-center px-6 md:px-10 py-4 bg-black/40 backdrop-blur-md border-b border-slate-800">
      <div class="flex items-center gap-3">
        <div class="w-11 h-11 rounded-2xl bg-slate-900 flex items-center justify-center shadow-lg shadow-indigo-500/40 overflow-hidden">
          <span class="text-xl">🏨</span>
        </div>
        <div>
          <p class="font-bold text-lg md:text-xl tracking-tight">CareerInn</p>
          <p class="text-[11px] text-slate-400">Hospitality Careers · Colleges · Jobs</p>
        </div>
      </div>

      <div class="hidden md:flex items-center gap-6 text-sm">
        <a href="{{ url_for('home') }}" class="nav-link">Home</a>
        <a href="{{ url_for('courses') }}" class="nav-link">Courses</a>
        <a href="{{ url_for('colleges') }}" class="nav-link">Colleges</a>
        <a href="{{ url_for('mentorship') }}" class="nav-link">Mentorship</a>
        <a href="{{ url_for('jobs') }}" class="nav-link">Jobs</a>
        <a href="{{ url_for('global_match') }}" class="nav-link">Global Match</a>
        <a href="{{ url_for('chatbot') }}" class="nav-link">AI Career Bot</a>
        <a href="{{ url_for('support') }}" class="nav-link">Support</a>

        {% if session.get('user') %}
          <div class="relative group">
            <button class="flex items-center gap-2 px-3 py-1.5 text-[13px] rounded-full border border-slate-700 bg-slate-900/80 hover:bg-slate-800">
              <div class="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center text-xs font-bold">
                {{ session.get('user')[0]|upper }}
              </div>
              <span class="text-slate-200">{{ session.get('user') }}</span>
            </button>
            <div class="absolute right-0 mt-2 w-44 bg-slate-900 border border-slate-700 rounded-xl shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition">
              <a href="{{ url_for('dashboard') }}" class="block px-3 py-2 text-xs hover:bg-slate-800">User Profile</a>
              <a href="{{ url_for('subscribe') }}" class="block px-3 py-2 text-xs hover:bg-slate-800">Subscription</a>
              <a href="{{ url_for('logout') }}" class="block px-3 py-2 text-xs text-rose-300 hover:bg-slate-900/80">Logout</a>
            </div>
          </div>
        {% else %}
          <a href="{{ url_for('login') }}" class="px-4 py-1.5 rounded-full bg-indigo-500 hover:bg-indigo-600 text-xs font-semibold shadow shadow-indigo-500/40">
            Login
          </a>
        {% endif %}
      </div>
    </nav>

    <!-- PAGE CONTENT -->
    <main class="px-5 md:px-10 py-8">
      {{ content|safe }}
    </main>

    <!-- AI floating button -->
    <button id="aiFab" class="fixed right-4 bottom-4 md:right-6 md:bottom-6 rounded-full shadow-xl bg-gradient-to-br from-indigo-500 to-emerald-400 p-3 md:p-4 flex items-center justify-center hover:scale-105 transition">
      <span class="text-2xl md:text-3xl">👩‍🍳</span>
    </button>

    <!-- AI popup -->
    <div id="aiPopup" class="hidden fixed right-4 bottom-20 md:right-6 md:bottom-24 w-80 max-w-[95vw] bg-slate-950/95 border border-slate-700 rounded-2xl shadow-2xl p-4 z-50">
      <div class="flex justify-between items-center mb-2">
        <div>
          <p class="text-sm font-semibold">CareerInn AI</p>
          <p class="text-[11px] text-slate-400">Your hotel & hospitality mentor bot.</p>
        </div>
        <button id="closeAi" class="text-slate-400 hover:text-white text-lg leading-none">×</button>
      </div>
      <p class="text-xs text-slate-300 mb-3">
        Confused about colleges, fees, or roles like front office / F&B / chef?
        Start a quick AI chat or a full guided session.
      </p>
      <div class="flex flex-col gap-2">
        <a href="{{ url_for('chatbot') }}" class="w-full text-center px-3 py-2 rounded-full bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold">
          🚀 Open AI Career Chat
        </a>
        <a href="{{ url_for('mentorship') }}" class="w-full text-center px-3 py-2 rounded-full border border-slate-700 text-[11px] hover:bg-slate-900">
          🧑‍🏫 Talk to mentors after AI plan
        </a>
      </div>
    </div>

  </div>

  <script>
    const fab = document.getElementById('aiFab');
    const popup = document.getElementById('aiPopup');
    const closeAi = document.getElementById('closeAi');

    if (fab && popup && closeAi) {
      fab.addEventListener('click', () => {
        popup.classList.remove('hidden');
      });
      closeAi.addEventListener('click', () => {
        popup.classList.add('hidden');
      });
    }
  </script>
</body>
</html>
"""


def render_page(content_html: str, title: str | None = None):
    return render_template_string(BASE_HTML, content=content_html, title=title)


# -------------------- AUTH --------------------
SIGNUP_FORM = """
<form method="POST" class="auth-card max-w-md mx-auto">
  <h2 class="text-xl font-bold mb-4">Create your CareerInn account</h2>
  <input name="name" placeholder="Full Name" required class="input-box">
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn">Signup</button>
  <p class="text-gray-400 mt-3 text-sm">
    Already registered?
    <a href="{{ url_for('login') }}" class="text-indigo-400">Login</a>
  </p>
</form>
"""

LOGIN_FORM = """
<form method="POST" class="auth-card max-w-md mx-auto">
  <h2 class="text-xl font-bold mb-2">Login to CareerInn</h2>
  <input name="email" placeholder="Email" required class="input-box">
  <input name="password" type="password" placeholder="Password" required class="input-box">
  <button class="submit-btn">Login</button>
  <p class="text-gray-400 mt-3 text-sm">
    New here?
    <a href="{{ url_for('signup') }}" class="text-indigo-400">Create Account</a>
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
            msg = "<p class='error-msg'>All fields are required.</p>"
            return render_page(msg + render_template_string(SIGNUP_FORM), "Signup")

        db = get_db()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            db.close()
            msg = "<p class='error-msg'>Account already exists. Please login.</p>"
            return render_page(msg + render_template_string(SIGNUP_FORM), "Signup")

        hashed = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        user = User(name=name, email=email, password=hashed)
        db.add(user)
        db.commit()
        db.close()

        return redirect(url_for("login"))

    return render_page(render_template_string(SIGNUP_FORM), "Signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.query(User).filter(User.email == email).first()
        db.close()

        ok = False
        if user:
            try:
                ok = check_password_hash(user.password, password)
            except Exception:
                ok = (user.password == password)

        if ok:
            session["user"] = user.name
            session["user_id"] = user.id
            session["ai_history"] = []
            if "first_login_done" not in session:
                session["first_login_done"] = False
            return redirect(url_for("dashboard"))

        msg = "<p class='error-msg'>Invalid email or password.</p>"
        return render_page(msg + render_template_string(LOGIN_FORM), "Login")

    return render_page(render_template_string(LOGIN_FORM), "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -------------------- HOME --------------------
@app.route("/")
def home():
    user_id = session.get("user_id")
    logged_in = bool(user_id)

    ai_used = False
    if user_id:
        db = get_db()
        usage = db.query(AiUsage).filter_by(user_id=user_id).first()
        db.close()
        if usage and usage.ai_used >= 1:
            ai_used = True
            session["ai_used"] = True

    if not ai_used:
        if logged_in:
            cta_html = """
              <div class="flex flex-wrap items-center gap-3 mt-3">
                <a href="/dashboard" class="primary-cta">🚀 Get started – ₹299 / year</a>
                <a href="/chatbot" class="secondary-cta">
                  🤖 Use your free AI career chat
                </a>
              </div>
              <p class="hero-footnote">
                You are logged in. You still have one free AI chat. After that, guidance continues inside the ₹299/year pass.
              </p>
            """
        else:
            cta_html = """
              <div class="flex flex-wrap items-center gap-3 mt-3">
                <a href="/signup" class="primary-cta">Create free account</a>
                <a href="/login" class="ghost-cta">Sign in</a>
                <a href="/login" class="secondary-cta">
                  🤖 Try free AI career chat
                </a>
              </div>
              <p class="hero-footnote">
                First AI chat is free after login. After that, guidance continues inside the ₹299/year pass.
              </p>
            """
    else:
        cta_html = """
          <div class="flex flex-wrap items-center gap-4 mt-3">
            <a href="/subscribe" class="primary-cta">
              🚀 Get started – ₹299 / year
            </a>
            <a href="/login" class="ghost-cta">
              Already have an account?
            </a>
            <a href="/chatbot" class="secondary-cta">
              🤖 Continue with AI guidance
            </a>
          </div>
          <p class="hero-footnote">
            ₹299 per student (prototype – payment hooks ready for Razorpay integration).
          </p>
        """

    content = f"""
    <div class="max-w-5xl mx-auto mt-6 md:mt-10 space-y-12 hero-shell">

      <!-- HERO -->
      <section class="grid md:grid-cols-2 gap-10 items-center">
        <div class="space-y-4">
          <span class="pill-badge">
            <span class="dot"></span> HOSPITALITY CAREERS · CAREERINN
          </span>

          <h1 class="hero-title">
            Plan your <span class="gradient-text">hotel &amp; hospitality</span> career in one place.
          </h1>

          <p class="hero-sub">
            One simple yearly pass that puts colleges, mentors, jobs and an AI career guide in a single platform.
          </p>

          {cta_html}
        </div>

        <!-- STUDENT PASS CARD -->
        <div class="hero-card rounded-3xl p-7 md:p-9 space-y-5">
          <p class="text-sm text-slate-300 uppercase tracking-[0.22em]">
            STUDENT PASS
          </p>
          <div class="flex items-end gap-3">
            <span class="text-5xl font-extrabold text-emerald-300">₹299</span>
            <span class="text-sm text-slate-300 mb-2">per student / year</span>
          </div>
          <p class="text-[13px] md:text-sm text-slate-300">
            Students can explore hospitality careers, compare colleges, and get mentor &amp; AI guidance in one simple space.
          </p>
          <ul class="text-xs md:text-sm text-slate-200 space-y-1.5 mt-2">
            <li>• Hyderabad hotel-management colleges &amp; fees snapshot</li>
            <li>• Mentor connect with demo booking flow</li>
            <li>• Jobs &amp; placement trends from top brands</li>
            <li>• AI-based college &amp; path suggestion chat</li>
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
          <a href="/colleges" class="feature-card">
            🏫 Colleges
            <p class="sub">Hyderabad hotel-management colleges.</p>
          </a>
          <a href="/mentorship" class="feature-card">
            🧑‍🏫 Mentorship
            <p class="sub">Talk to hospitality mentors.</p>
          </a>
          <a href="/jobs" class="feature-card">
            💼 Jobs &amp; Placements
            <p class="sub">Avg packages &amp; recruiters snapshot.</p>
          </a>
          <a href="/global-match" class="feature-card">
            🌍 Global Match
            <p class="sub">Abroad options overview.</p>
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


# -------------------- DASHBOARD --------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user_name = session["user"]
    tab = request.args.get("tab") or "home"

    db = get_db()
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()

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
            return redirect(url_for("dashboard", tab="skills"))

        if tab == "resume":
            profile.resume_link = request.form.get("resume_link", "").strip()
            profile.notes = request.form.get("notes", "").strip()
            db.commit()
            db.close()
            return redirect(url_for("dashboard", tab="resume"))

    skills_text = profile.skills_text or ""
    target_roles = profile.target_roles or ""
    self_rating = profile.self_rating or 0
    resume_link = profile.resume_link or ""
    notes = profile.notes or ""
    db.close()

    first = not session.get("first_login_done", False)
    if first:
        greeting = "CareerInn welcomes you 🎉"
        session["first_login_done"] = True
    else:
        greeting = "Welcome back 👋"

    def stars(n: int) -> str:
        full = "⭐" * n
        empty = "<span class='text-slate-700'>⭐</span>" * (5 - n)
        return full + empty

    home_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">{greeting}, {user_name}</h2>
        <p class="text-sm text-slate-300">
          This is your personal hospitality space. Track your skills, resume and readiness for hotel &amp; hospitality careers.
        </p>

        <div class="grid md:grid-cols-3 gap-4 mt-4">
          <div class="dash-box">
            <p class="dash-label">Career readiness rating</p>
            <p class="dash-value">{self_rating}/5</p>
          </div>
          <div class="dash-box">
            <p class="dash-label">Target roles set</p>
            <p class="dash-value">{"Yes" if target_roles else "No"}</p>
          </div>
          <div class="dash-box">
            <p class="dash-label">Resume link added</p>
            <p class="dash-value">{"Yes" if resume_link else "No"}</p>
          </div>
        </div>

        <div class="mt-6 bg-slate-900/70 border border-slate-700 rounded-2xl p-4">
          <h3 class="font-semibold mb-2">CareerInn guidance</h3>
          <ul class="text-xs md:text-sm text-slate-300 space-y-1.5">
            <li>• Strengthen English, grooming and basic customer service in the first year.</li>
            <li>• Target at least one internship in hotel / restaurant before final year.</li>
            <li>• Use the AI bot to get a college plan, then talk to mentors for final decisions.</li>
            <li>• Keep your resume link updated so mentors can quickly review it.</li>
          </ul>
        </div>
      </div>
    """

    skills_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Skills &amp; strengths ⭐</h2>
        <p class="text-sm text-slate-300">
          Fill this honestly. It helps mentors understand where you stand today.
        </p>
        <form method="POST" class="space-y-4 mt-4">
          <div>
            <label class="field-label">Current skills (communication, cooking, service, tools...)</label>
            <textarea name="skills_text" rows="4" class="input-box h-auto"
              placeholder="Example: Good English speaking, basic MS Office, love cooking, hosted college events.">{skills_text}</textarea>
          </div>
          <div>
            <label class="field-label">Target roles in hospitality</label>
            <textarea name="target_roles" rows="3" class="input-box h-auto"
              placeholder="Example: Front office executive, F&amp;B service, commis chef, cruise jobs.">{target_roles}</textarea>
          </div>
          <div class="grid md:grid-cols-2 gap-4 items-center">
            <div>
              <label class="field-label">Rate your overall readiness (0–5)</label>
              <input name="self_rating" type="number" min="0" max="5" value="{self_rating}" class="input-box" />
            </div>
            <p class="text-[11px] text-slate-400">
              This is only a self-check. Mentors can adjust it after speaking with you.
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
          A quick snapshot of how ready you feel for hospitality education and jobs.
        </p>
        <div class="mt-4 bg-slate-900/70 border border-slate-700 rounded-2xl p-4 space-y-3">
          <p class="text-xs text-slate-400">Self-rating (0–5)</p>
          <div class="flex items-center gap-3">
            <div class="flex gap-1 text-yellow-400">{stars(self_rating)}</div>
            <span class="text-sm text-slate-200">{self_rating}/5</span>
          </div>
          <p class="text-xs text-slate-400 mt-2">
            If below 3: focus on English, grooming, discipline, basic computer skills.
            If 3 or above: start internships, hotel visits and real exposure.
          </p>
        </div>
      </div>
    """

    resume_panel = f"""
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">Resume &amp; profile link 📄</h2>
        <p class="text-sm text-slate-300">
          Upload your resume to Google Drive or any cloud and paste the link here.
        </p>
        <form method="POST" class="space-y-4 mt-4">
          <input type="hidden" name="tab" value="resume">
          <div>
            <label class="field-label">Resume link (Google Drive / PDF)</label>
            <input name="resume_link" class="input-box"
                   placeholder="https://drive.google.com/..." value="{resume_link}">
          </div>
          <div>
            <label class="field-label">Notes for mentor (optional)</label>
            <textarea name="notes" rows="3" class="input-box h-auto"
              placeholder="Anything important mentors should know about your situation, gaps or goals.">{notes}</textarea>
          </div>
          <button class="submit-btn mt-2">Save resume details</button>
        </form>
        {"<p class='text-xs text-emerald-300 mt-2'>Current resume: <a href='" + resume_link + "' target='_blank' class='underline'>" + resume_link + "</a></p>" if resume_link else ""}
      </div>
    """

    faqs_panel = """
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">FAQs ❓</h2>
        <div class="space-y-3 text-sm text-slate-200">
          <div>
            <p class="font-semibold">Is ₹299 / year a real payment?</p>
            <p class="text-slate-300 text-xs">
              This prototype is ready for Razorpay integration. If payment keys are not configured,
              it behaves like a demo subscription.
            </p>
          </div>
          <div>
            <p class="font-semibold">Are these college details official?</p>
            <p class="text-slate-300 text-xs">
              No. Fees, ratings and packages are approximate guidance. Always confirm with each college before applying.
            </p>
          </div>
        </div>
      </div>
    """

    about_panel = """
      <div class="space-y-4">
        <h2 class="text-2xl md:text-3xl font-bold">About CareerInn 🏨</h2>
        <p class="text-sm text-slate-300">
          CareerInn is built for students who are serious about hospitality & hotel careers,
          but feel lost between colleges, agents and random advice.
        </p>
        <p class="text-sm text-slate-300">
          The goal is simple: one place where you can see colleges, fees, roles, salaries, talk to mentors
          and use AI to plan your path – without pressure.
        </p>
      </div>
    """

    panels = {
        "home": home_panel,
        "skills": skills_panel,
        "rating": rating_panel,
        "resume": resume_panel,
        "faqs": faqs_panel,
        "about": about_panel,
    }
    panel_html = panels.get(tab, home_panel)

    base_tab = "block w-full text-left px-3 py-2 rounded-lg text-xs md:text-sm"
    def cls(name: str) -> str:
        if tab == name:
            return base_tab + " bg-indigo-600 text-white border border-indigo-500"
        return base_tab + " text-slate-300 hover:bg-slate-800 border border-transparent"

    content = f"""
    <div class="max-w-6xl mx-auto">
      <div class="mb-4">
        <p class="text-xs text-slate-400">Profile · Hotel &amp; Hospitality</p>
        <h1 class="text-2xl md:text-3xl font-bold">User Profile</h1>
      </div>

      <div class="grid md:grid-cols-[220px,1fr] gap-6">
        <aside class="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 h-max">
          <p class="text-[11px] text-slate-400 mb-2">Your space</p>
          <p class="text-sm font-semibold mb-4 truncate">{user_name}</p>
          <nav class="flex flex-col gap-2">
            <a href="/dashboard?tab=home" class="{cls('home')}">🏠 Overview</a>
            <a href="/dashboard?tab=skills" class="{cls('skills')}">⭐ Skills</a>
            <a href="/dashboard?tab=rating" class="{cls('rating')}">📊 Rating</a>
            <a href="/dashboard?tab=resume" class="{cls('resume')}">📄 Resume</a>
            <a href="/dashboard?tab=faqs" class="{cls('faqs')}">❓ FAQs</a>
            <a href="/dashboard?tab=about" class="{cls('about')}">ℹ️ About us</a>
          </nav>
        </aside>

        <section class="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 md:p-6">
          {panel_html}
        </section>
      </div>
    </div>
    """
    return render_page(content, "Dashboard")


# -------------------- SUBSCRIPTION (payment-ready) --------------------
@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    db = get_db()
    sub = db.query(Subscription).filter_by(user_id=user_id).first()
    if not sub:
        sub = Subscription(user_id=user_id, active=False)
        db.add(sub)
        db.commit()

    razor_key = os.getenv("RAZORPAY_KEY_ID")
    razor_enabled = bool(razor_key)

    if request.method == "POST":
        # Demo: mark subscription active immediately.
        sub.active = True
        sub.paid_at = datetime.utcnow()
        db.commit()
        db.close()
        return redirect(url_for("dashboard"))

    db.close()

    # If you later wire Razorpay properly, you can replace POST form with checkout.js flow.
    content = f"""
    <div class="max-w-xl mx-auto space-y-4">
      <h2 class="text-2xl md:text-3xl font-bold mb-2">CareerInn Student Pass</h2>
      <p class="text-sm text-slate-300">
        Unlock mentorship, full AI planning and future premium features for just <b>₹299 / year</b>.
      </p>
      <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-2">
        <p class="text-sm text-slate-200">What you get:</p>
        <ul class="text-xs text-slate-300 space-y-1.5">
          <li>• Unlimited AI career planning sessions</li>
          <li>• Priority access to mentors &amp; mock sessions</li>
          <li>• Early access to new tools and college stats</li>
        </ul>
      </div>

      {"<p class='text-emerald-300 text-sm'>Your subscription is active.</p>" if sub.active else ""}

      <form method="POST" class="mt-3">
        <button class="primary-cta">
          { "✅ Subscription active" if sub.active else "Pay (demo) – Mark as Subscribed" }
        </button>
      </form>

      {"<p class='text-[11px] text-slate-500 mt-2'>Razorpay keys not configured – running in demo mode. When keys are added, this page becomes a real payment flow.</p>" if not razor_enabled else ""}
    </div>
    """
    return render_page(content, "Subscription")


# -------------------- COURSES --------------------
@app.route("/courses")
def courses():
    db = get_db()
    data = db.query(College).order_by(College.course.asc()).all()
    db.close()

    rows = ""
    for c in data:
        rows += f"<tr><td>{c.course}</td><td>{c.name}</td></tr>"

    if not rows:
        rows = "<tr><td colspan='2'>No courses found.</td></tr>"

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Hospitality &amp; Hotel Management Courses</h2>
    <p class="text-sm text-slate-300 mb-3">
      Snapshot of popular hospitality courses offered by different colleges in and around Hyderabad.
      Always confirm exact details with each college.
    </p>
    <table class="table mt-2">
      <tr><th>Course</th><th>College</th></tr>
      {rows}
    </table>
    """
    return render_page(content, "Courses")


# -------------------- COLLEGES (filters) --------------------
@app.route("/colleges")
def colleges():
    budget = request.args.get("budget", "").strip()
    rating_min = request.args.get("rating", "").strip()

    db = get_db()
    query = db.query(College)

    if budget == "lt2":
        query = query.filter(College.fees < 200000)
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
        rows = "<tr><td colspan='5'>No colleges match this filter yet.</td></tr>"

    sel_any = "selected" if budget == "" else ""
    sel_lt2 = "selected" if budget == "lt2" else ""
    sel_b23 = "selected" if budget == "b2_3" else ""
    sel_gt3 = "selected" if budget == "gt3" else ""
    sel_r_any = "selected" if rating_min == "" else ""
    sel_r_40 = "selected" if rating_min == "4.0" else ""
    sel_r_45 = "selected" if rating_min == "4.5" else ""

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Hyderabad Hotel Management – Colleges</h2>
    <form method="GET" class="mb-3 grid md:grid-cols-3 gap-3 items-center">
      <select name="budget" class="search-bar">
        <option value="" {sel_any}>Any budget</option>
        <option value="lt2" {sel_lt2}>Below ₹2,00,000</option>
        <option value="b2_3" {sel_b23}>₹2,00,000 – ₹3,00,000</option>
        <option value="gt3" {sel_gt3}>Above ₹3,00,000</option>
      </select>
      <select name="rating" class="search-bar">
        <option value="" {sel_r_any}>Any rating</option>
        <option value="4.0" {sel_r_40}>4.0★ &amp; above</option>
        <option value="4.5" {sel_r_45}>4.5★ &amp; above</option>
      </select>
      <button class="px-3 py-2 bg-indigo-600 rounded text-sm">Filter</button>
    </form>
    <p class="text-[11px] text-slate-400 mt-1">
      Fees are approximate yearly tuition for hotel-management programmes in Hyderabad.
      Always confirm with each college.
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
    return render_page(content, "Colleges")


# -------------------- MENTORSHIP --------------------
@app.route("/mentorship")
def mentorship():
    db = get_db()
    mentors = db.query(Mentor).all()
    db.close()

    cards = ""
    for m in mentors:
        cards += f"""
        <div class="mentor-card">
          <h3 class="text-lg font-bold mb-1">{m.name}</h3>
          <p class="text-sm text-slate-300 mb-1">{m.experience}</p>
          <p class="text-xs text-indigo-300 mb-2">{m.speciality}</p>
          <p class="text-[11px] text-slate-400">Booking flow demo only – can be wired to Calendly / Google Meet later.</p>
        </div>
        """

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Mentorship</h2>
    <p class="text-sm text-slate-300 mb-4">
      CareerInn mentors share real hotel stories, explain roles and help you choose the right path.
    </p>
    <div class="grid md:grid-cols-3 gap-6">
      {cards}
    </div>
    """
    return render_page(content, "Mentorship")


# -------------------- JOBS --------------------
@app.route("/jobs")
def jobs():
    db = get_db()
    data = db.query(Job).all()
    db.close()

    cards = ""
    for j in data:
        cards += f"""
        <div class="job-card">
          <h3 class="font-semibold text-sm md:text-base mb-1">{j.title}</h3>
          <p class="text-xs text-indigo-300">Top recruiter: {j.company}</p>
          <p class="text-xs text-slate-300">Location: {j.location}</p>
          <p class="text-xs text-emerald-300 mt-1">{j.salary}</p>
        </div>
        """

    content = f"""
    <h2 class="text-3xl font-bold mb-4">Jobs &amp; Placement Snapshot</h2>
    <p class="text-sm text-slate-300 mb-4">
      Example roles and package ranges for hotel-management graduates. Exact numbers depend on college,
      role, brand and year.
    </p>
    <div class="grid md:grid-cols-3 gap-6">
      {cards}
    </div>
    """
    return render_page(content, "Jobs & Placements")


# -------------------- GLOBAL MATCH --------------------
@app.route("/global-match")
def global_match():
    content = """
    <h2 class="text-3xl font-bold mb-4">Global College &amp; Internship Match</h2>
    <p class="text-sm text-slate-300 mb-4">
      Many hospitality students from Hyderabad explore abroad options after their base degree or diploma.
      This section gives a high-level idea – you can convert it into a full counsellor module later.
    </p>
    <div class="grid md:grid-cols-3 gap-5 mb-6">
      <div class="support-box">
        <h3 class="font-semibold mb-2 text-lg">Popular Countries</h3>
        <ul class="text-sm text-slate-200 space-y-1.5">
          <li>• Switzerland – classic hotel schools</li>
          <li>• Dubai / UAE – luxury hotel exposure</li>
          <li>• Singapore – structured hospitality diplomas</li>
          <li>• Canada – 2-year diplomas + work routes</li>
        </ul>
      </div>
      <div class="support-box">
        <h3 class="font-semibold mb-2 text-lg">Typical Requirements</h3>
        <ul class="text-sm text-slate-200 space-y-1.5">
          <li>• Strong 10th &amp; 12th marks (especially English)</li>
          <li>• IELTS / language tests for many programmes</li>
          <li>• Clear SOP explaining hospitality goals</li>
          <li>• Budget planning for fees + living</li>
        </ul>
      </div>
      <div class="support-box">
        <h3 class="font-semibold mb-2 text-lg">Internship Patterns</h3>
        <ul class="text-sm text-slate-200 space-y-1.5">
          <li>• 6–12 month internships in hotels / resorts</li>
          <li>• Roles in front office, F&amp;B, culinary, housekeeping</li>
          <li>• Mix of stipend + accommodation in many cases</li>
        </ul>
      </div>
    </div>
    """
    return render_page(content, "Global Match")


# -------------------- AI CAREER BOT --------------------
CHATBOT_HTML = """
<div class="max-w-3xl mx-auto space-y-6">
  <h1 class="text-3xl font-bold mb-2">CareerInn AI Mentor</h1>

  {% if not locked %}
    <p class="text-sm text-slate-300 mb-4">
      This AI bot will ask about your marks, budget, interests and city preference.
      You get <b>one full free chat</b> per account. After that, you can continue with a paid plan.
    </p>
  {% else %}
    <p class="text-sm text-slate-300 mb-4">
      Your free AI career chat is finished for this account.
      Please check the Student Pass and connect with mentors for more guidance.
    </p>
  {% endif %}

  <form method="GET" action="/chatbot" class="mb-3">
    <input type="hidden" name="reset" value="1">
    <button class="px-3 py-1 rounded-full border border-slate-600 text-[11px] hover:bg-slate-800">
      🔄 Clear chat on screen
    </button>
  </form>

  <div class="bg-slate-900/80 border border-slate-700 rounded-2xl p-4 h-[380px] overflow-y-auto mb-4">
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
        👋 Hi! I’m your CareerInn AI mentor. Tell me your name, latest class (10th / 12th / degree) and approximate marks.
      </p>
    {% endif %}
  </div>

  {% if not locked %}
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
    <form method="POST" action="/chatbot/end" class="mt-3">
      <button class="px-3 py-1.5 text-[11px] rounded-full border border-rose-500/70 text-rose-200 hover:bg-rose-500/10">
        🔒 End &amp; lock free AI chat
      </button>
    </form>
  {% else %}
    <p class="text-xs text-slate-400 mt-2">
      Tip: Go back to the Home page to see the Student Pass and mentors.
    </p>
  {% endif %}
</div>
"""


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    locked = bool(usage and usage.ai_used == 1)

    if request.args.get("reset") == "1":
        session["ai_history"] = []
        db.close()
        return redirect(url_for("chatbot"))

    history = session.get("ai_history", [])
    if not isinstance(history, list):
        history = []
    session["ai_history"] = history

    if request.method == "POST":
        if locked:
            history.append({
                "role": "assistant",
                "content": "Your free AI career chat session has ended. Please subscribe or talk to a mentor."
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
                reply = "AI is not configured yet. Ask the admin to set GROQ_API_KEY on the server."
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


@app.route("/chatbot/end", methods=["POST"])
def end_chatbot():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    if usage is None:
        usage = AiUsage(user_id=user_id, ai_used=1)
        db.add(usage)
    else:
        usage.ai_used = 1
    db.commit()
    db.close()

    session["ai_history"] = []
    session["ai_used"] = True
    return redirect(url_for("chatbot"))


# -------------------- SUPPORT --------------------
@app.route("/support")
def support():
    content = """
    <h2 class="text-3xl font-bold mb-6">Support &amp; Help</h2>
    <p class="mb-4 text-slate-300 text-sm">
      For now, this is a prototype. For any issues or partnership discussions, reach out:
    </p>
    <div class="support-box">
      <p>📧 support@careerinn.example</p>
      <p>📞 +91-98xx-xx-xxxx</p>
    </div>
    """
    return render_page(content, "Support")


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
