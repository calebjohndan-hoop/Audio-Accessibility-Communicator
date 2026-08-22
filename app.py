"""
Audio-Accessibility Communicator
=================================
An AAC (Augmentative and Alternative Communication) dashboard for mute individuals and people with temporary vocal loss.
Big touch-friendly buttons trigger instant text-to-speech; 
Gemini adds AI-generated custom phrases and a vision mode for pointing the camera at things instead of speaking about them.

Run:  streamlit run app.py
"""

import datetime as dt
import pandas as pd
import streamlit as st

from ai_utils import generate_phrase, describe_scene
from tts_utils import speak


st.set_page_config(
    page_title="Audio-Accessibility Communicator",
    page_icon="🔊",
    layout="wide",
)

st.markdown(
    """
    <style>
    div.stButton > button {
        height: 4.5em;
        width: 100%;
        font-size: 1.15em;
        font-weight: 600;
        border-radius: 16px;
        white-space: normal;
    }
    .emergency button {
        background-color: #d32f2f !important;
        color: white !important;
    }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


if "log" not in st.session_state:
    
    st.session_state.log = pd.DataFrame(
        columns=["timestamp", "category", "phrase"]
    )

if "custom_phrases" not in st.session_state:
    st.session_state.custom_phrases = pd.DataFrame(
        [
            {"label": "I need my family", "phrase": "Please call my family, I need them here."},
            {"label": "Turn off the light", "phrase": "Could you please turn off the light?"},
            {"label": "I'm anxious", "phrase": "I'm feeling anxious, can you stay with me a moment?"},
        ]
    )

if "location" not in st.session_state:
    
    st.session_state.location = {"lat": 0, "lon": 0}


def log_phrase(category: str, phrase: str) -> None:
    new_row = {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "phrase": phrase,
    }
    st.session_state.log = pd.concat(
        [st.session_state.log, pd.DataFrame([new_row])], ignore_index=True
    )


def say(category: str, phrase: str) -> None:
    log_phrase(category, phrase)
    speak(phrase, key=f"{category}-{len(st.session_state.log)}")



st.markdown(
    '<h1 style="color:#d32f2f;">🔊 Audio-Accessibility Communicator</h1>',
    unsafe_allow_html=True,
)
st.caption("Tap a button. It speaks for you — instantly.")

log_df = st.session_state.log
today = dt.date.today().isoformat()
spoken_today = log_df[log_df["timestamp"].str.startswith(today)] if not log_df.empty else log_df
total_ever = len(log_df)
top_category = (
    log_df["category"].value_counts().idxmax() if not log_df.empty else "—"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Phrases spoken today", len(spoken_today), delta=f"+{len(spoken_today)}")
col2.metric("Total phrases ever", total_ever)
col3.metric("Most used category", top_category)
col4.metric("Custom phrases saved", len(st.session_state.custom_phrases))

st.divider()

# --------------------------------------------------------------------------
# Emergency grid
# --------------------------------------------------------------------------
st.subheader("🚨 Emergency")
emergency_phrases = [
    ("Call 911", "Please call 911 right now, this is an emergency."),
    ("I need help NOW", "I need help immediately, please don't leave."),
    ("Chest pain", "I am having chest pain and I cannot speak."),
    ("Can't breathe", "I am having trouble breathing, please get help now."),
    ("Call my contact", "Please call my emergency contact immediately."),
]
e_cols = st.columns(len(emergency_phrases))
for col, (label, phrase) in zip(e_cols, emergency_phrases):
    with col:
        st.markdown('<div class="emergency">', unsafe_allow_html=True)
        if st.button(label, key=f"em-{label}", use_container_width=True):
            say("Emergency", phrase)
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# --------------------------------------------------------------------------
# Daily communication grid
# --------------------------------------------------------------------------
st.subheader("💬 Daily Communication")
daily_phrases = [
    ("Yes", "Yes."),
    ("No", "No."),
    ("Thank you", "Thank you very much."),
    ("Please wait", "One moment please, I'm trying to communicate."),
    ("I'm in pain", "I am in pain right now."),
    ("I need water", "Could I have some water, please?"),
    ("Bathroom", "I need to use the bathroom, please."),
    ("I'm cold", "I am feeling cold, could I have a blanket?"),
]
rows = [daily_phrases[i:i + 4] for i in range(0, len(daily_phrases), 4)]
for row in rows:
    d_cols = st.columns(4)
    for col, (label, phrase) in zip(d_cols, row):
        with col:
            if st.button(label, key=f"daily-{label}", use_container_width=True):
                say("Daily", phrase)

st.divider()

# --------------------------------------------------------------------------
# Custom phrases (user-editable quick-access grid)
# --------------------------------------------------------------------------
st.subheader("⭐ My Custom Phrases")
c_cols = st.columns(4)
for i, row in st.session_state.custom_phrases.iterrows():
    with c_cols[i % 4]:
        if st.button(row["label"], key=f"custom-{i}", use_container_width=True):
            say("Custom", row["phrase"])

with st.expander("Edit my custom phrases"):
    edited = st.data_editor(
        st.session_state.custom_phrases,
        num_rows="dynamic",
        use_container_width=True,
        key="custom_editor",
    )
    if st.button("Save changes"):
        st.session_state.custom_phrases = edited
        st.success("Custom phrases updated.")
        st.rerun()

st.divider()

# --------------------------------------------------------------------------
# AI phrase generator (Gemini text) — wrapped in st.form to avoid firing an API call on every keystroke.
# --------------------------------------------------------------------------
st.subheader("🤖 AI Phrase Generator")
st.caption("Describe what you want to say in a few words — Gemini turns it into a clean, speakable sentence.")

with st.form("ai_phrase_form", clear_on_submit=False):
    fcol1, fcol2 = st.columns([3, 1])
    rough_idea = fcol1.text_input("What do you want to say?", placeholder="e.g. tell nurse leg hurts since morning")
    urgency = fcol2.selectbox("Urgency", ["normal", "high"])
    submitted = st.form_submit_button("Generate & Speak", use_container_width=True)

if submitted and rough_idea.strip():
    with st.spinner("Generating phrase..."):
        generated = generate_phrase(rough_idea, urgency=urgency)
    st.info(f"**Generated:** {generated}")
    say("AI-Generated", generated)
    if st.button("💾 Save this as a custom button"):
        st.session_state.custom_phrases = pd.concat(
            [st.session_state.custom_phrases, pd.DataFrame([{"label": rough_idea[:20], "phrase": generated}])],
            ignore_index=True,
        )
        st.rerun()

st.divider()

# --------------------------------------------------------------------------
# Vision assistant (Gemini multimodal) — point camera at something instead of talking about it.
# --------------------------------------------------------------------------
st.subheader("📷 Point-and-Speak (Vision Assistant)")
st.caption("Can't describe it in words? Point the camera at it — Gemini Vision describes it for you.")

camera_image = st.camera_input("Take a photo to describe", key="camera")
if camera_image is not None:
    if st.button("Describe & Speak", key="describe-btn"):
        with st.spinner("Looking..."):
            description = describe_scene(camera_image.getvalue())
        st.info(f"**AI sees:** {description}")
        say("Vision", description)

st.divider()

# --------------------------------------------------------------------------
# Location sharing (emergency support)
# --------------------------------------------------------------------------
st.subheader("📍 Share My Location")
lcol1, lcol2, lcol3 = st.columns([1, 1, 2])
lat = lcol1.number_input(
    "Latitude",
    value=float(st.session_state.location["lat"]),
    min_value=-90.0,
    max_value=90.0,
    step=0.0001,
    format="%.4f",
)
lon = lcol2.number_input(
    "Longitude",
    value=float(st.session_state.location["lon"]),
    min_value=-180.0,
    max_value=180.0,
    step=0.0001,
    format="%.4f",
)
st.session_state.location = {"lat": lat, "lon": lon}
if lcol3.button("Announce my location", use_container_width=True):
    say("Location", f"My current location is latitude {lat}, longitude {lon}. Please come find me.")

st.map(pd.DataFrame([st.session_state.location]), zoom=12)

st.divider()

# --------------------------------------------------------------------------
# Communication log & analytics
# --------------------------------------------------------------------------
st.subheader("📊 Communication Log")
if st.session_state.log.empty:
    st.write("No phrases spoken yet — tap a button above to get started.")
else:
    lcol, ccol = st.columns([2, 1])
    with lcol:
        st.dataframe(
            st.session_state.log.sort_values("timestamp", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    with ccol:
        st.bar_chart(st.session_state.log["category"].value_counts())

    if st.button("Clear log"):
        st.session_state.log = st.session_state.log.iloc[0:0]
        st.rerun()

st.caption("Built by Caleb")
