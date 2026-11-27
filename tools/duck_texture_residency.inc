namespace {
// savestate.c accepts sidecars up to 64 MiB, including the outer header.
constexpr size_t kDuckResidencyCapacity = (64u << 20) - 16;

void residency_word(std::vector<uint8_t>& bytes, unsigned value) {
    if (value > 0xffffu) throw std::runtime_error("DuckStation residency value out of range");
    bytes.push_back(static_cast<uint8_t>(value));
    bytes.push_back(static_cast<uint8_t>(value >> 8));
}

void residency_rect(std::vector<uint8_t>& bytes, Rect rect) {
    for (unsigned value : {rect.x, rect.y, rect.w, rect.h}) residency_word(bytes, value);
}

struct ResidencyReader {
    const uint8_t* next;
    size_t remaining;

    unsigned word() {
        if (remaining < 2) throw std::runtime_error("Incomplete DuckStation residency");
        const unsigned value = unsigned(next[0]) | (unsigned(next[1]) << 8);
        next += 2;
        remaining -= 2;
        return value;
    }

    Rect rect() {
        const Rect region{word(), word(), word(), word()};
        if (!valid_rect(region)) throw std::runtime_error("Invalid DuckStation residency rectangle");
        return region;
    }
};

bool residency_matches_vram(const Source& source, Rect active, const uint16_t* vram) {
    if (!contains(source.rect, active)) return false;
    const size_t offset = size_t(active.y - source.rect.y) * source.rect.w
                        + active.x - source.rect.x;
    for (unsigned row = 0; row < active.h; ++row) {
        const auto* saved = source.words.data() + offset + size_t(row) * source.rect.w;
        if (!std::equal(saved, saved + active.w, vram + size_t(active.y + row) * 1024 + active.x))
            return false;
    }
    return true;
}
} // namespace

bool zoids_duck_residency_save(const DuckTexturePack* pack, std::vector<uint8_t>& bytes) {
    try {
        if (!pack || pack->copy_pending || pack->sources.size() > kMaxUploads) return false;
        const size_t size = 6 + 12 * pack->sources.size() + pack->snapshot_bytes
                          + 12 * pack->uploads.size() + 8 * pack->pages.size();
        if (size > kDuckResidencyCapacity) return false;
        bytes.reserve(size);
        residency_word(bytes, static_cast<unsigned>(pack->sources.size()));
        residency_word(bytes, static_cast<unsigned>(pack->uploads.size()));
        residency_word(bytes, static_cast<unsigned>(pack->pages.size()));

        std::unordered_map<const Source*, unsigned> indices;
        for (const auto& source : pack->sources) {
            indices.emplace(source.get(), static_cast<unsigned>(indices.size()));
            residency_rect(bytes, source->rect);
            residency_word(bytes, source->kind);
            residency_word(bytes, source->used);
            for (uint16_t word : source->words) residency_word(bytes, word);
        }
        for (const auto& upload : pack->uploads) {
            residency_word(bytes, indices.at(upload.source.get()));
            residency_rect(bytes, upload.active);
            residency_word(bytes, upload.splits);
        }
        for (const auto& page : pack->pages) {
            residency_word(bytes, indices.at(page.source.get()));
            residency_word(bytes, page.depth);
            residency_word(bytes, page.clut_x);
            residency_word(bytes, page.clut_y);
        }
        return bytes.size() == size;
    } catch (...) {
        return false;
    }
}

bool zoids_duck_residency_load(DuckTexturePack* pack, const uint16_t* vram,
                                const uint8_t* bytes, size_t size) {
    try {
        if (!pack || !vram || size > kDuckResidencyCapacity) return false;
        ResidencyReader reader{bytes, size};
        const unsigned sources_count = reader.word();
        const unsigned uploads_count = reader.word();
        const unsigned pages_count = reader.word();
        if (sources_count > kMaxUploads || pages_count > sources_count) return false;

        // Prepare a complete, validated replacement before changing live tracking.
        std::deque<std::shared_ptr<Source>> sources;
        size_t words_used = 0;
        for (unsigned index = 0; index < sources_count; ++index) {
            const auto rect = reader.rect();
            const auto kind = reader.word();
            const auto used = reader.word();
            const size_t count = size_t(rect.w) * rect.h;
            if (kind > DUCK_TEXTURE_PAGE || used > 1 || count > reader.remaining / 2 ||
                words_used + count > pack->snapshot_budget / 2)
                return false;
            auto source = std::make_shared<Source>();
            source->rect = rect;
            source->kind = static_cast<uint8_t>(kind);
            source->used = used != 0;
            source->dump_owner = pack;
            source->words.resize(count);
            for (auto& word : source->words) word = static_cast<uint16_t>(reader.word());
            source->hash = duck_texture_hash_words_le(source->words.data(), count);
            words_used += count;
            sources.push_back(std::move(source));
        }

        std::vector<Upload> uploads;
        std::vector<PageSource> pages;
        if (reader.remaining != 12u * uploads_count + 8u * pages_count) return false;
        uploads.reserve(uploads_count);
        pages.reserve(pages_count);
        for (unsigned index = 0; index < uploads_count; ++index) {
            const auto& source = sources.at(reader.word());
            const auto active = reader.rect();
            const auto splits = reader.word();
            if (source->kind != DUCK_TEXTURE_UPLOAD ||
                !residency_matches_vram(*source, active, vram)) return false;
            uploads.push_back({source, active, splits});
        }
        for (unsigned index = 0; index < pages_count; ++index) {
            const auto& source = sources.at(reader.word());
            const auto depth = reader.word();
            const auto clut_x = reader.word();
            const auto clut_y = reader.word();
            if (source->kind != DUCK_TEXTURE_PAGE || depth > 2 || clut_x >= 1024 || clut_y >= 512 ||
                !residency_matches_vram(*source, source->rect, vram)) return false;
            pages.push_back({source, static_cast<uint8_t>(depth),
                             static_cast<uint16_t>(clut_x), static_cast<uint16_t>(clut_y)});
        }

        if (duck_texture_pack_flush_dumps(pack, nullptr, 0) < 0) return false;
        pack->uploads.swap(uploads);
        pack->pages.swap(pages);
        pack->sources.swap(sources);
        pack->snapshot_bytes = words_used * sizeof(uint16_t);
        pack->palette_records = 0;
        pack->copy_updates.clear();
        pack->copy_pending = false;
        pack->rect_cache.clear();
        pack->match_cache.clear();
        ++pack->revision;
        return true;
    } catch (...) {
        return false;
    }
}
