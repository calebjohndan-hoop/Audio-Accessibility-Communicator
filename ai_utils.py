"""
ai_utils.py
-----------
Gemini API integration layer for the Audio-Accessibility Communicator.
Rewrites rough user inputs into clean, speakable AAC phrases.

Uses the current `google-genai` SDK (the old `google-generativeai` package
is deprecated). Pinned to one stable, non-"thinking" model call so output
is always a single clean sentence, not a visible reasoning trace.
"""

import os
import streamlit as st
from google import genai
from google.genai import types

MODEL_NAME = "gemini-3.5-flash-lite"

PHRASE_SYSTEM_PROMPT = """You are a communication assistant embedded in an Augmentative and Alternative Communication (AAC) app 
for a person who is mute or has temporarily lost their voice (e.g. post-surgery, laryngitis, intubation recovery).
The user cannot speak and is typing or picking a rough idea of what they want to say. Your job: convert it into ONE short, clear, speakable 
sentence a text-to-speech engine will read aloud to a listener (a nurse, family member, or stranger).

Rules:
- Output ONLY the sentence. No preamble, no quotes, no explanation, no bullet points.
- Keep it under 20 words.
- First-person voice, as if the user is speaking it themselves.
- Neutral, calm, and easy to understand out loud.
- If the situation sounds medically urgent, keep the sentence direct and unambiguous.
"""

VISION_SYSTEM_PROMPT = """You are the eyes for a non-verbal person using an
AAC app. They have pointed their camera at something because they want to
communicate about it instead of speaking. Describe what you see in ONE
short first-person sentence suitable for text-to-speech, as if the user
were saying it themselves (e.g. "I am pointing at my medication bottle,
I think I need my next dose."). Output ONLY that sentence, nothing else,
no bullet points, no preamble. Keep it under 25 words.
"""


def _get_api_key() -> str | None:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and isinstance(key, str) and key.strip():
                return key.strip()
    except Exception:
        pass
    env_key = os.environ.get("GEMINI_API_KEY", None)
    return env_key.strip() if env_key else None


@st.cache_resource(show_spinner=False)
def _get_client():
    key = _get_api_key()
    if not key or "your_" in key.lower() or "your-" in key.lower():
        return None
    try:
        return genai.Client(api_key=key)
    except Exception:
        return None


def _clean(text: str) -> str:
    """Safety net: if the model still returns multiple lines/bullets,
    take the first non-empty, non-bullet line instead of the whole blob."""
    if not text:
        return ""
    for line in text.strip().splitlines():
        line = line.strip().lstrip("*-•").strip().strip('"')
        if line:
            return line
    return text.strip()


def generate_phrase(user_context: str, urgency: str = "normal") -> str:
    """Turn a rough description into one clean, speakable sentence."""
    clean_input = user_context.strip()
    if not clean_input:
        return ""

    client = _get_client()
    if client is None:
        return clean_input

    prompt = (
        f"Urgency level: {urgency}. "
        f'Rough idea from the user: "{clean_input}". '
        f"Produce the single speakable sentence now."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PHRASE_SYSTEM_PROMPT,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
                temperature=0.3,
                max_output_tokens=60,
            ),
        )
        text = _clean(response.text or "")
        return text if text else clean_input
    except Exception:
        return clean_input


def describe_scene(image_bytes: bytes) -> str:
    """Vision multimodality: describe a camera frame as a speakable sentence."""
    client = _get_client()
    if client is None:
        return "[Offline mode] Camera description requires a configured Gemini API key."

    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[image_part, "Describe this for the user to speak."],
            config=types.GenerateContentConfig(
                system_instruction=VISION_SYSTEM_PROMPT,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
                temperature=0.3,
                max_output_tokens=80,
            ),
        )
        text = _clean(response.text or "")
        return text if text else "I want to show you something, but I couldn't describe it clearly."
    except Exception:
        return "[AI unavailable] Could not analyze the image right now."
