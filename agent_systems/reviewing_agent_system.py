from agent_systems.base_agent_system import BaseAgentSystem
from agents.critic_agent import CriticAgent
from agents.summarizing_agent import SummarizingAgent
from agents.tinker_agent import TinkerAgent
from util.colors import RED, RESET


class ReviewingAgentSystem(BaseAgentSystem):
    def __init__(self, system_name=None, description=None, model_for_minor_agents=None):

        if system_name is None:
            system_name = "Reviewing Agent System"
        if description is None:
            description = ("An AI agent system, where two agents work together to code and create dashboards. "
                           "One agent solves the users requests, and another agent verifies the completeness of the first agent.\n")
        self.tinker_agent = TinkerAgent(self)
        self.critic_agent = CriticAgent(self, model=model_for_minor_agents)
        self.summarizing_agent = SummarizingAgent(self, model=model_for_minor_agents)
        self.max_summarizing_iterations = 2
        agents=[self.tinker_agent, self.critic_agent, self.summarizing_agent]
        super().__init__(system_name, description, agents)

    def prompt_agent(self):
        self.replying = True
        self._prompt = self.clean_chat.get_last_messages_of_sender('User')

        i = 0
        while i < self.max_iterations:
            print(f"Executing prompt {i + 1}")
            instructions = (
                 "**Instructions:**\n"
                 "1. **Understand:** Read the User's request, the history and the current Context carefully.\n"
                 "2. **Plan:** Explain your plan step-by-step. Identify which commands (`<code>`, `<query>`, `<document>`, etc.) are (now) required.\n"
                 "3. **Execute Action:** Output the command tag for the *single, most important step* identified in your plan (e.g., `<query>...</query>` or `<code>...</code>).\n"
                 "    * If you determined clarification is needed (Step 1), do not output a command tag. Explain why you are blocked.\n"
                 "4. **Memory:** Consider if `<long_memory>` is appropriate for any findings or plans.\n\n"
            )

            entire_prompt = \
                f"{self._prompt}\n\n---\n\n{instructions}"
            self.prompt(entire_prompt, self.tinker_agent)

            if not self.extraction_failure:
                instructions = (
                    f"**Assess Completion:** Carefully review the Original User Request, the conversation history, and especially the **results from the last action**. \n"
                    "Do you **now** have all the information needed to provide the *complete and final answer* to the user? Explain your reasoning in detail.\n\n"

                    "* **If YES:** **CRITICAL CHECK:** Before confirming, perform this internal check:\n"
                    f"   1. Re-read the **Original User Request** precisely.\n"
                    "    2. Verify point-by-point: Does the available information (Context and Last Action Results) definitively and accurately answer **every single aspect** of that request?\n"
                    "    3. Consider completeness: Are there any parts of the request left unaddressed, any ambiguities remaining, or potential inaccuracies in the gathered information?\n"
                    "    4. Where there any extraction failures in the last action? If so, where they resolved?\n"
                    "    5. Code Tool Check (If Applicable): If the original request involved writing, running, modifying, or explaining code, confirm that the `<code>` command was actually used appropriately during the previous steps and that its output (or the code generated) is present and directly addresses the code-related aspect of the request.\n"
                    "    6. If the code produced a dashboard: Did the dashboard load and was a description produces of the dashboard  where all answered answered in the dashboard. Does the dashboard\n"
                    "  **Only if you are *absolutely certain* after completing all checks above that the task is fully resolved:**\n"  # Emphasized completing all checks
                    "    * Justify *why* the task is complete, explicitly referencing how the gathered information satisfies each user requirement (including the code aspect, if applicable).\n"
                    "    * **End your entire output *only* with the tag `<Yes>`.** Do not include any other tags or text after it.\n"
                    "  **(If this check reveals any gaps or confirms the `<code>` tool was needed but not used, proceed as if you initially answered NO below).**\n"  # Updated fallback condition

                    "* **If NO:** Justify *in detail* why you cannot finish yet by addressing the following points in your reasoning:\n"
                    "    1. What specific information is still missing or needs refinement?\n"
                    "    2. Why were the results from the previous action(s) insufficient?\n"
                    "    3. What is the *specific next action* you plan to take?\n"
                    "    4. **Which command tag (e.g., `<code>`, `<query>`, `<document>`, `<clarify>`) do you anticipate using for this next action?**\n"
                    "    5. Explain how this next action and chosen tool will help achieve the final answer.\n"
                    "  **After providing this detailed justification, end your entire output *only* with the tag `<No>`.** Do not include any other tags or text after it.\n"
                )


                self.prompt(instructions, self.critic_agent)

                if self.critic_agent.requirements_met:
                    break

            i += 1

            if i == self.max_iterations:
                print(f"{RED}Warning: Maximum iterations reached. Stopping prompt agent.{RESET}")
                self.chat.add_message("Warning", "Maximum iterations reached. Summarizing, current state of completeness.")
                self.complete_chat.add_message("Warning", "Maximum iterations reached. Summarizing, current state of completeness.")
                self.clean_chat.add_message("System", "Maximum iterations reached. Summarizing, current state of completeness.")
                break

        while self.clean_chat.get_last_sender() != self.summarizing_agent.get_name() and i < self.max_iterations+self.max_summarizing_iterations:
            print(f"Executing final prompt ({i + 1})")

            instructions = (
                "The action/assessment phase is complete. You **must** now provide the final, comprehensive response to the user using the `<response>` tag.\n\n"
                "**Construct the Final Response:**\n"
                "Review the Original User Request and the **full Conversation History & Results**. Formulate your response within `<response><![CDATA[...]]></response>` tags.\n\n"
                "**Ensure your response includes:**\n"
                "1.  Clear reference to the user's original query.\n"
                "2.  The direct answer, solution, or outcome.\n"
                "3.  A brief, user-friendly summary of the key steps or actions you took (e.g., searches performed, data analyzed via code).\n"
                "4.  Interpretation of any relevant code output the user saw during the process.\n"
                "5.  Context to ensure the response makes sense to the user (who only saw their prompts, your `<response>`, and `<code>` output).\n\n"
                "You may also use `<long_memory>` if appropriate."
            )

            entire_prompt = \
                f"{self._prompt}\n\n---\n\n{instructions}"

            self.prompt(entire_prompt, self.summarizing_agent, print_thinking=i >= self.max_iterations+self.max_summarizing_iterations)
            i += 1

        self.replying = False
        self.send_socket_message(f"Prompted agent `{self.get_name()}`. Agent has replied.")
        pass


class ReviewingAgentSystemWithLesserCritic(ReviewingAgentSystem):
    def __init__(self):
        system_name = "Reviewing Agent System with Lesser Critic"
        description = ("An AI agent system, where two agents work together to code and create dashboards. "
                       "One agent solves the users requests, and another agent verifies the completeness of the first agent.\n"
                       "The critic agent is a smaller model (Llama 3.3 70B), which is less expensive to run.\n")
        super().__init__(system_name, description, model_for_minor_agents="llama3.3-70b-instruct-fp8")
