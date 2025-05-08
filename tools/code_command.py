import xml.etree.ElementTree as ET

import api
from agent_objs.code import Code
from config import DEBUG
from util.colors import WHITE, GREEN, RESET


def execute_code_command(command: ET, agent_system):
    attr = command.attrib

    if "requirements" in attr:
        requirements = attr["requirements"]
    else:
        requirements = None

    if "version" in attr:
        version = attr["version"]
    else:
        version = None

    if "tag" in attr:
        tag = attr["tag"]
    else:
        tag = None

    if "frontend" in attr:
        frontend = True
    else:
        frontend = False

    code_imports = []
    if "import" in attr:
        to_import = attr["import"]
        if DEBUG:
            print(f"{WHITE}Importing code from {GREEN}{to_import}{RESET}")
        codes = agent_system.get_codes().copy().sort()
        if not isinstance(to_import, list):
            to_import = [to_import]
        for imp in to_import:
            if isinstance(imp, dict):
                if "tag" in imp.keys():
                    codes = [code for code in codes if code.tag == imp["tag"]]
                if "version" in imp.keys():
                    codes = [code for code in codes if code.version == imp["version"]]
            if codes:
                code_imports.append(max(codes)) # gets latest code

    code = command.text

    code_obj = Code(code, requirements, code_imports, agent_system, version, tag, frontend)
    code_obj.execute()
    agent_system.add_code(code_obj)

    agent_system.add_context_data("Code Results", code_obj.get_results_xml(), "Results from Code Execution",
                                  importance = 1)

    api.send_message(f"Agent {agent_system.name} just executed code")
    return "Code execution completed"