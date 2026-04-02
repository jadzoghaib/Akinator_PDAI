from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from whisper_model import transcribe_audio
from database import init_db
from langchain_agents import get_public_agent, get_spicy_agent, get_router_agent
from game_engine import load_all_candidates, best_next_question, filter_candidates
import traceback


def build_groq_llm():
    from langchain_groq import ChatGroq
    return ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, max_tokens=128)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory game sessions: {session_id: game_state}
games: dict = {}


class ChatRequest(BaseModel):
    message: str


class AnswerRequest(BaseModel):
    session_id: str
    answer: str  # "yes" | "no" | "maybe"


@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized.")
    app.state.master_router = build_master_router()
    print("Master Router initialized.")


# ---------------------------------------------------------------------------
# Akinator game endpoints
# ---------------------------------------------------------------------------

@app.post("/start")
async def start_game():
    """Start a new Akinator game session. Returns the first question."""
    session_id = str(uuid.uuid4())
    all_data = load_all_candidates()
    first_q = best_next_question(all_data, [])

    games[session_id] = {
        "data": all_data,
        "asked": [],
        "history": [],
        "current_q": first_q,
    }

    return {
        "session_id": session_id,
        "question": first_q["text"],
        "remaining": len(all_data),
    }


@app.post("/answer")
async def answer_question(request: AnswerRequest):
    """Process the user's answer, filter candidates, return next question or final guess."""
    game = games.get(request.session_id)
    if game is None:
        return {"error": "Session not found. Please start a new game."}

    current_q = game.get("current_q")
    if current_q is None:
        return {"error": "No active question found."}

    # Filter candidates based on the answer
    game["data"] = filter_candidates(
        game["data"], current_q["column"], current_q["yes_value"], request.answer
    )
    game["asked"].append(current_q["column"])
    game["history"].append((current_q["text"], request.answer))

    remaining = len(game["data"])

    if remaining == 1:
        name = list(game["data"].keys())[0]
        return {"done": True, "guess": _make_guess(name, game["history"]), "remaining": 1}

    if remaining == 0:
        return {"done": True, "guess": "You stumped me! I couldn't figure it out. You win this round! 🏆", "remaining": 0}

    next_q = best_next_question(game["data"], game["asked"])
    if next_q is None:
        # Ran out of distinguishing questions — best guess
        name = list(game["data"].keys())[0]
        return {"done": True, "guess": _make_guess(name, game["history"]), "remaining": remaining}

    game["current_q"] = next_q

    return {
        "done": False,
        "question": next_q["text"],
        "remaining": remaining,
    }


def _make_guess(name: str, history: list) -> str:
    from gossip import GOSSIP_DATA
    gossip = GOSSIP_DATA.get(name, "")
    clues = "; ".join([f"{q} → {a}" for q, a in history[-3:]])
    extra = (
        f" I also happen to know: {gossip[:120]}."
        if gossip and gossip != "Information not detailed in notes."
        else ""
    )
    return (
        f"🎉 I've got it! It's **{name}**! "
        f"The clues that gave it away: {clues}.{extra}"
    )


# ---------------------------------------------------------------------------
# Transcription endpoint
# ---------------------------------------------------------------------------

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    temp_dir = "./temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, audio.filename or "recording.wav")

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    try:
        text = transcribe_audio(temp_file_path)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return {"transcribed_text": text}


# ---------------------------------------------------------------------------
# Free-form chat endpoint (existing LangChain RAG pipeline)
# ---------------------------------------------------------------------------

def build_master_router():
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import SentenceTransformerEmbeddings
    from langchain_core.tools import Tool

    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    public_vs = Chroma(persist_directory="./chroma_db", collection_name="akinator_data", embedding_function=embeddings)
    spicy_vs = Chroma(persist_directory="./chroma_db", collection_name="akinator_data", embedding_function=embeddings)

    def query_public_data(query: str):
        docs = public_vs.similarity_search(query, k=2, filter={"data_tier": "public"})
        return "\n".join([d.page_content for d in docs])

    def query_spicy_data(query: str):
        docs = spicy_vs.similarity_search(query, k=2, filter={"data_tier": "spicy"})
        return "\n".join([d.page_content for d in docs])

    public_tool = Tool(
        name="Public_Retriever",
        func=query_public_data,
        description="Search for a person's major, LinkedIn, public resume details.",
    )
    spicy_tool = Tool(
        name="Spicy_Retriever",
        func=query_spicy_data,
        description="Search for secrets, hobbies, weird habits, or highly personalized gossip.",
    )

    llm = build_groq_llm()
    public_agent = get_public_agent(llm, public_tool)
    spicy_agent = get_spicy_agent(llm, spicy_tool)
    return get_router_agent(public_agent, spicy_agent, llm)


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        user_query = request.message.strip()
        master_router = getattr(app.state, "master_router", None)
        if master_router is None:
            app.state.master_router = build_master_router()
            master_router = app.state.master_router

        response = master_router.invoke({"input": user_query})
        output_reply = response.get("output", "")
        return {"reply": output_reply}
    except Exception as e:
        traceback.print_exc()
        return {"reply": f"Langchain Pipeline Error: {str(e)}"}
