import backoff
import openai
from openai import OpenAI
import numpy as np
import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import heapq
import random
from .client_context import action2prompt, state2prompt, topic2description, topic_graph

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
def get_precise_response(messages, model="gpt-4o-2024-08-06", temperature=0.2, top_p=0.1):
    message = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
    )
    return message.choices[0].message.content


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
def get_chatbot_response(
    messages, model="gpt-4o-2024-08-06", temperature=0.7, top_p=0.8, max_tokens=100
):
    message = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=100,
    )
    return message.choices[0].message.content


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
def get_json_response(messages, model="gpt-4o-2024-08-06", temperature=0.2, top_p=0.1):
    message = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        response_format={"type": "json_object"},
    )
    return message.choices[0].message.content


stage2description = {
    "Precontemplation": "The client doesn't think their behavior is problematic.",
    "Contemplation": "The client feels that their behavior is problematic, but still hesitate whether to change.",
    "Preparation": "The client begins discuss about steps toward behavior change.",
}


class Client:
    def __init__(
        self,
        goal,
        behavior,
        reference,
        personas,
        initial_stage,
        final_stage,
        motivation,
        beliefs,
        plans,
        receptivity,
        model,
        wikipedia_dir,
        retriever_path
    ):
        self.goal = goal
        self.behavior = behavior
        self.personas = personas
        self.motivation = motivation[-1]
        self.engagemented_topics = motivation[:-1]
        self.beliefs = beliefs
        self.initial_stage = initial_stage
        self.state = initial_stage
        self.final_stage = final_stage
        self.acceptable_plans = plans
        self.receptivity = receptivity
        self.engagement = receptivity
        self.context = [
            "Counselor: Hello. How are you?",
            "Client: I am good. What about you?",
        ]

        # Initialize client personality and knowledge base
        self.action2prompt = action2prompt  # 12 action type definitions

        self.state2prompt = {
            "Precontemplation": state2prompt["Precontemplation"].format(behavior=self.behavior),
            "Contemplation": state2prompt["Contemplation"].format(behavior=self.behavior, goal=self.goal),
            "Preparation": state2prompt["Preparation"].format(goal=self.goal),
        }

        self.topic2description = {
            topic: description.format(behavior=self.behavior, goal=self.goal)
            for topic, description in topic2description.items()
        }

        # assemble topics
        self.topic_graph = topic_graph
        self.all_topics = []
        for nodes in self.topic_graph:
            if nodes not in self.all_topics:
                self.all_topics.append(nodes)
            for node in self.topic_graph[nodes]:
                if node not in self.all_topics:
                    self.all_topics.append(node)
        self.passages = []
        for topic in self.all_topics:
            with open(os.path.join(wikipedia_dir, topic), "r") as f:
                self.passages.append(self.topic2description[topic] + f.read())
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # retriever
        self.retriever_tokenizer = AutoTokenizer.from_pretrained(
            retriever_path
        )
        self.retriever = AutoModelForSequenceClassification.from_pretrained(
            retriever_path
        ).to(device)
        self.retriever.eval()

        system_prompt = f"""In this role-play scenario, you'll take on the role of a Client discussing about your {self.behavior} where the Counselor's goal is {self.goal}.

Here is your personas which you need to follow consistently throughout the conversation:
[@personas]

Here is a conversation occurs in parallel world between you (Client) and Counselor, where you can follow the style and information provided in the conversation:
{reference}

Please follow these guidelines in your responses:
- **Start your response with "Client: "**
- **Adhere strictly to the state, action and persona specified within square brackets.**
- **Keep your responses coherent and concise, similar to the reference conversation and no more than 3 sentences.**
- **Be natural and concise without being overly polite.**
- **Stick to the persona provided and avoid introducing contradictive details.**
"""
        personas = "- " + "\n- ".join(self.personas) + "\n-".join(self.beliefs)
        system_prompt = system_prompt.replace("[@personas]", personas)
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Counselor: Hello. How are you?"},
            {"role": "assistant", "content": "Client: I am good. What about you?"},
        ]
        self.error_topic_count = 0
        self.model = model

    def verify_motivation(self):
        prompt = """Your task is to evaluate whether the Counselor's responses align with the Client's motivation concerning a specific topic, target (self or others), and aspect (risk or benefit). Determine if the Counselor's statements effectively motivates the Client. Your analysis should be logical, thorough, and well-supported, providing clear analysis at each step.

Here are some examples to help you understand the task better:
## Example 1:
### Input
Here is the conversation snippet toward reducing alcohol consumption:
- Counselor: Hello. How are you?
- Client: I am good. What about you?
- Counselor: I'm doing well, thank you. I understand you wanted to talk about your alcohol consumption. Can you share a bit more about how you're feeling about it?

The Motivation of Client is as follows:
- You are motivated because of the risk of drinking alcohol in relation to depression for yourself, as alcohol could worsen your depression.

Question: Can the Counselor's statement motivate the Client?

### Output
Analysis: The Counselor's initial statement focuses on building rapport and asking the Client to share their feelings about alcohol consumption, but it does not directly address the Client's specific motivation—the risk of alcohol exacerbating depression. Since the Client is motivated by the personal risk of worsening depression, an effective motivational approach would involve acknowledging that risk and connecting it to the Client's emotional or mental health concerns. The Counselor’s statement lacks any mention of the risks or the Client's depression, making it less likely to effectively motivate the Client in this context.
Answer: No


## Example 2:
### Input
Here is the conversation snippet toward reducing alcohol consumption:
- Counselor: Are you surprised what that might be true?
- Client: Yeah, and a couple of my friends drink too.
- Counselor: Well, you might not be drinking that much, and other kids are also trying alcohol. I'd like to share with you the risk of using. Alcohol and drugs could really harm you because your brain is still changing. It also-- you're very high risk for becoming addicted. Alcohol and drugs could also interfere with your role in life and your goals, especially in sports, and it could cause unintended sex. How do you feel about this information?

The Motivation of Client is as follows:
- You are motivated because of the risk of drinking alcohol in sports for yourself, as alcohol would affect your ability to play soccer.

Question: Can the Counselor's statement motivate the Client?

### Output
Analysis: The Counselor's statement addresses various risks associated with alcohol use, including its potential impact on the Client’s role in life and goals, particularly in sports. Since the Client's motivation revolves around the risk of alcohol affecting their ability to play soccer, the Counselor’s mention of how alcohol could interfere with sports aligns with the Client's concern. By highlighting this specific risk, the Counselor's statement effectively taps into the Client’s personal motivation, making it more likely to encourage behavior change.
Answer: Yes


## Example 3:
### Input
Here is the conversation snippet toward reducing alcohol consumption:
- Counselor: It sounds like you're considering making some changes around your alcohol consumption. What makes you think it might be good to cut back?
- Client: I guess I just want to be more mindful of my health and well-being.
- Counselor: It sounds like you're considering making some positive changes for your health. What are some reasons that are motivating you to cut back on alcohol?

The Motivation of Client is as follows:
- You are motivated because of the risk of drinking alcohol in relation to depression for yourself, as alcohol could worsen your depression.

Question: Can the Counselor's statement motivate the Client?

### Output
Analysis: While the Counselor’s statement touches on the Client’s general motivation to improve their health, it does not specifically address the Client's key motivation—the risk of alcohol worsening their depression. The Counselor asks broad questions about the Client’s reasons for cutting back on alcohol, but fails to connect directly to the Client’s concern about depression, which is a central aspect of their motivation. For the statement to effectively motivate the Client, it would need to focus more on the specific risk of alcohol impacting their mental health.
Answer: No

## Example 4:
### Input
Here is the conversation snippet toward reducing alcohol consumption:
- Counselor: It seems like you're concerned about staying productive at work, but drinking regularly could have some negative effects. Alcohol can make it harder to stay focused and might even cause you to miss deadlines or make mistakes. Have you noticed any of those risks affecting your productivity?
- Counselor: Not really, I still get my work done, and I don’t feel like my drinking is hurting my performance. I mean, I can still function well enough, so I don’t think it’s a problem.
- Counselor: That makes sense, but over time, regular drinking can slowly take a toll on your ability to perform at your best. You might not notice it now, but it could lead to more mistakes or slower work in the future. Are you worried that alcohol could start to interfere with your productivity in the long run?

The Motivation of Client is as follows:
- You are motivated because of the benefit of reducing alcohol consumption in terms of productivity for yourself, as you feel more productive when you don’t have a hangover.

Question: Can the Counselor's statement motivate the Client?

### Output
Analysis:The Client is motivated by the benefit of increased productivity without alcohol, but the Counselor focuses on the risk of future productivity loss from drinking. The Counselor’s focus on potential risks doesn't align with the Client's motivation, which is based on the immediate benefit of feeling more productive when avoiding alcohol. To be more effective, the Counselor should have highlighted the benefit the Client already experiences.
Answer: No

Now, Here is the conversation snippet toward [@goal]:
- [@context]

The Motivation of Client is as follows:
- [@motivation]

Question: Can the Counselor's statement motivate the Client?

#### Output
"""
        prompt = prompt.replace("[@goal]", self.goal)
        prompt = prompt.replace("[@context]", "\n- ".join(self.context[-5:]))
        prompt = prompt.replace("[@motivation]", self.motivation)
        response = get_precise_response(
            messages=[{"role": "user", "content": prompt}], model=self.model
        )
        if "yes" in response.lower():
            self.state = "Motivation"
        return response.split("\n")[0].split(": ")[-1]

    def top5_related_topics(self):
        query = self.context[-1].split("Counselor: ")[-1]
        queries = [query] * len(self.all_topics)
        query_evids = zip(queries, self.passages)
        with torch.no_grad():
            inputs = self.retriever_tokenizer(
                list(query_evids),
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            )
            inputs = {k: v.to(self.retriever.device) for k, v in inputs.items()}
            batch_scores = (
                self.retriever(**inputs, return_dict=True)
                .logits.view(
                    -1,
                )
                .float()
            )
            scores_sigmoid = torch.sigmoid(batch_scores)
            scores = scores_sigmoid.tolist()
        top_5_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:5]
        top5_topics = [self.all_topics[idx] for idx in top_5_indices]
        return top5_topics

    def dijkstra(self, graph, start_node, target_node):
        # Initialize distances dictionary with infinity for all nodes
        distances = {node: float("infinity") for node in graph}
        distances[start_node] = 0

        # Priority queue to store (distance, node)
        pq = [(0, start_node)]

        # Keep track of visited nodes
        visited = set()

        while pq:
            # Get node with minimum distance
            current_distance, current_node = heapq.heappop(pq)

            # If we reached target node, return the distance
            if current_node == target_node:
                return current_distance

            # Skip if we've already visited this node
            if current_node in visited:
                continue

            visited.add(current_node)

            # Check all neighbors
            for neighbor, weight in graph[current_node].items():
                if neighbor not in visited:
                    distance = current_distance + weight

                    # If we found a shorter path, update it
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        heapq.heappush(pq, (distance, neighbor))

        # If no path found
        return float("infinity")

    def update_state(self):
        if self.state == "Contemplation":
            if len(self.beliefs) == 0:
                self.state = "Preparation"
            return
        elif self.state == "Preparation":
            return
        else:
            top_topics = self.top5_related_topics()
            predicted_topic = top_topics[0]
            if predicted_topic == self.engagemented_topics[0]:
                self.engagement = 4
                self.error_topic_count = 0
                motivation_analysis = self.verify_motivation()
                return motivation_analysis
            distance = self.dijkstra(
                self.topic_graph, self.engagemented_topics[0], predicted_topic
            )
            if distance <= 3:
                self.engagement = 3
                self.error_topic_count = 0
                return f"The client's perceived topic is {predicted_topic}."
            if distance <= 5:
                self.engagement = 2
                return f"The client's perceived topic is {predicted_topic}."
            else:
                self.engagement = 1
                if len(self.context) > 10:
                    self.error_topic_count += 1
                return f"The client's perceived topic is {predicted_topic}."

    def select_action(self):
        prompt = """Assume you are a Client involved in a counseling conversation. The current conversation is provided below:
[@context]

Based on the context, allocate probabilities to each of the following dialogue actions to maintain coherence:
- Deny: The client should directly refuse to admit their behavior is problematic or needs change without additional reasons.
- Downplay: The client should downplay the importance or impact of their behavior or situation.
- Blame: The client should blame external factors or others to justify their behavior.
- Inform: The client should share details about their background, experiences, or emotions.
- Engage: The client interacts politely with the counselor, such as greeting or thanking.

Provide your response in JSON format, ensuring that the sum of all probabilities equals 100. For example: {'Deny': 35, 'Downplay': 25, 'Blame': 25, 'Inform': 5, 'Engage': 10}
"""
        prompt = prompt.replace(
            "[@context]",
            "\n".join(self.context[-3:])
            .replace("Client:", "**Client**:")
            .replace("Counselor:", "**Counselor**:"),
        )
        context_aware_action_distribution = None
        for _ in range(5):
            response = get_json_response(
                messages=[{"role": "user", "content": prompt}], model=self.model
            )
            response = response.replace("```", "").replace("json", "")
            try:
                context_aware_action_distribution = eval(response)
            except SyntaxError:
                continue
            if context_aware_action_distribution:
                break
        if not context_aware_action_distribution:
            context_aware_action_distribution = {
                "Deny": 20,
                "Downplay": 20,
                "Blame": 20,
                "Engage": 20,
                "Inform": 20,
            }
        if self.receptivity < 2:
            receptivity_aware_action_distribution = {
                "Deny": 23,
                "Downplay": 28,
                "Blame": 15,
                "Engage": 11,
                "Inform": 22,
            }
        elif self.receptivity < 3:
            receptivity_aware_action_distribution = {
                "Deny": 20,
                "Downplay": 25,
                "Blame": 10,
                "Engage": 15,
                "Inform": 30,
            }
        elif self.receptivity < 4:
            receptivity_aware_action_distribution = {
                "Deny": 19,
                "Downplay": 21,
                "Blame": 11,
                "Engage": 13,
                "Inform": 36,
            }
        elif self.receptivity < 5:
            receptivity_aware_action_distribution = {
                "Deny": 9,
                "Downplay": 20,
                "Blame": 13,
                "Engage": 14,
                "Inform": 44,
            }
        else:
            receptivity_aware_action_distribution = {
                "Deny": 7,
                "Downplay": 13,
                "Blame": 4,
                "Engage": 16,
                "Inform": 60,
            }
        action_distribution = {
            action: context_aware_action_distribution.get(action, 0)
            + receptivity_aware_action_distribution[action]
            for action in receptivity_aware_action_distribution
        }
        if len(self.personas) == 0:
            action_distribution["Inform"] = 0
        if len(self.beliefs) == 0:
            action_distribution["Blame"] = 0
        # normalize
        action_distribution = {
            k: v / sum(action_distribution.values())
            for k, v in action_distribution.items()
        }
        sampled_action = np.random.choice(
            list(action_distribution.keys()),
            size=1,
            p=list(action_distribution.values()),
        )[0]
        return sampled_action

    def select_information(self, action):
        messages = []
        if "?" not in self.context[-1]:
            return None
        prompt = """Here is a conversation between Client and Counselor:
[@conv]

Is there a question in the last utterance of Counselor? Yes or No"""
        prompt = prompt.replace("[@conv]", "\n".join(self.context[-3:]))
        response = "Yes, there is a question in the last utterance of Counselor."
        messages.append({"role": "user", "content": prompt})
        messages.append({"role": "assistant", "content": response})
        if action == "Inform":
            prompt2 = """Can the following Client's persona answer the question? Yes or No
[@persona]"""
            personas = self.personas
        elif action == "Downplay":
            prompt2 = """Can the following Client's persona reply the question to downplay the importance or impact of behavior? Yes or No
[@persona]"""
            personas = self.beliefs
        elif action == "Blame":
            prompt2 = """Can the following Client's persona reply the question to blame external factors or others to justify? Yes or No
[@persona]"""
            personas = self.beliefs
        elif action == "Hesitate":
            prompt2 = """Can the following Client's persona reply the question to show uncertainty, indicating ambivalence about change? Yes or No
[@persona]"""
            personas = self.beliefs
        for persona in personas:
            prompt = prompt2.replace("[@persona]", persona)
            messages.append({"role": "user", "content": prompt})
            response = get_precise_response(messages=messages, model=self.model)
            messages.append({"role": "assistant", "content": response})
            if "yes" in response.lower():
                if action == "Hesitate":
                    personas.pop(personas.index(persona))
                return persona
        persona = random.choice(personas)
        if action == "Hesitate":
            personas.pop(personas.index(persona))
        return persona

    def receive(self, response):
        self.context.append(response)

    def get_engage_instruction(self):
        if self.engagement == 1:
            return "You should provide vague and broad answers that avoid focusing on the current topic. Shift the conversation subtly toward unrelated areas, without engaging deeply with the topic."
        elif self.engagement == 2:
            return f"Acknowledge the importance of {self.engagemented_topics[2]}, but hint that your focus is on a more specific topic, i.e. {self.engagemented_topics[1]} within it."
        elif self.engagement == 3:
            return f"Engage more directly with {self.engagemented_topics[1]}, and offer responses that subtly indicate there’s a deeper, more specific issue worth exploring within that topic, i.e. {self.engagemented_topics[0]}."
        elif self.engagement == 4:
            return f"Offer specific responses that affirm the counselor is on the right track, showing that you're motivated by {self.engagemented_topics[0]}. {self.motivation}"

    def reply(self):
        engagement_analysis = self.update_state()
        information = None
        if self.state == "Motivation":
            engage_instruction = f"Offer specific responses that affirm the counselor is on the right track, showing that you're motivated by {self.engagemented_topics[0]}."
            instruction = f"[{self.motivation} {self.action2prompt['Acknowledge']} {engage_instruction}]"
            output_instruction = f"[Engagement: {engage_instruction} || Motivation: {self.motivation} || Action: {self.action2prompt['Acknowledge']}]"
            self.state = "Contemplation"
            action = "Acknowledge"
        elif self.state == "Precontemplation":
            engage_instruction = self.get_engage_instruction()
            if self.error_topic_count >= 5:
                action = "Terminate"
            else:
                action = self.select_action()
            if action == "Inform" or action == "Downplay" or action == "Blame":
                information = self.select_information(action)
                instruction = f"[{engage_instruction} {self.state2prompt[self.state]} {self.action2prompt[action]} You should follow the persona: {information} Don't show overknowledge and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"[Engage Instruction: {engagement_analysis} {engage_instruction} || State Instruction: {self.state2prompt[self.state]} || Information: {information} || Action Instruction: {self.action2prompt[action]}]"
            else:
                instruction = f"[{engage_instruction} {self.state2prompt[self.state]} {self.action2prompt[action]} Don't show overknowledge and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"[Engage Instruction: {engagement_analysis} {engage_instruction} || State Instruction: {self.state2prompt[self.state]} || Action Instruction: {self.action2prompt[action]}]"
        elif self.state == "Contemplation":
            action = self.select_action()
            if action == "Hesitate" or action == "Inform":
                information = self.select_information(action)
                instruction = f"[{self.state2prompt[self.state]} {self.action2prompt[action]} You should follow the persona: {information} Don't show overknowledge and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"[State Instruction: {self.state2prompt[self.state]} || Information: {information} || Action Instruction: {self.action2prompt[action]}]"
            else:
                instruction = f"[{self.state2prompt[self.state]} {self.action2prompt[action]} Don't show overknowledge and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"[State Instruction: {self.state2prompt[self.state]} || Action Instruction: {self.action2prompt[action]}]"
        else:
            if len(self.acceptable_plans) == 0:
                action = "Terminate"
            else:
                action = self.select_action()
            if action == "Inform":
                information = self.select_information(action)
                instruction = f"[{self.state2prompt[self.state]} {self.action2prompt[action]} You should follow the persona: {information} Don't show overknowledge and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"[State Instruction: {self.state2prompt[self.state]} || Information: {information} || Action Instruction: {self.action2prompt[action]}]"
            if action == "Plan":
                information = self.acceptable_plans.pop(0)
                instruction = f"[{self.state2prompt[self.state]} {information} {self.action2prompt[action]} Don't show overknowledge, and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"State Instruction: {self.state2prompt[self.state]} || Information: {information} || Action Instruction: {self.action2prompt[action]}]"
            else:
                instruction = f"[{self.state2prompt[self.state]} {self.action2prompt[action]} Don't show overknowledge, and keep your responses concise (no more than 50 words). Don't highlight your state explicitly.]"
                output_instruction = f"[State Instruction: {self.state2prompt[self.state]} || Action Instruction: {self.action2prompt[action]}]"
        instruction = instruction.replace("\n", " ")
        output_instruction = output_instruction.replace("\n", " ")
        self.messages.append(
            {"role": "user", "content": f"{self.context[-1]} {instruction}"}
        )
        response = get_chatbot_response(self.messages, model=self.model)
        if not response.startswith("Client: "):
            response = f"Client: {response}"
        response = response.replace("\n", " ").strip().lstrip()
        if "Counselor: " in response:
            response = response.split("Counselor: ")[0]
        self.messages.pop(-1)
        self.messages.append({"role": "user", "content": self.context[-1]})
        self.context.append(response)
        self.messages.append({"role": "assistant", "content": response})
        return f"{output_instruction} {response}"
