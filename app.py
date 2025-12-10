# app.py - CareerInn-Tech (merged) - single-file Flask app
# Save as app.py
# Requirements: flask, sqlalchemy, werkzeug, groq (optional)
# Run: python app.py
# For production: set FLASK_SECRET_KEY and optionally DATABASE_URL and GROQ_API_KEY

import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    send_from_directory,
    url_for,
)

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# optional: GROQ client for AI — install only if you plan to use it
try:
    from groq import Groq
except Exception:
    Groq = None

# -------------------- CONFIG --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "careerinn_tech_dev_secret")

# uploads folder (kept but prev-paper upload disabled)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------- GROQ HELPER --------------------
def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or Groq is None:
        return None
    return Groq(api_key=api_key)

# -------------------- DB SETUP --------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careerinn_tech.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

# -------------------- MODELS --------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    video_link = Column(String(1000), nullable=True)
    track = Column(String(50), nullable=False)  # 'btech' or 'hospitality'

class College(Base):
    __tablename__ = "colleges"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    fees = Column(Integer, nullable=False)
    course = Column(String(255), nullable=False)
    rating = Column(Float, nullable=False)
    track = Column(String(50), nullable=False)  # 'btech' or 'hospitality'

class Mentor(Base):
    __tablename__ = "mentors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    experience = Column(Text, nullable=False)
    speciality = Column(String(255), nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String(400), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    salary = Column(String(255), nullable=False)
    track = Column(String(50), nullable=False)

class AiUsage(Base):
    __tablename__ = "ai_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    ai_used = Column(Integer, nullable=False, default=0)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    skills_text = Column(Text, nullable=True)
    target_roles = Column(Text, nullable=True)
    self_rating = Column(Integer, nullable=False, default=0)
    resume_link = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=False)

class MockInterview(Base):
    __tablename__ = "mock_interviews"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    notes = Column(Text, nullable=True)
    link = Column(String(1000), nullable=True)
    uploader_id = Column(Integer, nullable=True)

class PrevPaper(Base):
    __tablename__ = "prev_papers"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    year = Column(String(20), nullable=True)
    link = Column(String(1000), nullable=True)
    uploader_id = Column(Integer, nullable=True)
    is_upload = Column(Boolean, nullable=False, default=False)

# -------------------- DB INIT & SEED --------------------
def get_db():
    return SessionLocal()

def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    # Seed sample courses (BTech + Hospitality)
    if db.query(Course).count() == 0:
        courses = [
            ("Intro to Programming (CSE)", "Learn basics of programming for B.Tech CSE students.", "https://www.example.com/video_intro_prog.mp4", "btech"),
            ("Data Structures & Algorithms", "Essential DSA course for placements.", "https://www.example.com/video_dsa.mp4", "btech"),
            ("Embedded Systems Basics", "For ECE/EE students - microcontrollers & IoT.", "https://www.example.com/video_embedded.mp4", "btech"),
            ("Front Office Operations", "Hospitality front office fundamentals.", "https://www.example.com/video_frontoffice.mp4", "hospitality"),
            ("Food & Beverage Service", "F&B service etiquette and practice.", "https://www.example.com/video_fb.mp4", "hospitality"),
            ("Kitchen Hygiene & Safety (HACCP)", "Food safety basics for hospitality.", "https://www.example.com/video_haccp.mp4", "hospitality"),
        ]
        for t, d, v, tr in courses:
            db.add(Course(title=t, description=d, video_link=v, track=tr))

    # Seed colleges for both tracks
    if db.query(College).count() == 0:
        colleges_seed = [
            # Hospitality
            ("IHM Hyderabad (IHMH)", "DD Colony, Hyderabad", 320000, "BSc Hospitality & Hotel Admin", 4.6, "hospitality"),
            ("IIHM Hyderabad", "Somajiguda, Hyderabad", 350000, "BA Hospitality Management", 4.5, "hospitality"),
            ("Regency College of Culinary Arts", "Himayatnagar, Hyderabad", 240000, "BHM & Culinary Arts", 4.4, "hospitality"),
            # BTech
            ("JNTU Hyderabad", "Kukatpally, Hyderabad", 90000, "B.Tech CSE / ECE", 4.1, "btech"),
            ("Osmania University - Engineering", "Hyderabad", 80000, "B.Tech All Branches", 4.0, "btech"),
            ("VNR Vignana Jyothi", "Ghatkesar, Hyderabad", 150000, "B.Tech CSE", 4.2, "btech"),
            ("IIIT Hyderabad", "Gachibowli, Hyderabad", 300000, "B.Tech CSE", 4.8, "btech"),
        ]
        for name, loc, fees, course, rating, track in colleges_seed:
            db.add(College(name=name, location=loc, fees=fees, course=course, rating=rating, track=track))

    # Mentors
    if db.query(Mentor).count() == 0:
        mentors = [
            ("Anita Rao", "15 years in luxury hotel operations", "Hotel Ops / Front Office"),
            ("Rohit Verma", "Ex-Accor chef and culinary trainer", "Culinary / F&B"),
            ("Dr. Priya Singh", "Professor of CSE with industry mentorship", "BTech - Placements / Projects"),
        ]
        for n, e, s in mentors:
            db.add(Mentor(name=n, experience=e, speciality=s))

    # Jobs
    if db.query(Job).count() == 0:
        jobs = [
            ("Management Trainee - Front Office", "Taj Group", "Hyderabad", "₹3.5–5 LPA", "hospitality"),
            ("Commis 1 - Kitchen", "ITC Hotels", "Bengaluru", "₹2.5–3.5 LPA", "hospitality"),
            ("Software Engineer - New Grad", "Tech startup", "Hyderabad", "₹6–8 LPA", "btech"),
            ("Embedded Systems Intern", "IoT Co.", "Bengaluru", "Stipend", "btech"),
        ]
        for t, c, loc, sal, tr in jobs:
            db.add(Job(title=t, company=c, location=loc, salary=sal, track=tr))

    # Mock interviews
    if db.query(MockInterview).count() == 0:
        db.add(MockInterview(title="Front Office Mock - Common Questions", notes="Guest complains about late check-in; practice handling the situation.", link="", uploader_id=None))
        db.add(MockInterview(title="BTech - Coding Round Mock", notes="Practice with common DS & Algo questions for placements.", link="", uploader_id=None))

    # Prev papers - view-only external links (no uploads)
    if db.query(PrevPaper).count() == 0:
        db.add(PrevPaper(title="NCHM JEE - Past Papers (Aglasem)", year="all", link="https://admission.aglasem.com/nchmct-jee-question-paper/", uploader_id=None, is_upload=False))
        db.add(PrevPaper(title="IIIT Hyderabad Sample Papers", year="recent", link="https://www.iiit.ac.in/admissions/sample-papers", uploader_id=None, is_upload=False))

    db.commit()
    db.close()

@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()

# initialize DB
init_db()

# -------------------- AI SYSTEM PROMPT --------------------
AI_SYSTEM_PROMPT = """
You are CareerInn-Tech's AI career guide. Talk like a friendly senior mentor, ask structured questions and give short actionable advice.
"""

# -------------------- BASE TEMPLATE (simplified top nav) --------------------
BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title or "CareerInnTech" }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="/static/style.css">
  <style>
    /* Larger UI sizes and basic styling tweaks */
    body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
    .primary-cta { background: linear-gradient(90deg,#6366f1,#10b981); padding:10px 18px; border-radius:12px; color:#fff; font-weight:600; }
    .feature-card { background:#0b1220; padding:16px; border-radius:12px; display:block; text-align:left; color:#fff; font-weight:600; }
    .support-box { background:#0b1220; padding:16px; border-radius:12px; color:#e6eef6; }
    .hero-card { background: linear-gradient(180deg,#071028,#0b1220); }
    .table { width:100%; border-collapse:collapse; color:#e6eef6; }
    .table th, .table td { padding:10px 8px; border-bottom:1px solid rgba(255,255,255,0.04); text-align:left; }
    .input-box { width:100%; padding:10px 12px; border-radius:8px; background:#071028; color:#e6eef6; border:1px solid rgba(255,255,255,0.04); }
    .submit-btn { padding:10px 14px; border-radius:10px; background:#6366f1; color:white; font-weight:600; }
    .ai-fab { position: fixed; right: 22px; bottom: 22px; z-index: 2000; width:92px; height:92px; border-radius:999px; display:flex; align-items:center; justify-content:center; font-size:36px; cursor:pointer; box-shadow:0 25px 60px rgba(16,185,129,0.12); }
    .ai-fab .emoji { display:inline-block; transform-origin:center; animation: float 3s ease-in-out infinite, rotate 6s linear infinite; }
    @keyframes float { 0%{transform:translateY(0)}50%{transform:translateY(-10px)}100%{transform:translateY(0)} }
    @keyframes rotate { 0%{transform:rotate(0deg)}100%{transform:rotate(360deg)} }
    .ai-modal { position: fixed; right: 26px; bottom: 130px; width:520px; max-width:94%; background:#041025; border-radius:14px; box-shadow:0 30px 60px rgba(2,6,23,0.75); padding:18px; display:none; z-index:2001; }
    .ai-modal .btn { padding:10px 12px; border-radius:10px; display:inline-block; }
    nav a { margin-left:10px; color:#dbeafe; font-weight:600; }
    .logo-txt { font-weight:700; font-size:16px; }
  </style>
</head>
<body class="bg-[#030617] text-white">

<nav class="flex justify-between items-center px-6 py-4 bg-black/30 backdrop-blur-md border-b border-slate-800">
  <div class="flex items-center gap-3">
    <div class="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center overflow-hidden">
      <img src="/static/logo.png" class="w-10 h-10 object-contain" alt="logo">
    </div>
    <div>
      <div class="logo-txt">CareerInnTech</div>
      <div class="text-xs text-slate-400">BTech • Hospitality • Careers</div>
    </div>
  </div>

  <div class="flex items-center">
    <a href="/" class="text-sm">Home</a>
    <a href="/about" class="text-sm">About</a>
    <a href="/contact" class="text-sm">Contact</a>
    <a href="/support" class="text-sm">Support</a>

    {% if session.get('user') %}
      <a href="/profile" class="ml-4 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-sm flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center font-semibold text-sm">{{ session.get('user')[0]|upper }}</div>
        <div>{{ session.get('user') }}</div>
      </a>
      <a href="/logout" class="ml-3 px-3 py-1 rounded-full bg-rose-500 text-sm">Logout</a>
    {% else %}
      <a href="/login" class="ml-4 px-3 py-1 rounded-full bg-indigo-600 text-sm">Login</a>
    {% endif %}
  </div>
</nav>

<main class="px-6 py-8">
  {{ content|safe }}
</main>

<!-- AI FAB -->
<button id="aiFab" class="ai-fab bg-gradient-to-br from-indigo-500 to-emerald-400">
  <span class="emoji">🤖</span>
</button>

<div id="aiModal" class="ai-modal">
  <div class="flex items-center justify-between mb-3">
    <div class="font-semibold text-lg">CareerInn AI</div>
    <button id="closeAi" class="text-slate-400">✕</button>
  </div>
  <p class="text-sm text-slate-300 mb-3">Quick friendly AI help — one free chat per account. Subscribe for unlimited guidance and mock interviews.</p>
  <div class="flex gap-2">
    <a href="/chatbot" class="btn" style="background:#6366f1;color:white">Start AI Chat</a>
    <a href="/mock-interviews/ai" class="btn" style="border:1px solid rgba(255,255,255,0.06)">Mock Interview Bot</a>
    <a href="/subscribe" class="btn" style="margin-left:auto;background:#10b981;color:white">Subscribe ₹499/yr</a>
  </div>
</div>

<script>
  const aiFab = document.getElementById('aiFab');
  const aiModal = document.getElementById('aiModal');
  const closeAi = document.getElementById('closeAi');
  aiFab.addEventListener('click', ()=> aiModal.style.display = 'block');
  closeAi.addEventListener('click', ()=> aiModal.style.display = 'none');
  window.addEventListener('click', (e)=> { if(e.target === aiModal) aiModal.style.display='none'; });
</script>

</body>
</html>
"""

def render_page(content_html, title="CareerInnTech"):
    return render_template_string(BASE_HTML, content=content_html, title=title)

# -------------------- helpers --------------------
def user_is_subscribed(user_id):
    if not user_id:
        return False
    db = get_db()
    s = db.query(Subscription).filter_by(user_id=user_id).first()
    db.close()
    return bool(s and s.active)

# -------------------- HOME --------------------
@app.route("/")
def home():
    user_id = session.get("user_id")
    logged_in = bool(user_id)
    # CTA text: one free AI chat then subscribe 499
    cta_html = ""
    if logged_in:
        db = get_db()
        usage = db.query(AiUsage).filter_by(user_id=user_id).first()
        db.close()
        if usage and usage.ai_used >= 1:
            cta_html = '<a href="/subscribe" class="primary-cta">Get Started – ₹499 / year</a><p class="text-sm text-slate-400 mt-2">Your free AI chat expired. Subscribe for unlimited access.</p>'
        else:
            cta_html = '<a href="/chatbot" class="primary-cta">Start your free AI chat</a><p class="text-sm text-slate-400 mt-2">Every user gets one free full AI chat. Subscribe afterwards for unlimited access.</p>'
    else:
        cta_html = '<a href="/signup" class="primary-cta">Create free account</a><p class="text-sm text-slate-400 mt-2">Signup to get one free AI chat.</p>'

    content = f"""
    <div class="max-w-6xl mx-auto space-y-8">
      <section class="grid md:grid-cols-2 gap-8 items-center">
        <div>
          <h1 class="text-4xl font-bold">CareerInn-Tech — BTech & Hospitality careers in one platform</h1>
          <p class="text-lg text-slate-300 mt-3">Personalized roadmaps, mentors, project bank, interview practice and curated colleges — all in a single student pass.</p>
          <div class="mt-4">{cta_html}</div>
        </div>
        <div class="hero-card rounded-2xl p-6">
          <h3 class="text-xl font-semibold mb-2">Student Pass — ₹499 / year</h3>
          <ul class="text-sm text-slate-200">
            <li>• College explorer (courses & fees)</li>
            <li>• Mentor connect flow & booking</li>
            <li>• 100% focused job & internship guidance (mentorship-based)</li>
            <li>• AI mock interviews & unlimited AI career chats</li>
          </ul>
        </div>
      </section>

      <section>
        <h3 class="text-lg font-semibold mb-3">Explore</h3>
        <div class="grid md:grid-cols-3 gap-4">
          <a href="/courses" class="feature-card">📘 Courses<p class="text-xs text-slate-400">Choose BTech or Hospitality first.</p></a>
          <a href="/colleges" class="feature-card">🏫 Colleges<p class="text-xs text-slate-400">Filtered by track, budget & rating.</p></a>
          <a href="/mentorship" class="feature-card">🧑‍🏫 Mentors<p class="text-xs text-slate-400">Connect with domain mentors.</p></a>
          <a href="/jobs" class="feature-card">💼 Jobs & Placements<p class="text-xs text-slate-400">Choose track to see jobs.</p></a>
          <a href="/prev-papers" class="feature-card">📚 Previous Papers<p class="text-xs text-slate-400">Curated view-only past papers.</p></a>
          <a href="/chatbot" class="feature-card">🤖 AI Career Bot<p class="text-xs text-slate-400">One free chat per user.</p></a>
        </div>
      </section>
    </div>
    """
    return render_page(content, "CareerInn-Tech | Home")

# -------------------- ABOUT/CONTACT/SUPPORT --------------------
@app.route("/about")
def about():
    content = """
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-3">About CareerInn-Tech</h1>
      <p class="text-sm text-slate-300">CareerInn-Tech integrates hospitality and BTech career guidance into one single student-first platform. Personalized roadmaps, mentor connect, project bank, and AI-powered practice.</p>
    </div>
    """
    return render_page(content, "About")

@app.route("/contact")
def contact():
    content = """
    <div class="max-w-4xl mx-auto">
      <h1 class="text-2xl font-bold mb-3">Contact</h1>
      <p class="text-sm text-slate-300">Email: support@careerinn-tech.com</p>
    </div>
    """
    return render_page(content, "Contact")

@app.route("/support")
def support():
    content = """
    <div class="max-w-4xl mx-auto">
      <h1 class="text-2xl font-bold mb-3">Support</h1>
      <p class="text-sm text-slate-300">Need help? Reach out at support@careerinn-tech.com</p>
    </div>
    """
    return render_page(content, "Support")

# -------------------- COURSES --------------------
@app.route("/courses", methods=["GET", "POST"])
def courses():
    # If track not selected, ask user
    track = request.args.get("track")
    if not track:
        # show simple selection UI
        content = """
        <div class="max-w-2xl mx-auto">
          <h2 class="text-2xl font-bold">Choose track</h2>
          <p class="text-sm text-slate-300">Select which track you want courses for.</p>
          <div class="mt-4 flex gap-3">
            <a href="/courses?track=btech" class="primary-cta">BTech</a>
            <a href="/courses?track=hospitality" class="primary-cta">Hospitality</a>
          </div>
        </div>
        """
        return render_page(content, "Courses")
    # show courses for selected track
    db = get_db()
    data = db.query(Course).filter_by(track=track).all()
    db.close()
    cards = ""
    for c in data:
        video = f"<a href='{c.video_link}' target='_blank' class='text-indigo-300 underline text-sm'>Watch video</a>" if c.video_link else ""
        cards += f"<div class='support-box mb-3'><h3 class='font-semibold'>{c.title}</h3><p class='text-sm text-slate-300'>{c.description or ''}</p><div class='mt-2'>{video}</div></div>"
    content = f"""
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl font-bold mb-2">Courses - {'BTech' if track=='btech' else 'Hospitality'}</h2>
      <div class="grid md:grid-cols-2 gap-4">{cards}</div>
      <div class="mt-4"><a href='/' class='px-3 py-1 rounded bg-indigo-600'>Back</a></div>
    </div>
    """
    return render_page(content, "Courses")

# -------------------- COLLEGES --------------------
@app.route("/colleges")
def colleges():
    track = request.args.get("track")
    if not track:
        content = """
        <div class="max-w-2xl mx-auto">
          <h2 class="text-2xl font-bold">Find Colleges — Pick track</h2>
          <div class="mt-4 flex gap-3">
            <a href="/colleges?track=btech" class="primary-cta">BTech Colleges</a>
            <a href="/colleges?track=hospitality" class="primary-cta">Hospitality Colleges</a>
          </div>
        </div>
        """
        return render_page(content, "Colleges")
    # filters retained
    budget = request.args.get("budget", "").strip()
    rating_min = request.args.get("rating", "").strip()
    db = get_db()
    query = db.query(College).filter_by(track=track)
    if budget == "lt1": query = query.filter(College.fees < 100000)
    elif budget == "b1_2": query = query.filter(College.fees.between(100000, 200000))
    elif budget == "b2_3": query = query.filter(College.fees.between(200000, 300000))
    elif budget == "gt3": query = query.filter(College.fees > 300000)
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
        rows += f"<tr><td>{col.name}</td><td>{col.course}</td><td>{col.location}</td><td>₹{col.fees:,}</td><td>{col.rating:.1f}★</td></tr>"
    if not rows:
        rows = "<tr><td colspan='5'>No colleges match this filter yet.</td></tr>"
    sel_any = "selected" if budget == "" else ""
    content = f"""
    <div class="max-w-6xl mx-auto">
      <h2 class="text-2xl font-bold mb-3">Colleges - {'BTech' if track=='btech' else 'Hospitality'}</h2>
      <form method="GET" class="mb-3 grid md:grid-cols-3 gap-3 items-center">
        <input type="hidden" name="track" value="{track}">
        <select name="budget" class="input-box">
          <option value="" {sel_any}>Any budget</option>
          <option value="lt1">Below ₹1,00,000</option>
          <option value="b1_2">₹1,00,000 – ₹2,00,000</option>
          <option value="b2_3">₹2,00,000 – ₹3,00,000</option>
          <option value="gt3">Above ₹3,00,000</option>
        </select>
        <select name="rating" class="input-box">
          <option value="">Any rating</option>
          <option value="3.5">3.5★ & above</option>
          <option value="4.0">4.0★ & above</option>
        </select>
        <button class="px-3 py-2 bg-indigo-600 rounded">Filter</button>
      </form>
      <table class="table"><tr><th>College</th><th>Key Course</th><th>Location</th><th>Fees</th><th>Rating</th></tr>{rows}</table>
      <div class="mt-4"><a href="/" class="px-3 py-1 rounded bg-indigo-600">Back</a></div>
    </div>
    """
    return render_page(content, "Colleges")

# -------------------- JOBS --------------------
@app.route("/jobs")
def jobs():
    track = request.args.get("track")
    if not track:
        content = """
        <div class="max-w-2xl mx-auto">
          <h2 class="text-2xl font-bold">Jobs & Placements — Choose track</h2>
          <div class="mt-4 flex gap-3">
            <a href="/jobs?track=btech" class="primary-cta">BTech Roles</a>
            <a href="/jobs?track=hospitality" class="primary-cta">Hospitality Roles</a>
          </div>
        </div>
        """
        return render_page(content, "Jobs")
    db = get_db()
    data = db.query(Job).filter_by(track=track).all()
    db.close()
    cards = ""
    for j in data:
        cards += f"<div class='support-box mb-3'><h3 class='font-semibold'>{j.title}</h3><p class='text-sm text-slate-300'>Company: {j.company} | Location: {j.location}</p><p class='text-sm text-emerald-300 mt-1'>{j.salary}</p></div>"
    content = f"""
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl font-bold mb-3">Jobs & Placements - {'BTech' if track=='btech' else 'Hospitality'}</h2>
      <div class="grid md:grid-cols-2 gap-4">{cards}</div>
      <div class="mt-4"><a href="/" class="px-3 py-1 rounded bg-indigo-600">Back</a></div>
    </div>
    """
    return render_page(content, "Jobs")

# -------------------- MENTORSHIP --------------------
@app.route("/mentorship")
def mentorship():
    user_id = session.get("user_id")
    if not user_is_subscribed(user_id):
        content = """
        <div class="max-w-3xl mx-auto">
          <h2 class="text-2xl">Mentorship</h2>
          <p class="text-sm text-slate-300">Mentor connections are available to subscribed users. Subscribe to unlock mentor booking and guidance flow.</p>
          <div class="mt-3"><a href="/subscribe" class="primary-cta">Subscribe ₹499 / year</a></div>
        </div>
        """
        return render_page(content, "Mentorship")
    db = get_db()
    mentors = db.query(Mentor).all()
    db.close()
    cards = ""
    for m in mentors:
        cards += f"<div class='support-box mb-3'><h3 class='font-semibold'>{m.name}</h3><p class='text-sm text-slate-300'>{m.experience}</p><p class='text-sm text-indigo-300'>{m.speciality}</p></div>"
    return render_page(f"<div class='max-w-4xl mx-auto'><h2 class='text-2xl mb-3'>Mentors</h2><div class='grid md:grid-cols-2 gap-4'>{cards}</div></div>", "Mentors")

# -------------------- MOCK INTERVIEWS (gated) --------------------
@app.route("/mock-interviews", methods=["GET", "POST"])
def mock_interviews():
    user_id = session.get("user_id")
    if not user_is_subscribed(user_id):
        return render_page("<div class='max-w-3xl mx-auto'><h2 class='text-2xl'>Mock Interviews</h2><p class='text-sm text-slate-300'>Mock interviews and AI mock interviewer require subscription.</p><a href='/subscribe' class='primary-cta'>Subscribe ₹499/yr</a></div>", "Mock Interviews")
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title","").strip()
        notes = request.form.get("notes","").strip()
        link = request.form.get("link","").strip()
        if title:
            db.add(MockInterview(title=title, notes=notes, link=link, uploader_id=user_id))
            db.commit()
            return redirect("/mock-interviews")
    items = db.query(MockInterview).order_by(MockInterview.id.desc()).all()
    db.close()
    cards = ""
    for it in items:
        uploader = " (by you)" if user_id and it.uploader_id == user_id else ""
        cards += f"<div class='support-box mb-3'><h3 class='font-semibold'>{it.title}{uploader}</h3><p class='text-sm text-slate-300'>{it.notes or ''}</p></div>"
    content = f"""
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl mb-3">Mock Interviews & Practice</h2>
      <form method="POST" class="mb-4">
        <input name="title" placeholder="Title" class="input-box mb-2" required>
        <input name="link" placeholder="Optional link" class="input-box mb-2">
        <textarea name="notes" rows="3" placeholder="Notes" class="input-box mb-2"></textarea>
        <button class="submit-btn">Add mock interview</button>
      </form>
      <div class="grid md:grid-cols-2 gap-4">{cards}</div>
    </div>
    """
    return render_page(content, "Mock Interviews")

@app.route("/mock-interviews/ai", methods=["GET","POST"])
def mock_interview_ai():
    user_id = session.get("user_id")
    if not user_is_subscribed(user_id):
        return render_page("<p class='text-sm text-slate-300'>AI Mock Interview requires subscription. <a href='/subscribe' class='text-indigo-300'>Subscribe</a></p>", "AI Mock Interview")
    history = session.get("mock_ai_history", [])
    if request.method == "POST":
        user_msg = request.form.get("message","").strip()
        if user_msg:
            history.append({"role":"user","content":user_msg})
            messages = [{"role":"system","content":"You are an AI mock interviewer. Ask scenario questions, give feedback."}] + history
            groq_client = get_groq_client()
            if groq_client is None:
                reply = "AI not configured. Please set GROQ_API_KEY in the server environment."
            else:
                try:
                    resp = groq_client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7)
                    reply = resp.choices[0].message.content
                except Exception as e:
                    reply = f"AI error: {e}"
            history.append({"role":"assistant","content":reply})
            session["mock_ai_history"] = history
    html = "<div class='max-w-3xl mx-auto space-y-4'><h1 class='text-2xl font-bold'>AI Mock Interview</h1><div class='bg-slate-900 p-4 rounded h-[320px] overflow-auto'>"
    for m in history:
        who = "You" if m["role"]=="user" else "Interviewer"
        cls = "bg-indigo-600" if m["role"]=="user" else "bg-slate-800"
        html += f"<div class='mb-3'><div class='text-xs text-slate-400'>{who}</div><div class='inline-block px-3 py-2 rounded-2xl {cls} text-xs'>{m['content']}</div></div>"
    html += "</div><form method='POST' class='flex gap-2'><input name='message' class='input-box flex-1' placeholder='Type answer or \"start\"...' required><button class='submit-btn'>Send</button></form></div>"
    return render_page(html, "AI Mock Interview")

# -------------------- Previous Papers (view-only) --------------------
@app.route("/prev-papers")
def prev_papers():
    db = get_db()
    items = db.query(PrevPaper).order_by(PrevPaper.year.desc()).all()
    db.close()
    rows = ""
    for p in items:
        link_html = f"<a href='{p.link}' target='_blank' class='text-indigo-300 underline'>Open</a>" if p.link else ""
        rows += f"<tr><td>{p.title}</td><td>{p.year or ''}</td><td>{link_html}</td></tr>"
    if not rows:
        rows = "<tr><td colspan='3'>No papers yet.</td></tr>"
    content = f"""
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl mb-3">Previous Year Question Papers (view-only)</h2>
      <table class="table"><tr><th>Title</th><th>Year</th><th>Link</th></tr>{rows}</table>
    </div>
    """
    return render_page(content, "Previous Papers")

# -------------------- AI Career Chat (one free chat) --------------------
CHATBOT_HTML = """
<div class="max-w-3xl mx-auto space-y-6">
  <h1 class="text-3xl font-bold mb-2">CareerInn AI Mentor</h1>
  {% if not locked %}
    <p class="text-sm text-slate-300 mb-4">You have one free AI career chat. After finishing, subscribe for unlimited access.</p>
  {% else %}
    <p class="text-sm text-slate-300 mb-4">Your free AI career chat is finished. Please subscribe for more guidance (₹499/yr).</p>
  {% endif %}
  <div class="bg-slate-900 p-4 rounded h-[320px] overflow-auto">
    {% if history %}
      {% for m in history %}
        <div class="mb-3">
          {% if m.role == 'user' %}
            <div class="text-xs text-slate-400">You</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-indigo-600 text-xs">{{ m.content }}</div>
          {% else %}
            <div class="text-xs text-slate-400">CareerInn AI</div>
            <div class="inline-block px-3 py-2 rounded-2xl bg-slate-800 text-xs">{{ m.content }}</div>
          {% endif %}
        </div>
      {% endfor %}
    {% else %}
      <p class="text-sm text-slate-400">👋 Hi! Tell me your name and what track (BTech/Hospitality) you'd like guidance on.</p>
    {% endif %}
  </div>
  {% if not locked %}
    <form method="POST" class="flex gap-2">
      <input name="message" autocomplete="off" placeholder="Type your message..." class="flex-1 input-box" required>
      <button class="px-4 py-2 rounded-full bg-indigo-600 text-sm">Send</button>
    </form>
    <form method="POST" action="/chatbot/end"><button class="mt-2 px-3 py-1 rounded-full border border-rose-500 text-rose-200">End & lock free AI chat</button></form>
  {% else %}
    <p class="text-xs text-slate-400 mt-2">Tip: Subscribe to continue with unlimited AI guidance.</p>
  {% endif %}
</div>
"""

@app.route("/chatbot", methods=["GET","POST"])
def chatbot():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    locked = bool(usage and usage.ai_used >= 1)
    db.close()
    history = session.get("ai_history", [])
    if request.method == "POST":
        if locked:
            history.append({"role":"assistant","content":"Your free AI chat ended. Subscribe for more."})
            session["ai_history"] = history
            return render_page(render_template_string(CHATBOT_HTML, history=history, locked=True), "CareerInn AI")
        user_msg = request.form.get("message","").strip()
        if user_msg:
            history.append({"role":"user","content":user_msg})
            messages = [{"role":"system","content":AI_SYSTEM_PROMPT}] + history
            groq_client = get_groq_client()
            if groq_client is None:
                reply = "AI not configured. Please set GROQ_API_KEY in environment to enable AI responses."
            else:
                try:
                    resp = groq_client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7)
                    reply = resp.choices[0].message.content
                except Exception as e:
                    reply = f"AI error: {e}"
            history.append({"role":"assistant","content":reply})
            session["ai_history"] = history
    return render_page(render_template_string(CHATBOT_HTML, history=history, locked=locked), "CareerInn AI")

@app.route("/chatbot/end", methods=["POST"])
def chatbot_end():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
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
    return redirect("/chatbot")

# -------------------- AUTH --------------------
SIGNUP_FORM = """
<form method="POST" class="max-w-md mx-auto space-y-3">
  <h2 class="text-xl font-bold">Create account</h2>
  <input name="name" placeholder="Full name" class="input-box" required>
  <input name="email" placeholder="Email" class="input-box" required>
  <input name="password" placeholder="Password" type="password" class="input-box" required>
  <button class="submit-btn">Signup</button>
  <p class="text-sm text-slate-400">Already have an account? <a href="/login" class="text-indigo-300">Login</a></p>
</form>
"""

LOGIN_FORM = """
<form method="POST" class="max-w-md mx-auto space-y-3">
  <h2 class="text-xl font-bold">Login</h2>
  <input name="email" placeholder="Email" class="input-box" required>
  <input name="password" placeholder="Password" type="password" class="input-box" required>
  <button class="submit-btn">Login</button>
  <p class="text-sm text-slate-400">New? <a href="/signup" class="text-indigo-300">Create account</a></p>
</form>
"""

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","").strip()
        if not name or not email or not password:
            return render_page("<p class='text-red-400'>All fields required.</p>" + SIGNUP_FORM)
        db = get_db()
        if db.query(User).filter(User.email==email).first():
            db.close()
            return render_page("<p class='text-red-400'>Email exists. Login instead.</p>" + LOGIN_FORM)
        hashed = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        db.add(User(name=name, email=email, password=hashed))
        db.commit()
        db.close()
        return redirect("/login")
    return render_page(SIGNUP_FORM)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","").strip()
        db = get_db()
        user = db.query(User).filter(User.email==email).first()
        db.close()
        authenticated = False
        if user:
            try:
                authenticated = check_password_hash(user.password, password)
            except Exception:
                authenticated = (user.password == password)
        if authenticated:
            session["user"] = user.name
            session["user_id"] = user.id
            session["ai_history"] = []
            session["first_time_login"] = True
            return redirect("/dashboard")
        return render_page("<p class='text-red-400'>Invalid credentials.</p>" + LOGIN_FORM)
    return render_page(LOGIN_FORM)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -------------------- SUBSCRIBE --------------------
@app.route("/subscribe", methods=["GET","POST"])
def subscribe():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    db = get_db()
    sub = db.query(Subscription).filter_by(user_id=user_id).first()
    if request.method == "POST":
        if not sub:
            sub = Subscription(user_id=user_id, active=True)
            db.add(sub)
        else:
            sub.active = True
        db.commit()
        db.close()
        return redirect("/dashboard")
    db.close()
    content = """
    <div class="max-w-md mx-auto">
      <h2 class="text-2xl font-bold mb-3">Subscribe — Student Pass ₹499 / year</h2>
      <p class="text-sm text-slate-300">Subscribe to unlock mentors, unlimited AI, mock interviews and college explorer features.</p>
      <form method="POST" class="mt-4"><button class="submit-btn">Subscribe – ₹499 / year (demo)</button></form>
    </div>
    """
    return render_page(content, "Subscribe")

# -------------------- DASHBOARD --------------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    user_name = session["user"]
    tab = request.args.get("tab", "home")
    db = get_db()
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.commit()
    # handle skills/resume saving
    if request.method == "POST":
        if request.form.get("tab") == "skills":
            if not user_is_subscribed(user_id):
                db.close()
                return redirect("/dashboard?tab=skills")
            profile.skills_text = request.form.get("skills_text","").strip()
            profile.target_roles = request.form.get("target_roles","").strip()
            try:
                profile.self_rating = int(request.form.get("self_rating","0"))
            except ValueError:
                profile.self_rating = 0
            db.commit()
            db.close()
            return redirect("/dashboard?tab=skills")
        if request.form.get("tab") == "resume":
            profile.resume_link = request.form.get("resume_link","").strip()
            profile.notes = request.form.get("notes","").strip()
            db.commit()
            db.close()
            return redirect("/dashboard?tab=resume")
    db.close()
    greeting = "Welcome back 👋" if not session.get("first_time_login", False) else "CareerInn-Tech welcomes you 🎉"
    session["first_time_login"] = False
    # quick panels
    skills_text = profile.skills_text or ""
    if not skills_text and user_is_subscribed(user_id):
        skills_text = "Communication, Problem-solving, Teamwork, Domain fundamentals"
    # assemble panels
    home_panel = f"""
    <div class="space-y-4">
      <h2 class="text-2xl font-bold">{greeting}, {user_name}</h2>
      <p class="text-sm text-slate-300">Your student workspace. Edit skills, add resume link, and prepare for interviews.</p>
      <div class="grid md:grid-cols-3 gap-4 mt-4">
        <div class="support-box"><p class="text-xs">Readiness</p><p class="text-2xl font-bold">--/5</p></div>
        <div class="support-box"><p class="text-xs">Target roles</p><p class="text-2xl font-bold">--</p></div>
        <div class="support-box"><p class="text-xs">Resume</p><p class="text-2xl font-bold">{ 'Yes' if profile.resume_link else 'No' }</p></div>
      </div>
      <div class="mt-4 support-box"><h3 class="font-semibold">Top Skills</h3><p class="text-sm text-slate-300 mt-2">{skills_text}</p><div class="mt-2"><a href="/dashboard?tab=skills" class="px-3 py-1 rounded bg-indigo-600">Edit skills</a></div></div>
    </div>
    """
    skills_panel = f"""
    <div class="space-y-4">
      <h2 class="text-2xl font-bold">Skills & Strengths</h2>
      <p class="text-sm text-slate-300">Add skills that matter for your track.</p>
      <form method="POST">
        <input type="hidden" name="tab" value="skills">
        <textarea name="skills_text" rows="4" class="input-box mb-2">{profile.skills_text or ''}</textarea>
        <input name="target_roles" placeholder="Target roles (comma separated)" class="input-box mb-2" value="{profile.target_roles or ''}">
        <input name="self_rating" type="number" min="0" max="5" class="input-box mb-2" value="{profile.self_rating or 0}">
        <button class="submit-btn">Save skills</button>
      </form>
    </div>
    """
    resume_panel = f"""
    <div class="space-y-4">
      <h2 class="text-2xl font-bold">Resume & Notes</h2>
      <form method="POST">
        <input type="hidden" name="tab" value="resume">
        <input name="resume_link" placeholder="Resume link" class="input-box mb-2" value="{profile.resume_link or ''}">
        <textarea name="notes" rows="3" class="input-box mb-2">{profile.notes or ''}</textarea>
        <button class="submit-btn">Save</button>
      </form>
    </div>
    """
    mentors_panel = "<div class='space-y-4'><h2 class='text-2xl font-bold'>Mentorship</h2><p class='text-sm text-slate-300'>Connect with mentors — subscribe to unlock booking.</p></div>"
    faqs_panel = "<div class='space-y-4'><h2 class='text-2xl font-bold'>FAQs</h2><p class='text-sm text-slate-300'>Demo app & sample data.</p></div>"
    panel_html = home_panel if tab=="home" else (skills_panel if tab=="skills" else (resume_panel if tab=="resume" else (mentors_panel if tab=="mentors" else faqs_panel)))
    # sidebar tabs
    def cls(name):
        return "block w-full text-left px-3 py-2 rounded-lg bg-indigo-600 text-white" if tab==name else "block w-full text-left px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800"
    content = f"""
    <div class="max-w-6xl mx-auto">
      <div class="mb-4"><h1 class="text-2xl font-bold">Student Dashboard</h1></div>
      <div class="grid md:grid-cols-[220px,1fr] gap-6">
        <aside class="bg-slate-900 p-4 rounded-2xl">
          <nav class="flex flex-col gap-2">
            <a href="/dashboard?tab=home" class="{cls('home')}">🏠 Home</a>
            <a href="/dashboard?tab=skills" class="{cls('skills')}">⭐ Skills</a>
            <a href="/dashboard?tab=resume" class="{cls('resume')}">📄 Resume</a>
            <a href="/mentorship" class="block px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800">🧑‍🏫 Mentorship</a>
            <a href="/mock-interviews" class="block px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800">🎤 Mock Interviews</a>
            <a href="/prev-papers" class="block px-3 py-2 rounded-lg text-slate-300 hover:bg-slate-800">📚 Question Papers</a>
          </nav>
        </aside>
        <section class="bg-slate-900 p-6 rounded-2xl">{panel_html}</section>
      </div>
    </div>
    """
    return render_page(content, "Dashboard")

# -------------------- PROFILE --------------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")
    user_name = session["user"]
    content = f"""
    <div class="max-w-4xl mx-auto">
      <h1 class="text-2xl font-bold mb-3">Profile — {user_name}</h1>
      <div class="grid md:grid-cols-2 gap-4">
        <div>
          <h3 class="font-semibold mb-2">CareerInn guidance</h3>
          <ul class="text-sm text-slate-300">
            <li>• Focus on core skills, internships and projects</li>
            <li>• Use AI to prepare for interviews</li>
            <li>• Connect with mentors after subscribing</li>
          </ul>
        </div>
        <div>
          <h3 class="font-semibold mb-2">How to use this website (video)</h3>
          <p class="text-xs text-slate-400 mb-2">Place tutorial video at /static/usage.mp4</p>
          <video controls style="width:100%;border-radius:10px;background:#000;">
            <source src="/static/usage.mp4" type="video/mp4">
            Your browser does not support the video tag.
          </video>
        </div>
      </div>
    </div>
    """
    return render_page(content, "Profile")

# -------------------- UPLOADS SERVE --------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)

# -------------------- RUN --------------------
if __name__ == "__main__":
    # default host/port for local dev
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
