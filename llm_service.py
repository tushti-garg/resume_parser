import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-5"


def _call(system, user, max_tokens=400):
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return None  # caller falls back to rule-based text


def explain_candidate_fit(parsed, job, match_result):
    """LLM paragraph explaining why a candidate fits a job posting.
    Grounded only in extracted facts — no invented claims."""
    system = (
        "You write short, factual recruiter-facing summaries of why a candidate "
        "matches a job. Use ONLY the facts given. Do not invent skills, employers, "
        "or achievements not present in the data. 3-4 sentences, professional tone."
    )
    user = json.dumps({
        "role": job["title"],
        "required_skills": job["skills"],
        "candidate_name": parsed.get("name"),
        "candidate_skills": parsed.get("skills"),
        "matched_skills": match_result["matched_skills"],
        "missing_skills": match_result["missing_skills"],
        "experience_section_excerpt": (parsed.get("experience") or "")[:800],
        "fit_score": match_result["fit_score"],
    })
    text = _call(system, user)
    if text:
        return text
    # Fallback if no API key / call fails
    matched = ", ".join(match_result["matched_skills"]) or "no listed skills"
    return (f"{parsed.get('name')} matches {len(match_result['matched_skills'])} of "
            f"{len(job['skills'])} required skills ({matched}), with a computed fit "
            f"score of {match_result['fit_score']}/100.")


def explain_improvements(parsed, role, ats_result, gap_result):
    system = (
        "You are a career coach giving specific, encouraging, concrete resume feedback "
        "for a candidate targeting a specific role. Use ONLY the facts given — do not "
        "invent details about their background. 4-6 sentences, actionable, no generic filler."
    )
    user = json.dumps({
        "target_role": role,
        "candidate_skills": parsed.get("skills"),
        "missing_skills_for_role": gap_result.get("missing_skills"),
        "ats_breakdown": ats_result.get("breakdown"),
        "word_count": ats_result.get("word_count"),
    })
    text = _call(system, user)
    if text:
        return text
    return "Add the missing skills listed below if you have relevant experience, and quantify your achievements with numbers wherever possible."
