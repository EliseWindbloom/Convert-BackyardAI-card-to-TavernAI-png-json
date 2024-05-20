"""
Usage:
pip install aichar
python faraday2tavern.py <file_path>

exports both as json compatible with TavernAI and
character card compatible with TavernAI
"""
# by Hukasx0, edited by EliseWindbloom

import os
import sys
import json
# https://github.com/Hukasx0/aichar
import aichar
import base64
#import re

class ContentNotFoundException(Exception):
    pass

def extract_content(input_str, start_delimiter, end_delimiter):
    start_pos = input_str.find(start_delimiter) + len(start_delimiter)
    end_pos = input_str.find(end_delimiter, start_pos)
    if end_pos == -1:
        raise ContentNotFoundException(f"Incorrect Faraday character card")
    return input_str[start_pos:end_pos]

def process_special_tokens(input_str):
    tokens = ["{character}", "{user}"]
    input_str = input_str.replace("{character}", "{{char}}")
    input_str = input_str.replace("\\n", "\n")
    input_str = input_str.replace('\\\"', '"')
    for token in tokens:
        input_str = input_str.replace(token, f"{{{{{token[1:-1]}}}}}")
    return input_str

def get_character(file_path):
    #with open(file_path, 'rb') as file:
    #    content = file.read().decode('utf-8', errors='replace') + "2}"
    content = get_png_extra_base64_data(file_path)
    #print(content)

    char_name = extract_content(content, 'aiName":"', '",')
    char_persona = extract_content(content, 'aiPersona":"', '","basePrompt')
    char_greeting = extract_content(content, ',"firstMessage":"', '","grammar"')
    example_dialogue = extract_content(content, ',"customDialogue":"', '","firstMessage":')

    char_persona = process_special_tokens(char_persona)
    example_dialogue = process_special_tokens(example_dialogue)
    char_greeting = process_special_tokens(char_greeting)

    character = aichar.create_character(
        name=char_name,
        summary=char_persona,
        personality="",#char_persona,
        scenario="",
        greeting_message=char_greeting,
        example_messages=example_dialogue,
        image_path=file_path
    )
    #print(character.image_path)
    return character

def my_base64(vCode, bEncode=True, bUrl=False):
    if bEncode:
        encoded_data = base64.b64encode(vCode)
        if not bUrl:
            return encoded_data.decode('utf-8')
        else:
            return encoded_data.decode('utf-8').replace("+", "-").replace("/", "_").replace("\n", "")
    else:
        if bUrl:
            vCode = vCode.replace("-", "+").replace("_", "/")
        return base64.b64decode(vCode)

def get_png_extra_base64_data(png_file_path):
    """
    Extracts the extra Base64 data from a PNG file and returns it as a UTF-8 string.
    
    Args:
        png_file_path (str): The path to the PNG file.
        
    Returns:
        str: The decoded extra Base64 data from the PNG file, or None if not found.
    """
    try:
        with open(png_file_path, 'rb') as f:
            png_file_content = f.read()
    except IOError:
        print("Error: Unable to open the PNG file.")
        return None
    
    try:
        png_file_string = png_file_content.decode('latin-1')
    except UnicodeDecodeError:
        print("Error: Unable to decode the PNG file content.")
        return None
    
    ascii_marker = "ASCII"
    marker_pos = png_file_string.find(ascii_marker)
    
    if (marker_pos == -1):
        print("Error: ASCII marker not found.")
        return None
    
    start_pos = marker_pos + len(ascii_marker)
    end_pos = png_file_string.find("Q==", start_pos)
    
    if (end_pos == -1):
        print("Error: Ending 'Q==' not found.")
        return None
    
    base64_data = png_file_string[start_pos:end_pos + 3]
    clean_base64_data = ''.join(char for char in base64_data if char.isalnum() or char in '+/=')
    
    try:
        decoded_data = my_base64(clean_base64_data, False).decode('utf-8', errors='replace') + "2}"
    except Exception as e:
        print(f"Error: Decoding base64 data failed. {str(e)}")
        return None
    
    return decoded_data

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <file_path>")
        sys.exit(1)

    png_file_path = sys.argv[1]
    base_name, _ = os.path.splitext(os.path.basename(png_file_path))

    try:
        character = get_character(png_file_path)
        character.export_neutral_json_file(base_name+".json")
        character.export_neutral_card_file(base_name+".tavern.png")

        print(f"\n{character.data_summary}\n")
        print(f"Exported in .json format as {base_name}.json")
        print(f"Exported in .png character card format as {base_name}.tavern.png")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
