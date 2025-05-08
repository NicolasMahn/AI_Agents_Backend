from agents.agent import Agent
from agent_systems.base_agent_system import BaseAgentSystem

class SimpleAgentSystem(BaseAgentSystem):
    def __init__(self):
        system_name = "Simple Agent System"
        description = ("An AI agent system, where a single agent that has the ability to use tools such as writing "
                       "code, and creating dashboards.\n")
        self.agent = Agent(self)
        agents=[self.agent]
        super().__init__(system_name, description, agents)