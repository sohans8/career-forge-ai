"""Resume parsing, ATS scoring and the learning loop.

Scoring is deterministic and explainable. If an LLM key is configured it adds
better bullet rewrites and a short summary on top of the rule-based result.
"""
from __future__ import annotations

import csv
import difflib
import io
import logging
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus

from backend.app.config import DATA_DIR
from backend.app.services.llm_service import LLMError, Message, llm_service

log = logging.getLogger("career_forge.resume")

SKILLS_FILE = DATA_DIR / "job_skills_ats.csv"

SECTION_PATTERNS = {
    "summary": r"(summary|objective|profile|about me)",
    "education": r"(education|academic|qualification)",
    "skills": r"(skills|technical skills|technologies|competenc)",
    "projects": r"(projects?|academic projects?|personal projects?)",
    "experience": r"(experience|internships?|work history|employment|training)",
    "certifications": r"(certifications?|courses|licen[sc]es)",
    "achievements": r"(achievements?|awards?|honou?rs|extracurricular|activities)",
}
SECTION_WEIGHTS = {"education": 25, "skills": 25, "projects": 20, "experience": 15, "summary": 5, "certifications": 5, "achievements": 5}

STRONG_VERBS = {
    "achieved", "automated", "analyzed", "analysed", "architected", "built", "created", "designed", "developed", "delivered",
    "deployed", "engineered", "implemented", "improved", "increased", "integrated", "launched", "led", "managed", "optimized",
    "optimised", "reduced", "resolved", "streamlined", "trained", "tested", "migrated", "organized", "organised", "coordinated",
    "fabricated", "calibrated", "configured", "constructed", "drafted", "surveyed", "wrote", "published", "won", "mentored",
}
WEAK_STARTS = [
    (r"^(responsible for|duties included|tasked with)\s+", "Led "),
    (r"^(worked on|worked with|working on)\s+", "Developed "),
    (r"^(helped|assisted|helping)( with| in)?\s+", "Supported "),
    (r"^(involved in|participated in)\s+", "Contributed to "),
    (r"^(made|did)\s+", "Built "),
]
SYNONYMS = {
    "js": "javascript", "reactjs": "react", "react.js": "react", "node": "node.js", "nodejs": "node.js",
    "ml": "machine learning", "dl": "deep learning", "sklearn": "scikit-learn", "powerbi": "power bi",
    "oops": "oop", "object oriented": "oop", "rest": "rest api", "restful": "rest api", "ms excel": "excel",
    "ms office": "ms office", "dsa": "data structures", "cpp": "c++",
}

# Curated resources. Everything else falls back to course search pages.
ROADMAP_SH = {"python": "python", "javascript": "javascript", "react": "react", "sql": "sql", "docker": "docker",
              "node.js": "nodejs", "typescript": "typescript", "java": "java", "git": "git-github", "mongodb": "mongodb",
              "aws": "aws", "machine learning": "ai-data-scientist", "data structures": "computer-science"}

MINI_PROJECTS = {
    "python": "Build a CLI expense tracker with file storage and unit tests.",
    "javascript": "Build a weather or quiz web app using a public API.",
    "react": "Build a responsive task manager with React hooks and deploy it on Netlify.",
    "sql": "Design a library database, write 10 analytical queries and publish the schema on GitHub.",
    "machine learning": "Train a classifier on a Kaggle dataset, report accuracy and F1, and write up the findings.",
    "pandas": "Clean a messy public CSV and publish a notebook with 5 insights.",
    "docker": "Containerise one of your existing projects and document the run steps.",
    "git": "Contribute 3 pull requests to an open-source repository or your own projects with clear commit messages.",
    "autocad": "Draw a complete floor plan or machine part with dimensions and share the drawing set.",
    "excel": "Build a sales dashboard with pivot tables and charts from a sample dataset.",
    "tally": "Record 30 sample transactions, generate trial balance and GST reports.",
    "plc": "Simulate a motor start-stop circuit in a PLC simulator and document the ladder logic.",
    "solidworks": "Model a 5-part assembly and produce a drawing with GD&T.",
    "embedded systems": "Build a temperature logger with Arduino and display the readings.",
    "data visualization": "Create a public dashboard (Power BI or Tableau Public) on an Indian open dataset.",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


class ResumeError(ValueError):
    pass


# ----------------------------------------------------------------- parsing
def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        if not data.startswith(b"%PDF"):
            raise ResumeError("File content is not a valid PDF")
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as exc:
            raise ResumeError("Could not read this PDF. It may be encrypted or corrupted.") from exc
    elif name.endswith(".docx"):
        if not data.startswith(b"PK"):
            raise ResumeError("File content is not a valid DOCX")
        import docx
        try:
            document = docx.Document(io.BytesIO(data))
            parts = [p.text for p in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            text = "\n".join(parts)
        except Exception as exc:
            raise ResumeError("Could not read this DOCX file.") from exc
    else:
        raise ResumeError("Only PDF and DOCX files are supported")
    text = text.replace("\x00", "").strip()
    if len(text) < 80:
        raise ResumeError("Very little text was found. Scanned/image-only resumes cannot be analysed. Export a text-based PDF.")
    return text


# ---------------------------------------------------------------- skills db
class SkillBank:
    def __init__(self, path: Path = SKILLS_FILE):
        self.path = path
        self._mtime = 0.0
        self._roles: dict[str, list[tuple[str, float]]] = {}

    def _load(self) -> dict[str, list[tuple[str, float]]]:
        mtime = self.path.stat().st_mtime if self.path.exists() else 0.0
        if mtime != self._mtime:
            roles: dict[str, dict[str, float]] = defaultdict(dict)
            if self.path.exists():
                with self.path.open(encoding="utf-8", newline="") as fh:
                    for row in csv.DictReader(fh):
                        skill, w = _norm(row["skill"]), float(row["weight"])
                        roles[row["role"]][skill] = max(w, roles[row["role"]].get(skill, 0))
            self._roles = {r: sorted(d.items(), key=lambda kv: -kv[1]) for r, d in roles.items()}
            self._mtime = mtime
        return self._roles

    def roles(self) -> list[str]:
        return sorted(self._load())

    def resolve_role(self, role: str) -> str | None:
        roles = self._load()
        if role in roles:
            return role
        lowered = {r.lower(): r for r in roles}
        if role.lower() in lowered:
            return lowered[role.lower()]
        match = difflib.get_close_matches(role.lower(), list(lowered), n=1, cutoff=0.6)
        return lowered[match[0]] if match else None

    def skills_for(self, role: str, limit: int = 24) -> list[tuple[str, float]]:
        return self._load()[role][:limit]


skill_bank = SkillBank()


def _skill_in_text(skill: str, text: str) -> bool:
    pattern = r"(?<![a-z0-9+#.])" + re.escape(skill) + r"(?![a-z0-9+#])"
    if re.search(pattern, text):
        return True
    return any(alias_target == skill and re.search(r"(?<![a-z0-9+#.])" + re.escape(alias) + r"(?![a-z0-9+#])", text)
               for alias, alias_target in SYNONYMS.items())


# ----------------------------------------------------------------- scoring
def detect_sections(text: str) -> dict[str, bool]:
    found = {k: False for k in SECTION_PATTERNS}
    for line in text.splitlines():
        stripped = line.strip().strip(":-_ ").lower()
        if 0 < len(stripped) <= 40:
            for key, pat in SECTION_PATTERNS.items():
                if re.fullmatch(pat + r"[a-z &/]*", stripped):
                    found[key] = True
    return found


NON_ACHIEVEMENT_SECTIONS = {"education", "skills", "certifications"}


def extract_bullets(text: str) -> list[str]:
    """Achievement bullets from projects/experience/other sections (skips education, skills, certifications)."""
    bullets = []
    current = None
    for line in text.splitlines():
        s = line.strip()
        head = s.strip(":-_ ").lower()
        if 0 < len(head) <= 40:
            hit = next((k for k, pat in SECTION_PATTERNS.items() if re.fullmatch(pat + r"[a-z &/]*", head)), None)
            if hit:
                current = hit
                continue
        if current in NON_ACHIEVEMENT_SECTIONS:
            continue
        m = re.match(r"^[\u2022\u25cf\u25aa\u2023\-\*\u2013>\u00b7]\s*(.+)$", s)
        if m and len(m.group(1).split()) >= 4:
            bullets.append(m.group(1).strip())
        elif not m and 6 <= len(s.split()) <= 40 and s[:1].isupper() and s.endswith(".") is False and _first_word(s) in STRONG_VERBS:
            bullets.append(s)
    return bullets


def _first_word(s: str) -> str:
    m = re.match(r"[A-Za-z]+", s)
    return m.group(0).lower() if m else ""


def has_metric(s: str) -> bool:
    return bool(re.search(r"\d+\s*(%|x|\+|k\b|lakh|crore|users|students|hours|days|ms|seconds|projects|models|apps|rs|inr|\u20b9)|[\u20b9$]\s*\d|\b\d{2,}\b", s.lower()))


def weak_bullets(bullets: list[str]) -> list[str]:
    return [b for b in bullets if _first_word(b) not in STRONG_VERBS or not has_metric(b)]


def rule_based_rewrite(bullet: str) -> str:
    out = bullet.strip().rstrip(".")
    for pat, repl in WEAK_STARTS:
        if re.match(pat, out, flags=re.I):
            out = re.sub(pat, repl, out, flags=re.I)
            break
    else:
        if _first_word(out) not in STRONG_VERBS:
            first = out.split(" ", 1)[0]
            keep_case = first.isupper() or any(c.isupper() for c in first[1:])
            out = "Developed " + (out if keep_case else out[:1].lower() + out[1:]) if out else out
    if not has_metric(out):
        out += ", achieving [add result: e.g. 30% faster / 500+ users / 95% accuracy]"
    return out[0].upper() + out[1:]


def score_resume(text: str, role: str) -> dict:
    lower = _norm(text)
    words = len(text.split())
    sections = detect_sections(text)
    bullets = extract_bullets(text)

    # keywords
    role_skills = skill_bank.skills_for(role)
    matched = [(s, w) for s, w in role_skills if _skill_in_text(s, lower)]
    missing = [(s, w) for s, w in role_skills if (s, w) not in matched]
    total_w = sum(w for _, w in role_skills) or 1
    keywords = round(100 * sum(w for _, w in matched) / total_w)

    # impact
    if bullets:
        verb_ratio = sum(1 for b in bullets if _first_word(b) in STRONG_VERBS) / len(bullets)
        metric_ratio = sum(1 for b in bullets if has_metric(b)) / len(bullets)
        impact = round(100 * (0.5 * verb_ratio + 0.5 * min(1.0, metric_ratio * 1.5)))
    else:
        impact = 15  # no recognisable bullet points

    # formatting
    fmt = 0
    fmt += 20 if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text) else 0
    fmt += 15 if re.search(r"(\+?\d[\d\s-]{8,})", text) else 0
    has_links = bool(re.search(r"(linkedin\.com|github\.com)", lower))
    fmt += 15 if has_links else 0
    fmt += 20 if 250 <= words <= 900 else (10 if 120 <= words < 250 or 900 < words <= 1300 else 0)
    fmt += 15 if len(bullets) >= 4 else 5 if bullets else 0
    fmt += 15 if sum(sections.values()) >= 4 else 7 if sum(sections.values()) >= 2 else 0

    # completeness
    completeness = sum(SECTION_WEIGHTS[k] for k, v in sections.items() if v)

    ats = round(0.40 * keywords + 0.25 * impact + 0.20 * fmt + 0.15 * completeness)
    return {
        "ats_score": max(0, min(100, ats)),
        "breakdown": {"keywords": keywords, "impact": impact, "formatting": min(100, fmt), "completeness": min(100, completeness)},
        "matched": matched, "missing": missing, "sections": sections, "bullets": bullets, "word_count": words, "has_links": has_links,
    }


# ----------------------------------------------------------- learning loop
def build_learning_checklist(missing: list[tuple[str, float]], role: str, limit: int = 8) -> list[dict]:
    items = []
    for idx, (skill, weight) in enumerate(missing[:limit]):
        q = quote_plus(skill)
        resources = [
            {"title": f"SWAYAM / NPTEL courses on {skill}", "url": f"https://swayam.gov.in/explorer?searchText={q}", "cost": "free"},
            {"title": f"Coursera: {skill} (audit for free)", "url": f"https://www.coursera.org/search?query={q}", "cost": "free to audit / paid certificate"},
            {"title": f"YouTube tutorials: {skill}", "url": f"https://www.youtube.com/results?search_query={q}+full+course", "cost": "free"},
        ]
        if skill in ROADMAP_SH:
            resources.insert(0, {"title": f"roadmap.sh guide: {skill}", "url": f"https://roadmap.sh/{ROADMAP_SH[skill]}", "cost": "free"})
        items.append({
            "id": f"skill-{idx + 1}",
            "priority": "high" if idx < 3 else "medium" if idx < 6 else "low",
            "skill": skill,
            "why": f"{skill.title()} appears in {int(round(weight * 100))}% of {role} skill profiles in the dataset.",
            "learn": f"Spend 1-2 weeks on {skill} fundamentals, then apply it in a small project.",
            "mini_project": MINI_PROJECTS.get(skill, f"Build a small project that uses {skill}, put it on GitHub with a README and one measurable result."),
            "resources": resources,
            "done": False,
        })
    return items


# ----------------------------------------------------------------- analyze
def analyze(filename: str, data: bytes, target_role: str) -> dict:
    role = skill_bank.resolve_role(target_role)
    if not role:
        raise ResumeError(f"Unknown target role. Choose one of: {', '.join(skill_bank.roles())}")
    text = extract_text(filename, data)
    s = score_resume(text, role)

    weak = weak_bullets(s["bullets"])[:5]
    rewrites = [{"before": b, "after": rule_based_rewrite(b)} for b in weak]
    section_feedback = _section_feedback(s, rewrites)
    summary = _default_summary(s["ats_score"], role, len(s["matched"]), len(s["missing"]))
    llm_used = False

    if llm_service.available and weak:
        try:
            enriched = _llm_enrich(text, role, weak, [m for m, _ in s["missing"][:8]])
            if enriched.get("rewrites"):
                rewrites = [{"before": r["before"], "after": r["after"]} for r in enriched["rewrites"]
                            if isinstance(r, dict) and r.get("before") and r.get("after")][:5] or rewrites
                section_feedback = _section_feedback(s, rewrites)
            summary = str(enriched.get("summary") or summary)
            llm_used = True
        except (LLMError, KeyError, TypeError) as exc:
            log.info("LLM enrichment skipped: %s", exc)

    return {
        "target_role": role,
        "ats_score": s["ats_score"],
        "breakdown": s["breakdown"],
        "matched_skills": [m for m, _ in s["matched"]],
        "missing_skills": [m for m, _ in s["missing"]],
        "sections_found": [k for k, v in s["sections"].items() if v],
        "section_feedback": section_feedback,
        "learning_checklist": build_learning_checklist(s["missing"], role),
        "summary": summary,
        "word_count": s["word_count"],
        "llm_used": llm_used,
    }


def _default_summary(score: int, role: str, matched: int, missing: int) -> str:
    band = "strong" if score >= 75 else "decent" if score >= 55 else "needs work"
    return (f"Your resume is {band} for {role} (ATS score {score}/100). It matches {matched} of {matched + missing} "
            f"target skills. Close the skill gaps below, add measurable results to your bullets, then re-upload.")


def _section_feedback(s: dict, rewrites: list[dict]) -> list[dict]:
    fb = []
    sec = s["sections"]
    b = s["breakdown"]
    missing_secs = [k for k in ("summary", "education", "skills", "projects", "experience") if not sec[k]]
    if missing_secs:
        fb.append({"section": "Structure", "status": "warn",
                   "feedback": [f"Add a clearly titled '{k.title()}' section." for k in missing_secs], "rewrites": []})
    fb.append({"section": "Impact & bullet points", "status": "good" if b["impact"] >= 70 else "warn",
               "feedback": ["Start every bullet with a strong action verb (Built, Reduced, Led).",
                            "Add numbers: percentage, users, time saved, accuracy or cost."] if b["impact"] < 70 else ["Bullets use action verbs and results. Keep it up."],
               "rewrites": rewrites})
    fb.append({"section": "Keywords", "status": "good" if b["keywords"] >= 70 else "warn",
               "feedback": [f"Missing high-value skills: {', '.join(m for m, _ in s['missing'][:6])}."] if s["missing"] else ["Strong keyword coverage."],
               "rewrites": []})
    fmt_tips = []
    if not s["has_links"]:
        fmt_tips.append("Include LinkedIn and GitHub links in the header.")
    if s["word_count"] > 900:
        fmt_tips.append("Trim to one page (about 400-700 words) for a fresher resume.")
    if s["word_count"] < 250:
        fmt_tips.append("The resume is short. Add projects, internships and certifications.")
    if fmt_tips:
        fb.append({"section": "Formatting", "status": "warn", "feedback": fmt_tips, "rewrites": []})
    return fb


def _llm_enrich(text: str, role: str, weak: list[str], missing: list[str]) -> dict:
    system = "You are an expert technical recruiter for Indian freshers. Reply with JSON only."
    prompt = (
        f"Target role: {role}\nMissing skills: {missing}\nWeak resume bullets:\n"
        + "\n".join(f"- {b}" for b in weak)
        + "\n\nReturn JSON: {\"summary\": \"2 sentences of overall feedback\", \"rewrites\": [{\"before\": \"<original bullet>\", \"after\": \"<stronger bullet with action verb and a measurable result>\"}]}.\n"
        "Rules: keep each rewrite truthful to the original. Where a number is unknown, use a bracketed placeholder like [X%], never invent facts.\n"
        f"Resume excerpt:\n{text[:3000]}"
    )
    return llm_service.chat_json(prompt, system=system)
