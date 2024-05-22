# Script By Elise Windbloom
# Special thanks to Hukasx0 for faraday2tavern.py eariler alternate version
# Concepts of this based on html/js character editor by zoltanai: https://zoltanai.github.io/character-editor/
# This was rebuild from stratch in part to fix conversion errors after faraday changed to base64 format for embedded data

import base64
import zlib
from struct import pack, unpack
import json
import time
import os
import sys

class PngError(Exception):
    pass

class PngMissingCharacterError(PngError):
    pass

class PngInvalidCharacterError(PngError):
    pass

class Png:
    @staticmethod
    def read_chunks(data):
        pos = 8  # Skip the signature
        chunks = []
        while pos < len(data):
            length = unpack(">I", data[pos:pos + 4])[0]
            chunk_type = data[pos + 4:pos + 8].decode('ascii')
            chunk_data = data[pos + 8:pos + 8 + length]
            crc = unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
            chunks.append({'type': chunk_type, 'data': chunk_data, 'crc': crc})
            pos += 12 + length
        return chunks

    @staticmethod
    def decode_text(data):
        keyword, text = data.split(b'\x00', 1)
        return {'keyword': keyword.decode('latin-1'), 'text': text.decode('latin-1')}

    @staticmethod
    def encode_text(keyword, text):
        return keyword.encode('latin-1') + b'\x00' + text.encode('latin-1')

    @staticmethod
    def encode_chunks(chunks):
        data = b'\x89PNG\r\n\x1a\n'  # PNG signature
        for chunk in chunks:
            length = pack(">I", len(chunk['data']))
            chunk_type = chunk['type'].encode('ascii')
            chunk_data = chunk['data']
            crc = pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xffffffff)
            data += length + chunk_type + chunk_data + crc
        return data

    @staticmethod
    def parse(array_buffer):
        chunks = Png.read_chunks(array_buffer)

        text_chunks = [Png.decode_text(c['data']) for c in chunks if c['type'] == 'tEXt']
        if not text_chunks:
            raise PngMissingCharacterError('No PNG text fields found in file')

        chara = next((t for t in text_chunks if t['keyword'] == 'chara'), None)
        if chara is None:
            raise PngMissingCharacterError('No PNG text field named "chara" found in file')

        try:
            return base64.b64decode(chara['text']).decode('utf-8')
        except Exception as e:
            raise PngInvalidCharacterError('Unable to parse "chara" field as base64', cause=e)

    @staticmethod
    def generate(array_buffer, json_data):
        chunks = Png.read_chunks(array_buffer)
        chunks = [c for c in chunks if c['type'] != 'tEXt']

        chara_text = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        chara_chunk = {'type': 'tEXt', 'data': Png.encode_text('chara', chara_text)}
        chunks.insert(-1, chara_chunk)

        return Png.encode_chunks(chunks)
    
def get_faraday_png_extra_base64_data(png_file_path):
    #This function is only for Faraday PNGS! use the other functions for normal tavern pngs
    #Extracts the extra Base64 data from a PNG file and returns it as a formatted JSON string.
    #Args:
    #    png_file_path (str): The path to the PNG file.
    #Returns:
    #    str: The decoded and formatted extra Base64 data from the PNG file, or None if not found.

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
    
    if marker_pos == -1:
        print("Error: ASCII marker not found.")
        return None
    
    start_pos = marker_pos + len(ascii_marker)
    end_pos = png_file_string.find("Q==", start_pos)
    
    if end_pos == -1:
        print("Error: Ending 'Q==' not found.")
        return None
    
    base64_data = png_file_string[start_pos:end_pos + 3]
    clean_base64_data = ''.join(char for char in base64_data if char.isalnum() or char in '+/=')
    
    # Decoding Base64 data
    try:
        vCode = clean_base64_data.replace("-", "+").replace("_", "/")
        decoded_bytes = base64.b64decode(vCode)
        decoded_string = decoded_bytes.decode('utf-8', errors='replace')
        
        # Attempt to find and remove extraneous characters after the JSON data
        json_start = decoded_string.find('{')
        json_end = decoded_string.rfind('}') + 1
        
        if json_start == -1 or json_end == -1:
            print("Error: JSON object boundaries not found.")
            return None
        
        json_string = decoded_string[json_start:json_end]
        
        # Attempt to load the string as JSON and pretty-print it
        try:
            json_data = json.loads(json_string)
            formatted_json = json.dumps(json_data, indent=4)
            return formatted_json
        except json.JSONDecodeError as e:
            print(f"Error: JSON decoding failed. {str(e)}")
            return None
    
    except Exception as e:
        print(f"Error: Decoding base64 data failed. {str(e)}")
        return None

def convert_faraday_png_to_tavern_data(faraday_png_file_path):
    #Function for Faraday data ONLY!
    #This loads the faraday png's embedded data to a variable, then converts it to tarven data 
    json_string = get_faraday_png_extra_base64_data(faraday_png_file_path)
    
    if not json_string:
        print("Error: Unable to extract JSON data.")
        return
    
    try:
        json_data = json.loads(json_string)
        
        ai_display_name = json_data.get('character', {}).get('aiDisplayName', 'N/A')
        ai_name = json_data.get('character', {}).get('aiName', 'N/A')
        ai_persona = json_data.get('character', {}).get('aiPersona', 'N/A')
        custom_dialogue = json_data.get('character', {}).get('customDialogue', 'N/A')
        first_message = json_data.get('character', {}).get('firstMessage', 'N/A')
        scenario = json_data.get('character', {}).get('scenario', 'N/A')
        
        #print("==AI Display Name:", ai_display_name)
        #print("==AI Name:", ai_name)
        #print("==AI Persona:", ai_persona)
        #print("==Custom Dialogue:", custom_dialogue)#example text
        #print("==First Message:", first_message)
        #print("==Scenario:", scenario)

        #format as tavern data and returns
        tavern_extracted_text = create_new_data(ai_name, "", ai_persona, scenario, first_message, custom_dialogue)
        return tavern_extracted_text
    
    except json.JSONDecodeError as e:
        print(f"Error: JSON decoding failed. {str(e)}")


def load_png(filename):
    # For extracting the embedded tavern data from a png containing embedded tavern data
    with open(filename, "rb") as f:
        data = f.read()
    try:
        extracted_text = Png.parse(data)
        return extracted_text
    except PngError as e:
        print(f"Error reading {filename}: {e}")
        return None

def save_png(extracted_text, source_filename, output_filename):
    # For saving a png with tavern data embedded into it
    with open(source_filename, "rb") as f:
        source_data = f.read()
    json_data = json.dumps(extracted_text, indent=4)
    output_data = Png.generate(source_data, json_data)
    with open(output_filename, "wb") as f:
        f.write(output_data)

def save_json(json_filename, json_data):
    # Write tavern data to JSON file
    # use json.loads(extracted_text) to get it formatted correctly for this function
    with open(json_filename, "w") as json_file:
        json.dump(json_data, json_file, indent=4)  # `indent` parameter formats the JSON data with indentation

def create_new_data(name, description="A bright and cheerful world", personality="Friendly and helpful", scenario="", first_mes="Hello, how can I assist you today?", mes_example="{{user}}: Hi\n{{char}}: Hello!", return_as_json_data=False):
    # For creating completely new tavern data from scratch
    description = description.replace("{character}", "{{char}}")
    description = description.replace("{user}", "{{user}}")
    personality = personality.replace("{character}", "{{char}}")
    personality = personality.replace("{user}", "{{user}}")
    scenario = scenario.replace("{character}", "{{char}}")
    scenario = scenario.replace("{user}", "{{user}}")
    first_mes = first_mes.replace("{character}", "{{char}}")
    first_mes = first_mes.replace("{user}", "{{user}}")
    mes_example = mes_example.replace("{character}", "{{char}}")
    mes_example = mes_example.replace("{user}", "{{user}}")
    json_data = {
        "name": name,
        "description": description,
        "personality": personality,
        "scenario": scenario,
        "first_mes": first_mes,
        "mes_example": mes_example,
        "metadata": {
            "version": 1,
            "created": int(time.time() * 1000),
            "modified": int(time.time() * 1000),
            "source": None,
            "tool": {
                "name": "Custom AI Character Editor",
                "version": "0.5.0",
                "url": "https://example.com/character-editor/"
            }
        }
    }
    # can format the created data to be in the "extracted_text" style 
    if return_as_json_data==False:
        extracted_text = json.dumps(json_data, indent=4)#without this, it would be the same as json_data
        return extracted_text #return as extracted_text
    else:
        return json_data #return as json_data

# Example usage
def main():
    if len(sys.argv) == 2:
        # For optional drag & drop a png file
        png_file_path = sys.argv[1]
    elif len(sys.argv) == 1:
        # If no command-line argument is provided, prompt the user for the file path
        png_file_path = input("Enter the path to the Faraday PNG file: ")
    else:
        print(f"Usage: python {sys.argv[0]} [<file_path>]")
        sys.exit(1)

    # Handling quoted paths
    if png_file_path.startswith('"') and png_file_path.endswith('"'):
        png_file_path = png_file_path[1:-1]

    # Process the PNG file path
    base_name, ext = os.path.splitext(os.path.basename(png_file_path))
    #print(f"ext=<{ext}> base_name=<{base_name}>")
    if ext.lower() != ".png":
        print("Error: Please provide a PNG file.")
        sys.exit(1)

    source_filename = png_file_path
    extracted_text = convert_faraday_png_to_tavern_data(png_file_path)
    json_data = json.loads(extracted_text)# Convert the extracted text to a proper JSON object
    print("Faraday png data (formatted for tarven):", extracted_text)
    # Save the new PNG with faraday data
    output_png = f"converted_{base_name}.png"
    output_json = f"converted_{base_name}.json"
    save_png(json_data, source_filename, output_png)
    save_json(output_json, json_data)# Write data to JSON file
    print(f"Also saved new PNG & JSON with from faraday(converted to tavern) embedded text to {output_png} and {output_json}")

if __name__ == "__main__":
    main()