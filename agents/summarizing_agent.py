from agents.base_agent import BaseAgent

class SummarizingAgent(BaseAgent):

    def __init__(self, system, model=None):
        agent_name = "Summarizing Agent"
        role = ("You are the AI Agent. A task has been given by the user, and has been completed. \n"
                "You are exceptionally adept at summarizing and presenting the final result.\n"
                "Your handle in the chat is `Summarizing Agent`.\n"
                "The User can only see information in the `<response>` section of the chat (explained below).\n")
        super().__init__(system, agent_name, role, model=model)
        self.command_instructions["code"]["active"] = False
        self.command_instructions["query"]["active"] = False
        self.command_instructions["document"]["active"] = False

    def get_full_prompt(self, prompt):
        """
        Generates the full prompt for the agent.
        :param prompt: The prompt to be sent to the agent.
        :return: The full prompt for the agent.
        """
        entire_prompt = \
            f"{prompt}\n\n---\n\n{self.get_instruction_str()}\n\n---\n\n{self.system.generate_context_data(self, status_info=True)}"
        return entire_prompt



