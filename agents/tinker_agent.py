from agents.base_agent import BaseAgent

class TinkerAgent(BaseAgent):
    """
    The Tinker Agent that has all tools but replying at its disposal.
    """

    def __init__(self, system):
        agent_name = "Tinker Agent"
        role = ("You are the Tinker Agent. You are given tasks by the User and must complete it.\n"
                "You are expected to use all the tools at your disposal to solve the users request."
                "You are exceptionally adept at writing code and creating dashboards.\n"
                "You can not directly interact with the user."
                "You are done when you have completed the task.\n"
                "Your handle in the chat is `Tinker Agent`.")
        chroma_collection = "python"
        super().__init__(system, agent_name, role, chroma_collection)
        self.command_instructions["response"]["active"] = False  # Forbid the use of the response command