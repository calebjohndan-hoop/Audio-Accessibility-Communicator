"""
tts_utils.py
------------
Text-to-speech layer. Uses gTTS (Google Text-to-Speech) to synthesize
audio, and injects it into the page as an autoplaying HTML <audio> tag
so the phrase speaks immediately when a button is tapped — critical for
a person who cannot speak and needs the listener to hear it *now*,
without an extra "press play" step.
"""

import base64
import io
import streamlit as st
from gtts import gTTS


@st.cache_data(show_spinner=False, ttl=3600)
def synthesize(text: str, lang: str = "en") -> bytes:
    """Convert text to MP3 bytes. Cached so repeated phrases (e.g. 'Yes',
    'Thank you') don't re-hit the TTS engine every tap."""
    buf = io.BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
    buf.seek(0)
    return buf.read()


def speak(text: str, lang: str = "en", key: str = "") -> None:
    """Synthesize and autoplay `text` inline in the Streamlit app."""
    if not text.strip():
        return
    audio_bytes = synthesize(text, lang=lang)
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f"""
        <audio autoplay="true" key="{key}">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True,
    )
    # Visible fallback control in case autoplay is blocked by the browser.
    st.audio(audio_bytes, format="audio/mp3")
