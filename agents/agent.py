from agents.base_agent import BaseAgent

class Agent(BaseAgent):
    """
    The Default Agent that has all tools at its disposal.
    """

    def __init__(self, system):
        agent_name = "Agent"
        role = ("You are the AI Agent. You are given tasks by the User and converse with him in a chat. \n"
                "You are exceptionally adept at writing code and creating dashboards.\n"
                "Your handle in the chat is `Agent`.\n"
                "The User can only see information in the `<response>` section of the chat (explained below).\n")
        chroma_collection = "python"
        super().__init__(system, agent_name, role, chroma_collection)



