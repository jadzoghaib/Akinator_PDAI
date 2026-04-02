import streamlit as st
from audiorecorder import audiorecorder
import requests
import io

FASTAPI_URL = "http://localhost:8000"

st.title("Akinator PDAI with Voice")

st.markdown("### 1. Speak or Type")
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Text Input")
    user_text = st.text_input("Type your question here:", key="text_input")

with col2:
    st.subheader("Voice Input")
    audio = audiorecorder("Click to record", "Click to stop recording")

# Handle what comes through (voice > text)
if len(audio) > 0:
    st.info("Transcribing audio...")
    # Send to FastAPI /transcribe endpoint
    files = {"audio": ("audio.wav", audio.export(format="wav").read(), "audio/wav")}
    try:
        response = requests.post(f"{FASTAPI_URL}/transcribe", files=files, timeout=120)
        if response.status_code == 200:
            transcribed_text = response.json().get("transcribed_text", "")
            st.success(f"Recognized: {transcribed_text}")
            user_text = transcribed_text
        else:
            st.error("Failed to transcribe audio.")
    except requests.exceptions.RequestException:
        st.error("Backend is not running. Start FastAPI with: uvicorn main:app --reload --port 8000")

# Proceed to chat only when user explicitly submits
if st.button("Submit"):
    if user_text.strip():
        with st.spinner("Processing with Agent..."):
            chat_payload = {"message": user_text}
            try:
                res = requests.post(f"{FASTAPI_URL}/chat", json=chat_payload, timeout=180)
                if res.status_code == 200:
                    answer = res.json().get("reply", "")
                    st.markdown(f"**Akinator Response:**\n > {answer}")
                else:
                    st.error("Error connecting to the backend.")
            except requests.exceptions.RequestException:
                st.error("Backend is not running. Start FastAPI with: uvicorn main:app --reload --port 8000")
