from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import SQLALCHEMY_DATABASE_URI
from functools import wraps
import requests
import json
import os


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "interview-ai-secret-key-2026"
)

db = SQLAlchemy(app)

os.makedirs("database", exist_ok=True)


# =========================================================
# USER MODEL
# =========================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# =========================================================
# RECRUITER REQUIRED
# =========================================================

def recruiter_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        if session.get("role") != "recruiter":

            return "Access denied. Recruiter only."

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "landing.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        role = request.form.get(
            "role",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if (
            not name
            or not email
            or not role
            or not password
        ):

            return (
                "Please fill all registration fields."
            )

        if role not in [
            "candidate",
            "recruiter"
        ]:

            return (
                "Invalid role selected."
            )

        if User.query.filter_by(
            email=email
        ).first():

            return (
                "Email already registered. "
                "Please use another email."
            )

        new_user = User(

            name=name,

            email=email,

            role=role,

            password=generate_password_hash(
                password
            )
        )

        db.session.add(
            new_user
        )

        db.session.commit()

        session["user_id"] = new_user.id
        session["name"] = new_user.name
        session["email"] = new_user.email
        session["role"] = new_user.role

        if role == "recruiter":

            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )

        return redirect(
            url_for(
                "candidate_dashboard"
            )
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        if (
            user
            and check_password_hash(
                user.password,
                password
            )
        ):

            session["user_id"] = user.id
            session["name"] = user.name
            session["email"] = user.email
            session["role"] = user.role

            if user.role == "recruiter":

                return redirect(
                    url_for(
                        "admin_dashboard"
                    )
                )

            return redirect(
                url_for(
                    "candidate_dashboard"
                )
            )

        return (
            "Invalid email or password."
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# CANDIDATE DASHBOARD
# =========================================================

@app.route("/candidate/dashboard")
@login_required
def candidate_dashboard():

    if session.get("role") != "candidate":

        return (
            "Access denied. Candidate only."
        )

    return render_template(

        "candidate/dashboard.html",

        user_name=session.get(
            "name"
        ),

        user_email=session.get(
            "email"
        )
    )


# =========================================================
# CANDIDATE PROFILE
# =========================================================

@app.route("/candidate/profile")
@login_required
def candidate_profile():

    if session.get("role") != "candidate":

        return (
            "Access denied. Candidate only."
        )

    return render_template(

        "candidate/profile.html",

        user_name=session.get(
            "name"
        ),

        user_email=session.get(
            "email"
        )
    )


# =========================================================
# INTERVIEW SETUP
# =========================================================

@app.route(
    "/candidate/interview-setup",
    methods=["GET", "POST"]
)
@login_required
def interview_setup():

    if session.get("role") != "candidate":

        return (
            "Access denied. Candidate only."
        )

    if request.method == "POST":

        session["interview_role"] = (
            request.form.get(
                "interview_role",
                "Software Developer"
            )
        )

        session["experience_level"] = (
            request.form.get(
                "experience_level",
                "Fresher"
            )
        )

        session["interview_started"] = True

        return redirect(
            url_for(
                "system_check"
            )
        )

    return render_template(
        "candidate/interview-setup.html"
    )


# =========================================================
# SYSTEM CHECK
# =========================================================

@app.route("/candidate/system-check")
@login_required
def system_check():

    if session.get("role") != "candidate":

        return (
            "Access denied. Candidate only."
        )

    return render_template(
        "candidate/system-check.html"
    )


# =========================================================
# INTERVIEW ROOM
# =========================================================

@app.route("/candidate/interview-room")
@login_required
def interview_room():

    if session.get("role") != "candidate":

        return (
            "Access denied. Candidate only."
        )

    if not session.get(
        "interview_started"
    ):

        return redirect(
            url_for(
                "interview_setup"
            )
        )

    return render_template(

        "candidate/interview-room.html",

        user_name=session.get(
            "name"
        ),

        interview_role=session.get(
            "interview_role",
            "Software Developer"
        ),

        experience_level=session.get(
            "experience_level",
            "Fresher"
        )
    )


# =========================================================
# RESULT
# =========================================================

@app.route("/candidate/result")
@login_required
def candidate_result():

    if session.get("role") != "candidate":

        return (
            "Access denied. Candidate only."
        )

    return render_template(

        "candidate/result.html",

        user_name=session.get(
            "name"
        ),

        interview_role=session.get(
            "interview_role",
            "Software Developer"
        )
    )


# =========================================================
# GEMINI AI ANSWER EVALUATION
# =========================================================

@app.route(
    "/api/evaluate-answer",
    methods=["POST"]
)
@login_required
def evaluate_answer():

    # -----------------------------------------------------
    # CANDIDATE ACCESS CHECK
    # -----------------------------------------------------

    if session.get("role") != "candidate":

        return jsonify({

            "success": False,

            "message":
                "Candidate access only."

        }), 403

    # -----------------------------------------------------
    # GET REQUEST DATA
    # -----------------------------------------------------

    data = request.get_json(
        silent=True
    ) or {}

    question = data.get(
        "question",
        ""
    ).strip()

    answer = data.get(
        "answer",
        ""
    ).strip()

    if not question or not answer:

        return jsonify({

            "success": False,

            "message":
                "Question and answer are required."

        }), 400

    # -----------------------------------------------------
    # GEMINI API KEY
    # -----------------------------------------------------

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:

        return jsonify({

            "success": False,

            "message":
                "Gemini API key is not configured on the server."

        }), 500

    # -----------------------------------------------------
    # AI EVALUATION PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are a strict and fair professional technical
interview evaluator.

You are evaluating a candidate in an AI-powered
corporate interview system.

QUESTION:
{question}

CANDIDATE ANSWER:
{answer}

Evaluate the candidate answer using these criteria:

1. Relevance
2. Correctness
3. Technical understanding
4. Clarity
5. Completeness

IMPORTANT EVALUATION RULES:

- The answer must directly address the question.
- Do NOT mark unrelated answers as correct.
- Do NOT mark random text as correct.
- Do NOT give a high score to meaningless answers.
- If the answer does not answer the question,
  score it very low.
- If the answer is completely wrong,
  status MUST be "Incorrect".
- If the answer contains some correct information
  but also has important mistakes or missing points,
  status MUST be "Partially Correct".
- Only use "Correct" when the answer genuinely
  answers the question accurately.
- Score must be between 0 and 10.
- Be strict but fair.
- Give useful interview feedback.

Return ONLY a valid JSON object.

Use exactly this structure:

{{
    "score": 0,
    "status": "Incorrect",
    "feedback": "Short explanation of why the answer received this score.",
    "improvement": "Specific advice for improving the answer."
}}

Allowed status values:

Correct
Partially Correct
Incorrect
"""

    try:

        # =================================================
        # GEMINI INTERACTIONS API
        # =================================================

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/interactions"
        )

        response = requests.post(

            url,

            params={
                "key": api_key
            },

            headers={
                "Content-Type":
                    "application/json"
            },

            json={

                "model":
                    "gemini-3.6-flash",

                "input":
                    prompt,

                "generation_config": {

                    "max_output_tokens":
                        500
                },

                "store":
                    False
            },

            timeout=60
        )

        # -------------------------------------------------
        # HTTP ERROR CHECK
        # -------------------------------------------------

        if not response.ok:

            print(
                "Gemini HTTP Status:",
                response.status_code
            )

            print(
                "Gemini Response:",
                response.text
            )

            return jsonify({

                "success": False,

                "message":
                    "Gemini API request failed.",

                "details":
                    response.text

            }), 502

        # -------------------------------------------------
        # PARSE RESPONSE
        # -------------------------------------------------

        response_data = response.json()

        print(
            "Gemini Interaction Response:",
            response_data
        )

        # -------------------------------------------------
        # CHECK INTERACTION STATUS
        # -------------------------------------------------

        interaction_status = (
            response_data.get(
                "status",
                ""
            )
        )

        if interaction_status == "failed":

            print(
                "Gemini interaction failed:",
                response_data
            )

            return jsonify({

                "success": False,

                "message":
                    "Gemini interaction failed."

            }), 502

        # -------------------------------------------------
        # EXTRACT MODEL OUTPUT
        # -------------------------------------------------

        text = ""

        steps = response_data.get(
            "steps",
            []
        )

        for step in steps:

            if step.get(
                "type"
            ) != "model_output":

                continue

            content = step.get(
                "content",
                []
            )

            for item in content:

                if item.get(
                    "type"
                ) == "text":

                    text = item.get(
                        "text",
                        ""
                    ).strip()

                    if text:

                        break

            if text:

                break

        # -------------------------------------------------
        # OUTPUT VALIDATION
        # -------------------------------------------------

        if not text:

            print(
                "Gemini returned no text:",
                response_data
            )

            return jsonify({

                "success": False,

                "message":
                    "Gemini did not return an evaluation."

            }), 502

        print(
            "Gemini Evaluation Text:",
            text
        )

        # -------------------------------------------------
        # REMOVE MARKDOWN JSON FENCES
        # -------------------------------------------------

        if text.startswith(
            "```"
        ):

            text = text.replace(
                "```json",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

            text = text.strip()

        # -------------------------------------------------
        # PARSE AI JSON
        # -------------------------------------------------

        result = json.loads(
            text
        )

        # -------------------------------------------------
        # SCORE
        # -------------------------------------------------

        try:

            score = float(
                result.get(
                    "score",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            score = 0

        score = max(
            0,
            min(
                10,
                score
            )
        )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        status = result.get(
            "status",
            "Incorrect"
        )

        allowed_statuses = [

            "Correct",

            "Partially Correct",

            "Incorrect"

        ]

        if status not in allowed_statuses:

            status = "Incorrect"

        # -------------------------------------------------
        # FEEDBACK
        # -------------------------------------------------

        feedback = str(

            result.get(
                "feedback",
                ""
            )

        ).strip()

        improvement = str(

            result.get(
                "improvement",
                ""
            )

        ).strip()

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "score": score,

            "status": status,

            "feedback": feedback,

            "improvement": improvement

        })

    # =====================================================
    # TIMEOUT
    # =====================================================

    except requests.exceptions.Timeout:

        print(
            "Gemini request timed out."
        )

        return jsonify({

            "success": False,

            "message":
                "Gemini took too long to respond. Please try again."

        }), 504

    # =====================================================
    # CONNECTION ERROR
    # =====================================================

    except requests.exceptions.RequestException as error:

        print(
            "Gemini Request Error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                "Could not connect to Gemini."

        }), 502

    # =====================================================
    # INVALID JSON FROM GEMINI
    # =====================================================

    except json.JSONDecodeError as error:

        print(
            "Gemini JSON Decode Error:",
            error
        )

        print(
            "Invalid Gemini Text:",
            text if "text" in locals() else ""
        )

        return jsonify({

            "success": False,

            "message":
                "Gemini returned an invalid evaluation format."

        }), 502

    # =====================================================
    # OTHER ERROR
    # =====================================================

    except Exception as error:

        print(
            "AI Evaluation Error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
                "AI evaluation failed. Check the Render logs."

        }), 500


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
@recruiter_required
def admin_dashboard():

    total_candidates = User.query.filter_by(
        role="candidate"
    ).count()

    total_recruiters = User.query.filter_by(
        role="recruiter"
    ).count()

    return render_template(

        "admin/dashboard.html",

        total_candidates=
            total_candidates,

        total_recruiters=
            total_recruiters,

        recruiter_name=
            session.get("name")
    )


# =========================================================
# ADMIN CANDIDATES
# =========================================================

@app.route("/admin/candidates")
@recruiter_required
def admin_candidates():

    candidates = User.query.filter_by(
        role="candidate"
    ).all()

    return render_template(

        "admin/candidates.html",

        candidates=candidates
    )


# =========================================================
# ADMIN CANDIDATE DETAIL
# =========================================================

@app.route("/admin/candidate-detail")
@recruiter_required
def candidate_detail():

    candidate_id = request.args.get(
        "id"
    )

    candidate = (

        User.query.get(
            candidate_id
        )

        if candidate_id

        else None
    )

    return render_template(

        "admin/candidate-detail.html",

        candidate=candidate
    )


# =========================================================
# ADMIN LIVE INTERVIEW
# =========================================================

@app.route("/admin/live-interview")
@recruiter_required
def live_interview():

    return render_template(
        "admin/live-interview.html"
    )


# =========================================================
# DATABASE
# =========================================================

with app.app_context():

    db.create_all()


# =========================================================
# CATEGORIES
# =========================================================

@app.route("/categories")
def categories():

    return render_template(
        "categories.html"
    )


# =========================================================
# START INTERVIEW
# =========================================================

@app.route(
    "/start-interview/<category>"
)
def start_interview(category):

    return render_template(

        "interview-room.html",

        category=category.replace(
            "-",
            " "
        ).title()
    )


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )