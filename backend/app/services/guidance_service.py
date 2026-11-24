"""Onboarding quiz scoring and personalised dashboard payload."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend.app.config import DATA_DIR
from backend.app.services.resume_service import skill_bank
from backend.app.services.roadmap_service import normalize_stream, roadmap_service

ONET_FILE = DATA_DIR / "onet_skills.json"

QUIZ = {
    "stages": [
        {"id": "after_10th", "label": "I have passed (or am in) Class 10"},
        {"id": "after_12th", "label": "I have passed (or am in) Class 12"},
        {"id": "after_diploma", "label": "I have a Diploma / am in Diploma"},
    ],
    "streams": {
        "after_10th": [
            {"id": "science_pcm", "label": "Science (PCM)"}, {"id": "science_pcb", "label": "Science (PCB)"},
            {"id": "commerce", "label": "Commerce"}, {"id": "arts", "label": "Arts"},
            {"id": "diploma", "label": "Diploma / Polytechnic"}, {"id": "iti", "label": "ITI"},
            {"id": "vocational", "label": "Vocational / Skills"},
        ],
        "after_12th": [
            {"id": "science_pcm", "label": "Science (PCM)"}, {"id": "science_pcb", "label": "Science (PCB)"},
            {"id": "commerce", "label": "Commerce"}, {"id": "arts", "label": "Arts"},
        ],
        "after_diploma": [
            {"id": "dip_cs", "label": "Computer Engg."}, {"id": "dip_it", "label": "Information Technology"},
            {"id": "dip_aiml", "label": "AI & ML / Data Science"}, {"id": "dip_mech", "label": "Mechanical"},
            {"id": "dip_civil", "label": "Civil"}, {"id": "dip_ece", "label": "Electronics & Telecom"},
            {"id": "dip_elec", "label": "Electrical"},
        ],
    },
    "interests": [
        {"id": "R", "label": "Hands-on", "hint": "Build, repair, operate machines or tools"},
        {"id": "I", "label": "Investigative", "hint": "Analyse, research, solve puzzles"},
        {"id": "A", "label": "Creative", "hint": "Design, write, create new things"},
        {"id": "S", "label": "Social", "hint": "Teach, help and care for people"},
        {"id": "E", "label": "Enterprising", "hint": "Lead, persuade, start ventures"},
        {"id": "C", "label": "Organised", "hint": "Work with data, records and processes"},
    ],
    "strengths": [
        {"id": "maths", "label": "Maths", "onet": ["Mathematics"]},
        {"id": "programming", "label": "Programming", "onet": ["Programming", "Systems Analysis"]},
        {"id": "problem_solving", "label": "Problem solving", "onet": ["Complex Problem Solving", "Critical Thinking"]},
        {"id": "communication", "label": "Communication", "onet": ["Speaking", "Active Listening", "Writing"]},
        {"id": "creativity", "label": "Creativity", "onet": ["Active Learning", "Critical Thinking"]},
        {"id": "leadership", "label": "Leadership", "onet": ["Coordination", "Persuasion", "Negotiation"]},
        {"id": "science", "label": "Science / Biology", "onet": ["Science"]},
        {"id": "design", "label": "Drawing & Design", "onet": ["Operations Analysis", "Critical Thinking"]},
        {"id": "hands_on", "label": "Hands-on building", "onet": ["Repairing", "Troubleshooting", "Equipment Maintenance"]},
        {"id": "numbers", "label": "Numbers & accounting", "onet": ["Mathematics", "Reading Comprehension"]},
        {"id": "teamwork", "label": "Teamwork", "onet": ["Social Perceptiveness", "Coordination"]},
    ],
}

NEXT_ACTIONS = {
    "after_10th": [
        "Compare 11th-12th Science, Commerce and a 3-year Diploma on the roadmap page.",
        "Check which polytechnics near you offer your preferred diploma branch.",
        "Ask the AI Mentor how the Class 10 merit-based CAP admission works in your state.",
    ],
    "after_12th": [
        "List the entrance exams for your stream and note their registration windows on the official portal.",
        "Shortlist 5 colleges for your target branch using the college finder.",
        "Start a mock-test routine for the entrance exam and track your scores weekly.",
    ],
    "after_diploma": [
        "Compare Direct Second Year (DSE) engineering with SSC JE / RRB JE for your branch.",
        "Build 2 projects from your diploma branch and add them to your resume.",
        "Run the Resume Studio against your target role and complete the learning checklist.",
    ],
}

ROLE_KEYWORDS = [
    (r"full.?stack|web|frontend|front-end|backend", "Full Stack Developer"),
    (r"\bai\b|machine learning|\bml\b|deep learning|robotic", "AI/ML Engineer"),
    (r"data scien", "Data Scientist"), (r"data analy|analytics|business analy", "Data Analyst"),
    (r"software|developer|programmer|computer|\bit\b|cyber", "Software Developer"),
    (r"mechanical|automobile|manufactur", "Mechanical Engineer"), (r"civil|construction|architect", "Civil Engineer"),
    (r"electrical|power", "Electrical Engineer"), (r"electronic|embedded|telecom|iot", "Electronics Engineer"),
    (r"account|finance|\bca\b|bank|audit|tax", "Finance / Accounting"),
]
STREAM_DEFAULT_ROLE = {"dip_cs": "Software Developer", "dip_it": "Software Developer", "dip_aiml": "AI/ML Engineer",
                       "dip_mech": "Mechanical Engineer", "dip_civil": "Civil Engineer", "dip_ece": "Electronics Engineer",
                       "dip_elec": "Electrical Engineer", "science_pcm": "Software Developer", "commerce": "Finance / Accounting"}


# O*NET-SOC major groups that fit each stream: 15 computing, 17 engineering, 19 science, 29 health,
# 13 business/finance, 11 management, 23 legal, 25 education, 27 arts/media, 49/51 installation & production.
_TECH = ("15-", "17-")
STREAM_SOC_FIT = {
    "science_pcm": _TECH + ("19-",), "science_pcb": ("29-", "19-", "31-"), "commerce": ("13-", "11-", "43-"),
    "arts": ("27-", "23-", "25-", "21-"), "diploma": _TECH + ("49-", "51-"), "iti": ("49-", "51-", "47-"),
    "vocational": ("49-", "51-", "41-", "39-"),
    "dip_cs": ("15-",), "dip_it": ("15-",), "dip_aiml": ("15-",), "dip_mech": ("17-", "49-", "51-"),
    "dip_civil": ("17-", "47-"), "dip_ece": ("17-", "15-", "49-"), "dip_elec": ("17-", "49-"),
}


class GuidanceService:
    def __init__(self, path: Path = ONET_FILE):
        self.path = path
        self._mtime = 0.0
        self._careers: list[dict] = []

    def careers(self) -> list[dict]:
        mtime = self.path.stat().st_mtime if self.path.exists() else 0.0
        if mtime != self._mtime:
            self._careers = json.loads(self.path.read_text(encoding="utf-8")).get("careers", []) if self.path.exists() else []
            self._mtime = mtime
        return self._careers

    @staticmethod
    def quiz() -> dict:
        return QUIZ

    def map_role(self, goal: str, stream: str | None, career_titles: list[str]) -> str | None:
        hay = f"{goal} {' '.join(career_titles[:2])}".lower()
        for pat, role in ROLE_KEYWORDS:
            if re.search(pat, hay):
                return role if skill_bank.resolve_role(role) else None
        return STREAM_DEFAULT_ROLE.get(stream or "")

    def recommend(self, stage: str, stream: str | None, interests: list[str], strengths: list[str], goal: str = "",
                  name: str = "") -> dict:
        stream_key = normalize_stream(stream)
        letters = [i.upper() for i in interests if i.upper() in "RIASEC"][:3]
        weights = {l: w for l, w in zip(letters, (1.0, 0.8, 0.6))}
        strength_defs = {s["id"]: s for s in QUIZ["strengths"]}
        wanted_skills = {sk.lower() for sid in strengths if sid in strength_defs for sk in strength_defs[sid]["onet"]}
        goal_tokens = {t for t in re.findall(r"[a-z]{3,}", goal.lower())}

        fit_prefixes = STREAM_SOC_FIT.get(stream_key or "", ("__none__",))
        scored = []
        for c in self.careers():
            r = c["riasec"]
            riasec = sum(r.get(l, 0) * w for l, w in weights.items()) / (sum(weights.values()) or 1) if weights else 0.5
            have = {s.lower() for s in c["skills"]}
            strength = len(wanted_skills & have) / len(wanted_skills) if wanted_skills else 0
            title_l = c["title"].lower()
            goal_hit = 1.0 if goal_tokens and any(t in title_l for t in goal_tokens) else 0.0
            fit = 1.0 if c["soc"].startswith(fit_prefixes) else 0.0
            scored.append((0.45 * riasec + 0.2 * strength + 0.2 * goal_hit + 0.15 * fit, c, riasec, strength))
        scored.sort(key=lambda x: -x[0])
        top = scored[:6]

        gap_counter: dict[str, int] = {}
        for _, c, _, _ in top[:5]:
            for sk in c["skills"] + c["hot_technologies"][:3]:
                if sk.lower() not in wanted_skills:
                    gap_counter[sk] = gap_counter.get(sk, 0) + 1
        gaps = [k for k, _ in sorted(gap_counter.items(), key=lambda kv: -kv[1])][:6]

        titles = [c["title"] for _, c, _, _ in top]
        role = self.map_role(goal, stream_key, titles)
        role_skills = [s for s, _ in skill_bank.skills_for(role, 8)] if role else []

        graph = roadmap_service.graph(stage, stream_key) if stage in ("after_10th", "after_12th", "after_diploma") else {"nodes": []}
        candidates = [n for n in graph["nodes"] if n["kind"] != "root" and not n.get("external")]
        if goal_tokens:
            def goal_hits(n: dict) -> int:
                text = (n["title"] + " " + " ".join(n["top_branches_or_roles"])).lower()
                hits = sum(1 for t in goal_tokens if t in text)
                return hits if hits >= 2 else 0  # one shared word is too weak to reorder the path

            candidates.sort(key=lambda n: -goal_hits(n))  # stable: ties keep graph order
        path = [{"id": n["id"], "title": n["title"], "duration": n["duration"], "entrance_exams": n["entrance_exams"][:4]} for n in candidates[:3]]

        return {
            "profile": {"name": name, "stage": stage, "stream": stream_key, "interests": letters, "strengths": strengths, "career_goal": goal},
            "recommended_roadmap": {"stage": stage, "stream": stream_key, "primary_node": path[0]["id"] if path else None, "paths": path},
            "top_careers": [{"title": c["title"], "soc": c["soc"], "riasec_code": c["code"], "match": round(s * 100),
                             "skills": c["skills"][:5], "hot_technologies": c["hot_technologies"][:4]} for s, c, _, _ in top],
            "skill_gap_summary": {"target_resume_role": role, "skills_to_build": (role_skills + gaps)[:8], "role_skills": role_skills},
            "next_actions": NEXT_ACTIONS.get(stage, []),
            "suggested_resume_role": role,
        }


guidance_service = GuidanceService()
