


def execute_response_command(command, agent_system):
    if agent_system.extraction_failure:
        return "Extraction of a command failed. Fix it, before replying!"
    response = command.text
    agent_system.clean_chat.add_message(agent_system.acting_agent.get_name(), response)

    if agent_system.get_name() == "Planning Agent System":
        plan = agent_system.get_plan()
        if plan.on_last_step():
            from tools import execute_next_step_command
            execute_next_step_command(command, agent_system)

    return "Response added to chat history."