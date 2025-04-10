import re

from overrides import override

from agent_objs.plan import Plan
from agents import Agent


class PlanningAgent(Agent):
    def __init__(self, name="Planning Agent",
                 role="You are a planning agent that generates a plan with a flexible number of steps and then executes each step."):
        super().__init__(name, role)

        self.plan = Plan(self)

        self.add_custom_command_instructions(
            name="planning",
            instructions=("## **Planning**\n"
                "When faced with a complex task, break it down into a series of logical, manageable steps. This structured approach will help you address the problem thoroughly and systematically.\n\n"
                "### **Plan Structure**\n"
                "Generate your plan using the following XML-like format:\n\n"
                "```xml\n"
                "<plan>\n"
                "   <step>Define the problem</step>\n"
                "   <step>Gather relevant information</step>\n"
                "   <step>Analyze the information</step>\n"
                "   <step>Develop a solution</step>\n"
                "   <step>Review and finalize your answer</step>\n"
                "</plan>\n"
                "```\n\n"
                "### **Execution Process**\n"
                "After generating your plan, work on each step individually. Focus on one step at a time and when you complete a step, signal your readiness to proceed by issuing the `<next_step />` command.\n"
                "It is impossible to code, query or check a document and going to the next step. As all these actions are pended on results and being successful.\n"
                "### **Dynamic Adjustments**\n"
                "If you realize that additional steps are needed or adjustments are required, update your plan accordingly by adding, modifying, or removing steps. Ensure that your plan always reflects your current approach.\n\n"
                "### **Completion Confirmation**\n"
                "Once all steps have been executed, provide a final summary that outlines your process and delivers the comprehensive answer to the user's query.\n\n"
                "### **Handling Uncertainties**\n"
                "If any step is unclear or you require further clarification, note these uncertainties during execution and adjust your plan as needed before proceeding.\n\n")
        )

    @override
    def handle_message(self, sender):
        if self.replying:
            pass
        elif sender != self.name and sender != "System":
            self.replying = True
            self.prompt_agent(
                f"The User has sent a message: {self.clean_chat.get_last_message_of_sender('User')}\n\n"
                f"Your task is to create a detailed, step-by-step plan to address the user's request. "
                f"Generate this plan using the `<plan>` XML structure as defined in your instructions.\n\n"
                f"When creating your plan, please consider the typical workflow for Data Science and exploratory coding tasks, breaking the problem down logically:\n"
                f"1.  **Understand & Define:** What is the core objective or question? Clearly define the problem based on the user's message. What are the desired inputs and outputs?\n"
                f"2.  **Information & Data Strategy:** What information or data is needed? Consider:\n"
                f"    * Internal Data: Do I need to query existing documents (`<document>`) or long-term memory (`<query>`)?\n"
                f"    * Data Exploration (EDA): Include a step to explore the data's structure, quality, and patterns, likely using `<code>`.\n"
                f"    * Data Preparation: Plan for any necessary cleaning, transformation, or feature engineering using `<code>`.\n"
                f"3.  **Methodology & Implementation:** Outline the core analytical approach or coding steps.\n"
                f"    * What algorithms, statistical methods, or coding logic will be used? (Plan `<code>` usage, including potential libraries/dependencies).\n"
                f"    * Break down complex coding tasks into smaller, manageable sub-steps within the plan.\n"
                f"4.  **Validation & Review:** How will the results be validated or the code tested? Plan for evaluating model performance or verifying code correctness.\n"
                f"5.  **Synthesis & Final Response:** Include a final step to consolidate the findings, draw conclusions, and prepare the `<response>` for the user.\n\n"
                f"Remember:\n"
                f"* Be specific in each step.\n"
                f"* Anticipate potential iterations – findings in one step might require revisiting an earlier one (e.g., EDA reveals data issues needing more cleaning).\n"
                f"* Think about the tools (`<query>`, `<document>`, `<code>`) you'll likely need for each step.\n\n"
                f"Please provide *only* the `<plan>...</plan>` structure as your response now. You will execute each step later using `<next_step />`."
            )
            while self.clean_chat.get_last_sender() != self.name:
                self.prompt_agent("It seems like the previous agent forgot to reply the User after finishing the query. "
                                  "Please explain to the User what you have done.")
        self.replying = False

    @override
    def prompt_agent(self, prompt):
        super().prompt_agent(prompt)

        if len(self.plan) > 0:
            step = self.plan[0]
            execution_prompt = (
                f"You are executing your plan step-by-step.\n\n"
                f"Your current step is:\n"
                f"---\n"
                f"{step}\n"  # The actual text of the step
                f"---\n\n"
                f"Please focus on completing *only this step* now.\n"
                f"After performing the action(s) for this step:\n"
                f"1.  **If this step is complete AND you DID NOT use a command that requires waiting** (like `<document>`, or `<code>` which return results later), you MUST include the `<next_step />` command at the end of your response to signal readiness for the next step.\n"
                f"2.  **If you use a command that requires waiting** (`<search>`, `<document>`, `<code>`), DO NOT include `<next_step />`. You will address the results and the plan in the next turn.\n"
                f"3.  **If this is the FINAL step** of your plan (e.g., summarizing results, formulating the final answer), then instead of `<next_step />`, generate the complete `<response>` for the user.\n\n"
                f"Proceed with executing the current step."
            )
            self.prompt_agent(execution_prompt)
        pass