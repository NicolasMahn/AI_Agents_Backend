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
        return "Long term memory is not yet implemented."
        # TODO: add long memory
    elif command.tag == "document":
        return "Document search is not yet implemented."
        # TODO: add document search
    elif command.tag == "query":
        return "Query is not yet implemented."
        # TODO: add query
    elif command.tag == "search":
        return "Search is not yet implemented."
        # TODO: add search
    elif command.tag == "second_opinion":
        return "Second Option is not yet implemented."
        # TODO: add second opinion
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