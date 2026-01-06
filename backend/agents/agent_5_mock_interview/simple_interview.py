"""
Simple Interview Agent - No LangGraph, just direct Gemini calls with state tracking.
Max 15 messages, 4 stages: intro -> resume -> gap_challenge -> conclusion
"""
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Agent5")

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)

# Simple 4-stage flow
STAGES = ["intro", "resume", "gap_challenge", "conclusion"]

class SimpleInterview:
    def __init__(self, context: dict):
        self.context = context
        self.job = context.get('job', {})
        self.user = context.get('user', {})
        self.gaps = context.get('gaps', {})
        self.messages = []  # Conversation history
        self.stage_idx = 0
        self.turn_count = 0
        self.max_turns = 15
        
        self._log_context()
    
    def _log_context(self):
        logger.info("=" * 60)
        logger.info("[AGENT 5] INTERVIEW INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"📋 JOB: {self.job.get('title', 'Unknown')} at {self.job.get('company', 'Unknown')}")
        logger.info(f"👤 CANDIDATE: {self.user.get('name', 'Unknown')}")
        logger.info(f"🛠️  SKILLS: {', '.join(self.user.get('skills', [])[:5])}")
        logger.info(f"📊 SIMILARITY: {self.gaps.get('similarity_score', 0):.1%}")
        logger.info(f"⚠️  GAPS: {self.gaps.get('missing_skills', [])}")
        logger.info("=" * 60)
    
    @property
    def current_stage(self) -> str:
        return STAGES[min(self.stage_idx, len(STAGES) - 1)]
    
    @property
    def is_complete(self) -> bool:
        return self.stage_idx >= len(STAGES) or self.turn_count >= self.max_turns
    
    def _build_prompt(self) -> str:
        stage = self.current_stage
        
        base = f"""You are interviewing {self.user.get('name', 'the candidate')} for {self.job.get('title', 'a position')} at {self.job.get('company', 'our company')}.

CANDIDATE INFO:
- Skills: {', '.join(self.user.get('skills', ['Not specified'])[:8])}
- Match Score: {self.gaps.get('similarity_score', 0):.0%}
- Skill Gaps: {', '.join(self.gaps.get('missing_skills', ['None'])[:3])}

RULES:
1. Be conversational and professional
2. Ask ONE question at a time
3. Keep responses to 2-3 sentences
4. Do NOT repeat previous questions
"""
        
        if stage == "intro":
            return base + f"""
CURRENT STAGE: INTRODUCTION
- Welcome {self.user.get('name', 'the candidate')} warmly
- Introduce yourself as the interviewer
- Ask them to give a brief introduction about themselves
"""
        
        elif stage == "resume":
            return base + f"""
CURRENT STAGE: RESUME DEEP-DIVE
- Ask about their experience related to: {self.job.get('summary', 'the role')[:150]}
- Focus on their projects or past work
- Ask follow-up questions based on their answers
"""
        
        elif stage == "gap_challenge":
            missing = self.gaps.get('missing_skills', ['advanced topics'])
            suggested = self.gaps.get('suggested_questions', [])
            return base + f"""
CURRENT STAGE: CHALLENGING QUESTIONS (Gap Analysis)
- The candidate may lack experience in: {', '.join(missing[:3])}
- Suggested questions: {suggested[:2] if suggested else ['Ask about their learning approach']}
- Ask challenging but fair questions to assess their potential
- Probe their problem-solving ability in weak areas
"""
        
        elif stage == "conclusion":
            return base + """
CURRENT STAGE: CONCLUSION
- Thank the candidate for their time
- Ask if they have any questions for you
- Provide a positive closing statement
- Mention that they'll hear back soon
"""
        
        return base
    
    def get_ai_response(self, user_input: str = None) -> str:
        """Get AI response, optionally processing user input first."""
        
        # Add user message if provided
        if user_input:
            self.messages.append(HumanMessage(content=user_input))
            self.turn_count += 1
            
            # Advance stage based on turn count
            if self.turn_count == 2:  # After intro response
                self.stage_idx = 1  # resume
            elif self.turn_count == 5:  # After resume questions
                self.stage_idx = 2  # gap_challenge
            elif self.turn_count == 9:  # After gap questions
                self.stage_idx = 3  # conclusion
        
        logger.info(f"[AGENT 5] Turn {self.turn_count} | Stage: {self.current_stage.upper()}")
        
        # Build messages for Gemini
        prompt = self._build_prompt()
        
        # Gemini needs messages ending with HumanMessage
        gemini_messages = []
        for msg in self.messages:
            gemini_messages.append(msg)
        
        # Add instruction as final human message
        if not gemini_messages or isinstance(gemini_messages[-1], AIMessage):
            gemini_messages.append(HumanMessage(content=prompt + "\n\n[Your response:]"))
        else:
            # Last was human, combine with prompt
            last_content = gemini_messages[-1].content
            gemini_messages[-1] = HumanMessage(content=f"{prompt}\n\nCandidate said: {last_content}\n\n[Your response:]")
        
        # Get response
        response = llm.invoke(gemini_messages)
        ai_text = response.content
        
        # Store AI response
        self.messages.append(AIMessage(content=ai_text))
        self.turn_count += 1
        
        logger.info(f"[AGENT 5] Response: {ai_text[:80]}...")
        
        return ai_text
    
    def get_feedback(self) -> dict:
        """Generate final evaluation."""
        logger.info("[AGENT 5] Generating final evaluation...")
        
        prompt = f"""Based on this interview for {self.job.get('title')} at {self.job.get('company')}:

Candidate: {self.user.get('name')}
Their skills: {self.user.get('skills', [])}
Identified gaps: {self.gaps.get('missing_skills', [])}

Conversation:
{self._format_conversation()}

Provide your evaluation as JSON only:
{{
    "score": <0-100>,
    "verdict": "Hire" or "No Hire" or "Maybe",
    "strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["area1", "area2"],
    "summary": "One sentence summary"
}}"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        try:
            content = response.content.replace("```json", "").replace("```", "").strip()
            feedback = json.loads(content)
            logger.info(f"[AGENT 5] Score: {feedback.get('score')}, Verdict: {feedback.get('verdict')}")
            return feedback
        except:
            logger.error("[AGENT 5] Failed to parse evaluation")
            return {"score": 50, "verdict": "Maybe", "summary": "Evaluation parsing failed", "raw": response.content}
    
    def _format_conversation(self) -> str:
        """Format conversation for evaluation."""
        lines = []
        for msg in self.messages[-10:]:  # Last 10 messages
            role = "Interviewer" if isinstance(msg, AIMessage) else "Candidate"
            lines.append(f"{role}: {msg.content[:200]}")
        return "\n".join(lines)


# Export for main.py
def create_interview(context: dict) -> SimpleInterview:
    return SimpleInterview(context)
