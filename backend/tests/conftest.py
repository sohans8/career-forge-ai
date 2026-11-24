import io

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

SAMPLE_RESUME = """Asha Patil
asha@example.com | +91 98765 43210 | github.com/asha | linkedin.com/in/asha

SUMMARY
Diploma computer engineering student seeking a software developer internship.

EDUCATION
Diploma in Computer Engineering, Government Polytechnic Pune, 2025, 82%

SKILLS
Python, JavaScript, SQL, Git, HTML, CSS, React, data structures

PROJECTS
- Built a student attendance web app using React and Python used by 120 students
- Worked on a library database with SQL
- Developed a REST API with 12 endpoints and reduced response time by 35%
- Responsible for testing the mobile app

EXPERIENCE
- Led a team of 4 students to deploy a college event portal serving 800+ users
- Helped with website design

CERTIFICATIONS
- NPTEL Python for Data Science
"""


def make_docx(text: str) -> bytes:
    import docx

    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_pdf(text: str) -> bytes:
    """Minimal single-page text PDF (no external dependency)."""
    lines = [l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for l in text.splitlines()]
    stream = "BT /F1 9 Tf 12 TL 40 780 Td " + " ".join(f"({l}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture()
def sample_resume():
    return SAMPLE_RESUME
