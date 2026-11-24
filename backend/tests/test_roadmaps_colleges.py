import pytest


@pytest.mark.parametrize("stage", ["after_10th", "after_12th", "after_diploma"])
def test_each_stage_returns_graph(client, stage):
    r = client.get("/api/roadmaps", params={"stage": stage})
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"] and body["edges"]
    ids = {n["id"] for n in body["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in body["edges"])


def test_after_10th_includes_diploma_branches(client):
    ids = {n["id"] for n in client.get("/api/roadmaps", params={"stage": "after_10th"}).json()["nodes"]}
    assert {"a10_dip_cs", "a10_dip_aiml", "a10_dip_mech", "a10_dip_civil", "a10_iti", "a10_sci_pcm"} <= ids


def test_stream_filter_narrows_results(client):
    all_ids = {n["id"] for n in client.get("/api/roadmaps", params={"stage": "after_10th"}).json()["nodes"]}
    pcb = client.get("/api/roadmaps", params={"stage": "after_10th", "stream": "pcb"}).json()
    pcb_ids = {n["id"] for n in pcb["nodes"] if not n.get("external")}
    assert "a10_sci_pcb" in pcb_ids and "a10_dip_cs" not in pcb_ids
    assert len(pcb_ids) < len(all_ids)


def test_diploma_branch_stream_keeps_dse_and_relevant_jobs(client):
    ids = {n["id"] for n in client.get("/api/roadmaps", params={"stage": "after_diploma", "stream": "dip_cs"}).json()["nodes"]}
    assert {"ad_start", "ad_dse", "ad_rrb_je", "ad_industry"} <= ids
    assert "ad_ssc_je" not in ids and "ad_state_je" not in ids  # civil/mech/elec only
    first = {n["id"] for n in client.get("/api/roadmaps", params={"stage": "after_10th", "stream": "dip_cs"}).json()["nodes"] if not n.get("external")}
    assert "a10_dip_cs" in first and "a10_dip_mech" not in first


def test_nodes_have_required_fields(client):
    required = {"id", "stage", "title", "duration", "eligibility", "entrance_exams", "top_branches_or_roles",
                "next_nodes", "avg_salary_range", "last_updated"}
    for stage in ("after_10th", "after_12th", "after_diploma"):
        for n in client.get("/api/roadmaps", params={"stage": stage}).json()["nodes"]:
            assert required <= n.keys()


def test_invalid_stage_is_rejected(client):
    assert client.get("/api/roadmaps", params={"stage": "nonsense"}).status_code == 422


def test_node_lookup_and_404(client):
    assert client.get("/api/roadmaps/nodes/ad_dse").json()["stage"] == "after_diploma"
    assert client.get("/api/roadmaps/nodes/nope").status_code == 404


def test_colleges_filter_by_state_and_type(client):
    r = client.get("/api/colleges", params={"state": "Maharashtra", "type": "diploma", "limit": 5})
    body = r.json()
    assert r.status_code == 200 and body["total"] > 0
    assert all(c["state"] == "Maharashtra" and "diploma" in c["kinds"] for c in body["results"])


def test_colleges_branch_filter_and_paging(client):
    a = client.get("/api/colleges", params={"type": "engineering", "branch": "computer", "limit": 3}).json()
    b = client.get("/api/colleges", params={"type": "engineering", "branch": "computer", "limit": 3, "offset": 3}).json()
    assert len(a["results"]) == 3 and a["results"] != b["results"]


def test_every_node_with_college_type_finds_colleges(client):
    """The roadmap drawer queries colleges the same way; an empty or mismatched list is a data bug."""
    for stage in ("after_10th", "after_12th", "after_diploma"):
        for n in client.get("/api/roadmaps", params={"stage": stage}).json()["nodes"]:
            if not n.get("college_type") or n.get("external"):
                continue
            params = {"type": n["college_type"], "limit": 1}
            if n["college_type"] == "diploma" and n["branch_keywords"]:
                params["branch"] = n["branch_keywords"][0]
            assert client.get("/api/colleges", params=params).json()["total"] > 0, n["id"]


def test_colleges_invalid_type(client):
    assert client.get("/api/colleges", params={"type": "xyz"}).status_code == 422


def test_states_list(client):
    assert "Maharashtra" in client.get("/api/colleges/states").json()["states"]
