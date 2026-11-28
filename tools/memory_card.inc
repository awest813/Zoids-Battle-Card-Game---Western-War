bool memory_card_uses_binary_arguments(const CPUState* cpu, uint32_t target) {
    // SLPS-03255 builds the raw memory-card block here. The dispatcher also
    // calls the text hook at internal branch targets, where a0-a3 hold binary
    // pointers and data. Replacing a coincidental text match can change the
    // source pointer of an inline copy loop or corrupt the saved bytes.
    constexpr uint32_t pack_start = 0x8003A8B4u;
    constexpr uint32_t pack_end = 0x8003B1B4u;
    // The load picker reads controller state at an offset from the live
    // commander buffer. The buffer itself can still match the default name.
    constexpr uint32_t picker_input_start = 0x8003D92Cu;
    constexpr uint32_t picker_input_end = 0x8003D9ECu;
    const uint32_t return_address = cpu->gpr[31];
    return (target >= pack_start && target < pack_end) ||
           (return_address > pack_start && return_address < pack_end) ||
           (target >= picker_input_start && target < picker_input_end);
}

bool trade_profile_argument(uint32_t address, uint32_t target, uint32_t return_address) {
    // Each slot's loaded profile starts with a commander name. The picker and
    // transfer routines index inventory fields beyond that name.
    if (address != 0x80195024u && address != 0x80197734u) return false;
    constexpr uint32_t trade_start = 0x80056700u;
    constexpr uint32_t trade_end = 0x80059714u;
    return (target >= trade_start && target < trade_end) ||
           (return_address > trade_start && return_address <= trade_end);
}
