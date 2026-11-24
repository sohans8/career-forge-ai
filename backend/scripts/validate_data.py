"""Validate the knowledge-base files. Exit code 1 on any problem (used by CI).

Usage: python -m backend.scripts.validate_data
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def validate_roadmap(doc: dict) -> list[str]:
    """Return a list of problems (empty when valid). Checks JSON schema and graph integrity."""
    import jsonschema

    schema = json.loads((DATA / "schemas" / "roadmaps.schema.json").read_text(encoding="utf-8"))
    errors = [f"schema: {e.message} at {'/'.join(map(str, e.path))}" for e in jsonschema.Draft7Validator(schema).iter_errors(doc)]
    if errors:
        return errors[:20]
    ids = [n["id"] for n in doc["nodes"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"duplicate node ids: {sorted(dupes)}")
    known = set(ids)
    for n in doc["nodes"]:
        errors += [f"{n['id']}: next_node '{t}' does not exist" for t in n["next_nodes"] if t not in known]
    for stage, meta in doc["stages"].items():
        root = next((n for n in doc["nodes"] if n["id"] == meta["root"]), None)
        if not root or root["stage"] != stage:
            errors.append(f"stage {stage}: root '{meta['root']}' missing or in wrong stage")
    return errors


def main() -> int:
    problems: list[str] = []
    rm = DATA / "roadmaps_india.json"
    if not rm.exists():
        problems.append("roadmaps_india.json missing")
    else:
        problems += [f"roadmaps_india.json: {p}" for p in validate_roadmap(json.loads(rm.read_text(encoding="utf-8")))]

    col = DATA / "aicte_colleges.json"
    if not col.exists():
        problems.append("aicte_colleges.json missing")
    else:
        rows = json.loads(col.read_text(encoding="utf-8")).get("colleges", [])
        if not rows or not all({"name", "state", "kinds"} <= r.keys() for r in rows[:500]):
            problems.append("aicte_colleges.json: empty or malformed")

    on = DATA / "onet_skills.json"
    if not on.exists():
        problems.append("onet_skills.json missing")
    else:
        careers = json.loads(on.read_text(encoding="utf-8")).get("careers", [])
        if not careers or not all("riasec" in c and "title" in c for c in careers[:500]):
            problems.append("onet_skills.json: empty or malformed")

    sk = DATA / "job_skills_ats.csv"
    if not sk.exists():
        problems.append("job_skills_ats.csv missing")
    else:
        with sk.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if not rows or set(rows[0]) != {"role", "skill", "weight", "source"}:
            problems.append("job_skills_ats.csv: empty or wrong header")

    if problems:
        print("VALIDATION FAILED")
        for p in problems:
            print(" -", p)
        return 1
    print("All datasets valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
