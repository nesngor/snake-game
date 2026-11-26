"""Estilo VITRAL: ventana de catedral, vidrio de colores unido con plomo y luz que entra."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, smooth_runs, WIDTH as W, HEIGHT as H

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "Cinzel.ttf"

LEAD = (34, 32, 38)
GOLD = (232, 184, 72)
STONE = (92, 86, 80)

# Juegos de vidrio: (nombre, colores). El primero es el de la serpiente, el segundo su franja.
WINDOWS = [
    ("ROSETON", [(30, 120, 80), (220, 170, 40), (180, 30, 50), (36, 64, 176), (112, 52, 152)]),
    ("TIFFANY", [(110, 156, 84), (226, 152, 60), (200, 112, 104), (56, 138, 140), (232, 196, 112)]),
    ("MODERNO", [(30, 80, 200), (250, 210, 30), (220, 40, 40), (236, 236, 228), (48, 48, 60)]),
]
# Luz: (nombre, brillo del vidrio, color de los rayos, intensidad de los rayos)
LIGHTS = [
    ("DIA", 1.0, (255, 250, 225), 34),
    ("ATARDECER", 0.86, (255, 170, 90), 40),
    ("NOCHE", 0.5, (130, 150, 255), 22),
]
POPS = ["¡AMÉN!", "¡GLORIA!", "¡ÑAM!", "¡BRILLA!"]


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


def octagon(cx, cy, r, rot=0.0):
    return [(cx + math.cos(rot + math.pi / 8 + k * math.pi / 4) * r,
             cy + math.sin(rot + math.pi / 8 + k * math.pi / 4) * r) for k in range(8)]


class VitralRenderer(Renderer):
    NAME = "VITRAL"
    KEY = "vitral"
    OPTIONS = [("VENTANA", [w[0] for w in WINDOWS]), ("LUZ", [l[0] for l in LIGHTS])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_title = font(96)
        except Exception:
            def font(size):
                return pygame.font.Font(None, int(size * 1.15))
            self.font_title = font(96)
        self.font_title.set_bold(True)
        self.font_big = font(52)
        self.font_big.set_bold(True)
        self.font_mid = font(32)
        self.font_mid.set_bold(True)
        self.font_small = font(22)
        self.font_small.set_bold(True)
        self.t = 0.0
        self.win_idx = 0
        self.light_idx = 0
        self.bg_cache = {}
        self.static_cache = {}
        self.jewel_cache = {}
        self.ray_cache = {}
        self.effects = []     # [tipo, x, y, vx, vy, vida, vida_max, extra]
        self.shake = 0.0
        self.flash = 0.0

    @property
    def colors(self):
        return WINDOWS[self.win_idx][1]

    @property
    def light(self):
        return LIGHTS[self.light_idx]

    def lit(self, color):
        return shade(color, self.light[1])

    # ------------------------------------------------------------ vidrio de fondo (cacheado)
    def mosaic(self, surf, area, spacing, pale, rnd, lead_w=3, lead=LEAD):
        """Llena 'area' con piezas de vidrio irregulares unidas con plomo."""
        a = pygame.Rect(area)
        nx, ny = a.w // spacing + 1, a.h // spacing + 1
        grid = []
        for j in range(ny + 1):
            row = []
            for i in range(nx + 1):
                x = a.left + a.w * i / nx
                y = a.top + a.h * j / ny
                if 0 < i < nx:
                    x += rnd.uniform(-spacing * 0.3, spacing * 0.3)
                if 0 < j < ny:
                    y += rnd.uniform(-spacing * 0.3, spacing * 0.3)
                row.append((x, y))
            grid.append(row)
        pieces = []
        for j in range(ny):
            for i in range(nx):
                p00, p10 = grid[j][i], grid[j][i + 1]
                p01, p11 = grid[j + 1][i], grid[j + 1][i + 1]
                if rnd.random() < 0.5:                       # cada cuadro se parte en 2 triangulos
                    pieces += [[p00, p10, p11], [p00, p11, p01]]
                elif rnd.random() < 0.5:
                    pieces += [[p00, p10, p01], [p10, p11, p01]]
                else:
                    pieces.append([p00, p10, p11, p01])
        for poly in pieces:
            base = rnd.choice(self.colors)
            col = self.lit(mix(base, (205, 200, 190), pale))
            pygame.draw.polygon(surf, col, poly)
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            inner = [(cx + (x - cx) * 0.55 - 2, cy + (y - cy) * 0.55 - 2) for x, y in poly]
            pygame.draw.polygon(surf, mix(col, (255, 255, 255), 0.12), inner)   # centro mas claro
            for _ in range(2):                                                  # burbujas del vidrio
                bx, by = cx + rnd.uniform(-6, 6), cy + rnd.uniform(-6, 6)
                surf.set_at((int(bx), int(by)), mix(col, (255, 255, 255), 0.35))
        for poly in pieces:
            pygame.draw.polygon(surf, lead, poly, lead_w)

    def background(self):
        key = (self.win_idx, self.light_idx)
        if key in self.bg_cache:
            return self.bg_cache[key]
        rnd = random.Random(17)
        surf = pygame.Surface((W, H))
        surf.fill(self.lit(STONE))
        for y in range(0, H, 24):                                   # sillares de piedra
            off = 0 if (y // 24) % 2 == 0 else 36
            pygame.draw.line(surf, shade(self.lit(STONE), 0.7), (0, y), (W, y), 2)
            for x in range(-off, W, 72):
                pygame.draw.line(surf, shade(self.lit(STONE), 0.7), (x, y), (x, y + 24), 2)
        for _ in range(1600):
            x, y = rnd.randrange(W), rnd.randrange(H)
            surf.set_at((x, y), shade(self.lit(STONE), rnd.uniform(0.85, 1.12)))
        field = pygame.Rect(FX, FY, FW, FH)
        self.mosaic(surf, field, 68, 0.7, rnd, lead_w=2,           # vidrio palido: la serpiente resalta
                    lead=self.lit((96, 92, 100)))
        pygame.draw.rect(surf, shade(self.lit(STONE), 0.55), field.inflate(16, 16), 8)
        pygame.draw.rect(surf, shade(self.lit(STONE), 1.25), field.inflate(16, 16), 2)
        self.bg_cache[key] = surf
        return surf

    def menu_background(self):
        key = ("menu", self.win_idx, self.light_idx)
        if key in self.bg_cache:
            return self.bg_cache[key]
        rnd = random.Random(23)
        surf = pygame.Surface((W, H))
        self.mosaic(surf, surf.get_rect(), 64, 0.25, rnd, lead_w=4)   # ventana entera, colores vivos
        self.bg_cache[key] = surf
        return surf

    def static_layer(self, g):
        key = (self.win_idx, self.light_idx, g.maze_idx, tuple(g.rocks))
        if key in self.static_cache:
            return self.static_cache[key]
        surf = self.background().copy()
        field = pygame.Rect(FX, FY, FW, FH)
        if g.maze["border"]:                                        # marco de plomo y oro
            pygame.draw.rect(surf, LEAD, field.inflate(6, 6), 6)
            pygame.draw.rect(surf, self.lit(GOLD), field.inflate(2, 2), 2)
        else:                                                       # se atraviesa: borde punteado dorado
            for x in range(field.left, field.right, 16):
                pygame.draw.line(surf, self.lit(GOLD), (x, field.top - 2), (x + 7, field.top - 2), 3)
                pygame.draw.line(surf, self.lit(GOLD), (x, field.bottom + 1), (x + 7, field.bottom + 1), 3)
            for y in range(field.top, field.bottom, 16):
                pygame.draw.line(surf, self.lit(GOLD), (field.left - 2, y), (field.left - 2, y + 7), 3)
                pygame.draw.line(surf, self.lit(GOLD), (field.right + 1, y), (field.right + 1, y + 7), 3)
        for c, r, w, h in g.wall_rects:                             # muros: piedra tallada
            rect = pygame.Rect(FX + c * CELL, FY + r * CELL, w * CELL, h * CELL)
            self.stone_block(surf, rect, c * 7 + r)
        if len(self.static_cache) > 30:
            self.static_cache.clear()
        self.static_cache[key] = surf
        return surf

    def stone_block(self, surf, rect, seed):
        rnd = random.Random(seed)
        base = self.lit((116, 108, 98))
        surf.fill(shade(base, 0.55), rect)
        inner = rect.inflate(-4, -4)
        surf.fill(base, inner)
        pygame.draw.line(surf, shade(base, 1.3), inner.topleft, inner.topright, 2)    # bisel
        pygame.draw.line(surf, shade(base, 1.3), inner.topleft, inner.bottomleft, 2)
        pygame.draw.line(surf, shade(base, 0.7), inner.bottomleft, inner.bottomright, 2)
        pygame.draw.line(surf, shade(base, 0.7), inner.topright, inner.bottomright, 2)
        for y in range(rect.top + CELL, rect.bottom, CELL):                          # juntas
            pygame.draw.line(surf, shade(base, 0.6), (rect.left + 2, y), (rect.right - 3, y), 1)
        for x in range(rect.left + CELL, rect.right, CELL):
            pygame.draw.line(surf, shade(base, 0.6), (x, rect.top + 2), (x, rect.bottom - 3), 1)
        for _ in range(rect.w * rect.h // 120):
            surf.set_at((rnd.randrange(inner.left, inner.right), rnd.randrange(inner.top, inner.bottom)),
                        shade(base, rnd.uniform(0.82, 1.1)))

    # ------------------------------------------------------------ luz
    def rays(self):
        key = self.light_idx
        if key not in self.ray_cache:
            _, _, col, alpha = self.light
            # suma de luz (BLEND_RGB_ADD ignora la transparencia): fondo negro y color ya atenuado
            s = pygame.Surface((W * 2, H))
            s.fill((0, 0, 0))
            for k, (x, w) in enumerate(((120, 90), (330, 150), (560, 70), (760, 120), (1040, 100),
                                        (1300, 160), (1560, 80))):
                a = alpha * (0.6 + 0.4 * (k % 3) / 2) / 255
                pygame.draw.polygon(s, shade(col, a), [(x, 0), (x + w, 0), (x + w - 260, H), (x - 260, H)])
            # los rayos se repiten cada W px: la segunda mitad copia la primera para que no haya salto
            s.blit(s, (W, 0), (0, 0, W, H))
            self.ray_cache[key] = s
        return self.ray_cache[key]

    def apply_light(self):
        off = int((self.t * 14) % W)                                # los rayos se desplazan despacio
        self.canvas.blit(self.rays(), (-off, 0), special_flags=pygame.BLEND_RGB_ADD)
        if self.light_idx == 2:                                     # noche: luz de velas abajo
            glow = pygame.Surface((W, 160))
            glow.fill((0, 0, 0))
            flick = 0.85 + 0.15 * math.sin(self.t * 9) * math.sin(self.t * 3.3)
            for i in range(8):                                      # elipses cada vez mas brillantes
                pygame.draw.ellipse(glow, shade((255, 150, 60), (i + 1) * 0.022 * flick),
                                    (W / 2 - 500 + i * 30, 40 + i * 12, 1000 - i * 60, 240 - i * 24))
            self.canvas.blit(glow, (0, H - 160), special_flags=pygame.BLEND_RGB_ADD)

    # ------------------------------------------------------------ joyas de vidrio
    def jewel(self, color, r):
        r = int(r)
        key = (color, r, self.light_idx)
        if key in self.jewel_cache:
            return self.jewel_cache[key]
        size = r * 2 + 6
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        col = self.lit(color)
        pygame.draw.polygon(s, LEAD, octagon(c, c, r + 2))
        pygame.draw.polygon(s, col, octagon(c, c, r - 1))
        pygame.draw.polygon(s, mix(col, (255, 255, 255), 0.28), octagon(c - 1, c - 1, r * 0.55))
        pygame.draw.line(s, (255, 255, 255), (c - r * 0.45, c - r * 0.15), (c - r * 0.1, c - r * 0.5), 2)
        if len(self.jewel_cache) > 300:
            self.jewel_cache.clear()
        self.jewel_cache[key] = s
        return s

    def draw_snake(self, points, facing, dead=False):
        cols = self.colors
        body, stripe = cols[0], cols[1]
        if dead:
            body, stripe = shade(body, 0.45), shade(stripe, 0.45)
        total = sum(len(run) for run in points)
        for run in points:                                          # varilla de plomo que une las piezas
            if len(run) > 1:
                pygame.draw.lines(self.canvas, LEAD, False, run, 16)
        idx = 0
        pieces = []
        for run in points:
            for k, (x, y) in enumerate(run):
                i = idx + k
                r = 17 - 5 * i / max(1, total - 1)
                pieces.append((stripe if i % 3 == 2 else body, r, x, y))
            idx += len(run)
        for col, r, x, y in reversed(pieces):
            spr = self.jewel(col, r)
            self.canvas.blit(spr, spr.get_rect(center=(x, y)))

        hx, hy = points[0][0]
        fx, fy = facing
        sx, sy = -fy, fx
        head = self.jewel(shade(GOLD, 0.5) if dead else GOLD, 19)
        self.canvas.blit(head, head.get_rect(center=(hx, hy)))
        for side in (-1, 1):
            ex, ey = hx + fx * 4 + sx * 8 * side, hy + fy * 4 + sy * 8 * side
            pygame.draw.circle(self.canvas, LEAD, (ex, ey), 6)
            if dead:
                pygame.draw.line(self.canvas, (230, 230, 230), (ex - 3, ey - 3), (ex + 3, ey + 3), 2)
                pygame.draw.line(self.canvas, (230, 230, 230), (ex - 3, ey + 3), (ex + 3, ey - 3), 2)
            else:
                pygame.draw.circle(self.canvas, (246, 244, 236), (ex, ey), 4.5)
                pygame.draw.circle(self.canvas, LEAD, (ex + fx * 1.8, ey + fy * 1.8), 2.2)

    def snake_points(self, g):
        return [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]

    def draw_apple(self, cell):
        x, y = cell_center(*cell)
        ruby = self.lit(self.colors[2])
        pulse = 0.5 + 0.5 * math.sin(self.t * 4)
        halo = pygame.Surface((80, 80))
        halo.fill((0, 0, 0))
        for k in range(4):                                          # anillos de fuera hacia dentro
            pygame.draw.circle(halo, shade(ruby, (k + 1) * (0.06 + 0.04 * pulse)), (40, 40), 36 - k * 6)
        self.canvas.blit(halo, (x - 40, y - 40), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(self.canvas, LEAD, (x, y), 14)
        pygame.draw.circle(self.canvas, ruby, (x, y), 11)
        pygame.draw.circle(self.canvas, mix(ruby, (255, 255, 255), 0.3), (x - 2, y - 2), 5)
        for a in (math.pi * 0.5, math.pi * 1.17, math.pi * 1.83):  # plomo que la parte en 3
            pygame.draw.line(self.canvas, LEAD, (x, y), (x + math.cos(a) * 12, y + math.sin(a) * 12), 2)
        leaf = self.lit(self.colors[0])
        pts = [(x + 2, y - 12), (x + 12, y - 19), (x + 8, y - 10)]
        pygame.draw.polygon(self.canvas, leaf, pts)
        pygame.draw.polygon(self.canvas, LEAD, pts, 2)

    def draw_rosette(self, g):
        """Bonus: un rosetón pequeño que gira, con el tiempo restante en un arco dorado."""
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        rot = self.t * 0.8
        cols = self.colors
        R = 22
        pygame.draw.circle(self.canvas, LEAD, (x, y), R + 3)
        for k in range(8):
            a0, a1 = rot + k * math.tau / 8, rot + (k + 1) * math.tau / 8
            pts = [(x, y)] + [(x + math.cos(a0 + (a1 - a0) * t / 4) * R, y + math.sin(a0 + (a1 - a0) * t / 4) * R)
                              for t in range(5)]
            pygame.draw.polygon(self.canvas, self.lit(cols[1] if k % 2 else cols[3]), pts)
            pygame.draw.polygon(self.canvas, LEAD, pts, 2)
        pygame.draw.circle(self.canvas, self.lit(cols[2]), (x, y), 7)
        pygame.draw.circle(self.canvas, LEAD, (x, y), 7, 2)
        frac = g.bonus_left / BONUS_TICKS
        if frac > 0:
            rect = pygame.Rect(0, 0, 2 * R + 16, 2 * R + 16)
            rect.center = (x, y)
            pygame.draw.arc(self.canvas, GOLD, rect, math.pi / 2, math.pi / 2 + math.tau * frac, 4)

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        if kind in ("eat", "bonus"):
            x, y = cell_center(*ev["pos"])
            if kind == "bonus":
                x += CELL / 2
            for i in range(10 if kind == "eat" else 16):          # destellos
                a = random.uniform(0, math.tau)
                v = random.uniform(60, 180)
                self.effects.append(["glint", x, y, math.cos(a) * v, math.sin(a) * v, 0.6, 0.6,
                                     random.choice(self.colors)])
            label = random.choice(POPS) if kind == "eat" else f"+{ev['points']}"
            self.effects.append(["text", x, y - 30, 0, -36, 1.0, 1.0, label])
        elif kind == "die":
            self.shake = 0.45
            self.shatter = True
        elif kind == "stage":
            self.flash = 0.6

    def shatter_snake(self, g):
        """Al morir, cada pieza de la serpiente se rompe en esquirlas que caen."""
        cols = self.colors
        for i, (c, r) in enumerate(g.snake):
            x, y = cell_center(c, r)
            col = GOLD if i == 0 else (cols[1] if i % 3 == 2 else cols[0])
            for k in range(3):
                a = random.uniform(0, math.tau)
                v = random.uniform(40, 200)
                self.effects.append(["shard", x, y, math.cos(a) * v, math.sin(a) * v - 120, 1.4, 1.4,
                                     (col, random.uniform(0, math.tau), random.uniform(-8, 8))])

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for e in self.effects:
            e[1] += e[3] * s
            e[2] += e[4] * s
            if e[0] == "shard":
                e[4] += 600 * s
                col, ang, spin = e[7]
                e[7] = (col, ang + spin * s, spin)
            e[5] -= s
        self.effects = [e for e in self.effects if e[5] > 0]

    def draw_effects(self):
        for kind, x, y, vx, vy, life, life_max, extra in self.effects:
            k = life / life_max
            if kind == "glint":
                L = 7 * k + 2
                col = mix(self.lit(extra), (255, 255, 255), 0.5)
                pygame.draw.line(self.canvas, col, (x - L, y), (x + L, y), 2)
                pygame.draw.line(self.canvas, col, (x, y - L), (x, y + L), 2)
            elif kind == "shard":
                col, ang, _ = extra
                pts = [(x + math.cos(ang + j * 2.3) * 9, y + math.sin(ang + j * 2.3) * 9) for j in range(3)]
                pygame.draw.polygon(self.canvas, self.lit(col), pts)
                pygame.draw.polygon(self.canvas, LEAD, pts, 2)
            else:
                self.text(extra, self.font_mid, GOLD, center=(x, y))

    # ------------------------------------------------------------ texto y paneles
    def text(self, s, font, color, outline=2, **anchor):
        img = font.render(s, True, color)
        rect = img.get_rect(**anchor)
        if outline:
            dark = font.render(s, True, LEAD)
            for dx in (-outline, 0, outline):
                for dy in (-outline, 0, outline):
                    if dx or dy:
                        self.canvas.blit(dark, rect.move(dx, dy))
        self.canvas.blit(img, rect)
        return rect

    def window_panel(self, w, h, cy=None, rosette=True):
        """Panel con forma de ventana gotica; devuelve el rectangulo util (debajo del arco)."""
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 120))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, cy or H // 2)
        rise = w * 0.18
        outer = pygame.Rect(rect.left, rect.top - rise, rect.w, rect.h + rise)
        pts = self.lancet(outer, rise)
        glass = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(glass, (*self.lit((22, 26, 64)), 236), pts)
        self.canvas.blit(glass, (0, 0))
        pygame.draw.polygon(self.canvas, LEAD, pts, 8)
        pygame.draw.polygon(self.canvas, self.lit(GOLD), pts, 2)
        inner = self.lancet(outer.inflate(-22, -22), rise * 0.9)
        pygame.draw.polygon(self.canvas, shade(self.lit(GOLD), 0.7), inner, 1)
        cx, cy2 = outer.centerx, outer.top + rise * 0.75            # rosetita en la punta
        if not rosette:
            return rect
        for k in range(6):
            a = self.t * 0.5 + k * math.tau / 6
            pygame.draw.circle(self.canvas, self.lit(self.colors[k % 2 + 2]),
                               (cx + math.cos(a) * 9, cy2 + math.sin(a) * 9), 5)
        pygame.draw.circle(self.canvas, self.lit(GOLD), (cx, cy2), 5)
        return rect

    @staticmethod
    def lancet(outer, rise, steps=12):
        """Rectangulo con arco apuntado: dos arcos que se juntan en la punta."""
        top = outer.top + rise
        half = outer.w / 2
        rad = (half * half + rise * rise) / (2 * half)               # radio que pasa por la punta
        pts = [(outer.left, outer.bottom), (outer.left, top)]
        for k in range(1, steps + 1):                                # arco izquierdo (centro a la derecha)
            y = top - rise * k / steps
            dx = math.sqrt(max(0.0, rad * rad - (top - y) ** 2))
            pts.append((outer.left + rad - dx, y))
        for k in range(steps - 1, -1, -1):                           # arco derecho (simetrico)
            y = top - rise * k / steps
            dx = math.sqrt(max(0.0, rad * rad - (top - y) ** 2))
            pts.append((outer.right - rad + dx, y))
        pts.append((outer.right, outer.bottom))
        return pts

    def draw_hud(self, g):
        self.text(f"PUNTOS {g.score:04d}", self.font_mid, self.lit(GOLD), midleft=(FX, 50))
        self.text(g.maze["name"], self.font_mid, (240, 236, 224), center=(W // 2, 50))
        if g.bonus:
            r = self.text(str(g.bonus_left), self.font_big, self.lit(GOLD), midright=(W - FX, 50))
            gem = self.jewel(self.colors[3], 12)
            self.canvas.blit(gem, gem.get_rect(midright=(r.left - 10, 52)))
        else:
            self.text(f"MAPA {g.maze_idx} · NIVEL {g.level}", self.font_small, (240, 236, 224),
                      midright=(W - FX, 50))

    def draw_menu(self, app):
        self.canvas.blit(self.menu_background(), (0, 0))
        self.apply_light()
        rect = self.window_panel(600, 404, cy=H // 2 + 46, rosette=False)
        self.text("SNAKE", self.font_title, self.lit(GOLD), outline=4, center=(W // 2, 70))
        n = 11
        pts = [(W // 2 + 150 - k * 30, rect.top + 18 + math.sin(self.t * 3 + k * 0.6) * 8) for k in range(n)]
        self.draw_snake([pts], (1, 0))
        rows = app.menu_rows()
        top = rect.top + 64
        for i, (label, value) in enumerate(rows):
            y = top + i * 38
            sel = i == app.menu_sel
            col = self.lit(GOLD) if sel else (226, 222, 210)
            self.text(label, self.font_mid if sel else self.font_small, col, midleft=(rect.left + 50, y))
            self.text(value, self.font_mid if sel else self.font_small, col, center=(rect.centerx + 120, y))
            if sel:
                for s in (-1, 1):
                    ax = rect.centerx + 120 + s * 130
                    pygame.draw.polygon(self.canvas, col, [(ax + s * 9, y), (ax, y - 8), (ax, y + 8)])
        y_end = top + len(rows) * 38
        self.text(f"RÉCORD {app.game.record}", self.font_small, (226, 222, 210), center=(W // 2, y_end + 6))
        if int(self.t * 2) % 2 == 0:
            self.text("PRESIONA ESPACIO PARA JUGAR", self.font_small, self.lit(GOLD), center=(W // 2, H - 24))

    def draw(self, app):
        self.win_idx, self.light_idx = app.opt(0), app.opt(1)
        g = app.game
        if getattr(self, "shatter", False):
            self.shatter = False
            if g.snake:
                self.shatter_snake(g)

        if g.state == "menu":
            self.draw_menu(app)
        else:
            self.canvas.blit(self.static_layer(g), (0, 0))
            if g.food:
                self.draw_apple(g.food)
            if g.bonus:
                self.draw_rosette(g)
            if g.snake and g.state != "dying":                      # al morir se hizo añicos
                self.draw_snake(self.snake_points(g), g.direction, g.state == "over")
            self.apply_light()
            self.draw_effects()
            self.draw_hud(g)

        if g.state == "pause":
            box = self.window_panel(420, 210)
            self.text("PAUSA", self.font_big, self.lit(GOLD), center=(W // 2, box.top + 40))
            for i, (s, sel) in enumerate(pause_items(app)):
                y = box.top + 112 + i * 48
                self.mark_pause(i, y)
                self.text(s, self.font_mid, self.lit(GOLD) if sel else (200, 196, 186), center=(W // 2, y))
        elif g.state == "stage":
            box = self.window_panel(560, 200)
            self.text("MAPA SUPERADO", self.font_mid, self.lit(GOLD), center=(W // 2, box.top + 34))
            self.text(f"{g.maze_idx}: {g.maze['name']}", self.font_big, (240, 236, 224),
                      center=(W // 2, box.centery + 10))
            self.text(f"PUNTOS {g.score}", self.font_small, self.lit(GOLD), center=(W // 2, box.bottom - 30))
        elif g.state == "over":
            box = self.window_panel(560, 290, cy=H // 2 + 30)
            self.text("FIN DEL JUEGO", self.font_mid, self.lit(GOLD), center=(W // 2, box.top + 30))
            self.text(f"{g.score}", self.font_title, (240, 236, 224), outline=3, center=(W // 2, box.top + 110))
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    self.text("¡NUEVO RÉCORD!", self.font_mid, self.lit(GOLD), center=(W // 2, box.top + 190))
            else:
                self.text(f"RÉCORD {g.record}", self.font_small, (200, 196, 186), center=(W // 2, box.top + 190))
            self.text("ESPACIO: OTRA VEZ    ESC: MENÚ", self.font_small, (226, 222, 210),
                      center=(W // 2, box.bottom - 32))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((*self.light[2], int(190 * self.flash / 0.6)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.45 * 9)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill(LEAD)
        self.screen.blit(self.canvas, (ox, oy))
