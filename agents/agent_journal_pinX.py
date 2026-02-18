"""
Journaling agent using CBT's emotion/cognition/behavior triangle.
"""

import os
import time

from .journal_common import MODELS, create_llm, openai_2_langchain


def load_prompts():
    """Load prompts from journal_prompt.txt file."""
    """Format: [SECTION_NAME]
    Section content
    """
    prompt_file = os.path.join(os.path.dirname(__file__), "journal_prompt.txt")
    with open(prompt_file, "r") as f:
        content = f.read()

    # Parse the sections
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


_prompts = load_prompts()
SYSTEM_PROMPT = _prompts["SYSTEM_PROMPT"]
REFRAME_PROMPT = _prompts["REFRAME_PROMPT"]
NARRATIVE_PROMPT = _prompts["NARRATIVE_PROMPT"]
SUMMARIZE_PROMPT = _prompts["SUMMARIZE_PROMPT"]
FEEDBACK_PROMPT = _prompts["FEEDBACK_PROMPT"]


class JournalAgent:
    def __init__(self, model="opus"):
        self.llm = create_llm(model)
        self.model_name = model
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "Counselor: 今天想寫些什麼呢？"},
        ]
        self.last_metadata = None
        self.init_journal = None
        self.reframed_journal = None
        self.final_summary = None
        self.narrative_messages = []
        self.phase = "cbt"

    @property
    def _current_messages(self):
        """Return the message list for the current phase."""
        if self.phase == "narrative":
            return self.narrative_messages
        elif self.phase == "finalize":
            return self.finalize_messages
        return self.messages

    def _invoke(self, messages):
        """Invoke LLM and record metadata. Returns the response content string."""
        lc_messages = openai_2_langchain(messages)
        start_time = time.time()
        response = self.llmstart_narrative.invoke(lc_messages)
        elapsed_time = time.time() - start_time

        usage = response.response_metadata.get("usage", {})
        self.last_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "elapsed_time": elapsed_time,
            "model": self.model_name,
        }
        return response.content

    def receive(self, user_input):
        """Store user input into the current phase's message list."""
        if self.phase == "cbt" and self.init_journal is None:
            self.init_journal = user_input
        self._current_messages.append({"role": "user", "content": user_input})

    def reply(self):
        """Generate and return an LLM reply for the current phase."""
        msgs = self._current_messages
        response_text = self._invoke(msgs)
        msgs.append({"role": "assistant", "content": response_text})
        return response_text

    def reframe(self):
        """Reframe the initial journal entry based on the conversation."""
        if not self.init_journal:
            return "沒有初始日記可以整理。"

        # Build conversation text (skip system prompt and first assistant greeting)
        conversation_lines = []
        for msg in self.messages[2:]:
            role = "You" if msg["role"] == "user" else "Agent"
            conversation_lines.append(f"{role}: {msg['content']}")
        conversation = "\n\n".join(conversation_lines)

        prompt = REFRAME_PROMPT.format(
            init_journal=self.init_journal,
            conversation=conversation
        )

        reframe_messages = [{"role": "user", "content": prompt}]
        reframed = self._invoke(reframe_messages)
        self.reframed_journal = reframed
        return reframed

    def start_narrative(self, reframed_journal=None):
        """Start the narrative therapy session with the reframed journal.

        Args:
            reframed_journal: Optional. If provided, use this instead of the one from reframe().
                              Useful for testing the narrative part directly.
        """
        self.phase = "narrative"
        if reframed_journal:
            self.reframed_journal = reframed_journal

        if not self.reframed_journal:
            return "沒有可用的整理日記。請先完成整理步驟或提供一份日記。"

        # Store the original reframed journal for use in feedback
        self.origin_reframed_journal = self.reframed_journal

        # Initialize narrative messages with the reframed journal as context
        system_content = f"{NARRATIVE_PROMPT}\n\n### Reframed Journal:\n{self.reframed_journal}"
        self.narrative_messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "讓我們更深入地探索這個故事。"},
        ]

        # Get the first question from the LLM
        response_text = self._invoke(self.narrative_messages)
        self.narrative_messages.append({"role": "assistant", "content": response_text})
        return response_text

    def summarize(self):
        """Generate a reflection summary based on the narrative therapy conversation."""
        if not self.reframed_journal:
            return "沒有可用的整理日記。"

        # Build conversation text (skip system prompt and first user kickoff)
        conversation_lines = []
        for msg in self.narrative_messages[2:]:
            role = "You" if msg["role"] == "user" else "Agent"
            conversation_lines.append(f"{role}: {msg['content']}")
        conversation = "\n\n".join(conversation_lines)

        prompt = SUMMARIZE_PROMPT.format(
            reframed_journal=self.reframed_journal,
            conversation=conversation
        )

        summarize_messages = [{"role": "user", "content": prompt}]
        summary = self._invoke(summarize_messages)
        self.final_summary = summary
        return summary

    def finalize(self, title):
        """Start the finalize phase - ask about current emotion."""
        self.phase = "finalize"
        if not hasattr(self, 'final_summary') or not self.final_summary:
            return "沒有可用的摘要來完成。"

        self.journal_title = title
        origin_story = getattr(self, 'origin_reframed_journal', self.reframed_journal) or ""

        system_content = FEEDBACK_PROMPT.format(
            title=title,
            origin_story=origin_story,
            summary=self.final_summary
        )
        self.finalize_messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"我把日記取名為「{title}」。"},
        ]

        response_text = self._invoke(self.finalize_messages)
        self.finalize_messages.append({"role": "assistant", "content": response_text})
        return response_text
