import argparse
import csv
import os
from typing import Tuple, Union
import re # Import regular expressions for cleaning currency

# --- Existing Function ---
def calculate_cost_per_use(
    input_token_price_per_million: float,
    output_token_price_per_million: float,
    input_tokens_per_iteration: int,
    avg_output_tokens_per_iteration: int,
    intelligence: int = -1, # Optional: for context in output
    coding_intelligence: int = -1, # Optional: for context in output
    model_name: str = "Unknown Model" # Optional: for context in output
) -> tuple[float, float, float]:
    """
    Calculates the estimated cost for a single iteration (use) of an LLM agent.

    Assumes a fixed number of input tokens are used per iteration and uses
    an average for the output tokens. Pricing is based on cost per million tokens.

    Args:
        input_token_price_per_million: Cost per 1 million input tokens for the model.
        output_token_price_per_million: Cost per 1 million output tokens for the model.
        input_tokens_per_iteration: The number of input tokens used per iteration.
        avg_output_tokens_per_iteration: The average number of output tokens
                                         generated per iteration.
        intelligence: evaluation from 0 to 100 (https://artificialanalysis.ai/leaderboards/models)
        coding_intelligence (optional): evaluation from 0 to 100 (https://artificialanalysis.ai/leaderboards/models)
        model_name (optional): The name of the LLM model for context.

    Returns:
        A tuple containing:
        - total_cost_per_iteration (float)
        - intelligence_cost_index (float)
        - coding_intelligence_cost_index (float)
    """
    # Validate inputs (basic check)
    if input_token_price_per_million < 0 or \
       output_token_price_per_million < 0 or \
       input_tokens_per_iteration < 0 or \
       avg_output_tokens_per_iteration < 0:
        raise ValueError("Token counts and prices cannot be negative.")

    # Calculate cost for input tokens
    cost_input = (input_tokens_per_iteration / 1_000_000) * input_token_price_per_million

    # Calculate cost for output tokens
    cost_output = (avg_output_tokens_per_iteration / 1_000_000) * output_token_price_per_million

    # Calculate total cost for this iteration
    total_cost_per_iteration = cost_input + cost_output

    # Avoid division by zero if total cost is zero
    if total_cost_per_iteration > 0:
        if intelligence != -1:
            intelligence_cost_index = intelligence / total_cost_per_iteration
        else:
            intelligence_cost_index = -1.0 # Or perhaps float('inf') or None if preferred

        if coding_intelligence != -1:
            coding_intelligence_cost_index = coding_intelligence / total_cost_per_iteration
        else:
            coding_intelligence_cost_index = -1.0 # Or perhaps float('inf') or None if preferred
    else:
        intelligence_cost_index = -1.0 # Indicate not applicable or calculable
        coding_intelligence_cost_index = -1.0

    print(f"--- Cost Calculation Breakdown for {model_name} ---")
    print(f"Input Tokens per Iteration:  {input_tokens_per_iteration:,}")
    print(f"Avg Output Tokens per Iteration: {avg_output_tokens_per_iteration:,}")
    print(f"Input Price per 1M Tokens:  ${input_token_price_per_million:.2f}")
    print(f"Output Price per 1M Tokens: ${output_token_price_per_million:.2f}")
    print("-" * 30)
    # Use a small epsilon to handle potential floating point inaccuracies near zero
    print(f"Input Cost per Iteration:   ${cost_input:.6f}") # Increased precision for small costs
    print(f"Output Cost per Iteration:  ${cost_output:.6f}") # Increased precision for small costs
    print(f"Total Estimated Cost per Use: ${total_cost_per_iteration:.6f}")
    print("-" * 30)
    if intelligence != -1:
        # Check if index is calculable before printing
        if total_cost_per_iteration > 0:
             print(f"Intelligence Cost Index:   {intelligence_cost_index:.2f}")
        else:
             print(f"Intelligence Cost Index:   N/A (zero cost)")
    if coding_intelligence != -1:
         # Check if index is calculable before printing
        if total_cost_per_iteration > 0:
            print(f"Coding Intelligence Cost Index:   {coding_intelligence_cost_index:.2f}")
        else:
            print(f"Coding Intelligence Cost Index:   N/A (zero cost)")
    print("\n") # Add newline for better separation

    return total_cost_per_iteration, intelligence_cost_index, coding_intelligence_cost_index

# --- New Function to Fill CSV ---
def fill_llm_info(csv_filepath: str = 'llm_info.csv'):
    """
    Reads an LLM info CSV, calculates cost metrics for each model,
    and writes the updated data back to the file.

    Args:
        csv_filepath: Path to the CSV file.
    """
    print(f"--- Starting to process {csv_filepath} ---")
    if not os.path.exists(csv_filepath):
        print(f"Error: File not found at {csv_filepath}")
        return

    updated_rows = []
    fieldnames = [] # To store the header order

    try:
        with open(csv_filepath, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            if reader.fieldnames:
                 fieldnames = reader.fieldnames # Capture the header names/order
                 # Ensure the necessary columns for calculation results exist in the header
                 for col in ['Estimated Cost per use by Agent', 'Cost General Intelligence Index', 'Cost Coding Intelligence Index']:
                      if col not in fieldnames:
                           print(f"Warning: Expected column '{col}' not found in header. It will be added.")
                           fieldnames.append(col) # Add if missing
            else:
                print("Error: CSV file appears to be empty or header is missing.")
                return


            for row in reader:
                try:
                    model_nickname = row.get('Model Nickname', 'Unknown') # Use Nickname for display
                    model_name_for_calc = row.get('Model Name', model_nickname) # Use actual name if available

                    # --- Data Cleaning and Conversion ---
                    # Remove '$' and ',' before converting prices
                    price_pattern = re.compile(r'[$,]')

                    input_price_str = price_pattern.sub('', row.get('Price per 1M Input Tokens', '0') or '0')
                    output_price_str = price_pattern.sub('', row.get('Price per 1M Output Tokens', '0') or '0')
                    input_tokens = int(row.get('Max Input Tokens', '2000') or '2000')
                    output_tokens = float(row.get('Median Output Tokens', '200') or '200')

                    input_price = float(input_price_str)
                    output_price = float(output_price_str)

                    # Get intelligence scores, default to -1 if empty, invalid, or missing
                    try:
                        intelligence = int(row.get('Artificial Analysis Intelligence Index') or -1)
                        if not (0 <= intelligence <= 100): intelligence = -1 # Validate range
                    except (ValueError, TypeError):
                        intelligence = -1

                    try:
                        coding_intelligence = int(row.get('Artificial Analysis Coding Index') or -1)
                        if not (0 <= coding_intelligence <= 100): coding_intelligence = -1 # Validate range
                    except (ValueError, TypeError):
                        coding_intelligence = -1
                    # --- End Data Cleaning ---


                    # --- Calculation ---
                    total_cost, intel_index, coding_index = calculate_cost_per_use(
                        input_token_price_per_million=input_price,
                        output_token_price_per_million=output_price,
                        input_tokens_per_iteration=input_tokens,
                        avg_output_tokens_per_iteration=output_tokens,
                        intelligence=intelligence,
                        coding_intelligence=coding_intelligence,
                        model_name=model_nickname # Pass nickname for clearer print output
                    )
                    # --- End Calculation ---

                    # Update the row dictionary with calculated values
                    # Format results for CSV consistency if desired, e.g., fixed decimal places
                    row['Estimated Cost per use by Agent'] = f"{total_cost:.6f}" # Store with precision
                    row['Cost General Intelligence Index'] = f"{intel_index:.2f}" if intel_index != -1.0 else '' # Store index or empty
                    row['Cost Coding Intelligence Index'] = f"{coding_index:.2f}" if coding_index != -1.0 else '' # Store index or empty

                    updated_rows.append(row)

                except ValueError as e:
                    print(f"Skipping row due to data conversion error for model '{model_nickname}': {e}")
                    # Append the original row if skipping calculation, or modify as needed
                    updated_rows.append(row)
                except Exception as e:
                     print(f"An unexpected error occurred processing row for model '{model_nickname}': {e}")
                     updated_rows.append(row) # Keep original row data on error

        # Write the updated data back to the *same* file
        with open(csv_filepath, mode='w', newline='', encoding='utf-8') as outfile:
            # Use the captured fieldnames to maintain column order and include added ones
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

        print(f"--- Finished processing {csv_filepath}. File has been updated. ---")

    except FileNotFoundError:
        print(f"Error: File not found at {csv_filepath}")
    except Exception as e:
        print(f"An error occurred during file processing: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":

    # --- Command Line Interface (Optional) ---
    parser = argparse.ArgumentParser(description="Calculate LLM API cost per use or fill a CSV file with calculations.")
    parser.add_argument("--input-price", type=float, required=False, help="Price per 1 Million input tokens (for single calculation).")
    parser.add_argument("--output-price", type=float, required=False, help="Price per 1 Million output tokens (for single calculation).")
    parser.add_argument("--input-tokens", type=int, required=False, help="Input tokens per iteration (used for single calculation OR overrides default for CSV fill).")
    parser.add_argument("--output-tokens", type=int, required=False, help="Average output tokens per iteration (used for single calculation OR overrides default for CSV fill).")
    parser.add_argument("--model", type=str, default="CLI Model", help="Name of the model for context (for single calculation).")
    parser.add_argument("--intelligence", type=int, default=-1, help="Intelligence level of the model (for single calculation).")
    parser.add_argument("--coding-intelligence", type=int, default=-1, help="Coding intelligence level of the model (for single calculation).")
    parser.add_argument("--fill-csv", action='store_true', help="Run the process to fill the llm_info.csv file instead of a single calculation.")
    parser.add_argument("--csv-path", type=str, default="llm_info.csv", help="Path to the CSV file to process.")


    args = parser.parse_args()

    # Decide whether to run single calculation or fill CSV
    if args.fill_csv:
         # Use CLI token counts if provided, otherwise use defaults in fill_llm_info
        csv_input_tokens = args.input_tokens if args.input_tokens is not None else 2000
        csv_output_tokens = args.output_tokens if args.output_tokens is not None else 500
        fill_llm_info(csv_filepath=args.csv_path, input_tokens=csv_input_tokens, output_tokens=csv_output_tokens)

    # Check if enough args for single calculation *and* fill_csv is not set
    elif all([args.input_price is not None, args.output_price is not None, args.input_tokens is not None, args.output_tokens is not None]):
        print("\n--- Calculating based on Command Line Arguments ---")
        try:
             calculate_cost_per_use(
                input_token_price_per_million=args.input_price,
                output_token_price_per_million=args.output_price,
                input_tokens_per_iteration=args.input_tokens,
                avg_output_tokens_per_iteration=args.output_tokens, # Use the provided output tokens
                intelligence=args.intelligence,
                coding_intelligence=args.coding_intelligence,
                model_name=args.model
            )
        except ValueError as e:
            print(f"Error processing command line arguments: {e}")
    else:
        # Default behavior if no specific action is requested via CLI args
        # Could print help, or default to filling the CSV, or do nothing.
        # Let's default to filling the CSV if no other action is specified.
        print("No specific action requested via CLI arguments. Defaulting to filling the CSV.")
        fill_llm_info(csv_filepath=args.csv_path) # Use default tokens