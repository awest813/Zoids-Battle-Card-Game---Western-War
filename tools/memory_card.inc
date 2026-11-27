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
