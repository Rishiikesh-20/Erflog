"""
Agent 6: The Interviewer
LangGraph-based conversational interview agent using Google Gemini.
"""

import os
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv
from google import genai
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in the environment or a .env file")

client = genai.Client(api_key=GEMINI_API_KEY)


# --- State Definition ---
class InterviewState(TypedDict):
    """State for the interview conversation."""
    messages: List[dict]        # Conversation history: [{"role": "user/assistant", "content": "..."}]
    job_context: str            # Job Title/Description
    interview_stage: str        # "Introduction", "Technical", "Behavioral", "Closing"


def add_message(messages: List[dict], role: str, content: str) -> List[dict]:
    """Helper to add a message to history."""
    return messages + [{"role": role, "content": content}]


# --- Interview Node ---
def node_interviewer(state: InterviewState) -> InterviewState:
    """
    Main interviewer logic:
    - If no messages, start the interview with a greeting.
    - Otherwise, analyze the last response and ask the next question.
    """
    messages = state.get("messages", [])
    job_context = state.get("job_context", "Software Developer")
    stage = state.get("interview_stage", "Introduction")
    
    # Build conversation history for Gemini
    system_prompt = f"""You are a friendly but professional Technical Interviewer for the role of "{job_context}".

RULES:
1. Ask ONE question at a time - never multiple questions.
2. Keep responses concise (2-3 sentences max).
3. After the candidate answers, give brief encouraging feedback, then ask the next question.
4. Progress through stages: Introduction → Technical Skills → Problem Solving → Behavioral → Closing.
5. Be conversational and supportive, not intimidating.

Current Stage: {stage}
"""

    # Check if this is the start of the interview
    if not messages:
        # First message - greet and ask opening question
        prompt = f"""{system_prompt}

This is the START of the interview. Greet the candidate warmly and ask them to briefly introduce themselves and what interests them about the {job_context} role."""
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            ai_response = response.text.strip()
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            ai_response = f"Hello! Welcome to your interview for the {job_context} position. I'm excited to learn more about you. Could you start by telling me a bit about yourself and what draws you to this role?"
        
        return {
            "messages": add_message([], "assistant", ai_response),
            "job_context": job_context,
            "interview_stage": "Introduction"
        }
    
    # Build conversation context for follow-up
    conversation_text = "\n".join([
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
        for m in messages
    ])
    
    # Determine next stage based on message count
    msg_count = len(messages)
    if msg_count < 4:
        next_stage = "Introduction"
    elif msg_count < 8:
        next_stage = "Technical"
    elif msg_count < 12:
        next_stage = "Behavioral"
    else:
        next_stage = "Closing"
    
    prompt = f"""{system_prompt}

CONVERSATION SO FAR:
{conversation_text}

Based on the candidate's last response, provide brief feedback (1 sentence) and ask the next relevant question for a {job_context} role.
If we're in the Closing stage (after 6+ exchanges), thank them and wrap up the interview professionally."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        ai_response = response.text.strip()
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        ai_response = "Thank you for that answer. Could you tell me more about your experience with the technologies mentioned in this role?"
    
    return {
        "messages": add_message(messages, "assistant", ai_response),
        "job_context": job_context,
        "interview_stage": next_stage
    }


# --- Build the Graph ---
def build_interview_graph():
    """Construct and compile the LangGraph interview agent."""
    
    # Create the graph
    workflow = StateGraph(InterviewState)
    
    # Add the single node
    workflow.add_node("interviewer", node_interviewer)
    
    # Define edges: START -> interviewer -> END
    workflow.add_edge(START, "interviewer")
    workflow.add_edge("interviewer", END)
    
    # Compile with MemorySaver for session persistence
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    return graph


# Create a singleton graph instance
interview_graph = build_interview_graph()


# --- Public API ---
def run_interview_turn(session_id: str, user_message: str, job_context: str) -> dict:
    """
    Run one turn of the interview conversation.
    
    Args:
        session_id: Unique session identifier for conversation persistence
        user_message: The user's input (empty string for first turn)
        job_context: Job title/description being interviewed for
    
    Returns:
        dict with 'response' (AI message) and 'stage' (current interview stage)
    """
    config = {"configurable": {"thread_id": session_id}}
    
    # Get existing state or create new
    try:
        current_state = interview_graph.get_state(config)
        existing_messages = current_state.values.get("messages", []) if current_state.values else []
    except Exception:
        existing_messages = []
    
    # Add user message if provided
    if user_message:
        existing_messages = add_message(existing_messages, "user", user_message)
    
    # Prepare input state
    input_state = {
        "messages": existing_messages,
        "job_context": job_context,
        "interview_stage": "Introduction"
    }
    
    # Invoke the graph
    result = interview_graph.invoke(input_state, config)
    
    # Extract the AI's response (last assistant message)
    ai_messages = [m for m in result["messages"] if m["role"] == "assistant"]
    latest_response = ai_messages[-1]["content"] if ai_messages else "Let's begin the interview."
    
    return {
        "response": latest_response,
        "stage": result.get("interview_stage", "Introduction"),
        "message_count": len(result["messages"])
    }
