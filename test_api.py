#!/usr/bin/env python
"""End-to-end API test: exercises the full CBT → narrative → finalize flow through HTTP endpoints.

Requires ANTHROPIC_API_KEY. Takes ~30-60s with sonnet.

    source .env && python test_api.py
    pytest test_api.py -s
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

# Ensure project root is on sys.path (same as api/main.py does)
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def fmt_meta(meta, phase=""):
    if not meta:
        return ""
    return f"  [{meta['model']}] phase: {phase} | in: {meta['input_tokens']} | out: {meta['output_tokens']} | time: {meta['elapsed_time']:.2f}s"


def send_message(session_id: str, text: str) -> dict:
    r = client.post(f"/session/{session_id}/message", json={"content": text})
    assert r.status_code == 200, f"message failed ({r.status_code}): {r.text}"
    return r.json()


def send_command(session_id: str, cmd: str, args: dict | None = None) -> dict:
    body = {"command": cmd}
    if args:
        body["args"] = args
    r = client.post(f"/session/{session_id}/command", json=body)
    assert r.status_code == 200, f"command '{cmd}' failed ({r.status_code}): {r.text}"
    return r.json()


def run_api_session():
    step = 0

    def exchange(session_id, user_input, expected_phase):
        nonlocal step
        step += 1
        print(f"\n--- Step {step}: POST /message ({expected_phase}) ---")
        print(f"You: {user_input}")
        data = send_message(session_id, user_input)
        print(f"Agent: {data['content'][:200]}{'...' if len(data['content']) > 200 else ''}")
        print(fmt_meta(data.get("metadata"), data["phase"]))
        assert data["phase"] == expected_phase, f"Expected phase '{expected_phase}', got '{data['phase']}'"
        assert len(data["content"]) > 0, "Empty response content"
        return data

    # ── 1. Create session ──
    print("\n--- Create session: POST /session ---")
    r = client.post("/session", json={"valence": -0.7, "support_type": -0.3, "model": "sonnet"})
    assert r.status_code == 200, f"create session failed ({r.status_code}): {r.text}"
    session = r.json()
    session_id = session["session_id"]
    print(f"Session: {session_id}")
    print(f"Greeting: {session['greeting'][:200]}{'...' if len(session['greeting']) > 200 else ''}")
    assert session["phase"] == "cbt"
    assert len(session["greeting"]) > 0

    # ── 2. CBT phase (4 user inputs) ──
    exchange(session_id,
             "Two days before Lunar New Year's Eve, Mom sent a barrage of messages, "
             "starting with 'Are you coming home for New Year?' then quickly escalating to "
             "'You never care about this family' and 'I've done so much for you and this is "
             "how you repay me.' I didn't even have time to reply before the next message hit.",
             "cbt")
    exchange(session_id, "angry", "cbt")
    exchange(session_id, "8", "cbt")
    exchange(session_id, "want to run away", "cbt")

    # ── 3. Reframe ──
    print("\n--- Reframe: POST /command {reframe} ---")
    data = send_command(session_id, "reframe")
    print(f"Reframed: {data['content'][:300]}{'...' if len(data['content']) > 300 else ''}")
    print(fmt_meta(data.get("metadata"), data["phase"]))
    assert len(data["content"]) > 0, "Empty reframe content"

    # ── 4. Start narrative ──
    print("\n--- Start Narrative: POST /command {next} ---")
    data = send_command(session_id, "next")
    print(f"Agent: {data['content'][:200]}{'...' if len(data['content']) > 200 else ''}")
    print(fmt_meta(data.get("metadata"), data["phase"]))
    assert data["phase"] == "narrative", f"Expected phase 'narrative', got '{data['phase']}'"
    assert len(data["content"]) > 0

    # ── 5. Narrative phase (2 user inputs) ──
    exchange(session_id, "i blocked her last time", "narrative")
    exchange(session_id, "i understood that i was hurt", "narrative")

    # ── 6. Summarize ──
    print("\n--- Summarize: POST /command {summarize} ---")
    data = send_command(session_id, "summarize")
    print(f"Summary: {data['content'][:300]}{'...' if len(data['content']) > 300 else ''}")
    print(fmt_meta(data.get("metadata"), data["phase"]))
    assert len(data["content"]) > 0, "Empty summary content"

    # ── 7. Finalize ──
    print("\n--- Finalize: POST /command {finalize} ---")
    data = send_command(session_id, "finalize", {"title": "Lunar New Year Reflections"})
    print(f"Agent: {data['content'][:200]}{'...' if len(data['content']) > 200 else ''}")
    print(fmt_meta(data.get("metadata"), data["phase"]))
    assert data["phase"] == "finalize", f"Expected phase 'finalize', got '{data['phase']}'"

    # ── 8. Finalize phase (2 user inputs) ──
    exchange(session_id, "2", "finalize")
    exchange(session_id, "nothing bye", "finalize")

    # ── 9. Verify session state ──
    print("\n--- Verify: GET /session/{id} ---")
    r = client.get(f"/session/{session_id}")
    assert r.status_code == 200, f"get session failed ({r.status_code}): {r.text}"
    state = r.json()
    assert state["phase"] == "finalize"
    assert len(state["messages"]) > 0, "Session messages should be non-empty"
    print(f"Phase: {state['phase']}, Messages: {len(state['messages'])}, Commands: {state['commands']}")

    print("\n=== ALL API STEPS PASSED ===")


def test_api_full_session():
    """Pytest entry point."""
    run_api_session()


if __name__ == "__main__":
    run_api_session()
