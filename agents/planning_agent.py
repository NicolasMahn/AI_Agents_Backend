import re

from agents import Agent


class PlanningAgent(Agent):
    def __init__(self, name="Planning Agent",
                 role="You are a planning agent that generates a plan with a flexible number of steps and then executes each step."):
        super().__init__(name, role)
        # This list will be populated dynamically from the agent's plan
        self.plan_steps = []

    def handle_message(self, sender):
        if self.replying:
            pass
        else:
            self.replying = True

        if sender != self.name and sender != "System":
            while self.clean_chat.get_last_sender() != self.name:
                self.prompt_agent(f"The User has sent a message: {self.clean_chat.get_last_message_of_sender('User')}\n"
                                  f"Please create a plan on how to iteratively respond to this message.")
        self.replying = False
