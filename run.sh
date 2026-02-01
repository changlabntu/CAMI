source .env

# Original complex client (state machine based)
# python generate.py --model gpt-4o-mini --retriever_path BAAI/bge-reranker-v2-m3 --profile_path ./annotations/profiles.jsonl --output_dir Output/ --round 5 --max_turns 25 --profile_idx 2
    # GPT model you want to use
    #--model gpt-4o-mini \
    # Retriever model you want to use
    #--retriever_path BAAI/bge-reranker-v2-m3 \
    # Path to the profiles.jsonl file
    #--profile_path ./annotations/profiles.jsonl \
    # Output directory to save the generated conversations
    #--output_dir Output/ \
    # Number of rounds to run the simulation
    #--round 5 \
    # Maximum number of turns of one agent for each conversation
    #--max_turns 25

# Simplified prompted client (LLM-based)
python generate_prompted.py --model gpt-4o-mini --output_dir Output/ --round 1 --max_turns 20

python talk_to_agent.py --agent story --story story/example.txt  --show-metadata --context story --model gpt-4-turbo