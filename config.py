import os

DEFAULT_MODEL = "gemini-2.0-flash"
selected_model = DEFAULT_MODEL

DEFAULT_VISION_MODEL = "gpt-4o-mini"

llm_names = {
    "🧠🏆🪙 o4 mini (high) (most Intelligent)": "o4-mini-high",
    "🧠🪙 o4 mini": "o4-mini",
    "🧠🪙 o3 mini (high)": "o3-mini-high",
    "🧠🪙 o3 mini": "o3-mini",
    "🥇📁💰 GPT 4.1 mini (most Intelligent non-Thinking Model)": "gpt-4.1-mini",
    "📁 GPT 4.1 nano": "gpt-4.1-nano",
    "💰 GPT 4o": "gpt-4o",
    "GPT 4o mini": "gpt-4o-mini",

    "🧠🏅📁💰💰 Gemini 2.5 Pro (most Intelligent by Google) (Most Expensive in Selection)": "gemini-2.5-pro-preview-03-25",
    "🧠📁💰💰 Gemini 2.5 Flash": "gemini-2.5-flash-preview-04-17",
    "💸📁 Gemini 2.0 Flash (Free)": "gemini-2.0-flash",
    "💸📁 Gemini 2.0 Flash Lite (Free)": "gemini-2.0-flash-lite",

    "🧠🏅 Deepseek R1 (most Intelligent Open Source)": "deepseek-r1-671b",
    "🧠 Deepseek Llama 3.3 70B (Cheapest Reasoning)": "deepseek-llama3.3-70b",
    "Deepseek V3 (Most Intelligent non-Reasoning Open Source)": "deepseek-v3-0324",

    "🏅📁🪙 Llama 4 Maverick (Most Intelligent Llama)": "llama-4-maverick-17b-128e-instruct-fp8",
    "🗂️💰 Llama 4 Scout (Largest Context Window)": "llama-4-scout-17b-16e-instruct",
    "Llama 3.3 70B": "llama3.3-70b-instruct-fp8",
    "🪙 Llama 3.1 405B": "llama3.1-405b-instruct-fp8",
    "Llama 3.1 70B": "llama3.1-70b-instruct-fp8",
    "Llama 3.1 8B": "llama3.1-8b-instruct",
    "📏 Llama 3.2 3B (smallest Model)": "llama3.2-3b-instruct",

    "Llama 3.1 Nemotron 70B (Nvidia)": "llama3.1-nemotron-70b-instruct-fp8",

    "LFM 40B": "lfm-40b",

    "Qwen 2.5 Coder (Code Specific)": "qwen25-coder-32b-instruct",
}

max_tokens = {
    # Open AI
    "o4-mini-high": 200000,
    "o4-mini": 200000,
    "o3-mini-high": 200000,
    "o3-mini": 200000,
    "gpt-4.1-mini": 1000000,
    "gpt-4.1-nano": 1000000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    # ---
    "text-embedding-ada-002": 8192,
    # Google
    "gemini-2.5-pro-preview-03-25": 1000000,
    "gemini-2.5-flash-preview-04-17": 1000000,
    "gemini-2.0-flash": 1000000,
    "gemini-2.0-flash-lite": 1000000,
    # Open Source
    "deepseek-r1-671b": 128000,
    "deepseek-llama3.3-70b": 128000,
    "deepseek-v3-0324": 128000,
    "llama-4-maverick-17b-128e-instruct-fp8": 1000000,
    "llama-4-scout-17b-16e-instruct": 10000000,
    "llama3.3-70b-instruct-fp8": 128000,
    "llama3.1-405b-instruct-fp8": 128000,
    "llama3.1-nemotron-70b-instruct-fp8": 128000,
    "llama3.1-70b-instruct-fp8": 128000,
    "llama3.1-8b-instruct": 128000,
    "llama3.2-3b-instruct": 128000,
    "lfm-40b": 66000,
    "qwen25-coder-32b-instruct": 32000,
}


max_tokens["default"] = max_tokens[selected_model]

MODEL_OWNER = {
    "openai": ["o4-mini-high", "o4-mini", "o3-mini-high", "o3-mini", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini",
               "text-embedding-ada-002"],
    "google": ["gemini-2.5-pro-preview-03-25", "gemini-2.5-flash-preview-04-17",
               "gemini-2.0-flash", "gemini-2.0-flash-lite"],
    "lambda": ["llama-4-maverick-17b-128e-instruct-fp8", "llama-4-scout-17b-16e-instruct",
               "llama3.3-70b-instruct-fp8", "llama3.2-3b-instruct", "llama3.1-405b-instruct-fp8",
               "llama3.1-70b-instruct-fp8", "llama3.1-8b-instruct",
               "deepseek-r1-671b", "deepseek-v3-0324", "deepseek-llama3.3-70b",
               "llama3.1-nemotron-70b-instruct-fp8",
               "lfm-40b",
               "qwen25-coder-32b-instruct"],
}

max_prompt_tokens = 10000
max_instructions_size = 10000
max_generic_content_length = 10000
max_context_tokens = max_tokens[selected_model] - max_instructions_size - max_prompt_tokens
max_chat_tokens = 4 * max_generic_content_length

RAG_CHUNK_SIZE = 8192

DEBUG = os.getenv("DEBUG", False)

