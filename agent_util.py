import html
import re
import xml.etree.ElementTree as ET

import pandas as pd
import yaml

from config import DEBUG


def find_commands_in_string(text: str):
    return extract_xml_elements(text)

import json

def convert_json_attributes(attr_str: str) -> str:
    """Converts JSON-like attributes to properly formatted XML attributes."""
    if not attr_str:
        return ""

    # Match key-value pairs inside attribute string
    attr_match = re.search(r'(\w+)=({.*})', attr_str)
    if attr_match:
        key, json_value = attr_match.groups()
        try:
            json_obj = json.loads(json_value)  # Parse JSON part
            xml_attr_value = html.escape(json.dumps(json_obj))  # Convert back to escaped string
            return f' {key}="{xml_attr_value}"'  # Ensure proper XML formatting
        except json.JSONDecodeError:
            pass  # Fall back if JSON parsing fails

    return attr_str  # Return unchanged if no JSON detected

def assign_default_value_to_attrs(attr_str: str) -> str:
    """Assigns a default value to attributes without values."""
    if not attr_str:
        return ""

    # Find attributes without values and assign them a default value
    attr_str = re.sub(r'(\w+)(\s|$)', r'\1="true"\2', attr_str)
    return attr_str

def extract_xml_elements(text: str):
    xml_pattern = re.compile(r'<(\w+)(\s+[^<>]*)?>(.*?)</\1>|<(\w+)(\s+[^<>]*)?/>', re.DOTALL)
    matches = xml_pattern.findall(text)

    elements = []
    for match in matches:
        if DEBUG:
            print("Match found:", match)  # Debugging output

        if match[0]:  # Normal tag
            try:
                cleaned_attributes = convert_json_attributes(match[1]) if match[1] else ""
                cleaned_attributes = assign_default_value_to_attrs(cleaned_attributes)
                element_str = f'<{match[0]}{cleaned_attributes}>{match[2]}</{match[0]}>'
                if DEBUG:
                    print("Attempting to parse:", element_str)  # Debugging output
                element = ET.fromstring(element_str)
                elements.append(element)
            except ET.ParseError as e:
                print(f"Error parsing normal tag: {e}")
        elif match[3]:  # Self-closing tag
            try:
                cleaned_attributes = convert_json_attributes(match[4]) if match[4] else ""
                cleaned_attributes = assign_default_value_to_attrs(cleaned_attributes)
                element_str = f'<{match[3]}{cleaned_attributes}/>'
                if DEBUG:
                    print("Attempting to parse self-closing:", element_str)  # Debugging output
                element = ET.fromstring(element_str)
                elements.append(element)
            except ET.ParseError as e:
                print(f"Error parsing self-closing tag: {e}")

    return elements

def add_command(name: str, attributes: dict = None, text: str = None) -> ET.Element:
    """Creates an XML element representing a command."""
    if attributes is None:
        command = ET.Element(name)
    else:
        command = ET.Element(name, attrib=attributes)
    if text:
        command.text = text
    return command


def do_basic_data_description(file_path):
    """
    Reads a file into a Pandas DataFrame and returns a basic description of the data.
    Supports CSV, JSON, XML, and YAML files.

    Parameters:
    file_path (str): Path to the data file.

    Returns:
    dict: Summary containing column info, missing values, and basic statistics.
    If the file format is not supported, it returns only the file format.
    """
    try:
        # Determine file type and read accordingly
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path)
        elif file_path.endswith(".xml"):
            tree = ET.parse(file_path)
            root = tree.getroot()
            data = []
            for child in root:
                data.append(child.attrib)
            df = pd.DataFrame(data)
        elif file_path.endswith(".yml") or file_path.endswith(".yaml"):
            with open(file_path, "r") as file:
                data = yaml.safe_load(file)
            df = pd.json_normalize(data)
        else:
            return {"file_format": file_path.split('.')[-1]}

        # Basic description
        description = {
            "Shape": df.shape,
            "Columns": list(df.columns),
            "Data Types": df.dtypes.to_dict(),
            "Missing Values": df.isnull().sum().to_dict(),
            "Summary Statistics": df.describe().to_dict()
        }

        return description

    except Exception as e:
        return {"Couldn't analyze file got error": str(e)}