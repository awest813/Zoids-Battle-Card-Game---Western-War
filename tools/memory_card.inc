bool packing_memory_card(const CPUState* cpu, uint32_t target) {
    // SLPS-03255 builds the raw memory-card block here. The dispatcher also
    // calls the text hook at internal branch targets, where a0-a3 hold binary
    // pointers and data. Replacing a coincidental text match can change the
    // source pointer of an inline copy loop or corrupt the saved bytes.
    constexpr uint32_t pack_start = 0x8003A8B4u;
    constexpr uint32_t pack_end = 0x8003B1B4u;
    const uint32_t return_address = cpu->gpr[31];
    return (target >= pack_start && target < pack_end) ||
           (return_address > pack_start && return_address < pack_end);
}
