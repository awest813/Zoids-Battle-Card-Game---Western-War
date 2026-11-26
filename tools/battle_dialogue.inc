// SLPS-03255 battle script text and input commands.
constexpr uint32_t kBattleScriptContext = 0x80109538u;
constexpr uint32_t kBattleTextHandler = 0x8004B404u;
constexpr uint32_t kAfterBattleCommand = 0x8004D664u;
constexpr uint32_t kRetailScriptStart = 0x800C0000u;
constexpr uint32_t kRetailScriptLimit = 0x800EAB2Cu;
constexpr uint32_t kScriptArena = 0x80620000u;
constexpr uint32_t kScriptMetadata = 0x80630000u;
constexpr uint32_t kScriptLines = 0x80630010u;
constexpr uint32_t kScriptArenaLimit = 0x80640000u;
constexpr uint16_t kShowText = 0x12u;
constexpr uint16_t kWaitInput = 6u;
constexpr uint16_t kFinishScript = 0x0Cu;
constexpr uint16_t kChooseYesNo = 0x13u;
constexpr size_t kBattleLineCells = 14u;
constexpr uint32_t kPlayerName = 0x80123EF8u;
constexpr uint32_t kDialogueValues = 0x80109648u;
constexpr uint16_t kPlayerToken = 0x8197u;
constexpr uint16_t kFirstValueToken = 0x83BFu;
constexpr uint16_t kNumberToken = 0x83C1u;
constexpr uint16_t kLastValueToken = 0x83C2u;

uint32_t script_read(uint8_t* ram, uint32_t address, unsigned bytes = 4) {
    uint32_t value = 0;
    for (unsigned i = 0; i < bytes; ++i)
        value |= uint32_t(grb(ram, address + i)) << (i * 8);
    return value;
}

void script_write(uint8_t* ram, uint32_t address, uint32_t value, unsigned bytes = 4) {
    for (unsigned i = 0; i < bytes; ++i)
        gwb(ram, address + i, uint8_t(value >> (i * 8)));
}

using BattleLine = std::vector<uint16_t>;

bool read_battle_line(uint8_t* ram, uint32_t address, BattleLine& text) {
    const uint32_t limit = 0x80000000u + psx_ram_live_bytes();
    if (address < 0x80010000u || address >= limit) return false;
    for (uint32_t offset = 0; offset + 1 < std::min(kSrcMax, limit - address); offset += 2) {
        const uint8_t lead = grb(ram, address + offset);
        if (lead == 0) return true;
        const uint8_t trail = grb(ram, address + offset + 1);
        if (!((lead >= 0x81 && lead <= 0x9F) || (lead >= 0xE0 && lead <= 0xEF)))
            return false;
        if (trail < 0x40 || trail > 0xFC || trail == 0x7F) return false;
        text.push_back((uint16_t(lead) << 8) | trail);
    }
    return false;
}

bool battle_token(uint16_t glyph) {
    return glyph == kPlayerToken || (glyph >= kFirstValueToken && glyph <= kLastValueToken);
}

void translate_dialogue_value(uint8_t* ram, uint32_t& address) {
    uint8_t bytes[kSrcMax];
    uint32_t size = 0;
    Term term = Term::None;
    if (!g_prof->read_record(ram, address, bytes, &size, &term) || term != Term::Nul)
        return;
    std::lock_guard<std::mutex> lock(g_mtx);
    const auto entry = g_table.find(fnv1a(bytes, size));
    if (entry != g_table.end()) apply_to_reg(ram, &address, entry->second, term);
}

void expand_dialogue_values(uint8_t* ram, BattleLine& line, bool& expanded) {
    if (std::none_of(line.begin(), line.end(), battle_token)) return;
    BattleLine result;
    for (const uint16_t glyph : line) {
        if (!battle_token(glyph)) {
            result.push_back(glyph);
            continue;
        }
        expanded = true;
        uint32_t address = kPlayerName;
        if (glyph != kPlayerToken) {
            // Alpha, beta and delta point to text. Gamma is an inline number.
            constexpr uint32_t offsets[] = {0x24u, 0x28u, 0x30u, 0x2Cu};
            const uint32_t field = kDialogueValues + offsets[glyph - kFirstValueToken];
            address = glyph == kNumberToken ? field : script_read(ram, field);
        }
        BattleLine value;
        if (!read_battle_line(ram, address, value)) {
            result.push_back(0x8148u); // Unavailable value.
            continue;
        }
        if (glyph != kPlayerToken && glyph != kNumberToken && !value.empty() &&
            address < kHashBase) {
            const uint32_t original = address;
            translate_dialogue_value(ram, address);
            if (address != original) {
                BattleLine translated;
                if (read_battle_line(ram, address, translated)) value = std::move(translated);
            }
        }
        // The native formatter will see these finished lines again. A token
        // in an inserted name must never trigger a second substitution.
        for (const uint16_t cell : value)
            result.push_back(battle_token(cell) ? 0x8148u : cell);
    }
    line = std::move(result);
}

void wrap_battle_line(const BattleLine& text, std::vector<BattleLine>& wrapped) {
    constexpr uint16_t space = 0x8140u;
    if (text.size() <= kBattleLineCells) {
        wrapped.push_back(text);
        return;
    }
    auto first = text.begin();
    while (first != text.end()) {
        const auto width = std::min(kBattleLineCells, size_t(text.end() - first));
        auto end = first + width;
        auto next = end;
        if (end != text.end()) {
            if (*end != space) {
                auto word = end;
                while (word != first && *word != space) --word;
                if (word != first) end = word;
            }
            next = end;
            while (next != text.end() && *next == space) ++next;
        }
        wrapped.emplace_back(first, end);
        first = next;
    }
}

void paginate_battle_text(uint8_t* ram, CPUState* cpu, uint32_t target) {
    if (target != kBattleTextHandler && target != kAfterBattleCommand) return;
    if (psx_ram_live_bytes() < (kScriptArenaLimit & 0x1FFFFFFFu)) return;
    const uint32_t context = kBattleScriptContext;
    const uint32_t base = script_read(ram, context + 4);
    const uint32_t index = script_read(ram, context + 8, 2);
    if (target == kAfterBattleCommand) {
        // The last generated command leaves the interpreter at our sentinel.
        // A choice needs the original context while the last page is visible.
        if (base != kScriptArena || index != script_read(ram, kScriptMetadata + 8))
            return;
        const uint32_t original = script_read(ram, kScriptMetadata);
        const uint32_t continuation = script_read(ram, kScriptMetadata + 4);
        if (original < kRetailScriptStart || original >= kRetailScriptLimit ||
            continuation >= 0x8000u || original + continuation * 2 >= kRetailScriptLimit)
            return;
        script_write(ram, context + 4, original);
        script_write(ram, context + 8, continuation, 2);
        script_write(ram, context + 10, script_read(ram, original + continuation * 2, 2), 2);
        return;
    }
    if (cpu->gpr[5] != context || base < kRetailScriptStart || base >= kRetailScriptLimit ||
        index >= 0x8000u || script_read(ram, context + 10, 2) != kShowText)
        return;
    const uint32_t start = base + index * 2;
    if (start + 12 > kRetailScriptLimit || script_read(ram, start) != kShowText) return;
    const uint32_t mode = script_read(ram, start + 4);
    const uint32_t count = script_read(ram, start + 8);
    if (mode > 1 || count == 0 || count > 3) return;
    const uint32_t followup = start + 12 + count * 4;
    if (followup + 4 > kRetailScriptLimit) return;
    const uint32_t next_command = script_read(ram, followup);
    const bool final_wait = next_command == kWaitInput;
    if (!final_wait && next_command != kChooseYesNo && next_command != kFinishScript) return;
    const uint32_t continuation = index + 2 * (count + (final_wait ? 4 : 3));
    if (continuation >= 0x8000u || base + continuation * 2 >= kRetailScriptLimit) return;

    BattleLine lines[3];
    bool needs_rewrite = false;
    for (uint32_t i = 0; i < count; ++i) {
        const uint32_t source = script_read(ram, start + 12 + i * 4);
        if (!((source >= 0x80010000u && source < 0x800F7000u) ||
              (source >= kPtrScratchBase && source < kPtrScratchLimit)))
            return;
        if (!read_battle_line(ram, source, lines[i])) return;
        expand_dialogue_values(ram, lines[i], needs_rewrite);
        needs_rewrite |= lines[i].size() > kBattleLineCells;
    }
    if (!needs_rewrite) return;

    std::vector<BattleLine> wrapped;
    for (uint32_t i = 0; i < count; ++i) wrap_battle_line(lines[i], wrapped);
    constexpr uint32_t stride = 32;
    const size_t pages = (wrapped.size() + 2) / 3;
    const size_t waits = pages - (final_wait ? 0 : 1);
    const size_t end = index + 2 * (3 * pages + wrapped.size() + waits);
    if (end >= 0x8000u ||
        wrapped.size() > (kScriptArenaLimit - kScriptLines) / stride)
        return;

    // Keep the original halfword index so the retail handler's mission-specific
    // gating sees the same index when it opens the first page.
    uint32_t address = kScriptArena + index * 2;
    for (size_t first = 0; first < wrapped.size(); first += 3) {
        const size_t rows = std::min<size_t>(3, wrapped.size() - first);
        script_write(ram, address, kShowText);
        script_write(ram, address + 4, mode);
        script_write(ram, address + 8, uint32_t(rows));
        address += 12;
        for (size_t row = first; row < first + rows; ++row) {
            const uint32_t line = kScriptLines + uint32_t(row) * stride;
            uint32_t cursor = line;
            for (const uint16_t glyph : wrapped[row]) {
                gwb(ram, cursor++, uint8_t(glyph >> 8));
                gwb(ram, cursor++, uint8_t(glyph));
            }
            script_write(ram, cursor, 0, 2);
            script_write(ram, address, line);
            address += 4;
        }
        if (final_wait || first + rows < wrapped.size()) {
            script_write(ram, address, kWaitInput);
            address += 4;
        }
    }
    script_write(ram, address, 0);
    script_write(ram, kScriptMetadata, base);
    script_write(ram, kScriptMetadata + 4, continuation);
    script_write(ram, kScriptMetadata + 8, uint32_t(end));
    script_write(ram, context + 4, kScriptArena);
}
