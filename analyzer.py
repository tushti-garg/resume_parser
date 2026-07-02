"""
analyzer.py
Smart resume scoring engine.
- Matches resume against job requirements (skills, experience, role keywords)
- Returns match score, matched/missing skills, strengths, and specific improvement tips
- No external API or ML model needed — runs fully offline
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Role keyword bank — maps common role names to relevant keywords
# ---------------------------------------------------------------------------

ROLE_KEYWORDS = {
    "software developer": ["python", "java", "javascript", "c++", "git", "api", "database", "oop", "agile", "testing", "debugging", "backend", "frontend"],
    "software engineer": ["python", "java", "c++", "algorithms", "data structures", "system design", "git", "rest", "microservices", "testing"],
    "frontend developer": ["html", "css", "javascript", "react", "vue", "angular", "responsive", "ui", "ux", "typescript", "webpack"],
    "backend developer": ["python", "java", "node", "flask", "django", "api", "database", "sql", "rest", "microservices", "docker"],
    "full stack developer": ["html", "css", "javascript", "python", "react", "node", "database", "api", "git", "deployment"],
    "data scientist": ["python", "machine learning", "statistics", "pandas", "numpy", "scikit-learn", "data visualization", "sql", "deep learning"],
    "data analyst": ["sql", "python", "excel", "tableau", "power bi", "data visualization", "statistics", "pandas"],
    "machine learning engineer": ["python", "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "nlp", "data preprocessing"],
    "ai engineer": ["python", "machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "computer vision", "llm", "api"],
    "devops engineer": ["docker", "kubernetes", "ci/cd", "linux", "aws", "azure", "git", "terraform", "monitoring", "bash"],
    "mobile developer": ["android", "ios", "kotlin", "swift", "react native", "flutter", "java", "mobile", "api"],
    "web developer": ["html", "css", "javascript", "react", "git", "responsive", "api", "database", "node"],
}

EXPERIENCE_PATTERNS = [
    (r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", "years"),
    (r"(\d+)\+?\s*yrs?\s+(?:of\s+)?experience", "years"),
    (r"intern(?:ship)?", "intern"),
    (r"fresher|entry.?level|junior", "fresher"),
    (r"senior|lead|principal|architect", "senior"),
    (r"mid.?level|(\d+)[-–](\d+)\s*years?", "mid"),
]

DEGREE_KEYWORDS = {
    "b.tech": 1, "btech": 1, "b.e": 1, "bachelor": 1, "bsc": 1, "b.sc": 1, "bca": 1,
    "m.tech": 2, "mtech": 2, "m.e": 2, "master": 2, "msc": 2, "m.sc": 2, "mca": 2,
    "phd": 3, "ph.d": 3, "doctorate": 3,
    "diploma": 0, "12th": 0, "high school": 0,
}

WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "assisted in", "involved in",
    "participated in", "exposure to", "knowledge of", "familiar with", "understanding of",
    "learned new materials", "asked appropriate questions", "attended training",
    "build understanding", "supported departmental tasks",
]

ACTION_VERBS = [
    "built", "developed", "designed", "implemented", "created", "deployed", "optimized",
    "automated", "integrated", "engineered", "architected", "led", "managed", "reduced",
    "improved", "increased", "launched", "delivered", "analyzed", "scaled",
]

SECTION_INDICATORS = {
    "experience": ["experience", "work history", "employment", "internship"],
    "education": ["education", "academic", "qualification"],
    "skills": ["skills", "technical skills", "technologies", "competencies"],
    "projects": ["projects", "personal projects", "portfolio", "work samples"],
    "achievements": ["achievements", "awards", "accomplishments", "certifications"],
    "summary": ["summary", "objective", "profile", "about"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    return text.lower().strip()


def count_action_verbs(text: str) -> int:
    lower = text.lower()
    return sum(1 for v in ACTION_VERBS if re.search(r'\b' + v + r'\b', lower))


def count_weak_phrases(text: str) -> list:
    lower = text.lower()
    return [p for p in WEAK_PHRASES if p in lower]


def detect_experience_level(text: str) -> str:
    lower = text.lower()
    for pattern, level in EXPERIENCE_PATTERNS:
        if re.search(pattern, lower):
            if level == "years":
                match = re.search(pattern, lower)
                years = int(match.group(1))
                if years <= 1: return "fresher/intern"
                elif years <= 3: return "junior"
                elif years <= 6: return "mid-level"
                else: return "senior"
            return level
    return "fresher/intern"


def detect_degree(text: str) -> int:
    lower = text.lower()
    for kw, level in DEGREE_KEYWORDS.items():
        if kw in lower:
            return level
    return -1


def detect_sections(text: str) -> list:
    found = []
    lower = text.lower()
    for section, keywords in SECTION_INDICATORS.items():
        if any(k in lower for k in keywords):
            found.append(section)
    return found


def detect_quantification(text: str) -> bool:
    """Check if resume has any quantified achievements (numbers, %, etc.)"""
    return bool(re.search(r'\d+\s*(%|percent|users|clients|requests|ms|seconds|hours|days|projects|models)', text.lower()))


def detect_contact_completeness(parsed: dict) -> dict:
    missing = []
    if not parsed.get("email"): missing.append("email")
    if not parsed.get("phone"): missing.append("phone")
    if not parsed.get("linkedin"): missing.append("LinkedIn URL")
    if not parsed.get("github"): missing.append("GitHub URL")
    return {"complete": len(missing) == 0, "missing": missing}


# ---------------------------------------------------------------------------
# Main scoring
# ---------------------------------------------------------------------------

def score_resume(parsed: dict, job_role: str, required_skills: list, experience_required: Optional[str] = None) -> dict:
    """
    Score a parsed resume against job requirements.
    Returns: score (0-100), grade, matched_skills, missing_skills, strengths, improvements
    """
    text = (parsed.get("raw_text_preview") or "") + " " + " ".join([
        parsed.get("skills_raw", ""),
        parsed.get("education", ""),
        parsed.get("experience", ""),
    ])
    text_lower = normalize(text)

    # --- 1. Skill matching (40 points) ---
    required_lower = [normalize(s) for s in required_skills]
    resume_skills_lower = [normalize(s) for s in parsed.get("skills", [])]

    matched_skills = []
    missing_skills = []
    for skill in required_lower:
        skill_pattern = r'(?<![a-z])' + re.escape(skill) + r'(?![a-z])'
        if re.search(skill_pattern, text_lower) or any(skill in rs for rs in resume_skills_lower):
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    skill_score = 0
    if required_lower:
        skill_score = round((len(matched_skills) / len(required_lower)) * 40)
    else:
        skill_score = 30  # no required skills specified, neutral

    # --- 2. Role keyword alignment (20 points) ---
    role_keys = []
    for role_name, keywords in ROLE_KEYWORDS.items():
        if any(word in normalize(job_role) for word in role_name.split()):
            role_keys = keywords
            break
    if not role_keys and job_role:
        role_keys = normalize(job_role).split()

    role_hits = sum(1 for k in role_keys if k in text_lower)
    role_score = min(20, round((role_hits / max(len(role_keys), 1)) * 20))

    # --- 3. Experience level match (15 points) ---
    exp_score = 15
    detected_level = detect_experience_level(text)
    exp_mismatch_note = None
    if experience_required:
        req_lower = normalize(experience_required)
        if "senior" in req_lower and detected_level in ["fresher/intern", "junior"]:
            exp_score = 5
            exp_mismatch_note = f"Role requires senior experience; resume shows {detected_level} level."
        elif ("3+" in req_lower or "5+" in req_lower) and detected_level == "fresher/intern":
            exp_score = 8
            exp_mismatch_note = f"Role requires {experience_required}; resume shows {detected_level} level."
        elif ("entry" in req_lower or "fresh" in req_lower or "intern" in req_lower) and detected_level == "senior":
            exp_score = 10
        else:
            exp_score = 15

    # --- 4. Resume quality (25 points) ---
    quality_score = 0
    sections = detect_sections(text)

    # Sections present (10 pts)
    key_sections = ["experience", "education", "skills", "projects"]
    sections_found = sum(1 for s in key_sections if s in sections)
    quality_score += round((sections_found / 4) * 10)

    # Action verbs (5 pts)
    verb_count = count_action_verbs(text)
    quality_score += min(5, verb_count)

    # Quantification (5 pts)
    if detect_quantification(text):
        quality_score += 5

    # Contact completeness (5 pts)
    contact = detect_contact_completeness(parsed)
    if contact["complete"]:
        quality_score += 5
    elif len(contact["missing"]) <= 1:
        quality_score += 3

    total = skill_score + role_score + exp_score + quality_score
    total = max(0, min(100, total))

    # Grade
    if total >= 85: grade = "Excellent Match"
    elif total >= 70: grade = "Strong Match"
    elif total >= 55: grade = "Moderate Match"
    elif total >= 40: grade = "Partial Match"
    else: grade = "Weak Match"

    # Strengths
    strengths = []
    if len(matched_skills) >= len(required_lower) * 0.8 and required_lower:
        strengths.append(f"Covers {len(matched_skills)}/{len(required_lower)} required skills")
    if verb_count >= 5:
        strengths.append(f"Strong use of action verbs ({verb_count} found)")
    if detect_quantification(text):
        strengths.append("Contains quantified achievements (numbers/metrics)")
    if "projects" in sections:
        strengths.append("Has a dedicated Projects section — strong for technical roles")
    if parsed.get("github"):
        strengths.append("GitHub profile linked")
    if "achievements" in sections:
        strengths.append("Includes certifications or achievements section")
    if not strengths:
        strengths.append("Resume parsed successfully with valid contact info")

    # Improvement suggestions
    improvements = []
    weak = count_weak_phrases(text)
    if weak:
        improvements.append(f"Replace weak phrases like '{weak[0]}' with action verbs (built, designed, implemented, delivered)")
    if missing_skills:
        top_missing = missing_skills[:5]
        improvements.append(f"Missing required skills: {', '.join(top_missing)} — add these if you have them")
    if not detect_quantification(text):
        improvements.append("Add numbers and metrics to your bullets (e.g. 'Reduced load time by 40%', 'Processed 1000+ resumes')")
    if "projects" not in sections:
        improvements.append("Add a Projects section — critical for software/AI roles with limited work experience")
    if not parsed.get("github"):
        improvements.append("Add a GitHub profile URL to your contact section")
    if not parsed.get("linkedin"):
        improvements.append("Add a LinkedIn URL to your contact section")
    if exp_mismatch_note:
        improvements.append(exp_mismatch_note)
    if not improvements:
        improvements.append("Strong resume overall — consider tailoring the summary to each job description for higher ATS match rates")

    return {
        "score": total,
        "grade": grade,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "detected_experience_level": detected_level,
        "sections_found": sections,
        "strengths": strengths,
        "improvements": improvements,
        "breakdown": {
            "skill_match": skill_score,
            "role_alignment": role_score,
            "experience_fit": exp_score,
            "resume_quality": quality_score,
        }
    }


def rank_resumes(parsed_list: list, job_role: str, required_skills: list, experience_required: Optional[str] = None) -> list:
    """Score and rank multiple resumes, returning sorted list with scores."""
    results = []
    for item in parsed_list:
        analysis = score_resume(item["parsed"], job_role, required_skills, experience_required)
        results.append({
            "filename": item["filename"],
            "name": item["parsed"].get("name") or item["filename"],
            "email": item["parsed"].get("email"),
            "phone": item["parsed"].get("phone"),
            "github": item["parsed"].get("github"),
            "linkedin": item["parsed"].get("linkedin"),
            "skills": item["parsed"].get("skills", []),
            **analysis
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results
