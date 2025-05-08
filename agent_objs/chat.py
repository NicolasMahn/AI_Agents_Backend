import os
import sys
from typing_extensions import override

import config
import util
from llm_functions import count_context_length
from util.colors import PINK, RESET

_message_callback = None

def register_message_callback(callback_func):
    """Registers a function to be called when a message needs to be sent."""
    global _message_callback
    _message_callback = callback_func

def _notify(message):
    """Internal helper to safely call the registered callback."""
    if _message_callback:
        try:
            _message_callback(message, "chat_update")
        except Exception as e:
            print(f"Error in message callback: {e}")
    else:
        print(f"Message notification attempted, but no callback registered: {message}")


class Chat(list):

    def __init__(self, chat_name: str = None, agent_system_name:str = "Unknown", chat_dir: str = "projects"):
        self.chat_name = chat_name
        self.agent_system_name = agent_system_name
        self.chat_file = os.path.join(chat_dir, f"{chat_name}.json")
        super().__init__(self.restore_chat_history())
        util.save_json(self.chat_file, self)
        pass

    def __str__(self):
        return str(self.get_chat_name())

    def restore_chat_history(self):
        try:
            chat_history = util.load_json(self.chat_file)
        except:
            chat_history = []
        return chat_history

    def clear(self):
        util.delete_file(self.chat_file)
        super().clear()
        pass

    def append_message(self, sender, text):
        self.add_message(sender, text)

    def add_message(self, sender, text):
        print(f"Adding message to `{self.chat_name}` by `{sender}`")
        self.append({"sender": sender, "text": text})
        _notify(f"Adding message to `{self.chat_name}` of `{self.agent_system_name}`")


    def append(self, item):
        super().append(item)
        util.save_json(self.chat_file, self)

    def find(self, value):
        return [i for i, item in enumerate(self) if value in item]

    def get_chat_name(self):
        return self.chat_name

    def get_chat_file(self):
        return self.chat_file

    def get_last_message_of_sender(self, sender: str):
        for message in reversed(self):
            if message['sender'] == sender:
                return message
        return None

    def get_last_messages_of_sender(self, sender: str):
        if self.chat_name != "Clean Chat":
            print(f"{PINK}Warning: This method is only intended, and will likely only work, for the Clean Chat! {RESET}")

        messages = []
        for message in reversed(self):
            if message['sender'] == "System":
                continue
            elif message['sender'] == sender:
                if count_context_length(message['text'] + str(messages)) < config.max_prompt_tokens:
                    messages.append(message)
            else:
                break
        if len(messages) == 1:
            return messages[0]['text']
        else:
            messages.reverse()
            messages = [message['text'] for message in messages]
            message_str = ""
            for message in messages:
                message_str += f"{message}\n"
            return message_str

    def get_last_n_tokens_in_xml_str(self, n: int):
        xml_str = ""
        for i in range(n):
            try:
                last_message = self[-(i+1)]
            except IndexError:
                break
            xml_str_message = f"<message sender='{last_message['sender']}'>\n<![CDATA[\n{last_message['text']}\n]]>\n</message>"
            tmp_xml_str = f"{xml_str_message}\n{xml_str}"
            if count_context_length(tmp_xml_str) > (n-100):
                omitted_messages = f"<message sender='System'>Omitted {len(self) - i} messages</message>"
                xml_str = f"{omitted_messages}\n{xml_str}"
                break
            else:
                xml_str = tmp_xml_str
        xml_str = f'<chat>\n{xml_str}\n</chat>'
        # print(f"XML string: {xml_str}")
        return xml_str

    def get_last_sender(self):
        try:
            return self[-1]['sender']
        except IndexError:
            return None

    @override
    def extend(self, iterable):
        raise NotImplementedError("The extend method is disabled for Chat class")

    @override
    def count(self, value):
        raise NotImplementedError("The count method is disabled for Chat class")

    @override
    def remove(self, value):
        raise NotImplementedError("The remove method is disabled for Chat class")

    @override
    def insert(self, index, object):
        raise NotImplementedError("The insert method is disabled for Chat class")

    @override
    def reverse(self):
        raise NotImplementedError("The reverse method is disabled for Chat class")

    @override
    def sort(self, key=None, reverse=False):
        raise NotImplementedError("The sort method is disabled for Chat class")

    @override
    def index(self, value, start=0, stop=sys.maxsize):
        raise NotImplementedError("The index method is disabled for Chat class")


class ChatManager:
    def __init__(self, chats: list = None):
        self.chats = []
        self.chats = self.extend(chats)
        pass

    def extend(self, iterable):
        if iterable is None:
            return self.chats
        for chat in iterable:
            self.append(chat)
        return self.chats

    def append(self, new_chat):
        for chat in self.chats:
            if chat.get_chat_name() == new_chat.get_chat_name():
                raise ValueError("Chat with same name already exists")
        self.chats.append(new_chat)
        pass

    def get_chats_with_agent(self, agent_name: str):
        return [chat for chat in self.chats if chat.is_participating_agent(agent_name)]

    def get(self, chat_name: str):
        for chat in self.chats:
            if chat.get_chat_name() == chat_name:
                return chat
        return None

    def __getitem__(self, item):
        for chat in self.chats:
            if chat.get_chat_name() == item:
                return chat

    def __iter__(self):
        return iter(self.chats)

    def __len__(self):
        return len(self.chats)

    def __str__(self):
        return str([chat.get_chat_name() for chat in self.chats])

    def __del__(self):
        for chat in self.chats:
            chat.clear()
        pass

    def __contains__(self, item):
        return item in [chat.get_chat_name() for chat in self.chats]

    def keys(self):
        return [chat.get_chat_name() for chat in self.chats]

    def values(self):
        return self.chats