


def execute_response_command(command, agent):
    if agent.extraction_failure:
        return "Extraction of a command failed. Fix it, before replying!"
    response = command.text
    agent.clean_chat.add_message(agent.get_name(), response)
    return "Response added to chat history."