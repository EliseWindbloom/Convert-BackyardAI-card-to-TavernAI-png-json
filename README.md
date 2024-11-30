# Convert-BackyardAI-card-to-TavernAI-card-json
***Update, Faraday.dev has officially rebranded as BackyardAI: https://backyard.ai/blog/rebranding-to-backyard***

-Currently BackyardAI(previously known as Faraday) can export PNG character cards, however these cards seem to only work with BackyardAI and not with other character AI apps.

-These small scripts converts BackyardAI PNG character cards to TavernAI json files/TavernAI character card PNGs, enabling compatibility and the ability to share your cards with most other character AI apps.

[Faraday video installation guide](https://www.youtube.com/watch?v=i_vM8T-oXSw) (NSFW)

## Features

- Converts BackyardAI PNG character cards to TavernAI JSON and PNG formats
- Supports both single file and batch database conversion
- Robust metadata extraction and preservation
- Cross-platform compatibility (Windows, macOS, Linux)
- Handles complex PNG file structures
- Comprehensive error handling and recovery

## Requirments

[BackyardAI](https://backyard.ai/) (App that allows you to chat with AI Characters Offline)

[Python](https://www.python.org/)

## Setup Python (outputs a TavernAI PNG file and TavernAI JSON file)

1) Download and install Python. then run this command on command line to install pillow `pip install "Pillow>=10.1.0"`
2) Make or load a character in BackyardAI, then go to the Home area -> click on the 3 vertical dots next to the card you want -> click on "Export To PNG" like [this](https://files.catbox.moe/i7zusw.png)
3) Download this repository by clicking on Code -> Download zip, then extract on your pc.
4) Drag-n-Drop your BackyardAI(Faraday) png to **"_BackyardAI_To_TavernAI (drag & drop backyardAI png here).bat"** to convert to TarvernAI json and TarvernAI png character card.
   - alternately, run `python backyard_to_tavern_v8.py --single <file_path>` on command line a single backyardAI png to TarvernAI png/json.
   - alternately, run `python backyard_to_tavern_v8.py --database <path/to/faraday/db.sqlite>` on command line to convert all the backyardAI pngs to TarvernAI pngs/jsons.
   - or you can try "faraday2tavern.py" in unused folder, though this might only output a json file and probably won't work on most faraday pngs.
   - or you can try "BackyardAI card to TavernAI json v4.au3" in unused folder which requires [Autoit](https://www.autoitscript.com/cgi-bin/getfile.pl?autoit3/autoit-v3-setup.zip), though it's been depericated, only generates a json on microsoft windows and doesn't work on most faraday pngs.

## Installation

1. Download and install Python 3.10 or higher, then run this command on command line `pip install "Pillow>=10.1.0"`
2. Download this [repo](https://github.com/EliseWindbloom/Convert-BackyardAI-card-to-TavernAI-png-json/archive/refs/heads/main.zip) and extract it.

## Usage

### Method 1: Drag and Drop (Windows)
Simply drag and drop your BackyardAI PNG onto **"_BackyardAI_To_TavernAI (drag & drop backyardAI png here).bat"**

### Method 2: Command Line

For single file conversion:
```bash
python backyard_to_tavern.py --single <path_to_png>
```

To convert all the BackyardAI cards from BackyardAI's database:
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
2. A corresponding JSON file with character data

## Version History

- v10: Current stable release
  - Improved database extraction
  - Enhanced PNG metadata handling
  - Better error recovery
  - Cross-platform compatibility improvements
