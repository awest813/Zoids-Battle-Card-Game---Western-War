/* Included in the REFERENCE OpenGL presenter. Positions are in the source
 * movie's pixel grid and mapped to the same viewport as its video. */
static void gl_draw_osd_layer(const uint32_t *px, int ow, int oh,
                              int dw, int dh, int vx, int vy, int ww, int wh, int blend);

static void gl_draw_osd_image(const uint32_t *px, int ow, int oh,
                              int dw, int dh, int vx, int vy, int ww, int wh) {
    gl_draw_osd_layer(px, ow, oh, dw, dh, vx, vy, ww, wh, 0);
}

typedef struct {
    int lba, sector_count, fps, width, height;
    int sector_lead_frames, first_frame, end_frame;
    int x, y, w, h, opacity;
    uint32_t background, foreground;
    const char *lines[2];
} ZoidsMovieCaption;

typedef struct {
    int lba, fps, sector_lead_frames, frame;
    uint8_t luma[20];
} ZoidsFrameSignature;

/* The builder inserts the caption table and the runtime's stock OSD font. */
/* ZOIDS_CAPTION_DATA */

static int zoids_sample_movie(uint8_t *luma, int lx, int ly, int lw, int lh) {
    static const int rows[] = {40, 68, 95, 120};
    static const int columns[] = {110, 157, 204, 251, 298};
    if (lw <= 0 || lh <= 0) return 0;
    uint32_t *line = malloc((size_t)lw * sizeof *line);
    if (!line) return 0;
    GLint draw_fbo, read_fbo, pack_buffer;
    glGetIntegerv(0x8CA6 /* DRAW_FRAMEBUFFER_BINDING */, &draw_fbo);
    glGetIntegerv(0x8CAA /* READ_FRAMEBUFFER_BINDING */, &read_fbo);
    glGetIntegerv(0x88ED /* PIXEL_PACK_BUFFER_BINDING */, &pack_buffer);
    p_glBindFramebuffer(PSXGL_READ_FRAMEBUFFER, draw_fbo);
    p_glBindBuffer(0x88EB /* PIXEL_PACK_BUFFER */, 0);
    for (int row = 0; row < 4; row++) {
        const int read_y = ly + lh - 1 - (2 * rows[row] + 1) * lh / 480;
        glReadPixels(lx, read_y, lw, 1, GL_BGRA, GL_UNSIGNED_BYTE, line);
        for (int col = 0; col < 5; col++) {
            const uint32_t color = line[(2 * columns[col] + 1) * lw / 640];
            luma[row * 5 + col] = (77 * ((color >> 16) & 255) + 150 * ((color >> 8) & 255) + 29 * (color & 255)) >> 8;
        }
    }
    p_glBindBuffer(0x88EB /* PIXEL_PACK_BUFFER */, pack_buffer);
    p_glBindFramebuffer(PSXGL_READ_FRAMEBUFFER, read_fbo);
    free(line);
    return 1;
}

static int zoids_match_movie_frame(int stream_lba, int delivered_lba, int lx, int ly, int lw, int lh) {
    if (stream_lba < 0 || delivered_lba < stream_lba) return -1;
    int best_frame = -1, best_distance = 200;
    uint8_t luma[20];
    int have_samples = 0;
    for (size_t i = 0; i < sizeof zoids_signatures / sizeof zoids_signatures[0]; i++) {
        const ZoidsFrameSignature *signature = &zoids_signatures[i];
        if (stream_lba != signature->lba) continue;
        const int estimate = (delivered_lba - stream_lba) * signature->fps / 150 - signature->sector_lead_frames;
        if (abs(estimate - signature->frame) > 3) continue;
        /* The disc cursor can lead or lag scanout by a frame. Sample above the
         * lettering to identify the pictured card before drawing on it. */
        if (!have_samples) {
            if (!zoids_sample_movie(luma, lx, ly, lw, lh)) return -1;
            have_samples = 1;
        }
        int distance = 0;
        for (int sample = 0; sample < 20; sample++)
            distance += abs(luma[sample] - signature->luma[sample]);
        if (distance < best_distance) {
            best_distance = distance;
            best_frame = signature->frame;
        }
    }
    return best_frame;
}

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

static void zoids_caption_line(uint32_t *image, int w, int top, const char *text, uint32_t color) {
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
                if (bits & (1u << col)) image[(top + row) * w + left + col] = color;
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
    const int matched_frame = zoids_match_movie_frame(stream_lba, delivered_lba, lx, ly, lw, lh);
    for (size_t i = 0; i < sizeof zoids_captions / sizeof zoids_captions[0]; i++) {
        const ZoidsMovieCaption *cue = &zoids_captions[i];
        if (stream_lba != cue->lba || delivered_lba < cue->lba ||
            delivered_lba >= cue->lba + cue->sector_count) continue;
        const int frame = matched_frame >= 0 ? matched_frame
            : (delivered_lba - cue->lba) * cue->fps / 150 - cue->sector_lead_frames;
        if (frame < cue->first_frame || frame >= cue->end_frame) continue;
        int visible = cue->width - cue->x;
        if (visible <= 0 || !cue->opacity) continue;
        if (visible > cue->w) visible = cue->w;
        const uint32_t alpha = (uint32_t)cue->opacity << 24;
        const uint32_t ink = alpha | cue->foreground;
        uint32_t image[320 * 48];
        for (int pixel = 0; pixel < cue->w * cue->h; pixel++)
            image[pixel] = alpha | cue->background;
        if (cue->lines[1]) {
            const int top = (cue->h - 20) / 2;
            zoids_caption_line(image, cue->w, top, cue->lines[0], ink);
            zoids_caption_line(image, cue->w, top + 12, cue->lines[1], ink);
        } else {
            zoids_caption_line(image, cue->w, (cue->h - 8) / 2, cue->lines[0], ink);
        }
        if (visible < cue->w) {
            for (int row = 1; row < cue->h; row++)
                memmove(image + row * visible, image + row * cue->w, visible * sizeof image[0]);
        }
        const int x0 = lx + lw * cue->x / cue->width;
        const int x1 = lx + lw * (cue->x + visible) / cue->width;
        const int y0 = wh - ly - lh + lh * cue->y / cue->height;
        const int y1 = wh - ly - lh + lh * (cue->y + cue->h) / cue->height;
        const int blend = cue->opacity < 255;
        gl_draw_osd_layer(image, visible, cue->h, x1 - x0, y1 - y0, x0, y0, ww, wh, blend);
        if (blend) glDisable(GL_BLEND);
    }
}
