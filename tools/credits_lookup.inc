#include <vector>

extern "C" void __real_func_8005C36C(CPUState* cpu);

namespace {
bool read_credits_background(CPUState* cpu) {
    if (cpu->pc != 0) return false;
    const uint32_t caller = cpu->gpr[31];
    if (caller != 0x8003FFA0u && caller != 0x80040224u && caller != 0x800403A8u)
        return false;

    constexpr uint32_t page_size = 0x13000u;
    constexpr uint32_t archive_size = 19u * page_size;
    constexpr uint32_t target = 0x80190000u;
    const uint32_t offset = cpu->gpr[6];
    if (cpu->gpr[4] != 0x8001CCF0u || cpu->gpr[5] != target ||
        offset % page_size || offset >= archive_size || !psx_ram_resolve(target, page_size, nullptr))
        return false;

    // The ending alternates XA playback with cooked-data reads. Read its
    // background without changing XA filter, drive position or interrupt state.
    std::vector<uint8_t> archive(archive_size);
    uint32_t size;
    if (!psx_mod_read_disc_file("TIM/W_MES4.TIM", archive.data(), archive_size, &size) ||
        size != archive_size) return false;

    const uint8_t* page = archive.data() + offset;
    const auto word_at = [](const uint8_t* bytes) {
        return static_cast<uint32_t>(bytes[0]) | (static_cast<uint32_t>(bytes[1]) << 8) |
               (static_cast<uint32_t>(bytes[2]) << 16) | (static_cast<uint32_t>(bytes[3]) << 24);
    };
    if (word_at(page) != 0x11u || word_at(page + 4) != 0x00F000A0u) return false;
    for (uint32_t i = 0; i < page_size; i += 4)
        psx_host_write_word(target + i, word_at(page + i));

    // Complete the guest SDK's poll without scheduling another read. Use its
    // current VBlank clock for the timeout so restores stay deterministic.
    psx_host_write_word(0x800F68F4u, cpu->read_word(0x800F5BB4u));
    psx_host_write_word(0x800F68E4u, 0);
    cpu->gpr[2] = 1;
    cpu->pc = caller;
    return true;
}
}

extern "C" void __wrap_func_8005C36C(CPUState* cpu) {
    if (!read_credits_background(cpu)) __real_func_8005C36C(cpu);
}
