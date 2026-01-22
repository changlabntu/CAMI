import os
import re
import random
import time
from typing import Literal, List, Dict, ClassVar
from pydantic import BaseModel, Field, validator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser, PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationSummaryBufferMemory
from .counselor_context import (
    state2instruction, 
    topic2description, 
    strategy2description, 
    topic_graph, 
    system_prompt_template, 
    topic_initialization_prompt, 
    topic_initialization_json_prompt, 
    infer_state_prompt, 
    select_strategy_prompt, 
    topic_explore_prompt, 
    refine_feedback_prompt, 
    refine_prompt,
    response_selection_prompt,
    explore1,
    explore2,
    explore3,
    exploreN,
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# Create LangChain LLM instances with built-in retry logic
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

json_llm = ChatOpenAI(
    model="gpt-4o-2024-08-06",
    temperature=0.2,
    top_p=0.1,
    model_kwargs={"response_format": {"type": "json_object"}},
    max_tokens=150,
    max_retries=3,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

# Pydantic model for state inference
class StateInference(BaseModel):
    """Structured model for client state inference."""
    state: Literal["Precontemplation", "Contemplation", "Preparation"] = Field(
        description="The client's current state in the stages of change model"
    )
    reasoning: str = Field(
        description="Brief explanation of why this state was inferred",
        default=""
    )





# Pydantic model for strategy selection
class StrategySelection(BaseModel):
    """Structured model for counseling strategy selection."""
    # Keep the same hardcoded list for validation (ClassVar means not a field)
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
        """Validate and filter strategies to match hardcoded list."""
        # Filter to only valid strategies (same logic as old parser)
        valid = [s for s in v if s in cls.VALID_STRATEGIES]
        return valid if valid else ["No Strategy"]

# Pydantic model for topic distribution
class TopicDistribution(BaseModel):
    """Structured model for topic distribution."""
    distribution: Dict[str, float] = Field(
        description="Distribution of topic probabilities as a dictionary, e.g., {{'Health': 0.6, 'Economy': 0.3, 'Education': 0.1}}"
    )
    
    @property
    def recommended_topic(self) -> str:
        """Get the topic with highest probability (same logic as old parser)."""
        if self.distribution:
            return max(self.distribution, key=self.distribution.get)
        return "Health"  # Default fallback

# Pydantic model for refinement feedback
class RefinementFeedback(BaseModel):
    """Structured model for response refinement feedback."""
    topic_alignment_score: int = Field(
        description="Score from 0-5 for how well the response aligns with the topic",
        ge=0, le=5
    )
    strategy_adherence_score: int = Field(
        description="Score from 0-5 for how well the response follows the strategy",
        ge=0, le=5
    )
    total_score: int = Field(
        description="Total score out of 10 (sum of topic_alignment_score and strategy_adherence_score)",
        ge=0, le=10
    )
    feedback: str = Field(
        description="Detailed feedback on alignment and adherence"
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

# Create Pydantic output parsers
state_parser = PydanticOutputParser(pydantic_object=StateInference)
strategy_parser = PydanticOutputParser(pydantic_object=StrategySelection)
topic_parser = PydanticOutputParser(pydantic_object=TopicDistribution)
refinement_feedback_parser = PydanticOutputParser(pydantic_object=RefinementFeedback)
refinement_response_parser = PydanticOutputParser(pydantic_object=RefinedResponse)

# Prompt template for analysis (simple text output, no Pydantic parser needed)
topic_initialization_analysis_template = PromptTemplate(
    input_variables=["context", "goal", "behavior", "topics", "response"],
    template=topic_initialization_prompt
)

# Prompt templates with format instructions for Pydantic parsers
state_inference_template = PromptTemplate(
    input_variables=["context"],
    template=infer_state_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": state_parser.get_format_instructions()}
)

strategy_selection_template = PromptTemplate(
    input_variables=["context", "state", "state_instruction"],
    template=select_strategy_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": strategy_parser.get_format_instructions()}
)

topic_initialization_json_template = PromptTemplate(
    input_variables=["context", "goal", "behavior", "topics", "response", "analysis"],
    template=topic_initialization_json_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": topic_parser.get_format_instructions()}
)

topic_explore_template = PromptTemplate(
    input_variables=["context", "goal", "behavior", "topics", "response"],
    template=topic_explore_prompt
)

refinement_feedback_template = PromptTemplate(
    input_variables=["context", "response", "topic", "strategy"],
    template=refine_feedback_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": refinement_feedback_parser.get_format_instructions()}
)

refinement_prompt_template = PromptTemplate(
    input_variables=["context", "response", "topic", "strategy", "feedback"],
    template=refine_prompt + "\n\n{format_instructions}",
    partial_variables={"format_instructions": refinement_response_parser.get_format_instructions()}
)


# Build LangChain Chains with Pydantic parsers
# infer_state()
state_inference_chain = state_inference_template | precise_llm | state_parser

# if no topic is initialized, initialize_topic()
topic_initialization_analysis_chain = topic_initialization_analysis_template | precise_llm | StrOutputParser()
topic_initialization_json_chain = topic_initialization_json_template | json_llm | topic_parser

# if topic is initialized, explore() (explore next topics)

# select_strategy()
strategy_selection_chain = strategy_selection_template | precise_llm | strategy_parser

# generate(last_utterance, topic, state, selected_strategies)

# refine()
refinement_feedback_chain = refinement_feedback_template | precise_llm | refinement_feedback_parser # precise_llm, feedback N times until score > 7
refinement_chain = refinement_prompt_template | chatbot_llm | refinement_response_parser # chatbot_llm, refine response based on feedback (max 3 times)


def openai_2_langchain(messages):
    # Convert OpenAI format messages to LangChain format
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
    
    # Extract token usage from response metadata
    usage = getattr(response, 'usage_metadata', None) or getattr(response, 'response_metadata', {}).get('token_usage', {})
    if usage:
        prompt_tokens = usage.get('input_tokens', 0) or usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('output_tokens', 0) or usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', prompt_tokens + completion_tokens)
        print(f"[counselor.get_llm_response] done in {dur:.2f}s | Tokens: {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total")
    else:
        print(f"[counselor.get_llm_response] done in {dur:.2f}s")
    
    return response.content


class CAMI:
    def __init__(self, goal, behavior, model):
        self.state2instruction = state2instruction
        system_prompt = system_prompt_template.format(goal=goal, behavior=behavior) # (You will act as a skilled counselor conducting....)
        self.topic2description = {
            topic: description.format(behavior=behavior, goal=goal)
            for topic, description in topic2description.items()
        }
        first_counselor = """Counselor: Hello. How are you?"""
        first_client = """Client: I am good. What about you?"""
        # CONTEXT WINDOW: Starts with 3 messages (system + 2-turn greeting exchange)
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": first_counselor},
            {"role": "user", "content": first_client},
        ]
        self.model = model
        self.goal = goal
        self.behavior = behavior
        self.strategy2description = strategy2description
        self.topic_graph = topic_graph
        self.explored_topics = []
        self.topic_stack = []
        self.initialized = False
        
        # Initialize LangChain memory for conversation summarization
        # Keeps recent ~2000 tokens verbatim, summarizes older messages
        self.memory = ConversationSummaryBufferMemory(
            llm=precise_llm,
            max_token_limit=2000,
            return_messages=False,  # Return string format
            memory_key="history"
        )
        
        # Seed memory with initial greeting exchange
        self.memory.save_context(
            {"input": first_client},
            {"output": first_counselor}
        )

    def _get_conversation_text(self):
        """Extract plain text conversation from messages (excluding system prompt)."""
        # CONTEXT WINDOW: All messages (full history, excludes system prompt at index 0)
        return [msg["content"] for msg in self.messages[1:]]

    def infer_state(self):
        """Infer client's state using LangChain chain with structured output."""
        conversation = self._get_conversation_text()  # Full history
        context = "\n- ".join(conversation[-10:])  # CONTEXT WINDOW: Last 10 utterances for state inference
        result = state_inference_chain.invoke({"context": context})
        return result.state  # Extract state from Pydantic model

    def select_strategy(self, state):
        """Select counseling strategies using LangChain chain with structured output."""
        conversation = self._get_conversation_text()  # Full history
        context = "\n".join(conversation)  # CONTEXT WINDOW: All messages (full conversation for strategy selection)
        state_instruction = self.state2instruction[state]
        result = strategy_selection_chain.invoke({
            "context": context,
            "state": state,
            "state_instruction": state_instruction
        })
        # Pydantic validator already filtered to valid strategies
        return result.analysis, result.strategies

    def initialize_topic(self):
        """Initialize topic using LangChain chains."""
        conversation = self._get_conversation_text()  # Full history
        # Prepare input data
        input_data = {
            "context": "\n- ".join(conversation[-6:-1]),  # CONTEXT WINDOW: 5 messages (from -6 to -1, excluding last)
            "goal": self.goal,
            "behavior": self.behavior,
            "topics": " -> ".join(self.explored_topics),
            "response": conversation[-1] # the last message as the most recent client message
        }
        
        # Two stage topic initialization: 1. Reasoning about topic selection, then
        analysis = topic_initialization_analysis_chain.invoke(input_data)
        
        # 2.Get topic distribution with json format
        input_data["analysis"] = analysis
        result = topic_initialization_json_chain.invoke(input_data)
        
        # Extract topic from Pydantic model (uses @property for recommended_topic)
        if result and result.distribution:
            topic = result.recommended_topic  # Uses max() logic in @property
            max_prob = result.distribution.get(topic, 0)
            if max_prob > 0.5 or len(conversation) > 10:
                self.topic_stack.append(topic)
                self.initialized = True
        else:
            topic = random.choice(
                ["Health", "Economy", "Interpersonal Relationships", "Law", "Education"]
            )
        
        return analysis, "Switch", topic

    def explore(self):
        """Explore next topic based on client feedback."""
        conversation = self._get_conversation_text()  # Full history
        # Format base prompt
        prompt = topic_explore_template.format(
            goal=self.goal,
            behavior=self.behavior,
            context="\n- ".join(conversation[-6:-1]),  # CONTEXT WINDOW: 5 messages (from -6 to -1, excluding last)
            response=conversation[-1],  # Most recent client message
            topics=" -> ".join(self.explored_topics)
        )
        
        # Add depth-specific prompt and get topic lists
        topic_config = self._get_topic_config()
        # Format topic lists for prompt (join with newlines)
        formatted_topics = {
            key: "\n    - ".join(value) for key, value in topic_config["topics"].items()
        }
        prompt += topic_config["prompt_template"].format(**formatted_topics)
        
        # Get LLM response
        response = get_llm_response(precise_llm, [{"role": "user", "content": prompt}])
        analysis = response.replace("\n", " ")
        
        # Try actions in priority order: Step Into > Switch > Step Out
        if "step_in_topics" in topic_config["topics"]:
            if self._action_mentioned("Step Into", response):
                topic = self._extract_topic(response, topic_config["topics"]["step_in_topics"])
                if topic:
                    self.topic_stack.append(topic)
                    return analysis, "Step Into", topic
        
        if "switch_topics" in topic_config["topics"]:
            if self._action_mentioned("Switch", response):
                topic = self._extract_topic(response, topic_config["topics"]["switch_topics"])
                if topic:
                    self.topic_stack.pop()
                    self.topic_stack.append(topic)
                    return analysis, "Switch", topic
        
        if "step_out_topics" in topic_config["topics"]:
            if self._action_mentioned("Step Out", response):
                topic = self._extract_topic(response, topic_config["topics"]["step_out_topics"])
                if topic:
                    self.topic_stack.pop()
                    self.topic_stack.pop()
                    self.topic_stack.append(topic)
                    return analysis, "Step Out", topic
        
        # Fallback
        return analysis, "Stay", self.explored_topics[-1] # Stay in the same topic
    
    def _get_topic_config(self):
        """Get prompt template and topic lists based on topic_stack depth."""
        stack_len = len(self.topic_stack)
        
        if stack_len == 1:
            return {
                "prompt_template": explore1,
                "topics": {
                    "step_in_topics": self.topic_graph[self.topic_stack[0]]["Children"].copy(),
                    "switch_topics": ["Health", "Interpersonal Relationships", "Law", "Economy", "Education"]
                }
            }
        elif stack_len == 2:
            return {
                "prompt_template": explore2,
                "topics": {
                    "step_in_topics": self.topic_graph[self.topic_stack[1]]["Children"].copy(),
                    "switch_topics": self.topic_graph[self.topic_stack[0]]["Children"].copy(),
                    "step_out_topics": ["Health", "Interpersonal Relationships", "Law", "Economy", "Education"]
                }
            }
        elif stack_len == 3:
            step_out = self.topic_graph[self.topic_stack[0]]["Children"].copy()
            if step_out:
                return {
                    "prompt_template": explore3,
                    "topics": {
                        "switch_topics": self.topic_graph[self.topic_stack[1]]["Children"].copy(),
                        "step_out_topics": step_out
                    }
                }
            else:
                return {
                    "prompt_template": exploreN,
                    "topics": {
                        "step_out_topics": step_out
                    }
                }
    
    def _extract_topic(self, response, valid_topics):
        """Extract topic from LLM response using multiple strategies."""
        if not valid_topics:
            return None
        
        # Try regex for **topic**
        matches = re.findall(r"\*\*(.*?)\*\*", response)
        if matches and matches[-1] in valid_topics:
            return matches[-1]
        
        # Try second-to-last sentence
        for t in valid_topics:
            if t in response.split(".")[-2]:
                return t
        
        # Try anywhere in response
        for t in valid_topics:
            if t in response:
                return t
        
        # Random fallback
        return random.choice(valid_topics)
    
    def _action_mentioned(self, action, response):
        """Check if action keyword appears in response."""
        return action in response or action.lower() in response

    def refine(self, context, response, strategy, topic):
        """Refine counselor response using LangChain chains with structured output."""
        # CONTEXT WINDOW: the last 5 messages (passed from caller)
        context_str = "\n- ".join(context)
        
        for _ in range(3):
            # Get feedback with structured output
            feedback_result = refinement_feedback_chain.invoke({
                "context": context_str,
                "response": response,
                "topic": topic,
                "strategy": strategy
            })
            
            # Break if score is good enough
            if feedback_result.total_score > 7:
                break
            
            # Refine the response using chain with structured output
            refined_result = refinement_chain.invoke({
                "context": context_str,
                "response": response,
                "topic": topic,
                "strategy": strategy,
                "feedback": f"{feedback_result.feedback}\n\nSuggestions: {feedback_result.suggestions}"
            })
            
            # Extract response from Pydantic model
            response = refined_result.response
            
            # Clean up response format if needed
            if not response.startswith("Counselor:"):
                response = f"Counselor: {response}"
        
        return response

    def generate(self, last_utterance, topic, state, selected_strategies):
        prompt = f"{last_utterance}\nBased on the previous counseling session, generate the response based on the following instruction and strategy: \nThe state of client is {state}, where {self.state2instruction[state]}\nThe client may interest about {topic}. {self.topic2description[topic]}\n"
        candidate_responses = {}
        strategies = {}
        for strategy in selected_strategies:
            temp_prompt = (
                prompt
                + f"The professional counselor suggests using the following strategy:\n- **{strategy}**: {self.strategy2description[strategy]}\nPlease generate one utterance following the suggested strategy and shorter than 50 words."
            )
            self.messages[-1]["content"] = temp_prompt  # Temporarily modify last message
            response = get_llm_response(chatbot_llm, self.messages)  # CONTEXT WINDOW: All messages (full conversation for generation)
            response = " ".join(response.split("\n"))
            response = response.replace("*", "").replace("#", "")
            if not response.startswith("Counselor: "):
                response = f"Counselor: {response}"
            if "Client: " in response:
                response = response.split("Client: ")[0]
            candidate_responses[len(candidate_responses)] = response
            strategies[len(strategies)] = strategy
        temp_prompt = (
            prompt
            + "The professional counselor suggests using the following startegies:\n"
        )
        for strategy in selected_strategies:
            temp_prompt += f"- **{strategy}**: {self.strategy2description[strategy]}\n"
        temp_prompt += "Please generate a response combining all the suggested strategies. The generated utterance should be precise and shorter than 50 words."
        self.messages[-1]["content"] = temp_prompt  # Temporarily modify last message
        response = get_llm_response(chatbot_llm, self.messages)  # CONTEXT WINDOW: All messages (full conversation for combined strategy)
        response = " ".join(response.split("\n"))
        response = response.replace("*", "").replace("#", "")
        if not response.startswith("Counselor: "):
            response = f"Counselor: {response}"
        if "Client: " in response:
            response = response.split("Client: ")[0]
        candidate_responses[len(candidate_responses)] = response
        strategies[len(strategies)] = "Combined Strategies"
        
        # Prepare formatted strings (can't use \n inside f-string expressions)
        conversation = self._get_conversation_text()
        conversation_str = "- " + "\n- ".join(conversation)
        responses_str = "\n".join([f"{i+1}. {response}" for i, response in candidate_responses.items()])
        
        # Format response selection prompt
        response_select_prompt = response_selection_prompt.format(
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
        return candidate_responses[2], strategies[2]

    def receive(self, response):
        # Append client message to conversation history
        self.messages.append({"role": "user", "content": response})

    def reply(self):
        # find state, topic, strategy
        print("[counselor.reply] enter")
        t0 = time.time()
        ## infer_state
        state = self.infer_state() 
        print(f"[counselor.reply] inferred state='{state}' in {time.time()-t0:.2f}s")

        if not self.initialized:
            t1 = time.time()
            ## initialize_topic first
            exploration, action, topic = self.initialize_topic() 
            print(f"[counselor.reply] initialized topic='{topic}', action='{action}' in {time.time()-t1:.2f}s")
        else:
            t1 = time.time()
            ## explore next topic
            exploration, action, topic = self.explore() 
            print(f"[counselor.reply] explored topic='{topic}', action='{action}' in {time.time()-t1:.2f}s")
        self.explored_topics.append(topic)
        ## select_strategy (no more than 2 strategies as defined in select_strategy_prompt)
        t2 = time.time()
        strategy_analysis, selected_strategies = self.select_strategy(state) 
        print(f"[counselor.reply] strategy selected {selected_strategies} in {time.time()-t2:.2f}s")

        # the client's most recent message for continuing conversation
        last_utterance = self.messages[-1]["content"]  # Most recent client utterance

        
        ## generate
        t3 = time.time()
        response, final_strategy = self.generate(
            last_utterance, topic, state, selected_strategies
        ) 
        print(f"[counselor.reply] generated response via '{final_strategy}' in {time.time()-t3:.2f}s")
        if final_strategy == "Combined Strategies":
            if selected_strategies:
                final_strategy = " + ".join(selected_strategies)
                strategy_description = "\n- ".join(
                    [
                        self.strategy2description[s]
                        for s in selected_strategies
                        if s in self.strategy2description
                    ]
                )
            else:
                final_strategy = "No Strategy"
                strategy_description = self.strategy2description["No Strategy"]
        else:
            strategy_description = self.strategy2description.get(
                final_strategy, self.strategy2description["No Strategy"]
            )
        response = response.replace("\n", " ").strip().lstrip()

        ## refine
        t4 = time.time()
        conversation = self._get_conversation_text()  # Full history
        response = self.refine(
            conversation[-5:],  # CONTEXT WINDOW: Last 5 utterances for refinement
            response,
            strategy_description,
            self.topic2description[topic],
        )
        print(f"[counselor.reply] refined response in {time.time()-t4:.2f}s")
        response = response.replace("\n", " ").strip().lstrip()
        self.messages[-1]["content"] = last_utterance  # Restore original client message
        self.messages.append({"role": "assistant", "content": response})  # Append counselor response
        return f"[Inferred State: {state} || Strategy Selection: {strategy_analysis} || Strategies: {selected_strategies} || Final Strategy: {final_strategy} || Topic: {topic} || Exploration Action: {action} || Exploration: {exploration}] {response}"
