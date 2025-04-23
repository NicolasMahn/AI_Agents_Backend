
from agents import Agent
from llm_functions import basic_prompt


class ReviewingAgent(Agent):
    def __init__(self, name="Planning Agent",
                 role="You are the AI Agent. You are given tasks by the User and converse with him in a chat. \n"
                        "Your handle in the chat is `Agent`. "
                        "The User can only see information in the `<response>` section of the chat (explained below..)\n",
                 chroma_collection = "python"
                 ):
        super().__init__(name, role, chroma_collection)

    def prompt_agent(self):
        self.replying = True
        self._prompt = self.clean_chat.get_last_messages_of_sender('User')

        i = 0
        while self.clean_chat.get_last_sender() != self.name and i < self.max_iterations:
            print(f"Executing prompt {i + 1}")
            instructions = (
                 "**Instructions:**\n"
                f"1. **Understand:** Read the User's request, the history and the current Context carefully.\n"
                 "2. **Plan:** Explain your plan step-by-step. Identify which commands (`<code>`, `<query>`, `<document>`, etc.) are (now) required.\n"
                 "3. **Execute Action:** Output the command tag for the *single, most important step* identified in your plan (e.g., `<query>...</query>` or `<code>...</code>).\n"
                 "    * If you determined clarification is needed (Step 1), do not output a command tag. Explain why you are blocked.\n"
                 "4. **Memory:** Consider if `<long_memory>` is appropriate for any findings or plans.\n\n"
            )

            self.command_instructions["response"]["active"] = False #Forbidde the use of the response command
            entire_prompt = \
                f"{self._prompt}\n---\n{instructions}\n---\n{self.get_instruction_str()}\n---\n{self.generate_context_data()}"
            self.prompt(entire_prompt)

            if not self.extraction_failure:
                print("Continuing to next step?")
                instructions = (
                    f"**Assess Completion:** Carefully review the Original User Request, the conversation history, and especially the **results from the last action**. \n"
                    "Do you **now** have all the information needed to provide the *complete and final answer* to the user? Explain your reasoning in detail.\n\n"

                    "* **If YES:** **CRITICAL CHECK:** Before confirming, perform this internal check:\n"
                    f"   1. Re-read the **Original User Request** precisely.\n"
                    "    2. Verify point-by-point: Does the available information (Context and Last Action Results) definitively and accurately answer **every single aspect** of that request?\n"
                    "    3. Consider completeness: Are there any parts of the request left unaddressed, any ambiguities remaining, or potential inaccuracies in the gathered information?\n"
                    "    4. **Code Tool Check (If Applicable): If the original request involved writing, running, modifying, or explaining code, confirm that the `<code>` command was actually used appropriately during the previous steps and that its output (or the code generated) is present and directly addresses the code-related aspect of the request.**\n"
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

                entire_prompt = \
                    f"{instructions}\n---\n{self.generate_context_data(status_info=True)}---\n**Here are the Instructions for reference, but they can not be used in this prompt:**\n{self.get_instruction_str()}"
                if self.prompt(entire_prompt, yes_no_prompt=True):
                    break
            i += 1

        while self.clean_chat.get_last_sender() != self.name:
            print(f"Executing final prompt ({i + 2})")

            self.command_instructions["response"]["active"] = True

            self.command_instructions["code"]["active"] = False
            self.command_instructions["query"]["active"] = False
            self.command_instructions["document"]["active"] = False
            self.command_instructions["search"]["active"] = False

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
                f"{self._prompt}\n---\n{instructions}\n---\n{self.get_instruction_str()}\n---\n{self.generate_context_data()}"

            self.prompt(entire_prompt)
            i += 1

        self.command_instructions["code"]["active"] = True
        self.command_instructions["query"]["active"] = True
        self.command_instructions["document"]["active"] = True
        self.command_instructions["search"]["active"] = False # TODO: Once search exists make true here too

        self.replying = False
        pass