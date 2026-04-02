from langchain_classic.agents import initialize_agent
from langchain_core.tools import Tool
from dotenv import load_dotenv

load_dotenv()

# You will need to set HUGGINGFACEHUB_API_TOKEN in your environment, e.g., os.environ["HUGGINGFACEHUB_API_TOKEN"] = "hf_..."

# --- SYSTEM PROMPTS ---

PUBLIC_AGENT_PROMPT = """
You are the Public Profile Agent. Your job is to answer questions about a person's public professional life, 
such as their technical background, LinkedIn profile, where they sit in class, and their preferred drinks.
Be playfully sarcastic, a bit sassy, and teasing, but still give the correct information!
If you don't know the answer based on the provided context, make a witty remark about how they must be hiding from you.
"""

SPICY_AGENT_PROMPT = """
You are the Spicy Info Agent (The Confidant). Your job is to answer questions about a person's secrets,
hidden hobbies, personal quirks, juicy gossip, and inside jokes.
You MUST be extremely playful, funny, full of drama, and a little bit roasting/teasing in your tone (in a good-hearted way, like a roasting comedian).
If you don't know the answer based on the provided context, dramatically complain that the tea wasn't spilled.
"""

ROUTER_AGENT_PROMPT = """
You are the Game Host: Akinator PDAI! You are playing a guessing game with the user.
The user is thinking of a specific classmate, and your goal is to guess who it is by asking the user ONE unique question at a time.
1. The user will provide free-form answers to your questions.
2. Based on their answers, use your tools (Public Profile Agent and Spicy Info Agent) to search the database and figure out who matches those clues.
3. If you still have multiple candidates, ASK the user another question (e.g., "Do they sit in the front row?" or "Do they like spicy dramas?").
4. If you know who it is, make your final dramatic guess!
Remember: Only ask ONE question at a time, and always act like a playful, sassy mind-reader.
"""

# --- AGENT SETUP ---

def get_public_agent(llm, public_retriever_tool):
    """Initializes the Agent responsible for public data (data_tier: public)."""
    tools = [public_retriever_tool]
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent="zero-shot-react-description",
        agent_kwargs={
            "system_message": PUBLIC_AGENT_PROMPT
        },
        verbose=True,
        handle_parsing_errors=True
    )
    return agent

def get_spicy_agent(llm, spicy_retriever_tool):
    """Initializes the Agent responsible for spicy/secret data (data_tier: spicy)."""
    tools = [spicy_retriever_tool]
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent="zero-shot-react-description",
        agent_kwargs={
            "system_message": SPICY_AGENT_PROMPT
        },
        verbose=True,
        handle_parsing_errors=True
    )
    return agent

def get_router_agent(public_agent, spicy_agent, llm):
    """
    The Router Agent that decides which sub-agent to call.
    """
    tools = [
        Tool(
            name="Public Profile Agent",
            func=public_agent.run,
            description="Use this tool when answering questions about a person's major, LinkedIn, professional skills, or public info."
        ),
        Tool(
            name="Spicy Info Agent",
            func=spicy_agent.run,
            description="Use this tool when answering questions about a person's secrets, hobbies, or personal life."
        )
    ]
    
    from langchain_classic.memory import ConversationBufferMemory
    memory = ConversationBufferMemory(memory_key="chat_history")
    
    router_agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent="conversational-react-description",
        memory=memory,
        agent_kwargs={
            "system_message": ROUTER_AGENT_PROMPT
        },
        verbose=True,
        handle_parsing_errors=True
    )
    return router_agent
