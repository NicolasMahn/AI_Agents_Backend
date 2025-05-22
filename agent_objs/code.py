import ast
import socket
from datetime import datetime
import docker, tempfile, os


from agent_objs.dash_app_evaluation import evaluate_dash_app
from config import DEBUG
from util import save_file
from util.colors import WHITE, RESET, LIGHT_GREEN, PINK, RED

DEFAULT_REQUIREMENTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "plotly",
    "dash",
    "scikit-learn",
    "datetime",
    "dash-bootstrap-components",
    "dash-extensions"
}
MEM_LIMIT = "1025m"
TIMEOUT = 50
CPU_QUOTA = 100000

CUSTOM_PYTHON_DOCKERFILE = os.getenv("CUSTOM_PYTHON_DOCKERFILE", "custom-python")
D_IN_D = os.getenv("D_IN_D", False)

def find_available_port(host='localhost'):
    """
    Finds and reserves an available port by binding to port 0.
    Returns the port number assigned by the OS.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Binding to port 0 tells the OS to pick an available ephemeral port.
        # Binding to host '' or '0.0.0.0' checks availability on all interfaces,
        # while 'localhost' checks only for loopback. Choose based on need.
        s.bind((host, 0))
        s.listen(1) # Optional: Put socket into listening state
        # getsockname() returns the (host, port) tuple the socket is bound to.
        port = s.getsockname()[1]
        # The 'with' statement ensures the socket is closed, releasing the port
        # *unless* you plan to use this exact socket object.
        # If you need the port number for a *different* process/socket,
        # this still has a small race window, but it's much smaller and often
        # acceptable compared to the check-then-bind approach.
        # The *best* approach is to use the *same socket* that bound to port 0.
    return port


class Code:
    def __init__(self, code: str, requirements, code_imports: list, agent_system,
                 version: str = "-", tag: str = "", frontend=False):

        self.code = code
        self.requirements :list = []
        if isinstance(requirements, str):
            try:
                requirements = ast.literal_eval(requirements)
            except Exception:
                requirements = [requirements]
        if isinstance(requirements, list):
            for requirement in requirements:
                if requirement not in DEFAULT_REQUIREMENTS:
                    self.requirements.append(requirement)
        self.version = version
        self.tag = tag
        self.dt = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        self.agent_system = agent_system
        self.logs = None
        self.frontend_html = None

        if isinstance(code_imports, str):
            try:
                code_imports = ast.literal_eval(code_imports)
            except Exception:
                code_imports = [code_imports]
        self.code_imports = code_imports

        self.frontend = frontend

        self.name = (f"by_agent_{agent_system.get_name()}_"
                     f"version_{version}_datetime_{self.dt}")
        if self.tag:
            self.name += f"_tag_{tag}"

        self.code_dir = f"{self.agent_system.agent_system_dir}/code"
        self.code_file_path = f"{self.code_dir}/{self.name}.py"

        self.input_dir = os.path.join(self.agent_system.agent_system_dir, "uploads")
        os.makedirs(self.input_dir, exist_ok=True)

        self.output_dir = os.path.join(self.agent_system.agent_system_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        self.dash_evaluation = None
        self.relative_code_file_path = f"code/{self.name}.py"

    def get_display_code(self):
        display_code = ""

        if self.requirements:
            display_code += f"# Needs these requirements: {self.requirements}\n"

        if self.code_imports:
            display_code += f"# Code to be run previously: {self.code_imports}\n"

        display_code += "\n\n"
        display_code += self.code
        return display_code

    def save_code(self):
        save_file(self.code_file_path, self.get_display_code())
        pass

    def get_execution_code(self, injection_code_front=""):
        if self.code_imports:
            for code_obj in self.code_imports:
                execution_code = code_obj.get_execution_code()
                injection_code_front += execution_code

        # Prepend the injection code to the user-provided code.
        return injection_code_front + "\n" + self.code + "\n"

    def get_main_code(self, port):
        return f"""
from agent_code import app
import os

if __name__ == '__main__':
    print("Files available for use: ", os.listdir('uploads/'))
    app.run(debug=True, host='0.0.0.0', port={port})                       
        """

    def execute(self):
        self.save_code()

        try:
            execution_code = self.get_execution_code("import pickle \n"
                                                     "import os\n"
                                                     "os.makedirs('output', exist_ok=True)\n")

            # Create a temporary directory for the wrapped code file.
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the combined code into the temporary directory.
                code_path = os.path.join(temp_dir, "agent_code.py")
                with open(code_path, "w") as f:
                    f.write(execution_code)
                start_command = "python /code/agent_code.py"

                if D_IN_D:
                    # Use Docker-in-Docker (DinD) for the container.
                    input_dir_index = self.input_dir.index("agent_files")
                    input_dir = self.input_dir[input_dir_index-1:]
                    output_dir_index = self.output_dir.index("agent_files")
                    output_dir = self.output_dir[output_dir_index-1:]

                    volumes = {code_path: {"bind": "/code/agent_code.py", "mode": "rw"},
                               input_dir: {"bind": "/code/uploads/", "mode": "rw"},
                               output_dir: {"bind": "/code/output/", "mode": "rw"}}
                else:
                    volumes = {code_path: {"bind": "/code/agent_code.py", "mode": "rw"},
                               self.input_dir: {"bind": "/code/uploads/", "mode": "rw"},
                               self.output_dir: {"bind": "/code/output/", "mode": "rw"}}

                if DEBUG:
                    for file in os.listdir(self.input_dir):
                        print(f"{PINK}File in input dir: {file}{RESET}")

                if self.frontend:
                    start_command = f"python /code/main.py"

                # Process any extra requirements.
                if self.requirements:
                    req_str = " ".join(self.requirements)
                    # Enable network access to allow pip to install missing packages.
                    command = f"sh -c 'pip install {req_str} && {start_command}'"
                else:
                    # Nothing extra to install.
                    command = start_command

                # Set up and run the Docker container with security restrictions.
                client = docker.from_env()

                if self.frontend:
                    port = find_available_port()
                    main_path = os.path.join(temp_dir, "main.py")
                    with open(main_path, "w") as f:
                        f.write(self.get_main_code(port))
                    volumes[main_path] = {"bind": "/code/main.py", "mode": "rw"}

                    container = client.containers.run(
                        CUSTOM_PYTHON_DOCKERFILE,  # Ensure this image is built from your CustomPythonDockerfile.
                        command=command,
                        volumes=volumes,
                        network_disabled=False,
                        mem_limit=MEM_LIMIT,  # Limit memory usage.
                        cpu_quota=CPU_QUOTA,  # Limit CPU time.
                        detach=True,
                        remove=False,
                        ports={port: port}
                    )
                    self.dash_evaluation = evaluate_dash_app(port, self.code_dir)
                    print("container ID: ", container.id)
                    # container.wait(timeout=TIMEOUT*100)
                else:
                    container = client.containers.run(
                        CUSTOM_PYTHON_DOCKERFILE,  # Ensure this image is built from your CustomPythonDockerfile.
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
                print(logs)

                self.logs = logs

        except Exception as e:
            print(f"Error executing code: {e}")
            self.logs = str(e)
        finally:
            # Ensure the container is stopped and removed.
            try:
                if container:
                    try:
                        container.stop()
                    except Exception as stop_error:
                        print(f"Error stopping container: {stop_error}")
                    try:
                        container.remove()
                    except Exception as remove_error:
                        print(f"Error removing container: {remove_error}")
            except UnboundLocalError:
                print("Container was never created.")
            except Exception as e:
                print(f"Error cleaning up container: {e}")

    def get_results_xml(self):
        results = (
            f"Here are the results from the code execution:\n"
            f"Logs:\n"
            f"{self.logs}\n\n")
        if self.frontend:
            results += (
                f"The Frontend was evaluated with these results:\n"
                f"{self.dash_evaluation}\n")
        results += (
            f"Executed Code:"
            f"```python\n"
            f"{self.get_display_code()}\n"
            f"```\n")
        print(results)
        return results

    def get_code_for_api(self):
        input_files = []
        for file in os.listdir(self.input_dir):
            input_files.append(os.path.join(self.input_dir, file))

        jsonable_class = [self.code, list(self.requirements),
                          [code_obj.get_name() for code_obj in self.code_imports],
                          input_files, self.frontend]
        return jsonable_class


    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __lt__(self, other):
        return self.dt < other.dt

    def get_name(self):
        return self.name

