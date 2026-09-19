"""
FastAPI server exposing the knowledge-base agent over HTTP.

Run:
    pip install fastapi uvicorn --trusted-host pypi.org --trusted-host files.pythonhosted.org
    uvicorn serve:app --reload         # from the agent/ folder
    # open http://127.0.0.1:8000/docs

Endpoints:
    GET  /health            -> {"status": "ok", "chunks": N, "llm": "..."}
    GET  /areas             -> list of available areas
    POST /ask   {question, area?, k?}  -> {answer, citations, area, used_llm}

This is the Phase 3 bridge: a small web API you can call from a chat box in the
MkDocs site later. It reuses kb_agent/kb_index unchanged.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from kb_index import load_index, build_index, save_index, INDEX_PATH
from kb_agent import answer, get_llm

app = FastAPI(
    title="GenAI KB Agent",
    description="Ask questions grounded in the personal GenAI/data knowledge base.",
    version="2.0",
)

# Allow the local MkDocs dev server / static site to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_INDEX = None


def _get_index():
    global _INDEX
    if _INDEX is None:
        if not INDEX_PATH.exists():
            save_index(build_index())
        _INDEX = load_index()
    return _INDEX


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, examples=["What is Cortex Analyst?"])
    area: str = Field("all", examples=["snowflake", "rag", "vector-db", "all"])
    k: int = Field(4, ge=1, le=10)


class GradeRequest(BaseModel):
    question: str = Field(..., min_length=2)
    answer: str = Field(..., min_length=1)
    model_answer: str = Field("", description="Reference answer to grade against.")


class GradeResponse(BaseModel):
    score: int
    feedback: str
    used_llm: bool


class Citation(BaseModel):
    label: str
    url: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    area: str
    used_llm: bool


@app.get("/health")
def health():
    idx = _get_index()
    return {
        "status": "ok",
        "chunks": len(idx["chunks"]),
        "llm": os.environ.get("KB_LLM", "none") if get_llm() else "extractive",
    }


@app.get("/areas")
def areas():
    idx = _get_index()
    seen = sorted({c["area"] for c in idx["chunks"]})
    return {"areas": ["all"] + seen}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    ans = answer(req.question, area=req.area, k=req.k, index=_get_index())
    return AskResponse(
        answer=ans.text, citations=ans.citations,
        area=ans.area, used_llm=ans.used_llm,
    )


@app.post("/grade", response_model=GradeResponse)
def grade(req: GradeRequest):
    """Grade a practice answer against a reference answer (LOCAL-ONLY feature).

    Used by the Interview Practice page's optional "AI grade" button. Requires
    an LLM backend (KB_LLM env var); otherwise returns used_llm=False with a
    hint, and the practice page falls back to manual self-rating.
    """
    import json
    import re

    llm = get_llm()
    if not llm:
        return GradeResponse(
            score=0, used_llm=False,
            feedback=("No LLM backend configured. Set KB_LLM (e.g. bedrock/openai/"
                      "ollama) to enable AI grading, or use manual self-rating."),
        )

    prompt = (
        "You are an interview coach. Grade the candidate's answer against the "
        "reference answer for the question. Score 1-5 (5 = excellent, complete, "
        "accurate; 1 = missed it). Give two sentences of specific, constructive "
        "feedback: what was good and what to add.\n\n"
        f"Question: {req.question}\n\n"
        f"Reference answer: {req.model_answer}\n\n"
        f"Candidate answer: {req.answer}\n\n"
        'Respond with JSON only: {"score": <int 1-5>, "feedback": "<text>"}'
    )
    try:
        raw = llm(prompt)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
        score = int(data.get("score", 0))
        score = max(1, min(5, score)) if score else 0
        feedback = str(data.get("feedback") or raw).strip()
        return GradeResponse(score=score or 3, feedback=feedback, used_llm=True)
    except Exception as exc:  # noqa: BLE001
        return GradeResponse(
            score=0, used_llm=False,
            feedback=f"Grading failed ({exc}). Use manual self-rating instead.",
        )


@app.post("/reindex")
def reindex():
    global _INDEX
    save_index(build_index())
    _INDEX = load_index()
    return {"status": "reindexed", "chunks": len(_INDEX["chunks"])}
