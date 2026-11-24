import copy
import json

import pytest

from backend.scripts import update_education_data as w
from backend.scripts.validate_data import DATA, main as validate_main, validate_roadmap


@pytest.fixture()
def doc():
    return json.loads((DATA / "roadmaps_india.json").read_text(encoding="utf-8"))


def test_all_datasets_validate():
    assert validate_main() == 0


def test_validator_catches_broken_graph(doc):
    bad = copy.deepcopy(doc)
    bad["nodes"][1]["next_nodes"].append("ghost_node")
    assert any("ghost_node" in e for e in validate_roadmap(bad))
    bad2 = copy.deepcopy(doc)
    del bad2["nodes"][2]["duration"]
    assert validate_roadmap(bad2)


def test_domain_allow_list():
    assert w.host_allowed("https://nta.ac.in/notice.pdf")
    assert w.host_allowed("https://cetcell.mahacet.org/x")
    assert not w.host_allowed("http://nta.ac.in/x")  # http refused
    assert not w.host_allowed("https://evil-nta.ac.in.attacker.com/x")
    assert not w.host_allowed("https://example.com/a.pdf")


def test_patch_validation_filters_unsafe_patches(doc):
    patches = [
        {"op": "update", "node_id": "ad_dse", "fields": {"eligibility": "Diploma with 50% marks"}, "confidence": 0.9, "evidence": "x"},
        {"op": "update", "node_id": "ad_dse", "fields": {"id": "hacked"}},            # forbidden field
        {"op": "update", "node_id": "missing", "fields": {"title": "Nope nope"}},      # unknown node
        {"op": "update", "node_id": "ad_dse", "fields": {"next_nodes": ["ghost"]}},    # breaks graph
        {"op": "delete", "node_id": "ad_dse", "fields": {}},                           # unsupported op
        "garbage",
    ]
    good = w.validate_patches(patches, doc)
    assert len(good) == 1 and good[0]["fields"]["eligibility"].startswith("Diploma")


def test_apply_requires_approval_and_updates_graph(tmp_path, monkeypatch, doc):
    roadmap = tmp_path / "roadmaps_india.json"
    roadmap.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(w, "ROADMAP", roadmap)
    patch_file = tmp_path / "p.json"
    record = {"status": "pending", "patches": [{"op": "update", "node_id": "ad_dse", "fields": {"duration": "3 years (updated)"}}]}
    patch_file.write_text(json.dumps(record), encoding="utf-8")
    assert w.apply_staged(patch_file) == 1  # pending: refused
    record["status"] = "approved"
    patch_file.write_text(json.dumps(record), encoding="utf-8")
    assert w.apply_staged(patch_file) == 0
    updated = json.loads(roadmap.read_text(encoding="utf-8"))
    assert next(n for n in updated["nodes"] if n["id"] == "ad_dse")["duration"] == "3 years (updated)"
    assert json.loads(patch_file.read_text())["status"] == "applied"


def test_extract_patches_with_fake_llm(doc):
    class FakeLLM:
        def chat_json(self, prompt, system=""):
            assert "untrusted" in prompt
            return {"patches": [{"op": "update", "node_id": "a10_iti", "fields": {"duration": "1-2 years"}, "confidence": 0.8}]}

    out = w.extract_patches({"source": "t", "text": "ITI duration revised"}, doc, FakeLLM())
    assert out[0]["node_id"] == "a10_iti"


def test_pdf_link_extraction_respects_allow_list():
    html = '<a href="/n/a.pdf">Notice A</a><a href="https://evil.com/b.pdf">B</a><a href="/page">C</a>'
    links = w.extract_pdf_links(html, "https://nta.ac.in/")
    assert links == [("Notice A", "https://nta.ac.in/n/a.pdf")]
