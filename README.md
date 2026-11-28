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

Pass `-ProjectDir`, `-BuildDir`, or `-ToolchainBin` to select a different build location. The launcher stages its own configuration, runtime, and test saves under `work/localization-runtime/<port>/`. Choose `-Lang jp` to launch the Japanese runtime. In-game memory-card saves work across languages. Emulator savestates must match the runtime's RAM size. When copying an English emulator checkpoint, keep its `.pst` and matching `.hdres` together to preserve translated menu and card artwork.

## Status

- The audit covers 2,462 tracked translations, 13 functional keypad records, all 674 mapped card text slots, and all 82 Zoid type and ability slots. The runtime includes 19 Zoid labels outside the original inventory.
- Both factions' Battle Results screens displayed English headings and point totals in a test build that opens Results from deployment. In regular play, Republic training ended on turn eight with 2,000 points and advanced to the next briefing. A Stage 2 battle verified the English Custom and Move Phase headings and seven hand thumbnails after transferring a checkpoint to another emulator. Full campaign playthroughs remain open.
- A normal Free Mode sortie displayed English objectives, Player Turn and Enemy Turn banners, and the Draw, Custom, Move and Fight phases. Card selection and the equip-target screen were spot-checked in-game.
- The English runtime wraps long battle dialogue at fourteen glyphs per line. An extended objective and the End Turn choice were tested in the native renderer by opening their scripts in a disposable battle. The choice opens on the last page and passes Yes and No back to the original script. Other script layouts still need in-game coverage.
- The audit covers 139 references to short dialogue fragments outside the original inventory. The English runtime inserts player names, card names, and amounts before wrapping the text to fit the battle panel.
- All 274 card thumbnails carry the English rule or stat panel from the matching full-size face, including captured dimmed variants. The full-size Zoid cards include 49 printed special rules, 35 verified dimension strips, and nine pilot or variant captions. Both Liger Zero variants retain the original printed frontal melee bonus digits pending a clearer reference. Range and movement modifiers on 67 Zoid faces use the values in the game's card records. All 119 Japanese rule records used by the 193 Custom, Event, and Pilot faces have been reviewed. The 32 Pilot terrain badges and the equipment and property markings on 88 Custom faces are in English. Forty-six Zoid dimension strips still need verification.
- The Card Album, Zoid Album, and Movie Album were spot-checked in-game. The Movie Album audit maps all 153 tiles to their disc clips. Death Saurer's melee and ranged clips replayed and returned to the grid, and Special clips use an English SP badge. The English OpenGL runtime overlays the opening's title, dialogue, map labels, and battle phase. Both the moving banners and the printed text on the Whale King and Missile Pod faces show English names and rules. Further replay testing remains open.
- The five ending-credit textures have English titles, roles, and names. The English runtime reads the original background pages from the mounted disc so the roll can continue after the campaign.
- The offline audio screen covers all 155 movie clips. The per-clip review records 59 candidates for listening. It found no dialogue reliable enough to add a subtitle.

## Edit and audit

Run these commands after editing the Python translation dictionaries. Texture builders use Pillow and the locally extracted files. Rebuilding captured fade variants also requires local texture dumps from a `-TextureDump` run.

```powershell
python -B -X utf8 tools/build_phase2.py
python -B -X utf8 tools/build_card_short.py
python -B -X utf8 tools/update_text_tracker.py
python -B -X utf8 tools/audit_translations.py
```

The texture builders are `tools/build_ui_textures.py`, `tools/build_stage_titles.py`, `tools/build_card_faces.py`, and `tools/build_credits.py`. The launcher loads the three live translation tables and the pack under `work/localization-textures/SLPS-03255/`.
