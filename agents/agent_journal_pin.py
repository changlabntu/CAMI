"""
Refactored journal agent: two reusable helpers, minimal abstraction.
"""

import os
import time
from typing import Literal

from .journal_common import MODELS, create_llm, openai_2_langchain

Phase = Literal["cbt", "narrative", "finalize"]


def load_prompts():
    """Load prompts from journal_prompt.txt file."""
    """Format: [SECTION_NAME]
    Section content"""
    prompt_file = os.path.join(os.path.dirname(__file__), "journal_prompt.txt")
    with open(prompt_file, "r") as f:
        content = f.read()

    sections = {}
    current_section = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("[") and line.endswith("]"):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line[1:-1]
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def build_conversation_text(messages: list[dict], skip: int = 2) -> str:
    """Turn a message list into a readable transcript, skipping the first `skip` messages."""
    lines = []
    for msg in messages[skip:]:
        role = "You" if msg["role"] == "user" else "Agent"
        lines.append(f"{role}: {msg['content']}")
    return "\n\n".join(lines)


class LLMService:
    """Wraps a LangChain chat model."""

    def __init__(self, llm, model_name: str):
        self.llm = llm
        self.model_name = model_name
        self.last_metadata: dict | None = None

    def invoke(self, messages: list[dict]) -> str:
        """Call LLM with a list of messages."""
        lc_messages = openai_2_langchain(messages)
        start = time.time()
        response = self.llm.invoke(lc_messages)
        elapsed = time.time() - start

        usage = response.response_metadata.get("usage", {})
        self.last_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "elapsed_time": elapsed,
            "model": self.model_name,
        }
        return response.content


class OneShotPhase:
    """Call LLM once with a formatted prompt, return the result."""

    def __init__(self, llm: LLMService, prompt_template: str):
        self.llm = llm
        self.prompt_template = prompt_template

    def execute(self, **kwargs) -> str:
        """Call LLM with a formatted prompt."""
        """ kwargs are passed to the prompt template """
        prompt = self.prompt_template.format(**kwargs)
        return self.llm.invoke([{"role": "user", "content": prompt}])


class ConversationPhase:
    """Maintain a multi-turn conversation with system prompt."""

    def __init__(self, llm: LLMService):
        self.llm = llm
        self.messages: list[dict] = []

    def start(self, system_content: str, first_user_msg: str) -> str:
        self.messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": first_user_msg},
        ]
        response = self.llm.invoke(self.messages)
        self.messages.append({"role": "assistant", "content": response})
        return response

    def receive(self, user_input: str) -> None:
        self.messages.append({"role": "user", "content": user_input})

    def reply(self) -> str:
        response = self.llm.invoke(self.messages)
        self.messages.append({"role": "assistant", "content": response})
        return response


class JournalAgent:
    def __init__(self, model="opus"):
        llm = LLMService(create_llm(model), model)
        prompts = load_prompts()
        self.llm = llm
        self.prompts = prompts

        # Shared state
        self.init_journal: str | None = None
        self.reframed_journal: str | None = None
        self.final_summary: str | None = None
        self.phase: Phase = "cbt"

        # CBT phase messages
        self.cbt_messages: list[dict] = [
            {"role": "system", "content": prompts["SYSTEM_PROMPT"]},
            {"role": "assistant", "content": "Counselor: 今天想寫些什麼呢？"},
        ]

        # Reusable phase objects
        self.reframe_phase = OneShotPhase(llm, prompts["REFRAME_PROMPT"])
        self.summarize_phase = OneShotPhase(llm, prompts["SUMMARIZE_PROMPT"])
        self.narrative_phase = ConversationPhase(llm)
        self.finalize_phase = ConversationPhase(llm)

    @property
    def last_metadata(self):
        return self.llm.last_metadata

    @property
    def messages(self):
        return self.cbt_messages

    @property
    def _active_conversation(self) -> ConversationPhase | None:
        if self.phase == "narrative":
            return self.narrative_phase
        if self.phase == "finalize":
            return self.finalize_phase
        return None

    def receive(self, user_input: str) -> None:
        if self.phase == "cbt":
            if self.init_journal is None:
                self.init_journal = user_input
            self.cbt_messages.append({"role": "user", "content": user_input})
        elif conv := self._active_conversation:
            conv.receive(user_input)

    def reply(self) -> str:
        if conv := self._active_conversation:
            return conv.reply()
        # CBT phase
        response = self.llm.invoke(self.cbt_messages)
        self.cbt_messages.append({"role": "assistant", "content": response})
        return response

    def reframe(self) -> str:
        if not self.init_journal:
            return "沒有初始日記可以整理。"

        conversation = build_conversation_text(self.cbt_messages)
        self.reframed_journal = self.reframe_phase.execute(
            init_journal=self.init_journal,
            conversation=conversation,
        )
        return self.reframed_journal

    def start_narrative(self, reframed_journal: str | None = None) -> str:
        if reframed_journal:
            self.reframed_journal = reframed_journal
        if not self.reframed_journal:
            return "沒有可用的整理日記。請先完成整理步驟或提供一份日記。"

        self.phase = "narrative"
        self.origin_reframed_journal = self.reframed_journal
        system = f"{self.prompts['NARRATIVE_PROMPT']}\n\n### Reframed Journal:\n{self.reframed_journal}"
        return self.narrative_phase.start(system, "讓我們更深入地探索這個故事。")

    def summarize(self) -> str:
        if not self.reframed_journal:
            return "沒有可用的整理日記。"

        conversation = build_conversation_text(self.narrative_phase.messages)
        self.final_summary = self.summarize_phase.execute(
            reframed_journal=self.reframed_journal,
            conversation=conversation,
        )
        return self.final_summary

    def finalize(self, title: str) -> str:
        if not self.final_summary:
            return "沒有可用的摘要來完成。"

        self.journal_title = title
        self.phase = "finalize"
        origin_story = getattr(self, "origin_reframed_journal", self.reframed_journal) or ""
        system = self.prompts["FEEDBACK_PROMPT"].format(
            title=title,
            origin_story=origin_story,
            summary=self.final_summary,
        )
        return self.finalize_phase.start(system, f"我把日記取名為「{title}」。")