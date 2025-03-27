


def execute_response_command(command, agent):
    response = command.text
    agent.clean_chat.add_message(agent.get_name(), response)
    return "Response added to chat history."