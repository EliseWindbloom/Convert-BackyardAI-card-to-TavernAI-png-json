"""
Usage:
pip install aichar
python faraday2tavern.py <file_path>

exports both as json compatible with TavernAI and
character card compatible with TavernAI
"""

import os
import sys
import json
# https://github.com/Hukasx0/aichar
import aichar

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
    with open(file_path, 'rb') as file:
        content = file.read().decode('utf-8', errors='replace') + "2}"
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
    return character

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
