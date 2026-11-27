"""Estilo ESPACIO: la serpiente es un cometa, la comida son planetas y los muros asteroides."""

import colorsys
import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, others, tint_mix, WIDTH as W, HEIGHT as H, smooth_runs

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "Orbitron.ttf"

SECTORS = [
    ("NEBULOSA", {"bg": ((6, 2, 18), (24, 6, 40)), "neb": [(150, 40, 170), (60, 40, 180), (220, 60, 120)],
                  "accent": (120, 220, 255), "text": (232, 240, 255), "warn": (255, 120, 200)}),
    ("GALAXIA", {"bg": ((2, 4, 16), (6, 18, 46)), "neb": [(40, 90, 210), (30, 160, 200), (100, 60, 200)],
                 "accent": (110, 200, 255), "text": (230, 240, 255), "warn": (255, 210, 90)}),
    ("SUPERNOVA", {"bg": ((14, 2, 2), (42, 10, 6)), "neb": [(220, 90, 30), (200, 40, 50), (240, 160, 40)],
                   "accent": (255, 190, 90), "text": (255, 240, 225), "warn": (255, 90, 70)}),
    ("AGUJERO NEGRO", {"bg": ((0, 0, 0), (10, 6, 16)), "neb": [(130, 60, 20), (60, 30, 90), (210, 110, 40)],
                       "accent": (255, 160, 70), "text": (245, 235, 225), "warn": (190, 120, 255)}),
]
COMETS = [
    ("CIAN", [(255, 255, 255), (130, 235, 255), (80, 120, 255), (140, 60, 220)]),
    ("FUEGO", [(255, 255, 220), (255, 210, 80), (255, 110, 40), (170, 30, 50)]),
    ("TOXICO", [(240, 255, 220), (150, 255, 120), (40, 200, 120), (20, 100, 90)]),
    ("ARCOIRIS", None),
]
PLANETS = [((210, 96, 64), False), ((64, 140, 232), False), ((222, 186, 124), True), ((196, 230, 255), False),
           ((150, 220, 120), True), ((200, 120, 220), False)]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def gradient(stops, t):
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return lerp(stops[i], stops[i + 1], t - i)


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


def star_points(cx, cy, r_out, r_in, rot=0.0, n=5):
    pts = []
    for k in range(n * 2):
        a = rot + k * math.pi / n - math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


class SpaceRenderer(Renderer):
    NAME = "ESPACIO"
    KEY = "espacio"
    OPTIONS = [("SECTOR", [s[0] for s in SECTORS]), ("COMETA", [c[0] for c in COMETS])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H), 0, 32)
        self.glow = pygame.Surface((W, H), 0, 32)
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_title = font(96)
        except Exception:
            def font(size):
                return pygame.font.Font(None, int(size * 1.3))
            self.font_title = font(96)
        self.font_big = font(44)
        self.font_mid = font(28)
        self.font_small = font(20)
        self.bg_cache = {}
        self.rock_cache = {}
        self.planet_cache = {}
        rnd = random.Random(3)
        self.stars = [[[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0.3, 1), rnd.uniform(0, 6)]
                       for _ in range(n)] for n in (120, 60, 25)]
        self.th = SECTORS[0][1]
        self.sector_idx = 0
        self.comet_idx = 0
        self.t = 0.0
        self.particles = []    # [x, y, vx, vy, vida, vida_max, color, tamano]
        self.rings = []        # ondas expansivas: [x, y, vida, vida_max, color, radio_max]
        self.floaters = []
        self.shake = 0.0
        self.flash = 0.0
        self.warp = 0.0

    # ------------------------------------------------------------ fondo
    def background(self):
        idx = self.sector_idx
        if idx in self.bg_cache:
            return self.bg_cache[idx]
        th = self.th
        bg = pygame.Surface((W, H), 0, 32)
        top, bot = th["bg"]
        for y in range(H):
            pygame.draw.line(bg, lerp(top, bot, y / H), (0, y), (W, y))
        neb = pygame.Surface((W // 4, H // 4), pygame.SRCALPHA)       # nebulosas difusas
        rnd = random.Random(idx * 13 + 1)
        for _ in range(26):
            col = rnd.choice(th["neb"])
            r = rnd.randint(10, 40)
            pygame.draw.circle(neb, (*col, rnd.randint(14, 30)),
                               (rnd.randint(0, W // 4), rnd.randint(0, H // 4)), r)
        neb = pygame.transform.smoothscale(pygame.transform.smoothscale(neb, (W // 16, H // 16)), (W, H))
        bg.blit(neb, (0, 0))
        # planeta gigante de decoracion con anillo
        px, py, pr = W - 90, H - 40, 120
        col = th["neb"][0]
        pygame.draw.ellipse(bg, lerp(col, (255, 255, 255), 0.3), (px - 210, py - 26, 420, 52), 3)
        pygame.draw.circle(bg, lerp(col, (0, 0, 0), 0.35), (px, py), pr)
        pygame.draw.circle(bg, lerp(col, (0, 0, 0), 0.15), (px - 22, py - 22), pr - 26)
        pygame.draw.arc(bg, lerp(col, (255, 255, 255), 0.3), (px - 210, py - 26, 420, 52), math.pi, math.tau, 3)
        # el tablero un poco mas oscuro para que se lea el juego
        veil = pygame.Surface((FW + 12, FH + 12), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 90))
        bg.blit(veil, (FX - 6, FY - 6))
        self.bg_cache[idx] = bg
        return bg

    def draw_stars(self):
        for layer, speed in zip(self.stars, (6, 14, 32)):
            k = speed / 32
            for x, y, b, ph in layer:
                tw = 0.65 + 0.35 * math.sin(self.t * 3 + ph)
                v = int(255 * b * tw * (0.5 + 0.5 * k))
                size = 1 if speed < 20 else 2
                self.canvas.fill((v, v, min(255, v + 20)), (x, y, size, size))

    # ------------------------------------------------------------ asteroides (cacheados)
    def asteroids(self, g):
        key = (self.sector_idx, g.maze_idx, tuple(g.rocks))
        if key in self.rock_cache:
            return self.rock_cache[key]
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for c, r in sorted(g.walls):
            rnd = random.Random(c * 131 + r * 17)
            cx, cy = cell_center(c, r)
            n = 9
            pts = [(cx + math.cos(a) * rad, cy + math.sin(a) * rad)
                   for a, rad in ((k * math.tau / n + rnd.uniform(-0.2, 0.2), rnd.uniform(13, 18))
                                  for k in range(n))]
            base = lerp((118, 104, 96), self.th["neb"][0], 0.15)
            pygame.draw.polygon(surf, lerp(base, (0, 0, 0), 0.45), [(x + 2, y + 3) for x, y in pts])
            pygame.draw.polygon(surf, base, pts)
            pygame.draw.polygon(surf, lerp(base, (255, 255, 255), 0.25),
                                [(cx + (x - cx) * 0.7 - 2, cy + (y - cy) * 0.7 - 3) for x, y in pts])
            for _ in range(2):                                    # crateres
                kx, ky = cx + rnd.uniform(-6, 6), cy + rnd.uniform(-6, 6)
                cr = rnd.uniform(2, 4)
                pygame.draw.circle(surf, lerp(base, (0, 0, 0), 0.4), (kx, ky), cr)
                pygame.draw.circle(surf, lerp(base, (255, 255, 255), 0.15), (kx - 1, ky - 1), cr * 0.5)
        if len(self.rock_cache) > 30:
            self.rock_cache.clear()
        self.rock_cache[key] = surf
        return surf

    def draw_border(self, solid):
        acc = self.th["accent"]
        rect = pygame.Rect(FX - 6, FY - 6, FW + 12, FH + 12)
        pulse = 0.6 + 0.4 * math.sin(self.t * 3)
        col = lerp((0, 0, 0), acc, pulse)
        if solid:   # campo de fuerza
            pygame.draw.rect(self.canvas, col, rect, 2, 8)
            pygame.draw.rect(self.glow, col, rect, 6, 8)
        else:       # portales: guiones que fluyen
            off = int(self.t * 40) % 24
            for x in range(rect.left + off, rect.right - 12, 24):
                for y in (rect.top, rect.bottom - 2):
                    self.canvas.fill(acc, (x, y, 12, 2))
                    self.glow.fill(acc, (x, y - 2, 12, 6))
            for y in range(rect.top + off, rect.bottom - 12, 24):
                for x in (rect.left, rect.right - 2):
                    self.canvas.fill(acc, (x, y, 2, 12))
                    self.glow.fill(acc, (x - 2, y, 6, 12))

    # ------------------------------------------------------------ planetas y supernova
    def planet(self, kind):
        if kind in self.planet_cache:
            return self.planet_cache[kind]
        col, ringed = PLANETS[kind]
        r = 11
        size = 44
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        body = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(body, col, (c, c), r)
        for k in range(-2, 3):                                     # bandas
            pygame.draw.line(body, lerp(col, (255, 255, 255), 0.18 if k % 2 else 0), (c - r, c + k * 4),
                             (c + r, c + k * 4), 2)
        pygame.draw.circle(body, (0, 0, 0, 120), (c + 5, c + 4), r)    # sombra
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), r)
        body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        ring_rect = (c - 19, c - 5, 38, 10)
        if ringed:
            pygame.draw.arc(s, lerp(col, (255, 255, 255), 0.4), ring_rect, 0, math.pi, 2)
        s.blit(body, (0, 0))
        if ringed:
            pygame.draw.arc(s, lerp(col, (255, 255, 255), 0.4), ring_rect, math.pi, math.tau, 2)
        self.planet_cache[kind] = s
        return s

    def draw_food(self, cell):
        kind = (cell[0] * 7 + cell[1] * 3) % len(PLANETS)
        x, y = cell_center(*cell)
        img = self.planet(kind)
        self.canvas.blit(img, img.get_rect(center=(x, y)))
        pygame.draw.circle(self.glow, scale_c(PLANETS[kind][0], 0.6), (x, y), 15)
        a = self.t * 2.2                                            # lunita
        mx, my = x + math.cos(a) * 17, y + math.sin(a) * 7
        pygame.draw.circle(self.canvas, (220, 220, 230), (mx, my), 2.5)

    def draw_supernova(self, g):
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        col = self.th["warn"]
        pulse = 1 + 0.18 * math.sin(self.t * 8)
        for k in range(8):                                          # rayos
            a = self.t * 1.5 + k * math.tau / 8
            l = (20 if k % 2 else 28) * pulse
            p2 = (x + math.cos(a) * l, y + math.sin(a) * l)
            pygame.draw.line(self.canvas, col, (x, y), p2, 2)
            pygame.draw.line(self.glow, col, (x, y), p2, 5)
        pygame.draw.circle(self.glow, col, (x, y), 16 * pulse)
        pygame.draw.circle(self.canvas, lerp(col, (255, 255, 255), 0.5), (x, y), 9 * pulse)
        pygame.draw.circle(self.canvas, (255, 255, 255), (x, y), 5)
        frac = g.bonus_left / BONUS_TICKS
        rect = pygame.Rect(x - 30, y - 30, 60, 60)
        pygame.draw.arc(self.canvas, col, rect, math.pi / 2, math.pi / 2 + math.tau * frac, 2)

    # ------------------------------------------------------------ cometa
    def comet_color(self, t):
        stops = COMETS[self.comet_idx][1]
        if stops is None:   # arcoiris
            r, g, b = colorsys.hsv_to_rgb((t * 0.8 + self.t * 0.25) % 1, 0.65, 1)
            return (int(r * 255), int(g * 255), int(b * 255))
        return gradient(stops, t)

    def draw_comet(self, runs_px, dead=False, tint=None):
        if tint:                                                    # rival: cometa de su color
            own = self.comet_color
            self.comet_color = lambda t: lerp(lerp(tint, (255, 255, 255), 0.35), scale_c(tint, 0.35), t)
            try:
                return self.draw_comet(runs_px, dead)
            finally:
                self.comet_color = own
        pts = [p for run in runs_px for p in run]
        n = len(pts)
        for run in runs_px:                                         # estela continua
            for k in range(len(run) - 1):
                i = sum(len(r) for r in runs_px[:runs_px.index(run)]) + k
                t = i / max(1, n - 1)
                col = self.comet_color(t) if not dead else lerp((90, 90, 100), (40, 40, 50), t)
                w = max(2, int(2 * (4 + 9 * (1 - t))))
                pygame.draw.line(self.canvas, col, run[k], run[k + 1], w)
                pygame.draw.line(self.glow, scale_c(col, 0.7), run[k], run[k + 1], w + 8)
        for i in range(n - 1, -1, -1):
            t = i / max(1, n - 1)
            col = self.comet_color(t) if not dead else (100, 100, 110)
            r = 4 + 9 * (1 - t)
            pygame.draw.circle(self.canvas, col, pts[i], r)
            pygame.draw.circle(self.glow, scale_c(col, 0.8), pts[i], r + 6)
        hx, hy = pts[0]
        pygame.draw.circle(self.canvas, (255, 255, 255), (hx, hy), 8 if not dead else 5)
        pygame.draw.circle(self.glow, (255, 255, 255), (hx, hy), 20)
        if not dead and random.random() < 0.7:                      # polvo estelar de la cola
            tx, ty = pts[-1]
            col = self.comet_color(1.0)
            self.particles.append([tx, ty, random.uniform(-15, 15), random.uniform(-15, 15),
                                   0.6, 0.6, col, 2])

    # ------------------------------------------------------------ efectos
    def burst(self, x, y, colors, n, speed=160, size=3):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1) * speed
            life = random.uniform(0.4, 0.9)
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, life, life,
                                   random.choice(colors), size])

    def on_event(self, ev):
        kind = ev["type"]
        th = self.th
        if kind == "eat":
            x, y = cell_center(*ev["pos"])
            col = PLANETS[(ev["pos"][0] * 7 + ev["pos"][1] * 3) % len(PLANETS)][0]
            self.burst(x, y, [col, (255, 255, 255)], 18)
            self.rings.append([x, y, 0.4, 0.4, col, 30])
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = cell_center(c, r)
            x += CELL / 2
            self.burst(x, y, [th["warn"], (255, 255, 255)], 36, 260, 4)
            self.rings.append([x, y, 0.7, 0.7, th["warn"], 110])
            self.floaters.append([x, y - 24, f"+{ev['points']}", 1.1])
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            self.burst(x, y, [(255, 255, 255), (255, 200, 80), (255, 90, 40), self.comet_color(0.5)], 60, 320, 5)
            self.rings.append([x, y, 0.8, 0.8, (255, 180, 80), 160])
            self.shake, self.flash = 0.45, 0.25
        elif kind == "stage":
            self.warp = 1.0
        elif kind == "rock":
            x, y = cell_center(*ev["pos"])
            self.rings.append([x, y, 0.5, 0.5, th["accent"], 40])

    def update(self, dt):
        s = dt / 1000
        self.t += s
        for layer, speed in zip(self.stars, (6, 14, 32)):
            mult = 1 + 30 * self.warp
            for st in layer:
                st[0] -= speed * s * mult
                if st[0] < 0:
                    st[0] += W
                    st[1] = random.uniform(0, H)
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        self.warp = max(0.0, self.warp - s * 0.8)
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            p[2] *= 0.95
            p[3] *= 0.95
            p[4] -= s
        self.particles = [p for p in self.particles if p[4] > 0][-500:]
        for r in self.rings:
            r[2] -= s
        self.rings = [r for r in self.rings if r[2] > 0]
        for f in self.floaters:
            f[1] -= 30 * s
            f[3] -= s
        self.floaters = [f for f in self.floaters if f[3] > 0]

    def draw_effects(self):
        for x, y, _, _, life, life_max, col, size in self.particles:
            k = life / life_max
            c = scale_c(col, 0.3 + 0.7 * k)
            pygame.draw.circle(self.canvas, c, (x, y), max(1, size * k))
            pygame.draw.circle(self.glow, c, (x, y), size * k + 2)
        for x, y, life, life_max, col, rmax in self.rings:
            k = 1 - life / life_max
            rad = 6 + rmax * k
            c = scale_c(col, 1 - k)
            pygame.draw.circle(self.canvas, c, (x, y), rad, 2)
            pygame.draw.circle(self.glow, c, (x, y), rad, 6)
        for x, y, s, life in self.floaters:
            self.text(s, self.font_mid, self.th["warn"], center=(x, y))
        if self.warp > 0:                                            # salto hiperespacial
            rnd = random.Random(int(self.t * 30))
            cx, cy = W / 2, H / 2
            for _ in range(70):
                a = rnd.uniform(0, math.tau)
                r1 = rnd.uniform(40, 300)
                r2 = r1 + 60 + 500 * self.warp
                col = scale_c(self.th["accent"], self.warp)
                p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
                p2 = (cx + math.cos(a) * r2, cy + math.sin(a) * r2)
                pygame.draw.line(self.canvas, col, p1, p2, 2)
                pygame.draw.line(self.glow, col, p1, p2, 4)

    def apply_glow(self):
        small = pygame.transform.smoothscale(self.glow, (W // 4, H // 4))
        small = pygame.transform.box_blur(small, 3)
        self.canvas.blit(pygame.transform.smoothscale(small, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)

    # ------------------------------------------------------------ textos y paneles
    def text(self, s, f, color, glow=True, **anchor):
        img = f.render(s, True, color)
        rect = img.get_rect(**anchor)
        self.canvas.blit(img, rect)
        if glow:
            self.glow.blit(f.render(s, True, scale_c(color, 0.6)), rect)
        return rect

    def holo_panel(self, rect):
        rect = pygame.Rect(rect)
        acc = self.th["accent"]
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((6, 12, 30, 200))
        for y in range(0, rect.h, 4):                                # lineas de holograma
            panel.fill((*acc, 10), (0, y, rect.w, 1))
        self.canvas.blit(panel, rect)
        L = 22                                                        # esquinas
        for (x, y), (dx, dy) in ((rect.topleft, (1, 1)), (rect.topright, (-1, 1)),
                                 (rect.bottomleft, (1, -1)), (rect.bottomright, (-1, -1))):
            x -= 1 if dx < 0 else 0
            y -= 1 if dy < 0 else 0
            pygame.draw.line(self.canvas, acc, (x, y), (x + dx * L, y), 3)
            pygame.draw.line(self.canvas, acc, (x, y), (x, y + dy * L), 3)
        pygame.draw.rect(self.canvas, scale_c(acc, 0.5), rect, 1)
        return rect

    def draw_hud(self, g):
        th = self.th
        self.text(f"{g.score:05d}", self.font_big, th["accent"], midleft=(FX, 48))
        self.text(f"SECTOR {g.maze['name']}", self.font_small, th["text"], glow=False, center=(W // 2, 48))
        if g.bonus:
            x = W - FX - 110
            pygame.draw.polygon(self.canvas, th["warn"], star_points(x, 48, 14, 6, self.t))
            self.text(f"{g.bonus_left:02d}", self.font_big, th["warn"], midleft=(x + 24, 48))
        else:
            self.text(f"MAPA {g.maze_idx}  NIVEL {g.level}", self.font_small, th["text"], glow=False,
                      midright=(W - FX, 48))

    def draw_menu(self, app):
        th = self.th
        self.text("SNAKE", self.font_title, th["accent"], center=(W // 2, 70))
        self.text("M I S I O N   G A L A C T I C A", self.font_small, th["text"], center=(W // 2, 128))
        n = 18                                                       # cometa de muestra
        pts = [(W // 2 + 260 - k * 30 + math.sin(self.t) * 40,
                170 + math.sin(self.t * 2.5 - k * 0.45) * 16) for k in range(n)]
        self.draw_comet([pts])
        rows = app.menu_rows()
        box = self.holo_panel((W // 2 - 280, 206, 560, 26 + len(rows) * 40))
        for i, (label, value) in enumerate(rows):
            y = box.top + 32 + i * 40
            sel = i == app.menu_sel
            col = th["accent"] if sel else lerp(th["text"], (0, 0, 0), 0.35)
            if sel:
                pygame.draw.rect(self.canvas, lerp((6, 12, 30), th["accent"], 0.18),
                                 (box.left + 14, y - 16, box.w - 28, 32))
                self.text("<", self.font_mid, col, center=(box.left + 290, y))
                self.text(">", self.font_mid, col, center=(box.right - 30, y))
            self.text(label, self.font_mid, col, glow=sel, midleft=(box.left + 34, y))
            self.text(value, self.font_mid, col, glow=sel, center=(box.left + 410, y))
        self.text(f"RECORD {app.game.record:05d}", self.font_small, th["warn"], center=(W // 2, box.bottom + 22))
        if int(self.t * 2) % 2 == 0:
            self.text("ESPACIO PARA DESPEGAR", self.font_mid, th["text"], center=(W // 2, H - 28))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.sector_idx, self.comet_idx = app.opt(0), app.opt(1)
        self.th = SECTORS[self.sector_idx][1]
        th = self.th
        g = app.game

        self.canvas.blit(self.background(), (0, 0))
        self.glow.fill((0, 0, 0))
        self.draw_stars()

        if g.state == "menu":
            self.draw_menu(app)
        else:
            self.draw_border(g.maze["border"])
            self.canvas.blit(self.asteroids(g), (0, 0))
            if g.food:
                self.draw_food(g.food)
            if g.bonus:
                self.draw_supernova(g)
            dead = g.state in ("dying", "over")
            for o in others(g):                                     # rivales (modo en linea)
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(o)]
                self.draw_comet(runs, o.dead, o.tint)
            if g.snake and g.state != "dying":
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]
                self.draw_comet(runs, dead)
            self.draw_hud(g)
        self.draw_effects()
        self.apply_glow()

        if g.state == "pause":
            box = self.holo_panel((W // 2 - 220, H // 2 - 100, 440, 200))
            self.text("PAUSA", self.font_big, th["accent"], center=(W // 2, box.top + 48))
            for i, (s, sel) in enumerate(pause_items(app)):
                self.mark_pause(i, box.top + 112 + i * 44)
                self.text(s, self.font_mid, th["accent"] if sel else th["text"], glow=sel,
                          center=(W // 2, box.top + 112 + i * 44))
        elif g.state == "stage":
            box = self.holo_panel((W // 2 - 280, H // 2 - 100, 560, 200))
            self.text("SALTO HIPERESPACIAL", self.font_mid, th["warn"], center=(W // 2, box.top + 44))
            self.text(f"SECTOR {g.maze_idx}: {g.maze['name']}", self.font_big, th["accent"],
                      center=(W // 2, box.centery + 4))
            self.text(f"PUNTOS {g.score:05d}", self.font_small, th["text"], center=(W // 2, box.bottom - 34))
        elif g.state == "over":
            box = self.holo_panel((W // 2 - 280, H // 2 - 140, 560, 280))
            self.text("MISION FALLIDA", self.font_mid, th["warn"], center=(W // 2, box.top + 44))
            self.text(f"{g.score:05d}", self.font_title, th["accent"], center=(W // 2, box.top + 120))
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    self.text("NUEVO RECORD!", self.font_mid, th["warn"], center=(W // 2, box.top + 190))
            else:
                self.text(f"RECORD {g.record:05d}", self.font_small, th["text"], center=(W // 2, box.top + 190))
            self.text("ESPACIO: OTRA VEZ    ESC: MENU", self.font_small, th["text"], glow=False,
                      center=(W // 2, box.bottom - 30))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 240, 220, int(200 * self.flash / 0.25)))
            self.canvas.blit(fl, (0, 0))
        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.45 * 10)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (ox, oy))


def scale_c(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)
