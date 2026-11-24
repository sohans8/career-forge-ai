import pytest

from backend.app.services import resume_service as rs
from backend.tests.conftest import make_docx, make_pdf

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_extract_text_docx_and_pdf(sample_resume):
    assert "Python" in rs.extract_text("r.docx", make_docx(sample_resume))
    assert "Python" in rs.extract_text("r.pdf", make_pdf(sample_resume))


def test_extract_rejects_bad_files():
    with pytest.raises(rs.ResumeError):
        rs.extract_text("r.pdf", b"not a pdf")
    with pytest.raises(rs.ResumeError):
        rs.extract_text("r.txt", b"hello")


def test_scoring_matches_skills(sample_resume):
    s = rs.score_resume(sample_resume, "Software Developer")
    matched = {m for m, _ in s["matched"]}
    assert {"python", "sql", "git"} <= matched
    assert 0 <= s["ats_score"] <= 100
    assert set(s["breakdown"]) == {"keywords", "impact", "formatting", "completeness"}


def test_rewrite_adds_verb_and_metric_placeholder():
    out = rs.rule_based_rewrite("Responsible for testing the mobile app")
    assert out.startswith("Led testing") and "[add result" in out


def test_api_analyze_docx(client, sample_resume):
    r = client.post("/api/resume/analyze", data={"target_role": "Software Developer"},
                    files={"file": ("resume.docx", make_docx(sample_resume), DOCX)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_role"] == "Software Developer"
    assert body["matched_skills"] and body["missing_skills"]
    assert body["learning_checklist"][0]["resources"]
    rewrites = [x for sec in body["section_feedback"] for x in sec["rewrites"]]
    assert rewrites and all(x["before"] != x["after"] for x in rewrites)


def test_api_analyze_pdf(client, sample_resume):
    r = client.post("/api/resume/analyze", data={"target_role": "software developer"},
                    files={"file": ("resume.pdf", make_pdf(sample_resume), PDF)})
    assert r.status_code == 200 and r.json()["ats_score"] > 0


def test_api_rejects_wrong_type_unknown_role_and_big_file(client, sample_resume):
    bad = client.post("/api/resume/analyze", data={"target_role": "Software Developer"},
                      files={"file": ("a.txt", b"x" * 200, "text/plain")})
    assert bad.status_code == 400
    role = client.post("/api/resume/analyze", data={"target_role": "Astronaut Wizard"},
                       files={"file": ("a.docx", make_docx(sample_resume), DOCX)})
    assert role.status_code == 422
    big = client.post("/api/resume/analyze", data={"target_role": "Software Developer"},
                      files={"file": ("a.pdf", b"%PDF" + b"0" * (6 * 1024 * 1024), PDF)})
    assert big.status_code == 413


def test_roles_endpoint(client):
    roles = client.get("/api/resume/roles").json()["roles"]
    assert "Software Developer" in roles and "Civil Engineer" in roles
