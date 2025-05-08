from llm_functions import basic_prompt
from util.colors import RED, RESET


class BaseAgent:
    """
    The Default Agent that has all tools at its disposal.
    """

    def __init__(self, system, agent_name, role, chroma_collection=None, model=None, internal_agent=True):
        """
        Initializes the BaseAgent with the given parameters.
        :param system: the agent system that this agent is part of
        :param agent_name: name of agent
        :param role: role of the agent
        :param chroma_collection: where to get the context_dump for the agent, None means no rag
        :param model: model the agent should use. None means default model / selectable
        :param internal_agent: if the agent does not use any tools (including response)
        """
        self.agent_name = agent_name
        self.role = role
        self.chroma_collection = chroma_collection
        self.model = model
        self.internal_agent = internal_agent

        self.system = system
        self.command_instructions = self.get_default_command_instructions()

        if not self.internal_agent:
            for key in self.command_instructions:
                self.command_instructions[key]["active"] = False

        self.no_consecutive_messages = False

    def get_name(self):
        return self.agent_name

    def get_role(self):
        return self.role

    def get_model(self):
        return self.model

    def get_chroma_collection(self):
        return self.chroma_collection

    def get_full_prompt(self, prompt):
        """
        Generates the full prompt for the agent.
        :param prompt: The prompt to be sent to the agent.
        :return: The full prompt for the agent.
        """
        entire_prompt = \
            f"{prompt}\n\n---\n\n{self.get_instruction_str()}\n\n---\n\n{self.system.generate_context_data(self)}"
        return entire_prompt

    def prompt(self, prompt):
        entire_prompt = self.get_full_prompt(prompt)
        try:
            response = basic_prompt(entire_prompt, self.get_role(), self.get_model())
        except Exception as e:
            print(f"{RED}Error in prompt:{RESET} {e} ")
            response = "Error when attempting to prompt the LLM. Please try again."

        if self.internal_agent:
            self.system.use_tools(response, self)

        return response, entire_prompt

    def add_custom_command_instructions(self, name, instructions, active=True):
        self.command_instructions[name] = {"text": instructions, "active": active}

    def get_instruction_str(self, ignore_active=False):
        instructions_str = ""
        for key, value in self.command_instructions.items():
            if ("active" in value and value["active"]) or ignore_active:
                if "dynamic_data" in value and value["dynamic_data"]:
                    if isinstance(value["dynamic_data"], list):
                        for i in value["dynamic_data"]:
                            instructions_str += value["text"].format(i)
                    else:
                        dynamic_data_str = value["dynamic_data"]()
                        instructions_str += value["text"].format(dynamic_info=dynamic_data_str)
                else:
                    instructions_str += value["text"]

        return instructions_str

    def get_default_command_instructions(self):
        return {
            "introduction": {
                "text": (
                    "# **Tool Instructions**\n"
                    "To perform actions beyond conversation, such as running code or searching, you will use commands "
                    "formatted as **XML tags**. Your interactions using these tags (both the commands you issue and "
                    "the results you receive) are recorded and may be referenced in later turns.\n\n"

                    "### Important: Avoiding Tag Confusion\n"
                    "The command parser looks for specific XML tags of tools like `<short_memory>` etc. in your regular conversational text or explanations, as this confuses the parser and can cause errors. \n"
                    "To refer to tag names within your text, use textual descriptions (e.g., 'the code tag'), rather than literal `< >` characters.\n\n"
                    "**Only use the exact, documented command tags when you intend to invoke a specific tool.**\n\n"
                    "### **Essential: Using `<![CDATA[...]]>`**\n\n"
                    "When you place code (e.g., Python) inside specific XML tags like `<code>`, you **must** wrap the entire code block within `<![CDATA[...]]>`. \n\n"
                    "**Why is `CDATA` required?**\n"
                    "* **Prevents XML Errors:** Code often contains characters like `<`, `>`, and `&` which have special meanings in XML...\n"  # Truncated for brevity
                    "* **Preserves Code Integrity:** `CDATA` tells the parser to treat everything within it as raw character data...\n\n"  # Truncated for brevity
                    "**Always use `CDATA` for code embedded within command tags.** Refer to the specific instructions for each available tool/command for details on their tags and arguments.\n"
                    "**Important:** Avoid nested command tags. For example, do not place `<code>` tags inside a `<response>` tag. This can lead to parsing errors and unexpected behavior.\n\n"
                ),
                "active": True
            },
            "code": {
                "text": (
                    "## **Code (`<code>`)**\n"
                    "This system allows you to run Python code in a secure, resource-limited environment. "
                    "Use the structured XML-like format below to define execution parameters.\n"
                    "Please provide code always in the `<code ...><![CDATA[...]]></code>` format. \n"
                    "**Important:** If the user request any code, please use the `<code>` tag. \n\n"

                    "💡 *Tip:* Add many print and try catch blocks to identify your own errors.\n\n"

                    "### **Basic Execution**\n"
                    "```xml\n"
                    "<code tag=\"simple example\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "# Your Python code here\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"

                    "### **Adding Dependencies**\n"
                    "```xml\n"
                    "<code requirements=[\"numpy\"] tag=\"requirements example\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "import numpy as np\n"
                    "a = np.array([1,2,3])\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "By default, the code will be executed in a virtual environment with the following packages:\n"
                    "pandas, numpy, matplotlib, seaborn, plotly, dash, scikit-learn, datetime\n\n"


                    "### **Frontend**\n"
                    "You can build a frontend using dash."
                    "Simply add a frontend tag to your code and the frontend will be displayed in the dashboard.\n"
                    "```xml\n"
                    "<code frontend=\"True\" tag=\"dash example\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "import dash\n"
                    "from dash import html\n"
                    "\n"
                    "# Initialize the Dash app\n"
                    "app = dash.Dash(__name__)\n"
                    ""
                    "# Define the layout of the app (just static HTML elements)\n"
                    "app.layout = html.Div([\n"
                    "    html.H1(\"Simplest Dash App\" tag=\"simple-dashboard\" version=\"1.0\"), # A header\n"
                    "    html.P(\"This app just displays static text.\") # A paragraph\n"
                    "])\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "**Important: The dash app has to be called `app` otherwise it will not run!**\n"
                    "**Important: If any kind of dashboard is requested by the user, please use the `<code frontend=\"True\">` tag.**\n\n"

                    "### **Accessing Files**\n"
                    "**Reading Files**\n"
                    "```xml\n"
                    "<code tag=\"file usage\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "with open(\"uploads/data.txt\", \"r\") as f:\n"
                    "    content = f.read()\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "**Important:** Only files in the `uploads` directory are available. \n\n"

                    "**Saving Files**\n"
                    "```xml\n"
                    "<code tag=\"output\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "with open(\"output/message.txt\", \"w\") as f:\n"
                    "    f.write(\"Hello, world!\")\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "**Important:** Output files will only be saved in the `output` directory if explicitly placed there. \n\n"

                    "### **Versioning and Tagging Code**\n"
                    "```xml\n"
                    "<code tag=\"experiment-alpha\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "x = 42\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n"

                    "Please add both a tag and a version to your code. as this increases the human readability of the code.\n\n"

                    "### **Reusing Code**\n"

                    "You can reuse previously written code by referencing a code `tag` and optionally a `version`. "
                    "If no version is provided, the latest version for that tag is used.\n\n"

                    "```xml\n"
                    "<code tag=\"add\" version=\"1.0\">\n"
                    "<![CDATA[\n"
                    "def add(a, b):\n"
                    "    return a + b\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "```xml\n"
                    "<code import={\"tag\": \"add\"}>\n"
                    "<![CDATA[\n"
                    "print(add(3, 4))\n"
                    "]]>\n"
                    "</code>\n"
                    "```\n\n"
                    "It is also possible to import multiple code snippets by providing a list of tags (`<code import=[{\"tag\": \"add\"}, {\"tag\": \"sub\"}]>...</code>`). "

                    "💡 *Tip:* Work in small, testable code chunks to reduce errors when combining logic.\n\n"
                    "💡 *Tip:* output files from previous code snippets are available in the `output` directory, *if* they are imported.\n\n"

                    "**Important:** When this command (`<code>`) is used it is impossible to reply to the user at the same time as you will have to wait for the results.\n\n"
                ),
                "active": True
            },
            "response": {
                "text": (
                    "## **Responding to the User (`<response>`)**\n\n"
                    "### **Crucial: The User's Perspective**\n"
                    "The user you are assisting has a limited view of our interaction. They **only** see:\n"
                    "1.  Their own prompts/messages to you.\n"
                    "2.  The exact content you place inside `<response>` tags.\n"
                    "3.  The output (e.g., print statements, plots, errors) generated by any `<code>` command you execute.\n\n"
                    "The user **does NOT** see your internal reasoning, planning steps, intermediate thoughts written outside tags, the code within `<code>` tags (only its output), or the results of non-code commands like `<query>`.\n\n"

                    "**Therefore, the `<response>` tag is your primary (and only) communication channel and must contain everything the user needs to understand the answer.**\n\n"

                    "### **Usage Rule: Exclusivity of `<response>`**\n\n"
                    "The `<response>` tag signals the completion of your task for the current user request. Therefore, it **must generally be used exclusively** in your output turn.\n\n"
                    "* **You CANNOT combine `<response>` with action tags** like `<code>`, `<query>`, or `<document>` in the same output. Attempting to do so will result in an error.\n"
                    "* You **CAN** optionally include a `<long_memory>` tag alongside `<response>` if you need to save information while responding.\n"
                    "* Any reasoning or planning text outside of tags should also conclude *before* you generate the `<response>`.\n\n"
                    "**Workflow:** If you need to perform an action (like running code), do that in one turn. Then, in a *subsequent* turn (after assessing the results), generate the final `<response>`.\n\n"


                    "### **What to Include in Your `<response>`:**\n"
                    "To provide a helpful and complete answer, your text inside `<response><![CDATA[...]]></response>` should generally:\n\n"
                    "* **Acknowledge/Reference the User's Query:** Briefly mention the core question you are answering. (e.g., \"Regarding your question about X...\", \"You asked for Y, here is the result:\").\n"
                    "* **Provide the Direct Answer:** State the solution, result, or information clearly and upfront.\n"
                    "* **Explain Your Key Steps (User-Friendly):** Briefly summarize *how* you (as the Agent) arrived at the answer, "
                    "especially if it involved actions the user isn't directly seeing results from (like searches) or complex logic. Focus on what's relevant for the user to understand the context or validity of the answer.\n"
                    "    * *Example:* \"I searched for recent articles on that topic and found...\"\n"
                    "    * *Example:* \"To calculate this, I wrote some code to process the data you provided. The main steps were...\"\n"
                    "* **Interpret Code/Data Output:** If you ran code (in the history) (`<code>`), don't just rely on the user seeing the raw output. Explain what the output means in the context of their query.\n"
                    "    * *Example:* \"The code calculated the average, and as you can see in the output above, the result is 42.5.\"\n"
                    "    * *Example:* \"I generated a plot showing the trend, which is displayed above.\"\n"
                    "* **Be Self-Contained:** Ensure the response makes sense on its own, considering the user only sees their query, your response, and code output.\n\n"

                    "### **Example Structure:**\n"
                    "```xml\n"
                    "<response>\n"
                    "<![CDATA[\n"
                    "Okay, I looked into your question about [User's Topic]. \n\n"
                    "The answer is [Direct Answer/Result].\n\n"
                    "To find this, I [briefly explain key steps, e.g., ran a search / analyzed the data / executed code]. [If code was run:] The code output above shows [interpretation of the output].\n\n"
                    "[Optional: Add any necessary context, caveats, or next steps/questions].\n"
                    "]]>\n"
                    "</response>\n"
                    "```\n"
                    "**Goal:** Your response should bridge the gap between the user's question and the final answer, making the process understandable from their limited perspective.\n"
                ),
                "active": True
            },
            "short_memory": {
                "text": (
                    "## **Short-Term Memory (`<short_memory>`)**\n"
                    "- Save temporary information:\n"
                    "```xml\n"
                    "<short_memory>\n"
                    "<![CDATA[\n"
                    "Your text here\n"
                    "]]>\n"
                    "</short_memory>\n"
                    "```\n"
                    "- Use this to store information that is relevant for the current task. The history will be truncated after a certain length. The Short-Term History will always remain in the context, until the history is reset.\n"
                ),
                "active": True
            },
            "long_memory": {
                "text": (
                    "## **Long-Term Memory (RAG-DB) (`<long_memory>`)**\n"
                    "- Save persistent knowledge:\n"
                    "```xml\n"
                    "<long_memory>\n"
                    "<![CDATA[\n"
                    "Your text here\n"
                    "]]>\n"
                    "</long_memory>\n"
                    "```\n"
                    "- Use this to store information that could be useful beyond this project.\n"
                    "- Stored in chunks of **8192** tokens.\n"
                    "- Relevant sections will be retrieved automatically when working on related tasks.\n\n"
                ),
                "active": True
            },
            "query": {
                "text": (
                    "## **Retrieving Information (`<query>`)**\n"
                    "\n"
                    "### **Querying Stored Information**\n"
                    "To access relevant information from the **RAG-DB (long-term memory)** or stored **documents**, use the `<query>` tag.\n\n"
                    "#### **General Query (Default)**\n"
                    "A `<query>` searches relevant documents by default.\n"
                    "Example:\n"
                    "```xml\n"
                    "<query>How can one reverse a linked list?</query>\n"
                    "```\n\n"
                    "#### **Targeted Queries**\n"
                    "You can specify the source:\n"
                    "\n"
                    "- **Long-Term Memory:**\n"
                    "```xml\n"
                    "<query type=\"memory\">Summarize previous discussions about model selection.</query>\n"
                    "```\n"
                    "- **Documents (default):**\n"
                    "```xml\n"
                    "<query type=\"documents\">Find references to data privacy regulations.</query>\n"
                    "```\n\n"
                ),
                "active": True
            },
            "document": {
                "text": (
                    "## **Project Documents (`<document>`)**\n"
                    "Throughout this project, several documents will be created and stored. You can query these documents using the `<document>` tag.\n"
                    "As an attribute, you will need to append the document path. Here is a list of available documents:\n"
                    "{dynamic_info}\n"  # Placeholder for dynamic content
                    "\n"
                    "Here is an example of how to query a document:\n"
                    "```xml\n"
                    "<document filepath=\"success_criteria.txt\" />\n"
                    "```\n\n"
                    "Please ensure to add the entire path to the document in the pseudo XML.\n"
                    "*Important:* When this command is used it is impossible to reply to the user at the same time as you will have to wait for the results.\n\n"
                ),
                "dynamic_data": self.system.get_available_document_filepaths_str,
                "active": True
            },
        }