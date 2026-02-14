# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

CAMI is a conversational AI counseling system with multiple specialized agents for mental health support. It uses LangChain with both Anthropic (Claude) and OpenAI (GPT-4o) backends. The project is transitioning from CLI-based prototypes to a React Native + Expo mobile app with a FastAPI backend (see PLAN.md for mobile architecture).

## Running the Agents

```bash
# Load API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
source .env

# JournalAgent — CBT-based journaling (primary active agent, uses Claude)
python talk_to_journal.py --model sonnet --show-metadata

# Multi-agent CLI — MI/DBT/narrative therapy agents (uses GPT-4o)
python talk_to_agent.py --agent simple --context cami --scenario smoking --show-metadata
python talk_to_agent.py --agent cami --context crisis --scenario suicidal
python talk_to_agent.py --agent story --context story --story story/example.txt

# Planned: FastAPI backend
cd api && uvicorn main:app --reload --port 8000

# Planned: Expo mobile app
cd mobile && npx expo start
```

No test suite, linter, or build system exists — this is a research prototype.

## Architecture

### Agent System

All agents follow a common interface: `receive(input)` stores user messages, `reply()` generates responses via LLM.

- **JournalAgent** (`agents/agent_journal.py`) — The primary production agent. Uses Claude (Opus/Sonnet) via `langchain-anthropic`. CBT emotion/cognition/behavior triangle for structured journaling. Has a `reframe()` method that rewrites the original journal entry after the conversation. Stores first user input as `self.init_journal`.

- **CAMISimple** (`agents/agent.py`) — Simplified Motivational Interviewing counselor using GPT-4o. Pipeline: state inference → strategy selection → response generation → refinement.

- **CAMI** (`agents/cami.py`) — Full MI implementation with topic management and Stages of Change tracking (Precontemplation → Contemplation → Preparation). Uses context graphs and multi-step reasoning.

- **CAMIStory** (`notinuse/agent_story.py`) — Narrative therapy agent (experimental, archived).

### Context Modules

Context modules (`agents/context_*.py`) define domain-specific prompts, state dictionaries, and strategy descriptions:
- `context_cami.py` — MI strategies, topic graphs, stage-of-change instructions
- `context_crisis.py` — DBT crisis intervention, safety assessment, TIP skills

### Message Format

Agents store messages in OpenAI format (`[{"role": "system|user|assistant", "content": "..."}]`) and convert to LangChain format (`SystemMessage`, `HumanMessage`, `AIMessage`) at inference time via `openai_2_langchain()`.

### Entry Points

- `talk_to_journal.py` — Interactive CLI for JournalAgent. Uses `importlib` to bypass `agents/__init__.py` (which imports modules with OpenAI dependencies).
- `talk_to_agent.py` — Interactive CLI supporting all agent types with `--agent`, `--context`, `--scenario` flags.
- `generate.py` / `notinuse/generate_prompted.py` — Batch conversation generation (older approach).

### Environment

- `agents/env.py` (`Env` class) — Conversation moderator with heuristic-based session termination (detects goodbye keywords, utterance overlap).

## Key Dependencies

- `langchain-anthropic`, `langchain-openai`, `langchain-core` — LLM integration
- `pydantic` — Structured output parsing for state/strategy inference
- `python-dotenv` — API key loading from `.env`
- `regex` — Response parsing

## Conventions

- Agent responses are prefixed with `"Counselor: "` in the message history.
- Token usage and timing are tracked in `agent.last_metadata` after each `reply()` or `reframe()` call.
- The `notinuse/` directory contains archived/experimental code — not imported by active agents.
- `agents/__init__.py` imports Client, CAMI, CAMISimple, CAMIStory, Env — but JournalAgent is deliberately excluded (imported directly to avoid pulling in OpenAI dependencies).
