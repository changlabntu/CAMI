"""Shared helpers for journal agents (JournalAgent and PinAgent)."""

import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MODELS = {
    "opus": "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-20250514",
}

PHASE_COMMANDS = {
    "cbt": ["reframe", "next"],
    "narrative": ["summarize"],
    "finalize": ["end"],
}


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
