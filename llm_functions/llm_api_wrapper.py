import asyncio
import base64
import io
import os
import time
import google
import openai
from PIL import Image
from google import genai
from openai import OpenAI

import config
from llm_functions.llm_util import is_context_too_long
from scrt import OPENAI_KEY, GOOGLE_KEY, LAMBDA_KEY

from config import DEBUG
from util.colors import PINK, RESET, BLUE, GREEN

def basic_prompt(prompt: str, role: str = "You are a helpful assistant.", model=None) -> str:
    if model is None:
        model = config.selected_model

    if DEBUG:
        print(f"--------Invoking Model: {model}-------------")
        # print(f"{PINK}ROLE:\n{role}{RESET}")
        # print(f"{BLUE}PROMPT:\n{prompt}{RESET}")

    if model in config.MODEL_OWNER["google"]:
        response = _basic_prompt_gemini(prompt, role, model)
    elif model in config.MODEL_OWNER["openai"]:
        response = _basic_prompt_openai(prompt, role, model)
    else:
        response = _basic_prompt_lambda(prompt, role, model)


    if DEBUG:
        print(f"{GREEN}RESPONSE:\n{response}{RESET}")
        print(f"---")
    return response


def _basic_prompt_lambda(prompt: str, role: str, model: str) -> str:
    lambda_api_key = LAMBDA_KEY
    lambda_api_base = "https://api.lambda.ai/v1"

    try:
        if is_context_too_long(prompt, model):
            raise ValueError("Prompt exceeds the maximum token limit.")
    except ValueError as e:
        print(f"Warning: {e}")

    client = OpenAI(
        api_key=lambda_api_key,
        base_url=lambda_api_base,
    )

    response_text = client.chat.completions.create(
        messages=[
            {"role": "system", "content": role},
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model = model
    )
    return response_text.choices[0].message.content



def _basic_prompt_openai(prompt: str, role: str, model: str) -> str:
    openai.api_key = OPENAI_KEY

    try:
        if is_context_too_long(prompt, model):
            raise ValueError("Prompt exceeds the maximum token limit.")
    except ValueError as e:
        print(f"Warning: {e}")

    reasoning_effort = None
    if model.endswith("-high"):
        reasoning_effort = "high"
        model = model[:-5]  # Remove "-high" suffix
    elif model.endswith("-medium"):
        reasoning_effort = "medium"
        model = model[:-7]
    elif model.endswith("-low"):
        reasoning_effort = "low"
        model = model[:-4]

    if reasoning_effort:
        response_text = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": role},
                {
                    "role": "user",
                    "content": prompt,
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
                }
            ]
        )
    return response_text.choices[0].message.content

def _basic_prompt_gemini(prompt: str, role: str, model: str) -> str:
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

    while True:
        try:
            response = client.models.generate_content(
                model=model,
                contents=role_prompt,
            )
            break  # Exit the loop if the request is successful
        except genai.errors.ClientError as e:
            if e.code == 429:
                print("The search for the retry delay:")
                print(e)
                try:
                    str_e = str(e)
                    retry_delay = None
                    for i in range(len(str_e)):
                        if not str_e[len(str_e)-7+i :-6 + i].isdigit():
                            retry_delay = int(str_e[len(str_e)-7+i:-6 + i])
                            break
                    print(f"Quota exceeded. Retrying in {retry_delay} seconds...")
                except Exception:
                    return f"Error: Quota exceeded and unable to parse retry delay. {e}"

                time.sleep(retry_delay)
            else:
                return f"Error: Quota exceeded {e}"

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
    if model_name in config.MODEL_OWNER["openai"]:
        return get_image_description_openai(image_path, text_prompt, model_name)
    else:
        return get_image_description_gemini(image_path, text_prompt, model_name)


def get_image_description_openai(
        image_path: str,
        text_prompt: str = "Describe this image in detail.",
        model_name: str = config.DEFAULT_VISION_MODEL,
) -> str:
    """
    Sends an image and a text prompt to an OpenAI vision model and returns the description.
    Uses default safety settings provided by the API.

    Args:
        image_path: Path to the image file.
        text_prompt: The text instruction for the LLM (e.g., "Describe this image.").
        model_name: The specific OpenAI vision model to use.
    Returns:
        The textual description generated by the model, or an error message.
    """

    if not os.path.exists(image_path):
        return f"Error: Image file not found at {image_path}"

    if DEBUG:
        print(f"{BLUE}--- Invoking Vision Model: {model_name} ---{RESET}")
        # print(f"Image Path: {image_path}")
        # print(f"Text Prompt: {text_prompt}")


    # --- Image Processing and Encoding ---
    try:
        # Load the image using Pillow
        img = Image.open(image_path)

        output_format = "PNG"
        mime_type = f"image/{output_format.lower()}"

        # Optional: Convert to RGB if needed (often good practice)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Create an in-memory bytes buffer
        buffered = io.BytesIO()
        img.save(buffered, format=output_format)
        img_byte_data = buffered.getvalue()

        # Encode the image bytes to base64
        base64_image = base64.b64encode(img_byte_data).decode('utf-8')

    except FileNotFoundError:
         return f"Error: Image file not found at {image_path}"
    except Exception as img_err:
        return f"Error: Could not open or process image file: {img_err}"

    # --- Prepare API Payload ---
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": text_prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        # Use f-string to create the data URI
                        "url": f"data:{mime_type};base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    # --- API Call ---
    try:
        openai.api_key = OPENAI_KEY
        response = openai.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=300
        )

        # Extract the response content
        return response.choices[0].message.content

    except Exception as e:
        error_msg = f"Error during OpenAI API call: {type(e).__name__} - {e}"
        if DEBUG:
            print(f"{PINK}{error_msg}{RESET}")
        return error_msg





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

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

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

if __name__ == "__main__":
    # Example usage
    role = "You are a helpful assistant.\n"
    question = "What is the meaning of life?\n"
    prompt = ("Give a funny answer to this question: {dynamic_content} \n"
              "Answer in 10 words or less.\n"
              "Give the answer in an xml format. Example:\n"
              "<answer>42</answer>\n"
              "Then give a next question that can be answered in a funny way.\n"
              "Please provide the answer in an xml format as well. Example:\n"
              "<question>What is Jaguar spelled backwards?</question>\n"
              )

    evaluation_string = "\n\nFirst Question: " + question + "\n"
    for model_name in config.llm_names.keys():
        evaluation_string += f"--------------{model_name}----------------\n"
        import agent_manager
        agent_manager.set_model(model_name)
        response = basic_prompt(prompt.format(dynamic_content=question), role)

        try:
            answer = response.split("<answer>")[1].split("</answer>")[0]
            evaluation_string += f"Answer: {answer}\n"
        except Exception as e:
            pass

        try:
            question = response.split("<question>")[1].split("</question>")[0]
            evaluation_string += f"Next Question: {question}\n"
        except Exception as e:
            question = "What is the capital of France?"

        evaluation_string += f"\nFull Response: {response}\n\n"

    print(evaluation_string)







