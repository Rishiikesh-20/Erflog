# Agent 5 - Interview Voice Bot (Experimental)

**Agent 5** adds a voice interface to the interview practice loop, allowing candidates to speak their answers instead of typing.

## Features

- **Audio Processing** - Ingests raw audio bytes from the frontend.
- 🗣️ **Speech-to-Text (STT)** - (Planned) Converts candidate speech to text for analysis.
- **Text-to-Speech (TTS)** - (Planned) plays back the interviewer's questions.

## Status

**Current State**: `Experimental / Alpha`

This agent is currently a foundational module designed to wrap the text-based logic of Agent 6 with an audio processing layer. It is intended to run on the client-side or via a websocket stream for low-latency interaction.
