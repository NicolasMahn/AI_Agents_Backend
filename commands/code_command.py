import xml.etree.ElementTree as ET

from agent_objs.code import Code
from config import DEBUG

WHITE = "\033[97m"
BLUE = "\033[34m"
GREEN = "\033[32m"
ORANGE = "\033[38;5;208m"
PINK = "\033[38;5;205m"
RED = "\033[31m"
RESET = "\033[0m"


def execute_code_command(command: ET, agent):
    attr = command.attrib
    if "input" in attr:
        input_vars = attr["input"]
    else:
        input_vars = None

    if "output" in attr:
        output_vars = attr["output"]
    else:
        output_vars = None

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
        codes = agent.get_codes().copy().sort()
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

    previous_outputs = []
    if "previous_outputs" in attr:
        get_output = attr["previous_outputs"]
        if DEBUG:
            print(f"{WHITE}Importing code from {GREEN}{get_output}{RESET}")
        codes = agent.get_codes().copy().sort()
        if not isinstance(get_output, list):
            get_output = [get_output]
        for outp in get_output:
            if isinstance(outp, dict):
                if "tag" in outp.keys():
                    codes = [code for code in codes if code.tag == outp["tag"]]
                if "version" in outp.keys():
                    codes = [code for code in codes if code.version == outp["version"]]
            if codes:
                previous_outputs.append(max(codes)) # gets latest code (from which the output can be retrieved)

    code = command.text

    code_obj = Code(code, input_vars, output_vars, requirements, code_imports, previous_outputs, agent, version, tag,
                    frontend=frontend)
    code_obj.execute_code()
    agent.add_code(code_obj)

    agent.add_context_data("Code Results", code_obj.get_results_xml(), "Results from Code Execution",
                           importance = 1)

    return "Code execution completed"