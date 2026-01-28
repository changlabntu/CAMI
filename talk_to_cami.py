#!/usr/bin/env python
"""Interactive chat with CAMI counselor (MI, Simple, or Crisis mode)."""

from agents import CAMI, CAMISimple
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
    parser = argparse.ArgumentParser(description="Interactive CAMI (MI counselor) session")
    parser.add_argument("--model", type=str, default="gpt-4o-2024-08-06", help="OpenAI model to use")
    parser.add_argument("--show-metadata", action="store_true", help="Show counselor's internal state metadata")
    parser.add_argument(
        "--scenario", type=str, default="suicidal", choices=list(DEFAULT_SCENARIOS.keys()),
        help="Predefined scenario to use (default: smoking)"
    )
    parser.add_argument("--goal", type=str, default=None, help="Custom goal (overrides scenario)")
    parser.add_argument("--behavior", type=str, default=None, help="Custom behavior (overrides scenario)")
    parser.add_argument("--simple", action="store_true", help="Use simplified MI counselor (no topic management)")
    parser.add_argument("--crisis", action="store_true", help="Use DBT crisis counselor (safety-focused, directive). Implies --simple.")
    args = parser.parse_args()

    # --crisis implies --simple
    if args.crisis:
        args.simple = True

    # Determine goal and behavior
    if args.goal and args.behavior:
        goal = args.goal
        behavior = args.behavior
    else:
        scenario = DEFAULT_SCENARIOS[args.scenario]
        goal = args.goal or scenario["goal"]
        behavior = args.behavior or scenario["behavior"]

    print("\n" + "="*60)
    if args.crisis:
        print("CAMI Crisis - DBT Crisis Counselor (safety-focused)")
    elif args.simple:
        print("CAMI Simple - MI Counselor (no topic management)")
    else:
        print("CAMI - Motivational Interviewing Counselor")
    print("="*60)
    print(f"Goal: {goal}")
    print(f"Behavior: {behavior}")
    print("-"*60)
    print("Type 'quit' or 'exit' to end the session")
    print("Type 'state' to see current inferred state")
    if not args.simple and not args.crisis:
        print("Type 'topics' to see explored topics")
    print("="*60 + "\n")

    if args.simple:
        counselor = CAMISimple(goal=goal, behavior=behavior, model=args.model, crisis_mode=args.crisis)
    else:
        counselor = CAMI(goal=goal, behavior=behavior, model=args.model)

    print("Counselor: Hello. How are you?\n")

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
            if args.simple:
                if args.crisis:
                    print(f"  Mode: Simple + Crisis (DBT, safety-focused)")
                else:
                    print(f"  Mode: Simple (MI, no topic management)")
                print(f"  Messages: {len(counselor.messages)}")
            else:
                print(f"  Initialized: {counselor.initialized}")
                print(f"  Topic Stack: {counselor.topic_stack}")
                print(f"  Explored Topics: {counselor.explored_topics}")
            print()
            continue

        if user_input.lower() == 'topics':
            if args.simple:
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
