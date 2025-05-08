from agents.base_agent import BaseAgent
from llm_functions import basic_prompt
from util.colors import RED, RESET


class CriticAgent(BaseAgent):
    """
    The Default Agent that has all tools at its disposal.
    """

    def __init__(self, system, model=None):
        agent_name = "Critic"
        role = ("You are a Critic. Another agent is given tasks by the User and you need to evaluate the responses on their completeness. \n"
                "Your handle in the chat is `Critic`.\n"
                "You should finish your evaluation with either <Yes> or <No>. Depending on the performance of the other agent.\n")
        super().__init__(system, agent_name, role, model=model, internal_agent=False)

        self.requirements_met = False

    def prompt(self, prompt):
        response, prompt = super().prompt(prompt)
        if "<Yes>" in response or "<yes>" in response:
            self.requirements_met = True
        else:
            self.requirements_met = False
        return response, prompt

    def get_full_prompt(self, prompt):
        entire_prompt = \
            (f"{prompt}\n\n---\n\n{self.system.generate_context_data(self, status_info=True)}\n\n"
             f"---\n\n"
             f"**Here are the Instructions for reference, but they can not be used in this prompt:**\n{self.get_instruction_str(ignore_active=True)}\n\n")
        return entire_prompt
