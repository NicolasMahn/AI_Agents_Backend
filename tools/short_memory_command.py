

def execute_short_memory_command(command, agent_system):
    agent_system.add_short_memory(command.text)
    return "Short memory updated."