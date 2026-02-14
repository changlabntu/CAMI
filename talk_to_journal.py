#!/usr/bin/env python
"""Simple script to talk to the JournalAgent."""

import argparse

from dotenv import load_dotenv
load_dotenv()

from agents.agent_journal import JournalAgent as BaseJournalAgent, MODELS as base_models
from agents.agent_journal_pin import JournalAgent as PinAgent, MODELS as pin_models

AGENTS = {
    "journal": (BaseJournalAgent, base_models),
    "pin": (PinAgent, pin_models),
}


def main():
    parser = argparse.ArgumentParser(description="Talk to the Journal Agent")
    parser.add_argument("--agent", choices=["journal", "pin"], default="journal",
                        help="Agent type: journal (default) or pin")
    parser.add_argument("--model", choices=["opus", "sonnet"], default="sonnet",
                        help="Model to use: opus (default) or sonnet")
    parser.add_argument("--show-metadata", action="store_true",
                        help="Show token usage and response time after each exchange")
    args = parser.parse_args()

    JournalAgent, MODELS = AGENTS[args.agent]

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
