import tiktoken

from config import DEFAULT_MODEL
from llm_functions.llm_config import MAX_TOKENS


def count_context_length(prompt: str, model: str = "default") -> int:
    if model not in MAX_TOKENS.keys() or model == "default":
        model = DEFAULT_MODEL
    try:
        encoding = tiktoken.encoding_for_model(model)
        num_tokens = len(encoding.encode(prompt))
    except Exception as e:
        num_tokens = len(prompt.split())
    return num_tokens

def model_max_context_length(model: str) -> int:
    if model in MAX_TOKENS:
        return MAX_TOKENS[model]
    return MAX_TOKENS["default"]

def is_context_too_long(prompt: str, model: str = "default") -> bool:
    return count_context_length(prompt, model) > model_max_context_length(model)