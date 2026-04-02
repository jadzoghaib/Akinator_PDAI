import chromadb
from chromadb.utils import embedding_functions

CHROMA_DATA_PATH = "./chroma_db"

def init_db():
    client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    collection_name = "akinator_data"
    # Delete if exists to refresh dummy data on start
    try:
        client.delete_collection(name=collection_name)
    except ValueError:
        pass
    
    collection = client.create_collection(
        name=collection_name, 
        embedding_function=embedding_func
    )

    # Insert dummy data with segregated tier tagging
    dummy_docs = [
        "Major: Software Engineering",
        "LinkedIn skills: Python, React, AWS",
        "Secret: I am afraid of clowns",
        "Hobbies: Collecting rare stamps, watching spicy dramas"
    ]
    
    metadatas = [
        {"data_tier": "public"},
        {"data_tier": "public"},
        {"data_tier": "spicy"},
        {"data_tier": "spicy"}
    ]
    
    ids = ["doc1", "doc2", "doc3", "doc4"]

    collection.add(
        documents=dummy_docs,
        metadatas=metadatas,
        ids=ids
    )
    
    return collection

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(name="akinator_data", embedding_function=embedding_func)
