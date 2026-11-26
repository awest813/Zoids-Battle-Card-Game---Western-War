struct AlbumHeading {
    uint32_t source;
    uint32_t caller;
    uint8_t japanese[16];
    uint8_t english[18];
};

constexpr AlbumHeading kAlbumHeadings[] = {
/* ALBUM_HEADINGS */
};

bool redirect_album_heading(uint8_t* ram, CPUState* cpu, uint32_t target) {
    // The Card Album copies eight glyph cells. Other screens use the same
    // Japanese wording with longer English translations through the hash table.
    if (target != 0x8005BA48u) return false;
    const uint32_t caller = cpu->gpr[31];
    if (caller != 0x80065818u && caller != 0x80065850u) return false;
    constexpr uint32_t scratch_base = kPtrScratchLimit;
    constexpr uint32_t scratch_stride = 20;
    static_assert(scratch_base + scratch_stride * std::size(kAlbumHeadings) <= kScriptArena);
    if (psx_ram_live_bytes() < (kScriptArena & 0x1FFFFFFFu)) return false;
    for (size_t i = 0; i < std::size(kAlbumHeadings); ++i) {
        const auto& heading = kAlbumHeadings[i];
        if (cpu->gpr[4] != heading.source || caller != heading.caller) continue;
        for (size_t j = 0; j < sizeof(heading.japanese); ++j)
            if (grb(ram, heading.source + static_cast<uint32_t>(j)) != heading.japanese[j]) return false;
        const uint32_t scratch = scratch_base + static_cast<uint32_t>(i) * scratch_stride;
        for (size_t j = 0; j < sizeof(heading.english); ++j) {
            const uint32_t address = scratch + static_cast<uint32_t>(j);
            if (grb(ram, address) != heading.english[j]) gwb(ram, address, heading.english[j]);
        }
        cpu->gpr[4] = scratch;
        return true;
    }
    return false;
}
