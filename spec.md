# CAMI Project Spec

## Overview

- **Name**: CAMI — Counselor Agent Supporting Motivational Interviewing
- **Purpose**: Simulate counseling sessions using MI principles with two agents:
  - **Counselor agent (`CAMI`)**: infers client state, explores topics, selects strategies, generates and refines responses.
  - **Client simulator (`Client`)**: responds per personas, current state, engagement, and acceptable plans.
- **Entry Point**: `generate.py`
- **Primary Modules**: `agents/counselor.py`, `agents/client.py`, `agents/env.py`

## High-Level Architecture

```mermaid
flowchart TD
  A[generate.py] -->|builds| B[CAMI (counselor)]
  A -->|builds| C[Client (simulated)]
  A -->|creates| D[Env]
  D -->|interact() loop| E[counselor.reply()]
  E -->|returns counselor text| D
  D -->|client.receive(counselor text)| C
  D -->|client.reply()| F[Client LLM turn]
  F -->|returns client text| D
  D -->|counselor.receive(client text)| B
  D -->|moderator checks| G{stop?}
  G -->|yes| H[write/print and end]
  G -->|no| E
```

## Components

- **`generate.py`**
  - Parses CLI args: `--model`, `--retriever_path`, `--wikipedia_dir`, `--profile_path`, `--output_dir`, `--round`, `--max_turns`.
  - Loads profiles from `annotations/profiles.jsonl` and runs multiple rounds/samples.
  - Instantiates:
    - `CAMI(goal, behavior, model)` from `agents/counselor.py`.
    - `Client(...)` from `agents/client.py` using profile fields (personas, states, motivations, beliefs, acceptable plans, suggestibility-based receptivity) and paths.
    - `Env(client, counselor, output_file, max_turns)` from `agents/env.py`.
  - Calls `env.interact()` to execute a session; outputs transcripts under `Output/`.

- **`agents/env.py` — Env (Orchestrator)**
  - Maintains turn-taking and conversation state.
  - Writes to file or prints; initializes with a greeting exchange.
  - Methods:
    - `interact()`: alternates `counselor.reply()` and `client.reply()` with `receive()` calls on the opposite side.
    - `clean_utterance(utterance)`: strips bracketed annotations via `regex`.
    - `heuristic_moderator(context)`: ends session if recent utterance says “goodbye” or if lexical overlap with an earlier turn is very high.

- **`agents/counselor.py` — CAMI (Counselor Agent)**
  - Constructs a MI-informed system prompt and tracks `self.messages` and `self.conversation`.
  - Uses OpenAI Chat Completions directly with robust retries (`backoff`).
  - Key flows in `reply()`:
    - `infer_state()`: infer client stage (e.g., Precontemplation, Contemplation, Preparation).
    - Topic control: `initialize_topic()` on the first turn; `explore()` thereafter to pick next topic using an internal topic graph and exploration logic.
    - `select_strategy(state)`: determine MI strategy set (e.g., Advise, Affirm, Open Question, Reflect, etc.).
    - `generate(last_utterance, topic, state, selected_strategies)`: produce multiple candidate responses.
    - Response selection: prompts LLM to select the best candidate by ID.
    - `refine(context_tail, response, strategy_description, topic_description)`: polish the final response.
    - Appends the assistant message and returns the utterance prefixed with metadata: inferred state, strategy selection, final strategy, topic, and exploration action.
  - Communication:
    - `receive(response)`: append user text to buffers.
    - `reply()`: perform the full counselor turn and return final utterance.

- **`agents/client.py` — Client (Simulated Client)**
  - Encapsulates client profile: goal, behavior, personas, beliefs, plans, motivation, initial/final states, receptivity/engagement, reference transcript, topic/state/action prompts and graphs.
  - Uses OpenAI Chat Completions directly with `backoff`.
  - Imports `transformers` (`AutoTokenizer`, `AutoModelForSequenceClassification`) for local classification/retriever utilities.
  - Key behaviors:
    - `update_state()`: evolve state and engagement; produce analysis text.
    - `select_action()`: choose next client action (e.g., Deny, Downplay, Blame, Inform, Engage, Hesitate, Doubt, Acknowledge, Plan, Terminate).
    - `select_information(action)`: pick persona/belief/plan snippet—may validate with a yes/no LLM check.
    - `get_engage_instruction()`: derive instruction text based on engagement level.
    - `receive(response)`: record counselor utterance in context.
    - `reply()`: craft bracketed instructions + last context as LLM input, normalize to `Client: ...`, update logs, and return with a metadata prefix.

- **`agents/__init__.py`**
  - Exports `Client`, `CAMI`, `Env` for convenient imports.

## Data and Configuration

- **Profiles**: `annotations/profiles.jsonl` — one JSON per line with fields used to initialize `Client` and `CAMI`.
- **Wikipedia directory**: `wikipedias/` — path passed into `Client` for topic grounding.
- **Retriever**: `--retriever_path` — model path used by `Client` utilities.
- **Model selection**: `--model` passed to both agents for OpenAI API calls.
- **Credentials**: `OPENAI_API_KEY`, `OPENAI_BASE_URL` env vars required by `openai.OpenAI`.
- **Output**: transcripts saved to `Output/Sample-<i>-Round-<j>.txt`.

## Control Flow and Termination

- **Turn order**:
  - Counselor speaks first: `counselor.reply()`
  - Client receives and replies: `client.receive()` then `client.reply()`
- **Normalization**:
  - `Env.clean_utterance()` strips bracketed meta before persisting/printing.
  - Agents normalize prefixes: ensure `Counselor:` and `Client:`; strip cross-role leakage if detected.
- **Termination conditions**:
  - Heuristic moderator: greeting-based end or high lexical overlap.
  - Client-triggered markers detected in `Env.interact()`:
    - Contains `You are motivated because`
    - Contains `You should highlight current state and engagement, express a desire to end the current session`

## External Dependencies

- **LLM**: Direct OpenAI Chat Completions via `openai` SDK (`OpenAI().chat.completions.create`).
- **Retries**: `backoff` for robust API error handling.
- **NLP**: `transformers` for local classification/retrieval.
- **Regex**: `regex` for bracketed content removal.

## File Map (primary)

- `generate.py`
- `agents/__init__.py`
- `agents/counselor.py`
- `agents/client.py`
- `agents/env.py`
- `annotations/profiles.jsonl`
- `wikipedias/`
- `Output/` (generated)

## Notes

- The project does not use an LLM agent framework (e.g., LangChain); it composes agent logic directly over the OpenAI SDK with structured prompting, candidate generation/selection, and refinement.
