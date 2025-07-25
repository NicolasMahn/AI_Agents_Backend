from datetime import datetime

import rag
import xml.etree.ElementTree as ET


def execute_long_memory_command(command: ET, agent_system):

    content = command.text

    metadata = {
        "timestamp": datetime.now().timestamp(),
        "agent": agent_system.get_name()
    }

    id_ = str(metadata["timestamp"])

    rag.add_chroma_entry(agent_system.get_long_term_memory_collection(), content, id_, metadata)

    return "Long term memory updated successfully."


