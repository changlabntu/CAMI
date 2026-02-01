import backoff
import openai
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


@backoff.on_exception(
    backoff.expo,
    (
        openai.RateLimitError,
        openai.Timeout,
        openai.APIError,
        openai.APIConnectionError,
        openai.APIStatusError,
    ),
)
def get_chatbot_response(messages, model="gpt-4o-2024-08-06", temperature=0.7, top_p=0.8, max_tokens=150):
    message = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    return message.choices[0].message.content


SYSTEM_PROMPT_TEMPLATE = """You are a client in a motivational interviewing counseling session.

## Your Situation
{profile_description}

## Session Context
- The counselor is helping you with: {goal}
- Your current behavior: {behavior}

## Response Guidelines
- Respond naturally as this client would
- Keep responses concise (1-3 sentences)
- Show realistic ambivalence about change
- Don't be overly cooperative or overly resistant
- Prefix your response with "Client: "
- Never break character or acknowledge you are an AI
"""


class ClientPrompted:
    def __init__(self, goal, behavior, profile_description, model="gpt-4o-2024-08-06"):
        self.goal = goal
        self.behavior = behavior
        self.profile_description = profile_description
        self.model = model

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            profile_description=profile_description,
            goal=goal,
            behavior=behavior,
        )

        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Counselor: Hello. How are you?"},
            {"role": "assistant", "content": "Client: I am good. What about you?"},
        ]

    def receive(self, counselor_message):
        self.messages.append({"role": "user", "content": counselor_message})

    def reply(self):
        response = get_chatbot_response(self.messages, model=self.model)

        if not response.startswith("Client: "):
            response = f"Client: {response}"

        response = response.replace("\n", " ").strip()

        if "Counselor: " in response:
            response = response.split("Counselor: ")[0].strip()

        self.messages.append({"role": "assistant", "content": response})

        return response
