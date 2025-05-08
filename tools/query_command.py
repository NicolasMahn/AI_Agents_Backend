import rag
import xml.etree.ElementTree as ET


def execute_query_command(command: ET, agent_system) -> str:
    query = command.text

    if "type" in command.attrib and command.attrib["type"] in ["documents", "memory"]:
        query_type = command.attrib["type"]
    else :
        query_type = "documents"

    if query_type == "documents":
        chroma_collection = agent_system.get_chroma_collection_of_acting_agent()
    else:
        chroma_collection = agent_system.get_long_term_memory_collection()

    results = rag.query_rag(query, chroma_collection, n_results=5)

    if isinstance(results, str):
        return results

    xml_str = agent_system.convert_query_results_to_xml_schema(results, root_name=query_type)

    response_text = f"Query results for `{query}`:\n"
    response_text += f"{xml_str}\n"
    if query_type == "documents":
        response_text += f"Please reference the source in your answer.\n"


    agent_system.add_context_data(f"{query_type} Query Results", response_text, "Query results", importance=3)

    return "Query executed successfully."