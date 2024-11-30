# backyard_to_tavern.py - version 10
# Script By Elise Windbloom
# Special thanks to Hukasx0 for faraday2tavern.py eariler alternate version
# Concepts of this based on html/js character editor by zoltanai: https://zoltanai.github.io/character-editor/
# This was second rebuild from stratch to try to make this much more reliable at converting
import os
import sqlite3
import json
import base64
import argparse
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import sys
import time
import zlib
from struct import pack, unpack
import re
import io

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

def get_default_db_path():
    """Get the default path to the BackyardAI database"""
    if sys.platform == 'win32':  # Windows
        return os.path.join(os.getenv('APPDATA'), 'faraday', 'db.sqlite')
    elif sys.platform == 'darwin':  # macOS
        return os.path.expanduser('~/Library/Application Support/faraday/db.sqlite')
    else:  # Linux and others
        return os.path.expanduser('~/.local/share/faraday/db.sqlite')

def get_character_data(db_path=None, skip_if_not_exists=False):
    """Get character data from the database"""
    if db_path is None:
        db_path = get_default_db_path()
        
    if not db_path or not os.path.exists(db_path):
        if skip_if_not_exists:
            return []
        raise FileNotFoundError(f"Database file not found: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get character data from the new table structure
        query = """
        SELECT 
            cc.id as config_id,
            ccv.id as version_id,
            ccv.displayName,
            ccv.name,
            ccv.persona,
            GROUP_CONCAT(ai.imageUrl) as images
        FROM CharacterConfig cc
        JOIN CharacterConfigVersion ccv ON cc.id = ccv.characterConfigId
        LEFT JOIN _AppImageToCharacterConfigVersion aitc ON ccv.id = aitc.B
        LEFT JOIN AppImage ai ON aitc.A = ai.id
        WHERE cc.isUserControlled = 0 AND cc.isDefaultUserCharacter = 0
        GROUP BY cc.id, ccv.id
        """
        
        cursor.execute(query)
        characters = []
        
        for row in cursor.fetchall():
            config_id, version_id, display_name, name, persona, images = row
            
            # Get lorebook items
            cursor.execute("""
                SELECT ali.key, ali.value
                FROM AppCharacterLorebookItem ali
                JOIN _AppCharacterLorebookItemToCharacterConfigVersion altc ON ali.id = altc.A
                WHERE altc.B = ?
            """, (version_id,))
            
            lorebook = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get chat data for example dialogue and scenario
            cursor.execute("""
                SELECT c.customDialogue, c.context, c.greetingDialogue
                FROM Chat c
                JOIN GroupConfig gc ON c.groupConfigId = gc.id
                JOIN _CharacterConfigToGroupConfig cctg ON gc.id = cctg.B
                WHERE cctg.A = ?
                ORDER BY c.createdAt ASC
                LIMIT 1
            """, (config_id,))
            
            chat_row = cursor.fetchone()
            example_dialogue = ""
            scenario = ""
            first_message = ""
            
            if chat_row:
                example_dialogue = chat_row[0] if chat_row[0] else ""
                scenario = chat_row[1] if chat_row[1] else ""
                first_message = chat_row[2] if chat_row[2] else ""
            
            # Process image paths
            image_paths = []
            if images:
                for img_path in images.split(','):
                    if img_path:
                        if img_path.startswith('file://'):
                            img_path = img_path[7:]  # Remove file:// prefix
                        image_paths.append(img_path)
                
            character = {
                'name': name or display_name,
                'display_name': display_name or name,
                'description': persona,
                'scenario': scenario,
                'first_message': first_message,
                'example_dialogue': example_dialogue,
                'lorebook': lorebook,
                'image_paths': image_paths
            }
            
            characters.append(character)
        
        if not characters:
            print("No characters found in database.")
            
        return characters
        
    except Exception as e:
        print(f"Error reading database: {str(e)}")
        return []
    finally:
        conn.close()
    
    return []

def get_character_from_database(filename, db_path=None, skip_if_not_exists=False):
    """Try to find character data in the BackyardAI database based on filename"""
    if not db_path:
        db_path = get_default_db_path()
    
    if not db_path or not os.path.exists(db_path):
        if skip_if_not_exists:
            return None
        return None
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get character data from database
        cursor.execute("""
            SELECT 
                cc.id as config_id,
                ccv.id as version_id,
                ccv.displayName,
                ccv.name,
                ccv.persona
            FROM CharacterConfig cc
            JOIN CharacterConfigVersion ccv ON cc.id = ccv.characterConfigId
            WHERE cc.isUserControlled = 0 AND cc.isDefaultUserCharacter = 0
            AND (ccv.name LIKE ? OR ccv.displayName LIKE ?)
        """, (f"%{filename}%", f"%{filename}%"))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        config_id, version_id, display_name, name, persona = row
        
        # Get lorebook items
        cursor.execute("""
            SELECT ali.key, ali.value
            FROM AppCharacterLorebookItem ali
            JOIN _AppCharacterLorebookItemToCharacterConfigVersion altc ON ali.id = altc.A
            WHERE altc.B = ?
        """, (version_id,))
        
        lorebook = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return {
            'name': name,
            'display_name': display_name,
            'description': persona,
            'scenario': "",
            'first_message': "",
            'example_dialogue': "",
            'lorebook': lorebook,
            'image_paths': []
        }
    except sqlite3.Error as e:
        if not skip_if_not_exists:
            print(f"Error accessing BackyardAI database: {str(e)}")
        return None

def normalize_newlines(text):
    """Normalize newlines to \n\n format"""
    if not text:
        return ""
    # First convert all types of newlines to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Then convert multiple newlines to double newlines
    while '\n\n\n' in text:
        text = text.replace('\n\n\n', '\n\n')
    return text

def convert_placeholders(text):
    """Convert BackyardAI placeholders to TavernAI format"""
    if not text:
        return ""
    # First replace any existing double-braced placeholders to prevent double conversion
    text = text.replace("{{char}}", "{character}")
    text = text.replace("{{user}}", "{user}")
    # Then do the final conversion
    text = text.replace("{character}", "{{char}}")
    text = text.replace("{user}", "{{user}}")
    return text

def create_tavern_card(character, output_dir=None, output_filename=None):
    """Create a TavernAI character card"""
    # Create output directory if it doesn't exist
    if not output_dir:
        output_dir = 'converted_cards'
    os.makedirs(output_dir, exist_ok=True)
    
    # Create safe filename if none provided
    if not output_filename:
        safe_filename = "".join(x if x.isascii() and (x.isalnum() or x in (' ', '-', '_')) else '_' for x in character['name'])
        safe_filename = safe_filename.replace(' ', '_')
    else:
        safe_filename = output_filename
        
    # Create output paths
    png_path = os.path.join(output_dir, f"{safe_filename}.png")
    json_path = os.path.join(output_dir, f"{safe_filename}.json")
    
    # Create TavernAI v2 format data
    tavern_data = {
        "name": character['name'],
        "description": convert_placeholders(character['description']),
        "personality": convert_placeholders(character.get('personality', '')),
        "scenario": convert_placeholders(character.get('scenario', '')),
        "first_mes": convert_placeholders(character.get('first_message', '')),
        "mes_example": convert_placeholders(character.get('example_dialogue', '')),
        "creator_notes": "",
        "system_prompt": convert_placeholders(character.get('base_prompt', '')),
        "post_history_instructions": "",
        "alternate_greetings": [],
        "character_book": {k: convert_placeholders(v) for k, v in character.get('lorebook', {}).items()},
        "tags": ["NSFW"] if character.get('is_nsfw', False) else [],
        "creator": "BackyardAI",
        "character_version": "v2",
        "extensions": {
            "temperature": character.get('temperature', 0.8),
            "repeat_penalty": character.get('repeat_penalty', 1.0),
            "repeat_last_n": character.get('repeat_last_n', 128),
            "top_k": character.get('top_k', 30),
            "top_p": character.get('top_p', 0.9),
            "min_p": character.get('min_p', 0.1)
        },
        "spec": "chara_card_v2"
    }
    
    # Save JSON file
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(tavern_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving JSON for {character['name']}: {str(e)}")
        return None, None

    # Check for image availability
    if not character['image_paths']:
        print(f"Error: No image found for character {character['name']}")
        return None, None

    # Use the first image as the character image
    image_path = character['image_paths'][0]
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return None, None

    # Convert the data to JSON and encode as base64 for PNG embedding
    json_data = json.dumps(tavern_data, ensure_ascii=False)
    
    try:
        # Open and convert the image
        with Image.open(image_path) as img:
            # Create PNG info object
            info = PngInfo()
            
            # Add the character data
            info.add_text("chara", base64.b64encode(json_data.encode('utf-8')).decode('utf-8'))
            
            # Save the image with the embedded data
            img.save(png_path, "PNG", pnginfo=info)
            
        return png_path, json_path
    except Exception as e:
        print(f"Error creating PNG for {character['name']}: {str(e)}")
        return None, None

def extract_character_data(image_path):
    """Extract character data from a PNG file if it exists"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return json.loads(Png.parse(image_data))
    except Exception as e:
        print(f"Warning: Could not extract character data from {image_path}: {str(e)}")
    return None

def extract_backyard_png_data(png_file_path):
    """Extract character data from BackyardAI PNG format"""
    try:
        with open(png_file_path, 'rb') as f:
            png_data = f.read()

            # Search for the start and end markers of the base64 data
            start_marker = b'ASCII'
            end_marker = b'IDATx'
            start_index = png_data.find(start_marker)
            end_index = png_data.find(end_marker, start_index + len(start_marker))

            if start_index == -1 or end_index == -1:
                return None

            # Extract and clean the base64 data
            base64_data = png_data[start_index + len(start_marker):end_index]
            cleaned_base64_data = re.sub(rb'[^a-zA-Z0-9+/=]', b'', base64_data)
            
            # Add padding if needed
            padding_needed = len(cleaned_base64_data) % 4
            if padding_needed:
                cleaned_base64_data += b'=' * (4 - padding_needed)

            try:
                # Decode the base64 data
                decoded_data = base64.b64decode(cleaned_base64_data)
                decoded_string = decoded_data.decode('utf-8', errors='replace')

                # Find JSON boundaries
                json_start = decoded_string.find('{"character":')
                if json_start == -1:
                    json_start = decoded_string.find('{')
                json_end = decoded_string.rfind('}')
                
                if json_start == -1 or json_end == -1:
                    return None

                # Extract the JSON and ensure it's complete
                json_string = decoded_string[json_start:json_end + 1]
                
                # Try to find a complete character object if the JSON is truncated
                if not json_string.endswith('}'):
                    char_end = json_string.rfind('}}')
                    if char_end != -1:
                        json_string = json_string[:char_end + 2]

                json_data = json.loads(json_string)

                # Extract character data
                character = json_data.get('character', {})
                
                # Get the raw fields directly without trying to parse them
                name = character.get('aiName', '')
                display_name = character.get('aiDisplayName', '')
                description = character.get('aiPersona', '')  # Use the entire aiPersona as description
                scenario = character.get('scenario', '')
                first_message = character.get('firstMessage', '')
                custom_dialogue = character.get('customDialogue', '')
                base_prompt = character.get('basePrompt', '')

                # Get additional fields
                lore_items = character.get('loreItems', [])
                lorebook = {}
                for item in lore_items:
                    if isinstance(item, dict):
                        key = item.get('key', '')
                        value = item.get('value', '')
                        if key and value:
                            lorebook[key] = value
                    elif isinstance(item, str):
                        lorebook[f'Entry {len(lorebook) + 1}'] = item

                # Get other important fields
                is_nsfw = character.get('isNSFW', False)
                temperature = character.get('temperature', 0.8)
                repeat_penalty = character.get('repeatPenalty', 1.0)
                repeat_last_n = character.get('repeatLastN', 128)
                top_k = character.get('topK', 30)
                top_p = character.get('topP', 0.9)
                min_p = character.get('minP', 0.1)

                return {
                    'name': name or display_name,
                    'display_name': display_name or name,
                    'description': description,  # Keep the entire aiPersona as description
                    'personality': '',  # Leave personality empty since it's part of description
                    'scenario': scenario,
                    'first_message': first_message,
                    'example_dialogue': custom_dialogue,
                    'lorebook': lorebook,
                    'base_prompt': base_prompt,
                    'is_nsfw': is_nsfw,
                    'temperature': temperature,
                    'repeat_penalty': repeat_penalty,
                    'repeat_last_n': repeat_last_n,
                    'top_k': top_k,
                    'top_p': top_p,
                    'min_p': min_p
                }
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                # Try to extract just the character object if the full JSON is corrupted
                try:
                    char_start = decoded_string.find('"character":{')
                    if char_start != -1:
                        char_data = decoded_string[char_start + 11:]  # Skip past '"character":'
                        char_end = char_data.find('}}')
                        if char_end != -1:
                            char_json = '{' + char_data[:char_end + 1] + '}'
                            character = json.loads(char_json)
                            # Process character data as before...
                            return {
                                'name': character.get('aiName', ''),
                                'display_name': character.get('aiDisplayName', ''),
                                'description': character.get('aiPersona', ''),
                                'personality': '',
                                'scenario': character.get('scenario', ''),
                                'first_message': character.get('firstMessage', ''),
                                'example_dialogue': character.get('customDialogue', ''),
                                'lorebook': {},
                                'base_prompt': character.get('basePrompt', ''),
                                'is_nsfw': character.get('isNSFW', False),
                                'temperature': character.get('temperature', 0.8),
                                'repeat_penalty': character.get('repeatPenalty', 1.0),
                                'repeat_last_n': character.get('repeatLastN', 128),
                                'top_k': character.get('topK', 30),
                                'top_p': character.get('topP', 0.9),
                                'min_p': character.get('minP', 0.1)
                            }
                except Exception as e2:
                    print(f"Error extracting character data: {str(e2)}")
                    return None
    except Exception as e:
        print(f"Error extracting BackyardAI data: {str(e)}")
        return None

def convert_single_png(input_path, output_dir):
    """Convert a single BackyardAI PNG card to TavernAI format"""
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        return None

    # Get the filename without extension
    name_without_ext = os.path.splitext(os.path.basename(input_path))[0]
    
    # First try to find the character in the BackyardAI database
    character = get_character_from_database(name_without_ext, skip_if_not_exists=True)
    
    if not character:
        # Extract data directly from the PNG file
        backyard_data = extract_backyard_png_data(input_path)
        if backyard_data:
            character = {
                'name': backyard_data['name'],
                'description': backyard_data['description'],
                'personality': backyard_data['personality'],
                'scenario': backyard_data['scenario'],
                'first_message': backyard_data['first_message'],
                'example_dialogue': backyard_data['example_dialogue'],
                'lorebook': backyard_data['lorebook'],
                'base_prompt': backyard_data['base_prompt'],
                'is_nsfw': backyard_data['is_nsfw'],
                'temperature': backyard_data['temperature'],
                'repeat_penalty': backyard_data['repeat_penalty'],
                'repeat_last_n': backyard_data['repeat_last_n'],
                'top_k': backyard_data['top_k'],
                'top_p': backyard_data['top_p'],
                'min_p': backyard_data['min_p'],
                'image_paths': [input_path],
                'display_name': backyard_data['display_name']
            }
        else:
            # If not found in BackyardAI format, try standard TavernAI format
            existing_data = extract_character_data(input_path)
            character = {
                'name': existing_data.get('name', name_without_ext) if existing_data else name_without_ext,
                'description': existing_data.get('description', "") if existing_data else "",
                'personality': existing_data.get('personality', "") if existing_data else "",
                'scenario': existing_data.get('scenario', "") if existing_data else "",
                'first_message': existing_data.get('first_mes', "") if existing_data else "",
                'example_dialogue': existing_data.get('mes_example', "") if existing_data else "",
                'lorebook': {},
                'base_prompt': "",
                'is_nsfw': False,
                'temperature': 0.8,
                'repeat_penalty': 1.0,
                'repeat_last_n': 128,
                'top_k': 30,
                'top_p': 0.9,
                'min_p': 0.1,
                'image_paths': [input_path],
                'display_name': existing_data.get('display_name', name_without_ext) if existing_data else name_without_ext
            }

    # Update the image path to the current file
    character['image_paths'] = [input_path]

    # Sanitize the original filename for output
    safe_filename = "".join(x if x.isascii() and (x.isalnum() or x in (' ', '-', '_')) else '_' for x in name_without_ext)
    safe_filename = safe_filename.replace(' ', '_')

    output_path = create_tavern_card(character, output_dir, output_filename=safe_filename)
    if isinstance(output_path, tuple):
        png_path, json_path = output_path
        if png_path and json_path:
            print(f"Successfully converted to PNG: {png_path}")
            print(f"Successfully converted to JSON: {json_path}")
            return png_path
        else:
            print("Failed to convert character card")
            return None
    else:
        print("Failed to convert character card")
        return None

def create_chunk(type_bytes, data_bytes):
    """Create a PNG chunk"""
    # Length (4 bytes) + Type (4 bytes) + Data + CRC (4 bytes)
    length = len(data_bytes)
    
    # Create chunk header (length + type)
    chunk = struct.pack(">I", length)  # Length
    chunk += type_bytes  # Type
    
    # Add data
    chunk += data_bytes
    
    # Calculate CRC
    crc = zlib.crc32(type_bytes + data_bytes) & 0xFFFFFFFF
    chunk += struct.pack(">I", crc)
    
    return chunk

def save_png_with_chunks(img, output_path, chunks):
    """Save a PNG file with additional chunks"""
    # Convert image to PNG bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_data = img_bytes.getvalue()
    
    # PNG header
    output = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk is always first
    ihdr_end = img_data.find(b'IDAT') - 4  # -4 to skip CRC
    output += img_data[8:ihdr_end]  # Skip PNG header
    
    # Add our chunks before IDAT
    for chunk in chunks:
        output += chunk
    
    # Add remaining chunks (IDAT and IEND)
    output += img_data[ihdr_end:]
    
    # Write to file
    with open(output_path, 'wb') as f:
        f.write(output)

def main():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(description='Convert BackyardAI character cards to TavernAI format')
    parser.add_argument('--single', help='Convert a single PNG file')
    parser.add_argument('--output-dir', default='converted_cards', help='Output directory for converted cards')
    parser.add_argument('--database', '-d', help='Custom path to BackyardAI db.sqlite')
    
    args = parser.parse_args()
    
    if args.single:
        # Skip database check for single file conversions
        print(f"Converting single file: {args.single}")
        convert_single_png(args.single, args.output_dir)
    else:
        # Only check database for bulk conversions
        characters = get_character_data(args.database, skip_if_not_exists=True)
        if not characters:
            print("No characters found in BackyardAI database.")
            return
            
        print(f"\nFound {len(characters)} characters in BackyardAI database")
        print("Converting characters to TavernAI format...")
        
        success_count = 0
        error_count = 0
        
        for i, character in enumerate(characters, 1):
            try:
                output_path = create_tavern_card(character, args.output_dir)
                if isinstance(output_path, tuple):
                    png_path, json_path = output_path
                    if png_path and json_path:
                        name = character['name'].encode('utf-8', errors='replace').decode('utf-8')
                        print(f"[{i}/{len(characters)}] Successfully converted: {name}")
                        print(f"  PNG: {png_path}")
                        print(f"  JSON: {json_path}")
                        success_count += 1
                    else:
                        name = character['name'].encode('utf-8', errors='replace').decode('utf-8')
                        print(f"[{i}/{len(characters)}] Failed to convert: {name}")
                        error_count += 1
                else:
                    name = character['name'].encode('utf-8', errors='replace').decode('utf-8')
                    print(f"[{i}/{len(characters)}] Failed to convert: {name}")
                    error_count += 1
            except Exception as e:
                name = character['name'].encode('utf-8', errors='replace').decode('utf-8')
                print(f"[{i}/{len(characters)}] Error converting {name}: {str(e)}")
                error_count += 1
                
        print(f"\nConversion complete!")
        print(f"Successfully converted: {success_count} characters")
        if error_count > 0:
            print(f"Failed to convert: {error_count} characters")
        print(f"\nConverted cards are in the '{args.output_dir}' directory")

if __name__ == "__main__":
    main()
