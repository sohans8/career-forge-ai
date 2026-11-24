"""Dataset audit and ingestion for Career Forge AI.

Builds the five datasets the platform needs inside backend/data/. Each step
uses local source files when present, then a remote source, then a built-in
seed so the app always runs out of the box.

  1. roadmaps_india.json   seeded graph (seed_roadmaps.py)
  2. aicte_colleges.json   institutions-with-programmes.json -> API -> seed
  3. onet_skills.json      O*NET CSV files -> seed
  4. job_skills_ats.csv    all_job_post.csv -> Hugging Face -> seed
  5. rag_policies/         policy PDFs/notes (indexed by rag_service)

Usage:
    python -m backend.scripts.fetch_datasets            # fill what is missing
    python -m backend.scripts.fetch_datasets --force    # rebuild everything
    python -m backend.scripts.fetch_datasets --audit    # report only
"""
from __future__ import annotations

import ast
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
COLLEGES_API = "https://indian-colleges-list.vercel.app/api/institutions"
HF_ROWS_API = "https://datasets-server.huggingface.co/rows"

RIASEC = {"R": "Realistic", "I": "Investigative", "A": "Artistic", "S": "Social", "E": "Enterprising", "C": "Conventional"}


def _log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ colleges
def _classify(prog: dict) -> str | None:
    p, lvl = (prog.get("programme") or "").upper(), (prog.get("level") or "").upper()
    if "ENGINEERING" in p or "TECHNOLOGY" in p:
        if lvl == "DIPLOMA":
            return "diploma"
        if lvl in ("UNDER GRADUATE", "UG", "INTEGRATED", "DUALDEGREE"):
            return "engineering"
    if "PHARMACY" in p and lvl in ("DIPLOMA", "UNDER GRADUATE"):
        return "pharmacy"
    if "MANAGEMENT" in p and lvl in ("POST GRADUATE", "POST GRADUATE DIPLOMA"):
        return "management"
    return None


def _compact_institution(inst: dict) -> dict | None:
    kinds, branches, intake = set(), defaultdict(set), 0
    for prog in inst.get("programmes", []) or []:
        k = _classify(prog)
        if not k:
            continue
        kinds.add(k)
        course = (prog.get("course") or "").strip().title()
        if course:
            branches[k].add(course)
        try:
            intake += int(prog.get("intake") or 0)
        except ValueError:
            pass
    if not kinds:
        return None
    return {
        "id": inst.get("aicte_id"),
        "name": (inst.get("institute_name") or "").title(),
        "state": inst.get("state") or "",
        "district": (inst.get("district") or "").title(),
        "ownership": inst.get("institution_type") or "",
        "university": inst.get("university") or "",
        "kinds": sorted(kinds),
        "branches": {k: sorted(v)[:25] for k, v in branches.items()},
        "intake": intake,
        "women_only": inst.get("women") == "Y",
        "minority": inst.get("minority") == "Y",
    }


SEED_COLLEGES = [
    ("Government Polytechnic Mumbai", "Maharashtra", "Mumbai", "Government", ["diploma"], {"diploma": ["Computer Engineering", "Civil Engineering", "Mechanical Engineering", "Electrical Engineering"]}),
    ("Veermata Jijabai Technological Institute", "Maharashtra", "Mumbai", "State Government University", ["engineering"], {"engineering": ["Computer Engineering", "Information Technology", "Mechanical Engineering"]}),
    ("College of Engineering Pune", "Maharashtra", "Pune", "Government", ["engineering"], {"engineering": ["Computer Engineering", "Electronics And Telecommunication", "Civil Engineering"]}),
    ("Government Polytechnic Pune", "Maharashtra", "Pune", "Government", ["diploma"], {"diploma": ["Computer Engineering", "Mechanical Engineering"]}),
    ("PSG College of Technology", "Tamil Nadu", "Coimbatore", "Govt aided", ["engineering"], {"engineering": ["Computer Science And Engineering", "Mechanical Engineering"]}),
    ("Government Polytechnic Bangalore", "Karnataka", "Bengaluru", "Government", ["diploma"], {"diploma": ["Computer Science And Engineering", "Electronics And Communication"]}),
    ("Delhi Technological University", "Delhi", "New Delhi", "State Government University", ["engineering"], {"engineering": ["Computer Engineering", "Electrical Engineering"]}),
    ("Pusa Polytechnic", "Delhi", "New Delhi", "Government", ["diploma"], {"diploma": ["Electronics And Communication", "Civil Engineering"]}),
]


def build_colleges(force: bool) -> None:
    out = DATA / "aicte_colleges.json"
    if out.exists() and not force:
        _log("[skip] aicte_colleges.json exists")
        return
    records: list[dict] = []
    src = DATA / "institutions-with-programmes.json"
    source = "local:institutions-with-programmes.json"
    if src.exists():
        for inst in json.loads(src.read_text(encoding="utf-8")):
            rec = _compact_institution(inst)
            if rec:
                records.append(rec)
    else:
        try:
            import requests  # type: ignore
            r = requests.get(COLLEGES_API, timeout=30)
            r.raise_for_status()
            payload = r.json()
            payload = payload.get("data", payload) if isinstance(payload, dict) else payload
            for inst in payload:
                rec = _compact_institution(inst)
                if rec:
                    records.append(rec)
            source = COLLEGES_API
        except Exception as exc:  # network or schema failure
            _log(f"[warn] colleges API unavailable ({exc}); using seed subset")
            source = "seed"
            for i, (name, state, dist, own, kinds, br) in enumerate(SEED_COLLEGES):
                records.append({"id": f"seed-{i}", "name": name, "state": state, "district": dist, "ownership": own,
                                "university": "", "kinds": kinds, "branches": br, "intake": 0,
                                "women_only": False, "minority": False})
    payload = {"source": source, "generated": date.today().isoformat(), "count": len(records), "colleges": records}
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    _log(f"[ok] aicte_colleges.json: {len(records)} institutions from {source}")


# --------------------------------------------------------------------- O*NET
SEED_ONET = [
    ("15-1252.00", "Software Developers", "IRC", ["Programming", "Critical Thinking", "Complex Problem Solving", "Systems Analysis"], ["Python", "JavaScript", "Git", "SQL"]),
    ("15-2051.00", "Data Scientists", "IRC", ["Mathematics", "Programming", "Critical Thinking", "Statistics"], ["Python", "SQL", "Tableau", "TensorFlow"]),
    ("15-1299.08", "Computer Systems Engineers/Architects", "IRC", ["Systems Analysis", "Programming", "Troubleshooting"], ["Linux", "AWS", "Docker"]),
    ("17-2141.00", "Mechanical Engineers", "RIC", ["Mathematics", "Science", "Critical Thinking", "Design"], ["AutoCAD", "SolidWorks", "MATLAB"]),
    ("17-2051.00", "Civil Engineers", "RIE", ["Mathematics", "Active Listening", "Critical Thinking"], ["AutoCAD", "STAAD.Pro", "Revit"]),
    ("17-2071.00", "Electrical Engineers", "IRC", ["Mathematics", "Science", "Troubleshooting"], ["MATLAB", "AutoCAD", "PLC"]),
    ("29-1216.00", "General Internal Medicine Physicians", "ISE", ["Science", "Active Listening", "Social Perceptiveness"], []),
    ("13-2011.00", "Accountants and Auditors", "CEI", ["Mathematics", "Critical Thinking", "Reading Comprehension"], ["Tally", "Excel", "SAP"]),
    ("27-1024.00", "Graphic Designers", "AER", ["Active Listening", "Critical Thinking"], ["Adobe Photoshop", "Figma"]),
    ("23-1011.00", "Lawyers", "ESA", ["Persuasion", "Reading Comprehension", "Speaking"], []),
    ("25-2031.00", "Secondary School Teachers", "SAE", ["Instructing", "Speaking", "Learning Strategies"], []),
    ("11-2021.00", "Marketing Managers", "ECA", ["Persuasion", "Negotiation", "Speaking"], ["Google Analytics", "HubSpot"]),
]


def build_onet(force: bool) -> None:
    out = DATA / "onet_skills.json"
    if out.exists() and not force:
        _log("[skip] onet_skills.json exists")
        return
    import pandas as pd

    occ_f, int_f, skl_f, sw_f = (DATA / n for n in ("occupation_data.csv", "career_interest_types.csv", "essential_skills.csv", "software_skills.csv"))
    careers: list[dict] = []
    if all(p.exists() for p in (occ_f, int_f, skl_f)):
        occ = pd.read_csv(occ_f)
        occ["Description"] = occ["Description"].fillna("").str.slice(0, 220)
        ints = pd.read_csv(int_f)
        ints = ints[ints["Scale ID"] == "OI"]
        riasec: dict[str, dict] = defaultdict(dict)
        for soc, name, val in zip(ints["O*NET-SOC Code"], ints["Element Name"], ints["Data Value"]):
            key = {v: k for k, v in RIASEC.items()}.get(name)
            if key:
                # O*NET occupational interests use a 1-7 scale; map it onto 0-1.
                riasec[soc][key] = round(min(max((float(val) - 1.0) / 6.0, 0.0), 1.0), 3)
        skills = pd.read_csv(skl_f)
        skills = skills[skills["Scale ID"] == "IM"].sort_values("Data Value", ascending=False)
        top_skills = skills.groupby("O*NET-SOC Code")["Element Name"].apply(lambda s: list(s.head(8))).to_dict()
        hot: dict[str, list] = {}
        if sw_f.exists():
            sw = pd.read_csv(sw_f, usecols=["O*NET-SOC Code", "Workplace Example", "Hot Technology"])
            sw = sw[sw["Hot Technology"] == "Y"]
            hot = sw.groupby("O*NET-SOC Code")["Workplace Example"].apply(lambda s: list(dict.fromkeys(s))[:8]).to_dict()
        for soc, title, desc in zip(occ["O*NET-SOC Code"], occ["Title"], occ["Description"]):
            vec = riasec.get(soc)
            if not vec or len(vec) < 6:
                continue
            code = "".join(k for k, _ in sorted(vec.items(), key=lambda kv: -kv[1])[:3])
            careers.append({"soc": soc, "title": title, "description": desc, "riasec": vec, "code": code,
                            "skills": top_skills.get(soc, []), "hot_technologies": hot.get(soc, [])})
        source = "O*NET (local CSV files)"
    else:
        source = "seed"
        for soc, title, code, sk, tech in SEED_ONET:
            vec = {k: (0.9 if k in code[:1] else 0.7 if k in code[1:2] else 0.5 if k in code[2:3] else 0.2) for k in RIASEC}
            careers.append({"soc": soc, "title": title, "description": "", "riasec": vec, "code": code,
                            "skills": sk, "hot_technologies": tech})
    payload = {"source": source, "generated": date.today().isoformat(), "riasec": RIASEC, "count": len(careers), "careers": careers}
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    _log(f"[ok] onet_skills.json: {len(careers)} careers from {source}")


# ----------------------------------------------------------- job skills (ATS)
SEED_ROLES: dict[str, tuple[list[str], list[str]]] = {
    "Software Developer": (["data structures", "algorithms", "git", "python", "java", "sql", "rest api", "oop", "debugging"],
                           ["docker", "unit testing", "linux", "agile", "ci/cd", "system design"]),
    "Full Stack Developer": (["html", "css", "javascript", "react", "node.js", "sql", "rest api", "git"],
                             ["typescript", "mongodb", "docker", "authentication", "deployment", "tailwind css"]),
    "AI/ML Engineer": (["python", "machine learning", "numpy", "pandas", "scikit-learn", "statistics", "deep learning"],
                       ["tensorflow", "pytorch", "nlp", "computer vision", "mlops", "docker", "sql"]),
    "Data Scientist": (["python", "sql", "statistics", "pandas", "machine learning", "data visualization", "excel"],
                       ["tableau", "power bi", "a/b testing", "feature engineering", "scikit-learn"]),
    "Data Analyst": (["sql", "excel", "data visualization", "python", "statistics", "power bi"],
                     ["tableau", "dashboards", "data cleaning", "reporting"]),
    "Mechanical Engineer": (["autocad", "solidworks", "thermodynamics", "manufacturing processes", "cad", "mechanics"],
                            ["ansys", "catia", "gd&t", "plc", "quality control", "six sigma"]),
    "Civil Engineer": (["autocad", "surveying", "structural analysis", "estimation and costing", "construction management"],
                       ["staad.pro", "revit", "primavera", "quantity surveying", "site supervision"]),
    "Electrical Engineer": (["circuit analysis", "power systems", "electrical machines", "plc", "autocad electrical"],
                            ["matlab", "scada", "control systems", "protection systems", "motor control"]),
    "Electronics Engineer": (["analog electronics", "digital electronics", "embedded systems", "microcontrollers", "pcb design"],
                             ["arduino", "raspberry pi", "c programming", "vhdl", "iot", "matlab"]),
    "Finance / Accounting": (["accounting", "excel", "financial reporting", "taxation", "gst", "tally"],
                             ["sap", "financial modelling", "auditing", "budgeting", "power bi"]),
    "Diploma Engineer (Fresher)": (["technical drawing", "workshop practice", "safety", "ms office", "communication"],
                                   ["autocad", "basic programming", "teamwork", "project work", "internship"]),
}


def build_job_skills(force: bool) -> None:
    out = DATA / "job_skills_ats.csv"
    if out.exists() and not force:
        _log("[skip] job_skills_ats.csv exists")
        return
    rows: list[tuple[str, str, float, str]] = []
    src = DATA / "all_job_post.csv"
    df = None
    if src.exists():
        import pandas as pd
        df = pd.read_csv(src)
        source = "kaggle:job-skill-set (local)"
    else:
        try:
            import requests  # type: ignore
            import pandas as pd
            data, off = [], 0
            while off < 1500:
                r = requests.get(HF_ROWS_API, params={"dataset": "batuhanmtl/job-skill-set", "config": "default",
                                                      "split": "train", "offset": off, "length": 100}, timeout=30)
                r.raise_for_status()
                batch = [x["row"] for x in r.json().get("rows", [])]
                if not batch:
                    break
                data += batch
                off += 100
            df = pd.DataFrame(data)
            source = "huggingface:batuhanmtl/job-skill-set"
        except Exception as exc:
            _log(f"[warn] Hugging Face fetch failed ({exc}); using curated seed only")
    if df is not None and {"category", "job_skill_set"} <= set(df.columns):
        for cat, grp in df.groupby("category"):
            role = str(cat).replace("-", " ").title()
            counts: Counter = Counter()
            for raw in grp["job_skill_set"].dropna():
                try:
                    items = ast.literal_eval(raw) if isinstance(raw, str) else list(raw)
                except (ValueError, SyntaxError):
                    continue
                counts.update({str(s).strip().lower() for s in items if 2 < len(str(s)) < 40})
            total = max(len(grp), 1)
            for skill, c in counts.most_common(60):
                if c >= 3:
                    rows.append((role, skill, round(c / total, 3), source))
    for role, (core, secondary) in SEED_ROLES.items():
        rows += [(role, s, 1.0, "curated") for s in core]
        rows += [(role, s, 0.6, "curated") for s in secondary]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["role", "skill", "weight", "source"])
        w.writerows(rows)
    _log(f"[ok] job_skills_ats.csv: {len(rows)} rows, {len({r[0] for r in rows})} roles")


# --------------------------------------------------------------------- audit
def audit() -> dict:
    items = {
        "roadmaps_india.json": DATA / "roadmaps_india.json",
        "aicte_colleges.json": DATA / "aicte_colleges.json",
        "onet_skills.json": DATA / "onet_skills.json",
        "job_skills_ats.csv": DATA / "job_skills_ats.csv",
        "rag_policies/": DATA / "rag_policies",
    }
    report = {}
    for name, p in items.items():
        if p.is_dir():
            report[name] = f"{len([f for f in p.iterdir() if f.is_file()])} files"
        else:
            report[name] = f"{p.stat().st_size / 1024:.0f} KB" if p.exists() else "MISSING"
    for k, v in report.items():
        _log(f"  {k:24s} {v}")
    return report


def main(argv: list[str]) -> None:
    force = "--force" in argv
    if "--audit" in argv:
        audit()
        return
    from backend.scripts import seed_roadmaps
    seed_roadmaps.main(force)
    build_colleges(force)
    build_onet(force)
    build_job_skills(force)
    _log("\nDataset audit:")
    audit()


if __name__ == "__main__":
    main(sys.argv[1:])
