import re

ACTION_VERBS = ["led", "built", "developed", "designed", "implemented", "managed",
                "created", "improved", "optimized", "launched", "reduced", "increased",
                "automated", "delivered", "achieved", "spearheaded"]

QUANT_RE = re.compile(r"\b\d+(\.\d+)?\s?(%|percent|x|hours|days|users|clients|k|million|\$)", re.I)


def calculate_ats_score(parsed):
    """Rule-based ATS-style score out of 100, with a breakdown."""
    breakdown = {}
    text = parsed.get("raw_text", "")
    word_count = len(text.split())

    # Contact completeness (20 pts)
    contact_score = 0
    if parsed.get("email"):
        contact_score += 8
    if parsed.get("phone"):
        contact_score += 6
    if parsed.get("links"):
        contact_score += 6
    breakdown["contact_info"] = contact_score

    # Key sections present (25 pts)
    section_score = 0
    if parsed.get("education"):
        section_score += 8
    if parsed.get("experience"):
        section_score += 12
    if parsed.get("skills"):
        section_score += 5
    breakdown["sections"] = section_score

    # Skills breadth (15 pts)
    skills_score = min(len(parsed.get("skills", [])) * 1.5, 15)
    breakdown["skills_breadth"] = round(skills_score, 1)

    # Action verbs (15 pts)
    lower = text.lower()
    verbs_found = sum(1 for v in ACTION_VERBS if v in lower)
    verb_score = min(verbs_found * 2, 15)
    breakdown["action_verbs"] = verb_score

    # Quantifiable achievements (15 pts)
    quant_matches = len(QUANT_RE.findall(text))
    quant_score = min(quant_matches * 3, 15)
    breakdown["quantifiable_impact"] = quant_score

    # Length sanity (10 pts) — too short or too long both hurt
    if 250 <= word_count <= 900:
        length_score = 10
    elif word_count < 250:
        length_score = max(0, round(word_count / 25))
    else:
        length_score = max(0, 10 - round((word_count - 900) / 100))
    breakdown["length"] = length_score

    total = round(sum(breakdown.values()))
    return {"score": min(total, 100), "breakdown": breakdown, "word_count": word_count}


def generate_suggestions(parsed, ats_result):
    suggestions = []
    b = ats_result["breakdown"]

    if not parsed.get("email"):
        suggestions.append("Add a professional email address near the top of your resume.")
    if not parsed.get("phone"):
        suggestions.append("Add a phone number so recruiters can reach you directly.")
    if not parsed.get("links"):
        suggestions.append("Include a LinkedIn and/or GitHub link to strengthen your profile.")
    if b["sections"] < 20:
        suggestions.append("Make sure Education and Experience sections are clearly labeled with standard headers.")
    if b["skills_breadth"] < 8:
        suggestions.append("List more relevant technical skills — aim for 8-12 that match your target role.")
    if b["action_verbs"] < 8:
        suggestions.append("Start bullet points with strong action verbs (e.g., 'Led', 'Built', 'Optimized') instead of passive phrases.")
    if b["quantifiable_impact"] < 6:
        suggestions.append("Quantify your impact with numbers — e.g., 'reduced load time by 40%' or 'managed a team of 5'.")
    if ats_result["word_count"] < 250:
        suggestions.append("Your resume looks short — add more detail on projects and achievements.")
    elif ats_result["word_count"] > 900:
        suggestions.append("Your resume is quite long — trim it to focus on your most relevant, recent experience (aim for 1-2 pages).")

    if not suggestions:
        suggestions.append("Strong resume overall — consider tailoring keywords to each specific job description.")
    return suggestions


def match_job_description(parsed, jd_text):
    """Compare resume skills/keywords against a job description."""
    from parser import SKILLS_DB
    jd_lower = jd_text.lower()
    jd_skills = sorted({s for s in SKILLS_DB if s in jd_lower})
    resume_skills = set(parsed.get("skills", []))

    matched = sorted(resume_skills & set(jd_skills))
    missing = sorted(set(jd_skills) - resume_skills)

    match_pct = round((len(matched) / len(jd_skills)) * 100) if jd_skills else 0

    return {
        "match_percentage": match_pct,
        "matched_skills": matched,
        "missing_skills": missing,
        "jd_skills_detected": jd_skills,
    }


def score_resume(parsed, jd_text=None):
    ats_result = calculate_ats_score(parsed)
    suggestions = generate_suggestions(parsed, ats_result)
    result = {
        "filename": parsed.get("filename"),
        "name": parsed.get("name"),
        "ats_score": ats_result["score"],
        "breakdown": ats_result["breakdown"],
        "suggestions": suggestions,
        "skills": parsed.get("skills"),
    }
    if jd_text:
        result["jd_match"] = match_job_description(parsed, jd_text)
        # blend ATS score with JD match for an overall ranking score
        result["overall_score"] = round(0.6 * ats_result["score"] + 0.4 * result["jd_match"]["match_percentage"])
    else:
        result["overall_score"] = ats_result["score"]
    return result


def rank_resumes(parsed_list, jd_text=None):
    scored = [score_resume(p, jd_text) for p in parsed_list]
    scored.sort(key=lambda r: r["overall_score"], reverse=True)
    for i, r in enumerate(scored, start=1):
        r["rank"] = i
    return scored


import re

EXPERIENCE_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years|yrs)", re.I)

ROLE_SKILL_PROFILES = {
    "ml engineer": ["python", "pytorch", "tensorflow", "scikit-learn", "machine learning",
                    "deep learning", "sql", "docker", "aws", "git"],
    "data scientist": ["python", "r", "sql", "pandas", "numpy", "machine learning",
                        "tableau", "power bi", "scikit-learn"],
    "backend developer": ["python", "java", "sql", "django", "flask", "node.js",
                           "docker", "kubernetes", "aws", "git"],
    "frontend developer": ["javascript", "typescript", "react", "html", "css",
                            "next.js", "tailwind", "git"],
    "devops engineer": ["docker", "kubernetes", "terraform", "aws", "azure",
                         "ci/cd", "jenkins", "linux", "bash"],
    "product manager": ["agile", "scrum", "jira", "figma", "sql", "excel"],
}


def estimate_years_experience(text):
    matches = [int(m) for m in EXPERIENCE_YEARS_RE.findall(text)]
    return max(matches) if matches else 0


def weighted_job_match(parsed, job):
    """job = {'title', 'skills': [{'skill','weight'}], 'min_experience_years', 'experience_weight'}"""
    resume_skills = set(parsed.get("skills", []))
    years = estimate_years_experience(parsed.get("raw_text", ""))

    total_weight = sum(s["weight"] for s in job["skills"]) + job["experience_weight"]
    earned = 0
    matched, missing = [], []

    for s in job["skills"]:
        if s["skill"] in resume_skills:
            earned += s["weight"]
            matched.append(s["skill"])
        else:
            missing.append(s["skill"])

    exp_met = years >= job["min_experience_years"]
    if exp_met:
        earned += job["experience_weight"]

    fit_score = round((earned / total_weight) * 100) if total_weight else 0
    qualifies = exp_met and len(missing) <= max(1, len(job["skills"]) // 3)

    return {
        "fit_score": fit_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "years_detected": years,
        "meets_min_experience": exp_met,
        "qualifies": qualifies,
    }


def role_skill_gap(parsed, role_name):
    role_key = role_name.lower().strip()
    profile = ROLE_SKILL_PROFILES.get(role_key)
    resume_skills = set(parsed.get("skills", []))
    if not profile:
        # unknown role -> just report what they have, no gap list
        return {"matched_skills": sorted(resume_skills), "missing_skills": [], "role_recognized": False}
    matched = sorted(resume_skills & set(profile))
    missing = sorted(set(profile) - resume_skills)
    return {"matched_skills": matched, "missing_skills": missing, "role_recognized": True}
