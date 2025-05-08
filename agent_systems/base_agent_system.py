import base64
import os

import numpy as np
from pygments.lexer import default

import rag
import util
import config
from agent_objs.code_manager import CodeManager

from tools import command_util
from llm_functions import count_context_length, basic_prompt
from tools import execute_commands, execute_document_command
from agent_objs.chat import Chat
from rag import query_rag

from util.colors import ORANGE, RESET, RED, PINK



class BaseAgentSystem:
    def __init__(self, system_name, description, agents, default_agent=None):

        self.system_name = system_name
        self.technical_name = self.system_name.lower().replace(" ", "_")
        self.description = description

        self.agent_dict = {}
        for agent in agents:
            self.agent_dict[agent.get_name()] = agent

        if not default_agent:
            self.default_agent = agents[0]
        else:
            self.default_agent = [agent for agent in agents if agent.get_name() == default_agent][0]

        self.long_term_memory_collection = f"long_term_memory_{self.technical_name}"

        self.relative_agent_dir = f"agent_files/{self.technical_name}"
        self.agent_system_dir = os.path.abspath(self.relative_agent_dir)

        self.clean_chat = Chat("Clean Chat", self.system_name, self.agent_system_dir)
        self.chat = Chat(f"Chat with thinking process", self.system_name, self.agent_system_dir)
        self.complete_chat = Chat(f"Chat with thinking process and with entire prompt", self.system_name, self.agent_system_dir)
        self.code_manager = CodeManager(self.system_name)

        self.context_data = self.get_default_context_data()

        # -- Changing Variables --
        self.commands :list = []
        self.extraction_failure = False
        self._prompt :str = ""
        self._tmp_context_data_str :str = ""
        self.replying :bool = False # indicates if the agent is currently replying to a user
        self.acting_agent = default_agent

        self.max_iterations = 10

    def reset(self):
        self.long_term_memory_collection = f"long_term_memory_{self.technical_name}"

        self.relative_agent_dir = f"agent_files/{self.technical_name}"
        self.agent_system_dir = os.path.abspath(self.relative_agent_dir)

        self.clean_chat = Chat("Clean Chat", self.system_name, self.agent_system_dir)
        self.chat = Chat(f"Chat with thinking process", self.system_name, self.agent_system_dir)
        self.complete_chat = Chat(f"Chat with thinking process and with entire prompt", self.system_name,
                                  self.agent_system_dir)
        self.code_manager = CodeManager(self.system_name)

        self.context_data = self.get_default_context_data()

        # -- Changing Variables --
        self.commands: list = []
        self.extraction_failure = False
        self._prompt: str = ""
        self._tmp_context_data_str: str = ""
        self.replying: bool = False  # indicates if the agent is currently replying to a user
        self.acting_agent = self.default_agent

        self.max_iterations = 10

    def get_name(self):
        return self.system_name

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

    def use_tools(self, llm_response, agent):
        self.commands, extraction_failures = command_util.find_commands_in_string(llm_response)
        if len(extraction_failures) > 0:
            self.extraction_failure = True
        command_responses = execute_commands(self.commands, agent, self)

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
        agent = self.default_agent


        self.replying = True
        self._prompt = "# User Prompt\n" + self.clean_chat.get_last_messages_of_sender('User') + "\n"

        i = 0
        while self.clean_chat.get_last_sender() not in list(self.agent_dict.keys()) and i < self.max_iterations:
            print(f"Executing prompt {i + 1}")
            self.prompt(self._prompt, agent)
            i += 1

        if i > self.max_iterations:
            print(f"{RED}Warning: Maximum iterations reached. Stopping prompt agent.{RESET}")
            self.chat.add_message("Warning", "Maximum iterations reached. Stopping prompt agent.")
            self.complete_chat.add_message("Warning", "Maximum iterations reached. Stopping prompt agent.")
            self.clean_chat.add_message("System", "Maximum iterations reached. Stopping prompt agent.")

        self.replying = False
        pass

    def prompt(self, prompt, agent=None):
        if not agent:
            agent = self.default_agent
        self.acting_agent = agent

        response, prompt = agent.prompt(prompt)
        self.complete_chat.add_message("Prompt", prompt)
        self.chat.add_message(agent.get_name(), response)
        self.complete_chat.add_message(agent.get_name(), response)
        self.acting_agent = self.default_agent
        pass

    def handle_message(self, sender):
        if self.replying:
            pass
        elif sender not in list(self.agent_dict.keys()) and sender != "System":
            self.prompt_agent()
        pass

    def generate_context_data(self, agent, status_info = False):
        context_data_str = ""

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
                context_item_str += f"{self.get_context_dump(remaining_context, agent)}\n---\n"
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

    def get_context_dump(self, max_length :int = None, agent=None):
        if not agent:
            agent = self.default_agent

        context_xml_str = "Whenever possible, please use the following context to answer the User's query.\n"
        context_xml_str += "The context is sorted by relevance. Reference the context source you used in the user response.\n"

        n_results = int(config.max_context_tokens / config.RAG_CHUNK_SIZE * 10)
        context_dict = query_rag(f"{self._prompt}\n---\n{self._tmp_context_data_str}", agent.chroma_collection,
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
        util.save_text(f"{self.agent_system_dir}/{self.system_name}_memory", text)
        pass

    def get_short_memory(self):
        return util.load_text(f"{self.agent_system_dir}/{self.system_name}_memory")

    def get_long_memory(self):
        return rag.query_rag(f"{self._prompt}\n---\n{self._tmp_context_data_str}",
                             self.long_term_memory_collection, n_results=1)

    def get_available_document_filepaths_str(self):
        all_files = ""
        for root, dirs, files in os.walk(self.agent_system_dir):
            for file in files:
                path = os.path.relpath(os.path.join(root, file), self.agent_system_dir).replace("\\", "/")
                if path.startswith("uploads") or path.startswith("output"):
                    all_files += f"- {path}\n"
        if all_files == "":
            all_files = "*No files available*"
        return all_files

    def upload_file(self, upload_contents, filename):
        if upload_contents is not None:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                os.makedirs(os.path.join(self.agent_system_dir, "uploads"), exist_ok=True)
                file_path = f"uploads/{filename}"
                abs_file_path = os.path.abspath(os.path.join(self.agent_system_dir, file_path))
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
        self.code_manager.append(code)
        pass

    def get_code_names(self):
        if len(self.code_manager) == 0:
            return []
        return [code.get_name() for code in self.code_manager]

    def get_codes(self):
        return self.code_manager

    def get_code_obj(self, name: str):
        for code in self.code_manager:
            if code.get_name() == name:
                return code
        return None

    def get_code_api(self, name: str):
        for code in self.code_manager:
            if code.get_name() == name:
                return code.get_code_for_api()
        return None

    def get_frontend_code(self):
        for code in self.code_manager:
            if code.frontend:
                return code
        return None

    def get_code_script(self, name: str):
        for code in self.code_manager:
            if code.get_name() == name:
                return code.code
        return None

    # def get_reply(self):
    #     return self.clean_chat.get_last_messages_of_sender("Agent")

    def get_chroma_collection_of_acting_agent(self):
        return self.acting_agent.chroma_collection

    def get_long_term_memory_collection(self):
        return self.long_term_memory_collection

    def __str__(self):
        return self.system_name

    def __repr__(self):
        return self.system_name