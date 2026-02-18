# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

CAMI is a conversational AI counseling system focused on structured journaling for mental health support. It uses LangChain with Anthropic (Claude) as the LLM backend. The project has a working React Native + Expo mobile app with a FastAPI backend. Earlier MI/DBT agents using GPT-4o have been archived to `notinuse/`.

## Running the Agents

```bash
# Load API keys (ANTHROPIC_API_KEY)
source .env

# JournalAgent — single-phase CBT journaling (uses Claude)
python talk_to_journal.py --model sonnet --show-metadata

# JournalAgent (pin) — multi-phase: CBT → narrative → finalize (uses Claude)
python talk_to_pin.py --cbt --model sonnet --show-metadata
python talk_to_pin.py --narrative --model sonnet --show-metadata
python talk_to_pin.py --finalize --model sonnet --show-metadata

# talk_to_journal.py also supports --agent pin for quick single-loop access
python talk_to_journal.py --agent pin --model sonnet --show-metadata

# FastAPI backend (start first — mobile app depends on it)
cd api && uvicorn main:app --reload --port 8000

# Expo mobile app (press 'i' for iOS Simulator)
cd mobile && npx expo start
```

No test suite, linter, or build system exists — this is a research prototype.

## Architecture

### Agent System

All agents follow a common interface: `receive(input)` stores user messages, `reply()` generates responses via LLM.

- **JournalAgent** (`agents/agent_journal.py`) — Single-phase CBT journaling agent. Uses Claude (Opus/Sonnet) via `langchain-anthropic`. CBT emotion/cognition/behavior triangle for structured journaling. Has a `reframe()` method that rewrites the original journal entry after the conversation. Stores first user input as `self.init_journal`.

- **JournalAgent (pin)** (`agents/agent_journal_pin.py`) — Multi-phase journaling agent. Extends the CBT approach with three phases managed by `self.phase`: **CBT** (emotion/cognition/behavior exploration + reframe), **narrative** (narrative therapy deepening via `start_narrative()` + `summarize()`), and **finalize** (emotion check-in + archiving via `finalize(title)`). Internally uses helper classes `LLMService`, `OneShotPhase`, and `ConversationPhase` to keep phase transitions clean. Phase-aware `receive()`/`reply()` automatically route to the correct message list.

### Message Format

Agents store messages in OpenAI format (`[{"role": "system|user|assistant", "content": "..."}]`) and convert to LangChain format (`SystemMessage`, `HumanMessage`, `AIMessage`) at inference time via `openai_2_langchain()`.

### FastAPI Backend (`api/`)

- **`api/main.py`** — Wraps JournalAgent as a REST API. In-memory session store with 1-hour TTL.
- Loads `.env` from parent directory for API keys.
- CORS allows all origins (dev mode).

| Endpoint | Method | Purpose |
|---|---|---|
| `/session` | POST | Create session with emotion coordinates (valence, support_type) |
| `/session/{id}` | GET | Fetch session messages |
| `/session/{id}/message` | POST | Send user message, get agent reply |
| `/session/{id}/reframe` | POST | Reframe the original journal entry |

- Emotion coordinates (-1..1) are mapped to natural language and appended to the system prompt.
- "Counselor: " prefix is stripped from responses (mobile app uses bubble alignment instead).

### Mobile App (`mobile/`)

React Native + Expo (SDK 54) app with three screens:

- **`app/_layout.tsx`** — Stack navigator with dark theme, wrapped in `GestureHandlerRootView`.
- **`app/index.tsx`** — Welcome screen with 2D Trackball for emotion input (valence: bad↔good, support: compassion↔advice). "Start Journaling" button creates a session and navigates to chat.
- **`app/chat.tsx`** — Chat screen with inverted FlatList, typing indicator, and reframe button (appears after 3+ exchanges).

Key components:
- **`components/Trackball.tsx`** — Circular gesture area using `react-native-gesture-handler` v2 + `react-native-reanimated`. Draggable ball clamped to circle radius.
- **`components/ChatBubble.tsx`** — User messages right-aligned (accent), assistant left-aligned (gray).
- **`components/ChatInput.tsx`** — Multiline text input with send button.
- **`lib/api.ts`** — HTTP client targeting `localhost:8000` with 90-second timeout (Claude responses can be slow).

**Note:** `react-native-worklets` must be pinned to 0.5.1 to match Expo Go's native binary. Higher versions cause a JS/native mismatch error.

### CLI Entry Points

- `talk_to_journal.py` — Interactive CLI for JournalAgent. Supports `--agent journal` (default, single-phase) and `--agent pin` (multi-phase).
- `talk_to_pin.py` — Multi-phase CLI for the pin agent with `--cbt`, `--narrative`, `--finalize` modes and phase-transition commands (`reframe`, `next`, `summarize`, `end`).

## Key Dependencies

**Python (agents + API):**
- `langchain-anthropic`, `langchain-core` — LLM integration
- `fastapi`, `uvicorn` — REST API server
- `pydantic` — Request/response models
- `python-dotenv` — API key loading from `.env`

**Mobile (Expo):**
- `expo` ~54, `expo-router` ~6 — App framework and file-based routing
- `react-native-gesture-handler` ~2.28, `react-native-reanimated` ~4.1 — Trackball gestures/animations
- `react-native-worklets` 0.5.1 (pinned) — Required by reanimated, must match Expo Go native version

## Conventions

- Agent responses are prefixed with `"Counselor: "` in the message history.
- Token usage and timing are tracked in `agent.last_metadata` after each `reply()` or `reframe()` call.
- The `notinuse/` directory contains archived/experimental code — not imported by active agents.
- `agents/__init__.py` is intentionally empty — all imports use explicit module paths (e.g. `from agents.agent_journal import JournalAgent`).
- `agents/journal_common.py` contains shared helpers (`MODELS`, `create_llm()`, `openai_2_langchain()`) used by both journal agents (`agent_journal.py` and `agent_journal_pin.py`).

## Archived (`notinuse/`)

The following agents and utilities have been archived. They are not imported by any active code.

- **CAMISimple** (`agent.py` → `notinuse/cami_original.py`) — Simplified Motivational Interviewing counselor using GPT-4o. Pipeline: state inference → strategy selection → response generation → refinement.
- **CAMI** — Full MI implementation with topic management and Stages of Change tracking. Used context modules (`context_cami.py`, `context_crisis.py`) for domain-specific prompts.
- **CAMIStory** (`notinuse/agent_story.py`) — Narrative therapy agent (experimental).
- **Env** (`env.py`) — Conversation moderator with heuristic-based session termination.
- **Context modules** (`context_cami.py`, `context_crisis.py`) — MI strategies, DBT crisis intervention prompts.
- **CLI**: `talk_to_agent.py` (MI/DBT agent CLI), `generate.py` / `generate_prompted.py` (batch conversation generation).
- **Client variants**: `client.py`, `client_backup.py`, `client_context.py`, `client_prompted.py` — older conversation clients.

## Git Policy
- Commit after each meaningful change, not at the end of a big task
- Use conventional commit messages: `type(scope): short description`
  - types: feat, fix, refactor, docs, style, test, chore
  - examples:
    - `feat(api): add session GET endpoint`
    - `fix(chat): handle 90s timeout on slow LLM responses`
    - `refactor(trackball): extract emotion description logic`
- Keep commits small and focused — one logical change per commit
- Never commit .env, API keys, or secrets
- Never commit node_modules or __pycache__
- Always commit from a feature branch, not main
- Branch naming: `feature/short-description` or `fix/short-description`
- Write a brief body in the commit message if the "why" isn't obvious from the title
- Don't amend or force-push commits that have already been discussed