#include "mod_plugins.h"

extern "C" void __real_func_800BBF6C(CPUState* cpu);

namespace {
bool resolve_small_movie(CPUState* cpu) {
    // The call inside the stock STR player is the only one that consumes
    // this replacement CdSearchFile record. The boot clips use the guest lookup.
    if (cpu->pc != 0 || cpu->gpr[31] != 0x8003F62Cu) return false;
    const uint32_t result = cpu->gpr[4];
    const uint32_t address = cpu->gpr[5];
    constexpr uint32_t record_size = 24;
    constexpr uint32_t path_capacity = 32;
    if ((result & 3u) || !psx_ram_resolve(result, record_size, nullptr) ||
        !psx_ram_resolve(address, path_capacity, nullptr)) return false;

    std::string path;
    for (uint32_t i = 0; i < path_capacity; ++i) {
        const char ch = static_cast<char>(cpu->read_byte(address + i));
        if (ch == '\0') break;
        path.push_back(ch);
    }
    if (path.size() == path_capacity || path.compare(0, 3, "\\M\\") != 0) return false;
    const size_t basename = path.rfind('\\') + 1;
    if (basename == 3) return false;
    // One retail table entry has a period after the ISO version suffix.
    if (path.back() == '.') path.pop_back();
    const std::string suffix = ".STR;1";
    if (path.size() < basename + suffix.size() ||
        path.compare(path.size() - suffix.size(), suffix.size(), suffix) != 0) return false;
    const std::string filename = path.substr(basename);
    if (filename.size() >= record_size - 8) return false;
    path.resize(path.size() - 2);

    uint32_t lba, size;
    if (!psx_mod_disc_file_extent(path.c_str(), &lba, &size) || lba >= 100u * 4500u - 150u)
        return false;
    const uint32_t frames = lba + 150u;
    const auto bcd = [](uint32_t decimal) { return (decimal / 10u) * 16u + decimal % 10u; };
    // SDK CdlFILE holds a four-byte BCD position, file size and 16-byte name.
    const uint32_t position = bcd(frames / 4500u) | (bcd(frames / 75u % 60u) << 8) |
                              (bcd(frames % 75u) << 16);
    psx_host_write_word(result, position);
    psx_host_write_word(result + 4, size);
    for (uint32_t i = 0; i < record_size - 8; ++i)
        psx_host_write_byte(result + 8 + i, i < filename.size() ? filename[i] : 0);
    cpu->gpr[2] = result;
    cpu->pc = cpu->gpr[31];
    return true;
}
}

extern "C" void __wrap_func_800BBF6C(CPUState* cpu) {
    if (!resolve_small_movie(cpu)) __real_func_800BBF6C(cpu);
}
