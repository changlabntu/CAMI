# Narrative Therapy Crisis Counselor context data structures and prompts
# Adapted from DBT template - focused on narrative approaches to crisis intervention

# Story State definitions based on narrative therapy principles
# Journal entry states - the mood/nature of what the user is writing about
# Journal entry types - what is the user bringing today?
state2instruction = {
    "sharing_something_hard": "The user is writing about something difficult - a bad day, conflict, disappointment, stress. Acknowledge the weight of it first. Then, if it feels right, offer one gentle question or reflection that helps them process.",
    "sorting_through_feelings": "The user is trying to untangle or understand how they feel. Be a calm mirror. Reflect back what you're hearing and maybe ask one question that helps them go a bit deeper.",
    "celebrating_a_win": "The user is sharing something good - an accomplishment, a nice moment, something they're proud of. Help them savor it. Ask what made it possible or what it meant to them.",
    "feeling_grateful": "The user is noticing things they appreciate. Warmly receive this. You might ask what made them notice this today, or simply reflect the goodness back.",
    "working_through_a_decision": "The user is thinking through a choice or problem. Don't solve it for them. Ask questions that help them hear their own thinking - what feels important? What are they torn between?",
    "noticing_something_about_themselves": "The user is having a small insight or realization about who they are, how they work, or what they want. Encourage this. Reflect it back and ask what this might mean for them.",
    "low_energy_or_blank": "The user doesn't have much to say, or the entry feels flat. That's okay. Gently offer a simple prompt - one small thing from today, or how their body feels right now.",
    "needing_comfort": "The user seems sad, lonely, or emotionally heavy. Warmth first, questions later (or not at all). Sometimes just being heard is enough. If it seems serious, gently encourage them to reach out to someone.",
}

strategy2description = {
    "Advise": "Give advice, makes a suggestion, offers a solution or possible action. For example, 'Consider starting with small, manageable changes like taking a short walk daily.'",
    "Affirm": "Say something positive or complimentary to the client. For example, 'You did well by seeking help.'",
    "Direct": "Give an order, command, direction. The language is imperative. For example, 'You've got to stop drinking.'",
    "Emphasize Control": "Directly acknowledges or emphasizes the client's freedom of choice, autonomy, ability to decide, personal responsibility, etc. For example, 'It's up to you to decide whether to drink.'",
    "Facilitate": "Provide simple utterances that function as 'keep going' acknowledgments encouraging the client to keep sharing. For example, 'Tell me more about that.'",
    "Inform": "Give information to the client, explains something, or provides feedback. For example, 'This is a hormone that helps your body utilize sugar.'",
    "Closed Question": "Ask a question in order to gather information, understand, or elicit the client's story. The question implies a short answer: Yes or no, a specific fact, a number, etc. For example, 'Did you use heroin this week?'",
    "Open Question": "Ask a question in order to gather information, understand, or elicit the client's story. The question should be not closed questions, that leave latitude for response. For example, 'Can you tell me more about your drinking habits?'",
    "Raise Concern": "Point out a possible problem with a client's goal, plan, or intention. For example, 'What do you think about my plan?'",
    "Confront": "Directly disagrees, argues, corrects, shames, blames, seeks to persuade, criticizes, judges, labels, moralizes, ridicules, or questions the client's honesty. For example, 'What makes you think that you can get away with it?'",
    "Simple Reflection": "Make a statement that reflects back content or meaning previously offered by the client, conveying shallow understanding without additional information. Add nothing at all to what the client has said, but simply repeat or restate it using some or all of the same words. For example, 'You don't want to do that.'",
    "Complex Reflection": "Make a statement that reflects back content or meaning previously offered by the client, conveying deep understanding with additional information. Change or add to what the client has said in a significant way, to infer the client's meaning. For example, 'That's where you drew the line.'",
    "Reframe": "Suggest a different meaning for an experience expressed by the client, placing it in a new light. For example, 'Maybe this setback is actually a sign that you're ready for change.'",
    "Support": "Generally supportive, understanding comments that are not codable as Affirm or Reflect. For example, 'That must have been difficult for you.'",
    "Warn": "Provide a warning or threat, implying negative consequences that will follow unless the client takes certain action. For example, 'You could go blind if you don't manage your blood sugar levels.'",
    "Structure": "Give comments made to explain what is going to happen in the session, to make a transition from one part of a session to another, to help the client anticipate what will happen next, etc. For example, 'First, let's discuss your drinking, and then we can explore other issues.'",
    "No Strategy": "Say something not related to behavior change. For example, 'Good morning!'",
}


# System prompt for Narrative Therapy crisis counselor
# System prompt for journaling companion
system_prompt_template = """You are a warm, thoughtful journaling companion. Your role is to help the user reflect on their day, notice what matters to them, and find small moments of clarity or meaning.

## Your Role
- Be a gentle, supportive presence - like a good friend who listens well
- Help the user see their own thoughts and feelings more clearly
- Notice what their words reveal about what they value and care about
- Celebrate small wins and bright spots without being cheery or dismissive
- Offer reframes that open up new perspectives, not advice or solutions

## Current Context
The user's journal entry: {initial_story}
"""

# Prompt for inferring client's story state
# Prompt for identifying the journal entry type
infer_state_prompt = """Read this journal entry and identify what kind of entry it is - what is the user bringing today?

## Entry Types

### sharing_something_hard
The user is writing about something difficult - a bad day, conflict, disappointment, frustration, stress, or something that went wrong.
Signs: complaints, venting, describing problems, words like "frustrated," "annoyed," "exhausted," "terrible day"

### sorting_through_feelings
The user is trying to untangle or understand their emotions. They might feel confused, mixed, or uncertain about how they feel.
Signs: "I don't know why I feel...", "part of me thinks... but also...", exploring emotions, questioning reactions

### celebrating_a_win
The user is sharing something good - an accomplishment, a nice moment, progress, or something they're proud of.
Signs: excitement, pride, "I did it," "finally," describing achievements or positive outcomes

### feeling_grateful
The user is noticing things they appreciate - people, moments, small pleasures, or what's going well.
Signs: thankfulness, appreciation, listing good things, "grateful for," "lucky to have," warmth toward life

### working_through_a_decision
The user is thinking through a choice, weighing options, or trying to figure out what to do about something.
Signs: "should I...", pros/cons, "I'm torn," "not sure whether to," thinking out loud about options

### noticing_something_about_themselves
The user is having an insight or realization about who they are, patterns they see, or something they're learning about themselves.
Signs: "I realized...", "I think I'm the kind of person who...", "I always...", self-reflection, connecting dots

### low_energy_or_blank
The user doesn't have much to say. The entry is short, flat, or they explicitly say they don't know what to write.
Signs: very brief entry, "nothing much," "don't know what to say," low detail, going through the motions

### needing_comfort
The user seems sad, lonely, hopeless, or emotionally heavy. This goes beyond a hard day - there's a deeper weight.
Signs: sadness, loneliness, feeling lost, hopelessness, "I don't know how much more I can take," heaviness, isolation

## Journal Entry
{context}

## Your Task
Read the entry and decide which type fits best. Most entries will clearly fit one type. If it's mixed, choose the one that feels most central to what the user needs right now.

Briefly explain your reasoning (2-3 sentences), then state the entry type on its own line at the end like this:

Entry type: [type]
"""

#####################################################################

# Prompt for selecting strategies
select_strategy_prompt = """During motivational interviewing, the counselor should employ some counseling strategies tailored to the client's readiness to change, to effectively facilitate behavioral transformation. These counseling strategies are as follows:

- **Advise**: Give advice, makes a suggestion, offers a solution or possible action. For example, "Consider starting with small, manageable changes like taking a short walk daily."
- **Affirm**: Say something positive or complimentary to the client. For example, "You did well by seeking help."
- **Direct**: Give an order, command, direction. The language is imperative. For example, "You’ve got to stop drinking."
- **Emphasize Control**: Directly acknowledges or emphasizes the client's freedom of choice, autonomy,ability to decide, personal responsibility, etc. For example, "It’s up to you to decide whether to drink."
- **Facilitate**: Provide simple utterances that function as "keep going" acknowledgments encouraging the client to keep sharing.. For example, "Tell me more about that."
- **Inform**: Give information to the client, explains something, or provides feedback. For example, "This is a hormone that helps your body utilize sugar."
- **Closed Question**: Ask a question in order to gather information, understand,or elicit the client's story. The question implies a short answer: Yes or no, a specific fact, a number, etc. For example, "Did you use heroin this week?"
- **Open Question**: Ask a question in order to gather information, understand,or elicit the client's story. The question should be not closed questions, that leave latitude for response. For example, "Can you tell me more about your drinking habits?"
- **Raise Concern**: Point out a possible problem with a client's goal, plan, or intention. For example, "What do you think about my plan?"
- **Confront**: Directly disagrees, argues, corrects, shames, blames, seeks to persuade, criticizes, judges, labels, moralizes, ridicules, or questions the client's honesty. For example, "What makes you think that you can get away with it?"
- **Simple Reflection**: Make a statement that reflects back content or meaning previously offered by the client, conveying shallow understanding without additional information. Add nothing at all to what the client has said, but simply repeat or restate it using some or all of the same words. For example, "You don’t want to do that."
- **Complex Reflection**: Make a statement that reflects back content or meaning previously offered by the client, conveying deep understanding with additional information. Change or add to what the client has said in a significant way, to infer the client's meaning. For example, "That’s where you drew the line."
- **Reframe**: Suggest a different meaning for an experience expressed by the client, placing it in a new light. For example, "Maybe this setback is actually a sign that you're ready for change."
- **Support**: Generally supportive, understanding comments that are not codable as Affirm or Reflect. For example, "That must have been difficult for you."
- **Warn**: Provide a warning or threat, implying negative consequences that will follow unless the client takes certain action. For example, "You could go blind if you don’t manage your blood sugar levels."
- **Structure**: Give comments made to explain what is going to happen in the session, to make a transition from one part of a session to another, to help the client anticipate what will happen next, etc. For example, "First, let’s discuss your drinking, and then we can explore other issues."
- **No Strategy**: Say something not related to behavior change. For example, "Good morning!"

Based on the current counseling context and the client's state, analyze and select appropriate strategies **but no more than 2** for **next response** to optimally advance the counseling process.

Given Current Context:
{context}

Client’s State:
{state}: {state_instruction}

Please analyse the current situation, then select appropriate strategies based on current topic and situation to motivate client after analysing. Remember, you can select up to 2 strategies.
"""

# Response selection prompt
response_selection_prompt = """You are a warm journaling companion.

## Conversation So Far
{conversation}

## Candidate Responses
{responses}

Select the response that best:
1. Acknowledges what the user shared before anything else
2. Feels warm, genuine, and accessible (not clinical or mechanical)
3. Helps the user reflect on their own thoughts and feelings
4. Stays curious rather than giving advice
5. Says something NEW - avoids repeating phrases from previous responses

Reply with ONLY the number of the best response.
"""