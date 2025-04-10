


def execute_response_command(command, agent):
    if any(command.tag in ["plan", "code", "query", "document"] for command in agent.commands):
        return "`Plan`, `Code`, `Document` and `Query` can't be used at the same time as `Response`."
    elif agent.extraction_failure:
        return "Extraction of a command failed. Fix it, before replying!"
    response = command.text
    agent.clean_chat.add_message(agent.get_name(), response)
    return "Response added to chat history."