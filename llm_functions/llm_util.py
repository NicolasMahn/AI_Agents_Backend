import tiktoken
from google import genai

from config import selected_model, DEBUG
from config import max_tokens, MODEL_OWNER


def count_context_length(prompt: str, model: str = "default") -> int:
    if model not in max_tokens.keys() or model == "default":
        model = selected_model
    try:
        if model in MODEL_OWNER["google"]:
            client = genai.Client()
            num_tokens = client.models.count_tokens(
                model=model, contents=prompt
            )
        else:
            encoding = tiktoken.encoding_for_model(model)
            num_tokens = len(encoding.encode(prompt))
    except Exception as e:
        try:
            num_tokens = int(len(prompt)/4)
        except Exception as e:
            print(f"Error: {e}")
            num_tokens = 0
    return num_tokens

def model_max_context_length(model: str) -> int:
    if model in max_tokens.keys():
        return max_tokens[model]
    return max_tokens["default"]

def is_context_too_long(prompt: str, role: str = "", model: str = "default") -> bool:
    if role != "":
        prompt = role + "\n" + prompt
    return count_context_length(prompt, model) > model_max_context_length(model)