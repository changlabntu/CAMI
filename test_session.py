#!/usr/bin/env python
"""Replay test: runs 8 real user inputs through JournalAgent's full CBT → narrative → finalize flow.

Requires ANTHROPIC_API_KEY. Takes ~30-60s with sonnet.

    source .env && python test_session.py
    pytest test_session.py -s
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

from agents.agent_journal_pin import JournalAgent
from agents.journal_common import PHASE_COMMANDS


def fmt_meta(meta, phase=""):
    if not meta:
        return ""
    return f"  [{meta['model']}] phase: {phase} | in: {meta['input_tokens']} | out: {meta['output_tokens']} | time: {meta['elapsed_time']:.2f}s"


def run_session():
    agent = JournalAgent(model="sonnet")
    step = 0

    def exchange(user_input):
        nonlocal step
        step += 1
        print(f"\n--- Step {step}: receive + reply ({agent.phase}) ---")
        commands = PHASE_COMMANDS.get(agent.phase, "")
        prompt = f"SELECT [{commands}] OR SAY SOMETHING" if commands else "You"
        print(f"{prompt}: {user_input}")
        agent.receive(user_input)
        response = agent.reply()
        print(f"Agent: {response[:200]}{'...' if len(response) > 200 else ''}")
        print(fmt_meta(agent.last_metadata, agent.phase))
        return response

    # ── CBT phase (4 user inputs) ──
    assert agent.phase == "cbt"

    exchange("Two days before Lunar New Year's Eve, Mom sent a barrage of messages, "
             "starting with 'Are you coming home for New Year?' then quickly escalating to "
             "'You never care about this family' and 'I've done so much for you and this is "
             "how you repay me.' I didn't even have time to reply before the next message hit.")
    exchange("angry")
    exchange("8")
    exchange("want to run away")

    # ── Reframe ──
    print("\n--- Reframe ---")
    reframed = agent.reframe()
    print(f"Reframed: {reframed[:300]}{'...' if len(reframed) > 300 else ''}")
    print(fmt_meta(agent.last_metadata, agent.phase))
    assert agent.reframed_journal is not None, "reframed_journal should be set after reframe()"
    assert len(agent.reframed_journal) > 0

    # ── Start narrative ──
    print("\n--- Start Narrative ---")
    narrative_response = agent.start_narrative()
    print(f"Agent: {narrative_response[:200]}{'...' if len(narrative_response) > 200 else ''}")
    print(fmt_meta(agent.last_metadata, agent.phase))
    assert agent.phase == "narrative", f"Expected phase 'narrative', got '{agent.phase}'"

    # ── Narrative phase (2 user inputs) ──
    exchange("i blocked her last time")
    exchange("i understood that i was hurt")

    # ── Summarize ──
    print("\n--- Summarize ---")
    summary = agent.summarize()
    print(f"Summary: {summary[:300]}{'...' if len(summary) > 300 else ''}")
    print(fmt_meta(agent.last_metadata, agent.phase))
    assert agent.final_summary is not None, "final_summary should be set after summarize()"
    assert len(agent.final_summary) > 0

    # ── Finalize ──
    print("\n--- Finalize ---")
    finalize_response = agent.finalize("end")
    print(f"Agent: {finalize_response[:200]}{'...' if len(finalize_response) > 200 else ''}")
    print(fmt_meta(agent.last_metadata, agent.phase))
    assert agent.phase == "finalize", f"Expected phase 'finalize', got '{agent.phase}'"

    # ── Finalize phase (2 user inputs) ──
    exchange("2")
    exchange("nothing bye")

    print("\n=== ALL STEPS PASSED ===")


def test_full_session():
    """Pytest entry point."""
    run_session()


if __name__ == "__main__":
    run_session()
