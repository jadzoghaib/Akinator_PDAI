from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from dotenv import load_dotenv

load_dotenv()

from whisper_model import transcribe_audio
from database import init_db
from langchain_agents import get_public_agent, get_spicy_agent, get_router_agent
import traceback


def build_groq_llm():
    """Build the Groq chat model used by all agents."""
    from langchain_groq import ChatGroq

    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        max_tokens=128,
    )

# Initialize LangChain components when needed, or at startup.
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.on_event("startup")
async def startup_event():
    # Initialize DB dummy data on startup
    init_db()
    print("Database initialized and populated with dummy data (with data_tier).")
    app.state.master_router = build_master_router()
    print("Master Router initialized at startup.")

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Receives an audio file, stores it locally, transcribes it, and responds with the text."""
    temp_dir = "./temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, audio.filename or "recording.wav")
    
    # Save the file correctly
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
        
    try:
        text = transcribe_audio(temp_file_path)
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    return {"transcribed_text": text}

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
        description="Must be used to search for a person's major, LinkedIn, public resume details."
    )

    spicy_tool = Tool(
        name="Spicy_Retriever",
        func=query_spicy_data,
        description="Must be used to search for secrets, hobbies, weird habits, or highly personalized gossip."
    )

    llm = build_groq_llm()
    public_agent = get_public_agent(llm, public_tool)
    spicy_agent = get_spicy_agent(llm, spicy_tool)
    return get_router_agent(public_agent, spicy_agent, llm)

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Predictive Model -> Router -> LangChain Agent.
    Here we implement the real LangChain Architecture from langchain_agents.py
    """
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

