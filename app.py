# app.py - CareerInn-Tech (final corrected single-file Flask app)
# Save this file as app.py and run with `python app.py`
import os
from flask import Flask, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# try optional groq import (AI)
try:
    from groq import Groq
except Exception:
    Groq = None

# ------------- CONFIG -------------
app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "careerinn_tech_dev_secret")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careerinn_tech.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------- MODELS -------------
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
    track = Column(String(50), nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String(400), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    salary = Column(String(255), nullable=False)
    track = Column(String(50), nullable=False)

class Mentor(Base):
    __tablename__ = "mentors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    experience = Column(Text, nullable=False)
    speciality = Column(String(255), nullable=False)

class PrevPaper(Base):
    __tablename__ = "prev_papers"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    year = Column(String(20), nullable=True)
    link = Column(String(1000), nullable=True)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=False)

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

# ------------- DB INIT & SEED -------------
def get_db():
    return SessionLocal()

def init_db():
    db = get_db()
    Base.metadata.create_all(bind=engine)

    # seed sample colleges
    if db.query(College).count() == 0:
        seed_colleges = [
            ("IHM Hyderabad", "DD Colony, Hyderabad", 320000, "BSc Hospitality", 4.6, "hospitality"),
            ("IIHM Hyderabad", "Somajiguda", 350000, "BA Hospitality", 4.5, "hospitality"),
            ("JNTU Hyderabad", "Kukatpally", 90000, "B.Tech CSE", 4.1, "btech"),
            ("IIIT Hyderabad", "Gachibowli", 300000, "B.Tech CSE", 4.8, "btech"),
        ]
        for n, loc, fees, course, rating, tr in seed_colleges:
            db.add(College(name=n, location=loc, fees=fees, course=course, rating=rating, track=tr))

    # seed sample courses
    if db.query(Course).count() == 0:
        seed_courses = [
            ("Intro to Programming", "Basic programming for BTech students", "https://example.com/vid1.mp4", "btech"),
            ("Data Structures", "Core DSA for placements", "https://example.com/vid2.mp4", "btech"),
            ("Front Office Basics", "Hospitality front office fundamentals", "https://example.com/vid3.mp4", "hospitality"),
            ("F&B Service", "Food & beverage service training", "https://example.com/vid4.mp4", "hospitality"),
        ]
        for t, d, v, tr in seed_courses:
            db.add(Course(title=t, description=d, video_link=v, track=tr))

    # seed jobs
    if db.query(Job).count() == 0:
        seed_jobs = [
            ("Management Trainee - Front Office", "Taj Group", "Hyderabad", "₹4 LPA", "hospitality"),
            ("Commis Chef", "Marriott", "Bengaluru", "₹2.5 LPA", "hospitality"),
            ("Software Engineer - New Grad", "Startup", "Hyderabad", "₹6 LPA", "btech"),
        ]
        for t, c, loc, sal, tr in seed_jobs:
            db.add(Job(title=t, company=c, location=loc, salary=sal, track=tr))

    # seed mentors
    if db.query(Mentor).count() == 0:
        db.add(Mentor(name="Anita Rao", experience="15 years in hotel operations", speciality="Hotel Ops"))
        db.add(Mentor(name="Dr. Priya", experience="Professor & placement mentor", speciality="BTech - Placements"))

    # seed prev papers
    if db.query(PrevPaper).count() == 0:
        db.add(PrevPaper(title="NCHM JEE - Past Papers (Aglasem)", year="all", link="https://admission.aglasem.com/nchmct-jee-question-paper/"))
        db.add(PrevPaper(title="IIIT Sample Papers", year="recent", link="https://www.iiit.ac.in/admissions/sample-papers"))

    db.commit()
    db.close()

init_db()

# ------------- AI helper -------------
def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or Groq is None:
        return None
    return Groq(api_key=api_key)

# ------------- Base HTML template (no Jinja logic) -------------
BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>__TITLE__</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="/static/style.css">
  <style>
    body { background: linear-gradient(180deg,#040617,#07102a); color: #e6eef6; font-family: Inter, system-ui, -apple-system; margin:0; }
    nav { padding: 12px 28px; display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid rgba(255,255,255,0.03); }
    .logo { display:flex; gap:10px; align-items:center; }
    .logo img { width:44px; height:44px; border-radius:10px; background:#0b1220; padding:6px; }
    .logo .brand { font-weight:700; font-size:18px; }
    .nav-links a { margin-left:16px; color:#cfe7ff; text-decoration:none; font-weight:600; }
    .hero { max-width:1200px; margin:28px auto; display:grid; grid-template-columns: 1fr 380px; gap:28px; padding:16px; align-items:center; }
    .hero h1 { font-size:40px; line-height:1.03; margin:0 0 12px 0; font-weight:800; color:#fff; }
    .hero p { margin:0 0 14px 0; color:#b8c8d8; }
    .cta { display:flex; gap:12px; margin-top:12px; flex-wrap:wrap; }
    .primary-cta { background: linear-gradient(90deg,#6366f1,#10b981); padding:12px 18px; border-radius:12px; color:#fff; font-weight:700; text-decoration:none; display:inline-block; }
    .ghost { padding:10px 14px; border-radius:12px; border:1px solid rgba(255,255,255,0.06); color:#dbeafe; text-decoration:none; display:inline-block; }
    .price-card { background: linear-gradient(180deg,#071028,#081226); border-radius:18px; padding:22px; border:1px solid rgba(255,255,255,0.03); }
    .price-card .price { font-size:36px; color:#7ef0c6; font-weight:800; }
    .features { max-width:1200px; margin:18px auto; padding:16px; }
    .feature-grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:18px; }
    .feature-box { background:#07112a; padding:18px; border-radius:14px; border:1px solid rgba(255,255,255,0.02); min-height:88px; }
    footer { max-width:1200px; margin:24px auto; padding:12px 16px; color:#98a7bd; }
    .ai-fab { position: fixed; right: 26px; bottom: 26px; width:84px; height:84px; border-radius:999px; display:flex; align-items:center; justify-content:center; background: linear-gradient(90deg,#6366f1,#10b981); box-shadow:0 20px 60px rgba(16,185,129,0.12); font-size:36px; cursor:pointer; }
    table { width:100%; border-collapse:collapse; background:transparent; }
    table th, table td { padding:10px 8px; border-bottom:1px solid rgba(255,255,255,0.02); text-align:left; }
    @media(max-width:900px) { .hero { grid-template-columns:1fr; } .price-card { order:-1; } .nav-links { display:none; } }
  </style>
</head>
<body>
  __NAV__
  __CONTENT__
  <div class="ai-fab" onclick="location.href='/chatbot'">🤖</div>
  <footer>
    <div style="display:flex; justify-content:space-between; align-items:center;"><div>© CareerInn-Tech</div><div>support@careerinn-tech.com</div></div>
  </footer>
</body>
</html>
"""

# ------------- helpers for rendering -------------
def build_nav_html():
    user = session.get("user")
    left = f'<div class="logo"><img src="/static/logo.png" alt="logo"><div><div class="brand">CareerInn</div><div style="font-size:12px;color:#9fb3d7">Hospitality · BTech · Careers</div></div></div>'
    if user:
        right = f'<div class="nav-links"><a href="/">Home</a><a href="/about">About</a><a href="/contact">Contact</a><a href="/support">Support</a><a href="/profile" style="margin-left:18px;background:#0b1220;padding:8px 12px;border-radius:12px;color:#e6eef6;text-decoration:none;">{user}</a><a href="/logout" style="margin-left:10px;padding:8px 12px;background:#ef476f;border-radius:12px;color:white;text-decoration:none;">Logout</a></div>'
    else:
        right = '<div class="nav-links"><a href="/">Home</a><a href="/about">About</a><a href="/contact">Contact</a><a href="/support">Support</a><a href="/login" style="margin-left:18px;padding:8px 12px;background:#6366f1;border-radius:12px;color:white;text-decoration:none;">Login</a></div>'
    return f'<nav>{left}{right}</nav>'

def render_page(content_html, title="CareerInn-Tech"):
    nav = build_nav_html()
    html = BASE_HTML.replace("__TITLE__", title).replace("__NAV__", nav).replace("__CONTENT__", content_html)
    return html

def user_is_subscribed(user_id):
    if not user_id:
        return False
    db = get_db()
    s = db.query(Subscription).filter_by(user_id=user_id).first()
    db.close()
    return bool(s and s.active)

# ------------- ROUTES -------------
@app.route("/")
def home():
    user = session.get("user")
    cta = '<a href="/chatbot" class="primary-cta">Try free AI career chat</a>' if user else '<a href="/signup" class="primary-cta">Create free account</a>'
    hero_html = f'''
    <div class="hero">
      <div>
        <div style="font-size:12px;color:#9fb3d7;margin-bottom:10px;">HOSPITALITY · BTECH · CAREERIN</div>
        <h1>Plan your <span style="color:#7ad2ff">hotel & hospitality</span> or <span style="color:#7ef0c6">BTech</span> career in one place.</h1>
        <p>One platform for courses, colleges, mentors, jobs and an AI career guide. Choose your track on the relevant pages.</p>
        <div class="cta">{cta}<a href="/login" class="ghost">Sign in</a></div>
      </div>
      <div class="price-card">
        <div style="font-size:12px;color:#9fb3d7;letter-spacing:2px;">STUDENT PASS</div>
        <div class="price">₹499</div>
        <div style="color:#a8cfc1;margin-top:8px;">per student / year</div>
        <ul style="margin-top:12px;color:#cfe7dd;">
          <li>• College explorer with courses</li>
          <li>• Mentor connect flow</li>
          <li>• Internship & job guidance</li>
          <li>• AI mock interviews</li>
        </ul>
      </div>
    </div>
    '''
    features_html = '''
    <div class="features">
      <h3 style="margin-bottom:12px;">CareerInn Spaces</h3>
      <div class="feature-grid">
        <a class="feature-box" href="/courses"><strong>📘 Courses</strong><div style="color:#9fb3d7;margin-top:8px;font-size:13px;">Choose BTech or Hospitality and watch course videos</div></a>
        <a class="feature-box" href="/colleges"><strong>🏫 Colleges</strong><div style="color:#9fb3d7;margin-top:8px;font-size:13px;">Filter by budget, rating and location</div></a>
        <a class="feature-box" href="/mentorship"><strong>🧑‍🏫 Mentorship</strong><div style="color:#9fb3d7;margin-top:8px;font-size:13px;">Connect with mentors (subscribe)</div></a>
        <a class="feature-box" href="/jobs"><strong>💼 Jobs & Placements</strong><div style="color:#9fb3d7;margin-top:8px;font-size:13px;">Filter by track for role suggestions</div></a>
        <a class="feature-box" href="/prev-papers"><strong>📚 Previous Papers</strong><div style="color:#9fb3d7;margin-top:8px;font-size:13px;">Curated past papers (view only)</div></a>
        <a class="feature-box" href="/chatbot"><strong>🤖 AI Career Bot</strong><div style="color:#9fb3d7;margin-top:8px;font-size:13px;">One free chat per user</div></a>
      </div>
    </div>
    '''
    return render_page(hero_html + features_html, "CareerInn-Tech | Home")

# -- Courses (ask track first) --
@app.route("/courses")
def courses():
    track = request.args.get("track")
    if not track:
        html = '''
        <div style="max-width:800px;margin:30px auto">
          <h2 style="font-size:24px;">Choose track for courses</h2>
          <div style="margin-top:14px;">
            <a class="primary-cta" href="/courses?track=btech">BTech</a>
            <a class="primary-cta" href="/courses?track=hospitality" style="margin-left:12px;">Hospitality</a>
            <a href="/" class="ghost" style="margin-left:12px;">Back</a>
          </div>
        </div>
        '''
        return render_page(html, "Courses")
    db = get_db()
    items = db.query(Course).filter_by(track=track).all()
    db.close()
    cards = ""
    for c in items:
        video_html = f'<div style="margin-top:8px;"><a class="ghost" href="{c.video_link}" target="_blank">Watch video</a></div>' if c.video_link else ""
        cards += f'<div class="feature-box"><strong>{c.title}</strong><div style="color:#9fb3d7;margin-top:8px;">{(c.description or "")}</div>{video_html}</div>'
    content = f'<div style="max-width:1100px;margin:20px auto"><h2 style="font-size:24px;">Courses — {"BTech" if track=="btech" else "Hospitality"}</h2><div class="feature-grid" style="margin-top:16px">{cards}</div><div style="margin-top:18px;"><a href="/" class="ghost">Back home</a></div></div>'
    return render_page(content, "Courses")

# -- Colleges (ask track first) --
@app.route("/colleges")
def colleges():
    track = request.args.get("track")
    if not track:
        html = '''
        <div style="max-width:800px;margin:30px auto">
          <h2 style="font-size:24px;">Choose track for colleges</h2>
          <div style="margin-top:14px;">
            <a class="primary-cta" href="/colleges?track=btech">BTech</a>
            <a class="primary-cta" href="/colleges?track=hospitality" style="margin-left:12px;">Hospitality</a>
          </div>
        </div>
        '''
        return render_page(html, "Colleges")
    budget = request.args.get("budget","")
    rating = request.args.get("rating","")
    db = get_db()
    q = db.query(College).filter_by(track=track)
    if budget == "lt1":
        q = q.filter(College.fees < 100000)
    elif budget == "b1_2":
        q = q.filter(College.fees.between(100000,200000))
    elif budget == "b2_3":
        q = q.filter(College.fees.between(200000,300000))
    elif budget == "gt3":
        q = q.filter(College.fees > 300000)
    if rating:
        try:
            rv = float(rating); q = q.filter(College.rating >= rv)
        except: pass
    items = q.order_by(College.rating.desc()).all()
    db.close()
    rows = ""
    for it in items:
        rows += f'<tr><td>{it.name}</td><td>{it.course}</td><td>{it.location}</td><td>₹{it.fees:,}</td><td>{it.rating:.1f}★</td></tr>'
    if not rows:
        rows = '<tr><td colspan="5">No colleges found.</td></tr>'
    content = f'''
    <div style="max-width:1100px;margin:20px auto">
      <h2 style="font-size:24px;">Colleges — {"BTech" if track=="btech" else "Hospitality"}</h2>
      <form method="GET" style="margin-top:12px;">
        <input type="hidden" name="track" value="{track}">
        <select name="budget" style="padding:8px;border-radius:8px;background:#07112a;color:#e6eef6;">
          <option value="">Any budget</option>
          <option value="lt1">Below ₹1,00,000</option>
          <option value="b1_2">₹1–2 L</option>
          <option value="b2_3">₹2–3 L</option>
          <option value="gt3">Above ₹3 L</option>
        </select>
        <select name="rating" style="padding:8px;border-radius:8px;background:#07112a;color:#e6eef6;margin-left:8px;">
          <option value="">Any rating</option>
          <option value="3.5">3.5★ & above</option>
          <option value="4.0">4.0★ & above</option>
        </select>
        <button type="submit" class="primary-cta" style="margin-left:10px;">Filter</button>
      </form>
      <table class="table" style="margin-top:14px;width:100%;">
        <tr style="text-align:left;color:#9fb3d7;"><th>College</th><th>Course</th><th>Location</th><th>Fees</th><th>Rating</th></tr>
        {rows}
      </table>
      <div style="margin-top:12px;"><a href="/" class="ghost">Back</a></div>
    </div>
    '''
    return render_page(content, "Colleges")

# -- Jobs (ask track first) --
@app.route("/jobs")
def jobs():
    track = request.args.get("track")
    if not track:
        html = '''
        <div style="max-width:800px;margin:30px auto">
          <h2 style="font-size:24px;">Choose track for jobs</h2>
          <div style="margin-top:14px;">
            <a class="primary-cta" href="/jobs?track=btech">BTech</a>
            <a class="primary-cta" href="/jobs?track=hospitality" style="margin-left:12px;">Hospitality</a>
          </div>
        </div>
        '''
        return render_page(html, "Jobs")
    db = get_db()
    items = db.query(Job).filter_by(track=track).all()
    db.close()
    cards = ""
    for j in items:
        cards += f'<div class="feature-box"><strong>{j.title}</strong><div style="color:#9fb3d7;margin-top:8px;">{j.company} • {j.location}</div><div style="color:#7ef0c6;margin-top:6px;">{j.salary}</div></div>'
    content = f'<div style="max-width:1100px;margin:20px auto"><h2 style="font-size:24px;">Jobs — {"BTech" if track=="btech" else "Hospitality"}</h2><div class="feature-grid" style="margin-top:12px">{cards}</div><div style="margin-top:12px;"><a href="/" class="ghost">Back</a></div></div>'
    return render_page(content, "Jobs")

# -- Previous Papers --
@app.route("/prev-papers")
def prev_papers():
    db = get_db()
    items = db.query(PrevPaper).order_by(PrevPaper.year.desc()).all()
    db.close()
    rows = ""
    for p in items:
        rows += f'<tr><td>{p.title}</td><td>{p.year or ""}</td><td><a href="{p.link}" target="_blank" class="ghost">Open</a></td></tr>'
    if not rows:
        rows = '<tr><td colspan="3">No papers</td></tr>'
    content = f'''
    <div style="max-width:900px;margin:20px auto">
      <h2 style="font-size:22px;">Previous Year Papers</h2>
      <table class="table" style="margin-top:12px;">
        <tr style="color:#9fb3d7;"><th>Title</th><th>Year</th><th>Link</th></tr>
        {rows}
      </table>
      <div style="margin-top:12px;"><a href="/" class="ghost">Back</a></div>
    </div>
    '''
    return render_page(content, "Previous Papers")

# -- Mentorship (subscription locked) --
@app.route("/mentorship")
def mentorship():
    if not user_is_subscribed(session.get("user_id")):
        return render_page('<div style="max-width:700px;margin:30px auto"><h2 style="font-size:22px;">Mentorship</h2><p style="color:#9fb3d7">Mentor connect flow is available to subscribed users. Subscribe to unlock.</p><div style="margin-top:12px;"><a href="/subscribe" class="primary-cta">Subscribe ₹499/yr</a> <a href="/" class="ghost" style="margin-left:8px;">Back</a></div></div>', "Mentorship")
    db = get_db()
    mentors = db.query(Mentor).all()
    db.close()
    cards = ''.join([f'<div class="feature-box"><strong>{m.name}</strong><div style="color:#9fb3d7;margin-top:8px;">{m.speciality}</div><div style="color:#a8cfc1;margin-top:6px;">{m.experience}</div></div>' for m in mentors])
    return render_page(f'<div style="max-width:900px;margin:20px auto"><h2>Mentors</h2><div class="feature-grid" style="margin-top:12px">{cards}</div></div>', "Mentors")

# -- Chatbot (one free chat) --
@app.route("/chatbot", methods=["GET","POST"])
def chatbot():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    db.close()
    locked = bool(usage and usage.ai_used >= 1)
    history = session.get("ai_history", [])
    if request.method == "POST":
        if locked:
            history.append({"role":"assistant","content":"Your free AI chat ended. Subscribe for more."})
        else:
            msg = request.form.get("message","").strip()
            if msg:
                history.append({"role":"user","content":msg})
                groq_client = get_groq_client()
                if groq_client is None:
                    reply = "AI is not configured. Set GROQ_API_KEY or use demo content."
                else:
                    try:
                        resp = groq_client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"system","content":"You are a helpful career mentor."}] + [{"role":h["role"],"content":h["content"]} for h in history], temperature=0.7)
                        reply = resp.choices[0].message.content
                    except Exception as e:
                        reply = f"AI error: {e}"
                history.append({"role":"assistant","content":reply})
    session["ai_history"] = history
    blocks = ""
    for h in history:
        who = "You" if h["role"]=="user" else "AI"
        bg = "#0b2133" if h["role"]=="user" else "#07112a"
        blocks += f'<div style="margin-bottom:10px"><div style="font-size:12px;color:#9fb3d7">{who}</div><div style="padding:8px;border-radius:8px;background:{bg};margin-top:6px;">{h["content"]}</div></div>'
    if locked:
        controls = '<div style="margin-top:12px;color:#cfe7ff">Your free AI chat ended. <a href="/subscribe" class="primary-cta" style="margin-left:8px;">Subscribe ₹499/yr</a></div>'
    else:
        controls = '<form method="POST" style="margin-top:10px;display:flex;gap:8px;"><input name="message" placeholder="Type your message..." style="flex:1;padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)"><button class="primary-cta">Send</button></form><form method="POST" action="/chatbot/end" style="margin-top:8px;"><button class="ghost">End & lock free AI chat</button></form>'
    page = f'<div style="max-width:900px;margin:20px auto"><h2 style="font-size:22px;">CareerInn AI Mentor</h2><div style="background:#07112a;padding:12px;border-radius:10px;margin-top:12px;">{blocks or "<div style=color:#9fb3d7>No messages yet</div>"}</div>{controls}</div>'
    return render_page(page, "AI Mentor")

@app.route("/chatbot/end", methods=["POST"])
def chatbot_end():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    db = get_db()
    usage = db.query(AiUsage).filter_by(user_id=user_id).first()
    if usage is None:
        db.add(AiUsage(user_id=user_id, ai_used=1))
    else:
        usage.ai_used = 1
    db.commit()
    db.close()
    session["ai_history"] = []
    return redirect("/chatbot")

# -- Mock interviews --
@app.route("/mock-interviews")
def mock_interviews():
    if not user_is_subscribed(session.get("user_id")):
        return render_page('<div style="max-width:700px;margin:30px auto"><h2>Mock Interviews</h2><p style="color:#9fb3d7">Mock interviews are for subscribed users.</p><div style="margin-top:10px"><a href="/subscribe" class="primary-cta">Subscribe ₹499/yr</a></div></div>', "Mock Interviews")
    db = get_db()
    mentors = db.query(Mentor).all()
    db.close()
    cards = ''.join([f'<div class="feature-box"><strong>{m.name}</strong><div style="color:#9fb3d7;margin-top:8px;">{m.speciality}</div></div>' for m in mentors])
    return render_page(f'<div style="max-width:900px;margin:20px auto"><h2>Mock Interviews</h2><div class="feature-grid" style="margin-top:12px">{cards}</div></div>', "Mock Interviews")

# -- Subscribe --
@app.route("/subscribe", methods=["GET","POST"])
def subscribe():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    db = get_db()
    sub = db.query(Subscription).filter_by(user_id=user_id).first()
    if request.method == "POST":
        if not sub:
            db.add(Subscription(user_id=user_id, active=True))
        else:
            sub.active = True
        db.commit()
        db.close()
        return redirect("/dashboard")
    db.close()
    return render_page('<div style="max-width:700px;margin:30px auto"><h2>Subscribe - ₹499 / year</h2><p style="color:#9fb3d7">Demo subscribe flow. Click to activate for this account.</p><form method="POST" style="margin-top:12px;"><button class="primary-cta">Subscribe – ₹499 / year (demo)</button></form></div>', "Subscribe")

# -- Auth: signup/login/logout --
SIGNUP_HTML = '''
<div style="max-width:500px;margin:30px auto">
  <h2>Create account</h2>
  <form method="POST" style="display:flex;flex-direction:column;gap:10px;margin-top:12px;">
    <input name="name" placeholder="Full name" required style="padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)">
    <input name="email" placeholder="Email" required style="padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)">
    <input name="password" placeholder="Password" type="password" required style="padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)">
    <button class="primary-cta">Signup</button>
  </form>
  <div style="margin-top:10px;"><a href="/login" class="ghost">Already have an account? Login</a></div>
</div>
'''

LOGIN_HTML = '''
<div style="max-width:500px;margin:30px auto">
  <h2>Login</h2>
  <form method="POST" style="display:flex;flex-direction:column;gap:10px;margin-top:12px;">
    <input name="email" placeholder="Email" required style="padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)">
    <input name="password" placeholder="Password" type="password" required style="padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)">
    <button class="primary-cta">Login</button>
  </form>
  <div style="margin-top:10px;"><a href="/signup" class="ghost">New here? Signup</a></div>
</div>
'''

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or not password:
            return render_page('<div style="color:#ef476f">All fields required</div>' + SIGNUP_HTML, "Signup")
        db = get_db()
        if db.query(User).filter(User.email==email).first():
            db.close()
            return render_page('<div style="color:#ef476f">Email exists — login instead.</div>' + LOGIN_HTML, "Signup")
        db.add(User(name=name, email=email, password=generate_password_hash(password)))
        db.commit()
        db.close()
        return redirect("/login")
    return render_page(SIGNUP_HTML, "Signup")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        db = get_db()
        user = db.query(User).filter(User.email==email).first()
        db.close()
        if user and check_password_hash(user.password, password):
            session["user"] = user.name
            session["user_id"] = user.id
            session["ai_history"] = []
            return redirect("/dashboard")
        return render_page('<div style="color:#ef476f">Invalid credentials</div>' + LOGIN_HTML, "Login")
    return render_page(LOGIN_HTML, "Login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -- Dashboard & Profile --
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    user_name = session.get("user")
    db = get_db()
    profile = db.query(UserProfile).filter_by(user_id=session["user_id"]).first()
    if not profile:
        profile = UserProfile(user_id=session["user_id"])
        db.add(profile); db.commit()
    db.close()
    content = f'''
    <div style="max-width:1000px;margin:20px auto">
      <h2 style="font-size:22px;">Welcome, {user_name}</h2>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;">
        <div class="feature-box"><strong>Top skills</strong><div style="color:#9fb3d7;margin-top:8px;">{profile.skills_text or 'No skills yet'}</div></div>
        <div class="feature-box"><strong>Resume</strong><div style="color:#9fb3d7;margin-top:8px;">{profile.resume_link or 'Not added'}</div></div>
      </div>
      <div style="margin-top:12px;"><a href="/profile" class="ghost">View profile</a> <a href="/" class="ghost" style="margin-left:8px">Back</a></div>
    </div>
    '''
    return render_page(content, "Dashboard")

@app.route("/profile", methods=["GET","POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    profile = db.query(UserProfile).filter_by(user_id=session["user_id"]).first()
    if request.method == "POST":
        profile.skills_text = request.form.get("skills_text","").strip()
        profile.resume_link = request.form.get("resume_link","").strip()
        db.commit()
        db.close()
        return redirect("/dashboard")
    db.close()
    content = f'''
    <div style="max-width:900px;margin:20px auto">
      <h2 style="font-size:22px;">Profile</h2>
      <form method="POST" style="margin-top:12px;">
        <textarea name="skills_text" rows="4" style="width:100%;padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04)">{profile.skills_text or ''}</textarea>
        <input name="resume_link" placeholder="Resume link" value="{profile.resume_link or ''}" style="width:100%;padding:10px;border-radius:8px;background:#07112a;color:#e6eef6;border:1px solid rgba(255,255,255,0.04);margin-top:8px;">
        <div style="margin-top:10px;"><button class="primary-cta">Save</button> <a href="/dashboard" class="ghost" style="margin-left:8px;">Cancel</a></div>
      </form>
      <div style="margin-top:16px;">
        <h3 style="font-size:18px;">How to use this website</h3>
        <p style="color:#9fb3d7">Watch the quick tutorial below (place usage.mp4 in /static/usage.mp4)</p>
        <video controls style="width:100%;border-radius:8px;margin-top:8px;background:#000"><source src="/static/usage.mp4" type="video/mp4">Your browser doesn't support video</video>
      </div>
    </div>
    '''
    return render_page(content, "Profile")

# -- About / Contact / Support --
@app.route("/about")
def about():
    return render_page('<div style="max-width:900px;margin:20px auto"><h2>About CareerInn-Tech</h2><p style="color:#9fb3d7;margin-top:8px;">Integrated platform for BTech & Hospitality students.</p></div>', "About")

@app.route("/contact")
def contact():
    return render_page('<div style="max-width:900px;margin:20px auto"><h2>Contact</h2><p style="color:#9fb3d7;margin-top:8px;">support@careerinn-tech.com</p></div>', "Contact")

@app.route("/support")
def support():
    return render_page('<div style="max-width:900px;margin:20px auto"><h2>Support</h2><p style="color:#9fb3d7;margin-top:8px;">Reach out to support@careerinn-tech.com</p></div>', "Support")

# -- static uploads route (optional) --
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ------------- teardown -------------
@app.teardown_appcontext
def remove_session(exception=None):
    try:
        SessionLocal.remove()
    except Exception:
        pass

# ------------- run -------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # debug True for local only
    app.run(debug=True, host="0.0.0.0", port=port)
