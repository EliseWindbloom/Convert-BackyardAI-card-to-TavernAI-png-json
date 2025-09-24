# backyard to tavern - version 14
# Script By Elise Windbloom
# Special thanks to Hukasx0 for faraday2tavern.py eariler alternate version
# This is the second major rebuild in part to fix conversion errors and allow optional use of the database

import base64
import zlib
import json
import re
import os
import sys
import sqlite3
from struct import pack, unpack
from pathlib import Path
import time
import argparse

class BackyardToTavernConverter:
    def __init__(self, debug=False, verbose=False):
        self.debug = debug
        self.verbose = verbose
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'method_usage': {},
            'database_extraction': 0,
            'tavern_format': 0,
            'backyard_export': 0,
            'exif_format': 0,
            'json_only': 0,
            'png_files': 0
        }
        self.db_conn = None
        self.db_cursor = None
        self.failed_files = []
    
    def debug_print(self, msg):
        if self.debug:
            print(f"[DEBUG] {msg}")
    
    def verbose_print(self, msg):
        if self.verbose or self.debug:
            print(msg)
    
    def get_default_db_path(self):
        """Get the default path to the BackyardAI database"""
        if sys.platform == 'win32':  # Windows
            return os.path.join(os.getenv('APPDATA'), 'faraday', 'db.sqlite')
        elif sys.platform == 'darwin':  # macOS
            return os.path.expanduser('~/Library/Application Support/faraday/db.sqlite')
        else:  # Linux and others
            return os.path.expanduser('~/.local/share/faraday/db.sqlite')
    
    def open_database(self, db_path=None):
        """Open connection to the BackyardAI database"""
        if db_path is None:
            db_path = self.get_default_db_path()
        
        if not os.path.exists(db_path):
            self.debug_print(f"Database not found at: {db_path}")
            return False
        
        try:
            self.db_conn = sqlite3.connect(db_path)
            self.db_cursor = self.db_conn.cursor()
            self.verbose_print(f"Connected to database: {db_path}")
            return True
        except Exception as e:
            print(f"Error opening database: {str(e)}")
            return False
    
    def close_database(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            self.db_cursor = None
    
    def get_character_data_from_db(self, image_path):
        """Extract character data directly from database for a given image"""
        if not self.db_cursor:
            return None
        
        try:
            # Get just the filename for matching
            filename = os.path.basename(image_path)
            
            # Query to get character data from the image filename
            query = """
            SELECT 
                ccv.id,
                ccv.name,
                ccv.displayName,
                ccv.persona,
                ccv.characterConfigId,
                gc.name as group_name,
                c.greetingDialogue,
                c.customDialogue
            FROM AppImage ai
            JOIN _AppImageToCharacterConfigVersion aitc ON ai.id = aitc.A
            JOIN CharacterConfigVersion ccv ON aitc.B = ccv.id
            LEFT JOIN CharacterConfig cc ON ccv.characterConfigId = cc.id
            LEFT JOIN _CharacterConfigToGroupConfig ccgc ON cc.id = ccgc.A
            LEFT JOIN GroupConfig gc ON ccgc.B = gc.id
            LEFT JOIN Chat c ON gc.id = c.groupConfigId
            WHERE ai.imageUrl LIKE ?
            ORDER BY ccv.createdAt DESC, c.createdAt DESC
            LIMIT 1
            """
            
            self.db_cursor.execute(query, (f"%{filename}",))
            result = self.db_cursor.fetchone()
            
            if result:
                self.debug_print(f"Found character in database: {filename}")
                
                # Extract the data
                (version_id, name, display_name, persona, 
                 char_config_id, group_name, greeting, custom_dialogue) = result
                
                # Build character data
                char_data = {
                    'name': name or display_name or 'Unknown',
                    'display_name': display_name or name,
                    'description': persona or '',
                    'personality': '',
                    'scenario': '',
                    'first_mes': greeting or '',
                    'mes_example': custom_dialogue or '',
                }
                
                # Parse persona field if it contains structured data
                if persona:
                    char_data = self.parse_persona_field(persona, char_data)
                
                return char_data
            
            return None
            
        except Exception as e:
            self.debug_print(f"Database extraction error: {str(e)}")
            return None
    
    def parse_persona_field(self, persona, char_data):
        """Parse the persona field to extract structured information"""
        # If persona contains personality/scenario markers, extract them
        if '\n' in persona or any(marker in persona.lower() for marker in ['personality:', 'scenario:', 'traits:']):
            lines = persona.split('\n')
            
            for line in lines:
                line_lower = line.lower().strip()
                if any(keyword in line_lower for keyword in ['personality:', 'traits:', 'character:']):
                    if not char_data['personality']:
                        char_data['personality'] = line.strip()
                elif any(keyword in line_lower for keyword in ['scenario:', 'setting:', 'context:']):
                    if not char_data['scenario']:
                        char_data['scenario'] = line.strip()
        
        # If no structured data found, use entire persona as description
        if not char_data['personality'] and not char_data['scenario']:
            char_data['description'] = persona
        
        return char_data
    
    def extract_tavern_format(self, png_data):
        """Extract character data from TavernAI format PNG (Method 1)"""
        try:
            if not png_data.startswith(b'\x89PNG'):
                return None
            
            pos = 8  # Skip PNG signature
            while pos < len(png_data):
                if pos + 8 > len(png_data):
                    break
                    
                length = unpack(">I", png_data[pos:pos + 4])[0]
                chunk_type = png_data[pos + 4:pos + 8].decode('ascii', errors='ignore')
                
                if pos + 8 + length > len(png_data):
                    break
                    
                chunk_data = png_data[pos + 8:pos + 8 + length]
                
                if chunk_type == 'tEXt':
                    keyword, text = chunk_data.split(b'\x00', 1)
                    if keyword == b'chara':
                        decoded = base64.b64decode(text).decode('utf-8')
                        self.stats['tavern_format'] += 1
                        self.debug_print("Found TavernAI format character data")
                        return json.loads(decoded)
                
                pos += 12 + length
                if chunk_type == 'IEND':
                    break
                    
        except Exception as e:
            self.debug_print(f"TavernAI extraction failed: {e}")
        
        return None

    def extract_exif_format(self, png_data):
        """Extract character data from EXIF metadata format (Method 3)"""
        try:
            if not png_data.startswith(b'\x89PNG'):
                return None
            
            pos = 8  # Skip PNG signature
            while pos < len(png_data):
                if pos + 8 > len(png_data):
                    break
                
                length = unpack(">I", png_data[pos:pos + 4])[0]
                chunk_type = png_data[pos + 4:pos + 8].decode('ascii', errors='ignore')
                
                if pos + 8 + length > len(png_data):
                    break
                
                chunk_data = png_data[pos + 8:pos + 8 + length]
                
                # Look for eXIf chunk
                if chunk_type == 'eXIf':
                    self.debug_print("Found eXIf chunk")
                    
                    # Look for ASCII marker in EXIF data
                    ascii_marker = b'ASCII'
                    ascii_index = chunk_data.find(ascii_marker)
                    
                    if ascii_index != -1:
                        # Extract base64 data after ASCII marker
                        # Look for the end of the base64 data (usually ends with })
                        start_pos = ascii_index + len(ascii_marker)
                        
                        # Skip any whitespace/control characters
                        while start_pos < len(chunk_data) and chunk_data[start_pos:start_pos+1] in b' \x00\n\r\t':
                            start_pos += 1
                        
                        base64_data = chunk_data[start_pos:]
                        
                        # Clean base64 data - remove non-base64 characters
                        cleaned = b''
                        for byte in base64_data:
                            if chr(byte) in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=':
                                cleaned += bytes([byte])
                            elif cleaned and cleaned[-1:] != b'=' and byte in (0, 1, 2, 3, 4):
                                # Stop at low control characters after we have data
                                break
                        
                        if cleaned:
                            try:
                                # Fix padding if needed
                                cleaned = cleaned.rstrip(b'=')
                                padding = 4 - (len(cleaned) % 4)
                                if padding != 4:
                                    cleaned += b'=' * padding
                                
                                decoded = base64.b64decode(cleaned)
                                text = decoded.decode('utf-8', errors='ignore')
                                
                                # Parse JSON
                                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(1)
                                    json_data = json.loads(json_str)
                                    self.stats['exif_format'] = self.stats.get('exif_format', 0) + 1
                                    self.debug_print("Found character data in EXIF format")
                                    return self.parse_backyard_format(json_data)
                            except Exception as e:
                                self.debug_print(f"Error decoding EXIF base64: {e}")
                    
                pos += 12 + length
                if chunk_type == 'IEND':
                    break
        
        except Exception as e:
            self.debug_print(f"EXIF extraction failed: {e}")
        
        return None
    
    def extract_backyard_export(self, png_data):
        """Extract character data from BackyardAI export format (simplified Method 2)"""
        try:
            start_marker = b'ASCII'
            end_marker = b'IDATx'
            
            start_index = png_data.find(start_marker)
            if start_index == -1:
                return None
                
            end_index = png_data.find(end_marker, start_index + len(start_marker))
            if end_index == -1:
                return None
            
            # Extract base64 data between markers
            base64_data = png_data[start_index + len(start_marker):end_index]
            
            # Clean and decode
            cleaned = re.sub(rb'[^a-zA-Z0-9+/=]', b'', base64_data)
            
            # Fix padding
            cleaned = cleaned.rstrip(b'=')  # Remove existing padding
            padding = 4 - (len(cleaned) % 4)
            if padding != 4:
                cleaned += b'=' * padding
            
            try:
                decoded = base64.b64decode(cleaned)
                text = decoded.decode('utf-8', errors='ignore')
                
                # Extract JSON
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    json_data = json.loads(json_str)
                    self.stats['backyard_export'] += 1
                    self.debug_print("Found BackyardAI export format data")
                    return self.parse_backyard_format(json_data)
            except:
                pass
                
        except Exception as e:
            self.debug_print(f"BackyardAI export extraction failed: {e}")
        
        return None
    
    def parse_backyard_format(self, json_data):
        """Parse BackyardAI format to standard format"""
        if 'character' in json_data:
            character = json_data['character']
        else:
            character = json_data
        
        # Extract fields with fallbacks
        result = {
            'name': character.get('aiName', character.get('aiDisplayName', character.get('name', 'Unknown'))),
            'description': character.get('aiPersona', character.get('description', character.get('persona', ''))),
            'personality': character.get('personality', ''),
            'scenario': character.get('scenario', ''),
            'first_mes': character.get('firstMessage', character.get('greeting', character.get('first_mes', ''))),
            'mes_example': character.get('customDialogue', character.get('examples', character.get('mes_example', ''))),
        }
        
        # Add display name if available
        if 'aiDisplayName' in character:
            result['display_name'] = character['aiDisplayName']
        elif 'display_name' in character:
            result['display_name'] = character['display_name']
        
        # Convert placeholders
        for key in ['description', 'personality', 'scenario', 'first_mes', 'mes_example']:
            if result[key]:
                result[key] = result[key].replace('{character}', '{{char}}')
                result[key] = result[key].replace('{user}', '{{user}}')
        
        return result
    
    def generate_unique_filename(self, base_path):
        """Generate a unique filename to prevent collisions"""
        if not os.path.exists(base_path):
            return base_path
        
        dir_name = os.path.dirname(base_path)
        base_name = os.path.basename(base_path)
        name_parts = os.path.splitext(base_name)
        
        counter = 1
        while True:
            new_name = f"{name_parts[0]}_{counter}{name_parts[1]}"
            new_path = os.path.join(dir_name, new_name)
            if not os.path.exists(new_path):
                return new_path
            counter += 1
    
    def sanitize_filename(self, name):
        """Sanitize a string for use in filename"""
        if not name:
            return "Unknown"
        # Replace non-ASCII and special characters
        safe_name = "".join(c if c.isascii() and (c.isalnum() or c in (' ', '-', '_')) else '_' 
                           for c in name)
        # Replace spaces with underscores and limit length
        safe_name = safe_name.replace(' ', '_')
        # Ensure it's not empty after sanitization
        if not safe_name:
            safe_name = "Unknown"
        return safe_name
    
    
    def convert_file(self, input_path, output_path=None, quiet=False, use_database=True, from_batch=False):
        """Convert a single file with optimized extraction order"""
        # Only increment total if not called from batch processing
        if not from_batch:
            self.stats['total'] += 1
        
        if not os.path.exists(input_path):
            if not quiet:
                print(f"Error: File not found: {input_path}")
            self.stats['failed'] += 1
            self.failed_files.append(input_path)
            return False
        
        try:
            # Read the PNG file
            with open(input_path, 'rb') as f:
                png_data = f.read()
        except Exception as e:
            if not quiet:
                print(f"Error reading file: {str(e)}")
            self.stats['failed'] += 1
            self.failed_files.append(input_path)
            return False
        
        extracted_data = None
        extraction_method = None
        
        # Optimized extraction order based on what actually works
        if use_database and self.db_cursor:
            # Try database first when available (most reliable)
            self.debug_print("Trying database extraction...")
            extracted_data = self.get_character_data_from_db(input_path)
            if extracted_data:
                extraction_method = "Database"
                self.stats['database_extraction'] += 1
        
        if not extracted_data:
            # Try TavernAI format (common for imports)
            self.debug_print("Trying TavernAI format extraction...")
            extracted_data = self.extract_tavern_format(png_data)
            if extracted_data:
                extraction_method = "TavernAI format"
        
        if not extracted_data:
            # Try BackyardAI export format (for exported files)
            self.debug_print("Trying BackyardAI export format extraction...")
            extracted_data = self.extract_backyard_export(png_data)
            if extracted_data:
                extraction_method = "BackyardAI export"

        if not extracted_data:
            # Try EXIF format (for alternate BackyardAI exports)
            self.debug_print("Trying EXIF format extraction...")
            extracted_data = self.extract_exif_format(png_data)
            if extracted_data:
                extraction_method = "EXIF format"
        
        if not extracted_data:
            if not quiet:
                print(f"✗ Failed to extract character data from: {os.path.basename(input_path)}")
            self.stats['failed'] += 1
            self.failed_files.append(input_path)
            return False
        
        # Update method usage stats
        if extraction_method not in self.stats['method_usage']:
            self.stats['method_usage'][extraction_method] = 0
        self.stats['method_usage'][extraction_method] += 1
        
        # Create output filename if not specified
        if not output_path:
            if from_batch:
                # For batch mode, use character names (current behavior)
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                char_name = extracted_data.get('name', base_name)
                display_name = extracted_data.get('display_name', '')
                
                # Sanitize names for filename
                safe_name = self.sanitize_filename(char_name)[:100]
                
                # Add display name if available and different from main name
                if display_name and display_name != char_name:
                    safe_display = self.sanitize_filename(display_name)[:50]
                    output_path = f"{safe_name} ({safe_display}).tavern.png"
                else:
                    output_path = f"{safe_name}.tavern.png"
            else:
                # For individual file mode, preserve original filename
                base_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = f"{base_name}.tavern.png"
                
                # If it already has .tavern in the name, don't double it
                if '.tavern' in base_name.lower():
                    output_path = os.path.basename(input_path)
        
        # Ensure unique filename
        output_path = self.generate_unique_filename(output_path)
        
        # Save the converted card
        try:
            self.save_tavern_card(extracted_data, png_data, output_path)
            
            # ALWAYS save as JSON
            json_path = output_path.replace('.tavern.png', '.tavern.json')
            if not json_path.endswith('.json'):  # Safety check
                json_path = output_path.replace('.png', '.tavern.json')
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
            self.verbose_print(f"  Saved JSON: {os.path.basename(json_path)}")
            
            if not quiet:
                if self.verbose:
                    print(f"✓ Extracted via {extraction_method} -> {os.path.basename(output_path)}")
                else:
                    print(f"✓")
            
            self.stats['success'] += 1
            return True
            
        except Exception as e:
            if not quiet:
                print(f"✗ Error saving: {str(e)}")
            self.stats['failed'] += 1
            self.failed_files.append(input_path)
            return False


    def get_database_stats(self):
        """Get statistics about the database content"""
        if not self.db_cursor:
            return None
        
        stats = {}
        
        # Total character configs
        self.db_cursor.execute("SELECT COUNT(*) FROM CharacterConfig")
        stats['total_configs'] = self.db_cursor.fetchone()[0]
        
        # Non-user characters
        self.db_cursor.execute("""
            SELECT COUNT(*) FROM CharacterConfig 
            WHERE isUserControlled = 0 AND isDefaultUserCharacter = 0
        """)
        stats['non_user_chars'] = self.db_cursor.fetchone()[0]
        
        # Characters with images
        self.db_cursor.execute("""
            SELECT COUNT(DISTINCT ccv.id)
            FROM CharacterConfigVersion ccv
            JOIN CharacterConfig cc ON ccv.characterConfigId = cc.id
            JOIN _AppImageToCharacterConfigVersion aitc ON ccv.id = aitc.B
            WHERE cc.isUserControlled = 0 AND cc.isDefaultUserCharacter = 0
        """)
        stats['chars_with_images'] = self.db_cursor.fetchone()[0]
        
        # Characters without images  
        self.db_cursor.execute("""
            SELECT COUNT(DISTINCT ccv.id)
            FROM CharacterConfigVersion ccv
            JOIN CharacterConfig cc ON ccv.characterConfigId = cc.id
            LEFT JOIN _AppImageToCharacterConfigVersion aitc ON ccv.id = aitc.B
            WHERE cc.isUserControlled = 0 AND cc.isDefaultUserCharacter = 0
            AND aitc.B IS NULL
        """)
        stats['chars_without_images'] = self.db_cursor.fetchone()[0]
        
        return stats
    
    def save_tavern_card(self, char_data, original_png, output_path):
        """Save character data as TavernAI card"""
        # Remove display_name from the data that goes into the card
        card_data = char_data.copy()
        if 'display_name' in card_data:
            del card_data['display_name']
        
        # Add metadata
        card_data['metadata'] = {
            'version': 1,
            'created': int(time.time() * 1000),
            'modified': int(time.time() * 1000),
            'tool': {
                'name': 'BackyardAI to TavernAI Converter',
                'version': '4.0.0',
                'source': 'Optimized Edition'
            }
        }
        
        # Encode as base64
        json_str = json.dumps(card_data, ensure_ascii=False)
        chara_base64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        
        # Parse PNG chunks
        chunks = self.read_png_chunks(original_png)
        
        # Remove existing tEXt chunks with 'chara' keyword
        chunks = [c for c in chunks if not (c['type'] == 'tEXt' and b'chara\x00' in c.get('data', b''))]
        
        # Create new tEXt chunk
        chara_data = b'chara\x00' + chara_base64.encode('latin-1')
        chara_chunk = {
            'type': 'tEXt',
            'data': chara_data,
            'crc': zlib.crc32(b'tEXt' + chara_data) & 0xffffffff
        }
        
        # Insert before IEND
        iend_index = next((i for i, c in enumerate(chunks) if c['type'] == 'IEND'), len(chunks)-1)
        chunks.insert(iend_index, chara_chunk)
        
        # Write new PNG
        with open(output_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n')
            for chunk in chunks:
                length = pack(">I", len(chunk['data']))
                chunk_type = chunk['type'].encode('ascii')
                crc = pack(">I", chunk['crc'])
                f.write(length + chunk_type + chunk['data'] + crc)
    
    def read_png_chunks(self, data):
        """Read PNG chunks from data"""
        pos = 8  # Skip signature
        chunks = []
        while pos < len(data):
            if pos + 8 > len(data):
                break
            length = unpack(">I", data[pos:pos + 4])[0]
            chunk_type = data[pos + 4:pos + 8].decode('ascii', errors='ignore')
            
            if pos + 8 + length > len(data):
                break
                
            chunk_data = data[pos + 8:pos + 8 + length]
            crc = unpack(">I", data[pos + 8 + length:pos + 12 + length])[0] if pos + 12 + length <= len(data) else 0
            
            chunks.append({
                'type': chunk_type,
                'data': chunk_data,
                'crc': crc
            })
            pos += 12 + length
            if chunk_type == 'IEND':
                break
        return chunks
    

    def get_character_files_from_db(self):
        """Get all character files from the BackyardAI database"""
        if not self.db_cursor:
            return []
        
        try:
            # Modified query to include characters without images using LEFT JOIN
            query = """
            SELECT DISTINCT 
                ccv.id as version_id,
                ccv.name,
                ccv.displayName,
                ccv.persona,
                ai.imageUrl,
                MAX(c.greetingDialogue) as greetingDialogue,
                MAX(c.customDialogue) as customDialogue
            FROM CharacterConfig cc
            JOIN CharacterConfigVersion ccv ON cc.id = ccv.characterConfigId
            LEFT JOIN _AppImageToCharacterConfigVersion aitc ON ccv.id = aitc.B
            LEFT JOIN AppImage ai ON aitc.A = ai.id
            LEFT JOIN _CharacterConfigToGroupConfig ccgc ON cc.id = ccgc.A
            LEFT JOIN GroupConfig gc ON ccgc.B = gc.id
            LEFT JOIN Chat c ON gc.id = c.groupConfigId
            WHERE cc.isUserControlled = 0 
            AND cc.isDefaultUserCharacter = 0
            GROUP BY ccv.id, ccv.name, ccv.displayName, ccv.persona, ai.imageUrl
            ORDER BY ccv.name
            """
            
            self.db_cursor.execute(query)
            character_files = []
            seen_versions = set()  # Track character versions to avoid true duplicates
            
            for row in self.db_cursor.fetchall():
                version_id, name, display_name, persona, image_url, greeting, custom_dialogue = row
                
                # Skip if we've already processed this character version
                if version_id in seen_versions:
                    continue
                seen_versions.add(version_id)
                
                # Include all characters, even without images
                character_info = {
                    'version_id': version_id,
                    'name': name or 'Unknown',
                    'display_name': display_name,
                    'persona': persona,
                    'greeting': greeting,
                    'custom_dialogue': custom_dialogue,
                    'has_image': False,
                    'path': None
                }
                
                # Check if image exists
                if image_url:
                    normalized_path = os.path.normpath(image_url)
                    if os.path.exists(normalized_path):
                        character_info['path'] = normalized_path
                        character_info['has_image'] = True
                    else:
                        self.debug_print(f"Image not found for {name}: {image_url}")
                
                character_files.append(character_info)
            
            return character_files
            
        except Exception as e:
            print(f"Error reading database: {str(e)}")
            import traceback
            traceback.print_exc()
            return []


    def convert_batch(self, files, output_dir='converted_cards'):
        """Convert multiple files"""
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating output directory: {str(e)}")
            return
        
        # Set the total count once at the beginning
        self.stats['total'] = len(files)
        
        no_image_count = sum(1 for f in files if not f.get('has_image', True))
        if no_image_count > 0:
            print(f"\nNote: {no_image_count} characters have no images (will export as JSON only)")
        
        print(f"\nConverting {len(files)} characters to: {output_dir}")
        print("-" * 60)
        
        for i, file_info in enumerate(files, 1):
            if isinstance(file_info, dict):
                char_name = file_info.get('name', 'Unknown')
                display_name = file_info.get('display_name', '')
                has_image = file_info.get('has_image', True)
                
                # Create display text for progress
                display_text = char_name[:30]
                if display_name and display_name != char_name:
                    display_text += f" ({display_name[:20]})"
                
                # Handle characters without images
                if not has_image:
                    display_text += " [JSON-only]"
                    print(f"[{i}/{len(files)}] Converting: {display_text}...", end=' ')
                    
                    # Extract character data directly from the database info
                    char_data = {
                        'name': char_name,
                        'display_name': display_name or char_name,
                        'description': file_info.get('persona', ''),
                        'personality': '',
                        'scenario': '',
                        'first_mes': file_info.get('greeting', ''),
                        'mes_example': file_info.get('custom_dialogue', ''),
                    }
                    
                    # Parse persona field if available
                    if file_info.get('persona'):
                        char_data = self.parse_persona_field(file_info['persona'], char_data)
                    
                    # Save as JSON only
                    safe_name = self.sanitize_filename(char_name)[:100]
                    if display_name and display_name != char_name:
                        safe_display = self.sanitize_filename(display_name)[:50]
                        json_filename = f"{safe_name} ({safe_display}).tavern.json"
                    else:
                        json_filename = f"{safe_name}.tavern.json"
                    
                    json_path = os.path.join(output_dir, json_filename)
                    json_path = self.generate_unique_filename(json_path)
                    
                    try:
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(char_data, f, indent=2, ensure_ascii=False)
                        print("✓ (JSON)")
                        self.stats['success'] += 1
                        self.stats['json_only'] += 1
                    except Exception as e:
                        print(f"✗ {str(e)}")
                        self.stats['failed'] += 1
                    
                    continue
                
                # Normal processing for characters with images
                file_path = file_info['path']
                
                # Generate proper output filename based on character names
                safe_name = self.sanitize_filename(char_name)[:100]
                if display_name and display_name != char_name:
                    safe_display = self.sanitize_filename(display_name)[:50]
                    output_filename = f"{safe_name} ({safe_display}).tavern.png"
                else:
                    output_filename = f"{safe_name}.tavern.png"
                
                output_path = os.path.join(output_dir, output_filename)
                
                print(f"[{i}/{len(files)}] Converting: {display_text}...", end=' ')
                
                # Ensure unique filename
                output_path = self.generate_unique_filename(output_path)
                
                # Pass from_batch=True to prevent double counting
                success = self.convert_file(file_path, output_path, quiet=True, from_batch=True)
                
                if success:
                    self.stats['png_files'] += 1
                else:
                    print("✗")
            else:
                # Legacy support for simple file paths  
                file_path = file_info
                display_text = os.path.basename(file_path)[:50]
                output_path = None
                
                print(f"[{i}/{len(files)}] Converting: {display_text}...", end=' ')
                # Also pass from_batch=True here
                success = self.convert_file(file_path, output_path, quiet=True, from_batch=True)
                
                if not success:
                    print("✗")


    def print_summary(self):
        """Print conversion summary"""
        print("\n" + "=" * 60)
        print("Conversion Summary")
        print("-" * 60)
        print(f"Total characters: {self.stats['total']}")
        print(f"Successful: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        
        json_only = self.stats.get('json_only', 0)
        png_count = self.stats['success'] - json_only
        
        if self.stats['success'] > 0:
            if png_count > 0:
                print(f"\n✓ Generated {png_count} PNG files (with embedded data)")
                print(f"✓ Generated {png_count} accompanying JSON files")
            if json_only > 0:
                print(f"✓ Generated {json_only} JSON-only files (no image)")
        
        if self.stats['method_usage']:
            print("\nExtraction methods used:")
            for method, count in sorted(self.stats['method_usage'].items(), 
                                    key=lambda x: x[1], reverse=True):
                percentage = (count / png_count * 100) if png_count > 0 else 0
                print(f"  {method}: {count} ({percentage:.1f}%)")
        
        if self.failed_files:
            print(f"\nFailed files ({len(self.failed_files)}):")
            for file_path in self.failed_files[:5]:  # Show first 5
                print(f"  - {os.path.basename(file_path)}")
            if len(self.failed_files) > 5:
                print(f"  ... and {len(self.failed_files) - 5} more")
        
        print("\nConversion complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Convert BackyardAI character cards to TavernAI format (Optimized)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Convert single file:
    %(prog)s "character.png"
    
  Convert from database:
    %(prog)s --database
    
  Convert from custom database:
    %(prog)s --database "path/to/db.sqlite"
    
  Convert with debug output:
    %(prog)s --database --debug
    
Note: Both PNG and JSON files are always generated for each character.
        """
    )
    
    parser.add_argument('input_file', nargs='?', help='Single PNG file to convert')
    parser.add_argument('--database', '-d', nargs='?', const='default', 
                       help='Convert all from BackyardAI database')
    parser.add_argument('--output-dir', '-o', default='converted_cards',
                       help='Output directory (default: converted_cards)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create converter
    converter = BackyardToTavernConverter(debug=args.debug, verbose=args.verbose)
    
    if args.database:
        # Database batch mode
        db_path = None if args.database == 'default' else args.database
        
        if converter.open_database(db_path):
            print("=" * 60)
            print("BackyardAI Database Batch Conversion")
            print("=" * 60)
            
            # Show database statistics
            db_stats = converter.get_database_stats()
            if db_stats:
                print("\nDatabase Statistics:")
                print(f"  Total character configs: {db_stats['total_configs']}")
                print(f"  Non-user characters: {db_stats['non_user_chars']}")
                print(f"  Characters with images: {db_stats['chars_with_images']}")
                print(f"  Characters without images: {db_stats['chars_without_images']}")
                print(f"  Expected total to export: {db_stats['chars_with_images'] + db_stats['chars_without_images']}")
                print()
            
            files = converter.get_character_files_from_db()
            if files:
                print(f"Found {len(files)} character files in database")
                converter.convert_batch(files, args.output_dir)
            else:
                print("No character files found in database")
            
            converter.close_database()
            converter.print_summary()
        else:
            print("Failed to open database")
            if args.database == 'default':
                print(f"Default location: {converter.get_default_db_path()}")
                print("Use --database with a path to specify a different location")
        
    elif args.input_file:
        # Single file mode
        input_file = args.input_file.strip('"')
        
        # Try with database support for better extraction
        converter.open_database()
        
        print(f"Converting: {os.path.basename(input_file)}")
        success = converter.convert_file(input_file, use_database=converter.db_cursor is not None)
        
        converter.close_database()
        
        if success:
            print("✓ Conversion successful!")
            print("  Generated .tavern.png and .tavern.json files")
        else:
            print("\n✗ Conversion failed")
            if not args.debug:
                print("Tip: Run with --debug for more information")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
