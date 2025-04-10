import base64
import os

import numpy as np

import rag
import util
import config

from commands import command_util
from llm_functions import count_context_length, basic_prompt
from commands import execute_commands, execute_document_command
from agent_objs.chat import Chat
from rag import query_rag
from util import delete_directory_with_content


class Agent:
    def __init__(self,
                 name = "Agent",
                 role = "You are an AI Agent. You are given tasks by the User and converse with him in a chat.",
                 chroma_collection = "python"
                 ):
        self.name = name
        self.technical_name = name.lower().replace(" ", "_")
        self.role = role
        self.chroma_collection = chroma_collection
        self.long_term_memory_collection = f"long_term_memory_{self.technical_name}"

        self.relative_agent_dir = f"agent_files/{self.technical_name}"
        self.agent_dir = os.path.abspath(self.relative_agent_dir)

        self.clean_chat = Chat("Clean Chat", self.agent_dir)
        self.chat = Chat(f"Chat with thinking process", self.agent_dir)
        self.complete_chat = Chat(f"Chat with thinking process and with entire prompt", self.agent_dir)
        self.code_list = []

        self.context_data = [
            {
                "name": "Chat with User",
                "value": self.chat,
                "description": "Stores all interactions of the agent (plus thinking process) with the User.",
                "last_interaction": 0,
                "importance": 1,
                "always_display": True,
            },
            {
                "name": "Short Memory",
                "value": self.get_xml_short_memory,
                "description": "Stores temporary information.",
                "last_interaction": 0,
                "importance": 3,
                "always_display": True
            },
            {
                "name": "Long-Term Memory",
                "value": self.get_xml_long_memory,
                "description": "Stores persistent knowledge.",
                "last_interaction": 0,
                "importance": 7,
                "always_display": False,
            },
            {
                "name": "Context Dump",
                "value": "HARDCODED",
                "description": "Gives the agent additional context about the current task.",
                "last_interaction": 0,
                "importance": 10,
                "always_display": True,
            }
        ]
        self.command_instructions = self.get_default_command_instructions()

        # -- Changing Variables --
        self.commands :list = []
        self.extraction_failure = False
        self._prompt :str = ""
        self._tmp_context_data :str = ""
        self.replying :bool = False # indicates if the agent is currently replying to a user

        # TODO: REMOVING NOT YET IMPLEMENTED COMMANDS
        self.command_instructions["search"]["active"] = False # Laked the time to implement this
        pass

    def get_name(self):
        return self.name

    def reset(self):
        self.clean_chat.clear()
        self.chat.clear()
        self.complete_chat.clear()
        self.code_list = []
        delete_directory_with_content(self.agent_dir)

    def update_last_use_context(self, name):
        for context_item in self.context_data:
            if context_item["name"] == name:
                context_item["last_interaction"] = 0
                break

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
        self._prompt = prompt

        entire_prompt = \
            f"{prompt}\n---\n{self.get_instruction_str()}\n---\n{prompt}\n---\n{self.generate_context_data()}"

        self.complete_chat.add_message("Prompt", entire_prompt)

        response = basic_prompt(entire_prompt, self.role)

        self.commands, extraction_failures = command_util.find_commands_in_string(response)
        if len(extraction_failures) >0:
            self.extraction_failure = True

        command_responses = execute_commands(self.commands, self)

        self.chat.add_message(self.name, response)
        self.complete_chat.add_message(self.name, response)
        if extraction_failures:
            for failure in extraction_failures:
                self.chat.add_message("Extraction Failure", failure)
                self.complete_chat.add_message("Extraction Failure", failure)
            self.extraction_failure = False
        for command, response in command_responses.items():
            self.chat.add_message(command, response)
            self.complete_chat.add_message(command, response)
        pass

    def handle_message(self, sender):
        if self.replying:
            pass
        elif sender != self.name and sender != "System":
            self.replying = True
            self.prompt_agent(f"The User has sent a message: {self.clean_chat.get_last_message_of_sender('User')}\n"
                              f"Please solve the query.\n"
                              "Please go through the task step by step:\n"
                              "1. Read the User's message carefully. Incase it is unclear or you need more information, please ask the User for more information.\n"
                              "2. Read the Context and find relevant information.\n"
                              "2. Explain step by step how you want to solve the problem and think about what commands you need or want to use.\n"
                              "3. Follow your own plan. \n"
                              "     * Some commands may need for you to wait for an answer in this case, it is recommended, to wrap your answer up, to let the command run and to retrieve the results in the next prompt.\n"
                              "4. Finally wrap up your answer and provide the User with a response.\n"
                              "5. Consider if you have learned anything new and if you want to add it to your long-term memory.\n"
                              f"**Tip:** When Coding I highly recommend to check via print statements if the code is working as expected. Especially if you want to build on the code or if you are loading a file.\n")

            while self.clean_chat.get_last_sender() != self.name:
                self.prompt_agent(f"You are taking over an ongoing task from a previous agent.\n\n"
                                  f"**Original User Request:**\n{self.clean_chat.get_last_message_of_sender('User')}\n\n"
                                  f"**Your Task Now:**\n"
                                  f"Please review the original request and the work done so far.\n"
                                  f"1. Determine the next logical step needed to fulfill the user's request.\n"
                                  f"2. Execute that step, using appropriate commands (`<code>`, `<query>`, etc.).\n"
                                  f"3. If you can now fully answer the user's query, formulate the final answer and provide it within the `<response>` tag.\n"
                                  f"4. If your action requires waiting for results, clearly state what you are doing.\n"
                                  f"5. Consider if any findings should be saved to `<long_memory>`."
                                  f"**Tip:** When Coding I highly recommend to check via print statements if the code is working as expected. Especially if you want to build on the code or if you are loading a file.\n"
                                  "**Important:** Ensure that your response adds to the conversation and doesn't repeat previous messages and or commands. I may sometimes be best to confirm with the User if the task is still relevant.\n")
        self.replying = False

    def generate_context_data(self):
        context_data = f"# **Context**\n\n"

        always_display_count = 0
        for context_item in self.context_data:
            if context_item["always_display"]:
                always_display_count += 1


        threshold = 0.7
        self.context_data = sorted(
            [item for item in self.context_data if item["always_display"] or (
                    1 / (1 + np.exp( -0.01 * ( item["last_interaction"]**2 + item["importance"]**2 +
                            (np.maximum(0, item["importance"] - 8.5))**4 ) ))) >= threshold],
            key=lambda x: 1 / (1 + np.exp( -0.01 * ( x["last_interaction"]**2 + x["importance"]**2 +
                                                     (np.maximum(0, x["importance"] - 8.5))**4 ) ))
        )

        for i, context_item in enumerate(self.context_data):
            name = context_item["name"]
            value = context_item["value"]
            if callable(value):
                value = value()

            if name == "Context Dump":
                context_item_str = f"## **{name}**:\n"
                remaining_context = config.max_context_tokens - count_context_length(context_data)
                context_item_str += f"{self.get_context_dump(remaining_context)}\n\n"
            elif isinstance(value, Chat):
                context_item_str = f"## **{name}**:\n"
                chat_content = value.get_last_n_tokens_in_xml_str(config.MAX_LENGTH_CONTEXT_ITEM)
                context_item_str += f"{chat_content}\n\n"
            else:
                context_item_str = f"## **{name}**:\n"
                context_item_str += f"{value}\n\n"
                context_item_str += "\n"


            if context_item["always_display"]:
                context_data += context_item_str
                always_display_count -= 1
            elif (count_context_length(context_data) +
                  count_context_length(context_item_str) +
                  (config.MAX_LENGTH_CONTEXT_ITEM*always_display_count)) < config.max_context_tokens:
                context_data += context_item_str
                self._tmp_context_data += context_data

            context_item["last_interaction"] += 1

        return context_data

    def get_xml_short_memory(self):
        short_memory = self.get_short_memory()
        if short_memory is not None:
            return f"<short_memory>{short_memory}</short_memory>"
        else:
            return "<short_memory> </short_memory>"

    def get_xml_long_memory(self):
        long_memory = self.get_long_memory()
        if long_memory is not None:
            return self.convert_query_results_to_xml_schema(long_memory, root_name="long_memory")
        else:
            return "<long_memory> </long_memory>"

    def get_context_dump(self, max_length :int = None):
        context_xml_str = "Whenever possible, please use the following context to answer the User's query.\n"
        context_xml_str += "The context is sorted by relevance. Reference the context source you used in the user response.\n"

        n_results = int(config.max_context_tokens / config.RAG_CHUNK_SIZE * 2)
        context_dict = query_rag(f"{self._prompt}\n---\n{self._tmp_context_data}", self.chroma_collection,
                                 n_results)
        context_xml_str += self.convert_query_results_to_xml_schema(context_dict, max_length=max_length, root_name="context")

        return context_xml_str

    def convert_query_results_to_xml_schema(self, query_results, max_length=None, root_name="context"):
        ids = query_results['ids'][0]
        page_contents = query_results['documents'][0]
        metadatas = query_results['metadatas'][0]

        xml_str = f"<{root_name}>\n"

        for i in range(len(ids)):
            source = metadatas[i].get("url", metadatas[i].get("pdf_name", None))
            if source is None:
                xml_str += f'  <item>'
            else:
                xml_str += f'  <item source="{source}">'
            xml_str += f"{page_contents[i]}\n  </item>\n"
            if max_length is not None and count_context_length(xml_str) > max_length:
                break

        xml_str += f"</{root_name}>\n"
        return xml_str

    def add_short_memory(self, text: str):
        util.save_text(f"{self.agent_dir}/{self.name}_memory", text)
        pass

    def get_short_memory(self):
        return util.load_text(f"{self.agent_dir}/{self.name}_memory")

    def get_long_memory(self):
        return rag.query_rag(f"{self._prompt}\n---\n{self._tmp_context_data}",
                             self.long_term_memory_collection, n_results=1)

    def add_custom_command_instructions(self, name, instructions, active = True):
        # Remove the last item and store it
        last_key, last_value = self.command_instructions.popitem()
        self.command_instructions[name] = {"text": instructions, "active": active}
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

    def get_available_document_filepaths(self):
        all_files = []
        for root, dirs, files in os.walk(self.agent_dir):
            for file in files:
                all_files.append(os.path.join(root, file))
        return all_files

    def get_default_command_instructions(self):
        return {
            "introduction": {
                "text": (
                    "# **Command Instructions**\n"
                    "You can interact with multiple agents in this project using an **XML-based format**. "
                    "Your interactions will be stored, and past responses may be referenced in future prompts.\n\n"

                    "### **Use `<![CDATA[...]]>` if necessary!**\n"
                    "The `<![CDATA[...]]>` section is crucial when embedding code within XML-like tags. "
                    "It tells the parser to treat everything inside it as raw text, ignoring characters that normally have special meaning in XML, such as `<`, `>`, and `&`. "
                    "Python code frequently uses these characters (e.g., for comparisons like `count < 5`, bitwise operations like `flags & 1`, or even within strings). "
                    "Without `CDATA`, the parser would misinterpret this code as broken XML, causing errors. "
                    "Using `CDATA` allows you to write or paste your Python code naturally without needing to manually escape these special characters (like writing `&lt;` for `<`), making your code blocks cleaner and less error-prone.\n\n"
                ),
                "active": True
            },
            "short_memory": {
                "text": (
                    "## **Short-Term Memory**\n"
                    "- Save temporary information:\n"
                    "```xml\n"
                    "<short_memory>\n"
                    "<![CDATA[\n"
                    "Your text here\n"
                    "]]>\n"
                    "</short_memory>\n"
                    "```\n"
                    "- Resets with each new message.\n"
                    f"- Maximum capacity: **{config.MAX_SHORT_MEMORY_TOKENS}** tokens.\n\n"
                ),
                "active": True
            },
            "long_memory": {
                "text": (
                    "## **Long-Term Memory (RAG-DB)**\n"
                    "- Save persistent knowledge:\n"
                    "```xml\n"
                    "<long_memory>\n"
                    "<![CDATA[\n"
                    "Your text here\n"
                    "]]>\n"
                    "</long_memory>\n"
                    "```\n"
                    f"- Stored in chunks of **{config.RAG_CHUNK_SIZE}** tokens.\n"
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
                    "Please ensure to add the entire path to the document in the pseudo XML.\n"
                    "*Important:* When this command is used it is impossible to reply to the user at the same time as you will have to wait for the results.\n\n"
                ),
                "dynamic_data": self.get_available_document_filepaths,
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
                    "*Important:* When this command is used it is impossible to reply to the user at the same time as you will have to wait for the results.\n\n"
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
                    "<![CDATA[\n"
                    "# Your Python code here\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    

                    "### **Adding Dependencies**\n"
                    "```xml\n"
                    "<code requirements=[\"numpy\"]>\n"
                    "<![CDATA[\n"
                    "import numpy as np\n"
                    "a = np.array([1,2,3])\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"

                    "### **Accessing Files**\n"
                    "**Reading Files**\n"
                    "```xml\n"
                    "<code input_files=[\"uploads/data.txt\"]>\n"
                    "<![CDATA[\n"
                    "filepath = os.path.join(\"/files\", \"uploads/data.txt\")\n"
                    "with open(filepath, \"r\") as f:\n"
                    "    content = f.read()\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"    
                    
                    
                    "**Saving Files**\n"
                    "```xml\n"
                    "<code output_files=[\"output.txt\"]>\n"
                    "<![CDATA[\n"
                    "filepath = os.path.join(\"/files\", \"output.txt\")\n"
                    "with open(filepath, \"w\") as f:\n"
                    "    f.write(\"Hello, world!\")\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    
                    "Files can be found under the `files` directory. The available files, and filepaths can be found under the section *Project Documents*.\n"
                    "If the required files have not been explicitly mentioned in the pseudo xml, then they will not be available in the execution environment. "
                    "If you want to access a file please ensure to add the entire path to it both in the pseudo xml as in the python code. \n"
                    "Please also ensure to save and import the output and input files both in the pseudo xml and in the python code. \n"

                    "### **Versioning and Tagging Code**\n"
                    "```xml\n"
                    "<code tag=\"experiment-alpha\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "x = 42\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n"
                    
                    "Please add both a tag and a version to your code. as this increases the human readability of the code.\n\n"
                    
                    "### **Reusing Code**\n"
                    
                    "You can reuse previously written code by referencing a code `tag` and optionally a `version`. "
                    "If no version is provided, the latest version for that tag is used.\n\n"
                    
                    "```xml\n"
                    "<code tag=\"add\">\n"
                    "<![CDATA[\n"
                    "def add(a, b):\n"
                    "    return a + b\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "```xml\n"
                    "<code import={\"tag\": \"add\"}>\n"
                    "<![CDATA[\n"
                    "print(add(3, 4))\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "It is also possible to import multiple code snippets by providing a list of tags (`<code import=[{\"tag\": \"add\"}, {\"tag\": \"sub\"}]>...</code>`). "
                    
                    "💡 *Tip:* Work in small, testable code chunks to reduce errors when combining logic.\n\n"
                    
                    "### **Frontend**\n"
                    "You can also build a frontend using dash."
                    "Simply add a frontend tag to your code and the frontend will be displayed in the dashboard.\n"
                    "```xml\n"
                    "<code frontend=\"True\">\n"
                    "<![CDATA[\n"
                    "import dash\n"
                    "from dash import html\n"
                    "\n"
                    "# Initialize the Dash app\n"
                    "app = dash.Dash(__name__)\n"
                    ""
                    "# Define the layout of the app (just static HTML elements)\n"
                    "app.layout = html.Div([\n"
                    "    html.H1(\"Simplest Dash App\" tag=\"simple-dashboard\" version=\"1.0\"), # A header\n"
                    "    html.P(\"This app just displays static text.\") # A paragraph\n"
                    "])\n"
                    "]]>\n"
                    "</code>\n"
                    
                    "**Important: The dash app has to be called `app` otherwise it will not run!**"

                    "💡 *Tip:* Recently dash changed its configuration now only `dash.run()` is valide `dash.run_server()` is deprecated.\n\n"
                    
                    "### **Execution Environment**\n"
                    "- **Isolated:** Runs in a containerized environment, separated from other processes.\n"
                    "- **Restricted Network Access:** Outbound connections are generally blocked, except for package installation from approved repositories during setup.\n\n"
                    "This ensures secure and controlled execution of the provided Python code.\n\n"

                    "*Important:* When this command is used it is impossible to reply to the user at the same time as you will have to wait for the results.\n\n"
                ),
                "active": True
            },
            "response_to_user": {
                "text": (
                    "## **Responding to the User**\n"
                    "When responding to the User, you can use the `<response>` tag to structure your answers.\n"
                    
                    "Your task is only complete if you have replied to the user. "
                    "Any information written outside of the response is not privy to the user.\n"
                    
                    "Here is an example:\n"
                    "```xml\n"
                    "<response>\n"
                    "<![CDATA[\n"
                    "The answer to the User's query goes here.\n"
                    "]]>\n"
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
                    "- **Use the `<response>` tag to structure your answers only once you have come to a conclusion or check if you understood the instructions.**\n"
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
                os.makedirs(os.path.join(self.agent_dir,"uploads"), exist_ok=True)
                file_path = f"uploads/{filename}"
                with open(os.path.join(self.agent_dir,file_path), "wb") as f:
                    f.write(decoded)
                self.add_message("System", f"Upload of file {file_path} succeeded")
                execute_document_command(file_path, self)
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

    def get_codes(self):
        return self.code_list

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

    def get_chroma_collection(self):
        return self.chroma_collection

    def get_long_term_memory_collection(self):
        return self.long_term_memory_collection

    def __del__(self):
        self.reset()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name