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

### Text

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
