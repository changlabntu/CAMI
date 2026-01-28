from agents import Env, DBTCrisisCall, ClientPrompted
from tqdm import tqdm
import os
import argparse

# Sample crisis scenarios for DBT skill coaching
CRISIS_SCENARIOS = [
    {
        "goal": "manage crisis",
        "behavior": "overwhelming anxiety",
        "description": "You are experiencing intense anxiety about a job interview tomorrow. Your heart is racing, you can't stop catastrophizing about everything that could go wrong, and you feel like you might have a panic attack. You called the crisis line because you don't know how to calm down."
    },
    {
        "goal": "manage crisis",
        "behavior": "conflict with partner",
        "description": "You just had a huge fight with your partner and they stormed out. You're furious and hurt. Part of you wants to send an angry text or pack their things, but you also don't want to make things worse. You're moderately distressed but can still think somewhat clearly."
    },
    {
        "goal": "manage crisis",
        "behavior": "urge to self-harm",
        "description": "You're having strong urges to hurt yourself after receiving rejection news. You haven't acted on it, but the urge is very strong. You're reaching out because you know you need help to get through this moment safely."
    },
    {
        "goal": "manage crisis",
        "behavior": "mild stress",
        "description": "You've been feeling a bit off lately - some work stress and general life pressures. Nothing major is happening, but you thought talking to someone might help. You're actually pretty calm right now, just looking for some coping strategies."
    },
    {
        "goal": "manage crisis",
        "behavior": "stuck in willfulness",
        "description": "You know what you need to do to fix your situation (apologize to your sister), but you absolutely refuse to do it because you feel she should apologize first. You're stuck and miserable, but also very stubborn about it. You're moderately upset."
    },
    {
        "goal": "manage crisis",
        "behavior": "overwhelming grief",
        "description": "You just found out your grandmother passed away. You're crying uncontrollably and feel like you can't breathe. The grief is overwhelming and you don't know how to get through the next few hours. You're very upset."
    },
    {
        "goal": "manage crisis",
        "behavior": "confused about next steps",
        "description": "You're in a difficult situation at work where your boss is treating you unfairly. You're moderately distressed and don't know whether to confront them, go to HR, or just quit. You can't figure out what the right move is."
    },
    {
        "goal": "manage crisis",
        "behavior": "interpersonal problem",
        "description": "Your roommate keeps eating your food and leaving messes in shared spaces. You're getting increasingly frustrated but haven't said anything because you don't know how to bring it up without causing conflict. You're moderately upset and think the situation is fixable if you could just communicate better."
    },
]


# Custom client for DBT crisis scenarios
class DBTClient(ClientPrompted):
    """Client adapted for DBT crisis call scenarios."""

    def __init__(self, goal, behavior, profile_description, model="gpt-4o-2024-08-06"):
        self.goal = goal
        self.behavior = behavior
        self.profile_description = profile_description
        self.model = model

        system_prompt = f"""You are a client calling a DBT crisis line for support.

## Your Situation
{profile_description}

## Response Guidelines
- Respond naturally based on your emotional state
- Keep responses concise (1-3 sentences)
- Show your actual distress level - don't be overly dramatic or overly calm
- If the counselor suggests a skill or technique, try to engage with it
- It's okay to express difficulty with suggestions or ask clarifying questions
- Prefix your response with "Client: "
- Never break character or acknowledge you are an AI
"""

        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Counselor: Hi, I'm glad you called. How are you doing right now? What's going on?"},
            {"role": "assistant", "content": "Client: I'm... I don't know. Things are just really hard right now."},
        ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DBT crisis call conversations")
    parser.add_argument("--model", type=str, default="gpt-4o-2024-08-06", help="OpenAI model to use for the agents")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./Output/DBT",
        help="Output directory to save the generated conversations",
    )
    parser.add_argument(
        "--round", type=int, default=1, help="Number of rounds to run the simulation"
    )
    parser.add_argument(
        "--max_turns", type=int, default=15, help="Maximum number of turns for each conversation"
    )
    parser.add_argument(
        "--scenario_idx", type=int, default=None, help="Specific scenario index to use (if not set, processes all scenarios)"
    )
    parser.add_argument(
        "--upset", type=str, default=None, choices=["very", "pretty", "not"],
        help="Fix the distress level: 'very' (acute), 'pretty' (moderate), 'not' (mild)"
    )

    args = parser.parse_args()

    # Map short names to internal values
    upset_map = {"very": "very_upset", "pretty": "pretty_upset", "not": "not_very"}
    fixed_distress = upset_map.get(args.upset) if args.upset else None

    # Determine which scenarios to process
    if args.scenario_idx is not None:
        if args.scenario_idx < 0 or args.scenario_idx >= len(CRISIS_SCENARIOS):
            raise ValueError(f"scenario_idx {args.scenario_idx} is out of range (0-{len(CRISIS_SCENARIOS)-1})")
        scenario_indices = [args.scenario_idx]
    else:
        scenario_indices = range(len(CRISIS_SCENARIOS))

    os.makedirs(args.output_dir, exist_ok=True)

    for j in range(args.round):
        for i in tqdm(scenario_indices, desc=f"Round-{j}"):
            scenario = CRISIS_SCENARIOS[i]
            # Include upset level in filename if specified
            upset_suffix = f"-{args.upset}" if args.upset else ""
            output_file = f"{args.output_dir}/DBT-Scenario-{i}-Round-{j}{upset_suffix}.txt"

            # Skip if already exists and completed
            if os.path.exists(output_file):
                with open(output_file) as f:
                    temp_lines = f.readlines()
                    if temp_lines and len(temp_lines) > 8:
                        continue

            counselor = DBTCrisisCall(model=args.model, fixed_distress_level=fixed_distress)

            client = DBTClient(
                goal=scenario["goal"],
                behavior=scenario["behavior"],
                profile_description=scenario["description"],
                model=args.model,
            )

            env = Env(
                client=client,
                counselor=counselor,
                output_file=output_file,
                max_turns=args.max_turns,
                initial_context=[
                    "Counselor: Hi, I'm glad you called. How are you doing right now? What's going on?",
                    "Client: I'm... I don't know. Things are just really hard right now.",
                ],
            )

            env.interact()
