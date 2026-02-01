#!/usr/bin/env python
"""Interactive chat with counselor agent."""

from dotenv import load_dotenv
load_dotenv()

from agents import CAMI, CAMISimple
from agents.agent_story import CAMIStory
import argparse


# Default scenarios for quick start
DEFAULT_SCENARIOS = {
    "smoking": {
        "goal": "quit smoking",
        "behavior": "smoking"
    },
    "drinking": {
        "goal": "reduce alcohol consumption",
        "behavior": "drinking"
    },
    "exercise": {
        "goal": "exercise regularly",
        "behavior": "sedentary lifestyle"
    },
    "diet": {
        "goal": "eat healthier",
        "behavior": "unhealthy eating habits"
    },
    "suicidal": {
        "goal": "willing to stay on the phone and talk about it",
        "behavior": "want to commit suicide"
    },
}


def main():
    parser = argparse.ArgumentParser(description="Interactive counselor session")
    parser.add_argument("--model", type=str, default="gpt-4o-2024-08-06", help="OpenAI model to use")
    parser.add_argument("--show-metadata", action="store_true", help="Show counselor's internal state metadata")
    parser.add_argument(
        "--scenario", type=str, default="suicidal", choices=list(DEFAULT_SCENARIOS.keys()),
        help="Predefined scenario to use (default: suicidal)"
    )
    parser.add_argument("--agent", type=str, default="simple", choices=["simple", "cami", "story"],
                        help="Agent type: simple (default) or cami (full MI with topics)")
    parser.add_argument("--context", type=str, default="cami", choices=["cami", "crisis", "story"],
                        help="Agent context: cami (default, MI-focused), crisis (DBT, safety-focused), or story (narrative therapy)")
    parser.add_argument("--story", type=str, default=None,
                        help="Path to initial client story file (used with --agent story)")
    args = parser.parse_args()

    # Get goal and behavior from scenario
    scenario = DEFAULT_SCENARIOS[args.scenario]
    goal = scenario["goal"]
    behavior = scenario["behavior"]

    # agent and context control
    print("\n" + "="*60)
    if args.agent == "cami":
        print("CAMI - Full Motivational Interviewing Counselor (with topics)")
    elif args.context == "crisis":
        print("Simple Agent - DBT Crisis Counselor (safety-focused)")
    elif args.context == "story":
        print("Simple Agent - Narrative Therapy")
    else:
        print("Simple Agent - MI Counselor")

    print(f"Context: {args.context}")
    print("="*60)
    print(f"Goal: {goal}")
    print(f"Behavior: {behavior}")
    print("-"*60)
    print("Type 'quit' or 'exit' to end the session")
    print("Type 'state' to see current inferred state")
    if args.agent == "cami":
        print("Type 'topics' to see explored topics")
    print("="*60 + "\n")

    if args.agent == "cami":
        counselor = CAMI(goal=goal, behavior=behavior, model=args.model)
    elif args.agent == "story":
        initial_story = ""
        if args.story:
            with open(args.story, "r") as f:
                initial_story = f.read().strip()
            print(f"Loaded client story from: {args.story}")
            print(f"\n{initial_story}\n")
            print("-"*60)
        counselor = CAMIStory(goal=goal, behavior=behavior, model=args.model, context=args.context, initial_story=initial_story)
    else:  # default: simple
        crisis_mode = (args.context == "crisis")
        counselor = CAMISimple(goal=goal, behavior=behavior, model=args.model, crisis_mode=crisis_mode)

    # Get initial greeting from agent's messages (index 1 is first assistant message after system prompt)
    initial_greeting = counselor.messages[1]["content"]
    print(f"\n{initial_greeting}\n")

    while True:
        # Get user input
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
            print("\nCounselor: Thank you for talking with me today. Take care of yourself.\n")
            break

        if user_input.lower() == 'state':
            print(f"\n[Current State]")
            if args.agent == "cami":
                print(f"  Mode: Full CAMI (MI with topic management)")
                print(f"  Initialized: {counselor.initialized}")
                print(f"  Topic Stack: {counselor.topic_stack}")
                print(f"  Explored Topics: {counselor.explored_topics}")
            else:
                print(f"  Mode: Simple (context: {args.context})")
                print(f"  Messages: {len(counselor.messages)}")
            print()
            continue

        if user_input.lower() == 'topics':
            if args.agent != "cami":
                print("\n[Topics not used in this mode]\n")
            else:
                print(f"\n[Topic History]")
                print(f"  Stack (current path): {' -> '.join(counselor.topic_stack) if counselor.topic_stack else '(none)'}")
                print(f"  All explored: {' -> '.join(counselor.explored_topics) if counselor.explored_topics else '(none)'}")
                print()
            continue

        # Send to counselor
        counselor.receive(f"Client: {user_input}")

        # Get response
        response = counselor.reply()

        # Parse response (remove metadata brackets if not showing)
        if args.show_metadata:
            # Format metadata with newlines for readability
            if "] Counselor:" in response:
                metadata_part = response.split("] Counselor:")[0] + "]"
                counselor_part = "Counselor:" + response.split("] Counselor:")[1]
                # Add newlines before each separator (|| for MI, | for crisis)
                if " || " in metadata_part:
                    formatted_metadata = metadata_part.replace(" || ", "\n|| ")
                else:
                    formatted_metadata = metadata_part.replace(" | ", "\n| ")
                print(f"\n{formatted_metadata}")
                print(f"{counselor_part.strip()}\n")
            else:
                print(f"\n{response}\n")
        else:
            # Extract just the counselor's words
            if "] Counselor:" in response:
                clean_response = "Counselor:" + response.split("] Counselor:")[1]
            elif "Counselor:" in response:
                clean_response = "Counselor:" + response.split("Counselor:")[-1]
            else:
                clean_response = response
            print(f"\n{clean_response.strip()}\n")


if __name__ == "__main__":
    main()
