"""Estilo NOKIA: pantalla LCD monocroma de 120x72 pixeles, escalada x8."""

import pygame

from game import COLS, ROWS, UP, DOWN, LEFT, RIGHT
from styles.base import Renderer, pause_items, others, tint_mix

LOGICAL_W, LOGICAL_H = 120, 72
SCALE = 8
CELL = 4
FIELD_X, FIELD_Y = 4, 12

# Pantalla: (nombre, fondo, pixel encendido)
PALETTES = [
    ("VERDE", (199, 240, 216), (67, 82, 61)),
    ("AMBAR", (250, 202, 112), (82, 45, 12)),
    ("AZUL", (160, 205, 240), (20, 42, 92)),
    ("GRIS", (196, 200, 188), (42, 44, 42)),
    ("NOCHE", (24, 38, 30), (140, 232, 170)),
]
SNAKE_STYLES = ["CLASICA", "BLOQUES", "RAYAS", "HUECA", "CADENA"]

BG = FG = GHOST = None   # los define apply_palette()


def apply_palette(idx):
    global BG, FG, GHOST
    _, BG, FG = PALETTES[idx]
    GHOST = tuple(round(b + (f - b) * 0.12) for b, f in zip(BG, FG))


apply_palette(0)

# ---------------------------------------------------------------- fuente 3x5
FONT = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"], "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "##."],
    " ": ["...", "...", "...", "...", "..."], ":": ["...", ".#.", "...", ".#.", "..."],
    "<": ["..#", ".#.", "#..", ".#.", "..#"], ">": ["#..", ".#.", "..#", ".#.", "#.."],
    "-": ["...", "...", "###", "...", "..."], "!": [".#.", ".#.", ".#.", "...", ".#."],
    "/": ["..#", "..#", ".#.", "#..", "#.."],
}

BUG = ["#.###.#", ".#####.", "#.#.#.#"]   # dibujo del bonus (7x3)


def text_width(text, scale=1):
    return (len(text) * 4 - 1) * scale


def draw_text(surf, text, x, y, scale=1):
    for i, ch in enumerate(text.upper()):
        glyph = FONT.get(ch, FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, px in enumerate(row):
                if px == "#":
                    surf.fill(FG, (x + (i * 4 + gx) * scale, y + gy * scale, scale, scale))


def draw_text_centered(surf, text, y, scale=1):
    draw_text(surf, text, (LOGICAL_W - text_width(text, scale)) // 2, y, scale)


def draw_pattern(surf, pattern, x, y):
    for py, row in enumerate(pattern):
        for px, ch in enumerate(row):
            if ch == "#":
                surf.fill(FG, (x + px, y + py, 1, 1))


def cell_px(c, r):
    return FIELD_X + c * CELL, FIELD_Y + r * CELL


class NokiaRenderer(Renderer):
    NAME = "NOKIA"
    KEY = "nokia"
    OPTIONS = [("PANTALLA", [p[0] for p in PALETTES]), ("SERPIENTE", SNAKE_STYLES)]

    def __init__(self, screen):
        super().__init__(screen)
        size = (LOGICAL_W, LOGICAL_H)
        self.surf = pygame.Surface(size)
        self.shadow = pygame.Surface(size)
        self.composed = pygame.Surface(size)
        w, h = screen.get_size()
        self.overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w, SCALE):
            self.overlay.fill((255, 255, 255, 45), (x, 0, 1, h))
        for y in range(0, h, SCALE):
            self.overlay.fill((255, 255, 255, 45), (0, y, w, 1))
        self.snake_style = SNAKE_STYLES[0]

    # --- composicion final: sombra suave + pixeles + rejilla LCD
    def present(self):
        self.surf.set_colorkey(BG)
        self.shadow.fill(BG)
        mask = pygame.mask.from_threshold(self.surf, FG, (1, 1, 1, 255))
        mask.to_surface(self.shadow, setcolor=GHOST, unsetcolor=None)
        self.composed.fill(BG)
        self.composed.blit(self.shadow, (1, 1))
        self.composed.blit(self.surf, (0, 0))
        pygame.transform.scale(self.composed, self.screen.get_size(), self.screen)
        self.screen.blit(self.overlay, (0, 0))

    # --- piezas
    def draw_snake(self, surf, cells, direction, origin=(FIELD_X, FIELD_Y), style=None):
        style = style or self.snake_style
        ox, oy = origin

        def px(c, r):
            return ox + c * CELL, oy + r * CELL

        for i, (c, r) in enumerate(cells):
            x, y = px(c, r)
            if i == 0 or style in ("CLASICA", "BLOQUES") or (style == "RAYAS" and i % 2 == 0):
                surf.fill(FG, (x, y, 3, 3))
            elif style in ("RAYAS", "HUECA"):
                pygame.draw.rect(surf, FG, (x, y, 3, 3), 1)
            elif style == "CADENA":
                draw_pattern(surf, [".#.", "###", ".#."], x, y)

            if i + 1 >= len(cells) or style == "BLOQUES":
                continue
            nc, nr = cells[i + 1]
            if nr == r and abs(nc - c) == 1:
                gx = x + 3 if nc > c else x - 1
                if style == "CADENA":
                    surf.fill(FG, (gx, y + 1, 1, 1))
                elif style == "HUECA":
                    surf.fill(FG, (gx, y, 1, 1))
                    surf.fill(FG, (gx, y + 2, 1, 1))
                else:
                    surf.fill(FG, (gx, y, 1, 3))
            elif nc == c and abs(nr - r) == 1:
                gy = y + 3 if nr > r else y - 1
                if style == "CADENA":
                    surf.fill(FG, (x + 1, gy, 1, 1))
                elif style == "HUECA":
                    surf.fill(FG, (x, gy, 1, 1))
                    surf.fill(FG, (x + 2, gy, 1, 1))
                else:
                    surf.fill(FG, (x, gy, 3, 1))

        hx, hy = px(*cells[0])
        ex, ey = {RIGHT: (2, 0), LEFT: (0, 0), UP: (2, 0), DOWN: (2, 2)}[direction]
        surf.fill(BG, (hx + ex, hy + ey, 1, 1))

    def draw_walls(self, surf, walls):
        for c, r in walls:
            x, y = cell_px(c, r)
            right = (c + 1, r) in walls
            below = (c, r + 1) in walls
            surf.fill(FG, (x, y, 4 if right else 3, 4 if below else 3))
            if right and below and (c + 1, r + 1) in walls:
                surf.fill(FG, (x + 3, y + 3, 1, 1))

    def draw_frame(self, surf, solid):
        fw, fh = COLS * CELL, ROWS * CELL
        pygame.draw.rect(surf, FG, (FIELD_X - 2, FIELD_Y - 2, fw + 3, fh + 3), 1)
        if not solid:
            for i in range(FIELD_X - 2, FIELD_X + fw + 1, 2):
                surf.fill(BG, (i, FIELD_Y - 2, 1, 1))
                surf.fill(BG, (i, FIELD_Y + fh, 1, 1))
            for j in range(FIELD_Y - 2, FIELD_Y + fh + 1, 2):
                surf.fill(BG, (FIELD_X - 2, j, 1, 1))
                surf.fill(BG, (FIELD_X + fw, j, 1, 1))

    def draw_field(self, surf, g, show_snake=True):
        self.draw_frame(surf, g.maze["border"])
        self.draw_walls(surf, g.walls)
        draw_text(surf, f"{g.score:04d}", 2, 2)
        if g.bonus:
            draw_pattern(surf, BUG, LOGICAL_W - 19, 3)
            draw_text(surf, f"{g.bonus_left:02d}", LOGICAL_W - 10, 2)
        else:
            hud = f"M{g.maze_idx} N{g.level}"
            draw_text(surf, hud, LOGICAL_W - 2 - text_width(hud), 2)
        if g.food:
            draw_pattern(surf, [".#.", "#.#", ".#."], *cell_px(*g.food))
        if g.bonus:
            draw_pattern(surf, BUG, *cell_px(*g.bonus))
        # rivales (modo en linea): la pantalla es de un solo color, asi que cada una
        # usa otra forma de serpiente; las eliminadas parpadean
        alt = [s for s in SNAKE_STYLES if s != self.snake_style]
        for o in others(g):
            if not o.dead or pygame.time.get_ticks() // 150 % 2 == 0:
                self.draw_snake(surf, o.snake, o.direction, style=alt[(o.k - 1) % len(alt)] if o.k else None)
        if show_snake and g.snake:
            self.draw_snake(surf, g.snake, g.direction)

    def draw_menu(self, surf, app):
        draw_text_centered(surf, "SNAKE", 2, scale=2)
        preview = [(11 - i, 0) for i in range(12)]
        self.draw_snake(surf, preview, RIGHT, origin=(36, 15))
        for i, (label, value) in enumerate(app.menu_rows()):
            y = 19 + i * 6
            draw_text(surf, label, 14, y)
            if i == app.menu_sel:
                draw_text(surf, ">", 8, y)
                draw_text(surf, "<", 56, y)
                draw_text(surf, ">", 108, y)
            draw_text(surf, value, 84 - text_width(value) // 2, y)
        draw_text_centered(surf, f"RECORD {app.game.record:04d}", 57)
        if pygame.time.get_ticks() // 500 % 2 == 0:
            draw_text_centered(surf, "ESPACIO: JUGAR", 65)

    # --- frame completo
    def draw(self, app):
        apply_palette(app.opt(0))
        self.snake_style = SNAKE_STYLES[app.opt(1)]
        g = app.game
        surf = self.surf
        surf.fill(BG)
        if g.state == "menu":
            self.draw_menu(surf, app)
        elif g.state == "play":
            self.draw_field(surf, g)
        elif g.state == "pause":
            self.draw_field(surf, g)
            surf.fill(BG, (26, 20, 68, 32))
            pygame.draw.rect(surf, FG, (26, 20, 68, 32), 1)
            draw_text_centered(surf, "PAUSA", 24)
            for i, (s, _) in enumerate(pause_items(app, ["SEGUIR", "MENU"])):
                self.mark_pause(i, (36 + i * 8) * SCALE)
                draw_text_centered(surf, s, 34 + i * 8)
        elif g.state == "dying":
            self.draw_field(surf, g, show_snake=(g.state_time // 150) % 2 == 0)
        elif g.state == "stage":
            draw_text_centered(surf, "MAPA SUPERADO!", 10)
            draw_text_centered(surf, f"MAPA {g.maze_idx}", 26, scale=2)
            draw_text_centered(surf, g.maze["name"], 42)
            draw_text_centered(surf, f"PUNTOS {g.score:04d}", 56)
        elif g.state == "over":
            draw_text_centered(surf, "FIN DEL JUEGO", 6)
            draw_text_centered(surf, f"{g.score:04d}", 16, scale=3)
            if g.new_record:
                if pygame.time.get_ticks() // 400 % 2 == 0:
                    draw_text_centered(surf, "NUEVO RECORD!", 37)
            else:
                draw_text_centered(surf, f"RECORD {g.record:04d}", 37)
            draw_text_centered(surf, "ESPACIO: OTRA VEZ", 52)
            draw_text_centered(surf, "ESC: MENU", 60)
        self.present()
