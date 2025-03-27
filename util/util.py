import os
import pickle
import shutil
import urllib.parse
import json
import re
import xml.etree.ElementTree as ET

def ensure_directory_exists(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)

def decode_url_str(url_str: str):
    return urllib.parse.unquote(url_str)

def encode_url_str(url_str: str):
    return urllib.parse.quote(url_str)

def delete_file(file_path: str):
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
    pass

def load_json(file_path: str):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def save_json(file_path: str, data):
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def load_pickle(file_path: str):
    with open(file_path, "rb") as f:
        data = pickle.load(f)
    return data

def save_pickle(file_path: str, data):
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, "wb") as f:
        pickle.dump(data, f)

def save_file(file_path: str, contents: str):
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, "w") as file:
        file.write(contents)
    return file_path

def save_text(file_path: str, text: str):
    if not file_path.endswith(".txt"):
        file_path += ".txt"
    with open(file_path, "w") as f:
        f.write(text)
    pass

def load_text(file_path: str):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        text = f.read()
    return text

def get_readable_document_paths(directory: str):
    documents = []
    for file in os.listdir(directory):
        if file.endswith(".txt") or file.endswith(".json") or file.endswith(".xml") or file.endswith(".csv") \
            or file.endswith(".py") or file.endswith(".pickle") or file.endswith(".pkl"):
            documents.append(f"{directory}/{file}")

def delete_directory_with_content(directory: str):
    try:
        shutil.rmtree(directory)
    except Exception as e:
        print(f"Error deleting directory: {str(e)}")
    pass
