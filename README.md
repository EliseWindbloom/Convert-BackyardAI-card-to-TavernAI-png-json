# Convert-BackyardAI-card-to-TavernAI-card-json
**BackyardAI to TavernAI version 14**  

***Update, Faraday.dev has officially rebranded as BackyardAI: https://backyard.ai/blog/rebranding-to-backyard***

-Currently BackyardAI(previously known as Faraday) can export PNG character cards, however these cards seem to only work with BackyardAI and not with other character AI apps.  

-This small script converts BackyardAI PNG character cards to TavernAI json files/TavernAI character card PNGs, enabling compatibility and the ability to share your cards with most other character AI apps.  
-This can also now optionally convert the entire database of your BackyardAI cards in one go.  

[Faraday video installation guide](https://www.youtube.com/watch?v=i_vM8T-oXSw) (NSFW)

## Features

- Converts BackyardAI PNG character cards to TavernAI JSON and PNG formats

## Requirments

[BackyardAI](https://backyard.ai/) (App that allows you to chat with AI Characters Offline)

[Python](https://www.python.org/)

## Setup Python (outputs a TavernAI PNG file and TavernAI JSON file)

1) Download and install Python. then run this command on command line to install pillow `pip install "Pillow>=10.1.0"`
2) Make or load a character in BackyardAI, then go to the Home area -> click on the 3 vertical dots next to the card you want -> click on "Export To PNG" like [this](https://files.catbox.moe/i7zusw.png)
3) Download this repository by clicking on Code -> Download zip, then extract on your pc.
4) Drag-n-Drop your BackyardAI(Faraday) png to **"_BackyardAI_To_TavernAI (drag & drop backyardAI png here).bat"** to convert to TarvernAI json and TarvernAI png character card.
   - alternately, run `python backyard_to_tavern.py <file_path>` on command line a single backyardAI png to TarvernAI png/json.
   - or you can try "faraday2tavern.py" in unused folder, though this might only output a json file and probably won't work on most faraday pngs.
   - or you can try "BackyardAI card to TavernAI json v4.au3" in unused folder which requires [Autoit](https://www.autoitscript.com/cgi-bin/getfile.pl?autoit3/autoit-v3-setup.zip), though it's been depericated, only generates a json on microsoft windows and doesn't work on most faraday pngs.

## Installation

1. Install [Python 3.10](https://www.python.org/downloads/release/python-3106/) or higher
2. Download this [repo](https://github.com/EliseWindbloom/Convert-BackyardAI-card-to-TavernAI-png-json/archive/refs/heads/main.zip) and extract it.
3. Run Command Line and install pillow using this command:
   ```bash
   pip install "Pillow>=10.1.0"
   ```

## Usage

### Method 1: Drag and Drop (Windows)
Simply drag and drop your BackyardAI PNG onto **"_BackyardAI_To_TavernAI (drag & drop backyardAI png here).bat"**

### Method 2: Command Line

For single file conversion:
```bash
python backyard_to_tavern.py <path_to_png>
```

For batch conversion from database (converts all your BackyardAI cards and saves to "converted_cards" folder):
```bash
python backyard_to_tavern.py --database <path_to_db.sqlite>
```

Default database locations:
- Windows: `%APPDATA%\faraday\db.sqlite`
- macOS: `~/Library/Application Support/faraday/db.sqlite`
- Linux: `~/.local/share/faraday/db.sqlite`

## Output

The script generates:
1. A TavernAI-compatible PNG character card
2. A TavernAI JSON file with character data

## Version History

- **v14**: Current stable release
  - Second major rebuild, much better PNG/JSON handling for conversions
  - Optional, extract entire database to convert all your BackyardAI cards to Tavern AI cards (Was able to successfully convert entire database without error when testing)

- **v5 to v13**: (developmental)
  
- **v4**: Rebuild from stratch in part to (attempt to) fix conversion errors and handle Faraday's format better

### Additional Previous Versions
- **faraday2tavern.py** (This version was created by Hukasx0):
   - Based on autoit version, uses python to convert cards
 
- **BackyardAI card to TavernAI json v4.au3**:
   - Initial release, uses autoit to attempt to convert cards
