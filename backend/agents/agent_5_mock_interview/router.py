# backend/agents/agent_5_mock_interview/router.py
"""
Agent 5: Mock Interview - API Router

Provides endpoints for:
- GET /api/interview/history/{user_id} - Get interview history
- POST /api/interview/chat - Legacy chat interview
- WebSocket /ws/interview/{job_id} - Voice interview
- WebSocket /ws/interview/text/{job_id} - Text interview
"""

import os
import re
import uuid
import math
import struct
import asyncio
import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from core.db import db_manager
from core.config import AudioState, SILENCE_THRESHOLD, SILENCE_DURATION, COOLDOWN_SECONDS
from core.context_loader import fetch_interview_context
from services.audio_service import transcribe_audio_bytes, synthesize_audio_bytes

from .graph import (
    chat_interview_graph,
    voice_interview_graph,
    create_chat_state,
    create_voice_state,
    add_chat_message,
    add_voice_message,
    run_interview_turn,
    run_evaluation
)

logger = logging.getLogger("Agent5")

# Use empty prefix since we need both /api/interviews and /ws/interview paths
router = APIRouter(tags=["Agent 5: Mock Interview"])


# =============================================================================
# Pydantic Models
# =============================================================================

class InterviewRequest(BaseModel):
    user_id: str
    job_id: str
    interview_type: Optional[str] = "TECHNICAL"
    message: Optional[str] = None
    session_id: Optional[str] = None
    job_context: Optional[dict] = None
    user_message: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_rms(audio_chunk: bytes) -> float:
    """Calculates the Root Mean Square (volume) of the audio chunk."""
    if not audio_chunk:
        return 0
    count = len(audio_chunk) // 2
    if count == 0:
        return 0
    try:
        shorts = struct.unpack(f"{count}h", audio_chunk)
        sum_squares = sum(s ** 2 for s in shorts)
        return math.sqrt(sum_squares / count)
    except:
        return 0


def extract_user_id_from_token(access_token: str) -> Optional[str]:
    """Extract user_id (sub) from JWT token without verification.
    
    The token is trusted since it comes from authenticated Supabase sessions.
    """
    if not access_token or access_token == "test":
        return None
    
    try:
        # JWT has 3 parts: header.payload.signature
        import base64
        import json
        
        parts = access_token.split(".")
        if len(parts) != 3:
            return None
        
        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        # Return the 'sub' claim which is the user_id
        return payload_data.get("sub")
    except Exception as e:
        logger.warning(f"Failed to extract user_id from token: {e}")
        return None


# =============================================================================
# REST Endpoints
# =============================================================================

@router.get("/api/interviews/{user_id}")
async def get_interview_history(user_id: str):
    """Fetch past interviews for a user from Supabase."""
    try:
        response = db_manager.get_client().table("interviews").select(
            "id, created_at, feedback_report, job_id"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
        
        interviews = response.data if response.data else []
        logger.info(f"[API] Fetched {len(interviews)} interviews for user {user_id[:8]}...")
        return interviews
    except Exception as e:
        logger.error(f"Error fetching interviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/interview/chat")
async def interview_chat(request: InterviewRequest):
    """Agent 5: Interview Chat Endpoint (Legacy)"""
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not request.job_context:
        raise HTTPException(status_code=400, detail="job_context is required")
    try:
        result = run_interview_turn(
            session_id=request.session_id,
            user_message=request.user_message,
            job_context=request.job_context
        )
        return {
            "status": "success",
            "response": result["response"],
            "stage": result["stage"],
            "message_count": result["message_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interview chat failed: {str(e)}")


# =============================================================================
# WebSocket: Text Interview
# =============================================================================

@router.websocket("/ws/interview/text/{job_id}")
async def interview_text_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    # Wait for initial auth message from frontend
    try:
        init_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        interview_type = init_data.get("interview_type", "TECHNICAL").upper()
        
        # Get user_id: prefer explicit user_id, then extract from token
        user_id = init_data.get("user_id")
        if not user_id:
            access_token = init_data.get("access_token", "")
            user_id = extract_user_id_from_token(access_token)
        
        if not user_id:
            logger.error("[Text Interview] No user_id provided and could not extract from token")
            await websocket.send_json({"type": "error", "message": "Authentication required"})
            await websocket.close(code=1008)  # Policy violation
            return
            
        logger.info(f"[Text Interview] User: {user_id[:8]}...")
            
    except asyncio.TimeoutError:
        await websocket.send_json({"type": "error", "message": "Auth timeout"})
        await websocket.close()
        return
    
    # Clean job_id
    numeric_part = re.search(r'\d+', job_id)
    job_id_clean = numeric_part.group() if numeric_part else job_id
    
    try:
        full_context = fetch_interview_context(user_id, job_id_clean)
        full_context["user_id"] = user_id
        full_context["job_id"] = job_id_clean
        logger.info(f"[Text {interview_type}] Context: {full_context['job']['title']} | {full_context['user']['name']}")
    except Exception as e:
        logger.error(f"Context Error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()
        return

    thread_id = f"text_{user_id}_{job_id}_{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    state = create_chat_state(full_context, interview_type=interview_type, user_id=user_id, job_id=job_id_clean)
    
    # Send interview config to frontend
    await websocket.send_json({
        "type": "config",
        "interview_type": interview_type,
        "job_title": full_context['job'].get('title', 'Unknown'),
        "user_name": full_context['user'].get('name', 'Candidate')
    })
    
    await websocket.send_json({"type": "event", "event": "thinking", "status": "start"})
    result = chat_interview_graph.invoke(state, config=config)
    ai_message = result["messages"][-1].content if result["messages"] else "Hello!"
    
    await websocket.send_json({"type": "event", "event": "thinking", "status": "end"})
    await websocket.send_json({"type": "event", "event": "stage_change", "stage": result.get("stage", "intro")})
    await websocket.send_json({"type": "message", "role": "assistant", "content": ai_message})
    
    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("message", "")
            if not user_text.strip():
                continue
            
            logger.info(f"[Text {interview_type}] User: {user_text[:50]}...")
            await websocket.send_json({"type": "event", "event": "thinking", "status": "start"})
            
            state = add_chat_message(result, user_text)
            result = chat_interview_graph.invoke(state, config=config)
            
            ai_message = result["messages"][-1].content if result["messages"] else "Could you repeat?"
            current_stage = result.get("stage", "unknown")
            
            logger.info(f"[Text {interview_type}] Stage: {current_stage} | Turn: {result.get('turn', 0)}")
            
            await websocket.send_json({"type": "event", "event": "thinking", "status": "end"})
            await websocket.send_json({"type": "event", "event": "stage_change", "stage": current_stage})
            await websocket.send_json({"type": "message", "role": "assistant", "content": ai_message})
            
            # Check if interview is ending
            if current_stage == "end" or result.get("ending"):
                logger.info(f"[Text {interview_type}] Interview ending - triggering evaluation...")
                logger.info(f"[Text] Current state - stage: {current_stage}, ending: {result.get('ending')}, user_id: {user_id}, job_id: {job_id_clean}")
                
                try:
                    logger.info(f"[Text] Running evaluation with user_id: {user_id[:8]}..., job_id: {job_id_clean}")
                    
                    # Run evaluation directly (bypasses graph interrupt_after issue)
                    eval_result = run_evaluation(result)
                    feedback = eval_result.get("feedback")
                    
                    if feedback:
                        logger.info(f"✅ Feedback generated: {feedback.get('verdict', 'N/A')} - Score: {feedback.get('score', 0)}")
                        
                        verdict = feedback.get("verdict", "Thank you")
                        score = feedback.get("score", 0)
                        summary = feedback.get("summary", "We appreciate your time.")
                        
                        feedback_message = f"\n\n**Interview Results**\n\n{verdict}. Your interview score is {score} out of 100.\n\n{summary}"
                        
                        await websocket.send_json({"type": "feedback", "data": feedback})
                        await websocket.send_json({"type": "message", "role": "assistant", "content": feedback_message})
                    else:
                        logger.warning("[Text] No feedback returned from evaluation")
                        logger.warning(f"[Text] Eval result: {eval_result}")
                except Exception as eval_error:
                    logger.error(f"[Text] Evaluation error: {eval_error}")
                    import traceback
                    traceback.print_exc()
                
                await asyncio.sleep(1)
                logger.info("Closing interview session")
                await websocket.close()
                break
                
    except WebSocketDisconnect:
        logger.info("[Text Interview] Client Disconnected")


# =============================================================================
# WebSocket: Voice Interview
# =============================================================================

@router.websocket("/ws/interview/{job_id}")
async def interview_voice_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    # Audio state machine to prevent listening while AI speaks
    audio_state = AudioState.IDLE
    
    # Wait for initial auth message from frontend
    try:
        init_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        interview_type = init_data.get("interview_type", "TECHNICAL").upper()
        
        # Get user_id: prefer explicit user_id, then extract from token
        user_id = init_data.get("user_id")
        if not user_id:
            access_token = init_data.get("access_token", "")
            user_id = extract_user_id_from_token(access_token)
        
        if not user_id:
            logger.error("[Voice Interview] No user_id provided and could not extract from token")
            await websocket.send_json({"type": "error", "message": "Authentication required"})
            await websocket.close(code=1008)  # Policy violation
            return
            
        logger.info(f"[Voice Interview] User: {user_id[:8]}...")
            
    except asyncio.TimeoutError:
        await websocket.send_json({"type": "error", "message": "Auth timeout"})
        await websocket.close()
        return
    
    # Clean job_id: "73.0" -> "73" or "job_18" -> "18"
    numeric_part = re.search(r'\d+', job_id)
    if not numeric_part:
        await websocket.send_json({"type": "error", "message": "Invalid job ID"})
        await websocket.close()
        return
    job_id_clean = numeric_part.group()
    
    logger.info(f"[Voice {interview_type}] Starting - Job: {job_id_clean}, User: {user_id[:8]}...")
    
    try:
        full_context = fetch_interview_context(user_id, job_id_clean)
        full_context["user_id"] = user_id
        full_context["job_id"] = job_id_clean
        logger.info(f"[Voice {interview_type}] Context: {full_context['job']['title']} | {full_context['user']['name']}")
    except Exception as e:
        logger.error(f"Context Error: {e}")
        await websocket.send_json({"type": "error", "message": f"Failed to load interview context: {str(e)}"})
        await websocket.close()
        return

    thread_id = f"voice_{user_id}_{job_id}_{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    state = create_voice_state(full_context, interview_type=interview_type, user_id=user_id, job_id=job_id_clean)
    
    # Send interview config to frontend
    await websocket.send_json({
        "type": "config",
        "interview_type": interview_type,
        "job_title": full_context['job'].get('title', 'Unknown'),
        "user_name": full_context['user'].get('name', 'Candidate')
    })
    
    # State: THINKING - AI generating welcome message
    audio_state = AudioState.THINKING
    await websocket.send_json({"type": "event", "event": "audio_state", "state": "thinking"})
    logger.info("[Voice] State -> THINKING")
    
    welcome_start = time.time()
    result = voice_interview_graph.invoke(state, config=config)
    welcome_text = result["messages"][-1].content if result["messages"] else "Hello!"
    
    # State: SPEAKING - AI speaking welcome
    audio_state = AudioState.SPEAKING
    await websocket.send_json({"type": "event", "event": "audio_state", "state": "speaking"})
    logger.info("[Voice] State -> SPEAKING")
    
    tts_start = time.time()
    clean_welcome = welcome_text.replace('**', '').replace('*', '').replace('_', '').replace('~~', '')
    welcome_audio = synthesize_audio_bytes(clean_welcome)
    tts_time = time.time() - tts_start
    logger.info(f"⏱️ Welcome TTS: {tts_time:.2f}s, Total: {time.time() - welcome_start:.2f}s")
    
    await websocket.send_json({"type": "event", "event": "stage_change", "stage": result.get("stage", "intro")})
    await websocket.send_bytes(welcome_audio)
    
    # Calculate audio duration (16kHz, 16-bit = 32000 bytes/sec)
    audio_duration = len(welcome_audio) / 32000.0
    wait_time = max(audio_duration + 0.5, COOLDOWN_SECONDS)
    logger.info(f"[Voice] Audio duration: {audio_duration:.2f}s, waiting {wait_time:.2f}s before listening")
    await asyncio.sleep(wait_time)
    
    # State: LISTENING - Ready for user input
    audio_state = AudioState.LISTENING
    await websocket.send_json({"type": "event", "event": "audio_state", "state": "listening"})
    logger.info("[Voice] State -> LISTENING")
    
    audio_buffer = bytearray()
    silence_start_time = None
    is_speaking = False
    last_ai_response_time = time.time()
    
    try:
        while result.get("stage") != "end" and not result.get("ending"):
            data = await websocket.receive_bytes()
            
            # CRITICAL: Only process audio when in LISTENING state
            if audio_state != AudioState.LISTENING:
                continue
            
            # Ignore buffered audio during cooldown
            if time.time() - last_ai_response_time < COOLDOWN_SECONDS:
                continue
            
            audio_buffer.extend(data)
            rms = calculate_rms(data)
            
            if rms > SILENCE_THRESHOLD:
                is_speaking = True
                silence_start_time = None
            elif is_speaking:
                if silence_start_time is None:
                    silence_start_time = asyncio.get_event_loop().time()
                
                if (asyncio.get_event_loop().time() - silence_start_time) >= SILENCE_DURATION:
                    logger.info(f"[Voice {interview_type}] Processing user audio...")
                    
                    # State: THINKING
                    audio_state = AudioState.THINKING
                    await websocket.send_json({"type": "event", "event": "audio_state", "state": "thinking"})
                    logger.info("[Voice] State -> THINKING")
                    
                    turn_start = time.time()
                    
                    # Transcription
                    transcribe_start = time.time()
                    user_text = transcribe_audio_bytes(bytes(audio_buffer))
                    transcribe_time = time.time() - transcribe_start
                    
                    # Clear buffer
                    audio_buffer = bytearray()
                    is_speaking = False
                    silence_start_time = None
                    
                    if user_text.strip():
                        logger.info(f"[Voice {interview_type}] User: {user_text[:50]}...")
                        logger.info(f"⏱️ Transcription: {transcribe_time:.2f}s")
                        
                        # LLM Inference
                        llm_start = time.time()
                        state = add_voice_message(result, user_text)
                        result = voice_interview_graph.invoke(state, config=config)
                        llm_time = time.time() - llm_start
                        
                        ai_text = result["messages"][-1].content if result["messages"] else "Could you repeat?"
                        current_stage = result.get("stage", "unknown")
                        
                        logger.info(f"[Voice {interview_type}] Stage: {current_stage} | Turn: {result.get('turn', 0)}")
                        logger.info(f"⏱️ Graph+LLM: {llm_time:.2f}s")
                        
                        # State: SPEAKING
                        audio_state = AudioState.SPEAKING
                        await websocket.send_json({"type": "event", "event": "audio_state", "state": "speaking"})
                        logger.info("[Voice] State -> SPEAKING")
                        await websocket.send_json({"type": "event", "event": "stage_change", "stage": current_stage})
                        
                        # Audio Synthesis
                        tts_start = time.time()
                        clean_text = ai_text.replace('**', '').replace('*', '').replace('_', '').replace('~~', '')
                        audio_bytes = synthesize_audio_bytes(clean_text)
                        tts_time = time.time() - tts_start
                        logger.info(f"⏱️ Audio TTS: {tts_time:.2f}s")
                        
                        await websocket.send_bytes(audio_bytes)
                        
                        total_time = time.time() - turn_start
                        logger.info(f"⏱️ TOTAL TURN: {total_time:.2f}s")
                        
                        # Wait for audio to finish before listening again
                        audio_duration = len(audio_bytes) / 32000.0
                        wait_time = max(audio_duration + 0.5, COOLDOWN_SECONDS)
                        logger.info(f"[Voice] Audio duration: {audio_duration:.2f}s, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                        
                        last_ai_response_time = time.time()
                        
                        # Check if interview is ending
                        if current_stage == "end" or result.get("ending"):
                            logger.info(f"[Voice {interview_type}] Interview ending...")
                            
                            # Send goodbye audio
                            goodbye_msg = "Thank you for your time today. We'll review and be in touch soon."
                            await websocket.send_bytes(synthesize_audio_bytes(goodbye_msg))
                            await asyncio.sleep(3)
                            
                            # Run evaluation
                            try:
                                logger.info(f"[Voice] Running evaluation with user_id: {user_id[:8]}..., job_id: {job_id_clean}")
                                
                                # Directly run evaluation (bypasses graph interrupt_after)
                                final_result = await asyncio.to_thread(
                                    run_evaluation,
                                    result
                                )
                                feedback = final_result.get("feedback")
                                
                                if feedback:
                                    logger.info(f"✅ Feedback saved: {feedback.get('verdict')} - Score: {feedback.get('score')}")
                                    await websocket.send_json({"type": "feedback", "data": feedback})
                                    
                                    verdict = feedback.get("verdict", "Thank you")
                                    score = feedback.get("score", 0)
                                    feedback_msg = f"{verdict}. Score: {score}. We'll be in touch soon."
                                    await websocket.send_bytes(synthesize_audio_bytes(feedback_msg))
                                    await asyncio.sleep(3)
                                else:
                                    logger.warning("[Voice] No feedback returned from evaluation")
                            except Exception as eval_error:
                                logger.error(f"Evaluation error: {eval_error}")
                                import traceback
                                traceback.print_exc()
                            
                            await websocket.close()
                            break
                        
                        # State: LISTENING - Ready for next input
                        audio_state = AudioState.LISTENING
                        await websocket.send_json({"type": "event", "event": "audio_state", "state": "listening"})
                        logger.info("[Voice] State -> LISTENING")
                    else:
                        # No valid transcription - go back to listening
                        logger.info("[Voice] Empty transcription, back to listening")
                        audio_state = AudioState.LISTENING
                        await websocket.send_json({"type": "event", "event": "audio_state", "state": "listening"})
                        last_ai_response_time = time.time()

    except WebSocketDisconnect:
        logger.info(f"[Voice {interview_type}] Client Disconnected")
        return
    
    # === INTERVIEW ENDED - PROCESS FEEDBACK OUTSIDE THE LOOP ===
    logger.info(f"[Voice {interview_type}] Interview loop ended - processing feedback...")
    
    # Let frontend know we're processing
    try:
        await websocket.send_json({"type": "event", "event": "processing", "status": "start"})
    except:
        pass
    
    # Send goodbye audio
    try:
        goodbye_msg = "Thank you for your time today. We'll review your responses and provide feedback shortly."
        await websocket.send_bytes(synthesize_audio_bytes(goodbye_msg))
        await asyncio.sleep(3)
    except:
        pass
    
    # Run evaluation
    try:
        logger.info(f"[Voice] Running evaluation with user_id: {user_id[:8]}..., job_id: {job_id_clean}")
        
        # Directly run evaluation
        final_result = await asyncio.to_thread(run_evaluation, result)
        feedback = final_result.get("feedback")
        
        if feedback:
            logger.info(f"✅ Feedback saved: {feedback.get('verdict')} - Score: {feedback.get('score')}")
            await websocket.send_json({"type": "feedback", "data": feedback})
            
            verdict = feedback.get("verdict", "Thank you")
            score = feedback.get("score", 0)
            feedback_msg = f"{verdict}. Score: {score}. We'll be in touch soon."
            await websocket.send_bytes(synthesize_audio_bytes(feedback_msg))
            await asyncio.sleep(3)
        else:
            logger.warning("[Voice] No feedback returned from evaluation")
            # Send empty feedback so frontend can still transition
            await websocket.send_json({
                "type": "feedback", 
                "data": {
                    "score": 0,
                    "verdict": "Unable to evaluate",
                    "summary": "An error occurred during evaluation. Please try again."
                }
            })
    except Exception as eval_error:
        logger.error(f"Evaluation error: {eval_error}")
        import traceback
        traceback.print_exc()
        # Send error feedback
        try:
            await websocket.send_json({
                "type": "feedback",
                "data": {
                    "score": 0,
                    "verdict": "Evaluation Error",
                    "summary": f"Error: {str(eval_error)}"
                }
            })
        except:
            pass
    
    # Clean close
    try:
        await websocket.close()
    except:
        pass
