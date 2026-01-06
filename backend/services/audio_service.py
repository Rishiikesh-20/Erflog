import os
from google.cloud import speech, texttospeech

# Set credentials path - Docker sets this via ENV, fallback for local dev
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credential.json"

speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

def transcribe_audio_bytes(audio_content: bytes) -> str:
    if not audio_content: return ""
    
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, 
        sample_rate_hertz=16000, 
        language_code="en-US",
        enable_automatic_punctuation=True,
        model="latest_short"
    )
    
    try:
        response = speech_client.recognize(config=config, audio=audio)
        return response.results[0].alternatives[0].transcript if response.results else ""
    except Exception as e:
        print(f"STT Error: {e}")
        return ""

def synthesize_audio_bytes(text: str) -> bytes:
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Journey-D", 
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.1
    )
    
    try:
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        print(f"TTS Error: {e}")
        return b""
