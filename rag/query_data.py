import argparse
import os

import httpx

from config import DEBUG, max_tokens
from scrt import CHROMADB_HOST, CHROMADB_PORT
import chromadb

from util.colors import ORANGE, RESET, WHITE, PINK
from .embedding_function import openai_ef

from llm_functions import llm_api_wrapper, count_context_length

PROMPT_TEMPLATE = """
Answer the question based only on the following context:
{context}

---

Answer the question based on the above context: {question}

Reference the source in your answer.
"""

def main():
    # Create CLI.
    parser = argparse.ArgumentParser()

    parser.add_argument("--query_text", type=str, help="The query text.")
    parser.add_argument("--debug", action="store_true", help="Additional print statements")
    parser.add_argument("--collection", default="python", help="Select the chroma collection.")
    parser.add_argument("--n_results", type=int, default=20, help="Number of results to retrieve initially.")
    args = parser.parse_args()
    if args.debug:
        print(f"{ORANGE}⭕  DEBUG Mode Active{RESET}")

    if not args.query_text:
        query_text = "How can i get python to print a pyramid of ducks (🦆) in the console?"
        print(f"{WHITE}🔍  Using default Test query: {query_text}{RESET}")
    else:
        query_text = args.query_text

    if not args.collection:
        collection = "python"
        print(f"{WHITE}🔍  Using default collection: {collection}{RESET}")
    else:
        collection = args.collection

    n_results = args.n_results

    response_text, _, _ = query_rag_with_llm_response(query_text, collection,
                                                      n_results=n_results)

    print(f"{WHITE}{response_text}{RESET}")
    print()


def query_rag_with_llm_response(query_text: str, chroma_collection: str, unique_role: str=None,
                                unique_prompt_template: str=None,
                                n_results: int = 20):

    results = query_rag(query_text, chroma_collection, n_results=n_results)
    if isinstance(results, str):
        return results, None, None

    ids = results['ids'][0]
    page_contents = results['documents'][0]
    metadatas = results['metadatas'][0]
    context_texts = []
    for i in range(len(ids)):
        source = metadatas[i].get("url", metadatas[i].get("pdf_name", None))
        chunk_number = metadatas[i].get("chunk_number", None)
        page_content = page_contents[i]
        # if type == "image":
        context_texts.append(f"{page_content}\n[source: {source}; chunk number: {chunk_number}]")

    context_text = "\n\n---\n\n".join(context_texts)
    # sources = [doc.metadata.get("id", None) for doc, _score in results]
    if DEBUG:
        print("Prompt:\n", query_text)
        # print("Retrieved Summarize:\n", results)
        print("Context:\n", context_text)
        print("Metadata:\n", metadatas)
        print("\n")

    prompt_template = PROMPT_TEMPLATE if not unique_prompt_template else unique_prompt_template

    prompt = prompt_template.format(context=context_text, question=query_text)

    role = "Provide accurate and concise answers based solely on the given context." if not unique_role else unique_role
    response_text = llm_api_wrapper.basic_prompt(prompt, role=role, model="default")

    return response_text, context_text, metadatas

def query_rag(query_text: str, chroma_collection: str, n_results: int = 3, _retry=0):
    print("@ query_rag() - immediately")
    try:
        print("@at query_rag() -while defining chroma_client")
        # Prepare the DB.
        chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

        print("@at query_rag() - while creating or getting the collection")
        # Create or get the test collection
        collection = chroma_client.get_or_create_collection(name=chroma_collection, embedding_function=openai_ef)

        print("@at query_rag() - in remove_excess_query_length()")
        query_text = remove_excess_query_length(query_text)

        print("@at query_rag() - while counting the collection size")
        collection_size = collection.count()
        print("@at query_rag() - after checking the collection size")
        if collection_size == 0:

            print(f"{WHITE}🔍  WARNING: The collection is empty. Please add documents before querying.{RESET}")
            return []

        elif n_results > collection_size:
            print("@at query_rag() - while getting the results")
            results = collection.get(limit=n_results)
            return results
        else:
            print("@at query_rag() - while querying the results")
            # Search the DB.
            results = collection.query(
                query_texts=[query_text],  # Chroma will embed this for you
                n_results=n_results  # how many results to return
            )
            return results
    except httpx.ReadError as e:
        if _retry < 3:
            print(f"{PINK}🔍  Retrying query due to ReadError: {e}{RESET}")
            return query_rag(query_text, chroma_collection, n_results, _retry + 1)
        else:
            print(f"{PINK}🔍  Failed to query after 3 retries: {e}{RESET}")
            return f"Failed to query after 3 retries: {e}"
    except Exception as e:
        print(f"{PINK}🔍  An error occurred: {e} TEST \n{RESET}")
        return "Error: " + str(e)

def remove_excess_query_length(query_text):
    embedding_model = "text-embedding-ada-002"
    token_length = count_context_length(query_text, model=embedding_model)
    max_token_length = max_tokens[embedding_model]

    if token_length > max_token_length:
        if DEBUG:
            print(f"{WHITE}🔍  Query length exceeds maximum token limit. Trimming the query...{RESET}")
        query_text = query_text[:max_token_length]

    return query_text


def load_raw_document_content(doc_name: str, data_dir: str):
    file_path = os.path.join(data_dir, doc_name)
    if file_path.endswith('.txt') or file_path.endswith('.csv'):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    return "Content not available"




if __name__ == "__main__":
    main()
