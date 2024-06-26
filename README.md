# Convert-BackyardAI-card-to-TavernAI-card-json
***Update, Faraday.dev has officially rebranded as BackyardAI: https://backyard.ai/blog/rebranding-to-backyard***

-Currently BackyardAI(previously known as Faraday) can export PNG character cards, however these cards seem to only work with BackyardAI and not with other character AI apps.

-These small scripts converts BackyardAI PNG character cards to TavernAI json files/TavernAI character card PNGs, enabling compatibility and the ability to share your cards with most other character AI apps.

[Faraday video installation guide](https://www.youtube.com/watch?v=i_vM8T-oXSw) (NSFW)

## Requirments

[BackyardAI](https://backyard.ai/) (App that allows you to chat with AI Characters Offline)

[Python](https://www.python.org/)

## Setup Python (outputs a TavernAI PNG file and TavernAI JSON file)

1) Download and install Python
2) Make or load a character in BackyardAI, then go to the Home area -> click on the 3 vertical dots next to the card you want -> click on "Export To PNG" like [this](https://files.catbox.moe/i7zusw.png)
3) Download this repository by clicking on Code -> Download zip, then extract on your pc.
4) Drag-n-Drop your BackyardAI(Faraday) png to **"_BackyardAI_To_TavernAI (drag & drop backyardAI png here).bat"** to convert to TarvernAI json and TarvernAI png character card.
   - alternately, run the script like this `python convert_backyardai_to_tavern_v4.py <file_path>` on command line if you're not on windows.
   - or you can try "faraday2tavern.py" in unused folder, though this might only output a json file and probably won't work on most faraday pngs.
   - or you can try "BackyardAI card to TavernAI json v4.au3" in unused folder which requires [Autoit](https://www.autoitscript.com/cgi-bin/getfile.pl?autoit3/autoit-v3-setup.zip), though it's been depericated, only generates a json on microsoft windows and doesn't work on most faraday pngs.
