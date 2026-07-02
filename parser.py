import re
import io
import pdfplumber
import docx
from pdf2image import convert_from_bytes
import pytesseract

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}\b")
URL_RE = re.compile(r"(https?://[^\s]+|(?:www\.)?linkedin\.com/[^\s]+|(?:www\.)?github\.com/[^\s]+)")

SKILLS_DB = [
    "python", "java", "c++", "c#", "javascript", "typescript", "sql", "r", "go", "rust",
    "html", "css", "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
    "spring", "express", "next.js", "tailwind",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "ci/cd",
    "git", "github", "gitlab", "linux", "bash",
    "machine learning", "deep learning", "nlp", "computer vision", "pytorch",
    "tensorflow", "scikit-learn", "pandas", "numpy", "keras",
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "excel", "tableau", "power bi", "figma", "jira", "agile", "scrum",
]

SECTION_HEADERS = ["experience", "education", "skills", "projects", "certifications",
                    "summary", "objective", "achievements", "publications"]


def _extract_text_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    # If almost no text was found, it's likely a scanned/image-based PDF -> OCR fallback
    if len(text.strip()) < 40:
        text = _ocr_pdf(file_bytes)
    return text


def _ocr_pdf(file_bytes):
    text = ""
    try:
        images = convert_from_bytes(file_bytes)
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
    except Exception as e:
        text = ""
    return text


def _extract_text_docx(file_bytes):
    document = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(filename, file_bytes):
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        return _extract_text_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return _extract_text_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type: " + ext)


def guess_name(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:8]:
        lower = line.lower()
        if EMAIL_RE.search(line) or PHONE_RE.search(line) or URL_RE.search(line):
            continue
        if any(h in lower for h in SECTION_HEADERS):
            continue
        words = line.split()
        if 1 <= len(words) <= 5 and all(w[0].isupper() for w in words if w[0].isalpha()):
            return line
    return lines[0] if lines else "Not found"


def extract_email(text):
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def extract_phone(text):
    match = PHONE_RE.search(text)
    return match.group(0) if match else None


def extract_links(text):
    return list(set(URL_RE.findall(text)))


def extract_skills(text):
    lower = text.lower()
    return sorted({s for s in SKILLS_DB if s in lower})


def extract_section(text, section_name, next_sections=None):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if section_name in line.lower().strip():
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    stop_words = next_sections or [s for s in SECTION_HEADERS if s != section_name]
    for i in range(start, len(lines)):
        if any(sw in lines[i].lower().strip() for sw in stop_words) and lines[i].strip():
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def extract_all(filename, file_bytes):
    text = extract_text(filename, file_bytes)
    return {
        "filename": filename,
        "name": guess_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "links": extract_links(text),
        "skills": extract_skills(text),
        "education": extract_section(text, "education"),
        "experience": extract_section(text, "experience"),
        "raw_text": text,
    }
