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
    #"💰 GPT 4o": "gpt-4o",
    "GPT 4o mini": "gpt-4o-mini",

    "[NEW] GPT 5": "gpt-5",
    "[NEW] GPT 5 mini": "gpt-5-mini",
    "[NEW] GPT 5 nano": "gpt-5-nano",

    "🧠🏅📁💰💰 Gemini 2.5 Pro (most Intelligent by Google) (Most Expensive in Selection)": "gemini-2.5-pro-preview-03-25",
    "🧠📁💰💰 Gemini 2.5 Flash": "gemini-2.5-flash-preview-04-17",
    "💸📁 Gemini 2.0 Flash (Free)": "gemini-2.0-flash",
    "💸📁 Gemini 2.0 Flash Lite (Free)": "gemini-2.0-flash-lite",
}

max_tokens = {
    # Open AI
    "o4-mini-high": 200_000,
    "o4-mini": 200_000,
    "o3-mini-high": 200_000,
    "o3-mini": 200_000,
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    #"gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-5": 400_000,
    "gpt-5-mini": 400_000,
    "gpt-5-nano": 400_000,
    # ---
    "text-embedding-ada-002": 8192,
    # Google
    "gemini-2.5-pro-preview-03-25": 1_000_000,
    "gemini-2.5-flash-preview-04-17": 1_000_000,
    "gemini-2.0-flash": 1_000_000,
    "gemini-2.0-flash-lite": 1_000_000,
    # Open Source
    "deepseek-r1-671b": 128_000,
    "deepseek-llama3.3-70b": 128_000,
    "deepseek-v3-0324": 128_000,
    "llama-4-maverick-17b-128e-instruct-fp8": 1_000_000,
    "llama-4-scout-17b-16e-instruct": 10_000_000,
    "llama3.3-70b-instruct-fp8": 128_000,
    "llama3.1-405b-instruct-fp8": 128_000,
    "llama3.1-nemotron-70b-instruct-fp8": 128_000,
    "llama3.1-70b-instruct-fp8": 128_000,
    "llama3.1-8b-instruct": 128_000,
    "llama3.2-3b-instruct": 128_000,
    "lfm-40b": 66_000,
    "qwen25-coder-32b-instruct": 32_000,
}


max_tokens["default"] = max_tokens[selected_model]

MODEL_OWNER = {
    "openai": ["o4-mini-high", "o4-mini", "o3-mini-high", "o3-mini", "gpt-4.1-mini", "gpt-4.1-nano", #"gpt-4o",
               "gpt-4o-mini", "gpt-5", "gpt-5-mini", "gpt-5-nano",
               "text-embedding-ada-002"],
    "google": ["gemini-2.5-pro-preview-03-25", "gemini-2.5-flash-preview-04-17",
               "gemini-2.0-flash", "gemini-2.0-flash-lite"],
}

max_prompt_tokens = 10_000
max_instructions_size = 10_000
max_generic_content_length = 10_000
max_context_tokens = max_tokens[selected_model] - max_instructions_size - max_prompt_tokens
max_chat_tokens = 4 * max_generic_content_length

top_k = 3
long_memory_display = True

RAG_CHUNK_SIZE = 8192

DEBUG = os.getenv("DEBUG", False)

