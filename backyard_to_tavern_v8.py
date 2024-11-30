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
    if sys.platform == 'win32':
        # Try AppData\Roaming\faraday first
        roaming_faraday_path = os.path.join(os.environ.get('APPDATA', ''), 'faraday', 'db.sqlite')
        if os.path.exists(roaming_faraday_path):
            return roaming_faraday_path
            
        # Try AppData\Local\faraday
        local_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'faraday', 'db.sqlite')
        if os.path.exists(local_path):
            return local_path
            
        # Try AppData\Local\BackyardAI
        local_backyard_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BackyardAI', 'db.sqlite')
        if os.path.exists(local_backyard_path):
            return local_backyard_path
            
        # Try AppData\Roaming\BackyardAI
        roaming_path = os.path.join(os.environ.get('APPDATA', ''), 'BackyardAI', 'db.sqlite')
        if os.path.exists(roaming_path):
            return roaming_path
            
        print(f"Warning: BackyardAI database not found in standard locations:")
        print(f"- {roaming_faraday_path}")
        print(f"- {local_path}")
        print(f"- {local_backyard_path}")
        print(f"- {roaming_path}")
        return None
    
    elif sys.platform == 'darwin':  # macOS
        return os.path.expanduser('~/Library/Application Support/BackyardAI/db.sqlite')
    else:  # Linux and others
        return os.path.expanduser('~/.local/share/BackyardAI/db.sqlite')

def get_character_data(db_path=None, skip_if_not_exists=False):
    """Get character data from BackyardAI database"""
    if not db_path:
        db_path = get_default_db_path()
        
    if not db_path or not os.path.exists(db_path):
        if skip_if_not_exists:
            return []
        print(f"Warning: BackyardAI database not found at {db_path}")
        return []
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all character configs and their latest versions
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
            
            # Get first chat for this character to extract example dialogue
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
                'name': name,
                'display_name': display_name,
                'description': persona,
                'scenario': scenario,
                'first_message': first_message,
                'example_dialogue': example_dialogue,
                'lorebook': lorebook,
                'image_paths': image_paths
            }
            
            characters.append(character)
        
        conn.close()
        return characters
    except sqlite3.Error as e:
        print(f"Error accessing BackyardAI database: {str(e)}")
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
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Clean up the character name for use in filename - use display_name for files
    clean_name = "".join(x for x in (character['display_name'] or character['name']) if x.isalnum() or x in (' ', '-', '_')).strip()
    clean_name = clean_name.replace(' ', '_')
    
    # Create file paths for both PNG and JSON
    if output_filename:
        base_filename = os.path.splitext(output_filename)[0]
    else:
        base_filename = clean_name
        
    png_path = os.path.join(output_dir, f"{base_filename}.png")
    json_path = os.path.join(output_dir, f"{base_filename}.json")

    # Create the character data in TavernAI v2 format - use internal name for character data
    tavern_data = {
        'name': character['name'],  # Use internal name for the character's actual name
        'description': normalize_newlines(convert_placeholders(character['description'])),
        'personality': "",  # Leave empty since it's same as description
        'scenario': normalize_newlines(convert_placeholders(character['scenario'])),
        'first_mes': normalize_newlines(convert_placeholders(character['first_message'])),
        'mes_example': normalize_newlines(convert_placeholders(character['example_dialogue'])),
        'creator_notes': "Converted from BackyardAI",
        'system_prompt': "",
        'post_history_instructions': "",
        'alternate_greetings': [],
        'character_version': "v2",
        'tags': [],
        'creator': "Unknown (BackyardAI)",
        'character_book': None,
        'extensions': {
            'world': "",
            'bias': "",
            'depth_prompt': "",
            'jailbreak': ""
        },
        'metadata': {
            'version': '2.0',
            'created': int(time.time()),
            'modified': int(time.time()),
            'source': 'BackyardAI',
            'tool': 'BackyardAI to TavernAI Converter'
        }
    }

    # Add lorebook entries if they exist
    if character['lorebook']:
        tavern_data['alternate_greetings'] = []
        for key, value in character['lorebook'].items():
            tavern_data['alternate_greetings'].append(f"{key}: {value}")

    # Save JSON file
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(tavern_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving JSON for {character['name']}: {str(e)}")
        return None

    # Check for image availability
    if not character['image_paths']:
        print(f"Error: No image found for character {character['name']}")
        return None

    # Use the first image as the character image
    image_path = character['image_paths'][0]
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return None

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
            
        return png_path
    except Exception as e:
        print(f"Error creating PNG for {character['name']}: {str(e)}")
        return None

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
            cleaned_base64_data = re.sub(rb'[^a-zA-Z0-9+/]', b'', base64_data)
            
            # Remove any padding characters
            while len(cleaned_base64_data) % 4 != 0:
                cleaned_base64_data = cleaned_base64_data[:-1]

            # Decode the base64 data
            decoded_data = base64.b64decode(cleaned_base64_data)
            decoded_string = decoded_data.decode('utf-8', errors='replace')

            # Find JSON boundaries
            json_start = decoded_string.find('{')
            json_end = decoded_string.rfind('}') + 1
            if json_start == -1 or json_end == -1:
                return None

            json_string = decoded_string[json_start:json_end]
            json_data = json.loads(json_string)

            # Extract character data
            character = json_data.get('character', {})
            
            # Split the persona into description and personality
            ai_persona = character.get('aiPersona', '')
            description = ""
            personality = ""
            world_info = ""
            
            # Look for world info section (before appearance)
            appearance_start = ai_persona.find("{character}'s appearance:")
            if appearance_start != -1:
                world_info = ai_persona[:appearance_start].strip()
            
            # Extract appearance section
            personality_start = ai_persona.find("{character}'s personality:")
            if appearance_start != -1 and personality_start != -1:
                description = ai_persona[appearance_start:personality_start].strip()
            elif appearance_start != -1:
                description = ai_persona[appearance_start:].strip()
            
            # Extract personality section
            if personality_start != -1:
                personality = ai_persona[personality_start:].strip()
            
            # If no sections found, put everything in personality
            if not description and not personality:
                personality = ai_persona
            
            # Add world info to description
            if world_info:
                description = f"{world_info}\n\n{description}" if description else world_info

            return {
                'name': character.get('aiName', ''),
                'description': convert_placeholders(description),
                'personality': convert_placeholders(personality),
                'first_message': convert_placeholders(character.get('firstMessage', '')),
                'example_dialogue': convert_placeholders(character.get('customDialogue', '')),
                'scenario': convert_placeholders(character.get('scenario', '')),
                'display_name': character.get('aiDisplayName', '')
            }

    except Exception as e:
        print(f"Warning: Could not extract BackyardAI data from {png_file_path}: {str(e)}")
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
                'lorebook': {k: convert_placeholders(v) for k, v in backyard_data.get('lorebook', {}).items()},
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
                'image_paths': [input_path],
                'display_name': existing_data.get('display_name', name_without_ext) if existing_data else name_without_ext
            }

    # Update the image path to the current file
    character['image_paths'] = [input_path]

    # Sanitize the original filename for output
    safe_filename = "".join(x if x.isascii() and (x.isalnum() or x in (' ', '-', '_')) else '_' for x in name_without_ext)
    safe_filename = safe_filename.replace(' ', '_')

    output_path = create_tavern_card(character, output_dir, output_filename=safe_filename)
    return output_path

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
    parser.add_argument('--database', '-d', help='Custom path to BackyardAI database.db')
    
    args = parser.parse_args()
    
    if args.single:
        # Skip database check for single file conversions
        print(f"Converting single file: {args.single}")
        output_path = convert_single_png(args.single, args.output_dir)
        if output_path:
            print(f"Successfully converted to: {output_path}")
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
                if output_path:
                    name = character['name'].encode('utf-8', errors='replace').decode('utf-8')
                    print(f"[{i}/{len(characters)}] Successfully converted: {name} -> {output_path}")
                    success_count += 1
                else:
                    name = character['name'].encode('utf-8', errors='replace').decode('utf-8')
                    print(f"[{i}/{len(characters)}] Failed to convert: {name} (No output path returned)")
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
