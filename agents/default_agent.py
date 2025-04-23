import base64
import itertools
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
from util.colors import ORANGE, RESET, RED, PINK


class Agent:
    def __init__(self,
                 name = "Agent",
                 role = "You are the AI Agent. You are given tasks by the User and converse with him in a chat. \n"
                        "Your handle in the chat is `Agent`. "
                        "The User can only see information in the `<response>` section of the chat (explained below..)\n",
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

        self.context_data = self.get_default_context_data()
        self.command_instructions = self.get_default_command_instructions()

        # -- Changing Variables --
        self.commands :list = []
        self.extraction_failure = False
        self._prompt :str = ""
        self._tmp_context_data_str :str = ""
        self.replying :bool = False # indicates if the agent is currently replying to a user

        self.max_iterations = 10
        self.no_consecutive_messages = False

        # TODO: REMOVING NOT YET IMPLEMENTED COMMANDS
        self.command_instructions["search"]["active"] = False # Laked the time to implement this

        pass

    def get_name(self):
        return self.name

    def get_default_context_data(self):
        return {
            "History": {
                "value": self.chat,
                "description": "Previous outputs tool actions and conversations.",
                "last_interaction": 0,
                "importance": 0,
                "always_display": True,
            },
            "Short-Tern Memory": {
                "value": self.get_xml_short_memory,
                "description": "Stores temporary information.",
                "last_interaction": 0,
                "importance": 3,
                "always_display": True
            },
            "Long-Term Memory": {
                "value": self.get_xml_long_memory,
                "description": "Stores persistent knowledge.",
                "last_interaction": 0,
                "importance": 9,
                "always_display": True,
            },
            "Context Dump": {
                "value": "HARDCODED",
                "description": "Gives the agent additional context about the current task.",
                "last_interaction": 10,
                "importance": 10,
                "always_display": True,
            }
        }

    def update_last_use_context(self, name):
        self.context_data[name]["last_interaction"] = 0

    def add_context_data(self, name, value, description="No description available", importance = 5, always_display = False):
        self.context_data[name] = {
            "value": value,
            "description": description,
            "last_interaction": 0,
            "importance": importance,
            "always_display": always_display
        }

    def use_tool(self, llm_response):
        self.commands, extraction_failures = command_util.find_commands_in_string(llm_response)
        if len(extraction_failures) > 0:
            self.extraction_failure = True
        command_responses = execute_commands(self.commands, self)

        if extraction_failures:
            for failure in extraction_failures:

                self.add_context_data("Extraction Failure", failure, description="Extraction Failure",
                                      importance=8)

                self.complete_chat.add_message("Extraction Failure", failure)
            self.extraction_failure = False
        for command, response in command_responses.items():
            self.chat.add_message(command, response)
            self.update_last_use_context("History")
            self.complete_chat.add_message(command, response)
        pass

    def prompt_agent(self):
        self.replying = True
        self._prompt = "# User Prompt\n" + self.clean_chat.get_last_messages_of_sender('User') + "\n"

        i = 0
        while self.clean_chat.get_last_sender() != self.name and i < self.max_iterations:
            print(f"Executing prompt {i + 1}")

            entire_prompt = \
                f"{self._prompt}\n---\n{self.get_instruction_str()}\n---\n{self.generate_context_data()}"
            self.prompt(entire_prompt)

            i += 1
        self.replying = False
        pass

    def prompt(self, prompt, yes_no_prompt = False):
        self.complete_chat.add_message("Prompt", prompt)
        try:
            response = basic_prompt(prompt, self.role)
        except Exception as e:
            print(f"{RED}Error in prompt:{RESET} {e} ")
            response = "Error when attempting to prompt the LLM. Please try again."
        self.chat.add_message(self.name, response)


        self.complete_chat.add_message(self.name, response)

        if yes_no_prompt:
            if "<Yes>" in response or "<yes>" in response:
                return True
            else:
                return False
        else:
            self.use_tool(response)
        return None

    def handle_message(self, sender):
        if self.replying:
            pass
        elif sender != self.name and sender != "System":
            self.prompt_agent()
        pass

    def generate_context_data(self, status_info = False):
        context_data_str = f""

        always_display_count = 0
        for name, context_item in self.context_data.items():
            if context_item["always_display"]:
                always_display_count += 1


        self.context_data = dict(sorted(
            self.context_data.items(),
            key=lambda x: 1 / (1 + np.exp( -0.01 * ( x[1]["last_interaction"]**2 + x[1]["importance"]**2 +
                                                     (np.maximum(0, x[1]["importance"] - 8.5))**4 ) ))
        ))

        for i, (name, context_item) in enumerate(self.context_data.copy().items()):
            print(f"{ORANGE} Current context item: {name} ({i + 1}/{len(self.context_data)}) {RESET}")
            value = context_item["value"]
            if callable(value):
                value = value()
            description_ = context_item["description"]

            if name == "Context Dump" and not status_info:
                context_item_str = f"# **{name}**:\n"
                remaining_context = config.max_context_tokens - count_context_length(context_data_str)
                context_item_str += f"{self.get_context_dump(remaining_context)}\n---\n"
            elif name == "Context Dump" and status_info:
                continue
            elif isinstance(value, Chat):
                context_item_str = f"# **{name}**:\n"
                context_item_str += f"Chat with {description_}\n"
                chat_content = value.get_last_n_tokens_in_xml_str(config.max_chat_tokens)
                context_item_str += f"{chat_content}\n---\n"
            else:
                context_item_str = f"# **{name}**:\n"
                context_item_str += f"{value}\n---\n"
                context_item_str += "\n"


            if context_item["always_display"]:
                context_data_str += context_item_str
                always_display_count -= 1
            elif (count_context_length(context_data_str) +
                  count_context_length(context_item_str) +
                  (config.max_generic_content_length * always_display_count)) < config.max_context_tokens:
                context_data_str += context_item_str
                self._tmp_context_data_str += context_data_str

            if not status_info:
                context_item["last_interaction"] += 1

                if context_item["last_interaction"] > 10 and not context_item["always_display"]:
                    self.context_data.pop(name)


        return context_data_str

    def get_xml_short_memory(self):
        short_memory = self.get_short_memory()
        if short_memory is not None:
            return f"<short_memory>{short_memory}</short_memory>"
        else:
            return "<short_memory> </short_memory>"

    def get_xml_long_memory(self):
        long_memory = self.get_long_memory()
        if long_memory is not None:
            try:
                return self.convert_query_results_to_xml_schema(long_memory, root_name="long_memory")
            except Exception as e:
                print(f"{RED}Error in converting long memory to XML: {e}{RESET}")
                return "<long_memory> </long_memory>"
        else:
            return "<long_memory> </long_memory>"

    def get_context_dump(self, max_length :int = None):
        context_xml_str = "Whenever possible, please use the following context to answer the User's query.\n"
        context_xml_str += "The context is sorted by relevance. Reference the context source you used in the user response.\n"

        n_results = int(config.max_context_tokens / config.RAG_CHUNK_SIZE * 10)
        context_dict = query_rag(f"{self._prompt}\n---\n{self._tmp_context_data_str}", self.chroma_collection,
                                 n_results)
        if isinstance(context_dict, list) or isinstance(context_dict, dict):
            context_xml_str += self.convert_query_results_to_xml_schema(context_dict, max_length=max_length,
                                                                        root_name="context")
        else:
            print(f"{PINK}Error when attempting to query the context: {str(context_dict)[:100]}{RESET}")
            self.chat.add_message("Error", f"Error when attempting to query the context: {context_dict}")
            context_xml_str = ""
        return context_xml_str

    def _build_xml_string(self, item_xml_strings, k, root_name):
        """Helper function to build the XML string for the first k items."""
        if k == 0:
            # Handle edge case of zero items - return just root tags
            return f"<{root_name}>\n</{root_name}>\n"

        # Select the first k item strings
        selected_items = item_xml_strings[:k]

        # Join items with newlines and add root tags
        # Note: Ensure each item string already ends with a newline if desired,
        # or adjust the join logic. The original code added \n after </item>.
        # Let's assume item strings are like '  <item...>...\n  </item>\n'
        content = "".join(selected_items)
        xml_str = f"<{root_name}>\n{content}</{root_name}>\n"
        return xml_str

    def convert_query_results_to_xml_schema(self, query_results, max_length=None, root_name="context"):
        """
        Converts query results to XML, respecting max_length using binary search
        to minimize calls to count_context_length.
        """
        # --- 1. Data Preparation ---
        # Flatten results consistently (same as original)
        ids = query_results['ids'][0]
        page_contents = query_results['documents'][0]
        metadatas = query_results['metadatas'][0]

        if not ids:
            return f"<{root_name}>\n</{root_name}>\n"  # Handle empty input

        # --- 2. Prepare Individual Item XML Strings ---
        item_xml_strings = []
        for i in range(len(ids)):
            source = metadatas[i].get("url", metadatas[i].get("pdf_name", None))
            xml_item_str = ""
            if source is None:
                xml_item_str += f'  <item id="{ids[i]}">'  # Added ID for potential usefulness
            else:
                # Basic escaping for XML attribute value
                safe_source = source.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"",
                                                                                                             "&quot;").replace(
                    "'", "&apos;")
                xml_item_str += f'  <item id="{ids[i]}" source="{safe_source}">'

            # Basic escaping for XML content (needs more robust solution for production)
            safe_content = page_contents[i].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml_item_str += f"{safe_content}\n  </item>\n"
            item_xml_strings.append(xml_item_str)

        total_items = len(item_xml_strings)

        # If no length limit, return all items
        if max_length is None:
            return self._build_xml_string(item_xml_strings, total_items, root_name)

        # --- 3. Binary Search for Optimal Number of Items (k) ---
        best_k = 0  # Stores the highest k that fits within max_length
        low = 0
        high = total_items  # Search space is [0, total_items] inclusive for k

        # Pre-calculate length of empty root tags as a baseline minimum
        empty_xml = self._build_xml_string([], 0, root_name)
        min_possible_length = count_context_length(empty_xml)

        if max_length < min_possible_length:
            print(
                f"Warning: max_length ({max_length}) is less than the minimum length of empty root tags ({min_possible_length}). Returning empty context.")
            return empty_xml

        search_steps = 0  # For analysis/logging

        while low <= high:
            search_steps += 1
            mid = (low + high) // 2
            if mid == 0:  # Ensure we check the empty case if needed
                current_length = min_possible_length
            else:
                # Build XML string for 'mid' items
                test_xml_str = self._build_xml_string(item_xml_strings, mid, root_name)
                # Call the expensive function
                current_length = count_context_length(test_xml_str)

            # print(f"  Binary Search: Trying k={mid}, length={current_length}, max_length={max_length}") # Debug logging

            if current_length <= max_length:
                # This number of items fits. It might be the optimal K.
                # Try including more items.
                best_k = mid
                low = mid + 1
            else:
                # This number of items is too long.
                # Try including fewer items.
                high = mid - 1

        print(
            f"Collection Results: Found optimal {best_k} items out of {total_items} using binary search ({search_steps} checks).")

        # --- 4. Construct Final XML ---
        final_xml_str = self._build_xml_string(item_xml_strings, best_k, root_name)

        # Optional: Final verification (mostly for debugging the binary search logic)
        # final_length = count_context_length(final_xml_str)
        # print(f"Final XML length: {final_length} (max_length: {max_length})")
        # assert final_length <= max_length or best_k == 0 # Should always hold if max_length >= min_possible_length

        return final_xml_str

    def add_short_memory(self, text: str):
        self.update_last_use_context("Short-Term Memory")
        util.save_text(f"{self.agent_dir}/{self.name}_memory", text)
        pass

    def get_short_memory(self):
        return util.load_text(f"{self.agent_dir}/{self.name}_memory")

    def get_long_memory(self):
        return rag.query_rag(f"{self._prompt}\n---\n{self._tmp_context_data_str}",
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
                        dynamic_data_str = value["dynamic_data"]()
                        instructions_str += value["text"].format(dynamic_info=dynamic_data_str)
                else:
                    instructions_str += value["text"]

        return instructions_str

    def get_available_document_filepaths_str(self):
        all_files = ""
        for root, dirs, files in os.walk(self.agent_dir):
            for file in files:
                path = os.path.relpath(os.path.join(root, file), self.agent_dir).replace("\\", "/")
                if path.startswith("uploads") or path.startswith("output"):
                    all_files += f"- {path}\n"
        if all_files == "":
            all_files = "*No files available*"
        return all_files

    def get_default_command_instructions(self):
        return {
            "introduction": {
                "text": (
                    "# **Tool Instructions**\n"
                    "To perform actions beyond conversation, such as running code or searching, you will use commands "
                    "formatted as **XML tags**. Your interactions using these tags (both the commands you issue and "
                    "the results you receive) are recorded and may be referenced in later turns.\n\n"
                    
                    "### Important: Avoiding Tag Confusion\n"
                    "The command parser looks for specific XML tags like `<code>`, `<query>`, etc. **Do NOT use XML-style formatting (e.g., `<my_note>`, `<step_1>`) in your regular conversational text or explanations**, as this confuses the parser and can cause errors.\n"
                    "To refer to tag names within your text, use textual descriptions (e.g., 'the code tag'), rather than literal `< >` characters.\n\n"
                    "**Only use the exact, documented command tags when you intend to invoke a specific tool.**\n\n"
                    "### **Essential: Using `<![CDATA[...]]>`**\n\n"
                    "When you place code (e.g., Python) inside specific XML tags like `<code>` or `<python>`, you **must** wrap the entire code block within `<![CDATA[...]]>`. \n\n"
                    "**Why is `CDATA` required?**\n"
                    "* **Prevents XML Errors:** Code often contains characters like `<`, `>`, and `&` which have special meanings in XML...\n" # Truncated for brevity
                    "* **Preserves Code Integrity:** `CDATA` tells the parser to treat everything within it as raw character data...\n\n" # Truncated for brevity
                    "**Always use `CDATA` for code embedded within command tags.** Refer to the specific instructions for each available tool/command for details on their tags and arguments.\n"
                ),
                "active": True
            },
            "code": {
                "text": (
                    "## **Code (`<code>`)**\n"
                    "This system allows you to run Python code in a secure, resource-limited environment. "
                    "Use the structured XML-like format below to define execution parameters.\n"
                    "Please provide code always in the `<code ...><![CDATA[...]]></code>` format. \n"
                    "**Important:** If the user request any code, please use the `<code>` tag. \n\n"
                    
                    "💡 *Tip:* Add many print and try catch blocks to identify your own errors.\n\n"

                    "### **Basic Execution**\n"
                    "```xml\n"
                    "<code tag=\"simple example\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "# Your Python code here\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    
                    "### **Adding Dependencies**\n"
                    "```xml\n"
                    "<code requirements=[\"numpy\"] tag=\"requirements example\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "import numpy as np\n"
                    "a = np.array([1,2,3])\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "By default, the code will be executed in a virtual environment with the following packages:\n"
                    "pandas, numpy, matplotlib, seaborn, plotly, dash, scikit-learn, datetime\n\n"
                    
                    
                    "### **Frontend**\n"
                    "You can also build a frontend using dash."
                    "Simply add a frontend tag to your code and the frontend will be displayed in the dashboard.\n"
                    "```xml\n"
                    "<code frontend=\"True\" tag=\"dash example\" version=\"1.0\">\n"
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
                    
                    "**Important: The dash app has to be called `app` otherwise it will not run!**\n\n"

                    "### **Accessing Files**\n"
                    "**Reading Files**\n"
                    "```xml\n"
                    "<code tag=\"file usage\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "with open(\"uploads/data.txt\", \"r\") as f:\n"
                    "    content = f.read()\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"    
                    "**Important:** Only files in the `uploads` directory are available. \n\n"
                    
                    "**Saving Files**\n"
                    "```xml\n"
                    "<code tag=\"output\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "with open(\"output/message.txt\", \"w\") as f:\n"
                    "    f.write(\"Hello, world!\")\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "**Important:** Output files will only be saved in the `output` directory if explicitly placed there. \n\n"

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
                    "<code tag=\"add\" version=\"1.0\">\n"
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
                    "💡 *Tip:* output files from previous code snippets are available in the `output` directory, *if* they are imported.\n\n"

                    "**Important:** When this command (`<code>`) is used it is impossible to reply to the user at the same time as you will have to wait for the results.\n\n"
                ),
                "active": True
            },
            "response": {
                "text": (
                    "## **Responding to the User (`<response>`)**\n\n"
                    "### **Crucial: The User's Perspective**\n"
                    "The user you are assisting has a limited view of our interaction. They **only** see:\n"
                    "1.  Their own prompts/messages to you.\n"
                    "2.  The exact content you place inside `<response>` tags.\n"
                    "3.  The output (e.g., print statements, plots, errors) generated by any `<code>` command you execute.\n\n"
                    "The user **does NOT** see your internal reasoning, planning steps, intermediate thoughts written outside tags, the code within `<code>` tags (only its output), or the results of non-code commands like `<query>`.\n\n"

                    "**Therefore, the `<response>` tag is your primary (and only) communication channel and must contain everything the user needs to understand the answer.**\n\n"
                    
                    "### **Usage Rule: Exclusivity of `<response>`**\n\n"
                    "The `<response>` tag signals the completion of your task for the current user request. Therefore, it **must generally be used exclusively** in your output turn.\n\n"
                    "* **You CANNOT combine `<response>` with action tags** like `<code>`, `<query>`, or `<document>` in the same output. Attempting to do so will result in an error.\n"
                    "* You **CAN** optionally include a `<long_memory>` tag alongside `<response>` if you need to save information while responding.\n"
                    "* Any reasoning or planning text outside of tags should also conclude *before* you generate the `<response>`.\n\n"
                    "**Workflow:** If you need to perform an action (like running code), do that in one turn. Then, in a *subsequent* turn (after assessing the results), generate the final `<response>`.\n\n"


                    "### **What to Include in Your `<response>`:**\n"
                    "To provide a helpful and complete answer, your text inside `<response><![CDATA[...]]></response>` should generally:\n\n"
                    "* **Acknowledge/Reference the User's Query:** Briefly mention the core question you are answering. (e.g., \"Regarding your question about X...\", \"You asked for Y, here is the result:\").\n"
                    "* **Provide the Direct Answer:** State the solution, result, or information clearly and upfront.\n"
                    "* **Explain Your Key Steps (User-Friendly):** Briefly summarize *how* you (as the Agent) arrived at the answer, "
                    "especially if it involved actions the user isn't directly seeing results from (like searches) or complex logic. Focus on what's relevant for the user to understand the context or validity of the answer.\n"
                    "    * *Example:* \"I searched for recent articles on that topic and found...\"\n"
                    "    * *Example:* \"To calculate this, I wrote some code to process the data you provided. The main steps were...\"\n"
                    "* **Interpret Code/Data Output:** If you ran code (in the history) (`<code>`), don't just rely on the user seeing the raw output. Explain what the output means in the context of their query.\n"
                    "    * *Example:* \"The code calculated the average, and as you can see in the output above, the result is 42.5.\"\n"
                    "    * *Example:* \"I generated a plot showing the trend, which is displayed above.\"\n"
                    "* **Be Self-Contained:** Ensure the response makes sense on its own, considering the user only sees their query, your response, and code output.\n\n"

                    "### **Example Structure:**\n"
                    "```xml\n"
                    "<response>\n"
                    "<![CDATA[\n"
                    "Okay, I looked into your question about [User's Topic]. \n\n"
                    "The answer is [Direct Answer/Result].\n\n"
                    "To find this, I [briefly explain key steps, e.g., ran a search / analyzed the data / executed code]. [If code was run:] The code output above shows [interpretation of the output].\n\n"
                    "[Optional: Add any necessary context, caveats, or next steps/questions].\n"
                    "]]>\n"
                    "</response>\n"
                    "```\n"
                    "**Goal:** Your response should bridge the gap between the user's question and the final answer, making the process understandable from their limited perspective.\n"
                ),
                "active": True
            },
            "short_memory": {
                "text": (
                    "## **Short-Term Memory (`<short_memory>`)**\n"
                    "- Save temporary information:\n"
                    "```xml\n"
                    "<short_memory>\n"
                    "<![CDATA[\n"
                    "Your text here\n"
                    "]]>\n"
                    "</short_memory>\n"
                    "```\n"
                    "- Use this to store information that is relevant for the current task. The history will be truncated after a certain length. The Short-Term History will always remain in the context, until the history is reset.\n"
                ),
                "active": True
            },
            "long_memory": {
                "text": (
                    "## **Long-Term Memory (RAG-DB) (`<long_memory>`)**\n"
                    "- Save persistent knowledge:\n"
                    "```xml\n"
                    "<long_memory>\n"
                    "<![CDATA[\n"
                    "Your text here\n"
                    "]]>\n"
                    "</long_memory>\n"
                    "```\n"
                    "- Use this to store information that could be useful beyond this project.\n"
                    "- Stored in chunks of **8192** tokens.\n"
                    "- Relevant sections will be retrieved automatically when working on related tasks.\n\n"
                ),
                "active": True
            },
            "query": {
                "text": (
                    "## **Retrieving Information (`<query>`)**\n"
                    "\n"
                    "### **Querying Stored Information**\n"
                    "To access relevant information from the **RAG-DB (long-term memory)** or stored **documents**, use the `<query>` tag.\n\n"
                    "#### **General Query (Default)**\n"
                    "A `<query>` searches relevant documents by default.\n"
                    "Example:\n"
                    "```xml\n"
                    "<query>How can one reverse a linked list?</query>\n"
                    "```\n\n"
                    "#### **Targeted Queries**\n"
                    "You can specify the source:\n"
                    "\n"
                    "- **Long-Term Memory:**\n"
                    "```xml\n"
                    "<query type=\"memory\">Summarize previous discussions about model selection.</query>\n"
                    "```\n"
                    "- **Documents (default):**\n"
                    "```xml\n"
                    "<query type=\"documents\">Find references to data privacy regulations.</query>\n"
                    "```\n\n"
                ),
                "active": True
            },
            "document": {
                "text": (
                    "## **Project Documents (`<document>`)**\n"
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
                "dynamic_data": self.get_available_document_filepaths_str,
                "active": True
            },
            "search": {
                "text": (
                    "## **Web Search (`<search>`)**\n"
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

    def upload_file(self, upload_contents, filename):
        if upload_contents is not None:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                os.makedirs(os.path.join(self.agent_dir,"uploads"), exist_ok=True)
                file_path = f"uploads/{filename}"
                abs_file_path = os.path.abspath(os.path.join(self.agent_dir,file_path))
                with open(abs_file_path, "wb") as f:
                    f.write(decoded)
                self.add_message("System", f"Upload of file {file_path} succeeded")
                execute_document_command(abs_file_path, self)
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

        num_tokens = count_context_length(text)
        if num_tokens > config.max_prompt_tokens:
            sender = "System"
            text = f"Message too long ({num_tokens} tokens). Please shorten your message."

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

    def get_code_script(self, name: str):
        for code in self.code_list:
            if code.get_name() == name:
                return code.code
        return None

    def get_reply(self):
        return self.clean_chat.get_last_messages_of_sender("Agent")

    def get_chroma_collection(self):
        return self.chroma_collection

    def get_long_term_memory_collection(self):
        return self.long_term_memory_collection

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name