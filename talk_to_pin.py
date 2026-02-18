#!/usr/bin/env python
"""Simple script to talk to the JournalAgent (multi-phase pin agent)."""

import argparse
import os

from dotenv import load_dotenv
load_dotenv()

from agents.agent_journal_pin import JournalAgent
from agents.journal_common import MODELS, PHASE_COMMANDS

ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "archived")


def save_to_archive(content, stage):
    """Save content to archived/ directory."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    filepath = os.path.join(ARCHIVE_DIR, f"{stage}.txt")
    with open(filepath, "w") as f:
        f.write(content)


def print_metadata(agent, show_metadata):
    """Print token usage and response time if enabled."""
    if show_metadata and agent.last_metadata:
        m = agent.last_metadata
        print(f"\n  [{m['model']}] phase: {agent.phase} | in: {m['input_tokens']} | out: {m['output_tokens']} | time: {m['elapsed_time']:.2f}s")


def get_input(prompt="\nYou: "):
    """Get user input, return None on quit commands."""
    user_input = input(prompt).strip()
    if not user_input:
        return ""
    if user_input.lower() in ("quit", "exit", "q"):
        return None
    return user_input


def run_session(agent, show_metadata):
    """Run the multi-phase journaling session."""
    while True:
        try:
            commands = PHASE_COMMANDS.get(agent.phase, "")
            prompt = f"\nSELECT [{commands}] OR SAY SOMETHING: " if commands else "\nYou: "
            user_input = get_input(prompt)
            if user_input is None:
                return
            if not user_input:
                continue

            cmd = user_input.lower() # hardcoded user input reframe > next > narrarive > summarize > end

            # --- CBT phase commands ---
            if agent.phase == "cbt":
                if cmd == "reframe": # hardcoded user input
                    print("\n--- Reframed Journal Entry ---\n")
                    reframed = agent.reframe()
                    print(reframed)
                    print_metadata(agent, show_metadata)
                    continue

                if cmd == "next": # hardcoded user input
                    if not agent.reframed_journal:
                        print("\n--- Reframing first... ---\n")
                        reframed = agent.reframe()
                        print(reframed)
                        print_metadata(agent, show_metadata)
                    save_to_archive(agent.reframed_journal, "reframe")
                    print("\n--- Narrative Therapy Session ---\n")
                    response = agent.start_narrative()
                    print(f"\n{response}")
                    print_metadata(agent, show_metadata)
                    continue

            # --- Narrative phase commands ---
            elif agent.phase == "narrative":
                if cmd == "summarize": # hardcoded user input
                    print("\n--- Reflection Summary ---\n")
                    summary = agent.summarize()
                    print(summary)
                    print_metadata(agent, show_metadata)

                    title = get_input("\nTitle: ")
                    if title is None:
                        return

                    save_to_archive(agent.final_summary, "summarize")
                    print("\n--- Finalizing Journal ---\n")
                    response = agent.finalize(title)
                    print(f"\n{response}")
                    print_metadata(agent, show_metadata)
                    continue

            # --- Finalize phase commands ---
            elif agent.phase == "finalize":
                if cmd == "end": # hardcoded user input
                    print(f"\nJournal '{agent.journal_title}' archived!")
                    return

            # --- Normal conversation (all phases) ---
            agent.receive(user_input)
            response = agent.reply()
            print(f"\n{response}")
            print_metadata(agent, show_metadata)

        except KeyboardInterrupt:
            return


def main():
    parser = argparse.ArgumentParser(description="Talk to the Journal Agent")
    parser.add_argument("--model", choices=["opus", "sonnet"], default="sonnet",
                        help="Model to use: opus (default) or sonnet")
    parser.add_argument("--show-metadata", action="store_true",
                        help="Show token usage and response time after each exchange")
    parser.add_argument("--cbt", action="store_true",
                        help="Start with CBT journaling session")
    parser.add_argument("--narrative", action="store_true",
                        help="Start narrative therapy directly")
    parser.add_argument("--finalize", action="store_true",
                        help="Start finalize directly (reads from archived/summarize.txt)")
    parser.add_argument("--origin_story", type=str, default="story/example.txt",
                        help="Path to story file (default: story/example.txt)")
    args = parser.parse_args()

    if not args.cbt and not args.narrative and not args.finalize:
        print("Please specify --cbt, --narrative, or --finalize")
        return

    agent = JournalAgent(model=args.model)
    print(f"Using model: {MODELS[args.model]}")

    if args.finalize:
        with open("archived/summarize.txt", "r") as f:
            summary = f.read().strip()
        agent.final_summary = summary
        agent.origin_reframed_journal = summary
        print(f"Loaded summary from: archived/summarize.txt")
        print("\n--- Finalizing Journal ---\n")

        title = input("Enter journal title: ").strip()
        if title.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            return

        response = agent.finalize(title)
        print(f"\n{response}")
        print_metadata(agent, args.show_metadata)

    elif args.narrative:
        with open(args.origin_story, "r") as f:
            reframed_journal = f.read().strip()
        print(f"Loaded story from: {args.origin_story}")
        print("\n--- Narrative Therapy Session ---\n")
        response = agent.start_narrative(reframed_journal=reframed_journal)
        print(f"\n{response}")
        print_metadata(agent, args.show_metadata)

    else:
        # CBT mode — print greeting, phase is already "cbt"
        print(agent.messages[-1]["content"])

    run_session(agent, args.show_metadata)
    print("\nGoodbye!")


if __name__ == "__main__":
    main()
