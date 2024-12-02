# backyard to tavern - version 4
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
import re

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
    
def extract_and_decode_base64(text):
    # Regular expression to find base64 encoded strings
    base64_pattern = r'([A-Za-z0-9+/=]+)'

    # Find all potential base64 encoded parts
    base64_parts = re.findall(base64_pattern, text)
    
    for part in base64_parts:
        try:
            # Decode the base64 part
            #decoded_bytes = base64.b64decode(part)
            #decoded_string = decoded_bytes.decode('utf-8')
            
            # Print the decoded string
            #print(f"Base64 Encoded Part: {part}")
            #print(f"Decoded Text: {decoded_string}\n")

            return part #returns first group only
        except (base64.binascii.Error, UnicodeDecodeError):
            # If there's an error in decoding, skip this part
            continue

def get_faraday_png_extra_base64_data(png_file_path):
    with open(png_file_path, 'rb') as f:
        # Read the entire PNG file
        png_data = f.read()

        # Search for the start and end markers of the base64 data
        start_marker = b'ASCII'
        end_marker = b'IDATx'
        start_index = png_data.find(start_marker)
        end_index = png_data.find(end_marker, start_index + len(start_marker))

        if start_index != -1 and end_index != -1:
            # Extract the base64 encoded data
            base64_data = png_data[start_index + len(start_marker):end_index]

            # Clean up base64 data by removing non-base64 characters
            cleaned_base64_data = re.sub(rb'[^a-zA-Z0-9+/]', b'', base64_data)
            
            # Remove any padding characters ('=')
            while len(cleaned_base64_data) % 4 != 0:
                cleaned_base64_data = cleaned_base64_data[:-1]
            #print(f"cleaned_base64_data=={cleaned_base64_data}") #this is the encoded data
            # Decode the base64 data without adding padding
            decoded_data = base64.b64decode(cleaned_base64_data) 
            #print(f"decoded_data=={decoded_data}") #this is the encoded data
            decoded_string = decoded_data.decode('utf-8', errors='replace') #this is the decoded data

            version_index = decoded_string.find('"version":')
            if version_index != -1 and '}' not in decoded_string[version_index:]:
                decoded_string += "}" #add } at the end if missing after '"version":'
            #print(f"decoded_string=={decoded_string}") #this is the encoded data
            
            #return decoded_data
            # Attempt to find and remove extraneous characters after the JSON data
            json_start = decoded_string.find('{')
            json_end = decoded_string.rfind('}') + 1
            if json_start == -1 or json_end == -1:
                print("Error: JSON object boundaries not found.")
                return None
        
            json_string = decoded_string[json_start:json_end]
            #return json_string
            #Attempt to load the string as JSON and pretty-print it
            try:
                json_data = json.loads(json_string)
                formatted_json = json.dumps(json_data, indent=4)
                return formatted_json
            except json.JSONDecodeError as e:
                print(f"Error: JSON decoding failed. {str(e)}")
                return None
            
        else:
            print("Base64 encoded data not found in the PNG file.")
            return None
        
    
def get_faraday_png_extra_base64_data_UNUSED(png_file_path):
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
    #end_pos = png_file_string.find("Q==", start_pos)
    end_pos = png_file_string.find("IDATx", start_pos)
    
    if end_pos == -1:
        print("Error: Ending 'IDATx' not found.")
        return None
    
    base64_data = png_file_string[start_pos:end_pos + 5]
    base64_data = extract_and_decode_base64(base64_data)#tries to strip string to only get the base64 data
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
        
        print("==AI Display Name:", ai_display_name)
        print("==AI Name:", ai_name)
        print("==AI Persona:", ai_persona)
        print("==Custom Dialogue:", custom_dialogue)#example text
        print("==First Message:", first_message)
        print("==Scenario:", scenario)

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
    
def search_with_partial_filename(directory):
    # This for when the batch file only captures part of the filename
    # This attempts to find the rest of the filename, but only will return if there is only 1 certain result (not mutliples with that starting name)
    # Extract the directory path and partial filename
    directory_path, partial_filename = os.path.split(directory)
    
    # Check if the directory exists
    if not os.path.isdir(directory_path):
        print("Error: Directory not found.")
        return
    
    # Initialize a list to store matched filenames
    matched_files = []
    
    # Iterate through files in the directory
    for filename in os.listdir(directory_path):
        # Check if the filename starts with the partial filename and ends with ".png"
        if filename.startswith(partial_filename) and filename.endswith(".png"):
            # Add the matched filename to the list
            matched_files.append(os.path.join(directory_path, filename))
    
    # Check the number of matched files
    if len(matched_files) == 1:
        # If only one file is found, return the full filepath
        return matched_files[0]
    else:
        # Otherwise, return the count of results
        return len(matched_files)
    
def get_file_extension(file_path):
    _, extension = os.path.splitext(file_path)
    return extension.lower()[1:]  # Remove the leading dot

def get_filename_without_extension(file_path):
    file_name, _ = os.path.splitext(os.path.basename(file_path))
    return file_name

# Main usage
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
    print(f"png_file_path=<{png_file_path}> base_name=<{base_name}> ext=<{ext}>")
    #filename = sys.argv[1]
    #print(f"Filename: {filename}")
    if ext.lower() != ".png":
        temp_result = search_with_partial_filename(png_file_path)#tries to check for fullname if batch file gave only partial filename
        if isinstance(temp_result, int):
            print(f"Found {temp_result} partial filename matches, so unsure which is the file's name (partial maybe due to the batch file or partly inputed filename).")#found more than one match, do nothing
            print("Move the png file to the same directory as this script and try again.")
        else:
            print(f'Single png match found from partial filename: "{temp_result}"')#only one match found, use it
            png_file_path = temp_result
            base_name=get_filename_without_extension(png_file_path)
    
    if get_file_extension(png_file_path) != "png":
        print("Error: Please provide a PNG file.")
        sys.exit(1)


    source_filename = png_file_path
    extracted_text = convert_faraday_png_to_tavern_data(png_file_path)
    json_data = json.loads(extracted_text)# Convert the extracted text to a proper JSON object
    print("Faraday png data (formatted for tarven):", extracted_text)
    # Save the new PNG with faraday data
    output_png = f"{base_name}.tavern.png"
    output_json = f"{base_name}.tavern.json"
    save_png(json_data, source_filename, output_png)
    save_json(output_json, json_data)# Write data to JSON file
    print(f"Also saved new PNG & JSON with from faraday(converted to tavern) embedded text to {output_png} and {output_json}")

if __name__ == "__main__":
    main()
