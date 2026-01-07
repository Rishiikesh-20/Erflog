"""
Agent 5 - Interview (Unified Chat + Voice)
Conducts mock interviews via text or voice with LangGraph state machine.
Toggle mode: 'text' for chat, 'voice' for voice-optimized responses.
Supports: Technical Interview & HR Interview types
"""
import os
import json
import datetime
import time
from typing import TypedDict, List, Literal, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from core.db import db_manager
from core.config import (
    get_interview_config, 
    get_stages_for_type, 
    get_total_turns,
    TECHNICAL_INTERVIEW_CONFIG,
    HR_INTERVIEW_CONFIG
)

# Lazy-load LLM to ensure environment variables are loaded
_llm = None
def get_llm():
    global _llm
    if _llm is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables")
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            temperature=0.5,
            google_api_key=api_key
        )
    return _llm

# Separate checkpointers for chat and voice
chat_checkpointer = MemorySaver()
voice_checkpointer = MemorySaver()

class InterviewState(TypedDict):
    messages: List[BaseMessage]
    stage: str
    turn: int
    stage_turn: int
    context: dict
    feedback: Optional[dict]
    ending: bool
    mode: str  # 'text' or 'voice'
    interview_type: str  # 'TECHNICAL' or 'HR'
    job_id: Optional[str]
    user_id: Optional[str]

# =============================================================================
# Stage Prompts - Technical Interview
# =============================================================================

def get_technical_prompt(stage: str, ctx: dict, stage_turn: int, mode: str = "text") -> str:
    """Get prompt for technical interview stages."""
    job = ctx.get('job', {})
    user = ctx.get('user', {})
    gaps = ctx.get('gaps', {})
    
    job_title = job.get('title', 'the role')
    job_company = job.get('company', 'the company')
    job_desc = job.get('description', '')[:500]
    user_name = user.get('name', 'the candidate')
    skills = user.get('skills', [])[:5]
    
    voice_note = " Keep responses SHORT (1-2 sentences). DO NOT include labels like 'Interviewer:' in your response." if mode == "voice" else ""
    
    base = f"""You are conducting a TECHNICAL interview for {job_title} at {job_company}.
Candidate: {user_name}
Their skills: {', '.join(skills) if skills else 'Not specified'}
{voice_note}

IMPORTANT RULES:
- Ask ONE clear question at a time
- Be professional but friendly
- Reference specific job requirements when relevant
"""

    if stage == "intro":
        return f"""{base}
STAGE: INTRODUCTION (Turn {stage_turn + 1}/1)
- Warmly welcome {user_name}
- Briefly introduce yourself as the technical interviewer
- Ask them to introduce themselves and their background
"""
    
    elif stage == "resume":
        return f"""{base}
STAGE: RESUME DEEP-DIVE (Turn {stage_turn + 1}/2)
Job requires: {job_desc[:200]}...

- Ask about their relevant experience or projects
- Focus on technical skills mentioned in their resume
- Probe deeper on their experience with: {', '.join(skills[:3]) if skills else 'their main technologies'}
"""
    
    elif stage == "challenge":
        missing = gaps.get('missing_skills', [])[:3]
        suggested = gaps.get('suggested_questions', [])[:2]
        return f"""{base}
STAGE: CHALLENGING QUESTIONS (Turn {stage_turn + 1}/2)
Gap Analysis: {', '.join(missing) if missing else 'General technical assessment'}
Suggested focus areas: {suggested if suggested else ['Problem solving', 'System design']}

- Ask challenging but fair technical questions
- Focus on DSA, core concepts, or system design
- Assess problem-solving approach
- If they struggle, provide hints and observe their thinking process
"""
    
    elif stage == "conclusion":
        return f"""{base}
STAGE: CONCLUSION (Turn {stage_turn + 1}/1)
CRITICAL: Wrap up the interview smoothly.
- Thank {user_name} for their time
- Ask if they have any questions about the role or company
- Provide a positive closing: "We'll review your responses and be in touch soon. Best of luck!"
"""
    
    return base

# =============================================================================
# Stage Prompts - HR Interview
# =============================================================================

def get_hr_prompt(stage: str, ctx: dict, stage_turn: int, mode: str = "text") -> str:
    """Get prompt for HR interview stages."""
    job = ctx.get('job', {})
    user = ctx.get('user', {})
    
    job_title = job.get('title', 'the role')
    job_company = job.get('company', 'the company')
    user_name = user.get('name', 'the candidate')
    
    voice_note = " Keep responses SHORT (1-2 sentences). DO NOT include labels like 'Interviewer:' in your response." if mode == "voice" else ""
    
    base = f"""You are conducting an HR/Behavioral interview for {job_title} at {job_company}.
Candidate: {user_name}
{voice_note}

IMPORTANT RULES:
- Ask ONE clear question at a time
- Be warm and professional
- Use STAR method to assess responses (Situation, Task, Action, Result)
"""

    if stage == "intro":
        return f"""{base}
STAGE: INTRODUCTION (Turn {stage_turn + 1}/1)
- Warmly welcome {user_name}
- Introduce yourself as the HR interviewer
- Explain the interview format briefly
- Ask them to share a bit about themselves and why they're interested in this role
"""
    
    elif stage == "behavioral":
        return f"""{base}
STAGE: BEHAVIORAL QUESTIONS (Turn {stage_turn + 1}/2)
Ask behavioral questions using STAR method:
- "Tell me about a time when you faced a challenging situation at work and how you handled it"
- "Describe a situation where you had to work with a difficult team member"
- "Give an example of a time you showed leadership"

Focus on: teamwork, conflict resolution, problem-solving, adaptability
"""
    
    elif stage == "experience":
        return f"""{base}
STAGE: EXPERIENCE & MOTIVATION (Turn {stage_turn + 1}/2)
- Ask about their career journey and key learnings
- Understand their motivation for this role
- Discuss their expectations for growth
- Ask about their preferred work environment
"""
    
    elif stage == "conclusion":
        return f"""{base}
STAGE: CONCLUSION (Turn {stage_turn + 1}/1)
CRITICAL: Wrap up the interview smoothly.
- Thank {user_name} for sharing their experiences
- Ask if they have any questions about the culture, benefits, or next steps
- Provide a positive closing: "It was great speaking with you. We'll be in touch soon!"
"""
    
    return base

def get_stage_prompt(stage: str, ctx: dict, stage_turn: int, mode: str = "text", interview_type: str = "TECHNICAL") -> str:
    """Get appropriate prompt based on interview type."""
    if interview_type.upper() == "HR":
        return get_hr_prompt(stage, ctx, stage_turn, mode)
    return get_technical_prompt(stage, ctx, stage_turn, mode)

def interviewer_node(state: InterviewState) -> dict:
    mode = state.get("mode", "text")
    interview_type = state.get("interview_type", "TECHNICAL")
    stage = state.get("stage", "intro")
    turn = state.get("turn", 0)
    stage_turn = state.get("stage_turn", 0)
    ctx = state.get("context", {})
    messages = state.get("messages", [])
    
    # Get configuration for this interview type
    stages_config = get_stages_for_type(interview_type)
    max_turns = get_total_turns(interview_type)
    
    log_prefix = f"[{interview_type} {'Voice' if mode == 'voice' else 'Chat'}]"
    print(f"{log_prefix} Stage: {stage}, Turn: {turn}, StageTurn: {stage_turn}, Ending: {state.get('ending', False)}")
    
    # Get stage order based on interview type
    if interview_type.upper() == "HR":
        stage_order = ["intro", "behavioral", "experience", "conclusion", "end"]
    else:
        stage_order = ["intro", "resume", "challenge", "conclusion", "end"]
    
    current_idx = stage_order.index(stage) if stage in stage_order else 0
    config = stages_config.get(stage, {"turns": 1, "next": "end"})
    
    # Voice mode: Special handling for conclusion
    if mode == "voice" and stage == "conclusion" and stage_turn >= 1:
        print(f"{log_prefix} Conclusion answer received, ending interview")
        return {
            "messages": messages,
            "stage": "end",
            "turn": turn,
            "stage_turn": stage_turn,
            "ending": True
        }
    
    # Check stage transition
    if stage_turn >= config["turns"]:
        next_stage = config["next"]
        next_idx = stage_order.index(next_stage) if next_stage in stage_order else len(stage_order) - 1
        
        if next_idx > current_idx:
            print(f"{log_prefix} ✅ TRANSITIONING: {stage} -> {next_stage}")
            
            if mode == "voice" and next_stage == "end":
                return {
                    "messages": messages,
                    "stage": "end",
                    "turn": turn,
                    "stage_turn": stage_turn,
                    "ending": True
                }
            
            stage = next_stage
            stage_turn = 0
            if next_stage == "end":
                state = {**state, "ending": True}
    
    # Check if interview should end
    if stage == "end" or state.get("ending", False) or turn >= max_turns:
        print(f"{log_prefix} Triggering conclusion - Stage:{stage}, Turn:{turn}/{max_turns}")
        
        if mode == "voice":
            return {
                "messages": messages,
                "stage": "end",
                "ending": True
            }
        
        # Text mode: Generate final message
        prompt = get_stage_prompt("conclusion", ctx, 1, mode, interview_type) + " Final message."
        response = get_llm().invoke(messages[-4:] + [HumanMessage(content=prompt)])
        return {
            "messages": messages + [AIMessage(content=response.content)],
            "stage": "end",
            "ending": True
        }
    
    # Generate next question
    prompt = get_stage_prompt(stage, ctx, stage_turn, mode, interview_type)
    
    if mode == "voice":
        start_time = time.time()
        response = get_llm().invoke(messages[-4:] + [HumanMessage(content=prompt)])
        print(f"{log_prefix} LLM took {time.time() - start_time:.2f}s")
    else:
        response = get_llm().invoke(messages[-4:] + [HumanMessage(content=prompt)])
    
    ai_content = response.content
    
    # Clean up voice responses
    if mode == "voice":
        ai_content = ai_content.replace("Interviewer:", "").replace("Interviewer :", "").strip()
        if stage == "conclusion" and len(ai_content) > 150:
            ai_content = ai_content[:150] + "..."
        ai_content = ai_content.replace('**', '').replace('*', '').replace('_', '')
    
    return {
        "messages": messages + [AIMessage(content=ai_content)],
        "stage": stage,
        "turn": turn + 1,
        "stage_turn": stage_turn + 1
    }

def should_continue(state: InterviewState) -> Literal["continue", "evaluate"]:
    stage = state.get("stage")
    ending = state.get("ending", False)
    
    if stage == "end" or ending:
        return "evaluate"
    return "continue"

def evaluate_node(state: InterviewState) -> dict:
    mode = state.get("mode", "text")
    interview_type = state.get("interview_type", "TECHNICAL")
    log_prefix = f"[{interview_type} Evaluate]"
    print(f"{log_prefix} Starting evaluation...")
    
    ctx = state.get("context", {})
    messages = state.get("messages", [])
    user_id = state.get("user_id")
    job_id = state.get("job_id")
    
    job_title = ctx.get('job', {}).get('title', 'this position')
    
    eval_focus = "technical skills, problem-solving ability, and coding knowledge" if interview_type == "TECHNICAL" else "communication skills, cultural fit, and behavioral competencies"
    
    prompt = f"""Evaluate this {interview_type} interview for {job_title}. 
Focus on: {eval_focus}

Return JSON only:
{{
    "score": <0-100>,
    "verdict": "Hired" or "Not Hired",
    "summary": "<brief 2-line evaluation>",
    "strengths": ["s1", "s2"],
    "improvements": ["i1", "i2"]
}}"""
    
    response = get_llm().invoke(messages[-8:] + [HumanMessage(content=prompt)])
    try:
        feedback = json.loads(response.content.replace("```json", "").replace("```", "").strip())
        # Add interview type to feedback for display purposes
        feedback["interview_type"] = interview_type
    except:
        feedback = {"score": 0, "verdict": "Error", "summary": "Failed to parse evaluation", "interview_type": interview_type}
    
    # Save to database
    try:
        if user_id:
            print(f"{log_prefix} Attempting to save to database for user_id: {user_id}")
            chat_history = [{"role": m.type, "content": m.content} for m in messages]
            
            # Parse job_id - required field in database
            job_id_int = None
            if job_id:
                try:
                    job_id_int = int(float(job_id))
                    print(f"{log_prefix} Parsed job_id: {job_id_int}")
                except (ValueError, TypeError):
                    print(f"⚠️ [DB] Invalid job_id format: {job_id}")
            
            # job_id is required (NOT NULL in schema) - get first valid job if not provided
            if job_id_int is None:
                print(f"⚠️ {log_prefix} No valid job_id provided - querying for first available job")
                try:
                    jobs_result = db_manager.get_client().table("jobs").select("id").limit(1).execute()
                    if jobs_result.data and len(jobs_result.data) > 0:
                        job_id_int = jobs_result.data[0]["id"]
                        print(f"{log_prefix} Using first available job_id: {job_id_int}")
                    else:
                        print(f"⚠️ {log_prefix} No jobs in database - cannot save interview")
                except Exception as job_query_error:
                    print(f"⚠️ {log_prefix} Failed to query jobs: {job_query_error}")
            
            if job_id_int is None:
                print(f"⚠️ {log_prefix} No valid job_id available - skipping database save")
            else:
                insert_data = {
                    "user_id": user_id,
                    "job_id": job_id_int,
                    "chat_history": chat_history,  # Already a list, Supabase handles JSONB
                    "feedback_report": feedback,   # Already a dict, Supabase handles JSONB
                }
                
                print(f"{log_prefix} Insert data prepared: user_id={user_id[:8]}..., job_id={job_id_int}")
                
                try:
                    result = db_manager.get_client().table("interviews").insert(insert_data).execute()
                    print(f"✅ [DB] Saved {interview_type} interview for User {user_id[:8]}... - Rows: {len(result.data) if result.data else 0}")
                except Exception as db_error:
                    error_str = str(db_error)
                    print(f"⚠️ [DB] Insert error: {error_str}")
                    
                    # If foreign key constraint fails, query for a valid job
                    if "23503" in error_str and "job_id" in error_str:
                        print(f"⚠️ [DB] Job {job_id_int} doesn't exist. Querying for valid job...")
                        jobs_result = db_manager.get_client().table("jobs").select("id").limit(1).execute()
                        if jobs_result.data and len(jobs_result.data) > 0:
                            insert_data["job_id"] = jobs_result.data[0]["id"]
                            result = db_manager.get_client().table("interviews").insert(insert_data).execute()
                            print(f"✅ [DB] Saved with job_id={insert_data['job_id']} - Rows: {len(result.data) if result.data else 0}")
                        else:
                            print(f"⚠️ [DB] No jobs found in database - cannot save interview")
                    else:
                        raise
        else:
            print(f"⚠️ {log_prefix} No user_id provided - skipping database save")
    except Exception as e:
        print(f"❌ [DB] Save Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ==========================================================================
    # FEEDBACK LOOP: Enhance roadmap based on interview improvements
    # ==========================================================================
    if user_id and feedback.get("improvements"):
        try:
            import httpx
            
            print(f"{log_prefix} 🔄 Triggering Feedback Loop - Enhancing roadmap...")
            
            # Build the enhancement request
            enhancement_payload = {
                "user_id": user_id,
                "improvements": feedback.get("improvements", []),
                "job_context": {
                    "title": ctx.get('job', {}).get('title', 'Unknown'),
                    "company": ctx.get('job', {}).get('company', 'Unknown'),
                }
            }
            
            # Call the enhancement endpoint (internal call)
            # Using sync httpx since we're in a sync function
            api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{api_base}/api/saved-jobs/enhance-roadmap-from-feedback",
                    json=enhancement_payload
                )
                
                if response.status_code == 200:
                    enhancement_result = response.json()
                    print(f"[DEBUG] Enhancement response keys: {enhancement_result.keys()}")
                    roadmap_additions = enhancement_result.get("additions", [])
                    print(f"[DEBUG] roadmap_additions count: {len(roadmap_additions)}")
                    
                    # Add roadmap additions to feedback for frontend display
                    feedback["roadmap_additions"] = {
                        "nodes": roadmap_additions,
                        "message": enhancement_result.get("message", ""),
                        "roadmap_id": enhancement_result.get("roadmap_id")
                    }
                    print(f"[DEBUG] feedback now has roadmap_additions: {feedback.get('roadmap_additions', {}).get('nodes', [])[:1]}...")
                    
                    print(f"✅ {log_prefix} Feedback Loop Complete - Added {len(roadmap_additions)} learning blocks")
                    
                    # Update the interview record in database with roadmap_additions
                    if job_id_int:
                        try:
                            db_manager.get_client().table("interviews").update({
                                "feedback_report": feedback
                            }).eq("user_id", user_id).eq("job_id", job_id_int).order("created_at", desc=True).limit(1).execute()
                            print(f"✅ {log_prefix} Updated interview record with roadmap additions")
                        except Exception as update_error:
                            print(f"⚠️ {log_prefix} Failed to update interview with roadmap: {update_error}")
                else:
                    print(f"⚠️ {log_prefix} Feedback Loop Error: {response.status_code} - {response.text[:200]}")
                    
        except Exception as feedback_loop_error:
            print(f"⚠️ {log_prefix} Feedback Loop Failed: {feedback_loop_error}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole evaluation if feedback loop fails
    
    print(f"{log_prefix} Complete - Verdict: {feedback.get('verdict')}, Score: {feedback.get('score')}")
    print(f"[DEBUG] Final feedback has roadmap_additions: {'roadmap_additions' in feedback}, nodes count: {len(feedback.get('roadmap_additions', {}).get('nodes', []))}")
    return {"feedback": feedback, "stage": "end"}


# Build workflow graphs
def _build_graph(checkpointer):
    workflow = StateGraph(InterviewState)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("evaluate", evaluate_node)
    
    workflow.add_edge(START, "interviewer")
    workflow.add_conditional_edges("interviewer", should_continue, {"continue": "interviewer", "evaluate": "evaluate"})
    workflow.add_edge("evaluate", END)
    
    return workflow.compile(checkpointer=checkpointer, interrupt_after=["interviewer"])

# Separate evaluation function to call directly when interview ends
def run_evaluation(state: dict) -> dict:
    """Directly run evaluation without going through the graph.
    This bypasses the interrupt_after issue."""
    return evaluate_node(state)

chat_interview_graph = _build_graph(chat_checkpointer)
voice_interview_graph = _build_graph(voice_checkpointer)

def create_initial_state(context: dict, mode: str = "text", interview_type: str = "TECHNICAL", user_id: str = None, job_id: str = None) -> InterviewState:
    """Create initial interview state."""
    return {
        "messages": [],
        "stage": "intro",
        "turn": 0,
        "stage_turn": 0,
        "context": context,
        "feedback": None,
        "ending": False,
        "mode": mode,
        "interview_type": interview_type.upper(),
        "user_id": user_id,
        "job_id": job_id
    }

def create_chat_state(context: dict, interview_type: str = "TECHNICAL", user_id: str = None, job_id: str = None) -> InterviewState:
    return create_initial_state(context, mode="text", interview_type=interview_type, user_id=user_id, job_id=job_id)

def create_voice_state(context: dict, interview_type: str = "TECHNICAL", user_id: str = None, job_id: str = None) -> InterviewState:
    return create_initial_state(context, mode="voice", interview_type=interview_type, user_id=user_id, job_id=job_id)

def add_user_message(state: dict, user_text: str) -> dict:
    return {
        **state,
        "messages": state.get("messages", []) + [HumanMessage(content=user_text)]
    }

add_chat_message = add_user_message
add_voice_message = add_user_message

def run_interview_turn(session_id: str, user_message: str, job_context: str, interview_type: str = "TECHNICAL") -> dict:
    """Run a single interview turn."""
    context = {
        "job": {"title": job_context, "company": "Company"},
        "user": {"name": "Candidate", "skills": []},
        "gaps": {"missing_skills": [], "suggested_questions": []},
        "user_id": session_id,
        "job_id": "1"
    }
    
    thread_id = f"interview_{session_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        state = create_chat_state(context, interview_type=interview_type)
        if user_message:
            state = add_user_message(state, user_message)
        
        result = chat_interview_graph.invoke(state, config=config)
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
