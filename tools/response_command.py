


def execute_response_command(command, agent_system):
    if agent_system.extraction_failure:
        return "Extraction of a command failed. Fix it, before replying!"
    response = command.text
    agent_system.clean_chat.add_message(agent_system.acting_agent.get_name(), response)
    return "Response added to chat history."