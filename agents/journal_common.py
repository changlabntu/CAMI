"""Shared helpers for journal agents (JournalAgent and PinAgent)."""

import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MODELS = {
    "opus": "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-20250514",
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


def describe_emotion(valence: float, support_type: float) -> str:
    """Map valence/support_type floats to natural-language description for the system prompt."""
    if valence < -0.5:
        feeling = "The user is feeling quite distressed or upset."
    elif valence < 0:
        feeling = "The user is feeling somewhat down or troubled."
    elif valence < 0.5:
        feeling = "The user is feeling okay, perhaps mildly positive."
    else:
        feeling = "The user is feeling quite good or positive."

    if support_type < -0.5:
        approach = "They are looking for compassion, empathy, and emotional validation. Focus on listening and reflecting their feelings rather than offering solutions."
    elif support_type < 0:
        approach = "They prefer a more empathetic and supportive approach, leaning toward emotional validation over direct advice."
    elif support_type < 0.5:
        approach = "They are open to some gentle guidance and practical suggestions alongside emotional support."
    else:
        approach = "They are looking for concrete advice, practical strategies, and actionable guidance."

    return f"\n\n{feeling} {approach}"


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
