"""Rebuild the REFERENCE localization object and link an isolated English runtime."""

import argparse
import hashlib
import re
import subprocess
from pathlib import Path

PROJECT = Path.home() / "zoids-recomp/zoids-battle-card-game"
BIN = Path.home() / ".local/share/retcomm/toolchains/cmake-clang-v1/latest/bin"
WORKSPACE = Path(__file__).resolve().parents[1]
TARGET = "ZoidsBattleCardGame.exe"
OBJECT = "CMakeFiles/psx-runtime.dir/psxrecomp/runtime/src/text_xlate.cpp.obj"
BATTLE_DIALOGUE = Path(__file__).with_name("battle_dialogue.inc")

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
        ("} // namespace", BATTLE_DIALOGUE.read_text(encoding="utf-8") + "\n} // namespace"),
        ("    uint32_t* argregs[4] =",
         "    if (app) paginate_battle_text(ram, cpu, target);\n    uint32_t* argregs[4] ="),
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
    stock_exe = build / TARGET
    fingerprint = hashlib.sha256(runtime.read_bytes() + stock_exe.read_bytes()
                                 + str(build).encode() + str(toolchain).encode()
                                 + Path(__file__).read_bytes() + BATTLE_DIALOGUE.read_bytes()).hexdigest()
    stamp = output / "source.sha256"
    if (output / TARGET).is_file() and stamp.is_file() and stamp.read_text() == fingerprint:
        print(output / TARGET)
        return

    code = output / "text_xlate.cpp"
    code.write_text(relocated_source(runtime.read_text(encoding="utf-8")), encoding="utf-8")
    obj = output / "text_xlate.cpp.obj"
    compile_command = command_for(build, OBJECT, toolchain)
    if "clang++.exe " not in compile_command or " -MD -MT " not in compile_command:
        raise ValueError("Unexpected compiler invocation in the REFERENCE build")
    compiler_flags = compile_command.split("clang++.exe ", 1)[1].split(" -MD -MT ", 1)[0]
    compiler = toolchain / "clang++.exe"
    subprocess.run(f'"{compiler}" {compiler_flags} -o "{obj}" -c "{code}"', cwd=build, check=True)

    graph = (build / "build.ninja").read_text(encoding="utf-8")
    marker = f"build {TARGET}: CXX_EXECUTABLE_LINKER__psx-runtime_Release "
    edge = graph.split(marker, 1)[1].splitlines()
    inputs = edge[0].split(" |", 1)[0]
    if inputs.count(OBJECT) != 1:
        raise ValueError("Missing or duplicate localization object in the link edge")
    inputs = inputs.replace(OBJECT, f'"{obj.as_posix()}"').replace("$:", ":")
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
    subprocess.run(f'"{compiler}" {link_flags} "@{rsp}" -o "{temporary}"',
                   cwd=build, check=True)
    temporary.replace(output / TARGET)
    stamp.write_text(fingerprint, encoding="ascii")
    print(output / TARGET)


if __name__ == "__main__":
    main()
