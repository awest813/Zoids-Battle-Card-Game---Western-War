# Zoids Battle Card Game — Western War

An English localization for the Japanese PlayStation release of *Zoids Battle Card Game: Seihou Tairiku Senki* (SLPS-03255), running on the Windows PSXRecomp REFERENCE build.

The project includes English text tables, a staged launcher, and an edited OpenGL texture pack. The stock disc image, extracted game files, runtime binaries, and saves are supplied locally.

## Run the English build

1. Prepare a compatible Windows REFERENCE checkout and Ninja build using the [PSXRecomp project setup guide](https://github.com/mstan/psxrecomp/blob/master/docs/GAME_PROJECT_SETUP.md). The tested setup uses the Zoids project at `~/zoids-recomp/zoids-battle-card-game` and the Retcomm CMake/Clang toolchain. The launcher requires the matching build objects and runtime source alongside the executable to build the localized text and OpenGL caption support.
2. Place your SLPS-03255 CUE/BIN pair in this directory. Keep the CUE's track reference correct and use the base name `Zoids - Battle Card Game - Seihou Tairiku Senki (Japan)` for both files.
3. Run the following in PowerShell with Python 3.11 or later available.

```powershell
python -B -X utf8 tools/extract.py
& .\tools\run_recomp.ps1 -Lang en
```

Pass `-ProjectDir`, `-BuildDir`, or `-ToolchainBin` to select a different build location. The launcher stages its own configuration, runtime, and test saves under `work/localization-runtime/<port>/`. Choose `-Lang jp` to launch the Japanese runtime. In-game memory-card saves work across languages. Emulator savestates must match the runtime's RAM size.

## Status

- The audit covers 2,462 tracked translations, 13 functional keypad records, all 674 mapped card text slots, and all 82 Zoid type and ability slots. The runtime includes 19 Zoid labels outside the original inventory.
- Both factions' Battle Results were verified in the native OpenGL renderer using a test build that opens Results from deployment. A normal Free Mode sortie displayed English objectives, Player Turn and Enemy Turn banners, and the Draw, Custom, Move and Fight phases. Card selection and the equip-target screen were spot-checked in-game. Full battles and campaign playthroughs remain unverified.
- The English runtime wraps long battle dialogue at fourteen glyphs per line. An extended objective and the End Turn choice were tested in the native renderer by opening their scripts in a disposable battle. The choice opens on the last page and passes Yes and No back to the original script. Other script layouts still need in-game coverage.
- The audit covers 139 references to short dialogue fragments outside the original inventory. The English runtime inserts player names, card names, and amounts before wrapping the text to fit the battle panel.
- The texture pack includes 274 full-size card overlays, 274 thumbnail name bands, and English wording for all 49 Zoid faces with printed special rules. Both Liger Zero variants retain the original printed frontal melee bonus digits pending a clearer reference. Range and movement modifiers on 67 Zoid faces use the values in the game's card records. The English rules on 111 Custom, Event, and Pilot faces have been checked against the Japanese game text. The other 82 faces and some small card legends still need review.
- The Card Album, Zoid Album, and Movie Album were spot-checked in-game. The Movie Album audit maps all 153 tiles to their disc clips. Death Saurer's melee and ranged clips replayed and returned to the grid, and Special clips use an English SP badge. The English OpenGL runtime overlays the opening's title, dialogue, map labels, and battle phase. The moving card banners show English names and rules for Whale King and Missile Pod. The card images inside the movie still have their original print. Movie audio and further replay testing remain open.

## Edit and audit

Run these commands after editing the Python translation dictionaries. Texture builders use Pillow and the locally extracted files. Rebuilding captured fade variants also requires local texture dumps from a `-TextureDump` run.

```powershell
python -B -X utf8 tools/build_phase2.py
python -B -X utf8 tools/build_card_short.py
python -B -X utf8 tools/update_text_tracker.py
python -B -X utf8 tools/audit_translations.py
```

The texture builders are `tools/build_ui_textures.py`, `tools/build_stage_titles.py`, and `tools/build_card_faces.py`. The launcher loads the three live translation tables and the pack under `work/localization-textures/SLPS-03255/`.
