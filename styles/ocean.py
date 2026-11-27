"""Estilo OCEANO: serpiente marina que nada ondulando, arrecifes de coral, peces y cofre del tesoro."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, others, tint_mix, WIDTH as W, HEIGHT as H, smooth_runs

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "LilitaOne-Regular.ttf"
DARK = (12, 30, 52)

WATERS = [
    ("ARRECIFE", {"water": ((96, 214, 232), (14, 78, 150)), "sand": ((236, 214, 160), (222, 198, 142)),
                  "rock": (118, 108, 140), "coral": [(255, 120, 150), (255, 164, 80), (200, 96, 222)],
                  "accent": (255, 222, 90), "glow": False}),
    ("ABISMO", {"water": ((12, 42, 84), (0, 4, 18)), "sand": ((18, 26, 44), (14, 22, 38)),
                "rock": (42, 48, 74), "coral": [(80, 255, 220), (160, 120, 255), (80, 180, 255)],
                "accent": (90, 255, 220), "glow": True}),
    ("LAGUNA", {"water": ((128, 206, 172), (18, 88, 92)), "sand": ((204, 204, 152), (190, 190, 138)),
                "rock": (92, 112, 92), "coral": [(240, 140, 120), (250, 210, 110), (150, 222, 140)],
                "accent": (255, 240, 140), "glow": False}),
    ("ARTICO", {"water": ((186, 228, 246), (28, 70, 122)), "sand": ((226, 236, 246), (212, 224, 238)),
                "rock": (150, 172, 204), "coral": [(160, 222, 255), (255, 255, 255), (140, 190, 240)],
                "accent": (120, 222, 255), "glow": False}),
]
CREATURES = [   # (nombre, colores de bandas, color de manchas)
    ("ANGUILA", [(108, 172, 72)], (196, 226, 96)),
    ("MARINA", [(40, 62, 112), (232, 232, 242)], (90, 120, 190)),
    ("DRAGON", [(222, 72, 62)], (255, 204, 64)),
    ("DORADA", [(242, 190, 60)], (255, 242, 172)),
]
FISH_COLORS = [((255, 140, 40), (255, 255, 255)), ((60, 120, 255), (255, 220, 60)),
               ((255, 100, 170), (255, 230, 240)), ((120, 220, 120), (30, 80, 40))]
POPS = ["¡Glup!", "¡Ñam!", "¡Blub!", "¡Splash!"]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


class OceanRenderer(Renderer):
    NAME = "OCEANO"
    KEY = "oceano"
    OPTIONS = [("AGUA", [w[0] for w in WATERS]), ("CRIATURA", [c[0] for c in CREATURES])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H), 0, 32)
        self.alpha = pygame.Surface((W, H), pygame.SRCALPHA)
        self.glow = pygame.Surface((W, H), 0, 32)
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_title = font(100)
        except Exception:
            def font(size):
                return pygame.font.Font(None, int(size * 1.2))
            self.font_title = font(100)
        self.font_big = font(50)
        self.font_mid = font(34)
        self.font_small = font(26)
        self.bg_cache = {}
        self.reef_cache = {}
        self.th = WATERS[0][1]
        self.water_idx = 0
        self.creature_idx = 0
        self.t = 0.0
        rnd = random.Random(21)
        self.school = [[rnd.uniform(0, W), rnd.uniform(110, H - 30), rnd.uniform(14, 34),
                        rnd.uniform(8, 16), rnd.choice((-1, 1))] for _ in range(9)]
        self.bubbles = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(2, 5), rnd.uniform(0, 6)]
                        for _ in range(26)]
        self.particles = []    # [x, y, vx, vy, vida, vida_max, tipo, color, tamano]
        self.pops = []         # [x, y, texto, vida, vida_max]
        self.shake = 0.0
        self.wave = 0.0        # ola de transicion entre mapas
        self.bubble_timer = 0.0

    # ------------------------------------------------------------ fondo (cacheado)
    def background(self, border, key):
        ck = (self.water_idx, key, border)
        if ck in self.bg_cache:
            return self.bg_cache[ck]
        th = self.th
        bg = pygame.Surface((W, H), 0, 32)
        top, bot = th["water"]
        for y in range(H):
            pygame.draw.line(bg, lerp(top, bot, y / H), (0, y), (W, y))
        if key != "menu":
            field = pygame.Rect(FX - 8, FY - 8, FW + 16, FH + 16)
            a, b = th["sand"]
            sand = pygame.Surface(field.size)
            sand.fill(a)
            rnd = random.Random(9)
            for y in range(6, field.h, 14):                       # ondas de la arena
                pts = [(x, y + math.sin(x / 40 + y) * 3) for x in range(0, field.w + 10, 10)]
                pygame.draw.lines(sand, b, False, pts, 2)
            for _ in range(160):
                sand.fill(lerp(a, (0, 0, 0), rnd.uniform(0.05, 0.15)),
                          (rnd.randrange(field.w), rnd.randrange(field.h), 2, 2))
            for _ in range(10):                                     # conchitas
                x, y = rnd.randrange(20, field.w - 20), rnd.randrange(20, field.h - 20)
                pygame.draw.circle(sand, lerp(a, (255, 200, 210), 0.5), (x, y), 4)
                pygame.draw.line(sand, b, (x, y + 3), (x, y - 3), 1)
            mask = pygame.Surface(field.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), 0, 18)
            sand = sand.convert_alpha()
            sand.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            bg.blit(sand, field)
            if border:   # borde de rocas
                rnd = random.Random(4)
                for x in range(field.left, field.right, 22):
                    for y in (field.top, field.bottom):
                        pygame.draw.circle(bg, th["rock"], (x + rnd.randint(-3, 3), y), rnd.randint(9, 13))
                for y in range(field.top, field.bottom, 22):
                    for x in (field.left, field.right):
                        pygame.draw.circle(bg, th["rock"], (x, y + rnd.randint(-3, 3)), rnd.randint(9, 13))
        if len(self.bg_cache) > 30:
            self.bg_cache.clear()
        self.bg_cache[ck] = bg
        return bg

    def reef(self, g):
        """Arrecife de coral sobre cada muro y roca (cacheado)."""
        key = (self.water_idx, g.maze_idx, tuple(g.rocks))
        if key in self.reef_cache:
            return self.reef_cache[key]
        th = self.th
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for c, r in sorted(g.walls):
            rnd = random.Random(c * 97 + r * 13)
            x, y = FX + c * CELL, FY + r * CELL
            rock = th["rock"]
            pygame.draw.rect(surf, lerp(rock, (0, 0, 0), 0.4), (x + 1, y + 3, CELL - 2, CELL - 2), 0, 9)
            pygame.draw.rect(surf, rock, (x + 1, y + 1, CELL - 2, CELL - 3), 0, 9)
            pygame.draw.ellipse(surf, lerp(rock, (255, 255, 255), 0.2), (x + 5, y + 4, 14, 6))
            col = rnd.choice(th["coral"])
            kind = rnd.randrange(3)
            cx, cy = x + CELL / 2, y + CELL / 2
            if kind == 0:                                          # coral de ramas
                for a in (-0.6, 0, 0.6):
                    ex, ey = cx + math.sin(a) * 10, cy - math.cos(a) * 11
                    pygame.draw.line(surf, col, (cx, cy + 8), (ex, ey), 3)
                    pygame.draw.circle(surf, lerp(col, (255, 255, 255), 0.4), (ex, ey), 3)
            elif kind == 1:                                        # coral cerebro
                pygame.draw.circle(surf, col, (cx, cy), 10)
                for k in range(-1, 2):
                    pygame.draw.arc(surf, lerp(col, (0, 0, 0), 0.3), (cx - 8, cy - 4 + k * 5, 16, 8), 0, math.pi, 2)
            else:                                                  # anemona
                for a in range(8):
                    ang = a * math.tau / 8
                    pygame.draw.line(surf, col, (cx, cy), (cx + math.cos(ang) * 10, cy + math.sin(ang) * 10), 3)
                pygame.draw.circle(surf, lerp(col, (255, 255, 255), 0.5), (cx, cy), 4)
        if len(self.reef_cache) > 30:
            self.reef_cache.clear()
        self.reef_cache[key] = surf
        return surf

    # ------------------------------------------------------------ ambiente
    def draw_rays(self):
        for i in range(5):
            x = 80 + i * 200 + math.sin(self.t * 0.4 + i) * 40
            pts = [(x, 0), (x + 50, 0), (x + 190, H), (x + 70, H)]
            pygame.draw.polygon(self.alpha, (255, 255, 255, 16), pts)

    def draw_caustics(self):
        rect = pygame.Rect(FX - 8, FY - 8, FW + 16, FH + 16)
        self.alpha.set_clip(rect)
        a = 55 if not self.th["glow"] else 14
        for k in range(0, FH + 40, 36):
            y0 = FY + k
            pts = [(x, y0 + math.sin(x / 55 + self.t * 1.4 + k) * 9) for x in range(rect.left, rect.right + 20, 20)]
            pygame.draw.lines(self.alpha, (255, 255, 255, a), False, pts, 3)
        for k in range(0, FW + 40, 44):
            x0 = FX + k
            pts = [(x0 + math.sin(y / 50 - self.t * 1.2 + k) * 10, y) for y in range(rect.top, rect.bottom + 20, 20)]
            pygame.draw.lines(self.alpha, (255, 255, 255, a), False, pts, 3)
        self.alpha.set_clip(None)

    def draw_school(self):
        col = (*lerp(self.th["water"][1], (0, 0, 0), 0.3), 90)
        for x, y, sp, size, d in self.school:
            pygame.draw.ellipse(self.alpha, col, (x - size, y - size / 2.4, size * 2, size / 1.2))
            tx = x - d * size
            pygame.draw.polygon(self.alpha, col, [(tx, y), (tx - d * size * 0.7, y - size * 0.5),
                                                  (tx - d * size * 0.7, y + size * 0.5)])

    def draw_bubbles(self):
        for x, y, r, ph in self.bubbles:
            bx = x + math.sin(self.t * 2 + ph) * 4
            pygame.draw.circle(self.alpha, (255, 255, 255, 110), (bx, y), r, 1)
            pygame.draw.circle(self.alpha, (255, 255, 255, 150), (bx - r * 0.35, y - r * 0.35), max(1, r * 0.3))

    def draw_seaweed(self, g):
        for c, r in g.walls:
            if (c * 7 + r * 3) % 4:
                continue
            x, y = FX + c * CELL + CELL / 2 + 8, FY + r * CELL + CELL - 4
            for s in (-1, 1):
                pts = [(x + s * 3 + math.sin(self.t * 2 + k * 0.7 + c) * k * 1.2, y - k * 6) for k in range(6)]
                pygame.draw.lines(self.canvas, (60, 170, 90) if not self.th["glow"] else (60, 220, 160),
                                  False, pts, 3)

    # ------------------------------------------------------------ criatura
    def draw_creature(self, runs_px, direction, dead=False, tint=None):
        name, bands, spot = CREATURES[self.creature_idx]
        if tint:                                                  # rival: misma criatura, su color
            bands = [tint, lerp(tint, (0, 0, 0), 0.25)]
            spot = lerp(tint, (255, 255, 255), 0.55)
        if dead:
            bands, spot = [(140, 150, 160)], (180, 186, 196)
        pts_all = []
        for run in runs_px:                                       # ondulacion al nadar
            out = []
            for k, (x, y) in enumerate(run):
                i = len(pts_all) + k
                a, b = run[max(0, k - 1)], run[min(len(run) - 1, k + 1)]
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.hypot(dx, dy) or 1
                amp = 0 if dead else min(1.0, i / 3) * 3.0
                off = math.sin(self.t * 9 - i * 0.8) * amp
                out.append((x - dy / d * off, y + dx / d * off))
            pts_all.extend(out)
            run[:] = out
        n = len(pts_all)
        radii = [12 - 5 * i / max(1, n - 1) for i in range(n)]
        outline = lerp(bands[0], (0, 0, 0), 0.55)
        for run in runs_px:
            for a, b in zip(run, run[1:]):
                pygame.draw.line(self.canvas, outline, a, b, 24)
        for i in range(n - 1, -1, -1):
            pygame.draw.circle(self.canvas, outline, pts_all[i], radii[i] + 3)
        for i in range(n - 1, -1, -1):
            col = bands[i % len(bands)] if len(bands) > 1 else lerp(bands[0], lerp(bands[0], (0, 0, 0), 0.25), i / max(1, n))
            pygame.draw.circle(self.canvas, col, pts_all[i], radii[i])
            if self.th["glow"] and not dead:
                pygame.draw.circle(self.glow, lerp((0, 0, 0), spot, 0.5), pts_all[i], radii[i] * 0.6)
        for i in range(1, n, 2):                                   # manchas y aleta dorsal
            x, y = pts_all[i]
            pygame.draw.circle(self.canvas, spot, (x, y), max(2, radii[i] * 0.35))
        for run in runs_px:
            if len(run) > 2:
                pygame.draw.lines(self.canvas, lerp(spot, (255, 255, 255), 0.2), False, run[1:], 2)
        # cabeza
        hx, hy = pts_all[0]
        fx, fy = direction
        sx, sy = -fy, fx
        head = bands[0]
        for s in (-1, 1):                                          # aletas pectorales
            bx, by = hx - fx * 6 + sx * 12 * s, hy - fy * 6 + sy * 12 * s
            flap = math.sin(self.t * 10) * 3
            pygame.draw.polygon(self.canvas, lerp(head, spot, 0.5),
                                [(hx + sx * 8 * s, hy + sy * 8 * s), (bx - fx * 6 + sx * flap * s, by - fy * 6 + sy * flap * s),
                                 (bx + fx * 3, by + fy * 3)])
        pygame.draw.circle(self.canvas, outline, (hx, hy), 16)
        pygame.draw.circle(self.canvas, head, (hx, hy), 13)
        for s in (-1, 1):
            ex, ey = hx + fx * 4 + sx * 6 * s, hy + fy * 4 + sy * 6 * s
            if dead:
                pygame.draw.line(self.canvas, DARK, (ex - 3, ey - 3), (ex + 3, ey + 3), 2)
                pygame.draw.line(self.canvas, DARK, (ex - 3, ey + 3), (ex + 3, ey - 3), 2)
            else:
                pygame.draw.circle(self.canvas, (255, 255, 255), (ex, ey), 4.5)
                pygame.draw.circle(self.canvas, DARK, (ex + fx * 1.5, ey + fy * 1.5), 2.5)
                if self.th["glow"]:
                    pygame.draw.circle(self.glow, (120, 255, 220), (ex, ey), 6)
        return hx + fx * 14, hy + fy * 14

    # ------------------------------------------------------------ comida y tesoro
    def draw_fish(self, cell):
        body, stripe = FISH_COLORS[(cell[0] * 5 + cell[1] * 3) % len(FISH_COLORS)]
        cx, cy = cell_center(*cell)
        swim = math.sin(self.t * 1.6)
        d = 1 if math.cos(self.t * 1.6) > 0 else -1
        x, y = cx + swim * 4, cy + math.sin(self.t * 3) * 1.5
        wag = math.sin(self.t * 14) * 3
        tail = [(x - d * 8, y), (x - d * 15, y - 6 + wag), (x - d * 15, y + 6 + wag)]
        pygame.draw.polygon(self.canvas, DARK, [(px, py) for px, py in tail], 0)
        pygame.draw.polygon(self.canvas, body, [(x - d * 9, y), (x - d * 14, y - 4 + wag), (x - d * 14, y + 4 + wag)])
        pygame.draw.ellipse(self.canvas, DARK, (x - 11, y - 8, 22, 16))
        pygame.draw.ellipse(self.canvas, body, (x - 9.5, y - 6.5, 19, 13))
        pygame.draw.line(self.canvas, stripe, (x, y - 6), (x, y + 6), 3)
        pygame.draw.circle(self.canvas, (255, 255, 255), (x + d * 5, y - 1.5), 2.5)
        pygame.draw.circle(self.canvas, DARK, (x + d * 5.5, y - 1.5), 1.3)
        if self.th["glow"]:                                        # luz de pez abisal
            lx, ly = x + d * 12, y - 10
            pygame.draw.line(self.canvas, body, (x + d * 6, y - 6), (lx, ly), 1)
            pygame.draw.circle(self.canvas, (255, 255, 200), (lx, ly), 3)
            pygame.draw.circle(self.glow, (200, 255, 200), (lx, ly), 10)

    def draw_chest(self, g):
        c, r = g.bonus
        x, y = FX + c * CELL + CELL, FY + r * CELL + CELL / 2 + 4
        open_k = (math.sin(self.t * 3) + 1) / 2
        body = pygame.Rect(x - 16, y - 6, 32, 16)
        if open_k > 0.3:                                           # brillo del oro
            pygame.draw.circle(self.alpha, (255, 230, 120, 90), (x, y - 6), 18 * open_k)
            pygame.draw.ellipse(self.canvas, (255, 210, 60), (x - 12, y - 10, 24, 8))
        lid_h = 10 * (1 - open_k) + 3
        lid = pygame.Rect(x - 16, y - 6 - lid_h - 6 * open_k, 32, lid_h)
        pygame.draw.rect(self.canvas, DARK, body.inflate(4, 4), 0, 3)
        pygame.draw.rect(self.canvas, (150, 92, 44), body, 0, 2)
        pygame.draw.rect(self.canvas, DARK, lid.inflate(4, 4), 0, 4)
        pygame.draw.rect(self.canvas, (176, 110, 54), lid, 0, 4)
        for bx in (x - 10, x + 8):
            pygame.draw.rect(self.canvas, (240, 196, 70), (bx, body.top, 3, body.h))
        pygame.draw.rect(self.canvas, (240, 196, 70), (x - 3, body.top + 2, 6, 6))
        if int(self.t * 5) % 3 == 0:
            pygame.draw.circle(self.canvas, (255, 255, 255), (x + 9, y - 12), 2)
        for k in range(math.ceil(5 * g.bonus_left / BONUS_TICKS)):  # burbujas = tiempo
            pygame.draw.circle(self.canvas, (255, 255, 255), (x - 16 + k * 8, body.bottom + 9), 3, 1)

    # ------------------------------------------------------------ texto
    def outlined(self, s, font, color, outline=DARK, width=3, **anchor):
        base = font.render(s, True, color)
        edge = font.render(s, True, outline)
        w, h = base.get_size()
        surf = pygame.Surface((w + width * 2, h + width * 2), pygame.SRCALPHA)
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if dx * dx + dy * dy <= width * width:
                    surf.blit(edge, (dx + width, dy + width))
        surf.blit(base, (width, width))
        rect = surf.get_rect(**anchor)
        self.canvas.blit(surf, rect)
        return rect

    def glass(self, rect):
        rect = pygame.Rect(rect)
        p = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(p, (*DARK, 170), p.get_rect(), 0, 24)
        pygame.draw.rect(p, (255, 255, 255, 150), p.get_rect(), 3, 24)
        pygame.draw.arc(p, (255, 255, 255, 110), (14, 10, rect.w // 2, 60), math.pi * 0.55, math.pi * 0.95, 4)
        self.canvas.blit(p, rect)
        return rect

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        if kind == "eat":
            x, y = cell_center(*ev["pos"])
            for _ in range(10):
                self.particles.append([x, y, random.uniform(-50, 50), random.uniform(-90, -30),
                                       0.9, 0.9, "bubble", (255, 255, 255), random.uniform(2, 5)])
            self.pops = [p for p in self.pops if p[2] not in POPS]
            self.pops.append([x, y - 28, random.choice(POPS), 0.9, 0.9])
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = cell_center(c, r)
            x += CELL / 2
            for _ in range(24):
                a = random.uniform(math.pi * 1.1, math.pi * 1.9)
                v = random.uniform(80, 200)
                self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, 1.1, 1.1, "coin",
                                       (255, 210, 60), 5])
            self.pops.append([x, y - 34, f"¡Tesoro! +{ev['points']}", 1.2, 1.2])
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            for _ in range(30):
                self.particles.append([x + random.uniform(-10, 10), y, random.uniform(-70, 70),
                                       random.uniform(-160, -40), 1.2, 1.2, "bubble", (255, 255, 255),
                                       random.uniform(3, 9)])
            self.pops.append([x, y - 34, "¡Blub blub!", 1.3, 1.3])
            self.shake = 0.4
        elif kind == "stage":
            self.wave = 1.0
        elif kind == "rock":
            x, y = cell_center(*ev["pos"])
            for _ in range(10):
                self.particles.append([x, y, random.uniform(-60, 60), random.uniform(-60, 20),
                                       0.6, 0.6, "sand", self.th["sand"][1], 3])

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.wave = max(0.0, self.wave - s * 0.7)
        for f in self.school:
            f[0] += f[2] * f[4] * s
            if f[0] < -60:
                f[0] = W + 50
            elif f[0] > W + 60:
                f[0] = -50
        for b in self.bubbles:
            b[1] -= (20 + b[2] * 8) * s
            if b[1] < -10:
                b[1], b[0] = H + 10, random.uniform(0, W)
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            if p[6] == "bubble":
                p[2] *= 0.96
                p[3] -= 30 * s
            elif p[6] == "coin":
                p[3] += 260 * s
            p[4] -= s
        self.particles = [p for p in self.particles if p[4] > 0][-400:]
        for p in self.pops:
            p[1] -= 26 * s
            p[3] -= s
        self.pops = [p for p in self.pops if p[3] > 0]

    def draw_effects(self):
        for x, y, _, _, life, life_max, kind, col, size in self.particles:
            k = life / life_max
            if kind == "bubble":
                pygame.draw.circle(self.alpha, (255, 255, 255, int(200 * k)), (x, y), size, 1)
                pygame.draw.circle(self.alpha, (255, 255, 255, int(220 * k)), (x - size * 0.3, y - size * 0.3),
                                   max(1, size * 0.3))
            elif kind == "coin":
                w = abs(math.sin(self.t * 12 + x)) * size + 1
                pygame.draw.ellipse(self.canvas, (190, 140, 20), (x - w, y - size, w * 2, size * 2))
                pygame.draw.ellipse(self.canvas, col, (x - w + 1, y - size + 1, max(1, w * 2 - 2), size * 2 - 2))
            else:
                pygame.draw.circle(self.canvas, col, (x, y), size * k)
        for x, y, s, life, _ in self.pops:
            self.outlined(s, self.font_mid, (255, 255, 255), center=(x, y))
        if self.wave > 0:                                           # ola que cruza la pantalla
            front = W * 1.2 * (1 - self.wave) - 100
            pts = [(front + math.sin(y / 30 + self.t * 6) * 26, y) for y in range(0, H + 20, 20)]
            pygame.draw.polygon(self.alpha, (255, 255, 255, 90), [(-10, 0)] + pts + [(-10, H)])

    # ------------------------------------------------------------ hud, menu
    def draw_hud(self, g):
        self.outlined(f"{g.score:04d}", self.font_big, (255, 255, 255), midleft=(FX, 46))
        self.outlined(g.maze["name"].capitalize(), self.font_mid, self.th["accent"], center=(W // 2, 46))
        if g.bonus:
            self.outlined(f"Tesoro {g.bonus_left}", self.font_mid, (255, 214, 70), midright=(W - FX, 46))
        else:
            self.outlined(f"Mapa {g.maze_idx} · Nivel {g.level}", self.font_small, (255, 255, 255),
                          midright=(W - FX, 46))

    def draw_menu(self, app):
        th = self.th
        self.outlined("Snake", self.font_title, (255, 255, 255), width=5, center=(W // 2, 70))
        self.outlined("del Océano", self.font_mid, th["accent"], width=3, center=(W // 2 + 110, 120))
        n = 14                                                      # criatura de muestra
        pts = [(W // 2 + 250 - k * 30 + math.sin(self.t * 0.8) * 30, 168) for k in range(n)]
        self.draw_creature([pts], (1, 0))
        rows = app.menu_rows()
        box = self.glass((W // 2 - 290, 204, 580, 30 + len(rows) * 42))
        for i, (label, value) in enumerate(rows):
            y = box.top + 36 + i * 42
            sel = i == app.menu_sel
            col = th["accent"] if sel else (226, 240, 250)
            if sel:
                pygame.draw.circle(self.canvas, (255, 255, 255), (box.left + 32, y), 7, 2)
                self.outlined("<", self.font_mid, col, width=2, center=(box.left + 300, y))
                self.outlined(">", self.font_mid, col, width=2, center=(box.right - 34, y))
            self.outlined(label.capitalize(), self.font_mid, col, width=2, midleft=(box.left + 52, y))
            self.outlined(value.capitalize(), self.font_mid, col, width=2, center=(box.left + 420, y))
        self.outlined(f"Récord {app.game.record}", self.font_small, (255, 255, 255), center=(W // 2 - 170, H - 26))
        if int(self.t * 2) % 2 == 0:
            self.outlined("¡ESPACIO para bucear!", self.font_small, th["accent"], center=(W // 2 + 120, H - 26))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.water_idx, self.creature_idx = app.opt(0), app.opt(1)
        self.th = WATERS[self.water_idx][1]
        th = self.th
        g = app.game
        self.alpha.fill((0, 0, 0, 0))
        self.glow.fill((0, 0, 0))

        if g.state == "menu":
            self.canvas.blit(self.background(True, "menu"), (0, 0))
            self.draw_school()
            self.draw_rays()
            self.draw_bubbles()
            self.canvas.blit(self.alpha, (0, 0))
            self.alpha.fill((0, 0, 0, 0))
            self.draw_menu(app)
        else:
            self.canvas.blit(self.background(g.maze["border"], g.maze_idx), (0, 0))
            self.draw_caustics()
            self.canvas.blit(self.alpha, (0, 0))
            self.alpha.fill((0, 0, 0, 0))
            self.canvas.blit(self.reef(g), (0, 0))
            self.draw_seaweed(g)
            if g.food:
                self.draw_fish(g.food)
            if g.bonus:
                self.draw_chest(g)
            dead = g.state in ("dying", "over")
            blink = g.state == "dying" and (g.state_time // 120) % 2 == 1
            for o in others(g):                                     # rivales (modo en linea)
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(o)]
                self.draw_creature(runs, o.direction, o.dead, o.tint)
            if g.snake and not blink:
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]
                mouth = self.draw_creature(runs, g.direction, dead)
                self.bubble_timer += 1
                if not dead and self.bubble_timer % 24 == 0:
                    self.particles.append([mouth[0], mouth[1], random.uniform(-10, 10), -40, 1.0, 1.0,
                                           "bubble", (255, 255, 255), random.uniform(2, 4)])
            self.draw_school()
            self.draw_rays()
            self.draw_bubbles()
            self.draw_effects()
            self.canvas.blit(self.alpha, (0, 0))
            self.alpha.fill((0, 0, 0, 0))
            self.draw_hud(g)

        if th["glow"]:                                              # bioluminiscencia
            small = pygame.transform.smoothscale(self.glow, (W // 4, H // 4))
            small = pygame.transform.box_blur(small, 3)
            self.canvas.blit(pygame.transform.smoothscale(small, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)

        if g.state == "pause":
            box = self.glass((W // 2 - 190, H // 2 - 110, 380, 220))
            self.outlined("Pausa", self.font_big, (255, 255, 255), center=(W // 2, box.top + 52))
            for i, (s, sel) in enumerate(pause_items(app, ["Seguir nadando", "Menú principal"])):
                self.mark_pause(i, box.top + 124 + i * 48)
                self.outlined(s, self.font_mid, th["accent"] if sel else (255, 255, 255),
                              center=(W // 2, box.top + 124 + i * 48))
        elif g.state == "stage":
            box = self.glass((W // 2 - 290, H // 2 - 110, 580, 220))
            self.outlined("¡Marea alta!", self.font_mid, th["accent"], center=(W // 2, box.top + 46))
            self.outlined(f"Mapa {g.maze_idx}: {g.maze['name'].capitalize()}", self.font_big, (255, 255, 255),
                          center=(W // 2, box.centery + 4))
            self.outlined(f"Puntos {g.score}", self.font_small, (255, 255, 255), center=(W // 2, box.bottom - 40))
        elif g.state == "over":
            box = self.glass((W // 2 - 290, H // 2 - 150, 580, 300))
            self.outlined("Fin de la inmersión", self.font_mid, th["accent"], center=(W // 2, box.top + 46))
            self.outlined(f"{g.score}", self.font_title, (255, 255, 255), width=5, center=(W // 2, box.top + 126))
            rec = "¡Nuevo récord!" if g.new_record else f"Récord {g.record}"
            if not g.new_record or int(self.t * 2.5) % 2 == 0:
                self.outlined(rec, self.font_small, (255, 214, 70), center=(W // 2, box.top + 200))
            self.outlined("ESPACIO: otra vez   ESC: menú", self.font_small, (255, 255, 255), center=(W // 2, box.bottom - 36))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.4 * 8)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill(th["water"][1])
        self.screen.blit(self.canvas, (ox, oy))
