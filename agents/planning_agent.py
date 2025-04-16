from agent_objs.plan import Plan
from agents import Agent


class PlanningAgent(Agent):
    def __init__(self, name="Planning Agent",
                 role="You are a planning agent that generates a plan with a flexible number of steps and then executes each step.\n"
                      "You are given tasks by the User and converse with him in a chat. \n"
                      "Your handle in the chat is `Planning Agent`. "
                      "The User can only see information in the `<response>` section of the chat (explained below..)\n",
                 chroma_collection = "python"
                 ):
        super().__init__(name, role, chroma_collection)

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

    def prompt_agent(self):
        self.replying = True
        self._prompt = self.clean_chat.get_last_messages_of_sender('User')

        i = 1
        while "plan" not in [command.tag for command in self.commands]:
            print(f"Developing Plan ({i})")
            instructions = (
                f"# **Instructions**\n"
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
                f"* Think about the tools (`<query>`, `<document>`, `<code>`) you'll likely need for each step.\n"
                f"* You can also do some research on the topic an to the plan in a later iteration\n"
            )

            entire_prompt = \
                f"{self._prompt}\n---\n{self.generate_context_data()}\n---\n{self.get_instruction_str()}\n---\n{instructions}"
            self.prompt(entire_prompt)
            i += 1

        while not self.plan.is_done():
            print(f"Executing prompt {i}")
            step = self.plan.get_current_step()
            message = f"Working on step: {step} ({self.plan.get_current_step_index()}/{len(self.plan)})"
            self.clean_chat.add_message(message, sender="System")
            self.chat.add_message(message, sender="System")
            self.complete_chat.add_message(message, sender="System")

            self._prompt = (
                f"You are executing your plan step-by-step.\n\n"
                f"Your current step is:\n"
                f"{step}\n"  # The actual text of the step
            )
            instructions = (
                f"Please focus on completing *only this step* now.\n"
                f"After performing the action(s) for this step:\n"
                f"1.  **If this step is complete AND you DID NOT use a command that requires waiting** (like `<document>`, or `<code>` which return results later), you MUST include the `<next_step />` command at the end of your response to signal readiness for the next step.\n"
                f"2.  **If you use a command that requires waiting** (`<search>`, `<document>`, `<code>`), DO NOT include `<next_step />`. You will address the results and the plan in the next turn.\n"
                f"3.  **If this is the FINAL step** of your plan (e.g., summarizing results, formulating the final answer), then instead of `<next_step />`, generate the complete `<response>` for the user.\n\n"
                f"Proceed with executing the current step."
            )
            entire_prompt = \
                f"{self._prompt}\n---\n{self.generate_context_data()}\n---\n{self.get_instruction_str()}\n---\n{instructions}"
            self.prompt(entire_prompt)
            i += 1

        while self.clean_chat.get_last_sender() != self.name:
            instructions = (
                "It seems like you forgot to reply to the User after finishing the query in the previous message. "
                "Please explain to the User what you have done.")
            entire_prompt = \
                f"{self.plan}\n---\n{self.generate_context_data()}\n---\n{self.get_instruction_str()}\n---\n{instructions}"
            self.prompt(entire_prompt)
            i += 1
        self.replying = False
        pass