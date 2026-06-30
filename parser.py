"""
parser.py
Core resume-parsing logic: extracts text from PDF/DOCX and pulls out
name, email, phone, skills, education, and experience using regex
and keyword-based heuristics (no external NLP model required).
"""

import re
import io
from typing import Optional

import pdfplumber
import docx


# ---------------------------------------------------------------------------
# Reference data used for keyword matching
# ---------------------------------------------------------------------------

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "c",
    "html", "css", "sql", "r", "go", "rust", "kotlin", "swift", "php",
    "react", "angular", "vue", "node.js", "node", "express", "django",
    "flask", "fastapi", "spring", "spring boot", ".net",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "data science", "data analysis", "data visualization", "statistics",
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch",
    "keras", "opencv",
    "mysql", "postgresql", "mongodb", "sqlite", "redis", "firebase",
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "github",
    "linux", "ci/cd", "rest api", "rest", "graphql", "microservices",
    "agile", "scrum", "tableau", "power bi", "excel",
]

EDUCATION_KEYWORDS = [
    "bachelor", "master", "b.tech", "btech", "m.tech", "mtech", "b.e",
    "m.e", "b.sc", "m.sc", "bca", "mca", "phd", "ph.d", "diploma",
    "university", "college", "institute", "school",
]

EXPERIENCE_SECTION_HEADERS = [
    "experience", "work experience", "professional experience",
    "employment history", "work history",
]

EDUCATION_SECTION_HEADERS = ["education", "academic background", "academics"]

SECTION_HEADERS_ALL = EXPERIENCE_SECTION_HEADERS + EDUCATION_SECTION_HEADERS + [
    "skills", "technical skills", "projects", "certifications",
    "summary", "objective", "contact", "achievements", "awards",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s-]?)?(\(?\d{3,5}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}"
)
LINKEDIN_RE = re.compile(r"(linkedin\.com/in/[A-Za-z0-9\-_/]+)", re.I)
GITHUB_RE = re.compile(r"(github\.com/[A-Za-z0-9\-_/]+)", re.I)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_stream: io.BytesIO) -> str:
    text_parts = []
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_stream: io.BytesIO) -> str:
    document = docx.Document(file_stream)
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(filename: str, file_bytes: bytes) -> str:
    stream = io.BytesIO(file_bytes)
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(stream)
    elif lower.endswith(".docx"):
        return extract_text_from_docx(stream)
    else:
        raise ValueError("Unsupported file type. Please upload a .pdf or .docx file.")


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------

def find_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def find_phone(text: str) -> Optional[str]:
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0)
        digits = re.sub(r"\D", "", candidate)
        if 7 <= len(digits) <= 13:
            return candidate.strip()
    return None


def find_links(text: str) -> dict:
    linkedin = LINKEDIN_RE.search(text)
    github = GITHUB_RE.search(text)
    return {
        "linkedin": ("https://" + linkedin.group(1)) if linkedin else None,
        "github": ("https://" + github.group(1)) if github else None,
    }


def guess_name(text: str) -> Optional[str]:
    """
    Heuristic: the candidate's name is usually the first non-empty line
    that isn't an email/phone/URL and doesn't look like a section header.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:6]:
        lower = line.lower()
        if EMAIL_RE.search(line) or LINKEDIN_RE.search(line) or GITHUB_RE.search(line):
            continue
        if any(h in lower for h in SECTION_HEADERS_ALL):
            continue
        if len(line.split()) <= 5 and not any(ch.isdigit() for ch in line):
            return line.title() if line.isupper() else line
    return lines[0] if lines else None


def find_skills(text: str) -> list:
    lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        pattern = r"(?<![a-zA-Z])" + re.escape(skill) + r"(?![a-zA-Z])"
        if re.search(pattern, lower):
            found.append(skill)
    # de-dupe, preserve a clean display order
    seen = set()
    ordered = []
    for s in found:
        if s not in seen:
            seen.add(s)
            ordered.append(s.title() if len(s) > 3 else s.upper())
    return ordered


def extract_section(text: str, headers: list) -> Optional[str]:
    """
    Grabs the block of text under a matching section header, stopping at
    the next recognized section header.
    """
    lines = text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        clean = line.strip().lower().rstrip(":")
        if clean in headers:
            start_idx = i + 1
            break
    if start_idx is None:
        return None

    collected = []
    for line in lines[start_idx:]:
        clean = line.strip().lower().rstrip(":")
        if clean in SECTION_HEADERS_ALL and clean not in headers:
            break
        if line.strip():
            collected.append(line.strip())
    return "\n".join(collected) if collected else None


def find_education(text: str) -> str:
    section = extract_section(text, EDUCATION_SECTION_HEADERS)
    if section:
        return section
    # fallback: scan whole document for education keywords
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    matches = [l for l in lines if any(k in l.lower() for k in EDUCATION_KEYWORDS)]
    return "\n".join(matches) if matches else "Not found"


def find_experience(text: str) -> str:
    section = extract_section(text, EXPERIENCE_SECTION_HEADERS)
    return section if section else "Not found"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_resume(filename: str, file_bytes: bytes) -> dict:
    text = extract_text(filename, file_bytes)
    if not text.strip():
        raise ValueError("Could not extract any text from this file. It may be a scanned/image-based document.")

    links = find_links(text)

    return {
        "name": guess_name(text),
        "email": find_email(text),
        "phone": find_phone(text),
        "linkedin": links["linkedin"],
        "github": links["github"],
        "skills": find_skills(text),
        "education": find_education(text),
        "experience": find_experience(text),
        "raw_text_preview": text[:800],
    }
