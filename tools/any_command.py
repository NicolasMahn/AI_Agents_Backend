from typing import Tuple, Any
import xml.etree.ElementTree as ET



def execute_commands(commands: list[ET], agent, agent_system) -> dict[str: str]:
    responses = {}
    for command in commands:
        if agent.no_consecutive_messages and command.tag in ["document", "query", "search", "code"]:
            responses[command.tag] = "Commands that take execution time are not allowed. reply to the User!"
            continue
        response = execute_command(command, agent, agent_system)
        responses[command.tag] =  response

    return responses

def execute_command(command: ET, agent, agent_system) -> str:
    command_instructions = agent.command_instructions

    try:
        if command.tag == "short_memory" and command_instructions["short_memory"]["active"]:
            from tools import execute_short_memory_command
            return execute_short_memory_command(command, agent_system)
        elif command.tag == "long_memory" and command_instructions["long_memory"]["active"]:
            from tools import execute_long_memory_command
            return execute_long_memory_command(command, agent_system)
        elif command.tag == "document" and command_instructions["document"]["active"]:
            from tools import execute_document_command
            return execute_document_command(command, agent_system)
        elif command.tag == "query" and command_instructions["query"]["active"]:
            from tools import execute_query_command
            return execute_query_command(command, agent_system)
        elif command.tag == "search" and command_instructions["search"]["active"]:
            return "Search is not yet implemented."
            # TODO: add search
        elif command.tag == "code" and command_instructions["code"]["active"]:
            from tools import execute_code_command
            return execute_code_command(command, agent_system)
        elif command.tag == "response" and command_instructions["response"]["active"]:
            from tools import execute_response_command
            return execute_response_command(command, agent_system)
        elif command.tag == "plan" and command_instructions.get("plan").get("active"):
            from tools import execute_plan_command
            return execute_plan_command(command, agent_system)
        elif command.tag == "next_step" and not agent_system.name == "Reviewing Planning Agent": # This might need to be improved
            from tools import execute_next_step_command
            return execute_next_step_command(command, agent_system)
        else:
            return "Command not recognized."
    except Exception as e:
        print(f"Error executing command {command.tag}: {e}")
        return f"Error executing command {command.tag}: {e}"