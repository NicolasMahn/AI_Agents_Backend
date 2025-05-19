import base64
import os

import numpy as np
import config

from llm_functions import count_context_length, basic_prompt
from tools.document_command import execute_document_command
from agent_objs.chat import Chat
from util import delete_directory_with_content
from util.colors import ORANGE, RESET, RED, PINK

def register_message_callback(callback_func):
    """Registers a function to be called when a message needs to be sent."""
    global _message_callback
    _message_callback = callback_func

def _notify(message):
    """Internal helper to safely call the registered callback."""
    if _message_callback:
        try:
            _message_callback(message, "agent_update")
        except Exception as e:
            print(f"Error in message callback: {e}")
    else:
        print(f"Message notification attempted, but no callback registered: {message}")

class LLMWrapperSystem:
    def __init__(self):
        self.system_name = "LLM Wrapper"
        self.technical_name = self.system_name.lower().replace(" ", "_")
        self.description = "This is an LLM wrapper to compare the Agents to (while implementing the absolute minimum of features). \n",

        self.relative_agent_dir = f"agent_files/{self.technical_name}"
        self.agent_system_dir = os.path.abspath(self.relative_agent_dir)

        self.chat = Chat("Clean Chat", self.system_name, self.agent_system_dir)
        self.code_list = []

        self.context_data = self.get_default_context_data()

        # -- Changing Variables --
        self.replying :bool = False # indicates if the agent is currently replying to a user

        pass

    def reset(self):
        self.chat = Chat("Clean Chat", self.system_name, self.agent_system_dir)
        self.code_list = []
        self.context_data = self.get_default_context_data()
        delete_directory_with_content(self.relative_agent_dir)
        os.makedirs(self.relative_agent_dir, exist_ok=True)
        pass

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

    def generate_context_data(self, status_info = False):
        context_data_str = f""

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

            if isinstance(value, Chat):
                context_item_str = f"# **{name}**:\n"
                context_item_str += f"Chat with {description_}\n"
                chat_content = value.get_last_n_tokens_in_xml_str(config.max_chat_tokens)
                context_item_str += f"{chat_content}\n---\n"
            else:
                context_item_str = f"# **{name}**:\n"
                context_item_str += f"{value}\n---\n"
                context_item_str += "\n"

                context_data_str += context_item_str

            context_item["last_interaction"] += 1

            if context_item["last_interaction"] > 10 and not context_item["always_display"]:
                self.context_data.pop(name)
        return context_data_str


    def prompt_agent(self):
        self.replying = True
        entire_prompt = \
            f"# User Prompt\n{self.chat.get_last_messages_of_sender('User')}\n---\n{self.generate_context_data()}"
        self.prompt(entire_prompt)

        self.replying = False
        _notify(f"Prompting agent `{self.get_name()}` is done with prompt")
        pass

    def prompt(self, prompt):
        try:
            response = basic_prompt(prompt)
        except Exception as e:
            print(f"{RED}Error in prompt:{RESET} {e} ")
            response = "Error when attempting to prompt the LLM. Please try again."
        self.chat.add_message("Agent", response)
        return None

    def handle_message(self, sender):
        if self.replying:
            pass
        elif sender != "Agent" and sender != "System":
            self.prompt_agent()
        pass

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
        return [str(self.chat)]

    def get_chat(self, _):
        return self.chat

    def add_message(self, sender: str, text: str,
                    add_to_clean_chat = False,
                    add_to_chat = True,
                    add_to_complete_chat = False):

        num_tokens = count_context_length(text)
        if num_tokens > config.max_prompt_tokens:
            sender = "System"
            text = f"Message too long ({num_tokens} tokens). Please shorten your message."

        if add_to_chat or add_to_complete_chat or add_to_clean_chat:
            self.chat.add_message(sender, text)
        self.handle_message(sender)
        pass

    def get_reply(self):
        return self.chat.get_last_messages_of_sender("Agent")

    def get_code_names(self):
        return []

    def __str__(self):
        return self.system_name

    def __repr__(self):
        return self.system_name