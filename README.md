# SugarLump

Simple parser / extractor for starlight engine SLF files. No one did this so I did.
It's just dumb pixel packing on a file, splitted bu header and resources. Take a look at the hexpat file under IMHex or even the python script to understand it more. Tested on beta / demo version of the engine. Can't garantee to work with any version.
Warning, the engine file are quite messy. You'll end of with a lot of unexpected assets that somehow got packed into prod ...

## Usage

Install [python](https://www.python.org/downloads/), then install Pillow: `python -m pip install Pillow`

Then put the `loaf.py` file next to the engine and run `python loaf.py -o DATAExt/UI "Games\AdventureMode\Chapter C\Datafiles\UI.slf"` (change to the output path and slf path)


## Repack / modding 
Not hard, but to be done. I'm not interested in the engine as it's proprietary and not documented at all + RPG Maker MV is far supperior to quickly iterate than custom LUA / C++ engine.

## TODO

Support `AUTOLOAD00` blocks ?
Support `MAPINFO000` to convert maps to Tiled + RPG Maker JSON ?

Future plans ? Port it to rpg maker, add a SLF file loader and see if the browser like that !

