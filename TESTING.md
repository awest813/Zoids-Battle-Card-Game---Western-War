# TESTING.md — Running and Verifying the Build

---

## 1. Launch commands

### Windowed English build (normal play)

```powershell
powershell -ExecutionPolicy Bypass -File tools\run_recomp.ps1 `
  -BuildDir build-reference -Port 4371 -Lang en
```

### Headless build (automation / screenshots)

```powershell
powershell -ExecutionPolicy Bypass -File tools\run_recomp.ps1 `
  -Headless -BuildDir build-reference -Port 4371 -Lang en -Capture
```

`-Capture` enables the string inventory scan. Leave it off for normal play; it costs CPU.

### Staged build

The launcher uses the REFERENCE build as input and stages the executable, config, current tables, and mod catalog under `work/localization-runtime/<port>/`. English uses the local CMake/Ninja toolchain to rebuild the translation runtime on the first launch. It reserves expanded guest RAM for translated strings, away from the original game's asset buffers and stack. The stage uses the config from its own directory. Test saves are scoped to the port. Use `-SaveDir` to point to a copy of an existing memory card.

Use the in-game memory-card save to move between Japanese and English. Emulator savestates record RAM geometry, so a 2 MiB state from an older English build or the Japanese launch cannot load in the current 8 MiB English runtime. Start from a fresh boot when the translation tables change between test runs.

To test the original UI, launch with `-Lang jp`. To test English without the texture pack, add `-NoTextures`. To collect more OpenGL textures, use `-TextureDump`. The dump and replacement folders live under `work/localization-textures/SLPS-03255/`.

```powershell
python -B -X utf8 tools\build_ui_textures.py
python -B -X utf8 tools\build_stage_titles.py
python -B -X utf8 tools\build_card_faces.py
```

The renderer uses the staged OpenGL pack automatically in English. Use `present_shot` in a windowed session to inspect replacement pixels. `screenshot_file` captures native VRAM with the original artwork.

---

## 2. Debug server

The runtime listens on TCP `4371` (one JSON command per connection).

Useful commands:

| Command | Purpose |
|---|---|
| `{"cmd":"xlate","sub":"stats"}` | translation counters and pointer status |
| `{"cmd":"xlate","sub":"reload"}` | reload TOMLs (pointer tables may need a moment to repair) |
| `{"cmd":"screenshot_file","path":"..."}` | write a 320×240 PNG from VRAM |
| `{"cmd":"read_ram","addr":2147585248,"len":64}` | read guest RAM |
| `{"cmd":"get_registers"}` | PC/SP/GPR snapshot |
| `{"cmd":"savestate","op":"save","slot":0}` | save a state |
| `{"cmd":"savestate","op":"load","slot":0}` | load a state |
| `{"cmd":"set_input","buttons":"0xDFFF"}` | hold Circle (PS1 active-low) |
| `{"cmd":"clear_input"}` | release the input override |
| `{"cmd":"vram_peek","x":0,"y":0,"w":128,"h":128}` | VRAM dump |

Button bits: Start `0x0008`, Up `0x0010`, Right `0x0020`, Down `0x0040`, Left `0x0080`, Triangle `0x1000`, Circle `0x2000`, Cross `0x4000`, Square `0x8000`. Clear a bit from `0xFFFF` to press that button. Circle confirms and Cross goes back in the stock menu controls.

Helper scripts:

```powershell
python -X utf8 tools\recomp_input.py --port 4371 --press start:0.8 --wait 5 --shot work/test.png
python -X utf8 tools\ram_probe.py regs --port 4371
python -X utf8 tools\ram_probe.py read --port 4371 --addr 0x800EAB2C --len 16
```

The input helpers send active-low masks. A keyboard or controller can also be used for manual verification.

---

## 3. Fast memory-card check

The original test savestate slot 0 is at the memory-card dialog in the 2 MiB runtime. For English, use a fresh boot or save a new snapshot at the same dialog in its 8 MiB runtime.

```python
{"cmd":"savestate","op":"load","slot":0}
```

Wait a few seconds. Expected text:

- `Checking card...`
- `Please wait...`
- `Don't remove card`
- `No Zoids Battle Card Game data on this card.`
- `No scenario.`

The saved state may be from an older table; the runtime's idle sweep repairs the pointers within a few frames.

---

## 4. Test checklist

### Battle startup regression

In Free Mode, select the Republic and Ocean World. Sortie with the Republic deck and place a Shield Liger. Confirm deployment and wait for the opening objective panel. It should display `Rout foes/base` and `Lose: All down`. Confirm the panel and check that the renderer keeps advancing on the battle map.

The retail battle script renderer uses a 30-byte stack buffer for each line. The objective and deployment rows allow fourteen fullwidth glyphs plus the terminator. The translation audit checks those emitted rows against this limit. Use `python -B -X utf8 tools/audit_battle_script.py --csv` to list lines that exceed the original width in script groups that wait for confirmation.

The English runtime wraps those groups to fourteen glyphs and displays up to three lines per page. For a pagination regression test, use a disposable English stage and two objective lines that wrap to five lines total. Confirm only after the indicator appears. The first confirmation should advance to page two and the second should resume the battle. Save and reload on the second page to check that confirmation still returns to the original script. Keep the fixture text and save files local.

Add `--choices` to the script audit to scan prompts followed by Yes/No. For the End Turn prompt, confirm the first page and wait for both options on the second page. Repeat from a test state and try both answers to check that the choice advances the original script.

For dialogue with substituted values, check a greeting after naming the commander, a card acquisition or equip message, and the shop price prompt. Check that the name or number appears and that confirmation returns to the original script. In a disposable test, use a card name that pushes the message onto a second page and check each line against the fourteen-glyph limit.

### Movie inventory and opening playback

`analysis/MOVIE_INVENTORY.csv` records 155 clips from the retail disc. The opening has 1,544 frames at nominal 15 fps. The TOMY logo and 153 small clips use nominal 30 fps. `duration_seconds` describes the encoded clip. The game can leave playback earlier. Every clip has an XA audio stream. Two pairs have identical encoded audio, recorded under `matching_xa`. Whether a clip contains speech or readable text still requires review.

Run the inventory against the original BIN. To review a clip locally, extract it into the ignored `work/` directory. The clip export preserves 2,352-byte sectors, including the XA audio. Ordinary file extraction uses 2,048-byte sectors and truncates audio data.

```powershell
$DiscPath = 'Zoids - Battle Card Game - Seihou Tairiku Senki (Japan).bin'
python -B -X utf8 tools/audit_movies.py $DiscPath
python -B -X utf8 tools/audit_movies.py $DiscPath --album-exe extracted/SLPS_032.55
python -B -X utf8 tools/audit_movies.py $DiscPath --extract M/OP_MOVIE.STR --output work/opening-review.str
```

For an in-game playback check, start a fresh English stage. During the opening, `cdrom_state` reports mode `0xE0`, seek MSF `[2, 19, 51]` (LBA 10326), and a `last_sector.lba` inside the opening extent. `fmv_state` reports active XA and an increasing MDEC decode count. The test run observed 1,415 sectors over 566 emulator frames, which agrees with 150 sectors per second at 60 Hz.

`translations/zoids.movie_captions.json` maps the captions to zero-based movie frames. The start frame is inclusive and the end frame is exclusive. Caption boxes use the original clip's pixel grid. For banners that rise, `top_rows` sets the vertical position for each frame. The opening's delivered disc position typically leads the visible frame by four frames in the tested runtime. The English build checks frame ranges, box placement and text fit before linking. OpenGL draws captions at presentation time with the original XA audio.

Use `present_shot` to inspect the composed image. The movie title appears around LBA 15446. Two briefing shots follow around 15796 and 16076. During a passage with captions, skip with Start and confirm the next screen has no movie text. For a resume test, save in a disposable slot during the title and restore the state after leaving playback. Confirm the title captions reappear at the same position in the movie.

The opening's map shows Gaigalus and New Helic City. In the battle preview, inspect the Battle Phase heading and the English names and rules in the blue name banners as both cards rise and settle. Tiny lettering printed on the card images still needs replacement. The windowed REFERENCE run returned to the localized interactive title after normal playback and cleared the movie overlay immediately after a Start skip. The first interactive title frame sampled after skipping from a restored state still showed the Japanese title artwork.

The `--album-exe` report reads the original executable's catalog order and checks every tile against the disc. The 17 pages contain 63 melee, 63 ranged, 11 special, and 16 Custom/Event clips. TOMY and the opening are boot clips. In Album Mode, select Movie Album. Use L1 and R1 to change pages. Disposable unlock fixtures verified playback and return to the grid for Death Saurer's melee clip on page 1, Gustav MS on page 5, Geno Saurer's special on page 15, and All-Direction Shot on page 16. The locked tile next to Death Saurer displayed `SECRET` and did not seek to a clip on confirm. Geno Saurer displayed the red `SP` badge beside its English name.

Death Saurer's ranged clip on page 8 previously stalled in the guest file search. The staged English runtime resolves small STR paths against the mounted disc's filesystem and passes the result to the original movie player. The boot clips use the guest file search. On a fresh English run, Death Saurer's ranged clip sought to LBA 93501, displayed decoded frames with XA active, and returned to page 8. Geno Saurer's special and All-Direction Shot replayed with XA active in the same run. A disposable opening state also showed the English movie title and returned to the localized interactive title after Start.

The TOMY logo's visible wording is already English. Sampled frames across all 153 small clips showed Zoid and weapon animations. Audio still requires review before assigning their subtitle status.

### Text

The Zoid face pass compared the game's printed rules against matching retail card photographs. Check the built-in weapon label and HP cost on Geno Saurer, a preserved targeting diagram on Gojulas V1, and the denser rules on the compact Geno Breaker RS and Blade Liger BS faces. Both Liger Zero variants use the wording from the disc textures for their printed specials. Both preserve the original pixels for the frontal melee bonus amount because the digits are ambiguous at disc resolution. Check that the amount fits beside the English label and that the second line reads “Melee power 700 against L-types.” Check the frontal qualifier on Iron Kong PK, Black Rhimos, and Hammer Rock. [Geno Saurer card](https://ameblo.jp/bluekoara/entry-12253089685.html) · [Republic booster photographs](https://jp.mercari.com/item/m65897994071) · [Geno Breaker RS card](https://ameblo.jp/bluekoara/entry-12367147043.html) · [Blade Liger BS card](https://ameblo.jp/bluekoara/entry-12368697968.html)

The OpenGL album test opened Geno Saurer, Gojulas V1, Geno Breaker RS, Blade Liger BS, Heldigunner DT and Ultrasaurus. A disposable state exposed locked entries and the two compact variants for rendering. A pixel comparison with the prior pack found changes limited to the rule bands of 29 faces and confirmed that the targeting diagrams were preserved.

The first Custom, Event, and Pilot review checked 31 distinct rules against the Japanese game text. These rules appear on 59 faces. A pixel comparison across all 274 full-size textures found changes confined to the rule boxes on 49 faces. A disposable Card Album fixture verified readable rules on Long Cannon, Float Unit, Self-Destruct, External Charged Particle Cannon, and Irvine. A fresh English launcher resolved all five revised live text slots. Check that Float Unit says Saboteur cannot discard it and that Self-Destruct includes nearby allies and bases.

The next review checked 28 more rules used by 52 faces. In the Card Album, compare Flamethrower's forest squares with Coolant Sprayer's water squares. Both convert the affected squares to plains. Check that Pile Bunker can discard the target's Armor Custom Card and that Laser Sword ignores the target's equipped Custom Card effects. The fresh English launcher resolved the corrected live rule fragments. Check the complete name band on both Assault Landing Capsule variants. All 70 Event name bands now use their full width, which covers the original lettering on long titles.

Scroll through the Card Album to check `Zoids`, `Pilots`, `Custom`, and `Events`. All four headers were verified in the native OpenGL renderer after loading a disposable album state. The renderer now receives an eight-cell label specific to the album's drawing calls. The separate `Event Card` and `Pilot Card` text slots retained their full wording in the same run.

- [ ] Memory-card dialog is clean English, no tail bleed.
- [ ] Opening story: 10–20 consecutive lines, no clipping.
- [ ] Battle voice/tutorial prompts are English.
- [ ] Card album: 10+ cards across Zoid/Pilot/Custom/Event.
- [ ] Card detail: effect text reads in order.
- [ ] Deck editor: main prompts English.
- [ ] Shop: welcome/buy/insufficient-points prompts English.

### Runtime

- [ ] `ptr_pending = 0`.
- [ ] `msg_inplace = 0`.
- [ ] No crash during scene transitions.
- [ ] Savestate load repairs pointers.
- [ ] Stack/scratch doesn't collide during battle/FMV.

### UI/graphics

- [ ] Title and Mode Select labels are English throughout the fade and selection states.
- [ ] Result, trade, and memory-card headings render in English.
- [ ] Name entry opens the Latin table in English and can switch to both kana tables.
- [ ] Card-face localization and the remaining texture discovery are tracked in the completion plan.

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| Build link fails with “Permission denied” | Stop the running `ZoidsBattleCardGame.exe`; the exe is locked. |
| Game exits after ~14–19 s | Starvation watchdog. `run_recomp.ps1` sets `PSX_STARVATION_TIMEOUT_US=0`; if launching manually, set it too. |
| No window | Check the process; run without `-Headless`. Look at the `.err`/`.out` log. |
| Port 4371 already in use | Kill the old process or use another `-Port`. |
| D-pad doesn't move a menu via debug input | Use a real controller/keyboard; debug injection is not equivalent for all menu code. |
| Pointers look original after loading a savestate | Wait a moment; the idle sweep re-applies them. |
| Translations not loading | Check the staged config path in the log and the three TOMLs under `work/localization-runtime/<port>/translations/`. |

---

## 6. Evidence capture

- Screenshots: `work/*.png`
- Memory-card evidence: `analysis/phase2_hash_memory_card.png`, `work/audit_mem.png`
- Translation stats: `analysis/PHASE4_VALIDATION.txt`
- Build logs: `.err` and `.out` files at the prefix given to `-Log`.

When reporting a bug, include:
- screen/scene,
- card or line ID if known,
- screenshot,
- `xlate stats` output,
- whether it reproduces after a fresh boot.
