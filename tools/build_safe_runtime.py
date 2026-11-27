"""Rebuild the REFERENCE localization objects and link an isolated English runtime."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
from itertools import groupby
from pathlib import Path

from translations_menu import ALBUM_HEADINGS, MENU

PROJECT = Path.home() / "zoids-recomp/zoids-battle-card-game"
BIN = Path.home() / ".local/share/retcomm/toolchains/cmake-clang-v1/latest/bin"
WORKSPACE = Path(__file__).resolve().parents[1]
TARGET = "ZoidsBattleCardGame.exe"
OBJECT = "CMakeFiles/psx-runtime.dir/psxrecomp/runtime/src/text_xlate.cpp.obj"
RENDERER_OBJECT = "CMakeFiles/psx-runtime.dir/psxrecomp/runtime/src/gpu_gl_renderer.c.obj"
BATTLE_DIALOGUE = Path(__file__).with_name("battle_dialogue.inc")
MEMORY_CARD = Path(__file__).with_name("memory_card.inc")
ALBUM_HEADINGS_SOURCE = Path(__file__).with_name("album_headings.inc")
MENU_TRANSLATIONS = Path(__file__).with_name("translations_menu.py")
MOVIE_CAPTIONS = Path(__file__).with_name("movie_captions.inc")
CREDITS_LOOKUP = Path(__file__).with_name("credits_lookup.inc")
MOVIE_LOOKUP = Path(__file__).with_name("movie_lookup.inc")
CAPTION_TEXT = WORKSPACE / "translations/zoids.movie_captions.json"
MOVIE_INVENTORY = WORKSPACE / "analysis/MOVIE_INVENTORY.csv"

STACK_SCRATCH = """    // Scratch below the caller's $sp, 8-byte aligned, with headroom.
    if (sp < 0x80001000u) return false;
    uint32_t scratch = (sp - 0x900u) & ~7u;
    if (!va_in_ram(scratch) || !va_in_ram(scratch + (uint32_t)body.size() + 2)) return false;
    for (size_t i = 0; i < body.size(); ++i) gwb(ram, scratch + (uint32_t)i, body[i]);
    if (t == Term::FFFF) { gwb(ram, scratch + (uint32_t)body.size(),     0xFF);
                           gwb(ram, scratch + (uint32_t)body.size() + 1, 0xFF); }
    else                 { gwb(ram, scratch + (uint32_t)body.size(),     0x00); }
"""
HASH_ARENA = """    // An argument can outlive the caller's frame. Keep the encoded string
    // in expanded RAM, with a distinct slot for each source/terminator pair.
    if (!te.scratch || psx_ram_live_bytes() < (kHashLimit & 0x1FFFFFFFu)) return false;
    body.push_back(t == Term::FFFF ? 0xFF : 0);
    body.push_back(t == Term::FFFF ? 0xFF : 0);
    const uint32_t scratch = te.scratch + (t == Term::FFFF ? kHashSlotBytes : 0u);
    // A saved state may restore the arena from before this string was used.
    for (size_t i = 0; i < body.size(); ++i) {
        const uint32_t address = scratch + static_cast<uint32_t>(i);
        if (grb(ram, address) != body[i]) gwb(ram, address, body[i]);
    }
"""
ASSIGN_HASH_SLOTS = """    // Sorted source hashes give identical tables identical save-state addresses.
    std::vector<uint64_t> sources;
    sources.reserve(g_table.size());
    for (const auto& entry : g_table) sources.push_back(entry.first);
    std::sort(sources.begin(), sources.end());
    uint32_t next_address = kHashBase;
    for (const uint64_t source : sources) {
        if (next_address > kHashLimit - 2 * kHashSlotBytes) break;
        g_table.at(source).scratch = next_address;
        next_address += 2 * kHashSlotBytes;
    }
"""


def localized_album_headings():
    rows = []
    for text_id, (source, caller, japanese) in ALBUM_HEADINGS.items():
        label = MENU[text_id]
        if len(japanese) != 8 or len(label) > 8 or not label.isascii():
            raise ValueError(f"{text_id}: Card Album headings use eight glyph cells")
        full_width = "".join("　" if char == " " else chr(ord(char) + 0xFEE0) for char in label.ljust(8))
        columns = [", ".join(f"{value:#04x}" for value in text.encode("shift_jis"))
                   for text in (japanese, full_width)]
        rows.append(f"    {{ {source:#010x}u, {caller:#010x}u, {{ {columns[0]} }}, {{ {columns[1]}, 0, 0 }} }},")
    return ALBUM_HEADINGS_SOURCE.read_text(encoding="utf-8").replace("/* ALBUM_HEADINGS */", "\n".join(rows))


def relocated_source(source):
    replacements = (
        ("constexpr uint32_t kPtrScratchBase  = 0x801E0000u;",
         "constexpr uint32_t kPtrScratchBase  = 0x80600000u;"),
        ("constexpr uint32_t kPtrScratchLimit = 0x801FE000u;  // 120 KiB arena; 8 KiB stack headroom",
         "constexpr uint32_t kPtrScratchLimit = 0x8061E000u;\n"
         "constexpr uint32_t kHashBase = 0x80300000u;\n"
         "constexpr uint32_t kHashLimit = 0x80600000u;\n"
         "constexpr uint32_t kHashSlotBytes = kSrcMax + 4u;"),
        ("    Term        term = Term::Nul;\n};\nstruct CapRec",
         "    Term        term = Term::Nul;\n    uint32_t scratch = 0;\n};\nstruct CapRec"),
        ("    // Mark inventory records that now have a translation.\n",
         ASSIGN_HASH_SLOTS + "    // Mark inventory records that now have a translation.\n"),
        ("void ptr_redirects_patch_locked(uint8_t* ram) {\n",
         "void ptr_redirects_patch_locked(uint8_t* ram) {\n"
         "    if (psx_ram_live_bytes() < (kPtrScratchLimit & 0x1FFFFFFFu)) return;\n"),
        ("bool apply_to_reg(uint8_t* ram, CPUState* cpu, uint32_t sp, uint32_t* reg,",
         "bool apply_to_reg(uint8_t* ram, uint32_t* reg,"),
        ("    const uint32_t sp = cpu->gpr[29];\n", ""),
        ("apply_to_reg(ram, cpu, sp, argregs[a], te, term)",
         "apply_to_reg(ram, argregs[a], te, term)"),
        ("    if (project_root && *project_root)\n"
         '        g_dir = (fs::path(project_root) / "translations").string();',
         '    const char* table_dir = std::getenv("PSX_XLATE_TABLE_DIR");\n'
         "    if (table_dir && *table_dir) g_dir = table_dir;\n"
         "    else if (project_root && *project_root)\n"
         '        g_dir = (fs::path(project_root) / "translations").string();'),
        (STACK_SCRATCH, HASH_ARENA),
        ("        case '@':  return 0x8197;",
         "        case '@':  return 0x8197;\n"
         "        case 0x03B1: return 0x83BF;  // dialogue parameter alpha\n"
         "        case 0x03B2: return 0x83C0;\n"
         "        case 0x03B3: return 0x83C1;\n"
         "        case 0x03B4: return 0x83C2;"),
        ("} // namespace", BATTLE_DIALOGUE.read_text(encoding="utf-8") + "\n"
         + MEMORY_CARD.read_text(encoding="utf-8") + "\n"
         + localized_album_headings() + "\n} // namespace"),
        ("    uint32_t* argregs[4] =",
         "    if (app && redirect_album_heading(ram, cpu, target)) return;\n"
         "    if (app) paginate_battle_text(ram, cpu, target);\n"
         "    if (copying_player_name(cpu, target) || packing_memory_card(cpu, target)) return;\n"
         "    uint32_t* argregs[4] ="),
        ("        if (scratch_recent(va)) continue;  // don't recapture our own English scratch",
         "        if (scratch_recent(va) || (va >= kScriptLines && va < kScriptArenaLimit)) continue;"),
    )
    for stock, updated in replacements:
        if source.count(stock) != 1:
            raise ValueError(f"Unexpected reference runtime source near {stock!r}")
        source = source.replace(stock, updated, 1)
    encoded_glyph = "fw_sjis_for_ascii(cp <= 0x7E ? cp : ' ')"
    if source.count(encoded_glyph) != 3:
        raise ValueError("Unexpected number of Shift-JIS encoders in the reference runtime")
    return source.replace(encoded_glyph, "fw_sjis_for_ascii(cp)")


def command_for(build, target, toolchain=BIN):
    return subprocess.check_output([toolchain / "ninja.exe", "-t", "commands", "-s", target], cwd=build,
                                   text=True, encoding="utf-8").strip()


def captioned_renderer(source, osd):
    font = re.search(r"static const uint8_t FONT8X8\[95\]\[8\] = \{.*?\n\};", osd, re.S)
    if not font:
        raise ValueError("Missing reference OSD font")
    glyph_rows = re.findall(r"\{((?:0x[0-9A-Fa-f]{2},?\s*){8})\}", font[0])
    if len(glyph_rows) != 95:
        raise ValueError("Unexpected reference OSD glyph count")
    glyph_widths = []
    for glyph in glyph_rows:
        mask = 0
        for row in re.findall(r"0x[0-9A-Fa-f]{2}", glyph):
            mask |= int(row, 16)
        glyph_widths.append(1 + (mask.bit_length() - (mask & -mask).bit_length() + 1 if mask else 3))
    with MOVIE_INVENTORY.open(encoding="utf-8-sig", newline="") as inventory:
        clips = {row["path"]: row for row in csv.DictReader(inventory)}
    records = []
    matches = []
    styles = {
        "caption": (0x141922, 0xFFFFFF),
        "card_name": (0x30362E, 0xFFF9EA),
        "card_rule": (0xF0EEE5, 0x27251F),
    }
    for path, track in json.loads(CAPTION_TEXT.read_text(encoding="utf-8")).items():
        clip = clips[path]
        disc = [int(clip[key]) for key in ("start_lba", "sector_count", "nominal_fps", "width", "height")]
        width, height = disc[-2:]
        lead = track["sector_lead_frames"]
        if not isinstance(lead, int) or lead < 0:
            raise ValueError(f"{path}: invalid sector lead")
        if "frame_match" in track:
            match = track["frame_match"]
            first = match["first_frame"]
            signatures = match["signatures"]
            if not 0 <= first < first + len(signatures) <= int(clip["frame_count"]):
                raise ValueError(f"{path}: frame match outside the movie")
            for frame, signature in enumerate(signatures, first):
                pixels = bytes.fromhex(signature)
                if len(pixels) != 20:
                    raise ValueError(f"{path}: expected 20 luma samples for frame {frame}")
                samples = ", ".join(map(str, pixels))
                matches.append(f"    {{ {disc[0]}, {disc[2]}, {lead}, {frame}, {{ {samples} }} }},")
        motions = track.get("motions", {})
        for cue in track["cues"]:
            motion = motions[cue["motion"]] if "motion" in cue else None
            first, end = (motion if motion else cue)["frames"]
            x, y, w, h = cue["box"]
            lines = cue["lines"]
            if not 0 <= first < end <= int(clip["frame_count"]):
                raise ValueError(f"{path}: caption frame range outside the movie: {cue}")
            if not (0 <= x < x + w <= width and 0 <= y < y + h <= height and w <= 320 and h <= 48):
                raise ValueError(f"{path}: caption box outside the movie or too large: {cue}")
            if not (1 <= len(lines) <= 2 and h >= (20 if len(lines) == 2 else 8)):
                raise ValueError(f"{path}: caption lines do not fit the box: {cue}")
            for line in lines:
                if (not line or any(not 32 <= ord(char) <= 126 for char in line)
                        or sum(glyph_widths[ord(char) - 32] for char in line) > w - 4):
                    raise ValueError(f"{path}: caption line is non-ASCII or too wide: {line!r}")
            text = ", ".join(json.dumps(line) for line in lines)
            duration = end - first
            top_rows = cue.get("top_rows", [y] * duration)
            left_columns = motion["left_columns"] if motion else [0] * duration
            fade = motion.get("fade", []) if motion else []
            if len(top_rows) != duration or len(left_columns) != duration or len(fade) > duration:
                raise ValueError(f"{path}: provide one position per frame: {cue}")
            opacity = [255] * (duration - len(fade)) + fade
            colors = ", ".join(f"0x{color:06X}u" for color in styles[cue.get("style", "caption")])
            for (left, top, alpha), run in groupby(zip(left_columns, top_rows, opacity)):
                if not (isinstance(left, int) and 0 <= left < width
                        and isinstance(top, int) and 0 <= top <= height - h
                        and isinstance(alpha, int) and 0 <= alpha <= 255):
                    raise ValueError(f"{path}: moving caption outside the movie: {cue}")
                stop = first + sum(1 for _ in run)
                numbers = ", ".join(map(str, (*disc, lead, first, stop, x + left, top, w, h, alpha)))
                records.append(f"    {{ {numbers}, {colors}, {{ {text} }} }},")
                first = stop
    if not records:
        raise ValueError("No movie captions defined")
    table = "static const ZoidsMovieCaption zoids_captions[] = {\n" + "\n".join(records) + "\n};"
    table += "\nstatic const ZoidsFrameSignature zoids_signatures[] = {\n" + "\n".join(matches) + "\n};"
    code = MOVIE_CAPTIONS.read_text(encoding="utf-8").replace("/* ZOIDS_CAPTION_DATA */", font[0] + "\n" + table)
    replacements = (
        ('#include "gpu_fmv_hd.h"', '#include "gpu_fmv_hd.h"\n#include "cdrom.h"'),
        ("static void gl_draw_osd_image(const uint32_t *px, int ow, int oh,\n"
         "                              int dw, int dh, int vx, int vy, int ww, int wh) {",
         "static void gl_draw_osd_layer(const uint32_t *px, int ow, int oh,\n"
         "                              int dw, int dh, int vx, int vy, int ww, int wh, int blend) {"),
        ("    glDisable(GL_BLEND);\n    if (p_glBlendEquationSeparate)\n"
         "        p_glBlendEquationSeparate(PSXGL_FUNC_ADD, PSXGL_FUNC_ADD);\n    /* GL viewport origin is bottom-left. */",
         "    if (blend) {\n        glEnable(GL_BLEND);\n"
         "        p_glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);\n"
         "    } else {\n        glDisable(GL_BLEND);\n    }\n"
         "    if (p_glBlendEquationSeparate)\n"
         "        p_glBlendEquationSeparate(PSXGL_FUNC_ADD, PSXGL_FUNC_ADD);\n    /* GL viewport origin is bottom-left. */"),
        ("static void present_fmv_hd(const FmvHdImage *hd) {",
         code + "\nstatic void present_fmv_hd(const FmvHdImage *hd, const FmvHdTimeline *timeline) {"),
        ("    pres_record(GL_PRES_CPU, 0, 0, hd->w, hd->h, lx, ly, lw, lh);",
         "    zoids_movie_captions(timeline->stream_lba, timeline->delivered_lba, ww, wh, lx, ly, lw, lh);\n"
         "    pres_record(GL_PRES_CPU, 0, 0, hd->w, hd->h, lx, ly, lw, lh);"),
        ("    if (s_present_d24) {\n        FmvHdImage hd;\n        const FmvHdTimeline timeline =",
         "    const FmvHdTimeline timeline ="),
        ("decode_serial };\n        if (gpu_fmv_hd_lookup",
         "decode_serial };\n    if (s_present_d24) {\n        FmvHdImage hd;\n        if (gpu_fmv_hd_lookup"),
        ("present_fmv_hd(&hd); return;", "present_fmv_hd(&hd, &timeline); return;"),
        ("    pres_record(GL_PRES_CPU, 0, 0, src_w, src_h, lx, ly, lw, lh);",
         "    if (s_present_d24 && decode_serial)\n"
         "        zoids_movie_captions(stream_lba, delivered_lba, ww, wh, lx, ly, lw, lh);\n"
         "    pres_record(GL_PRES_CPU, 0, 0, src_w, src_h, lx, ly, lw, lh);"),
        ("static void present_vram_impl(int disp_x, int disp_y, int w, int h, int linear,\n"
         "                              int force_4_3) {",
         "static void present_vram_impl(int disp_x, int disp_y, int w, int h, int linear,\n"
         "                              int force_4_3, int stream_lba, int delivered_lba) {"),
        ("        const int32_t a[6] = { disp_x, disp_y, w, h, linear, force_4_3 };\n"
         "        if (rth_record_present(RTH_PRESENT_VRAM, 6, a)) return;",
         "        const int32_t a[8] = { disp_x, disp_y, w, h, linear, force_4_3, stream_lba, delivered_lba };\n"
         "        if (rth_record_present(RTH_PRESENT_VRAM, 8, a)) return;"),
        ("    pres_record(geometry?GL_PRES_GEOMETRY:GL_PRES_VRAM, disp_x, disp_y, w, h, lx, ly, lw, lh);",
         "    zoids_movie_captions(stream_lba, delivered_lba, ww, wh, lx, ly, lw, lh);\n"
         "    pres_record(geometry?GL_PRES_GEOMETRY:GL_PRES_VRAM, disp_x, disp_y, w, h, lx, ly, lw, lh);"),
        ("void gl_renderer_present_vram(int disp_x, int disp_y, int w, int h, int linear,\n"
         "                              int force_4_3) {",
         "static void present_vram_with_movie(int disp_x, int disp_y, int w, int h, int linear,\n"
         "                                   int force_4_3, int stream_lba, int delivered_lba) {"),
        ("    present_vram_impl(disp_x, disp_y, w, h, linear, force_4_3);",
         "    present_vram_impl(disp_x, disp_y, w, h, linear, force_4_3, stream_lba, delivered_lba);"),
        ("int gl_renderer_present_wide_fbo(int disp_x, int disp_y, int disp_h, int linear) {",
         "void gl_renderer_present_vram(int disp_x, int disp_y, int w, int h, int linear, int force_4_3) {\n"
         "    const int stream_lba = cdrom_fmv_stream_pending() ? cdrom_get_stream_start_lba() : -1;\n"
         "    const int delivered_lba = stream_lba < 0 ? -1 : cdrom_get_delivered_lba();\n"
         "    present_vram_with_movie(disp_x, disp_y, w, h, linear, force_4_3, stream_lba, delivered_lba);\n"
         "}\n\nint gl_renderer_present_wide_fbo(int disp_x, int disp_y, int disp_h, int linear) {"),
        ("        gl_renderer_present_vram(a[0], a[1], a[2], a[3], a[4], a[5]);",
         "        present_vram_with_movie(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7]);"),
    )
    for stock, updated in replacements:
        if source.count(stock) != 1:
            raise ValueError(f"Unexpected reference renderer source near {stock!r}")
        source = source.replace(stock, updated, 1)
    return source


def compile_replacement(build, toolchain, target, compiler_name, source, output, original):
    compile_command = command_for(build, target, toolchain)
    compiler_marker = compiler_name + " "
    if compiler_marker not in compile_command or " -MD -MT " not in compile_command:
        raise ValueError(f"Unexpected compiler invocation for {target}")
    flags = compile_command.split(compiler_marker, 1)[1].split(" -MD -MT ", 1)[0]
    subprocess.run(f'"{toolchain / compiler_name}" {flags} -iquote "{original.parent}" '
                   f'-o "{output}" -c "{source}"', cwd=build, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=PROJECT)
    parser.add_argument("--toolchain-bin", type=Path, default=BIN)
    parser.add_argument("--build-dir", default="build-reference")
    args = parser.parse_args()
    project = args.project_dir.resolve()
    toolchain = args.toolchain_bin.resolve()
    build = project / args.build_dir
    output = WORKSPACE / "work" / "localization-build" / build.name
    output.mkdir(parents=True, exist_ok=True)
    runtime = project / "psxrecomp/runtime/src/text_xlate.cpp"
    renderer = runtime.with_name("gpu_gl_renderer.c")
    osd = runtime.with_name("host_osd.c")
    stock_exe = build / TARGET
    sources = (runtime, renderer, osd, stock_exe, Path(__file__), BATTLE_DIALOGUE,
               ALBUM_HEADINGS_SOURCE, MENU_TRANSLATIONS, MOVIE_CAPTIONS, MOVIE_LOOKUP, CREDITS_LOOKUP,
               CAPTION_TEXT, MOVIE_INVENTORY)
    fingerprint = hashlib.sha256(b"".join(path.read_bytes() for path in sources)
                                 + str(build).encode() + str(toolchain).encode()).hexdigest()
    stamp = output / "source.sha256"
    if (output / TARGET).is_file() and stamp.is_file() and stamp.read_text() == fingerprint:
        print(output / TARGET)
        return

    code = output / "text_xlate.cpp"
    code.write_text(relocated_source(runtime.read_text(encoding="utf-8")) + "\n"
                    + MOVIE_LOOKUP.read_text(encoding="utf-8") + "\n"
                    + CREDITS_LOOKUP.read_text(encoding="utf-8"), encoding="utf-8")
    obj = output / "text_xlate.cpp.obj"
    video_code = output / "gpu_gl_renderer.c"
    video_obj = output / "gpu_gl_renderer.c.obj"
    video_code.write_text(captioned_renderer(renderer.read_text(encoding="utf-8"),
                                             osd.read_text(encoding="utf-8")), encoding="utf-8")
    compile_replacement(build, toolchain, RENDERER_OBJECT, "clang.exe", video_code, video_obj, renderer)
    compile_replacement(build, toolchain, OBJECT, "clang++.exe", code, obj, runtime)
    compiler = toolchain / "clang++.exe"

    graph = (build / "build.ninja").read_text(encoding="utf-8")
    marker = f"build {TARGET}: CXX_EXECUTABLE_LINKER__psx-runtime_Release "
    edge = graph.split(marker, 1)[1].splitlines()
    inputs = edge[0].split(" |", 1)[0]
    for original, replacement in ((OBJECT, obj), (RENDERER_OBJECT, video_obj)):
        if inputs.count(original) != 1:
            raise ValueError(f"Missing or duplicate localization object in the link edge: {original}")
        inputs = inputs.replace(original, f'"{replacement.as_posix()}"')
    inputs = inputs.replace("$:", ":")
    variables = {}
    for line in edge[1:]:
        match = re.fullmatch(r"  ([A-Z_]+) = (.*)", line)
        if not match:
            break
        variables[match[1]] = match[2]
    rsp = output / "zoids-runtime.rsp"
    rsp.write_text(" ".join((inputs, variables.get("LINK_PATH", ""), variables["LINK_LIBRARIES"])),
                   encoding="utf-8")
    link_command = command_for(build, TARGET, toolchain)
    link_flags = link_command.split("clang++.exe ", 1)[1].split(" @", 1)[0]
    temporary = output / "ZoidsBattleCardGame.new.exe"
    wrappers = "-Wl,--wrap=func_800BBF6C,--wrap=func_8005C36C"
    subprocess.run(f'"{compiler}" {link_flags} {wrappers} "@{rsp}" -o "{temporary}"',
                   cwd=build, check=True)
    temporary.replace(output / TARGET)
    stamp.write_text(fingerprint, encoding="ascii")
    print(output / TARGET)


if __name__ == "__main__":
    main()
