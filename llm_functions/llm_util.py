import asyncio

import tiktoken
from google import genai

import config
from config import max_tokens, MODEL_OWNER, DEBUG
from scrt import GOOGLE_KEY, HUGGING_FACE_KEY
from util.colors import PINK, RESET
from transformers import AutoTokenizer

# --- Mapping for Hugging Face Tokenizers ---
HF_TOKENIZER_MAP = {
    "llama3.3-70b-instruct-fp8": "meta-llama/Llama-3.3-70B-Instruct",
    "llama3.2-3b-instruct": "meta-llama/Llama-3.2-3B-Instruct",
    "llama3.1-405b-instruct-fp8": "meta-llama/Meta-Llama-3.1-405B-Instruct",
    "llama3.1-nemotron-70b-instruct-fp8": "meta-llama/Meta-Llama-3.1-70B-Instruct", # using metas as a proxy
    "llama3.1-70b-instruct-fp8": "meta-llama/Meta-Llama-3.1-70B-Instruct",
    "llama3.1-8b-instruct": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "deepseek-r1-671b": "deepseek-ai/DeepSeek-R1",
    "deepseek-v3-0324": "deepseek-ai/DeepSeek-V3-0324",
    "deepseek-llama3.3-70b": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
    "qwen25-coder-32b-instruct": "Qwen/Qwen2.5-Coder-32B-Instruct",
    "llama-4-maverick-17b-128e-instruct-fp8": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "llama-4-scout-17b-16e-instruct": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    #"lfm-40b": None,   # Not available on Huggingface
}

# --- Cache for loaded tokenizers ---
_tokenizer_cache = {}


# --- Mapping for OpenAI Models ---
OPENAI_ENCODING_MAP = {
    "o4-mini": "o200k_base",
    "o3-mini": "o200k_base",
    "o1-mini": "o200k_base",
    "gpt-4.1-mini": "o200k_base", #guess
    "gpt-4.1-nano": "o200k_base", #guess
    "gpt-4o-mini": "o200k_base",
    "text-embedding-ada-002": "cl100k_base",
}

def get_tokenizer(model_name):
    """Loads and caches Hugging Face tokenizers."""
    if model_name in _tokenizer_cache:
        return _tokenizer_cache[model_name]

    hf_model_id = HF_TOKENIZER_MAP.get(model_name)
    if hf_model_id:
        try:
            tokenizer = AutoTokenizer.from_pretrained(hf_model_id, token=HUGGING_FACE_KEY)
            _tokenizer_cache[model_name] = tokenizer
            return tokenizer
        except Exception as e:
            print(f"{PINK}Failed to load tokenizer {hf_model_id} for {model_name}: {e}{RESET}")
            return None
    else:
        print(f"{PINK}No Hugging Face tokenizer mapping found for model: {model_name}{RESET}")
        return None

def count_context_length(prompt: str, model: str = "default") -> int:
    if model not in max_tokens.keys() or model == "default":
        model = config.selected_model
    if model.endswith("-high"):
        model = model[:-5]
    if model.endswith("-medium"):
        model = model[:-7]
    if model.endswith("-low"):
        model = model[:-4]
    if model.endswith("-basic"):
        model = model[:-6]
    try:
        if model in MODEL_OWNER["google"]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            client = genai.Client(api_key=GOOGLE_KEY)
            num_tokens = client.models.count_tokens(
                model=model, contents=prompt
            ).total_tokens
        elif model in MODEL_OWNER["openai"] and not model.startswith("gpt-5"):
            encoding_name = OPENAI_ENCODING_MAP.get(model)
            encoding = tiktoken.get_encoding(encoding_name)
            num_tokens = len(encoding.encode(prompt))
        elif model != "lfm-40b" and model not in MODEL_OWNER["openai"]:
            tokenizer = get_tokenizer(model)
            num_tokens = len(tokenizer.encode(prompt, add_special_tokens=False))
        else:
            num_tokens = int(len(prompt) / 4)
    except Exception as e:
        try:
            print(f"{PINK}Tokenizer Failed, using heuristic: {e}{RESET}")
            num_tokens = int(len(prompt)/4)
        except Exception as e:
            print(f"{PINK}Error: {e}{RESET}")
            num_tokens = 0
    return num_tokens

def model_max_context_length(model: str) -> int:
    if model in max_tokens.keys():
        return max_tokens[model]
    return max_tokens["default"]

def is_context_too_long(prompt: str, role: str = "", model: str = "default") -> bool:
    if role != "":
        prompt = role + "\n" + prompt
    num_tokens = count_context_length(prompt, model)
    if DEBUG:
        print("Estimated Number of Tokens: ", num_tokens)

    return num_tokens > model_max_context_length(model)