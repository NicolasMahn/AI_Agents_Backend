import base64
import copy
import os
import threading
import time
from lib2to3.fixes.fix_input import context

from win32comext.shell.shell import FOLDERID_NetworkFolder

import util
from agent_objs.plan import Plan
from config import MAX_SHORT_MEMORY_TOKENS, RAG_CHUNK_SIZE, MAX_CONTEXT_TOKENS, MAX_LENGTH_CONTEXT_ITEM, DEBUG

import agent_util
from llm_functions import count_context_length, basic_prompt
from commands import execute_commands
from agent_objs.chat import Chat
from util import delete_directory_with_content


class Agent:
    def __init__(self,
                 name = "Agent",
                 role = "You are a helpful AI Agent, that ensures the IUsers queries are followed."
                 ):
        self.name = name
        self.role = role

        self.relative_agent_dir = f"agent_files/{self.name}"
        self.agent_dir = os.path.abspath(self.relative_agent_dir)

        self.clean_chat = Chat("Clean Chat", self.agent_dir)
        self.chat = Chat(f"Chat with thinking process", self.agent_dir)
        self.complete_chat = Chat(f"Chat with thinking process and with entire prompt", self.agent_dir)
        self.code_list = []
        self.plan = Plan(self)

        self.context_data = [
            {
                "name": "Short Memory",
                "value": self.get_short_memory,
                "description": "Stores temporary information.",
                "last_interaction": 0,
                "importance": 1,
                "always_display": True
            },  # TODO: Add long term memory etc. when implemented
            {
                "name": "Chat with User",
                "value": self.chat,
                "description": "Stores all interactions of the agent (plus thinking process) with the User.",
                "last_interaction": 0,
                "importance": 8,
                "always_display": True,
            }
        ]
        self.command_instructions = self.get_default_command_instructions()

        # -- Changing Variables --
        self.commands = []
        self.replying = False # indicates if the agent is currently replying to a user

        # TODO: REMOVING NOT YET IMPLEMENTED COMMANDS
        self.command_instructions["long_memory"]["active"] = False
        self.command_instructions["query"]["active"] = False
        self.command_instructions["documents"]["active"] = True  # but not implemented true to print available docs
        self.command_instructions["search"]["active"] = False
        pass

    def get_name(self):
        return self.name

    def reset(self):
        self.clean_chat.clear()
        self.chat.clear()
        self.complete_chat.clear()
        self.code_list = []
        delete_directory_with_content(self.agent_dir)


    def add_context_data(self, name, value, description="No description available", importance = 5, always_display = False):
        self.context_data = [context_item for context_item in self.context_data if name != context_item["name"]]

        self.context_data.append({
            "name": name,
            "value": value,
            "description": description,
            "last_interaction": 0,
            "importance": importance,
            "always_display": always_display
        })


    def prompt_agent(self, prompt):
        entire_prompt = \
            f"{prompt}\n---\n{self.get_instruction_str()}\n---\n{prompt}\n---\n{self.generate_context_dump()}"

        self.complete_chat.add_message("Prompt", entire_prompt)

        response = basic_prompt(entire_prompt, self.role)

        self.commands = agent_util.find_commands_in_string(response)
        command_responses = execute_commands(self.commands, self)

        self.chat.add_message(self.name, response)
        self.complete_chat.add_message(self.name, response)
        for command, response in command_responses.items():
            self.chat.add_message(command, response)
            self.complete_chat.add_message(command, response)

        if len(self.plan) > 0:
            step = self.plan[0]
            execution_prompt = (
                f"Please complete the following step in your plan:\n\n"
                f"Step: {step}\n\n"
                f"The original user message was:\n{self.clean_chat.get_last_message_of_sender('User')}\n\n"
                "Once you complete this step, reply with the command `<next_step />` to continue."
            )
            self.prompt_agent(execution_prompt)
        pass

    def handle_message(self, sender):
        if self.replying:
            pass
        else:
            self.replying = True

        if sender != self.name and sender != "System":
            while self.clean_chat.get_last_sender() != self.name:
                self.prompt_agent(f"The User has sent a message: {self.clean_chat.get_last_message_of_sender('User')}\n"
                                  f"Please solve the query."
                                  "You may deliberate before replying to the User.")
        self.replying = False

    def generate_context_dump(self):
        context_dump = f"# **Context Dump**\n\n"

        always_display_count = 0
        for context_item in self.context_data:
            if context_item["always_display"]:
                always_display_count += 1

        self.context_data = sorted(self.context_data,
                                   key=lambda x: x["last_interaction"]/(10 - x["importance"] + x["last_interaction"]))

        for context_item in self.context_data:
            name = context_item["name"]
            value = context_item["value"]
            if callable(value):
                value = value()

            if name == "Short Memory":
                context_item_str = (f"## **{name}**:"
                                 f"<short_memory>"
                                 f" {value}"
                                 f"</short_memory>\n\n")
            elif isinstance(value, Chat):
                context_item_str = f"## **{name}**:\n"
                chat_content = value.get_last_n_tokens_in_xml_str(MAX_LENGTH_CONTEXT_ITEM)
                context_item_str += f"{chat_content}\n\n"
            else:
                context_item_str = f"## **{name}**:\n"
                context_item_str += f"{value}\n\n"
                context_item_str += "\n"


            if context_item["always_display"]:
                context_dump += context_item_str
                always_display_count -= 1
            elif (count_context_length(context_dump) +
                  count_context_length(context_item_str) +
                  (MAX_LENGTH_CONTEXT_ITEM*always_display_count)) < MAX_CONTEXT_TOKENS:
                context_dump += context_item_str

            context_item["last_interaction"] += 1

        return context_dump

    def add_short_memory(self, text: str):
        util.save_text(f"{self.agent_dir}/{self.name}_memory", text)
        pass

    def get_short_memory(self):
        return util.load_text(f"{self.agent_dir}/{self.name}_memory")

    def add_custom_commands(self, name, custom_command_instructions, active = True):
        # Remove the last item and store it
        last_key, last_value = self.command_instructions.popitem()
        self.command_instructions[name] = {"text": custom_command_instructions, "active": active}
        self.command_instructions[last_key] = last_value

    def get_instruction_str(self):
        instructions_str = ""
        for key, value in self.command_instructions.items():
            if "active" in value and value["active"]:
                if "dynamic_data" in value and value["dynamic_data"]:
                    if isinstance(value["dynamic_data"], list):
                        for i in value["dynamic_data"]:
                            instructions_str += value["text"].format(i)
                    else:
                        instructions_str += value["text"].format(dynamic_info=value["dynamic_data"])
                else:
                    instructions_str += value["text"]
        return instructions_str

    def get_readable_document_paths(self):
        return util.get_readable_document_paths(self.agent_dir)

    def get_default_command_instructions(self):
        return {
            "introduction": {
                "text": (
                    "# **Command Instructions**\n"
                    "You can interact with multiple agents in this project using an **XML-based format**. "
                    "Your interactions will be stored, and past responses may be referenced in future prompts.\n\n"
                ),
                "active": True
            },
            "short_memory": {
                "text": (
                    "## **Short-Term Memory**\n"
                    "- Save temporary information:\n"
                    "```xml\n"
                    "<short_memory>Your text here</short_memory>\n"
                    "```\n"
                    "- Resets with each new message.\n"
                    f"- Maximum capacity: **{MAX_SHORT_MEMORY_TOKENS}** tokens.\n\n"
                ),
                "active": True
            },
            "long_memory": {
                "text": (
                    "## **Long-Term Memory (RAG-DB)**\n"
                    "- Save persistent knowledge:\n"
                    "```xml\n"
                    "<long_memory>Your text here</long_memory>\n"
                    "```\n"
                    f"- Stored in chunks of **{RAG_CHUNK_SIZE}** tokens.\n"
                    "- Relevant sections will be retrieved automatically when working on related tasks.\n\n"
                ),
                "active": True
            },
            "query": {
                "text": (
                    "## **Retrieving Information**\n"
                    "\n"
                    "### **Querying Stored Information**\n"
                    "To access relevant information from the **RAG-DB (long-term memory)** or stored **documents**, use the `<query>` tag.\n\n"
                    "#### **General Query (Default)**\n"
                    "A `<query>` searches both long-term memory and relevant documents by default.\n"
                    "Example:\n"
                    "```xml\n"
                    "<query>What were the key product requirements from the last customer meeting?</query>\n"
                    "```\n\n"
                    "#### **Targeted Queries**\n"
                    "You can specify the source:\n"
                    "\n"
                    "- **Long-Term Memory Only:**\n"
                    "```xml\n"
                    "<query type=\"long_term\">Summarize previous discussions about model selection.</query>\n"
                    "```\n"
                    "- **Documents Only:**\n"
                    "```xml\n"
                    "<query type=\"documents\">Find references to data privacy regulations.</query>\n"
                    "```\n\n"
                ),
                "active": True
            },
            "documents": {
                "text": (
                    "## **Project Documents**\n"
                    "Throughout this project, several documents will be created and stored. You can query these documents using the `<document>` tag.\n"
                    "As an attribute, you will need to append the document path. Here is a list of available documents:\n"
                    "{dynamic_info}\n"  # Placeholder for dynamic content
                    "\n"
                    "Here is an example of how to query a document:\n"
                    "```xml\n"
                    "<document filepath=\"success_criteria.txt\" />\n"
                    "```\n\n"
                ),
                "dynamic_data": self.get_readable_document_paths,
                "active": True
            },
            "search": {
                "text": (
                    "## **Web Search**\n"
                    "If the needed information is not available in the RAG-DB, you can search the web:\n"
                    "```xml\n"
                    "<search>Latest trends in data visualization for enterprise dashboards.</search>\n"
                    "```\n"
                    "- **Scientific papers only:**\n"
                    "```xml\n"
                    "<search type=\"scholar\">Recent research on explainable AI in fraud detection.</search>\n"
                    "```\n\n"
                ),
                "active": True
            },
            "executing_code": {
                "text": (
                    "## **Executing Code Securely**\n"
                    "This system allows you to run Python code in a secure, resource-limited environment. "
                    "Use the structured XML-like format below to define execution parameters.\n\n"

                    "### **Basic Execution**\n"
                    "```xml\n"
                    "<code>\n"
                    "# Your Python code here\n"
                    "</code>\n"
                    "```\n\n"

                    "### **Providing Input Data**\n"
                    "```xml\n"
                    "<code input={\"x\": 3, \"y\": 4}>\n"
                    "z = x * y\n"
                    "</code>\n"
                    "```\n\n"

                    "### **Retrieving Results**\n"
                    "```xml\n"
                    "<code input={\"x\": 3, \"y\": 4} output=[\"z\"]>\n"
                    "z = x * y\n"
                    "</code>\n"
                    "```\n\n"

                    "### **Adding Dependencies**\n"
                    "```xml\n"
                    "<code requirements=[\"numpy\"]>\n"
                    "import numpy as np\n"
                    "a = np.array([1,2,3])\n"
                    "</code>\n"
                    "```\n\n"

                    "### **Accessing Files**\n"
                    "**Saving Files**\n"
                    "```xml\n"
                    "<code input={\"filename\": \"output.txt\"}>\n"
                    "filepath = os.path.join(\"/files\", filename)\n"
                    "with open(filepath, \"w\") as f:\n"
                    "    f.write(\"Hello, world!\")\n"
                    "</code>\n"
                    "```\n\n"

                    "**Reading Files**\n"
                    "```xml\n"
                    "<code input={\"filename\": \"data.txt\"}>\n"
                    "filepath = os.path.join(\"/files\", filename)\n"
                    "with open(filepath, \"r\") as f:\n"
                    "    content = f.read()\n"
                    "</code>\n"
                    "```\n\n"                                        
                    "Files can be found under the `files` directory"

                    "### **Versioning and Tagging Code**\n"
                    "```xml\n"
                    "<code version=\"1.0\">\n"
                    "print(\"Versioned Execution\")\n"
                    "</code>\n"
                    "```\n\n"

                    "```xml\n"
                    "<code tag=\"experiment-alpha\" output=[\"x\"]>\n"
                    "x = 42\n"
                    "</code>\n"
                    "```\n\n"
                    
                    "### **Reusing Code or Results**\n"
                    
                    "You can reuse previously written code or outputs by referencing a code `tag` and optionally a `version`. "
                    "If no version is provided, the latest version for that tag is used.\n\n"
                    
                    "**Using Previous Outputs**\n"
                    "```xml\n"
                    "<code previous_output={\"tag\": \"experiment-alpha\"}>\n"
                    "print(x)\n"
                    "</code>\n"
                    "```\n"
                    
                    "Since `x` was saved in `experiment-alpha`, it can be reused here.\n\n"
                    
                    "To include multiple previous outputs:\n"
                    "```xml\n"
                    "<code previous_output=[{\"tag\": \"alpha\"}, {\"tag\": \"beta\"}]>\n"
                    "# Use outputs from multiple tags\n"
                    "</code>\n"
                    "```\n"                    
                    "If a previous output is empty or not found, the latest available version will be used.\n\n"

                    "**Importing Previous Code**\n"
                    "```xml\n"
                    "<code tag=\"add\">\n"
                    "def add(a, b):\n"
                    "    return a + b\n"
                    "</code>\n"
                    "```\n"
                    "```xml\n"
                    "<code import={\"tag\": \"add\"}>\n"
                    "print(add(3, 4))\n"
                    "</code>\n"
                    "```\n\n"
                    "It is also possible to import multiple code snippets by providing a list of tags. "
                    "Keep in mind that the previous outputs will always be loaded first "
                    "(so if the name sof the previous outputs match they may be overwritten).\n\n"
                    
                    "💡 *Tip:* Work in small, testable code chunks to reduce errors when combining logic.\n\n"
                    
                    "### **Frontend**\n"
                    "You can also build a frontend using dash."
                    "Simply add a frontend tag to your code and the frontend will be displayed in the dashboard.\n"
                    "You will need to create a dash layout called `dashboard`.\n"
                    "```xml\n"
                    "<code frontend>\n"
                    "from dash import html\n"
                    "dashboard = html.Div(\"Hello, World!\")\n"
                    "</code>\n"
                    
                    "You may only use the libraries pandas, numpy, matplotlib, seaborn, plotly, dash, scikit-learn, "
                    "and datetime as these are the only libraries available in the frontend environment.\n"
                    
                    "Important: When building a frontend, store your Dash layout in a variable named dashboard. Do not attempt to create a full Dash app instance. The execution environment will automatically display the layout stored in dashboard on the dashboard.\n"
                    
                    "💡 *Tip:* Recently dash changed its configuration now only `dash.run()` is valide `dash.run_server()` is deprecated.\n\n"
                    
                    "### **Execution Environment**\n"
                    "- **Resource-limited** execution.\n"
                    "- **Isolated** environment.\n"
                    "- **Restricted network access** (except for package installations).\n"
                    "This ensures secure and controlled execution of arbitrary Python code.\n\n"
                ),
                "active": True
            },
            "planning": {
                    "text": (
                        "## **Planning**\n"
                        "When faced with a complex task, break it down into a series of logical, manageable steps. This structured approach will help you address the problem thoroughly and systematically.\n\n"
                        "### **Plan Structure**\n"
                        "Generate your plan using the following XML-like format:\n\n"
                        "```xml\n"
                        "<plan>\n"
                        "   <step>Define the problem</step>\n"
                        "   <step>Gather relevant information</step>\n"
                        "   <step>Analyze the information</step>\n"
                        "   <step>Develop a solution</step>\n"
                        "   <step>Review and finalize your answer</step>\n"
                        "</plan>\n"
                        "```\n\n"
                        "### **Execution Process**\n"
                        "After generating your plan, work on each step individually. Focus on one step at a time and when you complete a step, signal your readiness to proceed by issuing the `<next_step />` command.\n\n"
                        "### **Dynamic Adjustments**\n"
                        "If you realize that additional steps are needed or adjustments are required, update your plan accordingly by adding, modifying, or removing steps. Ensure that your plan always reflects your current approach.\n\n"
                        "### **Completion Confirmation**\n"
                        "Once all steps have been executed, provide a final summary that outlines your process and delivers the comprehensive answer to the user's query.\n\n"
                        "### **Handling Uncertainties**\n"
                        "If any step is unclear or you require further clarification, note these uncertainties during execution and adjust your plan as needed before proceeding."
                    ),
                    "active": True
            },
            "response_to_user": {
                "text": (
                    "## **Responding to the User**\n"
                    "When responding to the User, you can use the `<response>` tag to structure your answers.\n"
                    "Here is an example:\n"
                    "```xml\n"
                    "<response>\n"
                    "The answer to the User's query goes here.\n"
                    "</response>\n"
                    "```\n"
                    "Your answer to the User should be concise and informative.\n\n"
                ),
                "active": True
            },
            "response_recommendations": {
                "text": (
                    "## **Response Recommendations**\n"
                    "- **Use structured queries for better results.**\n"
                    "- **Remember to work iteratively and refine your queries, before responding to the User**\n"
                    "- **Prioritize querying the RAG-DB before using web searches.**\n"
                ),
                "active": True
            }
        }

    def does_agent_code(self):
        if self.command_instructions["executing_code"]["active"]:
            return True
        return False

    def upload_file(self, upload_contents, filename):
        if upload_contents is not None:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                os.mkdir(f"{self.agent_dir}/uploads")
                file_path = f"uploads/{filename}"
                with open(f"{self.agent_dir}/{file_path}", "wb") as f:
                    f.write(decoded)
                self.add_message("System", "Upload succeeded")
            except Exception as e:
                self.add_message("System", f"Error uploading file: {str(e)}")
        else:
            self.add_message("System", "No file uploaded")
        pass

    def get_chats(self):
        return [str(self.clean_chat), str(self.chat), str(self.complete_chat)]

    def get_chat(self, chat_name: str):
        if chat_name == "clean_chat" or chat_name == self.clean_chat.chat_name:
            return self.clean_chat
        elif chat_name == "chat" or chat_name == self.chat.chat_name:
            return self.chat
        elif chat_name == "complete_chat" or chat_name == self.complete_chat.chat_name:
            return self.complete_chat
        else:
            return None

    def add_message(self, sender: str, text: str,
                    add_to_clean_chat = True,
                    add_to_chat = True,
                    add_to_complete_chat = False):
        if add_to_clean_chat:
            self.clean_chat.add_message(sender, text)
        if add_to_chat:
            self.chat.add_message(sender, text)
        if add_to_complete_chat:
            self.complete_chat.add_message(sender, text)
        self.handle_message(sender)
        pass

    def add_code(self, code):
        self.code_list.append(code)
        pass

    def get_code_names(self):
        if len(self.code_list) == 0:
            return []
        return [code.get_name() for code in self.code_list]

    def get_code_obj(self, name: str):
        for code in self.code_list:
            if code.get_name() == name:
                return code
        return None

    def get_code_api(self, name: str):
        for code in self.code_list:
            if code.get_name() == name:
                return code.get_code_for_api()
        return None

    def get_frontend_code(self):
        for code in self.code_list:
            if code.frontend:
                return code
        return None

    def __del__(self):
        self.reset()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name