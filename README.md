# Convert-Faraday-card-to-TavernAI-card-json
-Currently Faraday can export PNG character cards, however these cards seem to only work with Faraday and not with other character AI apps.

-These small scripts converts Faraday PNG character cards to TavernAI json files/TavernAI character card PNGs, enabling compatibility and the ability to share your cards with most other character AI apps.

[Faraday video installation guide](https://www.youtube.com/watch?v=Z-Jh2csesqc) (NSFW)

<h3> ====Requirments==== </h3>

[Faraday](https://faraday.dev/) (App that allows you to chat with AI Characters Offline)

[Autoit](https://www.autoitscript.com/cgi-bin/getfile.pl?autoit3/autoit-v3-setup.zip) (Scripting/Automation Language)
or [Python](https://www.python.org/)

PC running Microsoft Windows (required for Autoit)

<h3> ==Setup Autoit (outputs a TavernAI JSON file)== </h3>

1) Download and install both Faraday and Autoit
2) Make or load a character in Faraday, then go to the Home area -> click on the 3 vertical dots next to the card you want -> click on "Export To PNG" like [this](https://files.catbox.moe/i7zusw.png) 
3) Download *Faraday card to TavernAI json v3.au3* in this repository, run it and choose the PNG file you just exported.
4) A JSON file will automatically be generated, this TarvernAI json file should be much more compatiable with different AI character apps than the Faraday card.

<h3> ==Setup Python (outputs a TavernAI JSON file and TavernAI PNG file)== </h3>

1) Download Python
2) Make or load a character in Faraday, then go to the Home area -> click on the 3 vertical dots next to the card you want -> click on "Export To PNG" like [this](https://files.catbox.moe/i7zusw.png)
3) Download *faraday2tavern.py*
4) run script like this `python faraday2tavern.py <file_path>`
5) A JSON and Png (character card) file will be generated, this TarvernAI json file and character card file should be more compatiable with different AI character apps than the Faraday card.
