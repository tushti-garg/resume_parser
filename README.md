# ResumeAI — Smart Resume Analyzer

A dual-mode resume analysis tool built with Python (Flask) and vanilla JavaScript. Designed for both job seekers and recruiters.

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![flask](https://img.shields.io/badge/flask-3.x-black)
![license](https://img.shields.io/badge/license-MIT-green)

**Live Demo →** [resume-parser-3r3h.onrender.com](https://resume-parser-3r3h.onrender.com)

---

## What it does

### 🎯 Candidate Mode
Upload your resume and enter your target role. Get:
- An **ATS match score out of 100**
- Score breakdown across 4 categories: Skill Match, Role Alignment, Experience Fit, Resume Quality
- Matched vs missing skills highlighted
- Specific, actionable improvement suggestions
- Parsed contact info verification

### 🏢 Recruiter Mode
Upload up to **20 resumes at once**, set your job requirements, and get:
- A **ranked shortlist** of candidates with match scores
- Per-candidate skill coverage and gaps
- Contact info (email, LinkedIn, GitHub) surfaced automatically
- Top improvement note per candidate

---

## Demo

| Candidate Mode | Recruiter Mode |
|---|---|
| Enter role → upload resume → get score + tips | Set requirements → upload resumes → ranked shortlist |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Parsing | pdfplumber, python-docx, regex |
| Scoring | Custom NLP keyword + heuristic engine |
| Frontend | HTML, CSS, JavaScript (no framework) |
| Deployment | Render (free tier) |

---

## Project Structure

```
resume-parser/
├── app.py              # Flask app + 3 API endpoints
├── parser.py           # PDF/DOCX text extraction
├── analyzer.py         # Resume scoring and ranking engine
├── index.html          # Dual-mode frontend (served by Flask)
├── requirements.txt    # Python dependencies
├── sample_resumes/
│   └── sample_resume.docx   # Test file
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.10+

### Installation

```bash
git clone https://github.com/tushti-garg/resume_parser.git
cd resume_parser
pip install -r requirements.txt
```

### Run locally

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

---

## API Reference

### `POST /api/analyze`
Candidate mode — single resume + job requirements → score + tips.

**Form fields:**
| Field | Type | Description |
|---|---|---|
| `resume` | file | PDF or DOCX resume |
| `job_role` | string | Target job title |
| `required_skills` | string | Comma-separated skills |
| `experience_required` | string | e.g. "Fresher", "2+ years" |

**Response:**
```json
{
  "success": true,
  "parsed": { "name": "...", "email": "...", "skills": [...] },
  "analysis": {
    "score": 78,
    "grade": "Strong Match",
    "matched_skills": ["Python", "Flask", "SQL"],
    "missing_skills": ["Docker"],
    "strengths": ["Covers 5/6 required skills", "GitHub profile linked"],
    "improvements": ["Add quantified achievements", "Add a Projects section"],
    "breakdown": {
      "skill_match": 33,
      "role_alignment": 15,
      "experience_fit": 15,
      "resume_quality": 15
    }
  }
}
```

### `POST /api/rank`
Recruiter mode — multiple resumes + job requirements → ranked list.

**Form fields:** same as above, but `resumes` accepts multiple files (up to 20).

### `POST /api/parse`
Raw extraction only — no scoring. Returns name, email, phone, skills, education, experience.

### `GET /api/health`
Returns `{"status": "ok"}`.

---

## How the Scoring Works

Scores are calculated across 4 dimensions (total 100 points):

| Category | Max Points | How it's calculated |
|---|---|---|
| Skill Match | 40 | % of required skills found in resume text |
| Role Alignment | 20 | Match against role-specific keyword bank |
| Experience Fit | 15 | Detected experience level vs required |
| Resume Quality | 25 | Sections present, action verbs, metrics, contact completeness |

---

## Known Limitations

- Multi-column PDF layouts can affect text extraction order (common limitation across all resume parsers)
- Scanned/image-based PDFs are not supported (no OCR)
- Skill matching is keyword-based, not semantic — exact or near-exact matches required

## Roadmap

- [ ] OCR support for scanned resumes
- [ ] Export ranked results as CSV
- [ ] Job description paste-in for automatic skill extraction
- [ ] Unit tests with pytest

---

## License

MIT — free to use, modify, and distribute.

## Author

**Tushti Garg**  
[LinkedIn](https://www.linkedin.com/in/tushti-garg/) · [GitHub](https://github.com/tushti-garg) · tushtigarg456@gmail.com
