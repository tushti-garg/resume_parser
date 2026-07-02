"""
app.py  — Resume Parser + Analyzer
Endpoints:
  GET  /                  serve frontend
  GET  /api/health        health check
  POST /api/parse         single resume → extracted fields
  POST /api/analyze       single resume + job info → score + suggestions
  POST /api/rank          multiple resumes + job info → ranked shortlist
"""

import os, json
from flask import Flask, request, jsonify, send_from_directory
from parser import parse_resume
from analyzer import score_resume, rank_resumes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED = {".pdf", ".docx"}
MAX_MB = 5

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/parse", methods=["POST"])
def parse():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    f = request.files["resume"]
    if not f.filename:
        return jsonify({"error": "No file selected."}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": "Upload a .pdf or .docx file."}), 400
    try:
        result = parse_resume(f.filename, f.read())
        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Parse failed: {e}"}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Candidate mode: single resume + job requirements → score + tips."""
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    f = request.files["resume"]
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify({"error": "Upload a .pdf or .docx file."}), 400

    job_role = request.form.get("job_role", "").strip()
    required_skills_raw = request.form.get("required_skills", "").strip()
    experience_required = request.form.get("experience_required", "").strip() or None
    required_skills = [s.strip() for s in re.split(r"[,\n]+", required_skills_raw) if s.strip()] if required_skills_raw else []

    try:
        parsed = parse_resume(f.filename, f.read())
        analysis = score_resume(parsed, job_role, required_skills, experience_required)
        return jsonify({"success": True, "parsed": parsed, "analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rank", methods=["POST"])
def rank():
    """Recruiter mode: multiple resumes + job requirements → ranked list."""
    files = request.files.getlist("resumes")
    if not files:
        return jsonify({"error": "No files uploaded."}), 400
    if len(files) > 20:
        return jsonify({"error": "Max 20 resumes at once."}), 400

    job_role = request.form.get("job_role", "").strip()
    required_skills_raw = request.form.get("required_skills", "").strip()
    experience_required = request.form.get("experience_required", "").strip() or None
    required_skills = [s.strip() for s in re.split(r"[,\n]+", required_skills_raw) if s.strip()] if required_skills_raw else []

    parsed_list = []
    errors = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED:
            errors.append(f"{f.filename}: unsupported type")
            continue
        try:
            parsed = parse_resume(f.filename, f.read())
            parsed_list.append({"filename": f.filename, "parsed": parsed})
        except Exception as e:
            errors.append(f"{f.filename}: {e}")

    if not parsed_list:
        return jsonify({"error": "No valid files could be parsed.", "details": errors}), 422

    ranked = rank_resumes(parsed_list, job_role, required_skills, experience_required)
    return jsonify({"success": True, "total": len(ranked), "errors": errors, "results": ranked})


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": f"File too large. Max {MAX_MB}MB."}), 413


import re   # needed in analyze/rank

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
