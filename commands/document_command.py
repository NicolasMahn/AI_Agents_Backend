import os
import xml.etree.ElementTree as ET
import pandas as pd
import json
import yaml
from io import StringIO
import pprint # For potentially pretty-printing json/yaml

from PIL import Image
# Import pdfminer for PDF text extraction
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError

from config import max_generic_content_length
from llm_functions import count_context_length
from llm_functions.llm_api_wrapper import get_image_description_gemini


def truncate_text_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncates text to approximately fit within the max_token limit.
    Relies on the count_context_length function.
    Note: This is approximate and might slightly exceed the limit
          depending on the tokenizer's behavior. A more robust implementation
          might iteratively remove words/sentences.
    """
    if count_context_length(text) <= max_tokens:
        return text

    # Simple truncation based on characters as a proxy, assuming tokens correlate
    # A better approach might involve splitting by words/sentences and counting
    avg_chars_per_token = len(text) / count_context_length(text) if count_context_length(text) > 0 else 5 # Estimate
    estimated_chars = int(max_tokens * avg_chars_per_token * 0.95) # Target slightly lower

    truncated = text[:estimated_chars]

    # Refine by removing last partial word/sentence if needed
    truncated = truncated.rsplit(' ', 1)[0] # Remove last partial word
    truncated += "\n\n[... Content truncated to fit token limit ...]"

    # Final check (optional, could be slow)
    # while count_context_length(truncated) > max_tokens:
    #    truncated = truncated.rsplit(' ', 1)[0]
    #    if ' ' not in truncated: break # Avoid infinite loop

    return truncated


def get_document_content(filepath: str) -> str:
    # Split the path into root and extension
    _, extension = os.path.splitext(filepath)

    # The extension includes the leading dot (e.g., '.pdf')
    # You might want to remove the dot and convert to lowercase
    file_extension = extension.lower().lstrip('.') if extension else None

    filepath = os.path.abspath(filepath)
    report_parts = []
    try:

        # Check if file exists before proceeding
        if not os.path.isfile(filepath):
             return f"Error: File not found at path: {filepath}"

        full_file_path = os.path.abspath(filepath)
        file_size = os.path.getsize(filepath)
        _, extension = os.path.splitext(filepath)
        file_extension = extension.lower().lstrip('.') if extension else None

        report_parts.append(f"# Document Report: `{os.path.basename(filepath)}`")
        #report_parts.append(f"**Full Path:** `{full_file_path}`")
        report_parts.append(f"**Size:** {file_size} bytes")
        report_parts.append(f"**Detected Type:** {file_extension or 'Unknown'}")
        #report_parts.append("---") # Separator

        # --- PDF Handling ---
        if file_extension == 'pdf':
            report_parts.append("## PDF Analysis")
            try:
                # Extract text using pdfminer.six
                # Note: This can be slow for very large PDFs.
                # Consider adding a timeout or page limit if necessary.
                extracted_text = extract_text(filepath)
                text_preview = truncate_text_to_tokens(extracted_text, max_generic_content_length - 50)  # Leave margin for headers

                # Simple page count attempt (can be inaccurate or fail for complex PDFs)
                # A more robust page count might require PyPDF2 or another library
                page_count_info = "(Page count not available with pdfminer.six)"
                try:
                    import PyPDF2  # Optional: Try PyPDF2 just for page count
                    with open(filepath, 'rb') as pf:
                        reader = PyPDF2.PdfReader(pf, strict=False)  # strict=False for leniency
                        page_count_info = f"**Page Count:** {len(reader.pages)}"
                except ImportError:
                    page_count_info = "(PyPDF2 not installed for accurate page count)"
                except Exception as pdf_err:
                    page_count_info = f"(Could not determine page count: {pdf_err})"

                report_parts.append(page_count_info)
                report_parts.append("### Initial Content Preview:")
                report_parts.append(f"```\n{text_preview}\n```")

            except PDFSyntaxError:
                report_parts.append("**Error:** Could not parse PDF. File might be corrupted or password-protected.")
            except Exception as e:
                report_parts.append(f"**Error processing PDF:** {e}")

        # --- Text Handling ---
        elif file_extension in ['txt', 'md']:
            report_parts.append("## Text File Analysis")
            try:
                line_count = 0
                content_preview = ""
                # Try common encodings
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
                file_encoding = None
                for enc in encodings_to_try:
                    try:
                        with open(filepath, 'r', encoding=enc) as f:
                            for line in f:
                                line_count += 1
                                # Check token count before adding more text
                                potential_text = content_preview + line
                                if count_context_length(potential_text) < (max_generic_content_length - 100):  # Leave margin
                                    content_preview = potential_text
                                else:
                                    content_preview += "\n[... Reached token limit during preview generation ...]"
                                    break  # Stop reading lines
                        file_encoding = enc  # Successfully read with this encoding
                        break  # Stop trying encodings
                    except UnicodeDecodeError:
                        continue  # Try next encoding
                    except Exception as read_err:  # Catch other read errors
                        raise read_err  # Re-raise other errors

                if file_encoding is None:
                    report_parts.append(
                        "**Error:** Could not decode file using common encodings (utf-8, latin-1, cp1252).")
                else:
                    report_parts.append(f"**Encoding:** `{file_encoding}` (detected)")
                    report_parts.append(f"**Line Count:** {line_count}")
                    report_parts.append("### Initial Content Preview:")
                    # Final trim just in case
                    final_preview = truncate_text_to_tokens(content_preview, max_generic_content_length - count_context_length(
                        "\n".join(report_parts)) - 20)
                    report_parts.append(f"```\n{final_preview}\n```")

            except Exception as e:
                report_parts.append(f"**Error reading text file:** {e}")

        # --- Tabular Data Handling ---
        elif file_extension in ['csv', 'xls', 'xlsx']:
            report_parts.append("## Tabular Data Analysis")
            try:
                if file_extension == 'csv':
                    df = pd.read_csv(filepath)
                else:  # xls, xlsx
                    df = pd.read_excel(filepath)

                report_parts.append(f"**Shape:** {df.shape[0]} rows, {df.shape[1]} columns")

                # Get Schema (df.info)
                schema_buffer = StringIO()
                df.info(buf=schema_buffer)
                schema_info = schema_buffer.getvalue()

                # Get Head Preview
                head_preview = df.head().to_markdown(index=False)

                # Combine and check token limit
                schema_report = "### Schema (Column Types & Non-Null Counts):\n```\n" + schema_info + "\n```"
                head_report = "### Data Preview (First 5 Rows):\n" + head_preview

                # Prioritize schema, then add head if space allows
                temp_report = "\n".join(report_parts) + "\n" + schema_report
                schema_tokens = count_context_length(temp_report)

                if schema_tokens < max_generic_content_length:
                    report_parts.append(schema_report)
                    remaining_tokens = max_generic_content_length - schema_tokens
                    if count_context_length(head_report) < remaining_tokens:
                        report_parts.append(head_report)
                    else:
                        # Try showing fewer rows or just header
                        head_preview_short = df.head(2).to_markdown(index=False)
                        head_report_short = "### Data Preview (First 2 Rows):\n" + head_preview_short
                        if count_context_length(head_report_short) < remaining_tokens:
                            report_parts.append(head_report_short)
                        else:
                            report_parts.append("*(Data preview omitted due to token limits)*")
                else:
                    report_parts.append(
                        "*(Schema and data preview omitted due to token limits. File has many columns.)*")


            except ImportError as e:
                report_parts.append("**Error:** Missing required library. Need `pandas` and `openpyxl` (for Excel).")
                print("Error:", e)
            except Exception as e:
                report_parts.append(f"**Error processing tabular file:** {e}")

        # --- Structured Data Handling ---
        elif file_extension in ['json', 'xml', 'yaml', 'yml']:
            report_parts.append("## Structured Data Analysis")
            preview_chars = 2000  # Read initial characters as proxy for token limit
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content_start = f.read(preview_chars)

                truncated = len(content_start) == preview_chars and file_size > preview_chars
                report_parts.append(f"**File Size:** {file_size} bytes.")
                report_parts.append("### Initial Content Preview:")

                # Try parsing for structure validation / pretty print (optional)
                parsed_structure_report = None
                try:
                    if file_extension == 'json':
                        data = json.loads(
                            content_start if not truncated else content_start + ' "..."}')  # Attempt valid end
                        # Limit depth/length of pretty print if needed
                        parsed_structure_report = f"```json\n{json.dumps(data, indent=2, ensure_ascii=False)[:preview_chars]}\n```"
                    elif file_extension == 'xml':
                        # Basic XML structure preview is hard without full parse
                        # Just show raw text for XML preview
                        pass  # Will fall through to raw text preview
                    elif file_extension in ['yaml', 'yml']:
                        # Ensure safe loading
                        data = yaml.safe_load(content_start)
                        # Limit depth/length of pretty print if needed
                        parsed_structure_report = f"```yaml\n{yaml.dump(data, indent=2, allow_unicode=True, default_flow_style=False)[:preview_chars]}\n```"

                except Exception as parse_error:
                    # Parsing failed (likely due to truncation), just show raw
                    parsed_structure_report = f"*(Could not parse truncated preview: {parse_error})*\n```\n{content_start}\n```"

                if parsed_structure_report:
                    report_parts.append(parsed_structure_report)
                else:  # Default for XML or if parsing failed/skipped
                    report_parts.append(f"```\n{content_start}\n```")

                if truncated:
                    report_parts.append("\n[... File content truncated for preview ...]")

            except Exception as e:
                report_parts.append(f"**Error processing structured file:** {e}")

        # --- Image Handling ---
        elif file_extension in ['jpg', 'jpeg', 'png', 'gif']:
            report_parts.append("## Image File Analysis")

            try:
                # Optional: Basic validation with Pillow before sending to LLM
                img = Image.open(filepath)
                img.verify()  # Verify basic integrity
                img_dims = img.size
                img_mode = img.mode
                img.close()  # Close after verification/getting info
                report_parts.append(f"**Dimensions:** {img_dims[0]}x{img_dims[1]} pixels")
                report_parts.append(f"**Mode:** {img_mode}")

                # Define the prompt for the vision model
                image_prompt = "Describe this image in detail, focusing on the main subject, setting, and any notable features or text present."

                # Calculate remaining token budget for the description
                current_report_tokens = count_context_length("\n".join(report_parts))
                description_token_budget = max(100,
                                               max_generic_content_length - current_report_tokens - 50)  # Ensure positive budget, leave margin

                report_parts.append("### AI Generated Description:")
                # Call the new vision function
                description = get_image_description_gemini(
                    image_path=filepath,
                    text_prompt=image_prompt
                    # model_name="gemini-pro-vision" # Or use DEFAULT_VISION_MODEL
                )

                # Check for errors returned by the function
                if description.startswith("Error:"):
                    report_parts.append(f"_{description}_")
                else:
                    # Truncate the description if it's too long for the remaining budget
                    truncated_description = truncate_text_to_tokens(description, description_token_budget)
                    report_parts.append(truncated_description)

            except FileNotFoundError:
                report_parts.append("**Error:** Image file seems to have disappeared after initial check.")
            except ImportError:
                # Should be caught by VISION_FUNCTION_AVAILABLE, but as fallback
                report_parts.append(
                    "_Image description skipped: Required libraries (e.g., Pillow, google-generativeai) might be missing._")
            except Exception as e:
                report_parts.append(f"**Error processing image for AI description:** {e}")

        # --- Else Case (Unsupported) ---
        else:
            report_parts.append("## Unsupported File Type")
            if file_extension:
                report_parts.append(f"Detailed analysis for file type '.{file_extension}' is not currently supported.")
            else:
                report_parts.append("File extension is missing or unknown. Cannot perform detailed analysis.")
            report_parts.append("Basic file information provided above.")


    except FileNotFoundError:
        return f"Error: File not found at the specified path: {filepath}"
    except Exception as e:
        # Catch-all for unexpected errors during setup or file handling
        return f"An unexpected error occurred while processing the file: {e}\nPath: {filepath}"

        # --- Final Report Assembly and Token Check ---
    final_report = "\n".join(report_parts)

    # Check final token count and truncate if necessary (though individual sections tried to stay within limits)
    if count_context_length(final_report) > max_generic_content_length:
        # If the report is still too long, aggressively truncate the largest text block (usually content preview)
        # This is a fallback; ideally, the section-specific logic prevents this.
        # For simplicity here, we'll just truncate the whole report string.
        # A better strategy would identify the preview sections and shorten them first.
        final_report = truncate_text_to_tokens(final_report, max_generic_content_length)
        # Ensure a note about truncation is present if not added by truncate_text_to_tokens
        if "[... Content truncated" not in final_report:
            final_report += "\n\n[... Report truncated to fit token limit ...]"

    return final_report


def execute_document_command(command, agent):

    if isinstance(command, str):
        filepath = command
    elif "filepath" in command.attrib:
        filepath = command.attrib["filepath"]
    else:
        return "Error: Document could not be retrieved. Filepath not provided."

    final_report = get_document_content(filepath)
    agent.add_context_data(f"Document Analysis Results of {os.path.basename(filepath)}", final_report,
                           "Document analysis results", importance=3)

    return "Document analysis executed successfully."




if __name__ == "__main__":
    root_folder = "C:\\Users\\nicol\\PycharmProjects\\AI_Agents_Backend\\test_docs"

    for doc in os.listdir(root_folder):
        final_report = get_document_content(os.path.join(root_folder, doc))
        print(final_report)

        input("Press Enter to continue...")
