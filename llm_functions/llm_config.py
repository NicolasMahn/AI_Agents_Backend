import config

DEFAUL_MODEL = config.DEFAULT_MODEL

MAX_TOKENS = {                                          # Price per 1M tokens
    "default": 128000,
    "gpt-4o": 128000,                                   # 2.5, 1.25, 10.0
    "gpt-4o-mini": 128000,                              # 0.15, 0, 0.6
    "o1": 200000,                                       # 15.0, 7.5, 60.0
    "o1-mini": 128000,                                  # 1.1, 0.55, 4.4
    "o3-mini": 200000,                                  # 1.1, 0.55, 4.4
    "gemini-2.0-flash": 1048576,                        # 0.1, 0.025, 0.4
    "gemini-2.0-flash-thinking-exp": 32767,             # non found
    "gemini-2.0-flash-lite-preview-02-05": 1048576,     # 0.075, 0.018750, 0.3,
    "learnlm-1.5-pro-experimental": 32000               # 1.25, 5.0, 0.3125 #prompts shorter than 128k (assumed)
}

MODEL_OWNER = {
    "openai": ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o3-mini"],
    "google": ["gemini-2.0-flash", "gemini-2.0-flash-thinking-exp", "gemini-2.0-flash-lite-preview-02-05",
               "learnlm-1.5-pro-experimental"]
}