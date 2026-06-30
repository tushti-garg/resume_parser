# Resume Parser

A web app that extracts key candidate details — name, email, phone, skills, education, and experience — from uploaded PDF or DOCX resumes. Built with a Python (Flask) backend and a vanilla HTML/CSS/JS frontend.

## Demo

Upload a resume → the app parses the text and returns structured fields in seconds.

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![flask](https://img.shields.io/badge/flask-3.x-black)

## Features

- Upload `.pdf` or `.docx` resumes via drag-and-drop or file picker
- Extracts: name, email, phone number, LinkedIn, GitHub, skills, education, experience
- Skill detection against a curated keyword list covering languages, frameworks, cloud, and tools
- Simple REST API (`/api/parse`) that returns clean JSON — easy to plug into other tools
- No external NLP model or API key required; runs fully offline

## Tech Stack

| Layer    | Technology              |
|----------|--------------------------|
| Backend  | Python, Flask            |
| Parsing  | pdfplumber, python-docx, regex |
| Frontend | HTML, CSS, JavaScript (no framework) |

## Project Structure

```
resume-parser/
├── backend/
│   ├── app.py              # Flask app + API routes
│   ├── parser.py           # Core resume-parsing logic
│   └── requirements.txt    # Python dependencies
├── frontend/
│   └── index.html          # Upload UI (served by Flask)
├── sample_resumes/
│   ├── sample_resume.txt   # Plain-text version for reference
│   └── sample_resume.docx  # Try this file to test the app
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10 or higher

### Installation

```bash
# Clone the repo
git clone https://github.com/tushti-garg/resume-parser.git
cd resume-parser

# Install dependencies
pip install -r backend/requirements.txt
```

### Run the app

```bash
cd backend
python app.py
```

Open `http://localhost:5000` in your browser, upload a resume (try `sample_resumes/sample_resume.docx`), and click **Parse Resume**.

## API Reference

### `POST /api/parse`

Upload a resume file and receive parsed fields as JSON.

**Request:** `multipart/form-data` with a `resume` field containing a `.pdf` or `.docx` file.

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "Aanya Sharma",
    "email": "aanya.sharma@example.com",
    "phone": "+91 9876543210",
    "linkedin": "https://linkedin.com/in/aanyasharma",
    "github": "https://github.com/aanyasharma",
    "skills": ["Python", "Java", "SQL", "React", "Flask"],
    "education": "Bachelor of Technology in Computer Science\nDelhi Technical University, 2021 - 2025",
    "experience": "Software Engineering Intern, TechNova Pvt Ltd\n..."
  }
}
```

### `GET /api/health`
Returns `{"status": "ok"}` — useful for uptime checks.

## How It Works

1. **Text extraction** — `pdfplumber` extracts text from PDFs; `python-docx` reads paragraphs from DOCX files.
2. **Field extraction** — regex patterns identify emails, phone numbers, and social links. The candidate's name is inferred from the first non-header line near the top of the document.
3. **Skill matching** — the extracted text is checked against a curated list of ~70 common technical skills and tools.
4. **Section extraction** — the parser looks for section headers like "Education" and "Experience" and captures the text block beneath each one until the next recognized header.

## Known Limitations

- Resumes with complex multi-column layouts can confuse text-extraction order (this is a common limitation across most resume parsers, including commercial ATS tools).
- Scanned/image-based PDFs (no embedded text layer) aren't supported — OCR is not included.
- Skill and section detection rely on keyword/heading matching rather than a trained NLP model, so unconventional formatting may reduce accuracy.

## Roadmap

- [ ] Add OCR support for scanned resumes (e.g., via `pytesseract`)
- [ ] Score resumes against a pasted job description
- [ ] Export parsed results as CSV/JSON download
- [ ] Add unit tests with `pytest`

## License

MIT License — free to use, modify, and distribute.

## Author

**Tushti Garg**
[LinkedIn](https://www.linkedin.com/in/tushti-garg/) · [GitHub](https://github.com/tushti-garg)
