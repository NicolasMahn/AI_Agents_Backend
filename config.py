import os

DEFAULT_MODEL = "gemini-2.5-pro-exp-03-25"
selected_model = DEFAULT_MODEL

DEFAULT_VISION_MODEL = "gemini-2.0-flash"

max_tokens = {                                          # Price per 1M tokens
    "gpt-4o": 128000,                                     # 2.5, 1.25, 10.0
    "gpt-4o-mini": 128000,                              # 0.15, 0, 0.6
    "o1": 128000,                                         # 15.0, 7.5, 60.0
    "o1-mini": 128000,                                    # 1.1, 0.55, 4.4
    "o3-mini": 200000,                                    # 1.1, 0.55, 4.4
    "gemini-2.0-flash": 1000000,                        # 0.1, 0.025, 0.4
    "gemini-2.0-flash-lite-preview-02-05": 1048576,     # 0.075, 0.018750, 0.3,
    "gemini-2.5-pro-exp-03-25": 1048576,
    "text-embedding-ada-002": 8192
}

max_tokens["default"] = max_tokens[selected_model]

MODEL_OWNER = {
    "openai": ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o3-mini"],
    "google": ["gemini-2.0-flash", "gemini-2.0-flash-lite-preview-02-05",
               "gemini-2.5-pro-exp-03-25"]
}

max_context_tokens = max_tokens[selected_model] - 60000 # minus a safety margin for role and other tokens
MAX_LENGTH_CONTEXT_ITEM = 700

MAX_SHORT_MEMORY_TOKENS = 700
RAG_CHUNK_SIZE = 1000

DEBUG = os.getenv("DEBUG", False)