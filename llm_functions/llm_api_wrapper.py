import asyncio
import os
import time
from http.client import responses

import google
import openai
from PIL import Image
from google import genai
from google.genai import types

import config
from llm_functions.llm_util import is_context_too_long, count_context_length
from scrt import OPENAI_KEY, GOOGLE_KEY

from config import DEBUG
from util.colors import PINK, RESET, BLUE, GREEN

def basic_prompt(prompt: str, role: str = "You are a helpful assistant.", temperature: float = 0.2,
                 model: str ="default") -> str:
    if model not in config.max_tokens or model == "default":
        print(f"{PINK} Default Model: {config.selected_model}{RESET}")
        model = config.selected_model

    if DEBUG:
        print(f"--------Invoking Model: {model}-------------")
        # print(f"{PINK}ROLE:\n{role}{RESET}")
        # print(f"{BLUE}PROMPT:\n{prompt}{RESET}")

    if model in config.MODEL_OWNER["google"]:
        response = _basic_prompt_gemini(prompt, role, temperature, model)
    else:
        response = _basic_prompt_openai(prompt, role, temperature, model)


    if DEBUG:
        print(f"{GREEN}RESPONSE:\n{response}{RESET}")
        print(f"---")
    return response

def _basic_prompt_openai(prompt: str, role: str, temperature: float, model: str) -> str:
    openai.api_key = OPENAI_KEY

    try:
        if is_context_too_long(prompt, model):
            raise ValueError("Prompt exceeds the maximum token limit.")
    except ValueError as e:
        print(f"Warning: {e}")

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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = genai.Client(api_key=GOOGLE_KEY)
    # Add the role to the prompt for context
    role_prompt = f"TASK: {role} \n---\nPROMPT: {prompt}"

    try:
        if is_context_too_long(role_prompt, model):
            raise ValueError("Prompt exceeds the maximum token limit.")
    except ValueError as e:
        print(f"Warning: {e}")

    if DEBUG:
        print("Estimated Number of Tokens: ", count_context_length(role_prompt, model))

    while True:
        try:
            response = client.models.generate_content(
                model=model,
                contents=role_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature
                )
            )
            break  # Exit the loop if the request is successful
        except genai.errors.ClientError as e:
            if e.code == 429:
                print("The search for the retry delay:")
                print(e)
                try:
                    str_e = str(e)
                    for i in range(len(str_e)):
                        if not str_e[len(str_e)-7+i :-6 + i].isdigit():
                            retry_delay = int(str_e[len(str_e)-7+i:-6 + i])
                            break
                    print("retry_delay:", retry_delay)
                except Exception:
                    print("could not surmise retry_delay using str")
                    retry_delay = 200



                print(f"Quota exceeded. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise e  # Re-raise the exception if it's not a quota error

    # Error handling (good practice)
    if not response.candidates:
        # Handle cases where the API returns no candidates (e.g., safety blocks)
        # You might want to inspect response.prompt_feedback
        if DEBUG:
            print("Prompt Feedback:", response.prompt_feedback)
        return f"Error: No content generated. Reason: {response.prompt_feedback.block_reason}"  # Or raise an exception

    # Check if 'text' attribute exists (newer versions might change structure slightly)
    if hasattr(response, 'text'):
        return response.text
    else:
        # Handle potential variations or errors (e.g., iterate through parts)
        try:
            # Try accessing text through parts if 'text' attribute isn't available
            full_text = "".join(part.text for part in response.candidates[0].content.parts)
            return full_text
        except (AttributeError, IndexError) as e:
            print(f"Error accessing response content: {e}")
            print("Full Response:", response)
            return "Error: Could not parse response."

def get_image_description(
        image_path: str,
        text_prompt: str = "Describe this image in detail.",
        model_name: str = config.DEFAULT_VISION_MODEL,
) -> str:
    return get_image_description_gemini(image_path, text_prompt, model_name)

def get_image_description_gemini(
        image_path: str,
        text_prompt: str = "Describe this image in detail.",
        model_name: str = config.DEFAULT_VISION_MODEL,
) -> str:
    """
    Sends an image and a text prompt to a Gemini vision model and returns the description.
    Uses default safety settings provided by the API.

    Args:
        image_path: Path to the image file.
        text_prompt: The text instruction for the LLM (e.g., "Describe this image.").
        model_name: The specific Gemini vision model to use.
    Returns:
        The textual description generated by the model, or an error message.
    """
    if not os.path.exists(image_path):
        return f"Error: Image file not found at {image_path}"

    if DEBUG:
        print(f"{BLUE}--- Invoking Vision Model: {model_name} ---{RESET}")
        # print(f"Image Path: {image_path}")
        # print(f"Text Prompt: {text_prompt}")

    try:
        # Configure the API client
        client = genai.Client(api_key=GOOGLE_KEY)

        # Load the image using Pillow for validation and compatibility
        try:
            img = Image.open(image_path)
            # Optional: Convert to RGB if needed, some models prefer it
            if img.mode != 'RGB':
                img = img.convert('RGB')
        except Exception as img_err:
            return f"Error: Could not open or process image file: {img_err}"

        # Prepare the content (list containing text prompt and image)
        content = [text_prompt, img]

        # Make the API call with retry logic for quota errors (similar to basic_prompt)
        retry_delay = 60  # Initial retry delay in seconds
        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=content,
                )

                # Check for safety blocks before accessing text (still important even with default settings)
                if not response.candidates:
                    block_reason = response.prompt_feedback.block_reason if hasattr(response.prompt_feedback,
                                                                                    'block_reason') else 'Unknown'
                    safety_ratings = response.prompt_feedback.safety_ratings if hasattr(response.prompt_feedback,
                                                                                        'safety_ratings') else 'N/A'
                    error_msg = f"Error: No content generated. Block Reason: {block_reason}. Ratings: {safety_ratings}"
                    if DEBUG: print(f"{PINK}{error_msg}{RESET}")
                    # Try to provide more info if available in the response object
                    # print("Full response feedback on block:", response.prompt_feedback)
                    return error_msg

                # Extract text - handle potential variations
                if hasattr(response, 'text'):
                    description = response.text
                else:
                    try:
                        description = "".join(part.text for part in response.candidates[0].content.parts)
                    except (AttributeError, IndexError):
                        # Fallback if parsing fails
                        # print("Full response on parsing failure:", response)
                        description = "Error: Could not parse response structure."

                if DEBUG:
                    print(f"{GREEN}RESPONSE:\n{description}{RESET}")
                    print(f"---")
                return description

            # Specific handling for Quota Exceeded (ResourceExhausted)
            except google.api_core.exceptions.ResourceExhausted as e:
                retries += 1
                print(
                    f"{PINK}Quota exceeded (429). Retrying in {retry_delay} seconds... ({retries}/{max_retries}){RESET}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            # Handle other potential API errors
            except Exception as e:
                error_msg = f"Error during Gemini API call: {type(e).__name__} - {e}"
                if DEBUG:
                    print(f"{PINK}{error_msg}{RESET}")
                # Optionally log the full traceback here if DEBUG is True
                # import traceback
                # if DEBUG: traceback.print_exc()
                return error_msg  # Return error after non-retryable exceptions

        return f"Error: Exceeded max retries ({max_retries}) due to API quota limits."


    except Exception as e:
        # Catch-all for configuration or unexpected errors
        error_msg = f"An unexpected error occurred in get_image_description_gemini: {e}"
        if DEBUG:
            import traceback
            tb_str = traceback.format_exc()
            print(f"{PINK}{error_msg}\nTraceback:\n{tb_str}{RESET}")
        return error_msg