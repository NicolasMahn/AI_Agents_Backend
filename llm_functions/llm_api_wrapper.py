from http.client import responses

import openai
from google import genai
from google.genai import types
import tiktoken

from llm_functions.llm_config import MAX_TOKENS, MODEL_OWNER
from llm_functions.llm_util import is_context_too_long
from scrt import OPENAI_KEY, GOOGLE_KEY

from config import DEFAULT_MODEL, DEBUG
from util.colors import PINK, RESET, BLUE, GREEN

def basic_prompt(prompt: str, role: str = "You are a helpful assistant.", temperature: float = 0.2,
                 model: str ="default") -> str:
    try:
        if model not in MAX_TOKENS or model == "default":
            model = DEFAULT_MODEL
        if is_context_too_long(prompt, model):
            raise ValueError("Prompt exceeds the maximum token limit.")
    except ValueError as e:
        print(f"Warning: {e}")

    if DEBUG:
        print(f"-------------Model: {model}-------------")
        print(f"{PINK}ROLE:\n{role}{RESET}")
        print(f"{BLUE}PROMPT:\n{prompt}{RESET}")

    if model in MODEL_OWNER["google"]:
        response = _basic_prompt_gemini(prompt, role, temperature, model)
    else:
        response = _basic_prompt_openai(prompt, role, temperature, model)


    if DEBUG:
        print(f"{GREEN}RESPONSE:\n{response}{RESET}")
        print(f"---")
    return response

def _basic_prompt_openai(prompt: str, role: str, temperature: float, model: str) -> str:
    openai.api_key = OPENAI_KEY

    if model.startswith("o3"):
        reasoning_effort = None
        if model == "o3-mini-high":
            reasoning_effort = "high"
            model = "o3-mini"
        elif model == "o3-mini-medium":
            reasoning_effort = "medium"
            model = "o3-mini"
        elif model == "o3-mini-low":
            reasoning_effort = "low"
            model = "o3-mini"
        response_text = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": role},
                {
                    "role": "user",
                    "content": prompt,
                    "temperature": temperature
                }
            ],
            reasoning_effort=reasoning_effort
        )
    else:
        response_text = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": role},
                {
                    "role": "user",
                    "content": prompt,
                    "temperature": temperature
                }
            ]
        )
    return response_text.choices[0].message.content

def _basic_prompt_gemini(prompt: str, role: str, temperature: float, model: str) -> str:
    client = genai.Client(api_key=GOOGLE_KEY)
    # Add the role to the prompt for context
    role_prompt = f"TASK: {role} \n---\nPROMPT: {prompt}"

    response = client.models.generate_content(
        model=model,
        contents=role_prompt,
        config=types.GenerateContentConfig(
            temperature=temperature
        )
    )
    return response.text