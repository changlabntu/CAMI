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

from agents.agent_journal_pin import JournalAgent

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
    phase: str
    commands: list[str]


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]
    phase: str
    commands: list[str]


class MessageResponse(BaseModel):
    role: str
    content: str
    phase: str
    commands: list[str]
    metadata: Optional[dict] = None


class CommandRequest(BaseModel):
    command: str
    args: dict = {}


class CommandResponse(BaseModel):
    content: str
    phase: str
    commands: list[str]
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
    agent = JournalAgent(
        model=request.model or "sonnet",
        valence=request.valence,
        support_type=request.support_type,
    )

    # Extract greeting
    greeting = strip_counselor_prefix(agent.messages[1]["content"])

    session_id = uuid.uuid4().hex
    sessions[session_id] = (agent, time.time())

    return CreateSessionResponse(
        session_id=session_id,
        greeting=greeting,
        phase=agent.phase,
        commands=agent.commands,
    )


@app.get("/session/{session_id}", response_model=SessionResponse)
def get_session_info(session_id: str):
    agent = get_session(session_id)

    messages = []
    for msg in agent._active_conversation.messages:
        if msg["role"] == "system":
            continue
        content = strip_counselor_prefix(msg["content"]) if msg["role"] == "assistant" else msg["content"]
        messages.append({"role": msg["role"], "content": content})

    return SessionResponse(
        session_id=session_id,
        messages=messages,
        phase=agent.phase,
        commands=agent.commands,
    )


@app.post("/session/{session_id}/message", response_model=MessageResponse)
def send_message(session_id: str, request: SendMessageRequest):
    agent = get_session(session_id)

    agent.receive(request.content)
    response_text = agent.reply()

    return MessageResponse(
        role="assistant",
        content=strip_counselor_prefix(response_text),
        phase=agent.phase,
        commands=agent.commands,
        metadata=agent.last_metadata,
    )


@app.post("/session/{session_id}/command", response_model=CommandResponse)
def execute_command(session_id: str, request: CommandRequest):
    agent = get_session(session_id)
    try:
        result = agent.command(request.command, **request.args)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CommandResponse(
        content=strip_counselor_prefix(result),
        phase=agent.phase,
        commands=agent.commands,
        metadata=agent.last_metadata,
    )
