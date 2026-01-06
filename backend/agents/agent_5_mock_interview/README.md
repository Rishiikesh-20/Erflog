# Agent 5 - Interview (Unified)

**Agent 5** is a conversational AI designed to conduct technical and behavioral mock interviews. It uses **LangGraph** to maintain state and **Gemini 2.0** to generate context-aware questions and feedback.

## Features

- **Mode Toggle** - Switch between `text` (chat) and `voice` modes
- **Conversational State** - Remembers entire interview history via LangGraph checkpoints
- **Staged Flow** - Progresses through 4 interview stages:
  1. **Intro** - Welcome and self-introduction
  2. **Resume** - Deep dive into skills and projects
  3. **Gap Challenge** - Questions on missing skills
  4. **Conclusion** - Wrap up and feedback
- **Context Awareness** - Tailors questions to Job Description and candidate answers

## API Endpoints

### Text Interview (WebSocket)
**WS** `/ws/interview/text/{job_id}`

### Voice Interview (WebSocket)  
**WS** `/ws/interview/{job_id}`

### Chat Interview (REST)
**POST** `/api/interview/chat`
```json
{
  "session_id": "uuid-session",
  "job_context": "Senior Python Developer at Google",
  "user_message": "I have 5 years of experience with Django..."
}
```

## Usage

```python
from agents.agent_5_interview.graph import (
    chat_interview_graph,
    voice_interview_graph,
    create_chat_state,
    create_voice_state,
    add_user_message
)

# Text interview
state = create_chat_state(context)
result = chat_interview_graph.invoke(state, config)

# Voice interview  
state = create_voice_state(context)
result = voice_interview_graph.invoke(state, config)
```
