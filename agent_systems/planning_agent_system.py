from agent_objs.plan import Plan
from agent_systems.base_agent_system import BaseAgentSystem
from agents.agent import Agent
from agents.planning_agent import PlanningAgent
from agents.summarizing_agent import SummarizingAgent
from tools import execute_next_step_command


#deprecated

class PlanningAgentSystem(BaseAgentSystem):
    def __init__(self):
        system_name="Planning Agent System"
        description = ("An AI agent system, where an Agent sets a plan beforehand. "
                       "That two further agents work together to complete. "
                       "One agent solves the users requests, "
                       "and another agent verifies the completeness of the first agent.\n")
        self.planning_agent = PlanningAgent(self)
        self.agent = Agent(self)
        self.agent.add_custom_command_instructions(
            name="## **Next Step**:\n",
            instructions=("You are executing your plan step-by-step.\n\n"
                          "To go to the next step, you must include the `<next_step />` command at the end of your response.\n"
                          "Only go to the next step if you are sure that the current step is complete.\n")
        )
        self.summarizing_agent = SummarizingAgent(self)
        agents = [self.planning_agent, self.agent, self.summarizing_agent]
        super().__init__(system_name, description, agents)
        self.plan = Plan(self)
        self.max_step_iterations = 5

    def get_plan(self):
        return self.plan

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
                f"{self._prompt}\n\n---\n\n{instructions}"
            self.prompt(entire_prompt, self.planning_agent)
            i += 1

        step_at_iteration = []
        while not self.plan.is_done():
            print(f"Executing prompt {i}")
            step = self.plan.get_current_step()
            step_at_iteration.append(step)
            if len(step_at_iteration) > self.max_step_iterations and step == step_at_iteration[-self.max_step_iterations]:
                print(f"Maximum number of iterations reached for Step.")
                self.chat.add_message("System", "Maximum number of iterations reached for Step.")
                self.plan.next_step()
                continue

            message = f"Working on step: {step} ({self.plan.get_current_step_index()+1}/{len(self.plan)})"
            self.clean_chat.add_message("System", message)
            self.chat.add_message("System", message)
            self.complete_chat.add_message("System", message)

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
                f"{self._prompt}\n\n---\n\n{instructions}"
            self.prompt(entire_prompt, self.agent)
            i += 1

        while self.clean_chat.get_last_sender() not in list(self.agent_dict.keys()):
            instructions = (
                "It seems like you forgot to reply to the User after finishing the query in the previous message. "
                "Please explain to the User what you have done.")
            entire_prompt = \
                f"{self.plan}\n\n---\n\n{instructions}"
            self.prompt(entire_prompt, self.summarizing_agent)
            i += 1
        self.replying = False
        self.send_socket_message(f"Prompted agent `{self.get_name()}`. Agent has replied.")
        pass