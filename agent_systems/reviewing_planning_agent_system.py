
from agent_objs.plan import Plan
from agent_systems.base_agent_system import BaseAgentSystem
from agents.critic_agent import CriticAgent
from agents.planning_agent import PlanningAgent
from agents.summarizing_agent import SummarizingAgent
from agents.tinker_agent import TinkerAgent


class ReviewingPlanningAgentSystem(BaseAgentSystem):
    def __init__(self, system_name=None, description=None, model_for_minor_agents=None):
        if system_name is None:
            system_name="Reviewing Agent System"
        if description is None:
            description = ("An AI agent system, where an Agent sets a plan beforehand. "
                           "That two further agents work together to complete. "
                           "One agent solves the users requests, "
                           "and another agent verifies the completeness of the first agent.\n")
        self.planning_agent = PlanningAgent(self)
        self.tinker_agent = TinkerAgent(self)
        self.critic_agent = CriticAgent(self, model=model_for_minor_agents)
        self.summarizing_agent = SummarizingAgent(self, model=model_for_minor_agents)
        agents = [self.planning_agent, self.tinker_agent, self.critic_agent, self.summarizing_agent]
        super().__init__(system_name, description, agents)

        self.plan = Plan(self)
        self.max_planning_iterations = 5
        self.max_iterations = 5

    def prompt_agent(self):
        self.replying = True
        self._prompt = self.clean_chat.get_last_messages_of_sender('User')

        i = 1

        while i < self.max_planning_iterations:
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

            if not self.extraction_failure and self.plan.is_set():
                instructions_validate_plan = (
                    f"**Your Task:** Review the plan you just generated to address the user's request (`{self._prompt}`).\n\n"
                    f"**Generated Plan:**\n```xml\n{self.plan}\n```\n\n"
                    f"**Assessment Criteria:**\n"
                    f"1.  **Completeness:** Does the plan address all key aspects of the user's request?\n"
                    f"2.  **Logical Flow:** Are the steps in a sensible order? Do they build on each other?\n"
                    f"3.  **Feasibility:** Are the steps achievable with the available tools (`<code>`, `<query>`, `<document>`, etc.)?\n"
                    f"4.  **Specificity:** Are the steps detailed enough to be actionable?\n"
                    f"5.  **Includes Key Phases:** Does it cover understanding, data handling, methodology, validation, and synthesis?\n\n"
                    f"**Based on this review, is the plan satisfactory?**\n"
                    f"* **If YES:** Explain briefly why it meets the criteria. **End your entire output *only* with the tag `<Yes>`.**\n"
                    f"* **If NO:** Explain the specific weaknesses or missing elements. Suggest concrete improvements or which steps need revision. **End your entire output *only* with the tag `<No>`.**"
                )
                self.prompt(instructions_validate_plan, self.critic_agent)

                if self.critic_agent.requirements_met:
                    break

        instructions_summarize_plan = (
            f"**Your Task:** Summarize the execution plan for the user.\n\n"
            f"**Approved Plan:**\n```xml\n{self.plan}\n```\n\n"
            f"Explain the main steps of this plan to the user in a clear and concise way using the `<response><![CDATA[...]]></response>` tag.\n\n"
            f"Focus on the overall approach and what the user can expect."
        )

        entire_prompt = \
            f"{self._prompt}\n\n---\n\n{instructions_summarize_plan}"
        self.prompt(entire_prompt, self.summarizing_agent)


        while not self.plan.is_done():
            step = self.plan.get_current_step()
            message = f"Working on step: {step} ({self.plan.get_current_step_index()+1}/{len(self.plan)})"
            self.clean_chat.add_message("System", message)
            self.chat.add_message("System", message)
            self.complete_chat.add_message("System", message)

            starting_i = i
            while (i - starting_i) < self.max_iterations:
                print(f"Executing prompt {i}  --- On Step: ({self.plan.get_current_step_index()}/{len(self.plan)})")
                self._prompt = (
                    f"You are executing your plan step-by-step.\n\n"
                    f"Your current step is:\n"
                    f"{step}\n"  # The actual text of the step
                )
                instructions_do_step = (
                    f"**Your Task:** Execute the following step from your approved plan.\n\n"
                    f"**Current Step Details:**\n---\n{step}\n---\n\n"
                    f"Focus *only* on completing the actions described in this step.\n"
                    f"Use the necessary command tags (`<code>`, `<query>`, `<document>`) as appropriate for this step.\n"
                    f"Perform the action(s) now."
                )
                entire_prompt = \
                    f"{self._prompt}\n\n---\n\n{instructions_do_step}"
                self.prompt(entire_prompt, self.tinker_agent)
                i += 1

                if not self.extraction_failure:
                    instructions_validate_step = (
                        f"**Your Task:** Assess if the current plan step has been successfully completed.\n\n"
                        f"**Step Description:**\n---\n{step}\n---\n"
                        f"**Results of Last Action:**\n---\n{step}\n---\n\n"  # Context from step 4 execution
                        f"**Assessment:** Based on the results, is the objective of *this specific step* fully achieved?\n"
                        f"* **If YES:** Explain briefly how the results satisfy the step's objective. **End your entire output *only* with the tag `<Yes>`.**\n"
                        f"* **If NO:** Explain what is still missing or needs to be redone for *this step*. **End your entire output *only* with the tag `<No>`.**"
                    )

                    entire_prompt = \
                        f"{self._prompt}\n\n---\n\n{instructions_validate_step}"
                    if self.prompt(entire_prompt, self.critic_agent):
                        self.plan.next_step()
                        break

        instructions_final_summary = (
            f"**Your Task:** All planned steps have been executed successfully. Provide the complete and final response to the user, synthesizing the results and summarizing the process.\n\n"
            f"**Review Context:** Carefully examine the Original User Request, the Executed Plan, and the full Conversation History including all results from the executed steps.\n"
            f"**Original User Request:**\n---\n{self.clean_chat.get_last_messages_of_sender('User')}\n---\n"
            f"**Executed Plan Overview:**\n---\n{self.plan}\n---\n"

            f"Generate the final, comprehensive response for the user within `<response><![CDATA[...]]></response>`. Your response **must**:\n"
            "1.  Directly address the user's **original request**.\n"
            "2.  Clearly state the **final answer**, conclusion, or outcome based on the results obtained.\n"
            "3.  Briefly summarize the **key steps** that were executed according to the plan to reach the conclusion.\n"
            "4.  Interpret any crucial **results or outputs** (like plots or final calculations from `<code>` blocks) that the user saw during the process and that support your final answer.\n"
            "5.  Be **self-contained and understandable** from the user's perspective (remembering they saw their prompts, the initial plan summary, and `<code>` outputs).\n\n"
            f"This is the concluding response for the user's request. Ensure it is complete and accurate. You may use `<long_memory>` if appropriate."
        )
        self.prompt(instructions_final_summary, self.summarizing_agent)

        self.plan = Plan(self)

        self.replying = False
        pass

class ReviewingPlanningAgentSystemWithLesserCritic(ReviewingPlanningAgentSystem):
    def __init__(self):
        system_name = "Reviewing Planning Agent System with Lesser Critic"
        description = ("An AI agent system, where an Agent sets a plan beforehand. "
                       "That two further agents work together to complete. "
                       "One agent solves the users requests, "
                       "and another agent verifies the completeness of the first agent.\n"
                       "The critic agent is a smaller model (Llama 3.3 70B), which is less expensive to run.\n")
        super().__init__(system_name, description, model_for_minor_agents="llama3.3-70b-instruct-fp8")