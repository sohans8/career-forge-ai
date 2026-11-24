"""Roadmaps, colleges, mentor, resume and guidance endpoints."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.services import mentor_service, resume_service
from backend.app.services.college_service import college_service
from backend.app.services.guidance_service import guidance_service
from backend.app.services.llm_service import llm_service
from backend.app.services.rag_service import rag_service
from backend.app.services.roadmap_service import roadmap_service

Stage = Literal["after_10th", "after_12th", "after_diploma"]

roadmaps = APIRouter(prefix="/api/roadmaps", tags=["Roadmaps"])
colleges = APIRouter(prefix="/api/colleges", tags=["Colleges"])
mentor = APIRouter(prefix="/api/mentor", tags=["AI Mentor"])
resume = APIRouter(prefix="/api/resume", tags=["Resume"])
guidance = APIRouter(prefix="/api/guidance", tags=["Guidance"])
system = APIRouter(prefix="/api", tags=["System"])


# ------------------------------------------------------------------ roadmaps
@roadmaps.get("")
def get_roadmap(stage: Stage = Query(..., description="after_10th | after_12th | after_diploma"),
                stream: str | None = Query(None, description="e.g. science_pcm, commerce, diploma, dip_cs")):
    """Filtered node/edge graph for one stage."""
    return roadmap_service.graph(stage, stream)


@roadmaps.get("/meta")
def roadmap_meta():
    return roadmap_service.meta()


@roadmaps.get("/nodes/{node_id}")
def get_node(node_id: str):
    node = roadmap_service.get_node(node_id)
    if not node:
        raise HTTPException(404, "Roadmap node not found")
    return node


# ------------------------------------------------------------------- colleges
@colleges.get("")
def search_colleges(state: str | None = None, type: Literal["engineering", "diploma", "pharmacy", "management"] | None = None,
                    branch: str | None = None, district: str | None = None, ownership: str | None = None,
                    q: str | None = Query(None, description="Name contains"), limit: int = Query(20, ge=1, le=100),
                    offset: int = Query(0, ge=0)):
    return college_service.search(state, type, branch, district, ownership, q, limit, offset)


@colleges.get("/states")
def list_states():
    return {"states": college_service.states()}


# --------------------------------------------------------------------- mentor
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class MentorProfile(BaseModel):
    stage: Stage | None = None
    stream: str | None = Field(None, max_length=60)
    target_goal: str | None = Field(None, max_length=200)
    name: str | None = Field(None, max_length=80)


class MentorRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=30)
    profile: MentorProfile = Field(default_factory=MentorProfile)
    node_id: str | None = Field(None, max_length=60)


@mentor.post("/chat")
def mentor_chat(req: MentorRequest):
    return mentor_service.chat(req.message, [t.model_dump() for t in req.history], req.profile.model_dump(), req.node_id)


@mentor.get("/prompts")
def mentor_prompts(stage: Stage = "after_10th"):
    return {"prompts": mentor_service.QUICK_PROMPTS[stage]}


# --------------------------------------------------------------------- resume
@resume.get("/roles")
def resume_roles():
    from backend.app.services.resume_service import skill_bank
    return {"roles": skill_bank.roles()}


@resume.post("/analyze")
async def analyze_resume(file: UploadFile = File(...), target_role: str = Form(..., max_length=80)):
    """Upload a PDF/DOCX resume and receive ATS score, skill gaps, rewrites and a learning checklist."""
    name = (file.filename or "").lower()
    if not name.endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX files are supported")
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")
    try:
        return resume_service.analyze(name, data, target_role)
    except resume_service.ResumeError as exc:
        raise HTTPException(422, str(exc))


# ------------------------------------------------------------------- guidance
class GuidanceRequest(BaseModel):
    stage: Stage
    stream: str | None = Field(None, max_length=60)
    interests: list[str] = Field(default_factory=list, max_length=6)
    strengths: list[str] = Field(default_factory=list, max_length=12)
    career_goal: str = Field("", max_length=200)
    name: str = Field("", max_length=80)


@guidance.get("/quiz")
def quiz():
    return guidance_service.quiz()


@guidance.post("/recommend")
def recommend(req: GuidanceRequest):
    return guidance_service.recommend(req.stage, req.stream, req.interests, req.strengths, req.career_goal, req.name)


# --------------------------------------------------------------------- system
@system.get("/status")
def status():
    """Dataset and AI configuration status (no secrets)."""
    meta = roadmap_service.meta()
    return {
        "roadmap_version": meta.get("schema_version"),
        "roadmap_last_updated": meta.get("last_updated"),
        "roadmap_nodes": len(roadmap_service.nodes),
        "colleges": college_service.search(limit=1)["total"],
        "careers": len(guidance_service.careers()),
        "resume_roles": len(resume_service.skill_bank.roles()),
        "rag": rag_service.stats(),
        "llm": {"configured": llm_service.available, "provider": llm_service.provider(), "model": llm_service.model_name(),
                "providers": llm_service.candidates(), "last_error": llm_service.last_error},
    }
