import chromadb

from rag.embedding_function import openai_ef
from scrt import CHROMADB_HOST, CHROMADB_PORT


def add_chroma_entry(chroma_collection_name: str, content: str, id_: str, metadata: dict):
    chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    collection = chroma_client.get_or_create_collection(name=chroma_collection_name,
                                                        embedding_function=openai_ef)
    collection.upsert(
        documents=[content],
        metadatas=[metadata],
        ids=[id_]
    )