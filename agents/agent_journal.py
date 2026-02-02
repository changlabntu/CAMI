"""
Journaling agent using CBT's emotion/cognition/behavior triangle.
Asks one question at a time to help users expand their journal entries.
"""

import os
import time
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MODELS = {
    "opus": "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-20250514",
}

SYSTEM_PROMPT = """Act as a psychologist helping me write a structured journal. Using the emotion/cognition/behavior triangle from CBT, ask questions to help me expand the emotional, cognitive, and behavioral aspects of my journal entry. Ask only one question at a time."""

REFRAME_PROMPT = """Based on the journaling conversation below, rewrite the original journal entry to be more complete and insightful. Incorporate the emotions, thoughts, and behaviors that were explored during the session. Write in first person, as if the user is writing their own journal. Keep the personal, authentic voice of the original entry while expanding it with the insights gained.

### Original Journal Entry:
{init_journal}

### Conversation:
{conversation}

### Reframed Journal Entry:"""


def create_llm(model_name="opus"):
    """Create a ChatAnthropic LLM with the specified model."""
    model_id = MODELS.get(model_name.lower(), MODELS["opus"])
    return ChatAnthropic(
        model=model_id,
        temperature=0.7,
        max_tokens=1024,
        max_retries=5,
        api_key=ANTHROPIC_API_KEY
    )


def openai_2_langchain(messages):
    """Convert OpenAI message format to LangChain format."""
    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
    return lc_messages


class JournalAgent:
    def __init__(self, model="opus"):
        self.llm = create_llm(model)
        self.model_name = model
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "Counselor: What would you like to journal about today?"},
        ]
        self.last_metadata = None
        self.init_journal = None

    def receive(self, user_input):
        if self.init_journal is None:
            self.init_journal = user_input
        self.messages.append({"role": "user", "content": user_input})

    def reply(self):
        lc_messages = openai_2_langchain(self.messages)

        start_time = time.time()
        response = self.llm.invoke(lc_messages)
        elapsed_time = time.time() - start_time

        # Extract token usage from response metadata
        usage = response.response_metadata.get("usage", {})
        self.last_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "elapsed_time": elapsed_time,
            "model": self.model_name,
        }

        response_text = response.content
        if not response_text.startswith("Counselor:"):
            response_text = f"Counselor: {response_text}"
        self.messages.append({"role": "assistant", "content": response_text})
        return response_text

    def reframe(self):
        """Reframe the initial journal entry based on the conversation."""
        if not self.init_journal:
            return "No initial journal entry to reframe."

        # Build conversation text (skip system prompt and first assistant greeting)
        conversation_lines = []
        for msg in self.messages[2:]:
            role = "You" if msg["role"] == "user" else "Counselor"
            conversation_lines.append(f"{role}: {msg['content']}")
        conversation = "\n\n".join(conversation_lines)

        prompt = REFRAME_PROMPT.format(
            init_journal=self.init_journal,
            conversation=conversation
        )

        reframe_messages = [{"role": "user", "content": prompt}]
        lc_messages = openai_2_langchain(reframe_messages)

        start_time = time.time()
        response = self.llm.invoke(lc_messages)
        elapsed_time = time.time() - start_time

        usage = response.response_metadata.get("usage", {})
        self.last_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "elapsed_time": elapsed_time,
            "model": self.model_name,
        }

        return response.content
