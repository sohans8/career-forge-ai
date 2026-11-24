"""Context-aware AI Mentor: profile + roadmap node + RAG + unified LLM."""
from __future__ import annotations

import logging
from datetime import date

from backend.app.services.llm_service import LLMError, Message, llm_service
from backend.app.services.rag_service import rag_service
from backend.app.services.roadmap_service import roadmap_service

log = logging.getLogger("career_forge.mentor")

OFFICIAL_PORTALS = (
    "AICTE https://www.aicte-india.org, NTA https://nta.ac.in, UGC https://www.ugc.gov.in, "
    "Ministry of Education https://www.education.gov.in, Maharashtra CET Cell https://cetcell.mahacet.org, "
    "JoSAA https://josaa.nic.in, MCC https://mcc.nic.in"
)

STAGE_LABEL = {"after_10th": "Class 10 student", "after_12th": "Class 12 student", "after_diploma": "Diploma student/graduate"}

QUICK_PROMPTS = {
    "after_10th": ["Compare Diploma CS vs 11th Science", "What can I do after a polytechnic diploma?", "How does diploma admission (CAP) work?", "Is ITI a good option after 10th?"],
    "after_12th": ["JEE Main vs MHT-CET: which should I focus on?", "How do I choose between B.Tech branches?", "What are the options after 12th Commerce?", "How does NEET counselling work?"],
    "after_diploma": ["How does DSE admission work?", "SSC JE vs RRB JE: which is better for me?", "Should I do DSE or take a job first?", "What projects should a diploma holder build?"],
}


def system_prompt(profile: dict, node: dict | None, snippets: list[dict]) -> str:
    ctx = [f"Student stage: {STAGE_LABEL.get(profile.get('stage'), 'unknown')}"]
    if profile.get("stream"):
        ctx.append(f"Stream/branch: {profile['stream']}")
    if profile.get("target_goal"):
        ctx.append(f"Career goal: {profile['target_goal']}")
    if profile.get("name"):
        ctx.append(f"Name: {profile['name']}")
    node_ctx = ""
    if node:
        node_ctx = (f"\nThe student is viewing this roadmap node: {node['title']} | duration {node['duration']} | "
                    f"eligibility {node['eligibility']} | exams {', '.join(node['entrance_exams'])} | roles {', '.join(node['top_branches_or_roles'])}.")
    kb = "\n\n".join(f"[{i + 1}] ({s['source']}) {s['text']}" for i, s in enumerate(snippets)) or "(no matching documents)"
    return (
        "You are Career Forge AI Mentor, a friendly career counsellor for Indian students "
        "(after 10th, after 12th, after diploma). Give practical, honest, step-by-step advice in simple English.\n"
        f"Today's date: {date.today().isoformat()}.\n"
        "Student context:\n- " + "\n- ".join(ctx) + node_ctx + "\n\n"
        "Knowledge base excerpts (official policy notes). Prefer these over memory and cite them as [1], [2]:\n" + kb + "\n\n"
        "Rules:\n"
        "- Exam dates, cut-offs, fees, seat counts and eligibility change every year. For anything year-specific, give the general process "
        "and tell the student to confirm on the official portal. Never invent dates or numbers.\n"
        f"- Official portals: {OFFICIAL_PORTALS}.\n"
        "- If you are unsure, say so. Keep answers under 250 words unless asked for detail. Use short bullet points when comparing options."
    )


def _offline_reply(question: str, node: dict | None, snippets: list[dict], reason: str = "no_key") -> str:
    intro = {
        "no_key": "AI Mentor is running in offline mode (no LLM API key configured), so this answer comes from the local knowledge base.",
        "provider_failed": "The AI service did not respond just now, so this answer comes from the local knowledge base. Please try again in a minute.",
    }[reason]
    parts = [intro]
    if node:
        parts.append(f"**{node['title']}**: {node['duration']}. Eligibility: {node['eligibility']}. "
                     f"Entrance routes: {', '.join(node['entrance_exams']) or 'none'}. Typical roles: {', '.join(node['top_branches_or_roles'][:5])}.")
    if snippets:
        parts.append("Relevant notes:\n" + "\n".join(f"- {s['text'][:320]}... ({s['source']})" for s in snippets[:3]))
    elif not node:
        parts.append("I could not find a matching note. Try asking about diplomas, DSE, JEE/NEET/CUET, or a roadmap step.")
    parts.append(f"Always verify current-year details on the official portals: {OFFICIAL_PORTALS}.")
    return "\n\n".join(parts)


def chat(message: str, history: list[dict], profile: dict, node_id: str | None = None) -> dict:
    node = roadmap_service.get_node(node_id) if node_id else None
    query = " ".join(filter(None, [message, profile.get("stream") or "", node["title"] if node else ""]))
    snippets = rag_service.search(query, k=4)
    sources = sorted({s["source"] for s in snippets})
    if not llm_service.available:
        return {"reply": _offline_reply(message, node, snippets), "sources": sources, "llm_used": False, "provider": None}
    messages = [Message(h["role"], h["content"]) for h in history[-8:] if h["role"] in ("user", "assistant")]
    messages.append(Message("user", message))
    try:
        reply = llm_service.chat(messages, system=system_prompt(profile, node, snippets))
        return {"reply": reply, "sources": sources, "llm_used": True,
                "provider": llm_service.used_provider or llm_service.provider()}
    except LLMError as exc:
        log.warning("Mentor LLM failure: %s", exc)
        return {"reply": _offline_reply(message, node, snippets, reason="provider_failed"),
                "sources": sources, "llm_used": False, "provider": None}
