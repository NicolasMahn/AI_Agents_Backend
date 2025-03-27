

def execute_short_memory_command(command, agent):
    agent.add_short_memory(command.text)
    return "Short memory updated."