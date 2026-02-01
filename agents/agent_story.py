"""
CAMI counselor with evolving client story/portrait.
Maintains a ~200 word narrative about the client that evolves throughout the conversation.
"""

import os
import time
from typing import List, ClassVar
from pydantic import BaseModel, Field, validator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# Create LangChain LLM instances
chatbot_llm = ChatOpenAI(
    model="gpt-4o-2024-08-06",
    temperature=0.7,
    top_p=0.8,
    max_tokens=150,
    max_retries=3,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

precise_llm = ChatOpenAI(
    model="gpt-4o-2024-08-06",
    temperature=0.2,
    top_p=0.1,
    max_tokens=150,
    max_retries=3,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

# LLM for story updates (needs more tokens for ~200 word stories)
story_llm = ChatOpenAI(
    model="gpt-4o-2024-08-06",
    temperature=0.3,
    top_p=0.5,
    max_tokens=400,
    max_retries=3,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)


# Pydantic model for state inference
class StateInference(BaseModel):
    """Structured model for client state inference."""
    state: str = Field(
        description="The client's current state"
    )
    reasoning: str = Field(
        description="Brief explanation of why this state was inferred",
        default=""
    )


# Pydantic model for strategy selection
class StrategySelection(BaseModel):
    """Structured model for counseling strategy selection."""
    VALID_STRATEGIES: ClassVar[List[str]] = [
        "Advise", "Affirm", "Direct", "Emphasize Control", "Facilitate",
        "Inform", "Closed Question", "Open Question", "Raise Concern",
        "Confront", "Simple Reflection", "Complex Reflection", "Reframe",
        "Support", "Warn", "Structure", "No Strategy"
    ]

    strategies: List[str] = Field(
        description="List of selected counseling strategies. Valid options: " + ", ".join(VALID_STRATEGIES)
    )
    analysis: str = Field(
        description="Analysis of the current situation and rationale for strategy selection"
    )

    @validator('strategies')
    def validate_strategies(cls, v):
        valid = [s for s in v if s in cls.VALID_STRATEGIES]
        return valid if valid else ["No Strategy"]


# Pydantic model for refinement feedback
class RefinementFeedback(BaseModel):
    """Structured model for response refinement feedback."""
    strategy_adherence_score: int = Field(
        description="Score from 0-10 for how well the response follows the strategy",
        ge=0, le=10
    )
    feedback: str = Field(
        description="Detailed feedback on strategy adherence"
    )
    suggestions: str = Field(
        description="Concrete suggestions for refinement",
        default=""
    )


# Pydantic model for refined response
class RefinedResponse(BaseModel):
    """Structured model for refined counselor response."""
    response: str = Field(
        description="The refined counselor response, starting with 'Counselor:'"
    )


# Pydantic model for story updates
class StoryUpdate(BaseModel):
    """Structured model for client story updates."""
    updated_story: str = Field(
        description="Updated client story (~200 words)"
    )
    changes_made: str = Field(
        description="Brief summary of what changed in the story"
    )


# Create parsers
state_parser = PydanticOutputParser(pydantic_object=StateInference)
strategy_parser = PydanticOutputParser(pydantic_object=StrategySelection)
refinement_feedback_parser = PydanticOutputParser(pydantic_object=RefinementFeedback)
refinement_response_parser = PydanticOutputParser(pydantic_object=RefinedResponse)
story_update_parser = PydanticOutputParser(pydantic_object=StoryUpdate)

# Simplified refinement prompt (no topic)
refine_feedback_simple_prompt = """Evaluate the following counselor response for strategy adherence.

### Conversation Context:
{context}

### Counselor Response:
{response}

### Strategy Used:
{strategy}

### Evaluation Criteria:
- Does the response follow the suggested counseling strategy?
- Is the response appropriate for the conversation context?
- Is the tone warm, empathetic, and non-judgmental?

Provide a score from 0-10 and specific feedback."""

refine_simple_prompt = """Refine the counselor response based on the feedback.

### Conversation Context:
{context}

### Original Response:
{response}

### Strategy to Follow:
{strategy}

### Feedback:
{feedback}

### Guidelines:
- Keep response under 100 words
- Follow the suggested strategy more closely
- Maintain warm, empathetic tone
- Start with "Counselor:"

### Refined Response:"""

# Story update prompt
story_update_prompt = """Given the conversation so far and the current client portrait, update the portrait to reflect any new information learned about the client.

### Current Portrait:
{current_story}

### Recent Conversation:
{recent_conversation}

### Guidelines:
- Keep the portrait around 200 words
- Incorporate new facts, emotions, or insights revealed
- Remove or revise outdated assumptions
- Maintain narrative coherence
- Focus on: background, situation, emotional state, motivations, barriers
- Preserve the original point of view and writing style (first-person journal style, third-person narrative, etc.)

### Updated Portrait:"""

refinement_feedback_template = PromptTemplate(
    input_variables=["context", "response", "strategy"],
    template=refine_feedback_simple_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": refinement_feedback_parser.get_format_instructions()}
)

refinement_prompt_template = PromptTemplate(
    input_variables=["context", "response", "strategy", "feedback"],
    template=refine_simple_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": refinement_response_parser.get_format_instructions()}
)

story_update_template = PromptTemplate(
    input_variables=["current_story", "recent_conversation"],
    template=story_update_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": story_update_parser.get_format_instructions()}
)

# Build chains
refinement_feedback_chain = refinement_feedback_template | precise_llm | refinement_feedback_parser
refinement_chain = refinement_prompt_template | chatbot_llm | refinement_response_parser
story_update_chain = story_update_template | story_llm | story_update_parser


def openai_2_langchain(messages):
    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
    return lc_messages


def get_llm_response(llm, messages):
    start = time.time()
    lc_messages = openai_2_langchain(messages)
    response = llm.invoke(lc_messages)
    dur = time.time() - start

    usage = getattr(response, 'usage_metadata', None) or getattr(response, 'response_metadata', {}).get('token_usage', {})
    if usage:
        prompt_tokens = usage.get('input_tokens', 0) or usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('output_tokens', 0) or usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
        print(f"[agent_story.get_llm_response] done in {dur:.2f}s | Tokens: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total")
    else:
        print(f"[agent_story.get_llm_response] done in {dur:.2f}s")

    return response.content


class CAMIStory:
    """
    CAMI counselor with evolving client story/portrait.
    Pipeline: State Inference → Strategy Selection → Generate (with story) → Refine → Update Story
    """

    def __init__(self, goal, behavior, model, context="cami", initial_story=""):
        self.context = context
        self.client_story = initial_story
        self.story_changes = ""  # Track what changed in the last update

        # Lazy import based on context
        if context == "crisis":
            from .context_crisis import (
                state2instruction, strategy2description, system_prompt_template,
                infer_state_prompt, select_strategy_prompt, response_selection_prompt
            )
        elif context == "story":
            from .context_story import (
                state2instruction, strategy2description, system_prompt_template,
                infer_state_prompt, select_strategy_prompt, response_selection_prompt
            )
        else:  # default: cami
            from .context_cami import (
                state2instruction, strategy2description, system_prompt_template,
                infer_state_prompt, select_strategy_prompt, response_selection_prompt
            )

        self.state2instruction = state2instruction
        self.strategy2description = strategy2description
        self.response_selection_prompt = response_selection_prompt
        self.valid_strategies = list(strategy2description.keys())

        # Build state inference chain
        state_inference_template = PromptTemplate(
            input_variables=["context"],
            template=infer_state_prompt + "\n\n{format_instructions}",
            partial_variables={"format_instructions": state_parser.get_format_instructions()}
        )
        self.state_chain = state_inference_template | precise_llm | state_parser

        # Build strategy selection chain with context-specific strategies
        context_strategy_parser = self._create_strategy_parser(self.valid_strategies)
        strategy_selection_template = PromptTemplate(
            input_variables=["context", "state", "state_instruction"],
            template=select_strategy_prompt + "\n\n{format_instructions}",
            partial_variables={"format_instructions": context_strategy_parser.get_format_instructions()}
        )
        self.strategy_chain = strategy_selection_template | precise_llm | context_strategy_parser

        system_prompt = system_prompt_template.format(goal=goal, behavior=behavior)

        first_counselor = """Counselor: What's your story today?"""

        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": first_counselor},
        ]
        self.model = model
        self.goal = goal
        self.behavior = behavior

    def _create_strategy_parser(self, valid_strategies):
        """Create a strategy parser with context-specific valid strategies."""
        valid_strategies_list = valid_strategies

        class ContextStrategySelection(BaseModel):
            """Structured model for counseling strategy selection."""
            strategies: List[str] = Field(
                description="List of selected counseling strategies. Valid options: " + ", ".join(valid_strategies_list)
            )
            analysis: str = Field(
                description="Analysis of the current situation and rationale for strategy selection"
            )

            @validator('strategies')
            def validate_strategies(cls, v):
                valid = [s for s in v if s in valid_strategies_list]
                return valid if valid else ["No Strategy"]

        return PydanticOutputParser(pydantic_object=ContextStrategySelection)

    def _get_conversation_text(self):
        """Extract plain text conversation from messages (excluding system prompt)."""
        return [msg["content"] for msg in self.messages[1:]]

    def _update_story(self):
        """Update the client story based on recent conversation."""
        if not self.client_story:
            return  # No story to update

        conversation = self._get_conversation_text()
        recent_conversation = "\n".join(conversation[-6:])  # Last 6 turns (3 exchanges)

        try:
            result = story_update_chain.invoke({
                "current_story": self.client_story,
                "recent_conversation": recent_conversation
            })
            self.client_story = result.updated_story
            self.story_changes = result.changes_made
        except Exception as e:
            print(f"[agent_story._update_story] Error updating story: {e}")
            self.story_changes = "Error updating story"

    def infer_state(self):
        """Infer client's state using LangChain chain with structured output."""
        conversation = self._get_conversation_text()
        context = "\n- ".join(conversation[-10:])
        result = self.state_chain.invoke({"context": context})
        return result.state

    def select_strategy(self, state):
        """Select counseling strategies using LangChain chain with structured output."""
        conversation = self._get_conversation_text()
        context = "\n".join(conversation)
        state_instruction = self.state2instruction.get(state, "Unknown state")
        result = self.strategy_chain.invoke({
            "context": context,
            "state": state,
            "state_instruction": state_instruction
        })
        return result.analysis, result.strategies

    def refine(self, context, response, strategy):
        """Refine counselor response using LangChain chains with structured output."""
        context_str = "\n- ".join(context)

        for _ in range(3):
            feedback_result = refinement_feedback_chain.invoke({
                "context": context_str,
                "response": response,
                "strategy": strategy
            })

            if feedback_result.strategy_adherence_score > 7:
                break

            refined_result = refinement_chain.invoke({
                "context": context_str,
                "response": response,
                "strategy": strategy,
                "feedback": f"{feedback_result.feedback}\n\nSuggestions: {feedback_result.suggestions}"
            })

            response = refined_result.response

            if not response.startswith("Counselor:"):
                response = f"Counselor: {response}"

        return response

    def generate(self, last_utterance, state, selected_strategies):
        """Generate candidate responses for each strategy and select the best one."""
        state_instruction = self.state2instruction.get(state, "Unknown state")

        # Include client story in the prompt if available
        story_context = ""
        if self.client_story:
            story_context = f"\n\n### What we know about this client:\n{self.client_story}\n"

        # Extract recent counselor responses to avoid repetition
        conversation = self._get_conversation_text()
        recent_counselor_responses = [
            msg for msg in conversation[-10:]
            if msg.startswith("Counselor:")
        ][-3:]  # Last 3 counselor responses
        avoid_repetition = ""
        if recent_counselor_responses:
            avoid_repetition = "\n\n### Previous Counselor Responses (DO NOT REPEAT these questions or phrases):\n" + "\n".join(recent_counselor_responses)

        prompt = f"""{last_utterance}
Based on the previous counseling session, generate the response based on the following instruction and strategy:
The client's goal is to {self.goal} regarding {self.behavior}.
The state of client is {state}, where {state_instruction}{story_context}{avoid_repetition}

IMPORTANT: Generate a NEW response that asks different questions or explores different angles than the previous counselor responses shown above.
"""
        candidate_responses = {}
        strategies = {}

        # Generate one response per strategy
        for strategy in selected_strategies:
            temp_prompt = (
                prompt
                + f"The professional counselor suggests using the following strategy:\n- **{strategy}**: {self.strategy2description[strategy]}\nPlease generate one utterance following the suggested strategy and shorter than 100 words."
            )
            self.messages[-1]["content"] = temp_prompt
            response = get_llm_response(chatbot_llm, self.messages)
            response = " ".join(response.split("\n"))
            response = response.replace("*", "").replace("#", "")
            if not response.startswith("Counselor: "):
                response = f"Counselor: {response}"
            if "Client: " in response:
                response = response.split("Client: ")[0]
            candidate_responses[len(candidate_responses)] = response
            strategies[len(strategies)] = strategy

        # Generate combined response
        temp_prompt = prompt + "The professional counselor suggests using the following strategies:\n"
        for strategy in selected_strategies:
            temp_prompt += f"- **{strategy}**: {self.strategy2description[strategy]}\n"
        temp_prompt += "Please generate a response combining all the suggested strategies. The generated utterance should be precise and shorter than 100 words."
        self.messages[-1]["content"] = temp_prompt
        response = get_llm_response(chatbot_llm, self.messages)
        response = " ".join(response.split("\n"))
        response = response.replace("*", "").replace("#", "")
        if not response.startswith("Counselor: "):
            response = f"Counselor: {response}"
        if "Client: " in response:
            response = response.split("Client: ")[0]
        candidate_responses[len(candidate_responses)] = response
        strategies[len(strategies)] = "Combined Strategies"

        # Select best response
        conversation = self._get_conversation_text()
        conversation_str = "- " + "\n- ".join(conversation)
        responses_str = "\n".join([f"{i+1}. {response}" for i, response in candidate_responses.items()])

        response_select_prompt = self.response_selection_prompt.format(
            goal=self.goal,
            behavior=self.behavior,
            conversation=conversation_str,
            responses=responses_str
        )

        response = get_llm_response(
            precise_llm,
            [{"role": "user", "content": response_select_prompt}]
        )
        for i in candidate_responses.keys():
            if str(i + 1) in response:
                return candidate_responses[i], strategies[i]
        return candidate_responses[len(candidate_responses) - 1], strategies[len(strategies) - 1]

    def receive(self, response):
        """Append client message to conversation history."""
        self.messages.append({"role": "user", "content": response})

    def reply(self):
        """Main reply loop: infer state → select strategy → generate → refine → update story."""
        print("[agent_story.reply] enter")
        t0 = time.time()

        # 1. Infer state
        state = self.infer_state()
        print(f"[agent_story.reply] inferred state='{state}' in {time.time()-t0:.2f}s")

        # 2. Select strategy
        t1 = time.time()
        strategy_analysis, selected_strategies = self.select_strategy(state)
        print(f"[agent_story.reply] strategy selected {selected_strategies} in {time.time()-t1:.2f}s")

        last_utterance = self.messages[-1]["content"]

        # 3. Generate response
        t2 = time.time()
        response, final_strategy = self.generate(last_utterance, state, selected_strategies)
        print(f"[agent_story.reply] generated response via '{final_strategy}' in {time.time()-t2:.2f}s")

        if final_strategy == "Combined Strategies":
            if selected_strategies:
                final_strategy = " + ".join(selected_strategies)
                strategy_description = "\n- ".join(
                    [self.strategy2description[s] for s in selected_strategies if s in self.strategy2description]
                )
            else:
                final_strategy = "No Strategy"
                strategy_description = self.strategy2description["No Strategy"]
        else:
            strategy_description = self.strategy2description.get(final_strategy, self.strategy2description["No Strategy"])

        response = response.replace("\n", " ").strip()

        # 4. Refine response
        t3 = time.time()
        conversation = self._get_conversation_text()
        response = self.refine(conversation[-5:], response, strategy_description)
        print(f"[agent_story.reply] refined response in {time.time()-t3:.2f}s")

        response = response.replace("\n", " ").strip()
        self.messages[-1]["content"] = last_utterance
        self.messages.append({"role": "assistant", "content": response})

        # 5. Update client story
        t4 = time.time()
        self._update_story()
        print(f"[agent_story.reply] updated story in {time.time()-t4:.2f}s")

        return f"[Inferred State: {state} || Strategy Analysis: {strategy_analysis} || Strategies: {selected_strategies} || Final Strategy: {final_strategy}] {response}"
