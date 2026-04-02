import streamlit as st
from AudioRecorder import audiorecorder
import requests

FASTAPI_URL = "http://localhost:8000"

st.title("🔮 Akinator PDAI")

tab_game, tab_chat = st.tabs(["🎮 Play Akinator", "💬 Ask a Question"])


# ---------------------------------------------------------------------------
# TAB 1 — Akinator guessing game
# ---------------------------------------------------------------------------
with tab_game:
    # Initialise session state for the game
    if "game_session_id" not in st.session_state:
        st.session_state.game_session_id = None
    if "game_question" not in st.session_state:
        st.session_state.game_question = None
    if "game_remaining" not in st.session_state:
        st.session_state.game_remaining = None
    if "game_done" not in st.session_state:
        st.session_state.game_done = False
    if "game_guess" not in st.session_state:
        st.session_state.game_guess = None
    if "game_history" not in st.session_state:
        st.session_state.game_history = []

    def start_new_game():
        try:
            res = requests.post(f"{FASTAPI_URL}/start", timeout=10)
            if res.status_code == 200:
                data = res.json()
                st.session_state.game_session_id = data["session_id"]
                st.session_state.game_question = data["question"]
                st.session_state.game_remaining = data["remaining"]
                st.session_state.game_done = False
                st.session_state.game_guess = None
                st.session_state.game_history = []
            else:
                st.error("Failed to start game.")
        except requests.exceptions.RequestException:
            st.error("Backend is not running. Start FastAPI with: uvicorn main:app --reload --port 8000")

    def send_answer(answer: str):
        try:
            res = requests.post(
                f"{FASTAPI_URL}/answer",
                json={"session_id": st.session_state.game_session_id, "answer": answer},
                timeout=10,
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("error"):
                    st.error(data["error"])
                    return
                st.session_state.game_history.append(
                    (st.session_state.game_question, answer)
                )
                st.session_state.game_remaining = data["remaining"]
                if data["done"]:
                    st.session_state.game_done = True
                    st.session_state.game_guess = data["guess"]
                else:
                    st.session_state.game_question = data["question"]
            else:
                st.error("Error communicating with backend.")
        except requests.exceptions.RequestException:
            st.error("Backend is not running.")

    # --- UI ---
    st.markdown("Think of a **classmate**. I'll try to guess who it is by asking yes/no questions!")

    if st.button("🚀 Start New Game"):
        start_new_game()
        st.rerun()

    if st.session_state.game_session_id and not st.session_state.game_done:
        remaining = st.session_state.game_remaining
        st.progress(
            max(0.0, 1.0 - (remaining / 26)),
            text=f"🔍 {remaining} candidate(s) remaining",
        )

        st.markdown(f"### ❓ {st.session_state.game_question}")

        col_yes, col_no, col_maybe = st.columns(3)
        with col_yes:
            if st.button("✅ Yes", use_container_width=True):
                send_answer("yes")
                st.rerun()
        with col_no:
            if st.button("❌ No", use_container_width=True):
                send_answer("no")
                st.rerun()
        with col_maybe:
            if st.button("🤷 Maybe", use_container_width=True):
                send_answer("maybe")
                st.rerun()

        # History
        if st.session_state.game_history:
            with st.expander("📜 Questions so far"):
                for q, a in st.session_state.game_history:
                    icon = "✅" if a == "yes" else ("❌" if a == "no" else "🤷")
                    st.write(f"{icon} **{q}** → {a}")

    if st.session_state.game_done and st.session_state.game_guess:
        st.balloons()
        st.success(st.session_state.game_guess)
        if st.button("🔄 Play Again"):
            start_new_game()
            st.rerun()


# ---------------------------------------------------------------------------
# TAB 2 — Free-form chat (existing RAG pipeline)
# ---------------------------------------------------------------------------
with tab_chat:
    st.markdown("Ask anything about your classmates. Powered by the RAG pipeline.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Text Input")
        user_text = st.text_input("Type your question here:", key="text_input")

    with col2:
        st.subheader("Voice Input")
        audio = audiorecorder("Click to record", "Click to stop recording")

    if len(audio) > 0:
        st.info("Transcribing audio...")
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
            st.error("Backend is not running.")

    if st.button("Submit", key="chat_submit"):
        if user_text.strip():
            with st.spinner("Processing with Agent..."):
                try:
                    res = requests.post(
                        f"{FASTAPI_URL}/chat",
                        json={"message": user_text},
                        timeout=180,
                    )
                    if res.status_code == 200:
                        answer = res.json().get("reply", "")
                        st.markdown(f"**Akinator Response:**\n > {answer}")
                    else:
                        st.error("Error connecting to the backend.")
                except requests.exceptions.RequestException:
                    st.error("Backend is not running.")
