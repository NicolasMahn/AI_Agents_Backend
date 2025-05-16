from agents.base_agent import BaseAgent

class PlanningAgent(BaseAgent):

    def __init__(self, system):
        agent_name = "Planning Agent"
        role = ("You are a planning agent that generates a plan with a flexible number of steps and then executes each step.\n"
                "You are given tasks by the User and converse with him in a chat. \n"
                "Your handle in the chat is `Planning Agent`. \n")
        chroma_collection = "python"
        super().__init__(system, agent_name, role, chroma_collection)
        self.command_instructions["code"]["active"] = False
        self.add_custom_command_instructions(
            name="plan",
            instructions=("## **Planning**\n"
                "When faced with a complex task, break it down into a series of logical, manageable steps. This structured approach will help you address the problem thoroughly and systematically.\n\n"
                "### **Plan Structure**\n"
                "Generate your plan using the following XML-like format:\n\n"
                "```xml\n"
                "<plan>\n"
                "   <step>Clean the data</step>\n"
                "   <step>Make dashboard from cleaned data</step>\n"
                "   <step>Test the dashboard</step>\n"
                "</plan>\n"
                "```\n\n"
                "Ensure that the plan is not excessively long or too short. Aim for a balance that allows for thoroughness without overwhelming detail."
                "The fewer steps the better, as this reduces the costs. But as many steps as necessary to complete the users request\n\n")
        )


