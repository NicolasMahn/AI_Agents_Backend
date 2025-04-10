import ast, re
import shutil
from datetime import datetime
import docker, tempfile, os

from config import DEBUG
from util import save_pickle, save_file, load_pickle
from util.colors import WHITE, RESET, LIGHT_GREEN

DEFAULT_REQUIREMENTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "plotly",
    "dash",
    "scikit-learn",
    "datetime"
}
MEM_LIMIT = "1025m"
TIMEOUT = 100
CPU_QUOTA = 100000



class Code:
    def __init__(self, code: str, output_vars: list, requirements,
                 code_imports: list, previous_outputs: list, input_files, output_files, agent,
                 version: str = "-", tag: str = "", frontend=False):

        self.code = code
        if isinstance(output_vars, str):
            output_vars = ast.literal_eval(output_vars)
        self.output_vars = {var: None for var in output_vars} if output_vars else {}
        self.get_last_line_outputs()
        self.requirements :list = []
        if isinstance(requirements, str):
            requirements = ast.literal_eval(requirements)
        if isinstance(requirements, list):
            for requirement in requirements:
                if requirement not in DEFAULT_REQUIREMENTS:
                    self.requirements.append(requirement)
        self.version = version
        self.tag = tag
        self.dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        self.agent = agent
        self.logs = None

        if isinstance(code_imports, str):
            code_imports = ast.literal_eval(code_imports)
        self.code_imports = code_imports
        if isinstance(previous_outputs, str):
            previous_outputs = ast.literal_eval(previous_outputs)
        self.previous_outputs = previous_outputs

        self.frontend = frontend

        self.name = (f"by_agent_{agent.get_name()}_"
                     f"version_{version}_datetime_{self.dt}")
        if self.tag:
            self.name += f"_tag_{tag}"

        self.code_dir = f"{self.agent.agent_dir}/code"
        self.code_file_path = f"{self.code_dir}/{self.name}.py"
        self.output_file_path = f"{self.code_dir}/{self.name}.pkl"

        self.input_files :list = []
        self.relative_input_files :list = []
        self.container_input_files :list = []
        self.output_files :list = []
        if isinstance(input_files, str):
            input_files = ast.literal_eval(input_files)
        if input_files:
            for file in input_files:
                self.input_files.append(os.path.join(self.agent.agent_dir, file))
                self.relative_input_files.append(file)
                self.container_input_files.append(f"/files/{file}")
        if isinstance(output_files, str):
            output_files = ast.literal_eval(output_files)
        if output_files:
            for file in output_files:
                self.output_files.append(f"/files/{file}")
        self.output_dir = f"{self.code_dir}/{self.name}_output_files"

        os.makedirs(self.output_dir, exist_ok=True)

        self.relative_code_file_path = f"code/{self.name}.py"
        self.relative_output_file_path = f"code/{self.name}.pkl"

    def get_last_line_outputs(self):
        lines = [line for line in self.code.split("\n") if line.strip()]
        try:
            last_line = lines[-1].strip()
            if last_line and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(,\s*[a-zA-Z_][a-zA-Z0-9_]*)*$', last_line):
                vars_ = last_line.split(",")
                self.output_vars = {var: None for var in vars_}
        except IndexError:
            pass

    def get_display_code(self):
        display_code = ""

        if self.requirements:
            display_code += f"# Needs these requirements: {self.requirements}\n"

        if self.code_imports:
            display_code += f"# Code to be run previously: {self.code_imports}\n"

        if self.previous_outputs:
            display_code += f"# Previous Outputs: {self.previous_outputs}\n"

        if self.input_files:
            display_code += f"# Input files: {self.input_files}\n"

        if self.output_files:
            display_code += f"# Output files: {self.output_files}\n"

        display_code += "\n\n"
        display_code += self.code
        return display_code

    def save_code(self):
        save_file(self.code_file_path, self.get_display_code())
        pass

    def get_execution_code(self):
        code_and_front_injection = self.get_minimal_execution_code("import pickle \n"
                                                                   "import os\n"
                                                                   "os.makedirs('/files', exist_ok=True)\n")

        if self.output_vars.keys():
            injection_code_end = """\n\n
def save_output(data, filename="/code/output.pkl"):
    with open(filename, "wb") as f:
        pickle.dump(data, f)
"""
            injection_code_end += """
output = {"""
            for var in self.output_vars.keys():
                injection_code_end += f"""
    "{var}": {var},"""
            injection_code_end += """
}
save_output(output)"""
        else:
            injection_code_end = ""

        return code_and_front_injection + injection_code_end

    def get_minimal_execution_code(self, injection_code_front=""):

        if self.previous_outputs:
            for code_obj in self.previous_outputs:
                output_dir = code_obj.relative_output_file_path
                if os.path.exists(output_dir):
                    injection_code_front += f"""
try:
    _output_vars = pickle.load(open("{output_dir}", "rb"))
    for key, value in _output_vars.items():
        globals()[key] = value
except Exception as e:
    print("Error loading previous output_vars:", e)
"""

        if self.code_imports:
            for code_obj in self.code_imports:
                execution_code = code_obj.get_minimal_execution_code()
                injection_code_front += execution_code

        # Prepend the injection code to the user-provided code.
        return injection_code_front + "\n" + self.code + "\n"

    def execute_code(self):
        self.save_code()

        try:

            execution_code = self.get_execution_code()

            if DEBUG:
                if self.frontend:
                    print(f"{WHITE}Running Frontend Code: \n{LIGHT_GREEN}{execution_code}{RESET}")
                else:
                    print(f"{WHITE}Running Code: \n{LIGHT_GREEN}{execution_code}{RESET}")

            # Create a temporary directory for the wrapped code file.
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the combined code into the temporary directory.
                code_path = os.path.join(temp_dir, "user_code.py")
                with open(code_path, "w") as f:
                    f.write(execution_code)

                # Process any extra requirements.
                if self.requirements:
                    req_str = " ".join(self.requirements)
                    # Enable network access to allow pip to install missing packages.
                    command = f"sh -c 'pip install {req_str} && python /code/user_code.py'"
                else:
                    # Nothing extra to install.
                    command = "python /code/user_code.py"

                volumes = {
                    code_path: {"bind": "/code/user_code.py", "mode": "rw"},
                    **{os.path.abspath(self.input_files[i]): {"bind": f"{self.container_input_files[i]}", "mode": "rw"}
                       for i in range(len(self.input_files))},
                    **{code_obj.output_file_path: {"bind": f"{code_obj.output_file_path}", "mode": "rw"}
                       for code_obj in self.previous_outputs},
                }
                print(self.input_files)
                print(f"{WHITE}Volumes: {LIGHT_GREEN}{volumes}{RESET}")

                # Set up and run the Docker container with security restrictions.
                client = docker.from_env()
                container = client.containers.run(
                    "custom-python",  # Ensure this image is built from your CustomPythonDockerfile.
                    command=command,
                    volumes=volumes,
                    network_disabled=False,
                    mem_limit=MEM_LIMIT,  # Limit memory usage.
                    cpu_quota=CPU_QUOTA,  # Limit CPU time.
                    detach=True,
                    remove=False  # Auto-remove the container after execution.
                )
                container.wait(timeout=TIMEOUT)
                logs = container.logs().decode()
                output_path = os.path.join(temp_dir, "output.pkl")
                if os.path.exists(output_path):
                    output_data = load_pickle(output_path)
                else:
                    output_data = dict()

                for output_file in self.output_files:
                    output_path = os.path.join(temp_dir, output_file)
                    if os.path.exists(output_path):
                        shutil.move(output_path, self.output_dir)

                container.remove()

                if DEBUG:
                    print(f"{WHITE}Logs: {LIGHT_GREEN}{logs}{RESET}")
                    print(f"{WHITE}Output: {LIGHT_GREEN}{output_data}{RESET}")

                save_pickle(self.output_file_path, output_data)

                self.logs = logs
                self.output_vars = output_data
        except Exception as e:
            print(f"Error executing code: {e}")
            self.logs = str(e)
            self.output_vars = {}

    def get_results_xml(self):
        return (f"<logs>\n"
            f"  {self.logs}"
            f"</logs>\n\n  "
            f'<output saved="{self.relative_output_file_path}" >\n'
            f"  {self.output_vars}"
            f"</output>\n\n  "
            f'<code saved="{self.relative_code_file_path}" />\n')

    def get_code_for_api(self):
        jsonable_class = [self.code, self.output_vars, list(self.requirements),
                [code_obj.get_name() for code_obj in self.code_imports],
                [code_obj.relative_output_file_path for code_obj in self.previous_outputs],
                self.relative_input_files, self.output_files, self.frontend]
        return jsonable_class


    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __lt__(self, other):
        return self.dt < other.dt

    def get_name(self):
        return self.name

