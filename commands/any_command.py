from typing import Tuple, Any
import xml.etree.ElementTree as ET



def execute_commands(commands: list[ET], agent) -> dict[str: str]:
    responses = {}
    for command in commands:
        response = execute_command(command, agent)
        responses[command.tag] =  response

    return responses

def execute_command(command: ET, agent) -> str:
    if command.tag == "short_memory":
        from commands import execute_short_memory_command
        return execute_short_memory_command(command, agent)
    elif command.tag == "long_memory":
        from commands import execute_long_memory_command
        return execute_long_memory_command(command, agent)
    elif command.tag == "document":
        from commands import execute_document_command
        return execute_document_command(command, agent)
    elif command.tag == "query":
        from commands import execute_query_command
        return execute_query_command(command, agent)
    elif command.tag == "search":
        return "Search is not yet implemented."
        # TODO: add search
    elif command.tag == "code":
        from commands import execute_code_command
        return execute_code_command(command, agent)
    elif command.tag == "response":
        from commands import execute_response_command
        return execute_response_command(command, agent)
    elif command.tag == "plan":
        from commands import execute_plan_command
        return execute_plan_command(command, agent)
    elif command.tag == "next_step":
        from commands import execute_next_step_command
        return execute_next_step_command(command, agent)
    else:
        return "Command not recognized."