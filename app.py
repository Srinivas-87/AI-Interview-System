from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import SQLALCHEMY_DATABASE_URI
from functools import wraps
import requests
import json
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "interview-ai-secret-key-2026"

db = SQLAlchemy(app)
os.makedirs("database", exist_ok=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)


def login_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return decorated_function


def recruiter_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "recruiter":
            return "Access denied. Recruiter only."
        return function(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not role or not password:
            return "Please fill all registration fields."

        if role not in ["candidate", "recruiter"]:
            return "Invalid role selected."

        if User.query.filter_by(email=email).first():
            return "Email already registered. Please use another email."

        new_user = User(
            name=name,
            email=email,
            role=role,
            password=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        session["name"] = new_user.name
        session["email"] = new_user.email
        session["role"] = new_user.role

        if role == "recruiter":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("candidate_dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["name"] = user.name
            session["email"] = user.email
            session["role"] = user.role

            if user.role == "recruiter":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("candidate_dashboard"))

        return "Invalid email or password."

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/candidate/dashboard")
@login_required
def candidate_dashboard():
    if session.get("role") != "candidate":
        return "Access denied. Candidate only."

    return render_template(
        "candidate/dashboard.html",
        user_name=session.get("name"),
        user_email=session.get("email")
    )


@app.route("/candidate/profile")
@login_required
def candidate_profile():
    if session.get("role") != "candidate":
        return "Access denied. Candidate only."

    return render_template(
        "candidate/profile.html",
        user_name=session.get("name"),
        user_email=session.get("email")
    )


@app.route("/candidate/interview-setup", methods=["GET", "POST"])
@login_required
def interview_setup():
    if session.get("role") != "candidate":
        return "Access denied. Candidate only."

    if request.method == "POST":
        session["interview_role"] = request.form.get(
            "interview_role", "Software Developer"
        )
        session["experience_level"] = request.form.get(
            "experience_level", "Fresher"
        )
        session["interview_started"] = True
        return redirect(url_for("system_check"))

    return render_template("candidate/interview-setup.html")


@app.route("/candidate/system-check")
@login_required
def system_check():
    if session.get("role") != "candidate":
        return "Access denied. Candidate only."
    return render_template("candidate/system-check.html")


@app.route("/candidate/interview-room")
@login_required
def interview_room():
    if session.get("role") != "candidate":
        return "Access denied. Candidate only."

    if not session.get("interview_started"):
        return redirect(url_for("interview_setup"))

    return render_template(
        "candidate/interview-room.html",
        user_name=session.get("name"),
        interview_role=session.get("interview_role", "Software Developer"),
        experience_level=session.get("experience_level", "Fresher")
    )


@app.route("/candidate/result")
@login_required
def candidate_result():
    if session.get("role") != "candidate":
        return "Access denied. Candidate only."

    return render_template(
        "candidate/result.html",
        user_name=session.get("name"),
        interview_role=session.get("interview_role", "Software Developer")
    )


@app.route("/api/evaluate-answer", methods=["POST"])
@login_required
def evaluate_answer():
    if session.get("role") != "candidate":
        return jsonify({
            "success": False,
            "message": "Candidate access only."
        }), 403

    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()

    if not question or not answer:
        return jsonify({
            "success": False,
            "message": "Question and answer are required."
        }), 400

    prompt = f"""
You are a strict and fair technical interview evaluator.

Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer based on relevance, correctness, clarity,
technical understanding, and completeness.

Return ONLY valid JSON in this exact format:
{{
  "score": 0,
  "status": "Correct",
  "feedback": "short clear feedback",
  "improvement": "specific improvement suggestion"
}}

Rules:
- score must be a number from 0 to 10.
- status must be exactly one of:
  "Correct", "Partially Correct", "Incorrect".
- Do not mark unrelated or meaningless answers as correct.
- If the answer is empty, unrelated, or nonsense, score 0 and status Incorrect.
- Return JSON only. No markdown.
"""

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )

        response.raise_for_status()
        ai_response = response.json().get("response", "").strip()
        result = json.loads(ai_response)

        score = float(result.get("score", 0))
        score = max(0, min(10, score))

        return jsonify({
            "success": True,
            "score": score,
            "status": result.get("status", "Incorrect"),
            "feedback": result.get("feedback", ""),
            "improvement": result.get("improvement", "")
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "message": "Ollama is not running. Open CMD and run: ollama serve"
        }), 503

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "message": "AI took too long. Please try again."
        }), 504

    except Exception as error:
        print("AI Evaluation Error:", error)
        return jsonify({
            "success": False,
            "message": "AI evaluation failed. Check the terminal."
        }), 500


@app.route("/admin/dashboard")
@recruiter_required
def admin_dashboard():
    total_candidates = User.query.filter_by(role="candidate").count()
    total_recruiters = User.query.filter_by(role="recruiter").count()

    return render_template(
        "admin/dashboard.html",
        total_candidates=total_candidates,
        total_recruiters=total_recruiters,
        recruiter_name=session.get("name")
    )


@app.route("/admin/candidates")
@recruiter_required
def admin_candidates():
    candidates = User.query.filter_by(role="candidate").all()
    return render_template("admin/candidates.html", candidates=candidates)


@app.route("/admin/candidate-detail")
@recruiter_required
def candidate_detail():
    candidate_id = request.args.get("id")
    candidate = User.query.get(candidate_id) if candidate_id else None

    return render_template(
        "admin/candidate-detail.html",
        candidate=candidate
    )


@app.route("/admin/live-interview")
@recruiter_required
def live_interview():
    return render_template("admin/live-interview.html")


with app.app_context():
    db.create_all()


@app.route("/categories")
def categories():
    return render_template("categories.html")


@app.route("/start-interview/<category>")
def start_interview(category):
    return render_template(
        "interview-room.html",
        category=category.replace("-", " ").title()
    )


if __name__ == "__main__":
    app.run(debug=True)
