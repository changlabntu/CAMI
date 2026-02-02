#!/usr/bin/env python
"""Simple script to talk to the JournalAgent."""

import argparse
import importlib.util

from dotenv import load_dotenv
load_dotenv()

# Direct import to bypass agents/__init__.py
spec = importlib.util.spec_from_file_location("agent_journal", "agents/agent_journal.py")
agent_journal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_journal)
JournalAgent = agent_journal.JournalAgent
MODELS = agent_journal.MODELS


def main():
    parser = argparse.ArgumentParser(description="Talk to the Journal Agent")
    parser.add_argument("--model", choices=["opus", "sonnet"], default="sonnet",
                        help="Model to use: opus (default) or sonnet")
    parser.add_argument("--show-metadata", action="store_true",
                        help="Show token usage and response time after each exchange")
    args = parser.parse_args()

    agent = JournalAgent(model=args.model)

    print(f"Using model: {MODELS[args.model]}")
    print(agent.messages[-1]["content"])

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input.lower() == "reframe":
                print("\n--- Reframed Journal Entry ---\n")
                reframed = agent.reframe()
                print(reframed)
                if args.show_metadata and agent.last_metadata:
                    m = agent.last_metadata
                    print(f"\n  [{m['model']}] in: {m['input_tokens']} tokens | out: {m['output_tokens']} tokens | time: {m['elapsed_time']:.2f}s")
                continue
            agent.receive(user_input)
            response = agent.reply()
            print(f"\n{response}")

            if args.show_metadata and agent.last_metadata:
                m = agent.last_metadata
                print(f"\n  [{m['model']}] in: {m['input_tokens']} tokens | out: {m['output_tokens']} tokens | time: {m['elapsed_time']:.2f}s")
        except KeyboardInterrupt:
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    main()
