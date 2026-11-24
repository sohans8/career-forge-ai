import pytest

from backend.app.services.llm_service import parse_json_object, LLMError
from backend.app.services.rag_service import chunk_text


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(k, "")


def test_quiz_definition(client):
    q = client.get("/api/guidance/quiz").json()
    assert {"stages", "streams", "interests", "strengths"} <= q.keys()


def test_recommend_diploma_student(client):
    r = client.post("/api/guidance/recommend", json={
        "stage": "after_diploma", "stream": "dip_cs", "interests": ["I", "R", "C"],
        "strengths": ["programming", "problem_solving"], "career_goal": "full stack developer", "name": "Asha"})
    assert r.status_code == 200
    b = r.json()
    assert len(b["top_careers"]) == 6
    assert b["suggested_resume_role"] == "Full Stack Developer"
    assert b["recommended_roadmap"]["primary_node"]
    assert b["next_actions"]
    assert b["top_careers"][0]["match"] >= b["top_careers"][-1]["match"]


@pytest.mark.parametrize("stage,stream,interests,strengths,goal", [
    ("after_10th", "science_pcm", ["R", "I", "A"], ["programming", "problem_solving"], "mechanical engineer"),
    ("after_12th", "science_pcm", ["R", "I"], ["programming"], "civil engineer"),
    ("after_diploma", "dip_mech", ["R", "C", "I"], ["problem_solving"], "automotive engineering technician"),
])
def test_match_percent_stays_within_0_and_100(client, stage, stream, interests, strengths, goal):
    b = client.post("/api/guidance/recommend", json={"stage": stage, "stream": stream, "interests": interests,
                                                     "strengths": strengths, "career_goal": goal}).json()
    assert all(0 <= c["match"] <= 100 for c in b["top_careers"]), [c["match"] for c in b["top_careers"]]


def test_onet_riasec_values_are_normalised():
    from backend.app.services.guidance_service import guidance_service
    values = [v for c in guidance_service.careers() for v in c["riasec"].values()]
    assert values and 0.0 <= min(values) and max(values) <= 1.0


def test_recommend_validates_input(client):
    assert client.post("/api/guidance/recommend", json={"stage": "bad"}).status_code == 422
    r = client.post("/api/guidance/recommend", json={"stage": "after_10th"})
    assert r.status_code == 200


def test_mentor_offline_uses_rag_and_node(client):
    r = client.post("/api/mentor/chat", json={
        "message": "How does DSE admission work?", "node_id": "ad_dse",
        "profile": {"stage": "after_diploma", "stream": "dip_cs", "target_goal": "B.Tech CSE"}})
    assert r.status_code == 200
    b = r.json()
    assert b["llm_used"] is False
    assert "Direct Second Year" in b["reply"] and "official" in b["reply"].lower()
    assert any(s.startswith("02_") for s in b["sources"])


def test_mentor_validation(client):
    assert client.post("/api/mentor/chat", json={"message": ""}).status_code == 422
    assert client.get("/api/mentor/prompts", params={"stage": "after_diploma"}).json()["prompts"]


def test_mentor_uses_llm_when_configured(client, monkeypatch):
    from backend.app.services import llm_service as mod
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    seen = {}

    def fake(self, messages, system="", json_mode=False, temperature=0.4):
        seen["system"] = system
        return "Mock answer"

    monkeypatch.setattr(mod.LLMService, "chat", fake)
    b = client.post("/api/mentor/chat", json={"message": "Compare Diploma CS vs 11th Science",
                                              "profile": {"stage": "after_10th", "stream": "diploma"}}).json()
    assert b["llm_used"] is True and b["reply"] == "Mock answer" and b["provider"] == "groq"
    assert "Class 10 student" in seen["system"] and "official portal" in seen["system"]


def _http_error(status, message):
    import httpx
    req = httpx.Request("POST", "https://example.test")
    resp = httpx.Response(status, json={"error": {"message": message}}, request=req)
    return httpx.HTTPStatusError("boom", request=req, response=resp)


def test_llm_falls_back_to_next_provider(monkeypatch):
    from backend.app.services import llm_service as mod
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFAKEKEY1234567890")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake")
    svc = mod.LLMService()

    def bad_gemini(*a, **k):
        raise _http_error(400, "API key not valid AIzaFAKEKEY1234567890")

    monkeypatch.setattr(svc, "_gemini", bad_gemini)
    monkeypatch.setattr(svc, "_openai_compatible", lambda provider, *a, **k: f"answer from {provider}")
    assert svc.candidates() == ["gemini", "groq"]
    assert svc.chat([mod.Message("user", "hi")]) == "answer from groq"
    assert svc.used_provider == "groq"
    assert "gemini: HTTP 400" in svc.last_error and "AIza" not in svc.last_error  # key never leaks


def test_llm_all_providers_fail_gives_offline_answer(client, monkeypatch):
    from backend.app.services import llm_service as mod
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFAKE")

    def bad(*a, **k):
        raise _http_error(404, "model not found")

    monkeypatch.setattr(mod.LLMService, "_gemini", bad)
    monkeypatch.setattr(mod.LLMService, "_discover_model", lambda self, provider, exclude="": None)
    b = client.post("/api/mentor/chat", json={"message": "What is DSE?", "node_id": "ad_dse"}).json()
    assert b["llm_used"] is False and "did not respond" in b["reply"] and "no LLM API key" not in b["reply"]
    assert "gemini: HTTP 404" in client.get("/api/status").json()["llm"]["last_error"]


def test_retired_model_is_replaced_automatically(monkeypatch):
    from backend.app.services import llm_service as mod
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFAKE")
    svc = mod.LLMService()
    calls = []

    def send(provider, model, *a):
        calls.append(model)
        if model == "gemini-2.0-flash":
            raise _http_error(404, "This model models/gemini-2.0-flash is no longer available.")
        return f"answer from {model}"

    monkeypatch.setattr(svc, "_send", send)
    monkeypatch.setattr(svc, "_discover_model", lambda provider, exclude="": "gemini-9.9-flash")
    assert svc.chat([mod.Message("user", "hi")]) == "answer from gemini-9.9-flash"
    assert svc.model_name() == "gemini-9.9-flash" and svc.last_error is None
    svc.chat([mod.Message("user", "again")])
    assert calls == ["gemini-2.0-flash", "gemini-9.9-flash", "gemini-9.9-flash"]  # remembered, no second failure


def test_pick_model_prefers_current_general_chat_models():
    from backend.app.services.llm_service import pick_model
    gemini = ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.8-flash-lite", "gemini-3.8-pro", "text-embedding-004",
              "gemini-3.9-flash-preview", "gemini-2.5-flash-image"]
    assert pick_model("gemini", gemini) == "gemini-3.8-flash"
    assert pick_model("gemini", gemini + ["gemini-flash-latest"]) == "gemini-flash-latest"
    groq = ["whisper-large-v3", "llama-guard-4-12b", "llama-4.1-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b"]
    assert pick_model("groq", groq) == "llama-4.1-70b-versatile"
    assert pick_model("groq", ["whisper-large-v3", "openai/gpt-oss-120b"]) == "openai/gpt-oss-120b"
    assert pick_model("openai", ["gpt-4o", "gpt-5-mini", "gpt-4o-mini", "text-embedding-3-small"]) == "gpt-5-mini"


def test_status_and_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    s = client.get("/api/status").json()
    assert s["roadmap_nodes"] > 20 and s["colleges"] > 1000 and s["rag"]["chunks"] > 0
    assert s["llm"]["configured"] is False


def test_parse_json_object_variants():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Here: {"a": 2} done') == {"a": 2}
    with pytest.raises(LLMError):
        parse_json_object("no json")


def test_chunking_overlaps():
    words = " ".join(f"w{i}" for i in range(400))
    chunks = chunk_text(words)
    assert len(chunks) >= 2 and chunks[0].split()[-1] in chunks[1]
