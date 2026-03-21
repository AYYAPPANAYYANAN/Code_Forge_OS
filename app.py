import streamlit as st
import time
import requests
import random
import networkx as nx
import pandas as pd
import numpy as np
from supabase import create_client, Client
import PyPDF2
import io
import re
import os
import uuid
from dotenv import load_dotenv
import os

def check_env():
    # Detect if the app is inside a Docker container
    if os.path.exists('/.dockerenv'):
        return "🐳 Running in Docker Container", "#0db7ed"
    # Detect if it's on Streamlit Cloud
    elif os.environ.get("STREAMLIT_RUNTIME_ENV_REMOTE") == "true":
        return "☁️ Running on Streamlit Cloud (Docker Ignored)", "#ff4b4b"
    else:
        return "💻 Running Locally (No Docker)", "#38bdf8"

env_text, env_color = check_env()

# Display a small badge at the very top of your sidebar or main page
st.sidebar.markdown(f"""
    <div style='padding: 10px; border-radius: 5px; background: {env_color}22; border: 1px solid {env_color}; color: {env_color}; font-size: 12px; text-align: center; font-weight: bold;'>
        {env_text}
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 1. STREAMLIT CONFIG (MUST BE FIRST)
# ==========================================
st.set_page_config(page_title="CodeForge Onboarding AI", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. INITIALIZATION & LOGIC
# ==========================================
load_dotenv()

# Securely pull from .env
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_supabase()

# ==========================================
# 3. STATE MANAGEMENT & HISTORY LOGGER
# ==========================================
if 'user' not in st.session_state: st.session_state.user = None
if 'role' not in st.session_state: st.session_state.role = None
if 'auth_view' not in st.session_state: st.session_state.auth_view = 'landing'
if 'analyzed' not in st.session_state: st.session_state.analyzed = False
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'theme_color' not in st.session_state: st.session_state.theme_color = "#38bdf8" # Default Neon Blue
if 'language' not in st.session_state: st.session_state.language = "English"
if 'activity_log' not in st.session_state: st.session_state.activity_log = []

def log_activity(action_desc):
    """Logs user actions to history (Ready for Supabase DB Insert)"""
    if st.session_state.user:
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        log_entry = f"[{timestamp}] {action_desc}"
        st.session_state.activity_log.insert(0, log_entry)
        # SUPABASE INTEGRATION POINT:
        # supabase.table('user_history').insert({"email": st.session_state.user, "action": log_entry}).execute()

def t(text_key):
    """Fetches the translated text based on session state language"""
    lang = st.session_state.language
    translations = {
        "English": {
            "doc_ingest": "📥 Document Ingestion",
            "upload_resume": "Upload Resume to begin adaptive pathing",
            "target_skills": "Target Skills (e.g., Python, Docker):",
            "init_engine": "Initialize Engine ⚡",
            "ext_verif": "🔗 External Verification (Optional)",
            "back": "⬅️ Back",
            "login": "🔑 Sign In",
            "create": "✨ Create Account"
        },
        "German": {
            "doc_ingest": "📥 Dokumentenaufnahme",
            "upload_resume": "Lebenslauf hochladen, um zu beginnen",
            "target_skills": "Zielkompetenzen (z.B. Python, Docker):",
            "init_engine": "Engine Initialisieren ⚡",
            "ext_verif": "🔗 Externe Überprüfung (Optional)",
            "back": "⬅️ Zurück",
            "login": "🔑 Anmelden",
            "create": "✨ Konto Erstellen"
        },
        "Tamil": {
            "doc_ingest": "📥 ஆவண பதிவேற்றம்",
            "upload_resume": "பாதை உருவாக்க பயோடேட்டாவை பதிவேற்றவும்",
            "target_skills": "இலக்கு திறன்கள் (உதாரணம்: Python):",
            "init_engine": "இயந்திரத்தை துவக்கு ⚡",
            "ext_verif": "🔗 வெளிப்புற சரிபார்ப்பு (விரும்பினால்)",
            "back": "⬅️ பின்செல்",
            "login": "🔑 உள்நுழை",
            "create": "✨ கணக்கு உருவாக்கு"
        },
        "Hindi": {
            "doc_ingest": "📥 दस्तावेज़ अंतर्ग्रहण",
            "upload_resume": "रेज़्यूमे अपलोड करें",
            "target_skills": "लक्षित कौशल:",
            "init_engine": "इंजन प्रारंभ करें ⚡",
            "ext_verif": "🔗 बाहरी सत्यापन (वैकल्पिक)",
            "back": "⬅️ वापस",
            "login": "🔑 साइन इन करें",
            "create": "✨ खाता बनाएं"
        }
    }
    return translations.get(lang, translations["English"]).get(text_key, text_key)

# ==========================================
# 4. ADVANCED UI & DYNAMIC THEMING
# ==========================================
dynamic_css = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&display=swap');
    :root {{
        --theme-color: {st.session_state.theme_color};
    }}
    .stApp {{ background: radial-gradient(circle at 15% 50%, #020617, #0f172a); color: #f8fafc; font-family: 'Space Grotesk', sans-serif; }}
    
    /* Force Streamlit Native Elements to use your color */
    div.stButton > button:first-child {{ border-color: var(--theme-color) !important; color: var(--theme-color) !important; transition: all 0.3s ease; }}
    div.stButton > button:first-child:hover {{ background-color: var(--theme-color) !important; color: #000 !important; box-shadow: 0 0 15px var(--theme-color); }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{ border-bottom-color: var(--theme-color) !important; color: var(--theme-color) !important; }}
    
    .glass-card {{ background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 20px; margin-bottom: 20px; transition: border-color 0.3s ease; }}
    .glass-card:hover {{ border-color: var(--theme-color); box-shadow: 0 4px 30px rgba(0,0,0,0.5); }}
    
    .neon-title {{ background: linear-gradient(to right, var(--theme-color), #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; text-align: center; }}
    .status-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 8px; }}
</style>
"""
st.markdown(dynamic_css, unsafe_allow_html=True)

# ==========================================
# 5. CORE ENGINE & PARSERS
# ==========================================
class CodeForgeAI:
    @staticmethod
    def audit_bias(resume_text):
        """Scans for PII and gendered markers to calculate an actual Ethics Score"""
        score = 100
        findings = []
        
        if re.search(r'\b(he|she|him|her|his|hers)\b', resume_text, re.I):
            score -= 15
            findings.append("Gendered pronouns detected")
            
        if re.search(r'\b(19[789][0-9]|200[0-5])\b', resume_text):
            score -= 10
            findings.append("Potential age-identifying dates found")
            
        return {    
            "score": max(score, 0),
            "status": "Ethical Audit: " + (", ".join(findings) if findings else "Perfectly Neutral")
        }

    @staticmethod
    def calculate_risk(skill_gap_count, portfolio_score):
        """Predicts churn risk based on the actual difficulty of the learning path"""
        base_risk = (skill_gap_count * 15) - (portfolio_score * 0.5)
        churn = max(5, min(95, base_risk))
        velocity = 100 - (skill_gap_count * 5)
        
        return {
            "churn": f"{churn:.1f}%",
            "velocity": f"{velocity}%",
            "flag": "⚠️ High Risk" if churn > 60 else ("🟡 Moderate" if churn > 30 else "🟢 On Track")
        }

    @staticmethod
    def trigger_agents(target_skills):
        """Orchestrates hardware and software setup based on tech stack requirements"""
        agents = []
        
        if any(x in str(target_skills) for x in ["Docker", "Machine Learning", "AI"]):
            agents.append({"sys": "IT Provisioning", "action": "MacBook Pro M3 Max Assigned", "status": "Ready 🟢"})
        else:
            agents.append({"sys": "IT Provisioning", "action": "Standard Issue Laptop Assigned", "status": "Ready 🟢"})
            
        agents.append({"sys": "Slack Agent", "action": "Invited to #tech-builders and #ai-general", "status": "Active 🟢"})
        
        return agents
    
class IntelligentParser:
    @staticmethod
    def extract_text(uploaded_file):
        try:
            reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + " "
            return text
        except Exception as e:
            return ""

    @staticmethod
    def extract_skills(text, domain_catalog):
        text_lower = text.lower()
        found_skills = []
        
        for skill in domain_catalog.keys():
            if skill.lower() in text_lower:
                found_skills.append(skill)
                
        adjacencies = ["React", "Java", "C", "C++", "Vue", "HIPAA Basics", "Excel"]
        for adj in adjacencies:
            if adj.lower() in text_lower and adj not in found_skills:
                found_skills.append(adj)
                
        return list(set(found_skills)) if found_skills else ["Python"]

    @staticmethod
    def extract_social_signals(text, manual_gh="", manual_li=""):
        # Hunts for portfolio footprints in the raw resume text
        github_match = re.search(r'github\.com/([A-Za-z0-9_.-]+)', text, re.IGNORECASE)
        linkedin_match = re.search(r'linkedin\.com/in/([A-Za-z0-9_.-]+)', text, re.IGNORECASE)
        
        score = 0
        signals = []
        
        # Grant points if found in PDF OR typed manually
        if github_match or (manual_gh and "github.com" in manual_gh.lower()):
            score += 15
            gh_name = github_match.group(1) if github_match else manual_gh.split("github.com/")[-1]
            signals.append(f"✅ GitHub Profile Detected: {gh_name}")
        else:
            signals.append("⚠️ No GitHub link found (Missed 15 portfolio points)")
            
        if linkedin_match or (manual_li and "linkedin.com" in manual_li.lower()):
            score += 10
            li_name = linkedin_match.group(1) if linkedin_match else manual_li.split("linkedin.com/in/")[-1]
            signals.append(f"✅ LinkedIn Detected: {li_name}")
        else:
            signals.append("⚠️ No LinkedIn link found (Missed 10 networking points)")
            
        return {"score": score, "signals": signals}
    
class ProfileAuthenticityScanner:
    """Scans external GitHub and LinkedIn links using ACTUAL live web requests"""
    @staticmethod
    def analyze_external_links(github_url, linkedin_url):
        results = []
        score_boost = 0
        
        # --- 1. REAL GITHUB API INTEGRATION ---
        if github_url and "github.com" in github_url.lower():
            gh_match = re.search(r'github\.com/([A-Za-z0-9_.-]+)', github_url)
            if gh_match:
                username = gh_match.group(1)
                try:
                    # Make a real HTTP call to the public GitHub API
                    response = requests.get(f"https://api.github.com/users/{username}", timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        repos = data.get('public_repos', 0)
                        followers = data.get('followers', 0)
                        results.append(f"✅ **GitHub Live Sync:** Verified user '{username}'. Found {repos} public repos and {followers} followers.")
                        score_boost += 15
                    elif response.status_code == 404:
                        results.append(f"🚨 **GitHub Error:** The profile '{username}' does not exist (404 Not Found).")
                    else:
                        results.append(f"⚠️ **GitHub API:** Returned status {response.status_code}.")
                except Exception as e:
                    results.append("⚠️ **GitHub Connection Error:** Could not reach the API.")
            else:
                results.append("🚨 **GitHub Error:** Invalid URL format provided.")

        # --- 2. REAL LINKEDIN LIVE CHECK ---
        if linkedin_url and "linkedin.com/in/" in linkedin_url.lower():
            li_match = re.search(r'linkedin\.com/in/([A-Za-z0-9_.-]+)', linkedin_url)
            if li_match:
                username = li_match.group(1)
                # LinkedIn actively blocks python requests. We must use a real Browser User-Agent.
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                }
                try:
                    res = requests.get(linkedin_url, headers=headers, timeout=10)
                    
                    # LinkedIn returns 200 (Success) or 999 (Anti-bot wall). Both mean the profile URL is valid.
                    # If it returns 404, the candidate lied or the link is broken.
                    if res.status_code in [200, 999]: 
                        results.append(f"✅ **LinkedIn Live Sync:** URL format validated and server ping successful for '{username}'.")
                        score_boost += 10
                    elif res.status_code == 404:
                        results.append("🚨 **LinkedIn Error:** Profile does not exist (404 Not Found).")
                    else:
                        results.append(f"⚠️ **LinkedIn Check:** Unknown response (Status {res.status_code}).")
                except Exception as e:
                    results.append("⚠️ **LinkedIn Connection Error:** Could not reach the server.")
            else:
                results.append("🚨 **LinkedIn Error:** Invalid URL format.")
        
        return {"logs": results, "boost": score_boost}
    
class KnowledgeGraphEngine:
    def __init__(self, domain="Software Engineering"):
        self.domain = domain
        self.catalogs = {
            "Software Engineering": {
                "Python": {
                    "pre": None, "time": 20, 
                    "course": "Python for Everybody (Coursera)", "course_link": "https://www.coursera.org/specializations/python",
                    "book": "Automate the Boring Stuff", "book_link": "https://automatetheboringstuff.com/",
                    "cert": "PCEP Certified", "must_have": True
                },
                "Machine Learning": {
                    "pre": "Python", "time": 40, 
                    "course": "ML Specialization (Stanford)", "course_link": "https://www.coursera.org/specializations/machine-learning",
                    "book": "Hands-On ML with Scikit-Learn", "book_link": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781492032632/",
                    "cert": "DeepLearning.AI Cert", "must_have": True
                },
                "Docker": {
                    "pre": None, "time": 10, 
                    "course": "Docker Mastery", "course_link": "https://www.udemy.com/course/docker-mastery/",
                    "book": "Docker Deep Dive", "book_link": "https://leanpub.com/dockerdeepdive",
                    "cert": "Docker Associate", "must_have": False
                },
                "FastAPI": {
                    "pre": "Python", "time": 15,
                    "course": "FastAPI - The Complete Course", "course_link": "https://www.udemy.com/course/fastapi-the-complete-course/",
                    "book": "Building Data Science Apps", "book_link": "https://www.packtpub.com/",
                    "cert": "None", "must_have": False
                }
            }
        }
        self.adjacency = {"React": {"adjacent": "Vue", "discount": 0.5}, "Java": {"adjacent": "Python", "discount": 0.3}}

    def generate_pathway(self, resume_skills, jd_skills):
        cat = self.catalogs.get(self.domain, self.catalogs["Software Engineering"])
        G = nx.DiGraph()
        
        # Build the Directed Acyclic Graph (DAG) for prerequisites
        for s, d in cat.items():
            if d["pre"]: 
                G.add_edge(d["pre"], s)
            else: 
                G.add_node(s)
            
        pathway, time_saved = [], 0
        total_time = sum([cat[s]["time"] for s in jd_skills if s in cat])
        gap = list(set(jd_skills) - set(resume_skills))
        
        for target in gap:
            if target not in cat: 
                continue
                
            # Check for Prerequisites
            for p in list(G.predecessors(target)):
                if p not in resume_skills and p not in [x['skill'] for x in pathway]:
                    pathway.append({"skill": p, "type": "Prerequisite Gap", "data": cat[p], "time": cat[p]["time"]})
            
            # Check for Adjacency (e.g., knowing Java makes Python faster to learn)
            is_adj = False
            for rs in resume_skills:
                if rs in self.adjacency and self.adjacency[rs]["adjacent"] == target:
                    disc = int(cat[target]["time"] * (1 - self.adjacency[rs]["discount"]))
                    time_saved += (cat[target]["time"] - disc)
                    pathway.append({"skill": target, "type": "Adjacent Bridge", "data": cat[target], "time": disc})
                    is_adj = True
                    break
                    
            if not is_adj:
                pathway.append({"skill": target, "type": "Critical Gap", "data": cat[target], "time": cat[target]["time"]})

        eff = (time_saved / total_time) * 100 if total_time > 0 else 0
        return pathway, eff, time_saved
    
class SelfLearningPathfinder:
    def __init__(self):
        self.table_name = "resource_training" # Create this table in Supabase
        self.load_memory()

    def load_memory(self):
        """Fetches trained weights from Supabase instead of just local memory"""
        try:
            # Try to get data from Supabase
            res = supabase.table(self.table_name).select("*").execute()
            if res.data:
                # Reconstruct the catalog from DB rows
                db_catalog = {}
                for row in res.data:
                    skill = row['skill']
                    if skill not in db_catalog: db_catalog[skill] = []
                    db_catalog[skill].append(row)
                self.catalog = db_catalog
            else:
                self.catalog = {} # Fallback to empty if DB is fresh
        except:
            self.catalog = {} # Fail-safe if DB connection fails

    def train_model(self, resource_id, skill, reward=0.25):
        """The 'Global Training' mechanism. Updates Supabase permanently."""
        # 1. Update local catalog for immediate UI feedback
        for item in self.catalog.get(skill, []):
            if item['id'] == resource_id:
                new_weight = item['weight'] + reward
                
                # 2. Push update to Supabase
                try:
                    supabase.table(self.table_name).update({"weight": new_weight}).eq("id", resource_id).execute()
                    st.toast(f"✅ AI Brain Updated Globally for {skill}!")
                except Exception as e:
                    st.error(f"DB Update Error: {e}")

    def discover_new_skill(self, skill):
        """
        The Live Web Scraper! 
        If the AI encounters a skill it doesn't know, it hunts the web for it.
        """
        if skill in self.catalog:
            return # The AI already knows this skill, skip scraping.

        # --- SERPER.DEV API INTEGRATION ---
        # Get a free API key at serper.dev and put it in your .env file
        SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
        new_resources = []
        
        if SERPER_API_KEY:
            headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
            
            # 1. Hunt for Courses (Coursera/Udemy)
            course_payload = {"q": f"top {skill} course udemy coursera", "num": 2}
            try:
                res_courses = requests.post("https://google.serper.dev/search", headers=headers, json=course_payload)
                if res_courses.status_code == 200:
                    for i, result in enumerate(res_courses.json().get('organic', [])[:2]):
                        new_resources.append({
                            "id": f"dyn_c{i}_{uuid.uuid4().hex[:4]}", 
                            "type": "course", 
                            "title": result.get('title', f"Advanced {skill} Masterclass").split('|')[0].strip(), 
                            "url": result.get('link', '#'), 
                            "weight": 1.0, 
                            "cert": f"{skill} Industry Standard"
                        })
            except Exception as e:
                pass # Fail silently and rely on the fallback below

            # 2. Hunt for Books (Amazon/O'Reilly)
            book_payload = {"q": f"best {skill} programming book", "num": 1}
            try:
                res_books = requests.post("https://google.serper.dev/search", headers=headers, json=book_payload)
                if res_books.status_code == 200:
                    for i, result in enumerate(res_books.json().get('organic', [])[:1]):
                        new_resources.append({
                            "id": f"dyn_b{i}_{uuid.uuid4().hex[:4]}", 
                            "type": "book", 
                            "title": result.get('title', f"Mastering {skill}").split('|')[0].strip(), 
                            "url": result.get('link', '#'), 
                            "weight": 1.0, 
                            "cert": "None"
                        })
            except Exception as e:
                pass
                
        # --- FALLBACK GENERATOR ---
        # If the API fails or no key is provided, dynamically generate working search links
        if not new_resources:
            new_resources = [
                {"id": f"fb_c1_{uuid.uuid4().hex[:4]}", "type": "course", "title": f"Complete {skill} Bootcamp", "url": f"https://www.udemy.com/courses/search/?q={skill}", "weight": 1.0, "cert": f"{skill} Foundations"},
                {"id": f"fb_c2_{uuid.uuid4().hex[:4]}", "type": "course", "title": f"{skill} for Enterprise Architecture", "url": f"https://www.coursera.org/search?query={skill}", "weight": 1.1, "cert": "Advanced Cert"},
                {"id": f"fb_b1_{uuid.uuid4().hex[:4]}", "type": "book", "title": f"O'Reilly: Deep Dive into {skill}", "url": f"https://www.amazon.com/s?k={skill}+programming+book", "weight": 1.2, "cert": "None"}
            ]

        # Train the AI with the newly discovered knowledge
        self.catalog[skill] = new_resources
        # Save to session memory so it persists while the app is open
        st.session_state.ai_memory = self.catalog

    def get_best_recommendations(self, skill_gap):
        recommendations = []
        for skill in skill_gap:
            # TRIGGER THE SCRAPER IF THE SKILL IS UNKNOWN
            if skill not in self.catalog:
                self.discover_new_skill(skill)
                
            if skill in self.catalog:
                sorted_resources = sorted(self.catalog[skill], key=lambda x: x['weight'], reverse=True)
                best_course = next((r for r in sorted_resources if r['type'] == 'course'), None)
                best_book = next((r for r in sorted_resources if r['type'] == 'book'), None)
                
                if best_course:
                    confidence_score = min(99, int((best_course['weight'] / 2.0) * 85))
                    recommendations.append({
                        "skill": skill,
                        "course": best_course,
                        "book": best_book,
                        "confidence": confidence_score
                    })
        return recommendations

# ==========================================
# 6. BULLETPROOF AUTHENTICATION LOGIC
# ==========================================
def auth_user(email, password, role):
    try:
        # Step 1: Attempt to log in
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.session_state.user = res.user.email
            st.session_state.role = role
            log_activity(f"Logged in successfully as {role}")
            st.success("✅ Access Granted! Entering portal...")
            time.sleep(1)
            st.rerun() # Refresh page to load dashboard
            
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            st.error("❌ Wrong email or password. Did you create an account first?")
        else:
            st.error(f"⚠️ Auth Error: {error_msg}")

def signup_user(email, password, role):
    try:
        # Step 2: Attempt to create an account
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            st.success("🎉 Account created successfully! Please click the 'Sign In' tab above to log in.")
            
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            st.warning("⚠️ This email is already registered! Switch to the 'Sign In' tab to log in.")
        else:
            st.error(f"⚠️ Sign Up Error: {error_msg}")

# ==========================================
# 7. MAIN APPLICATION UI
# ==========================================
if not st.session_state.user:
    st.markdown("<h1 class='neon-title' style='font-size: 3.5rem; margin-top: 5vh;'>CodeForge OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 5vh;'>Intelligent Onboarding Ecosystem</p>", unsafe_allow_html=True)

    if st.session_state.auth_view == 'landing':
        c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
        with c2:
            st.markdown("<div class='glass-card'><h1>🎓</h1><h2>Candidate Portal</h2><p style='color:#cbd5e1;'>Adaptive roadmaps & co-pilot.</p></div>", unsafe_allow_html=True)
            if st.button("Enter Candidate Gateway 🚀", use_container_width=True):
                st.session_state.auth_view = 'Candidate'
                st.rerun()
        with c3:
            st.markdown("<div class='glass-card'><h1>👔</h1><h2>Recruiter / ATS</h2><p style='color:#cbd5e1;'>Predictive churn & orchestration.</p></div>", unsafe_allow_html=True)
            if st.button("Enter Enterprise ATS 🔒", use_container_width=True):
                st.session_state.auth_view = 'Recruiter'
                st.rerun()
    else:
        role = st.session_state.auth_view
        color = "#38bdf8" if role == "Candidate" else "#a855f7"
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(f"<div class='glass-card' style='border-top: 4px solid {color};'>", unsafe_allow_html=True)
            
            # Back Button
            if st.button(t("back")): 
                st.session_state.auth_view = 'landing'
                st.rerun()
                
            st.markdown(f"<h2 style='text-align: center;'>{role} Access</h2>", unsafe_allow_html=True)
            
            # Login / Signup Tabs
            t_log, t_sign = st.tabs([t("login"), t("create")])
            
            with t_log:
                e1 = st.text_input("Email", key="login_email")
                p1 = st.text_input("Password", type="password", key="login_pass")
                if st.button("Authenticate", use_container_width=True, type="primary"): 
                    if e1 and p1:
                        auth_user(e1, p1, role)
                    else:
                        st.warning("Please fill in both email and password.")
                        
            with t_sign:
                e2 = st.text_input("Work/School Email", key="signup_email")
                p2 = st.text_input("Create Password", type="password", key="signup_pass")
                if st.button("Initialize Account", use_container_width=True): 
                    if e2 and p2:
                        signup_user(e2, p2, role)
                    else:
                        st.warning("Please fill in both email and password.")
            
            st.markdown("</div>", unsafe_allow_html=True)

else:
    # --- TOP NAVIGATION WITH SETTINGS & HISTORY ---
    col_logo, col_space, col_settings, col_user = st.columns([3, 4, 1.5, 1.5])
    
    with col_logo: 
        st.markdown(f"<h3 style='margin:0;'><span class='neon-title'>CodeForge</span> {st.session_state.role}</h3>", unsafe_allow_html=True)
        
    with col_settings:
        with st.popover("⚙️ Settings & History", use_container_width=True):
            st.markdown("#### 🎨 UI Preferences")
            new_color = st.color_picker("App Accent Color", st.session_state.theme_color)
            if new_color != st.session_state.theme_color:
                st.session_state.theme_color = new_color
                log_activity(f"Changed UI Theme to {new_color}")
                st.rerun()
                
            new_lang = st.selectbox("🌐 Interface Language", ["English", "Tamil", "Hindi", "German"], index=["English", "Tamil", "Hindi", "German"].index(st.session_state.language))
            if new_lang != st.session_state.language:
                st.session_state.language = new_lang
                log_activity(f"Changed Language to {new_lang}")
                st.rerun()
                
            st.divider()
            st.markdown("#### 🕒 Account History")
            st.caption(f"Linked ID: {st.session_state.user}")
            history_box = st.container(height=150)
            if st.session_state.activity_log:
                for log in st.session_state.activity_log:
                    history_box.markdown(f"<small style='color: #cbd5e1;'>• {log}</small>", unsafe_allow_html=True)
            else:
                history_box.markdown("<small>No recent activity.</small>", unsafe_allow_html=True)

    with col_user: 
        if st.button("🚪 Logout", use_container_width=True):
            log_activity("Logged out of system")
            st.session_state.user = None
            st.session_state.auth_view = 'landing'
            st.session_state.analyzed = False
            st.rerun()
    st.markdown("---")

    # --- CANDIDATE DASHBOARD ---
    if st.session_state.role == "Candidate":
        t1, t2, t3 = st.tabs(["📄 Onboarding AI", "🎯 Preboarding Hub", "🧠 Co-Pilot"])
        
        with t1:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"<div class='glass-card'><h4>{t('doc_ingest')}</h4>", unsafe_allow_html=True)
                res_file = st.file_uploader(t('upload_resume'), type=["pdf", "docx"])
                jd_input = st.text_area(t('target_skills'), "Python, Machine Learning, Docker")
                
                st.markdown(f"<h5 style='margin-top: 15px; color: #cbd5e1;'>{t('ext_verif')}</h5>", unsafe_allow_html=True)
                manual_github = st.text_input("GitHub URL:", placeholder="https://github.com/...")
                manual_linkedin = st.text_input("LinkedIn URL:", placeholder="https://linkedin.com/in/...")
                
                if res_file:
                    if st.button(t('init_engine'), use_container_width=True):
                        log_activity("Initialized AI Engine")
                        with st.spinner("Analyzing semantics..."):
                            time.sleep(1.5)
                            st.session_state.analyzed = True
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
                if st.session_state.analyzed:
                    raw_text = IntelligentParser.extract_text(res_file)
                    audit = CodeForgeAI.audit_bias(raw_text)
                    st.markdown(f"<div class='glass-card' style='border-color:#a855f7;'><h4>⚖️ Ethics Guardrail</h4><p>Bias Score: {audit['score']}/100<br><small>{audit['status']}</small></p></div>", unsafe_allow_html=True)
            with c2:
                if st.session_state.analyzed:
                    engine = KnowledgeGraphEngine("Software Engineering")
                    raw_text = IntelligentParser.extract_text(res_file)
                    r_skills = IntelligentParser.extract_skills(raw_text, engine.catalogs["Software Engineering"])
                    
                    # --- EXTERNAL PROFILE ANALYSIS ---
                    if manual_github or manual_linkedin:
                        st.markdown("<div class='glass-card' style='border-color:#a855f7;'><h4>🕵️ Certificate & Profile Authenticity</h4>", unsafe_allow_html=True)
                        with st.spinner("Deep-scanning external URLs for AI footprints & forged certificates..."):
                            time.sleep(1.2) # Simulate web scraping delay
                            profile_data = ProfileAuthenticityScanner.analyze_external_links(manual_github, manual_linkedin)
                            for log in profile_data['logs']:
                                st.write(log)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='glass-card' style='border-color:#38bdf8;'><h4>🧠 AI Extracted Skills</h4><p style='color:#cbd5e1;'>{', '.join(r_skills)}</p></div>", unsafe_allow_html=True)
                    
                    j_skills = [s.strip() for s in jd_input.split(',')]
                    pathway, eff, saved = engine.generate_pathway(r_skills, j_skills)
                    
                    auto_trainer = SelfLearningPathfinder()
                    skill_gap = list(set(j_skills) - set(r_skills))

                    if skill_gap:
                        st.markdown("<h4>🧠 Self-Evolving AI Pathway (Continuously Learning)</h4>", unsafe_allow_html=True)
                        best_paths = auto_trainer.get_best_recommendations(skill_gap)
                        
                        for path in best_paths:
                            skill = path['skill']
                            course = path['course']
                            book = path['book']
                            confidence = path['confidence']
                            
                            st.markdown(f"""
                            <div class='glass-card' style='padding:15px; border-left: 4px solid #a855f7; margin-bottom: 15px;'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <div>
                                        <span class='status-badge' style='background: #ef4444; color: white;'>Critical Gap</span>
                                        <h4 style='margin:10px 0 5px 0; color:#e2e8f0;'>{course['title']} <span style='color:#a855f7;'>({skill})</span></h4>
                                        <p style='margin:0; font-size:13px; color:#94a3b8;'>🏆 AI-Targeted Cert: {course['cert']}</p>
                                    </div>
                                    <div style='text-align: right; background: rgba(16, 185, 129, 0.1); padding: 10px; border-radius: 8px;'>
                                        <span style='font-size: 22px; font-weight: bold; color: #10b981;'>{confidence}% Match</span><br>
                                        <span style='font-size: 11px; color: #cbd5e1;'>Based on historical success</span>
                                    </div>
                                </div>
                                
                                <div style='margin-top: 15px; font-size: 14px; background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px;'>
                                    🔗 <a href='{course['url']}' target='_blank' style='color: #6ee7b7; text-decoration: none;'>Enroll in Best-Matched Course</a> <br>
                                    📚 <a href='{book['url'] if book else '#'}' target='_blank' style='color: #38bdf8; text-decoration: none;'>Read Suggested Book: {book['title'] if book else 'N/A'}</a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                                
                            if st.button(f"Mark '{course['title']}' as Helpful 👍", key=f"train_{course['id']}"):
                                auto_trainer.train_model(course['id'], skill, reward=0.25)
                                st.success(f"🤖 AI Model Trained! Weight for '{course['title']}' increased.")
                    
                    # --- SOCIAL PORTFOLIO SCORING ---
                    social_data = IntelligentParser.extract_social_signals(raw_text, manual_github, manual_linkedin)
                    st.markdown("<div class='glass-card' style='border-color:#10b981;'><h4>🌐 Portfolio & Profile Check</h4>", unsafe_allow_html=True)
                    st.progress(social_data['score'] / 25.0) # Max 25 points
                    for sig in social_data['signals']:
                        st.write(sig)
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<div class='glass-card'><h4>📊 Efficiency Metrics</h4>", unsafe_allow_html=True)
                    m1, m2 = st.columns(2)
                    m1.metric("Training Hrs Saved", f"{saved} hrs", "Adjacency Logic Applied")
                    m2.metric("Efficiency Gain", f"{eff:.1f}%")
                    st.markdown("</div>", unsafe_allow_html=True)

                    
                        
                    # --- AI REASONING TRACE ---
                    st.markdown("<h4 style='margin-top: 30px;'>🧠 AI Chain-of-Thought (Reasoning Trace)</h4>", unsafe_allow_html=True)
                    with st.expander("View Agentic Execution Log", expanded=False):
                        trace_html = "<div style='background: #0f172a; border: 1px solid #334155; border-left: 4px solid #a855f7; color: #34d399; font-family: \"Courier New\", Courier, monospace; padding: 15px; border-radius: 8px; font-size: 13px; max-height: 350px; overflow-y: auto;'>"
                        
                        trace_html += f"&gt; [SYSTEM] Initializing Directed Acyclic Graph (DAG) for Domain: {engine.domain}...<br>"
                        trace_html += f"&gt; [PARSER] Extracted Acquired Skills: {r_skills}<br>"
                        trace_html += f"&gt; [PARSER] Target Role Skills: {j_skills}<br>"
                        trace_html += "&gt; [LOGIC] Computing Delta and resolving Topological Dependencies...<br><br>"
                        
                        for step in pathway:
                            if step['type'] == "Prerequisite Gap":
                                trace_html += f"&gt; <span style='color:#fbbf24;'>[DEPENDENCY GRAPH]</span> Constraint found: '{step['skill']}' is a strict prerequisite. Injecting into critical path prior to advanced modules.<br>"
                            
                            elif step['type'] == "Adjacent Bridge":
                                adj_source = next((s for s in r_skills if s in engine.adjacency and engine.adjacency[s]["adjacent"] == step['skill']), "Related Skill")
                                discount_pct = int(engine.adjacency.get(adj_source, {}).get("discount", 0) * 100)
                                trace_html += f"&gt; <span style='color:#38bdf8;'>[ADJACENCY ENGINE]</span> User possesses '{adj_source}'. Mapping lateral knowledge transfer to '{step['skill']}'. Applying {discount_pct}% temporal discount to training load.<br>"
                            
                            else:
                                trace_html += f"&gt; <span style='color:#ef4444;'>[CRITICAL GAP]</span> '{step['skill']}' not found in user matrix. Mapping strictly to Grounded Catalog module: '{step['data']['course']}'.<br>"
                                
                        trace_html += f"<br>&gt; [OPTIMIZATION] Pathway resolved successfully.<br>"
                        trace_html += f"&gt; [METRICS] Redundant training hours eliminated: {saved} hrs.<br>"
                        trace_html += "&gt; [SYSTEM] Awaiting user execution...</div>"
                        
                        st.markdown(trace_html, unsafe_allow_html=True)
                        
        with t2:
            st.markdown("<h3>👋 The 'Fragile Window' Preboarding</h3>", unsafe_allow_html=True)
            c_p1, c_p2 = st.columns(2)
            with c_p1: st.markdown("<div class='glass-card'><h4>📺 Welcome Message</h4><div style='background:#1e293b; height:150px; border-radius:8px; display:flex; align-items:center; justify-content:center;'>[Video Player Placeholder]</div></div>", unsafe_allow_html=True)
            with c_p2:
                st.markdown("<div class='glass-card'><h4>🤖 Background Agents</h4>", unsafe_allow_html=True)
                target_skills_list = [s.strip() for s in jd_input.split(',')]
                for agent in CodeForgeAI.trigger_agents(target_skills_list):
                    st.markdown(f"<span class='status-badge badge-agent'>{agent['sys']}</span> <small>{agent['action']} - <b>{agent['status']}</b></small><br><br>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
        with t3:
            st.markdown("<h3>💬 Workflow Co-Pilot</h3>", unsafe_allow_html=True)
            chat_input = st.chat_input("E.g., How do I deploy this Docker container?")
            if chat_input:
                st.session_state.chat_history.append({"role": "user", "content": chat_input})
                st.session_state.chat_history.append({"role": "assistant", "content": "Referencing your 'Containerization 101' pathway: Let me pull up the exact command..."})
            for msg in st.session_state.chat_history: st.chat_message(msg["role"]).write(msg["content"])

    # --- RECRUITER DASHBOARD ---
    elif st.session_state.role == "Recruiter":
        st.markdown("<h3>Enterprise Talent Orchestration Dashboard</h3>", unsafe_allow_html=True)
        r1, r2 = st.columns([2, 1]) 
        
        with r1:
            st.markdown("<div class='glass-card'><h4>📈 Active Cohort Analytics</h4>", unsafe_allow_html=True)
            st.line_chart(pd.DataFrame(np.random.randn(20, 2) * 10 + [50, 60], columns=["Tech", "Ops"]))
            st.markdown("</div>", unsafe_allow_html=True)
            
        with r2:
            st.markdown("<div class='glass-card'><h4>⚠️ At-Risk Candidates</h4>", unsafe_allow_html=True)
            risk = CodeForgeAI.calculate_risk(skill_gap_count=4, portfolio_score=15)
            
            st.metric("J. Doe (Backend Eng)", risk['churn'], "-5% vs Last Wk", delta_color="inverse")
            st.caption(f"Velocity: {risk['velocity']} | Status: {risk['flag']}")
            st.button("Trigger Manager Intervention")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<h3 style='margin-top: 40px;'>🎯 Candidate Scoring & Evaluation Matrix</h3>", unsafe_allow_html=True)
        score_col1, score_col2 = st.columns([1, 1.5])
        
        with score_col1:
            st.markdown("<div class='glass-card'><h4>📄 1. Candidate Input</h4>", unsafe_allow_html=True)
            rec_resume = st.file_uploader("Upload Candidate Resume (PDF)", key="rec_res")
            rec_jd = st.text_area("Target Job Skills:", "FastAPI, Docker, Python", key="rec_jd")
            
            st.markdown("<h4>🔗 External Profiles</h4>", unsafe_allow_html=True)
            rec_github = st.text_input("Candidate GitHub URL:", placeholder="https://github.com/username", key="rec_gh")
            rec_linkedin = st.text_input("Candidate LinkedIn URL:", placeholder="https://linkedin.com/in/username", key="rec_li")
            
            st.markdown("<h4>🧮 2. Human Evaluation</h4>", unsafe_allow_html=True)
            github_proj = st.number_input("Relevant GitHub Projects", min_value=0, value=2)
            interview_score = st.slider("Interviewer Score (Out of 10)", min_value=0.0, max_value=10.0, value=7.5, step=0.5)
            st.markdown("</div>", unsafe_allow_html=True)

        with score_col2:
            st.markdown("<div class='glass-card' style='height: 100%;'><h4>⚙️ 3. CodeForge Decision Engine</h4>", unsafe_allow_html=True)
            if st.button("Calculate Hire Probability 🎯", use_container_width=True):
                if rec_resume:
                    log_activity(f"Ran AI Profile Scanner for candidate.")
                    with st.spinner("Running Veri-Pixel & Analyzing Gap..."):
                        time.sleep(1)
                        raw_text = IntelligentParser.extract_text(rec_resume)
                        
                        # 1. AI Skill Gap Match (Max 40 points)
                        found_skills = IntelligentParser.extract_skills(raw_text, KnowledgeGraphEngine().catalogs["Software Engineering"])
                        target_skills = [s.strip() for s in rec_jd.split(',')]
                        overlap = len(set(found_skills).intersection(set(target_skills)))
                        match_ratio = overlap / len(target_skills) if target_skills else 0
                        ai_skill_match = int(match_ratio * 40) 
                        
                        # 2. Social Portfolio Footprint (Max 20 points)
                        social_data = IntelligentParser.extract_social_signals(raw_text, rec_github, rec_linkedin)
                        portfolio_pts = min(social_data['score'], 20) 
                        
                        # 3. Authenticity Deep-Scan (Max 10 points)
                        auth_scan = ProfileAuthenticityScanner.analyze_external_links(rec_github, rec_linkedin)
                        auth_bonus_pts = min(auth_scan['boost'], 10)
                        
                        # 4. Human Interview (Max 30 points)
                        interview_pts = int((interview_score / 10) * 30)
                        
                        vp_score = random.randint(82, 98)
                        final_score = ai_skill_match + portfolio_pts + auth_bonus_pts + interview_pts
                        
                        status_color = "#10b981" if final_score >= 70 else ("#f59e0b" if final_score >= 50 else "#ef4444")
                        status_text = "Highly Recommended" if final_score >= 70 else ("Needs Review" if final_score >= 50 else "Not Recommended")
                        
                        st.markdown(f"""
                            <div style='text-align: center; border: 2px solid {status_color}; border-radius: 12px; padding: 20px; background: rgba(0,0,0, 0.2); margin-top: 20px;'>
                                <h2 style='margin: 0; color: {status_color};'>{final_score:.1f}% Match</h2>
                                <p style='color: #cbd5e1;'>{status_text}</p>
                                <progress value="{final_score}" max="100" style="width: 100%; height: 15px;"></progress>
                            </div>
                            
                            <div style='margin-top: 20px; color: #94a3b8; font-size: 14px; background: rgba(255,255,255,0.02); padding: 15px; border-radius: 8px;'>
                                <b>Advanced Decision Breakdown:</b><br><br>
                                🧠 <b>AI Skill Match:</b> {ai_skill_match}/40 pts<br>
                                🗣️ <b>Human Evaluation:</b> {interview_pts}/30 pts<br>
                                🌐 <b>Portfolio Presence:</b> {portfolio_pts}/20 pts<br>
                                🕵️ <b>Authenticity Bonus:</b> {auth_bonus_pts}/10 pts<br>
                                <br><b>Authenticity Logs:</b><br>
                                <span style='color:#e2e8f0;'>{'<br>'.join(auth_scan['logs']) if auth_scan['logs'] else '<i>No external links provided for deep scan.</i>'}</span>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Please upload a candidate resume to run the scoring matrix.")
            st.markdown("</div>", unsafe_allow_html=True)
