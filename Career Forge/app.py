from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from twilio.rest import Client
import requests
import sqlite3
import os
import schedule
import time
import threading

# -------------------- Custom Modules --------------------
from recommender import recommend_careers

# -------------------- Twilio & Groq Config --------------------
TWILIO_ACCOUNT_SID = 'AC32b7453f637dd568201918eafd56e0ba'
TWILIO_AUTH_TOKEN = '882a028b2fb8705456f9a10aa3875262'
TWILIO_PHONE_NUMBER = '+919865022866'
GROQ_API_KEY = "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"

# -------------------- Flask App Setup --------------------
app = Flask(__name__)
CORS(app)
app.secret_key = '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'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------- Database Initialization --------------------
def init_db():
    with sqlite3.connect('careerforage.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT)''')

        conn.execute('''CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL)''')

        conn.execute('''CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            ats_score INTEGER,
            summary TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id))''')

        conn.execute('''CREATE TABLE IF NOT EXISTS job_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            posted_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

# -------------------- SMS Career Reminder --------------------
def send_sms_reminders():
    with sqlite3.connect('careerforage.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, phone FROM users WHERE phone IS NOT NULL")
        users = cur.fetchall()

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for name, phone in users:
            try:
                message = client.messages.create(
                    body=f"Hello {name}, here’s your CareerForge tip: Polish your resume or apply to a job today!",
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone
                )
                print(f"SMS sent to {name} - {phone}")
            except Exception as e:
                print(f"Failed to send to {phone}: {e}")

# -------------------- Routes --------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/user_register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        with sqlite3.connect('careerforage.db') as conn:
            try:
                conn.execute("INSERT INTO users (name, email, password, phone) VALUES (?, ?, ?, ?)",
                             (name, email, password, phone))
                return redirect(url_for('login_user'))
            except sqlite3.IntegrityError:
                return "Email already exists. Please try another."
    return render_template('user_register.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        with sqlite3.connect('careerforge.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = cur.fetchone()
            if user:
                session['user_id'] = user[0]
                return redirect(url_for('career_dashboard'))
            return "Invalid credentials. Please try again."
    return render_template('user_login.html')

@app.route('/career_dashboard')
def career_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))
    return render_template('career_dashboard.html')


@app.route('/recommend_career', methods=['POST'])
def recommend_career():
    skills = request.json.get("skills", [])
    if not skills:
        return jsonify({"careers": []})
    careers = recommend_careers(skills)
    return jsonify({"careers": careers})

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"response": "Please enter a message."})
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a helpful career assistant that guides users with resume help, career paths, and job advice."},
                {"role": "user", "content": user_input}
            ]
        }
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        if "choices" in data and data["choices"]:
            reply = data["choices"][0]["message"]["content"]
            return jsonify({"response": reply})
        else:
            return jsonify({"response": "Error: Invalid response from AI."})
    except Exception as e:
        return jsonify({"response": f"Exception: {str(e)}"})

# -------------------- Admin Panel --------------------
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('careerforge.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
            admin = cur.fetchone()
            if admin:
                session['admin_id'] = admin[0]
                return redirect(url_for('admin_dashboard'))
            return "Invalid admin credentials"
    return render_template('admin_login.html')

@app.route('/career_quiz')
def career_quiz():
    return render_template('career_quiz.html')
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/post_job_alert', methods=['POST'])
def post_job_alert():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    title = request.form['title']
    message = request.form['message']
    with sqlite3.connect('careerforge.db') as conn:
        conn.execute("INSERT INTO job_alerts (title, message) VALUES (?, ?)", (title, message))
    return redirect(url_for('admin_dashboard'))

@app.route('/job_alerts')
def job_alerts():
    with sqlite3.connect('careerforge.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT title, message, posted_on FROM job_alerts ORDER BY posted_on DESC")
        alerts = cur.fetchall()
    return render_template('job_alerts.html', alerts=alerts)

@app.route('/test_sms')
def test_sms():
    send_sms_reminders()
    return "CareerForge SMS tips sent!"

@app.route('/career_portal')
def career_portal():
    return render_template('career_portal.html')



def add_test_admin():
    with sqlite3.connect('careerforge.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE username = ?", ('admin',))
        if cur.fetchone() is None:
            conn.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ('admin', 'admin123'))
            print("Admin added: admin / admin123")
        else:
            print("Admin already exists. Skipping insert.")

if __name__ == "__main__":
    init_db()
    add_test_admin()
    app.run(debug=True)
