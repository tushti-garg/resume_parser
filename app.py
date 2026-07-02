import os
from flask import Flask, request, jsonify, session, render_template
from werkzeug.utils import secure_filename

import parser as resume_parser
import analyzer
from database import init_db, get_db
from auth import register_user, login_user, logout_user, login_required

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB per file
ALLOWED_EXTENSIONS = {"pdf", "docx"}

init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_history(filename, ats_score, skills):
    if "user_id" not in session:
        return
    with get_db() as conn:
        conn.execute(
            "INSERT INTO history (user_id, filename, ats_score, skills) VALUES (?, ?, ?, ?)",
            (session["user_id"], filename, ats_score, ",".join(skills or [])),
        )


@app.route("/")
def home():
    return render_template("index.html")


# ---------- Auth ----------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    result, status = register_user(data.get("username", "").strip(), data.get("password", ""))
    return jsonify(result), status


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    result, status = login_user(data.get("username", "").strip(), data.get("password", ""))
    return jsonify(result), status


@app.route("/api/logout", methods=["POST"])
def logout():
    result, status = logout_user()
    return jsonify(result), status


@app.route("/api/me")
def me():
    if "user_id" in session:
        return jsonify({"logged_in": True, "username": session["username"]})
    return jsonify({"logged_in": False})


# ---------- Core parsing ----------
@app.route("/api/parse", methods=["POST"])
def parse_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["resume"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Please upload a PDF or DOCX file"}), 400

    filename = secure_filename(file.filename)
    try:
        parsed = resume_parser.extract_all(filename, file.read())
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {str(e)}"}), 422
    return jsonify(parsed)


@app.route("/api/analyze", methods=["POST"])
def analyze_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["resume"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Please upload a PDF or DOCX file"}), 400

    jd_text = request.form.get("job_description", "").strip() or None
    filename = secure_filename(file.filename)
    try:
        parsed = resume_parser.extract_all(filename, file.read())
        result = analyzer.score_resume(parsed, jd_text)
    except Exception as e:
        return jsonify({"error": f"Could not analyze file: {str(e)}"}), 422

    save_history(filename, result["ats_score"], result["skills"])
    return jsonify(result)


@app.route("/api/bulk", methods=["POST"])
def bulk_parse():
    files = request.files.getlist("resumes")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400
    jd_text = request.form.get("job_description", "").strip() or None

    parsed_list = []
    errors = []
    for file in files:
        if not allowed_file(file.filename):
            errors.append({"filename": file.filename, "error": "Unsupported file type"})
            continue
        filename = secure_filename(file.filename)
        try:
            parsed_list.append(resume_parser.extract_all(filename, file.read()))
        except Exception as e:
            errors.append({"filename": filename, "error": str(e)})

    ranked = analyzer.rank_resumes(parsed_list, jd_text)
    for r in ranked:
        save_history(r["filename"], r["ats_score"], r["skills"])

    return jsonify({"results": ranked, "errors": errors})


# ---------- Dashboard ----------
@app.route("/api/dashboard")
@login_required
def dashboard():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT filename, ats_score, skills, created_at FROM history WHERE user_id = ? ORDER BY created_at DESC",
            (session["user_id"],),
        ).fetchall()

    history = [dict(r) for r in rows]
    if not history:
        return jsonify({"total_parsed": 0, "avg_score": 0, "top_skills": [], "history": []})

    avg_score = round(sum(h["ats_score"] or 0 for h in history) / len(history), 1)

    skill_counts = {}
    for h in history:
        for s in (h["skills"] or "").split(","):
            s = s.strip()
            if s:
                skill_counts[s] = skill_counts.get(s, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return jsonify({
        "total_parsed": len(history),
        "avg_score": avg_score,
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
        "history": history[:20],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

from database import get_db
from llm_service import explain_candidate_fit, explain_improvements
import analyzer

# ---------- Recruiter: create job posting ----------
@app.route("/api/recruiter/jobs", methods=["POST"])
@login_required
def create_job():
    data = request.get_json(force=True)
    title = data.get("title", "").strip()
    skills = data.get("skills", [])  # [{"skill": "python", "weight": 5}, ...]
    min_exp = int(data.get("min_experience_years", 0))
    exp_weight = int(data.get("experience_weight", 3))
    if not title or not skills:
        return jsonify({"error": "Title and at least one skill required"}), 400

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO job_postings (recruiter_id, title, min_experience_years, experience_weight) VALUES (?, ?, ?, ?)",
            (session["user_id"], title, min_exp, exp_weight),
        )
        job_id = cur.lastrowid
        for s in skills:
            conn.execute(
                "INSERT INTO job_skills (job_id, skill, weight) VALUES (?, ?, ?)",
                (job_id, s["skill"].lower().strip(), int(s.get("weight", 3))),
            )
    return jsonify({"job_id": job_id}), 201


@app.route("/api/recruiter/jobs", methods=["GET"])
@login_required
def list_jobs():
    with get_db() as conn:
        jobs = conn.execute(
            "SELECT * FROM job_postings WHERE recruiter_id = ? ORDER BY created_at DESC",
            (session["user_id"],),
        ).fetchall()
    return jsonify([dict(j) for j in jobs])


def _load_job(job_id):
    with get_db() as conn:
        job_row = conn.execute("SELECT * FROM job_postings WHERE id = ?", (job_id,)).fetchone()
        if not job_row:
            return None
        skills = conn.execute("SELECT skill, weight FROM job_skills WHERE job_id = ?", (job_id,)).fetchall()
    return {
        "title": job_row["title"],
        "min_experience_years": job_row["min_experience_years"],
        "experience_weight": job_row["experience_weight"],
        "skills": [dict(s) for s in skills],
    }


# ---------- Recruiter: bulk upload against a job ----------
@app.route("/api/recruiter/jobs/<int:job_id>/upload", methods=["POST"])
@login_required
def upload_for_job(job_id):
    job = _load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    files = request.files.getlist("resumes")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    for file in files:
        if not allowed_file(file.filename):
            continue
        filename = secure_filename(file.filename)
        try:
            parsed = resume_parser.extract_all(filename, file.read())
        except Exception:
            continue
        match = analyzer.weighted_job_match(parsed, job)
        explanation = None
        if match["qualifies"]:
            explanation = explain_candidate_fit(parsed, job, match)

        with get_db() as conn:
            conn.execute(
                """INSERT INTO job_results (job_id, candidate_name, filename, fit_score, qualifies, explanation)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, parsed.get("name"), filename, match["fit_score"], int(match["qualifies"]), explanation),
            )

        results.append({
            "name": parsed.get("name"),
            "filename": filename,
            "fit_score": match["fit_score"],
            "qualifies": match["qualifies"],
            "matched_skills": match["matched_skills"],
            "missing_skills": match["missing_skills"],
            "years_detected": match["years_detected"],
            "explanation": explanation,
        })

    results.sort(key=lambda r: r["fit_score"], reverse=True)
    qualified = [r for r in results if r["qualifies"]]
    return jsonify({"job": job["title"], "total": len(results), "qualified": qualified, "all_results": results})


# ---------- Candidate: rate against a target role ----------
@app.route("/api/candidate/analyze", methods=["POST"])
def candidate_analyze():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["resume"]
    role = request.form.get("target_role", "").strip()
    if not allowed_file(file.filename):
        return jsonify({"error": "Please upload a PDF or DOCX file"}), 400

    filename = secure_filename(file.filename)
    parsed = resume_parser.extract_all(filename, file.read())
    ats_result = analyzer.calculate_ats_score(parsed)
    gap = analyzer.role_skill_gap(parsed, role) if role else {"matched_skills": [], "missing_skills": [], "role_recognized": False}
    improvement_text = explain_improvements(parsed, role or "general", ats_result, gap)

    save_history(filename, ats_result["score"], parsed.get("skills"))

    return jsonify({
        "name": parsed.get("name"),
        "target_role": role,
        "ats_score": ats_result["score"],
        "breakdown": ats_result["breakdown"],
        "role_recognized": gap["role_recognized"],
        "matched_skills": gap["matched_skills"],
        "missing_skills": gap["missing_skills"],
        "improvement_feedback": improvement_text,
    })
