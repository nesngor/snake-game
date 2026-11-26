"""Estilo PIXEL: arte de 16 bits a 240x144 escalado x4, con contornos y sombras."""

import math
import random

import pygame

from game import COLS, ROWS, BONUS_TICKS, UP, DOWN, LEFT, RIGHT
from styles.base import Renderer, WIDTH, HEIGHT
from styles.nokia import FONT

LW, LH = 240, 144
SCALE = WIDTH // LW
CELL = 8
FX, FY = 8, 24                  # esquina del tablero; el anillo de borde va alrededor
OUTLINE = (24, 20, 37)
TEXT_DARK = (92, 58, 36)

WORLDS = [
    ("PRADERA", {"ground": ((104, 188, 54), (96, 178, 48)), "hud": (46, 82, 34),
                 "wall": ((152, 152, 168), (110, 110, 128), (196, 196, 210)),
                 "deco": [(["x.x", "xx."], (64, 140, 40)), (["x..x", ".xx."], (70, 150, 44)),
                          ([".w.", "wyw", ".w."], None), (["x.x", "xx."], (64, 140, 40))]}),
    ("DESIERTO", {"ground": ((236, 204, 128), (228, 194, 116)), "hud": (120, 76, 40),
                  "wall": ((214, 150, 84), (168, 108, 58), (242, 194, 124)),
                  "deco": [(["xx"], (196, 158, 92)), (["x.", ".x"], (200, 164, 98)),
                           ([".g.", "ggg", ".g."], (92, 160, 72)), (["xx", "xx"], (176, 140, 92))]}),
    ("NIEVE", {"ground": ((236, 242, 252), (224, 233, 247)), "hud": (60, 90, 140),
               "wall": ((140, 196, 240), (92, 146, 210), (212, 238, 255)),
               "deco": [(["x"], (180, 200, 232)), (["x.x", ".x.", "x.x"], (196, 214, 240)),
                        (["xx"], (170, 190, 225)), ([".x.", "xxx", ".x."], (255, 255, 255))]}),
    ("MAZMORRA", {"ground": ((72, 64, 88), (66, 58, 82)), "hud": (34, 28, 44),
                  "wall": ((132, 94, 82), (88, 58, 54), (172, 126, 106)),
                  "deco": [(["xx.", "..x"], (54, 48, 66)), (["x", "x"], (56, 50, 68)),
                           (["xx"], (96, 88, 112)), (["x.."], (54, 48, 66))]}),
]

# Serpiente: (nombre, colores de las bandas)
SNAKES = [
    ("VERDE", [(84, 176, 64)]),
    ("CORAL", [(222, 52, 44), (34, 30, 40), (250, 208, 64), (34, 30, 40)]),
    ("AZUL", [(64, 126, 226)]),
    ("DORADA", [(240, 188, 44)]),
]

APPLE = ["....ngg.", "....n...", ".rrrrrr.", "rrlrrrrr",
         "rlrrrrrr", "rrrrrrdr", ".rrrrdd.", "..rrdd.."]
APPLE_COLORS = {"r": (220, 40, 44), "l": (255, 206, 206), "d": (148, 22, 34),
                "n": (110, 70, 30), "g": (84, 184, 64)}
CROWN = ["y.....y.....y", "yy...yyy...yy", "yyy.yyyyy.yyy", "yyyyyyyyyyyyy",
         "ylyyryybyyryl", "yyyyyyyyyyyyy", "ddddddddddddd"]
CROWN_COLORS = {"y": (250, 202, 44), "l": (255, 250, 206), "r": (230, 40, 64),
                "b": (60, 124, 240), "d": (190, 128, 20)}
BRICK = ["llllllll", "mmmdmmmm", "mmmdmmmm", "dddddddd",
         "mmmmmmdm", "mmmmmmdm", "mmmmmmdm", "dddddddd"]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def pattern_surface(rows, colors):
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                surf.set_at((x, y), colors[ch])
    return surf


def outlined(layer, shadow=True):
    """Devuelve el dibujo con contorno oscuro de 1px y sombra suave abajo-derecha."""
    w, h = layer.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(layer)
    if shadow:
        out.blit(mask.to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0)), (1, 2))
    edge = mask.to_surface(setcolor=OUTLINE, unsetcolor=(0, 0, 0, 0))
    for off in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out.blit(edge, off)
    out.blit(layer, (0, 0))
    return out


def text_width(text, scale=1):
    return (len(text) * 4 - 1) * scale


def draw_text(surf, text, x, y, color, scale=1, outline=True):
    def put(dx, dy, col):
        for i, ch in enumerate(text.upper()):
            for gy, row in enumerate(FONT.get(ch, FONT[" "])):
                for gx, px in enumerate(row):
                    if px == "#":
                        surf.fill(col, (x + dx + (i * 4 + gx) * scale,
                                        y + dy + gy * scale, scale, scale))
    if outline:
        for off in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)):
            put(*off, OUTLINE)
    put(0, 0, color)


def draw_text_centered(surf, text, y, color, scale=1, outline=True, cx=LW // 2):
    draw_text(surf, text, cx - text_width(text, scale) // 2, y, color, scale, outline)


def to_local(direction, u, v):
    """Coordenadas (u adelante, v al costado) -> (x, y) dentro de la celda."""
    return {RIGHT: (u, v), LEFT: (7 - u, v), DOWN: (v, u), UP: (v, 7 - u)}[direction]


class PixelRenderer(Renderer):
    NAME = "PIXEL"
    KEY = "pixel"
    OPTIONS = [("MUNDO", [w[0] for w in WORLDS]), ("SERPIENTE", [s[0] for s in SNAKES])]

    def __init__(self, screen):
        super().__init__(screen)
        self.surf = pygame.Surface((LW, LH))
        self.layer = pygame.Surface((LW, LH), pygame.SRCALPHA)
        self.ground_cache = {}
        self.wall_cache = {}
        self.apple = outlined(pattern_surface(APPLE, APPLE_COLORS))
        self.crown = outlined(pattern_surface(CROWN, CROWN_COLORS))
        self.world = WORLDS[0][1]
        self.world_idx = 0
        self.snake_idx = 0
        self.t = 0.0
        self.particles = []     # [x, y, vx, vy, vida, color]
        self.floaters = []      # [x, y, texto, vida]
        self.shake = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------ escenario (cacheado)
    def ground(self, idx):
        if idx not in self.ground_cache:
            w = WORLDS[idx][1]
            g = pygame.Surface((LW, LH))
            g.fill(w["hud"])
            a, b = w["ground"]
            for r in range(-1, ROWS + 1):
                for c in range(-1, COLS + 1):
                    g.fill(a if (c + r) % 2 else b, (FX + c * CELL, FY + r * CELL, CELL, CELL))
            rnd = random.Random(idx * 97 + 3)
            for r in range(-1, ROWS + 1):
                for c in range(-1, COLS + 1):
                    if rnd.random() < 0.28:
                        rows, col = rnd.choice(w["deco"])
                        colors = {"x": col} if col else {"w": (250, 250, 240), "y": (255, 214, 64)}
                        if col:
                            colors["g"] = col
                        deco = pattern_surface(rows, colors)
                        g.blit(deco, (FX + c * CELL + rnd.randint(0, 8 - deco.get_width()),
                                      FY + r * CELL + rnd.randint(0, 8 - deco.get_height())))
            self.ground_cache[idx] = g
        return self.ground_cache[idx]

    def walls(self, g, idx):
        key = (g.maze_idx, idx, tuple(g.rocks))
        if key not in self.wall_cache:
            w = WORLDS[idx][1]
            main, dark, light = w["wall"]
            brick = pattern_surface(BRICK, {"m": main, "d": dark, "l": light})
            layer = pygame.Surface((LW, LH), pygame.SRCALPHA)
            cells = set(g.walls)
            ring = ([(c, -1) for c in range(-1, COLS + 1)] + [(c, ROWS) for c in range(-1, COLS + 1)]
                    + [(-1, r) for r in range(ROWS)] + [(COLS, r) for r in range(ROWS)])
            if g.maze["border"]:
                cells |= set(ring)
            for c, r in cells:
                layer.blit(brick, (FX + c * CELL, FY + r * CELL))
            result = outlined(layer)
            if not g.maze["border"]:          # se atraviesa: solo una linea punteada
                for c, r in ring:
                    if (c + r) % 2 == 0:
                        x, y = FX + c * CELL + 3, FY + r * CELL + 3
                        result.fill(shade(w["ground"][0], 0.7), (x, y, 2, 2))
            if len(self.wall_cache) > 40:
                self.wall_cache.clear()
            self.wall_cache[key] = result
        return self.wall_cache[key]

    # ------------------------------------------------------------ serpiente
    def draw_snake(self, target, cells, direction, origin=(FX, FY), dead=False):
        bands = SNAKES[self.snake_idx][1]
        if dead:
            bands = [(120, 120, 130), (90, 90, 100)]
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        ox, oy = origin
        n = len(cells)
        for i, (c, r) in enumerate(cells):
            x, y = ox + c * CELL, oy + r * CELL
            band = bands[i % len(bands)]
            inset = 2 if (i == n - 1 and n > 1) else 1          # cola mas fina
            body = pygame.Rect(x + inset, y + inset, CELL - 2 * inset, CELL - 2 * inset)
            layer.fill(band, body)
            for j in (i - 1, i + 1):                             # unir con vecinos
                if 0 <= j < n:
                    dc, dr = cells[j][0] - c, cells[j][1] - r
                    if dc == 1 and dr == 0:
                        layer.fill(band, (body.right, body.top, x + CELL - body.right, body.h))
                    elif dc == -1 and dr == 0:
                        layer.fill(band, (x, body.top, body.left - x, body.h))
                    elif dr == 1 and dc == 0:
                        layer.fill(band, (body.left, body.bottom, body.w, y + CELL - body.bottom))
                    elif dr == -1 and dc == 0:
                        layer.fill(band, (body.left, y, body.w, body.top - y))
            if i > 0 and inset == 1:                             # escamas
                dark, light = shade(band, 0.68), lerp(band, (255, 255, 255), 0.35)
                sx = 1 if i % 2 else 3
                layer.fill(dark, (x + 1 + sx, y + 4, 1, 1))
                layer.fill(dark, (x + 4 - sx + 2, y + 2, 1, 1))
                layer.fill(light, (x + 2 + (i % 2), y + 2, 1, 1))
        target.blit(outlined(layer), (0, 0))

        # cara
        hx, hy = ox + cells[0][0] * CELL, oy + cells[0][1] * CELL
        for v in (2, 5):
            ex, ey = to_local(direction, 4, v)
            px, py = to_local(direction, 5, v)
            if dead:
                target.fill(OUTLINE, (hx + ex, hy + ey, 1, 1))
                target.fill(OUTLINE, (hx + px, hy + py, 1, 1))
            else:
                target.fill((255, 255, 255), (hx + ex, hy + ey, 1, 1))
                target.fill(OUTLINE, (hx + px, hy + py, 1, 1))
        if not dead and (self.t % 2.2) < 0.3:                   # lengua
            for u, v in ((8, 3), (8, 4), (9, 2), (9, 5)):
                lx, ly = to_local(direction, u, v)
                target.fill((230, 40, 70), (hx + lx, hy + ly, 1, 1))

    # ------------------------------------------------------------ efectos
    def burst(self, x, y, colors, n, speed=60):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1) * speed
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v - 20,
                                   random.uniform(0.3, 0.7), random.choice(colors)])

    def on_event(self, ev):
        kind = ev["type"]
        if kind == "eat":
            c, r = ev["pos"]
            self.burst(FX + c * CELL + 4, FY + r * CELL + 4,
                       [APPLE_COLORS["r"], APPLE_COLORS["l"], APPLE_COLORS["g"]], 12)
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = FX + c * CELL + 8, FY + r * CELL + 4
            self.burst(x, y, [CROWN_COLORS["y"], CROWN_COLORS["l"], (255, 255, 255)], 24, 80)
            self.floaters.append([x, y - 6, f"+{ev['points']}", 1.0])
        elif kind == "die":
            c, r = ev["pos"]
            self.burst(FX + c * CELL + 4, FY + r * CELL + 4, SNAKES[self.snake_idx][1], 18, 70)
            self.shake = 0.4
        elif kind == "stage":
            self.flash = 0.5

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            p[3] += 140 * s          # gravedad
            p[4] -= s
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[1] -= 14 * s
            f[3] -= s
        self.floaters = [f for f in self.floaters if f[3] > 0]

    # ------------------------------------------------------------ piezas
    def draw_hud(self, surf, g):
        draw_text(surf, f"{g.score:04d}", 4, 3, (255, 255, 255), scale=2)
        draw_text_centered(surf, g.maze["name"], 6, (255, 236, 170))
        if g.bonus:
            surf.blit(self.crown, (LW - 46, 4))
            draw_text(surf, f"{g.bonus_left:02d}", LW - 26, 3, CROWN_COLORS["y"], scale=2)
        else:
            hud = f"M{g.maze_idx} N{g.level}"
            draw_text(surf, hud, LW - 4 - text_width(hud), 6, (255, 255, 255))

    def draw_field(self, surf, g, show_snake=True):
        surf.blit(self.ground(self.world_idx), (0, 0))
        surf.blit(self.walls(g, self.world_idx), (0, 0))
        if g.food:
            bob = -1 if math.sin(self.t * 5) > 0.3 else 0
            surf.blit(self.apple, (FX + g.food[0] * CELL, FY + g.food[1] * CELL + bob))
        if g.bonus:
            bob = round(math.sin(self.t * 4))
            x, y = FX + g.bonus[0] * CELL + 1, FY + g.bonus[1] * CELL + 1 + bob
            surf.blit(self.crown, (x, y))
            if int(self.t * 6) % 3 == 0:                          # destello
                sx = x + random.randint(0, 12)
                sy = y + random.randint(-2, 6)
                surf.fill((255, 255, 255), (sx, sy, 1, 1))
            frac = g.bonus_left / BONUS_TICKS                     # barra de tiempo
            surf.fill(OUTLINE, (x - 1, y + 9, 15, 3))
            surf.fill(CROWN_COLORS["y"], (x, y + 10, max(1, int(13 * frac)), 1))
        if show_snake and g.snake:
            self.draw_snake(surf, g.snake, g.direction, dead=g.state in ("dying", "over"))
        for x, y, _, _, life, col in self.particles:
            surf.fill(col, (int(x), int(y), 1 if life < 0.25 else 2, 1 if life < 0.25 else 2))
        for x, y, s, life in self.floaters:
            draw_text_centered(surf, s, int(y), (255, 240, 120), cx=int(x))
        self.draw_hud(surf, g)

    def panel(self, surf, rect):
        rect = pygame.Rect(rect)
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 80))
        surf.blit(shadow, rect.move(2, 3))
        surf.fill(OUTLINE, rect)
        surf.fill((244, 226, 180), rect.inflate(-2, -2))
        pygame.draw.rect(surf, (204, 176, 120), rect.inflate(-6, -6), 1)
        return rect

    def dim(self, surf):
        veil = pygame.Surface((LW, LH), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 110))
        surf.blit(veil, (0, 0))

    def draw_menu(self, surf, app):
        surf.blit(self.ground(self.world_idx), (0, 0))
        draw_text_centered(surf, "SNAKE", 2, (255, 214, 64), scale=4)
        head = int(self.t * 7)
        cells = [((head - i) % 30 - 1, 0) for i in range(9)]
        self.draw_snake(surf, cells, RIGHT, origin=(FX, 26))

        rows = app.menu_rows()
        box = self.panel(surf, (34, 40, 172, 10 + len(rows) * 10))
        for i, (label, value) in enumerate(rows):
            y = box.top + 6 + i * 10
            sel = i == app.menu_sel
            color = (200, 40, 40) if sel else TEXT_DARK
            draw_text(surf, label, box.left + 12, y, color, outline=False)
            draw_text_centered(surf, value, y, color, outline=False, cx=box.left + 128)
            if sel:
                draw_text(surf, ">", box.left + 5, y, color, outline=False)
                draw_text(surf, "<", box.left + 90, y, color, outline=False)
                draw_text(surf, ">", box.right - 10, y, color, outline=False)
        draw_text_centered(surf, f"RECORD {app.game.record:04d}", box.bottom + 6, (255, 236, 170))
        if int(self.t * 2) % 2 == 0:
            draw_text_centered(surf, "ESPACIO: JUGAR", LH - 10, (255, 255, 255))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.world_idx = app.opt(0)
        self.snake_idx = app.opt(1)
        g = app.game
        surf = self.surf

        if g.state == "menu":
            self.draw_menu(surf, app)
        elif g.state in ("play", "pause", "stage", "over"):
            self.draw_field(surf, g)
        elif g.state == "dying":
            self.draw_field(surf, g, show_snake=(g.state_time // 120) % 2 == 0)

        if g.state == "pause":
            self.dim(surf)
            self.panel(surf, (80, 58, 80, 26))
            draw_text_centered(surf, "PAUSA", 65, TEXT_DARK, scale=2, outline=False)
        elif g.state == "stage":
            self.dim(surf)
            box = self.panel(surf, (50, 34, 140, 76))
            draw_text_centered(surf, "MAPA SUPERADO!", box.top + 8, (200, 40, 40), outline=False)
            draw_text_centered(surf, f"MAPA {g.maze_idx}", box.top + 22, TEXT_DARK, 2, False)
            draw_text_centered(surf, g.maze["name"], box.top + 40, TEXT_DARK, outline=False)
            draw_text_centered(surf, f"PUNTOS {g.score:04d}", box.top + 58, TEXT_DARK,
                               outline=False)
        elif g.state == "over":
            self.dim(surf)
            box = self.panel(surf, (46, 26, 148, 94))
            draw_text_centered(surf, "FIN DEL JUEGO", box.top + 8, (200, 40, 40), outline=False)
            draw_text_centered(surf, f"{g.score:04d}", box.top + 20, TEXT_DARK, 4, False)
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    draw_text_centered(surf, "NUEVO RECORD!", box.top + 50, (220, 150, 20),
                                       outline=False)
            else:
                draw_text_centered(surf, f"RECORD {g.record:04d}", box.top + 50, TEXT_DARK,
                                   outline=False)
            draw_text_centered(surf, "ESPACIO: OTRA VEZ", box.top + 66, TEXT_DARK, outline=False)
            draw_text_centered(surf, "ESC: MENU", box.top + 78, TEXT_DARK, outline=False)

        if self.flash > 0:
            fl = pygame.Surface((LW, LH), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(170 * self.flash / 0.5)))
            surf.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = max(1, int(self.shake / 0.4 * 3))
            ox, oy = random.randint(-k, k) * SCALE, random.randint(-k, k) * SCALE
        self.screen.fill(OUTLINE)
        self.screen.blit(pygame.transform.scale(surf, (LW * SCALE, LH * SCALE)), (ox, oy))
