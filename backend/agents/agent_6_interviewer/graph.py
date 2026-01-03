import json
import datetime
import os
from typing import TypedDict, List, Literal, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from core.db import db_manager

# Lazy-load LLM to ensure environment variables are loaded
_llm = None
def get_llm():
    global _llm
    if _llm is None:
        # Check for either GOOGLE_API_KEY or GEMINI_API_KEY
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables")
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0.7,
            google_api_key=api_key
        )
    return _llm

checkpointer = MemorySaver()

STAGES = {
    "intro": {"turns": 1, "next": "resume"},
    "resume": {"turns": 2, "next": "challenge"},
    "challenge": {"turns": 2, "next": "conclusion"},
    "conclusion": {"turns": 1, "next": "end"}
}
MAX_TURNS = 6

class InterviewState(TypedDict):
    messages: List[BaseMessage]
    stage: str
    turn: int
    stage_turn: int
    context: dict
    feedback: Optional[dict]
    ending: bool

def get_stage_prompt(stage: str, ctx: dict, stage_turn: int) -> str:
    job = ctx.get('job', {})
    user = ctx.get('user', {})
    gaps = ctx.get('gaps', {})
    
    base = f"""You are an expert interviewer at {job.get('company', 'the company')}.
    Candidate: {user.get('name', 'Candidate')}. Role: {job.get('title', 'Role')}.
    Keep responses SHORT (2 sentences max). Ask ONE question at a time.
    """

    if stage == "intro":
        return f"{base} STAGE: INTRO. Greet them and ask for a quick intro."
    elif stage == "resume":
        return f"{base} STAGE: RESUME. Ask about {user.get('skills', [])[:3]}."
    elif stage == "challenge":
        missing = gaps.get('missing_skills', [])
        q = gaps.get('suggested_questions', [''])[0]
        return f"{base} STAGE: CHALLENGE. Gap: {missing}. Suggested: {q}. Drill down."
    elif stage == "conclusion":
        return f"{base} STAGE: CONCLUSION. This is the final turn. Do NOT ask any more interview questions. Simply thank the candidate for their time, mention that we will be in touch, and say goodbye. Keep it professional and brief."
    
    return base

def interviewer_node(state: InterviewState) -> dict:
    stage = state.get("stage", "intro")
    turn = state.get("turn", 0)
    stage_turn = state.get("stage_turn", 0)
    ctx = state.get("context", {})
    messages = state.get("messages", [])
    
    if stage == "end" or state.get("ending", False) or turn >= MAX_TURNS:
        prompt = get_stage_prompt("conclusion", ctx, 1) + " Final message. Bye."
        response = get_llm().invoke(messages[-6:] + [HumanMessage(content=prompt)])
        return {
            "messages": messages + [AIMessage(content=response.content)],
            "stage": "end",
            "ending": True
        }
    
    prompt = get_stage_prompt(stage, ctx, stage_turn)
    response = get_llm().invoke(messages[-6:] + [HumanMessage(content=prompt)])
    
    return {
        "messages": messages + [AIMessage(content=response.content)],
        "turn": turn + 1,
        "stage_turn": stage_turn + 1
    }

def check_stage_transition(state: InterviewState) -> dict:
    stage = state.get("stage", "intro")
    stage_turn = state.get("stage_turn", 0)
    
    config = STAGES.get(stage, {"turns": 2, "next": "end"})
    
    if stage_turn >= config["turns"]:
        next_stage = config["next"]
        updates = {"stage": next_stage, "stage_turn": 0}
        if next_stage == "end":
            updates["ending"] = True
        return updates
    
    return {}

def should_continue(state: InterviewState) -> Literal["continue", "evaluate"]:
    if state.get("stage") == "end" or state.get("ending"):
        return "evaluate"
    return "continue"

def evaluate_node(state: InterviewState) -> dict:
    ctx = state.get("context", {})
    messages = state.get("messages", [])
    
    prompt = f"""Evaluate interview for {ctx.get('job', {}).get('title')}.
    Return JSON: {{ "score": 0-100, "verdict": "Hire/No Hire", "summary": "text" }}"""
    
    response = get_llm().invoke(messages[-10:] + [HumanMessage(content=prompt)])
    try:
        feedback = json.loads(response.content.replace("```json", "").replace("```", "").strip())
    except:
        feedback = {"score": 0, "verdict": "Error"}
    
    # Save to DB
    try:
        user_id = ctx.get("user_id")
        job_id = ctx.get("job_id")
        if user_id and job_id:
            chat_history = [{"role": m.type, "content": m.content} for m in messages]
            
            db_manager.get_client().table("interviews").insert({
                "user_id": user_id,
                "job_id": int(job_id),
                "chat_history": json.dumps(chat_history),
                "feedback_report": json.dumps(feedback),
                "created_at": datetime.datetime.now().isoformat()
            }).execute()
            print(f"✅ [DB] Saved interview feedback for User {user_id} Job {job_id}")
    except Exception as e:
        print(f"❌ [DB] Save Error: {e}")
        
    return {"feedback": feedback, "stage": "end"}

workflow = StateGraph(InterviewState)
workflow.add_node("interviewer", interviewer_node)
workflow.add_node("transition", check_stage_transition)
workflow.add_node("evaluate", evaluate_node)

workflow.add_edge(START, "transition")
workflow.add_edge("transition", "interviewer")
workflow.add_conditional_edges("interviewer", should_continue, {"continue": END, "evaluate": "evaluate"})
workflow.add_edge("evaluate", END)

interview_graph = workflow.compile(checkpointer=checkpointer)

def create_initial_state(context: dict) -> InterviewState:
    return {
        "messages": [],
        "stage": "intro",
        "turn": 0,
        "stage_turn": 0,
        "context": context,
        "feedback": None,
        "ending": False
    }

def add_user_message(state: dict, user_text: str) -> dict:
    return {
        **state,
        "messages": state.get("messages", []) + [HumanMessage(content=user_text)]
    }

def run_interview_turn(session_id: str, user_message: str, job_context: str) -> dict:
    """
    Run a single interview turn. Returns the AI response and current state.
    """
    # Create a simple context from job_context string
    context = {
        "job": {"title": job_context, "company": "Company"},
        "user": {"name": "Candidate", "skills": []},
        "gaps": {"missing_skills": [], "suggested_questions": []},
        "user_id": session_id,
        "job_id": "1"
    }
    
    thread_id = f"interview_{session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get or create initial state
    try:
        # Try to get existing state from checkpointer
        state = create_initial_state(context)
        if user_message:
            state = add_user_message(state, user_message)
        
        result = interview_graph.invoke(state, config=config)
        
        ai_response = result["messages"][-1].content if result["messages"] else "Hello!"
        
        return {
            "response": ai_response,
            "stage": result.get("stage", "intro"),
            "message_count": len(result.get("messages", []))
        }
    except Exception as e:
        print(f"Interview error: {e}")
        return {
            "response": "I apologize, there was an error. Could you repeat that?",
            "stage": "intro",
            "message_count": 0
        }
