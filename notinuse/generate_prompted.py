from agents import Env, CAMI, ClientPrompted
from tqdm import tqdm
import os
import argparse

# Sample profiles as simple text descriptions
SAMPLE_PROFILES = [
    {
        "goal": "increase physical activity",
        "behavior": "avoiding exercise",
        "description": "You are a 45-year-old recovering from a stroke. You are hesitant to exercise because you fear it might cause another health episode. You value your independence but worry about overdoing it."
    },
    {
        "goal": "reduce alcohol consumption",
        "behavior": "drinking heavily on weekends",
        "description": "You are a 32-year-old professional who drinks heavily on weekends to unwind from work stress. You don't think it's a problem because you never drink on weekdays, but your spouse has expressed concern."
    },
    {
        "goal": "improve medication adherence",
        "behavior": "skipping medications",
        "description": "You are a 58-year-old with type 2 diabetes who frequently forgets or skips medications. You feel fine most days and don't see the immediate need for pills. You're skeptical about taking so many medications."
    },
    {
        "goal": "quit smoking",
        "behavior": "smoking a pack a day",
        "description": "You are a 40-year-old who has smoked for 20 years. You've tried quitting before but always relapsed during stressful times. Part of you wants to quit for your kids, but smoking helps you cope with anxiety."
    },
    {
        "goal": "improve diet",
        "behavior": "eating fast food frequently",
        "description": "You are a 28-year-old busy parent who relies on fast food because it's convenient and affordable. You know it's not healthy but feel overwhelmed by the idea of cooking healthy meals every day."
    },
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="OpenAI model to use for the agents")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./Output",
        help="Output directory to save the generated conversations",
    )
    parser.add_argument(
        "--round", type=int, default=1, help="Number of rounds to run the simulation"
    )
    parser.add_argument(
        "--max_turns", type=int, default=20, help="Maximum number of turns for each conversation"
    )
    parser.add_argument(
        "--profile_idx", type=int, default=None, help="Specific profile index to use (if not set, processes all profiles)"
    )

    args = parser.parse_args()

    # Determine which profiles to process
    if args.profile_idx is not None:
        if args.profile_idx < 0 or args.profile_idx >= len(SAMPLE_PROFILES):
            raise ValueError(f"profile_idx {args.profile_idx} is out of range (0-{len(SAMPLE_PROFILES)-1})")
        profile_indices = [args.profile_idx]
    else:
        profile_indices = range(len(SAMPLE_PROFILES))

    os.makedirs(args.output_dir, exist_ok=True)

    for j in range(args.round):
        for i in tqdm(profile_indices, desc=f"Round-{j}"):
            profile = SAMPLE_PROFILES[i]
            output_file = f"{args.output_dir}/Prompted-Sample-{i}-Round-{j}.txt"

            # Skip if already exists and completed
            if os.path.exists(output_file):
                with open(output_file) as f:
                    temp_lines = f.readlines()
                    if temp_lines and len(temp_lines) > 10:
                        continue

            counselor = CAMI(
                goal=profile["goal"],
                behavior=profile["behavior"],
                model=args.model,
            )

            client = ClientPrompted(
                goal=profile["goal"],
                behavior=profile["behavior"],
                profile_description=profile["description"],
                model=args.model,
            )

            env = Env(
                client=client,
                counselor=counselor,
                output_file=output_file,
                max_turns=args.max_turns,
            )

            env.interact()
