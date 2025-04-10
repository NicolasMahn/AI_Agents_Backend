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
    json_pattern = re.compile(r'(\w+)=(\{.*?\}|\[.*?\])', re.DOTALL)
    attr_matches = json_pattern.findall(attr_str)
    for attr_match in attr_matches:
        key, json_value = attr_match
        try:
            json_obj = json.loads(json_value)  # Parse JSON part
            xml_attr_value = html.escape(json.dumps(json_obj))  # Convert back to escaped string
            attr_str = attr_str.replace(f'{key}={json_value}', f'{key}="{xml_attr_value}"')
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

    errors = []
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
                errors.append(f"Error parsing normal tag: {match}\n\n Error: {e}")
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
                errors.append(f"Error parsing self-closing tag: {match}\n\n Error: {e}")

    return elements, errors

def add_command(name: str, attributes: dict = None, text: str = None) -> ET.Element:
    """Creates an XML element representing a command."""
    if attributes is None:
        command = ET.Element(name)
    else:
        command = ET.Element(name, attrib=attributes)
    if text:
        command.text = text
    return command


if __name__ == "__main__":
    test_commands = [
        '<command name="plan" version="1.0" tag="test">This is a test command</command>',
        '<command name="plan" version="1.0" attr={"key": "value"} tag="test">This is a test command</command>',
        '<command name="plan" tag="test" attr=[{"key": "value1"}, {"key": "value2"}] version="1.0">This is a test command</command>',
        '<command name="plan" tag=["test"] attr=["test1", "test2"] version="1.0">This is a test command</command>',
        '''
<code tag="correlation_dashboard" version="1.1" requirements=["pandas", "numpy", "plotly", "dash"] frontend="True" previous_output={"tag": "load_clean_smartwatch_data", "version": "1.0"}>
<![CDATA[
i = 5
if i < 10:
    print("i is less than 10")
else:
    print("i is 10 or more")
]]>
</code>''',
        '''
<code tag="correlation_dashboard" version="1.1" requirements=["pandas", "numpy", "plotly", "dash"] frontend="True" previous_output={"tag": "load_clean_smartwatch_data", "version": "1.0"}>
<![CDATA[
i = 5
if i < 10:
    print("i is less than 10")
else:
    print("i is 10 or more")
]]>
<code>This is a test command</code>'''
        # leads to an error because of the CDATA the first one is malformed, so it thinks all of it is one xml element
    ]

    for tc in test_commands:
        #print(tc)
        elements, errors = extract_xml_elements(tc)
        if elements:
            for elem in elements:
                print(ET.tostring(elem, encoding='unicode'))
        if errors:
            print("Errors:", errors)