# Zoids Battle Card Game — Western War

An English localization for the Japanese PlayStation release of *Zoids Battle Card Game: Seihou Tairiku Senki* (SLPS-03255), running on the Windows PSXRecomp REFERENCE build.

The project includes English text tables, a staged launcher, and an edited OpenGL texture pack. The stock disc image, extracted game files, runtime binaries, and saves are supplied locally.

## Run the English build

1. Prepare a compatible Windows REFERENCE checkout and Ninja build using the [PSXRecomp project setup guide](https://github.com/mstan/psxrecomp/blob/master/docs/GAME_PROJECT_SETUP.md). The tested setup uses the Zoids project at `~/zoids-recomp/zoids-battle-card-game` and the Retcomm CMake/Clang toolchain. The launcher requires the matching build objects and runtime source alongside the executable because it relinks the translation runtime.
2. Place your SLPS-03255 CUE/BIN pair in this directory. Keep the CUE's track reference correct and use the base name `Zoids - Battle Card Game - Seihou Tairiku Senki (Japan)` for both files.
3. Run the following in PowerShell with Python 3.11 or later available.

```powershell
python -B -X utf8 tools/extract.py
& .\tools\run_recomp.ps1 -Lang en
```

Pass `-ProjectDir`, `-BuildDir`, or `-ToolchainBin` to select a different build location. The launcher stages its own configuration, runtime, and test saves under `work/localization-runtime/<port>/`. Choose `-Lang jp` to launch the Japanese runtime. In-game memory-card saves work across languages. Emulator savestates must match the runtime's RAM size.

## Status

- The audit covers 2,462 translated text records, 13 functional keypad records, and all 674 mapped card text slots.
- Both factions' Battle Results were verified in the native OpenGL renderer using a test build that opens Results from deployment. A normal Free Mode sortie now reaches the English objectives, Draw Phase, and first-turn Custom Phase. Card selection and the equip-target screen were spot-checked in-game. Full battles and campaign playthroughs remain unverified.
- The English runtime wraps long battle dialogue at fourteen glyphs per line and adds pages when the script normally pauses for confirmation. Both pages of an extended objective panel were tested in the native renderer. Other script layouts and a full campaign still need in-game coverage.
- The texture pack includes 274 full-size card overlays and 274 thumbnail name bands. The 193 CEP rules are draft translations. Some printed Zoid special abilities and small legends still need translation.
- The Card Album, Zoid Album, and locked Movie Album were spot-checked in-game. Unlocked movie entries and subtitle work are still open.

## Edit and audit

Run these commands after editing the Python translation dictionaries. Texture builders use Pillow and the locally extracted files. Rebuilding captured fade variants also requires local texture dumps from a `-TextureDump` run.

```powershell
python -B -X utf8 tools/build_phase2.py
python -B -X utf8 tools/build_card_short.py
python -B -X utf8 tools/update_text_tracker.py
python -B -X utf8 tools/audit_translations.py
```

The texture builders are `tools/build_ui_textures.py`, `tools/build_stage_titles.py`, and `tools/build_card_faces.py`. The launcher loads the three live translation tables and the pack under `work/localization-textures/SLPS-03255/`.
