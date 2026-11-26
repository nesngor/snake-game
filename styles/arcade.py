"""Estilo ARCADE: maquinita de los 80 en pantalla de tubo (scanlines, brillo, viñeta)."""

import math
import random

import pygame

from game import COLS, ROWS, BONUS_TICKS, UP, DOWN, LEFT, RIGHT
from styles.base import Renderer, pause_items, WIDTH as W, HEIGHT as H
from styles.nokia import FONT

LW, LH = 320, 192
SCALE = W // LW
CELL = 10
FX, FY = 20, 36

RED, WHITE, CYAN = (255, 60, 60), (255, 255, 255), (0, 220, 255)
YELLOW, MAGENTA, GREEN = (255, 230, 40), (255, 60, 200), (40, 230, 80)
TITLE_BANDS = [(255, 240, 80), (255, 200, 40), (255, 150, 30), (255, 100, 30), (240, 50, 40)]
MONITORS = [("COLOR", None), ("VERDE", (90, 255, 130)), ("AMBAR", (255, 176, 40))]
CRT_LEVELS = [("FUERTE", 120, 70), ("SUAVE", 60, 40), ("NO", 0, 0)]   # (nombre, scanlines, brillo)

COIN = ["..####..", ".#yyyy#.", "#yy#yyy#", "#y#yyyy#",
        "#y#yyyy#", "#yyyyyy#", ".#yyyy#.", "..####.."]
UFO = ["......####......", "....#cccccc#....", "..############..",
       ".#mmmmmmmmmmmm#.", "#mLmmLmmLmmLmmL#", ".#mmmmmmmmmmmm#.",
       "..############..", "...#........#..."]


def pattern(rows, colors):
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                surf.set_at((x, y), colors[ch])
    return surf


def text_width(text, scale=1):
    return (len(text) * 4 - 1) * scale


def draw_text(surf, text, x, y, color, scale=1):
    """color puede ser una tupla o una lista de 5 colores (uno por fila de la letra)."""
    for i, ch in enumerate(text.upper()):
        for gy, row in enumerate(FONT.get(ch, FONT[" "])):
            col = color[gy] if isinstance(color, list) else color
            for gx, px in enumerate(row):
                if px == "#":
                    surf.fill(col, (x + (i * 4 + gx) * scale, y + gy * scale, scale, scale))


def text_c(surf, text, y, color, scale=1, cx=LW // 2):
    draw_text(surf, text, cx - text_width(text, scale) // 2, y, color, scale)


def to_local(direction, u, v):
    return {RIGHT: (u, v), LEFT: (7 - u, v), DOWN: (v, u), UP: (v, 7 - u)}[direction]


class ArcadeRenderer(Renderer):
    NAME = "ARCADE"
    KEY = "arcade"
    OPTIONS = [("MONITOR", [m[0] for m in MONITORS]), ("CRT", [c[0] for c in CRT_LEVELS])]

    def __init__(self, screen):
        super().__init__(screen)
        self.low = pygame.Surface((LW, LH))
        self.big = pygame.Surface((W, H))
        self.coin = pattern(COIN, {"#": (200, 120, 0), "y": YELLOW})
        self.ufo = {k: pattern(UFO, {"#": (170, 170, 200), "c": CYAN, "m": MAGENTA, "L": col})
                    for k, col in ((0, YELLOW), (1, RED))}
        self.scan = {}
        for name, alpha, _ in CRT_LEVELS:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            for y in range(0, H, SCALE):
                s.fill((0, 0, 0, alpha), (0, y + SCALE - 1, W, 1))
            self.scan[name] = s
        self.vignette = pygame.Surface((W, H), pygame.SRCALPHA)
        steps = 26
        for k in range(steps):
            a = int(170 * (1 - k / steps) ** 2.2)
            pygame.draw.rect(self.vignette, (0, 0, 0, a), (k * 3, k * 3, W - 6 * k, H - 6 * k), 3, 70)
        self.bezel = pygame.Surface((W, H), pygame.SRCALPHA)
        self.bezel.fill((0, 0, 0, 255))
        pygame.draw.rect(self.bezel, (0, 0, 0, 0), (4, 4, W - 8, H - 8), 0, 46)
        self.t = 0.0
        self.particles = []    # [x, y, vx, vy, vida, color]
        self.floaters = []     # [x, y, texto, vida]
        self.shake = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        if kind in ("eat", "die"):
            c, r = ev["pos"]
            x, y = FX + c * CELL + 5, FY + r * CELL + 5
            cols = [YELLOW, WHITE, (255, 160, 0)] if kind == "eat" else [RED, WHITE, YELLOW, GREEN]
            for _ in range(10 if kind == "eat" else 30):
                a = random.uniform(0, math.tau)
                v = random.uniform(20, 90 if kind == "eat" else 130)
                self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v,
                                       random.uniform(0.3, 0.7), random.choice(cols)])
            if kind == "die":
                self.shake = 0.35
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = FX + c * CELL + 10, FY + r * CELL + 5
            for _ in range(24):
                a = random.uniform(0, math.tau)
                v = random.uniform(30, 120)
                self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v,
                                       random.uniform(0.4, 0.8), random.choice([CYAN, MAGENTA, WHITE])])
            self.floaters.append([x, y - 6, str(ev["points"]), 1.0])
        elif kind == "stage":
            self.flash = 0.4

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            p[4] -= s
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[1] -= 12 * s
            f[3] -= s
        self.floaters = [f for f in self.floaters if f[3] > 0]

    # ------------------------------------------------------------ sprites
    def draw_snake(self, surf, cells, direction, origin=(FX, FY), flash=None):
        ox, oy = origin
        n = len(cells)
        for i, (c, r) in enumerate(cells):
            x, y = ox + c * CELL, oy + r * CELL
            if flash:
                col = flash
                inner = flash
            elif i == 0:
                col, inner = YELLOW, (255, 170, 0)
            else:
                col, inner = (GREEN, (10, 130, 40)) if i % 2 else ((90, 255, 120), (20, 160, 60))
            surf.fill(col, (x + 1, y + 1, 8, 8))
            if i > 0:
                surf.fill(inner, (x + 3, y + 3, 4, 4))
            if i + 1 < n:                                   # union con el siguiente
                nc, nr = cells[i + 1]
                if nr == r and abs(nc - c) == 1:
                    surf.fill(col, (x + 9 if nc > c else x - 1, y + 1, 2, 8))
                elif nc == c and abs(nr - r) == 1:
                    surf.fill(col, (x + 1, y + 9 if nr > r else y - 1, 8, 2))
        hx, hy = ox + cells[0][0] * CELL + 1, oy + cells[0][1] * CELL + 1
        for v in (1, 5):
            ex, ey = to_local(direction, 5, v)
            surf.fill((0, 0, 0), (hx + ex, hy + ey, 2, 2))

    def draw_walls(self, surf, walls):
        for c, r in walls:
            x, y = FX + c * CELL, FY + r * CELL
            surf.fill((170, 30, 50), (x, y, CELL, CELL))
            surf.fill((255, 110, 120), (x, y, CELL, 1))
            surf.fill((255, 110, 120), (x, y, 1, CELL))
            surf.fill((90, 10, 30), (x, y + 5, CELL, 1))
            surf.fill((90, 10, 30), (x + 5, y, 1, 5))
            surf.fill((90, 10, 30), (x + 2, y + 5, 1, 5))

    def draw_border(self, surf, solid):
        rect = pygame.Rect(FX - 3, FY - 3, COLS * CELL + 6, ROWS * CELL + 6)
        if solid:
            pygame.draw.rect(surf, CYAN, rect, 1)
            pygame.draw.rect(surf, MAGENTA, rect.inflate(-2, -2), 1)
        else:
            for x in range(rect.left, rect.right, 4):
                surf.fill(CYAN, (x, rect.top, 2, 1))
                surf.fill(CYAN, (x, rect.bottom - 1, 2, 1))
            for y in range(rect.top, rect.bottom, 4):
                surf.fill(CYAN, (rect.left, y, 1, 2))
                surf.fill(CYAN, (rect.right - 1, y, 1, 2))

    def draw_coin(self, surf, cell):
        widths = [8, 6, 4, 2, 4, 6]
        w = widths[int(self.t * 10) % 6]
        img = pygame.transform.scale(self.coin, (w, 8))
        x, y = FX + cell[0] * CELL + 5, FY + cell[1] * CELL + 5
        surf.blit(img, img.get_rect(center=(x, y)))

    def draw_hud(self, surf, g):
        draw_text(surf, "1UP", FX, 4, RED)
        draw_text(surf, f"{g.score:06d}", FX, 12, WHITE, 2)
        text_c(surf, "HI-SCORE", 4, RED)
        text_c(surf, f"{g.record:06d}", 12, WHITE, 2)
        if g.bonus:
            surf.blit(self.ufo[int(self.t * 6) % 2], (LW - FX - 46, 13))
            draw_text(surf, f"{g.bonus_left:02d}", LW - FX - 22, 12, CYAN, 2)
            draw_text(surf, "BONUS", LW - FX - text_width("BONUS"), 4, MAGENTA)
        else:
            s = f"STAGE {g.maze_idx}"
            draw_text(surf, s, LW - FX - text_width(s), 4, CYAN)
            s = f"LV {g.level}"
            draw_text(surf, s, LW - FX - text_width(s, 2), 12, WHITE, 2)
        draw_text(surf, g.maze["name"], FX, LH - 8, (150, 150, 170))
        s = "CREDIT 01"
        draw_text(surf, s, LW - FX - text_width(s), LH - 8, (150, 150, 170))

    def draw_field(self, surf, g):
        self.draw_border(surf, g.maze["border"])
        self.draw_walls(surf, g.walls)
        if g.food:
            self.draw_coin(surf, g.food)
        if g.bonus:
            bob = round(math.sin(self.t * 5))
            surf.blit(self.ufo[int(self.t * 6) % 2],
                      (FX + g.bonus[0] * CELL + 2, FY + g.bonus[1] * CELL + 1 + bob))
            frac = g.bonus_left / BONUS_TICKS
            surf.fill(CYAN, (FX + g.bonus[0] * CELL + 2, FY + g.bonus[1] * CELL + 10, int(16 * frac), 1))
        if g.snake:
            flash = None
            if g.state in ("dying", "over"):
                flash = RED if (g.state_time // 100) % 2 == 0 or g.state == "over" else WHITE
            self.draw_snake(surf, g.snake, g.direction, flash=flash)
        for x, y, _, _, life, col in self.particles:
            surf.fill(col, (int(x), int(y), 2 if life > 0.3 else 1, 2 if life > 0.3 else 1))
        for x, y, s, life in self.floaters:
            text_c(surf, s, int(y), CYAN, cx=int(x))
        self.draw_hud(surf, g)

    def box(self, surf, rect, color):
        rect = pygame.Rect(rect)
        surf.fill((0, 0, 0), rect)
        pygame.draw.rect(surf, color, rect, 1)
        pygame.draw.rect(surf, color, rect.inflate(-4, -4), 1)
        return rect

    def draw_menu(self, surf, app):
        text_c(surf, "SNAKE", 10, TITLE_BANDS, 5)
        text_c(surf, "- ARCADE EDITION -", 40, CYAN)
        rows = app.menu_rows()
        top = 54
        for i, (label, value) in enumerate(rows):
            y = top + i * 11
            sel = i == app.menu_sel
            col = YELLOW if sel else WHITE
            draw_text(surf, label, 86, y, col)
            text_c(surf, value, y, col if sel else (170, 170, 190), cx=214)
            if sel and int(self.t * 4) % 2 == 0:
                draw_text(surf, ">", 76, y, RED)
                draw_text(surf, "<", 176, y, RED)
                draw_text(surf, ">", 250, y, RED)
        y_end = top + len(rows) * 11 + 6
        text_c(surf, f"HI-SCORE {app.game.record:06d}", y_end, RED)
        if int(self.t * 1.6) % 2 == 0:
            text_c(surf, "PRESS SPACE", y_end + 14, WHITE, 2)
        # demo: serpiente persiguiendo una moneda en la ultima fila
        pos = int(self.t * 9)
        cells = [((pos - i) % 30 - 1, 0) for i in range(7)]
        coin_c = (pos + 6) % 30 - 1
        self.draw_snake(surf, cells, RIGHT, origin=(10, LH - 22))
        img = pygame.transform.scale(self.coin, ([8, 6, 4, 2, 4, 6][int(self.t * 10) % 6], 8))
        surf.blit(img, img.get_rect(center=(10 + coin_c * CELL + 5, LH - 22 + 5)))
        s = "CREDIT 01"
        draw_text(surf, s, LW - FX - text_width(s), LH - 8, (150, 150, 170))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        monitor = MONITORS[app.opt(0)][1]
        crt_name, _, glow = CRT_LEVELS[app.opt(1)]
        g = app.game
        surf = self.low
        surf.fill((0, 0, 0))

        if g.state == "menu":
            self.draw_menu(surf, app)
        else:
            self.draw_field(surf, g)

        if g.state == "pause":
            r = self.box(surf, (LW // 2 - 70, LH // 2 - 32, 140, 64), CYAN)
            if int(self.t * 2) % 2 == 0:
                text_c(surf, "PAUSE", r.top + 8, YELLOW, 2)
            for i, (s, sel) in enumerate(pause_items(app, ["CONTINUE", "MAIN MENU"])):
                text_c(surf, s, r.top + 32 + i * 14, YELLOW if sel else WHITE)
        elif g.state == "stage":
            r = self.box(surf, (LW // 2 - 90, LH // 2 - 34, 180, 68), YELLOW)
            text_c(surf, "STAGE CLEAR!", r.top + 8, TITLE_BANDS, 2)
            text_c(surf, f"NEXT: {g.maze_idx} {g.maze['name']}", r.top + 30, CYAN)
            text_c(surf, f"SCORE {g.score:06d}", r.top + 44, WHITE)
        elif g.state == "over":
            r = self.box(surf, (LW // 2 - 96, LH // 2 - 44, 192, 88), RED)
            text_c(surf, "GAME OVER", r.top + 8, RED, 3)
            text_c(surf, f"SCORE {g.score:06d}", r.top + 32, WHITE)
            if g.new_record and int(self.t * 3) % 2 == 0:
                text_c(surf, "NEW HI-SCORE!", r.top + 44, YELLOW)
            text_c(surf, "PRESS SPACE", r.top + 60, CYAN)
            text_c(surf, "ESC: MENU", r.top + 72, (170, 170, 190))

        if self.flash > 0:
            k = int(200 * self.flash / 0.4)
            surf.fill((k, k, k), special_flags=pygame.BLEND_ADD)

        if monitor:   # monitor monocromo: todo en un solo color de fosforo
            mono = pygame.transform.grayscale(surf)
            mono.fill(monitor, special_flags=pygame.BLEND_MULT)
            surf = mono

        # ---- pantalla de tubo
        pygame.transform.scale(surf, (W, H), self.big)
        if glow:
            small = pygame.transform.smoothscale(surf, (LW // 2, LH // 2))
            small = pygame.transform.box_blur(small, 2)
            bloom = pygame.transform.smoothscale(small, (W, H))
            bloom.fill((glow * 2, glow * 2, glow * 2), special_flags=pygame.BLEND_MULT)
            self.big.blit(bloom, (0, 0), special_flags=pygame.BLEND_ADD)
            self.big.blit(self.scan[crt_name], (0, 0))
            self.big.blit(self.vignette, (0, 0))
            flicker = random.randint(0, 10)
            if flicker:
                fl = pygame.Surface((W, H), pygame.SRCALPHA)
                fl.fill((0, 0, 0, flicker))
                self.big.blit(fl, (0, 0))
            self.big.blit(self.bezel, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.35 * 3) * SCALE
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.big, (ox, oy))
