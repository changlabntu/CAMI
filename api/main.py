"""CAMI Journal API — FastAPI backend wrapping JournalAgent."""

import os
import sys
import time
import uuid
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root (parent of api/) — MUST run before importing agent_journal
# because it reads ANTHROPIC_API_KEY at module scope
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add project root to sys.path so `agents` package is importable
# (uvicorn runs from api/, so the parent dir isn't on sys.path by default)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.agent_journal import JournalAgent

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Pydantic models ---


class CreateSessionRequest(BaseModel):
    valence: float = Field(..., ge=-1.0, le=1.0)
    support_type: float = Field(..., ge=-1.0, le=1.0)
    model: Optional[str] = Field("sonnet")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class CreateSessionResponse(BaseModel):
    session_id: str
    greeting: str


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]


class MessageResponse(BaseModel):
    role: str
    content: str
    metadata: Optional[dict] = None


class ReframeResponse(BaseModel):
    reframed_entry: str
    metadata: Optional[dict] = None


# --- Session store ---

SESSION_TTL = 3600  # 1 hour

sessions: dict[str, tuple] = {}  # {id: (JournalAgent, last_access_time)}


def cleanup_sessions():
    now = time.time()
    expired = [sid for sid, (_, ts) in sessions.items() if now - ts > SESSION_TTL]
    for sid in expired:
        del sessions[sid]


def get_session(session_id: str):
    cleanup_sessions()
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    agent, _ = sessions[session_id]
    sessions[session_id] = (agent, time.time())
    return agent


# --- Emotion mapping ---


def describe_emotion(valence: float, support_type: float) -> str:
    if valence < -0.5:
        feeling = "The user is feeling quite distressed or upset."
    elif valence < 0:
        feeling = "The user is feeling somewhat down or troubled."
    elif valence < 0.5:
        feeling = "The user is feeling okay, perhaps mildly positive."
    else:
        feeling = "The user is feeling quite good or positive."

    if support_type < -0.5:
        approach = "They are looking for compassion, empathy, and emotional validation. Focus on listening and reflecting their feelings rather than offering solutions."
    elif support_type < 0:
        approach = "They prefer a more empathetic and supportive approach, leaning toward emotional validation over direct advice."
    elif support_type < 0.5:
        approach = "They are open to some gentle guidance and practical suggestions alongside emotional support."
    else:
        approach = "They are looking for concrete advice, practical strategies, and actionable guidance."

    return f"\n\n{feeling} {approach}"


def strip_counselor_prefix(text: str) -> str:
    if text.startswith("Counselor: "):
        return text[len("Counselor: "):]
    return text


# --- App ---

app = FastAPI(title="CAMI Journal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---


@app.post("/session", response_model=CreateSessionResponse)
def create_session(request: CreateSessionRequest):
    agent = JournalAgent(model=request.model or "sonnet")

    # Append emotion description to system prompt
    agent.messages[0]["content"] += describe_emotion(request.valence, request.support_type)

    # Extract greeting
    greeting = strip_counselor_prefix(agent.messages[1]["content"])

    session_id = uuid.uuid4().hex
    sessions[session_id] = (agent, time.time())

    return CreateSessionResponse(session_id=session_id, greeting=greeting)


@app.get("/session/{session_id}", response_model=SessionResponse)
def get_session_info(session_id: str):
    agent = get_session(session_id)

    messages = []
    for msg in agent.messages:
        if msg["role"] == "system":
            continue
        content = strip_counselor_prefix(msg["content"]) if msg["role"] == "assistant" else msg["content"]
        messages.append({"role": msg["role"], "content": content})

    return SessionResponse(session_id=session_id, messages=messages)


@app.post("/session/{session_id}/message", response_model=MessageResponse)
def send_message(session_id: str, request: SendMessageRequest):
    agent = get_session(session_id)

    agent.receive(request.content)
    response_text = agent.reply()

    return MessageResponse(
        role="assistant",
        content=strip_counselor_prefix(response_text),
        metadata=agent.last_metadata,
    )


@app.post("/session/{session_id}/reframe", response_model=ReframeResponse)
def reframe_entry(session_id: str):
    agent = get_session(session_id)

    if not agent.init_journal:
        raise HTTPException(status_code=400, detail="No journal entry to reframe. Send at least one message first.")

    reframed = agent.reframe()

    return ReframeResponse(
        reframed_entry=reframed,
        metadata=agent.last_metadata,
    )
