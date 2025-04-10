import xml.etree.ElementTree as ET

from agent_objs.code import Code
from config import DEBUG
from util.colors import WHITE, GREEN, RESET


def execute_code_command(command: ET, agent):
    attr = command.attrib

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

    if "input_files" in attr:
        input_files = attr["input_files"]
        print()
    else:
        input_files = None

    if "output_files" in attr:
        output_files = attr["output_files"]
    else:
        output_files = None

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

    code_obj = Code(code, output_vars, requirements, code_imports, previous_outputs, input_files,
                    output_files, agent, version, tag, frontend)
    code_obj.execute_code()
    agent.add_code(code_obj)

    agent.add_context_data("Code Results", code_obj.get_results_xml(), "Results from Code Execution",
                           importance = 1)

    return "Code execution completed"