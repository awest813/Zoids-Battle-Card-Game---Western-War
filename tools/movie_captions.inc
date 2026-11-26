/* Included in the REFERENCE OpenGL presenter. Positions are in the source
 * movie's pixel grid and mapped to the same viewport as its video. */
static void gl_draw_osd_image(const uint32_t *px, int ow, int oh,
                              int dw, int dh, int vx, int vy, int ww, int wh);

typedef struct {
    int lba, sector_count, fps, width, height;
    int sector_lead_frames, first_frame, end_frame;
    int x, y, w, h;
    const char *lines[2];
} ZoidsMovieCaption;

/* The builder inserts the caption table and the runtime's stock OSD font. */
/* ZOIDS_CAPTION_DATA */

static int zoids_caption_glyph(const unsigned char *glyph, int *shift) {
    unsigned mask = 0;
    for (int row = 0; row < 8; row++) mask |= glyph[row];
    *shift = 0;
    if (!mask) return 3;
    while (!(mask & 1u)) { mask >>= 1; ++*shift; }
    int width = 0;
    while (mask) { mask >>= 1; ++width; }
    return width;
}

static void zoids_caption_line(uint32_t *image, int w, int top, const char *text) {
    int used = 0;
    for (const char *c = text; *c; c++) {
        int shift;
        used += 1 + zoids_caption_glyph(FONT8X8[(unsigned char)*c - 32], &shift);
    }
    int left = (w - used) / 2;
    if (left < 2) return;
    for (const char *c = text; *c; c++) {
        const unsigned char *glyph = FONT8X8[(unsigned char)*c - 32];
        int shift;
        int width = zoids_caption_glyph(glyph, &shift);
        for (int row = 0; row < 8; row++) {
            const unsigned bits = (unsigned)glyph[row] >> shift;
            for (int col = 0; col < width; col++)
                if (bits & (1u << col)) image[(top + row) * w + left + col] = 0xFFFFFFFFu;
        }
        left += width + 1;
    }
}

static void zoids_movie_captions(int stream_lba, int delivered_lba,
                                int ww, int wh, int lx, int ly, int lw, int lh) {
    /* The guest-thread snapshot travels with the actual scanout, including
     * on the render thread. Use the current seek and delivery position so a
     * skip, replay, or save-state restore cannot leave a wall-clock cue armed. */
    if (stream_lba < 0) return;
    for (size_t i = 0; i < sizeof zoids_captions / sizeof zoids_captions[0]; i++) {
        const ZoidsMovieCaption *cue = &zoids_captions[i];
        if (stream_lba != cue->lba || delivered_lba < cue->lba ||
            delivered_lba >= cue->lba + cue->sector_count) continue;
        const int frame = (delivered_lba - cue->lba) * cue->fps / 150 - cue->sector_lead_frames;
        if (frame < cue->first_frame || frame >= cue->end_frame) continue;
        uint32_t image[320 * 48];
        for (int pixel = 0; pixel < cue->w * cue->h; pixel++)
            image[pixel] = 0xFF141922u;
        if (cue->lines[1]) {
            const int top = (cue->h - 20) / 2;
            zoids_caption_line(image, cue->w, top, cue->lines[0]);
            zoids_caption_line(image, cue->w, top + 12, cue->lines[1]);
        } else {
            zoids_caption_line(image, cue->w, (cue->h - 8) / 2, cue->lines[0]);
        }
        const int x0 = lx + lw * cue->x / cue->width;
        const int x1 = lx + lw * (cue->x + cue->w) / cue->width;
        const int y0 = wh - ly - lh + lh * cue->y / cue->height;
        const int y1 = wh - ly - lh + lh * (cue->y + cue->h) / cue->height;
        gl_draw_osd_image(image, cue->w, cue->h, x1 - x0, y1 - y0, x0, y0, ww, wh);
    }
}
