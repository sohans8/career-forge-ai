"""Roadmap knowledge graph access and filtering."""
from __future__ import annotations

import json
from pathlib import Path

from backend.app.config import DATA_DIR

ROADMAP_FILE = DATA_DIR / "roadmaps_india.json"
VALID_STAGES = ("after_10th", "after_12th", "after_diploma")

STREAM_ALIASES = {
    "pcm": "science_pcm", "science": "science_pcm", "science_pcm": "science_pcm", "engineering": "science_pcm",
    "pcb": "science_pcb", "science_pcb": "science_pcb", "medical": "science_pcb",
    "commerce": "commerce", "arts": "arts", "humanities": "arts",
    "diploma": "diploma", "polytechnic": "diploma", "iti": "iti", "vocational": "vocational",
    "diploma_cs": "dip_cs", "diploma_it": "dip_it", "diploma_aiml": "dip_aiml", "diploma_mech": "dip_mech",
    "diploma_civil": "dip_civil", "diploma_ece": "dip_ece", "diploma_elec": "dip_elec", "diploma_electrical": "dip_elec",
    "diploma_pharm": "dip_pharm",
}


def normalize_stream(stream: str | None) -> str | None:
    if not stream:
        return None
    key = stream.strip().lower().replace("-", "_").replace(" ", "_")
    return STREAM_ALIASES.get(key, key)


def _tags_match(tags: list[str], stream_key: str) -> bool:
    """A node matches a stream when it is tagged for it or for everyone.

    A specific diploma branch (dip_cs) also matches generic diploma nodes, but
    not nodes tagged only for other diploma branches.
    """
    if "all" in tags or stream_key in tags:
        return True
    if stream_key.startswith("dip_"):
        other_branch = any(t.startswith("dip_") for t in tags)
        return "diploma" in tags and not other_branch
    return False


class RoadmapService:
    def __init__(self, path: Path = ROADMAP_FILE):
        self.path = path
        self._mtime = 0.0
        self._data: dict = {"nodes": [], "stages": {}}

    def _load(self) -> dict:
        mtime = self.path.stat().st_mtime if self.path.exists() else 0.0
        if mtime != self._mtime:  # hot-reload when the watcher applies a patch
            self._data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"nodes": [], "stages": {}}
            self._mtime = mtime
        return self._data

    @property
    def nodes(self) -> list[dict]:
        return self._load()["nodes"]

    def meta(self) -> dict:
        d = self._load()
        return {k: d.get(k) for k in ("schema_version", "last_updated", "disclaimer", "stages")}

    def get_node(self, node_id: str) -> dict | None:
        return next((n for n in self.nodes if n["id"] == node_id), None)

    def graph(self, stage: str, stream: str | None = None) -> dict:
        """Nodes and edges for one stage, optionally narrowed to a stream.

        Targets that live in another stage are returned as `external` stub nodes
        so the UI can show where a path continues.
        """
        if stage not in VALID_STAGES:
            raise ValueError(f"stage must be one of {', '.join(VALID_STAGES)}")
        stream_key = normalize_stream(stream)
        by_id = {n["id"]: n for n in self.nodes}
        in_stage = [n for n in self.nodes if n["stage"] == stage]

        def keep(node: dict) -> bool:
            if node["kind"] == "root" or not stream_key:
                return True
            return _tags_match(node["streams"], stream_key)

        kept = [n for n in in_stage if keep(n)]
        kept_ids = {n["id"] for n in kept}
        edges, external = [], {}
        for n in kept:
            for target in n["next_nodes"]:
                t = by_id.get(target)
                if not t:
                    continue
                if target in kept_ids:
                    edges.append({"id": f"{n['id']}->{target}", "source": n["id"], "target": target})
                elif t["stage"] != stage and (not stream_key or _tags_match(t["streams"], stream_key) or n["kind"] == "path"):
                    external[target] = {**t, "external": True}
                    edges.append({"id": f"{n['id']}->{target}", "source": n["id"], "target": target, "external": True})
        return {
            "stage": stage,
            "stream": stream_key,
            "root": self._load()["stages"].get(stage, {}).get("root"),
            "nodes": kept + list(external.values()),
            "edges": edges,
            "last_updated": self._load().get("last_updated"),
        }


roadmap_service = RoadmapService()
