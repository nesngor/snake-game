"""Estilo ANIME: kawaii en pastel, serpiente chibi con ojos grandes, sakura y textos manga."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, others, tint_mix, WIDTH as W, HEIGHT as H, smooth_runs

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "Chewy-Regular.ttf"

THEMES = [
    ("SAKURA", {"sky": ((255, 206, 226), (255, 242, 248)), "board": (255, 250, 253),
                "dots": (255, 226, 238), "border": (255, 160, 196), "snake": (255, 158, 196),
                "line": (214, 84, 138), "wall": (176, 218, 255), "wall_line": (104, 150, 220),
                "text": (232, 76, 140), "accent": (255, 110, 170), "petal": (255, 182, 210)}),
    ("MENTA", {"sky": ((194, 244, 226), (240, 255, 250)), "board": (246, 255, 252),
               "dots": (214, 246, 234), "border": (112, 208, 176), "snake": (128, 222, 188),
               "line": (52, 156, 124), "wall": (255, 200, 222), "wall_line": (220, 112, 156),
               "text": (36, 150, 118), "accent": (60, 190, 150), "petal": (255, 255, 255)}),
    ("LAVANDA", {"sky": ((222, 206, 255), (246, 240, 255)), "board": (251, 248, 255),
                 "dots": (234, 224, 255), "border": (176, 146, 240), "snake": (192, 164, 255),
                 "line": (116, 84, 204), "wall": (255, 230, 156), "wall_line": (214, 164, 60),
                 "text": (124, 84, 212), "accent": (160, 120, 255), "petal": (255, 220, 250)}),
    ("MELOCOTON", {"sky": ((255, 214, 184), (255, 246, 236)), "board": (255, 251, 246),
                   "dots": (255, 230, 208), "border": (255, 164, 116), "snake": (255, 182, 124),
                   "line": (216, 116, 64), "wall": (176, 224, 176), "wall_line": (84, 160, 100),
                   "text": (230, 108, 56), "accent": (255, 130, 80), "petal": (255, 200, 170)}),
]
FOODS = ["ONIGIRI", "FRESA", "DANGO"]

POPS = ["SUGOI!", "OISHII!", "KAWAII!", "YATTA!", "NYAA~"]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


def heart_points(cx, cy, s):
    pts = []
    for k in range(24):
        t = math.tau * k / 24
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * s / 16, cy + y * s / 16))
    return pts


def star_points(cx, cy, r_out, r_in, rot=0.0):
    pts = []
    for k in range(10):
        a = rot + k * math.pi / 5 - math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


class AnimeRenderer(Renderer):
    NAME = "ANIME"
    KEY = "anime"
    OPTIONS = [("TEMA", [t[0] for t in THEMES]), ("COMIDA", FOODS)]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        self.alpha = pygame.Surface((W, H), pygame.SRCALPHA)   # capa para cosas semitransparentes
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_huge = font(110)
        except Exception:
            def font(size):
                return pygame.font.Font(None, size)
            self.font_huge = font(110)
        self.font_big = font(60)
        self.font_mid = font(40)
        self.font_small = font(30)
        self.bg_cache = {}
        self.th = THEMES[0][1]
        self.theme_idx = 0
        self.food_idx = 0
        self.t = 0.0
        rnd = random.Random(4)
        self.petals = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0, math.tau),
                        rnd.uniform(0.6, 1.2)] for _ in range(26)]
        self.particles = []    # corazones: [x, y, vx, vy, vida, vida_max, tamano]
        self.pops = []         # textos manga: [x, y, texto, vida, vida_max, angulo]
        self.lines_fx = 0.0    # lineas de impacto
        self.lines_dark = False
        self.shake = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------ fondo (cacheado)
    def background(self, maze_border, maze_key):
        key = (self.theme_idx, maze_key, maze_border)
        if key in self.bg_cache:
            return self.bg_cache[key]
        th = self.th
        bg = pygame.Surface((W, H))
        top, bot = th["sky"]
        for y in range(H):
            pygame.draw.line(bg, lerp(top, bot, y / H), (0, y), (W, y))
        if maze_key != "menu":
            board = pygame.Rect(FX - 10, FY - 10, FW + 20, FH + 20)
            pygame.draw.rect(bg, lerp(th["border"], (0, 0, 0), 0.15), board.move(0, 6), 0, 22)
            pygame.draw.rect(bg, th["board"], board, 0, 22)
            for r in range(ROWS):                                # lunares
                for c in range(COLS):
                    if (c + r) % 2 == 0:
                        x, y = cell_center(c, r)
                        pygame.draw.circle(bg, th["dots"], (x, y), 4)
            if maze_border:
                pygame.draw.rect(bg, th["border"], board, 6, 22)
            else:   # se atraviesa: borde de bolitas
                for x in range(board.left + 20, board.right - 10, 26):
                    pygame.draw.circle(bg, th["border"], (x, board.top + 3), 4)
                    pygame.draw.circle(bg, th["border"], (x, board.bottom - 3), 4)
                for y in range(board.top + 20, board.bottom - 10, 26):
                    pygame.draw.circle(bg, th["border"], (board.left + 3, y), 4)
                    pygame.draw.circle(bg, th["border"], (board.right - 3, y), 4)
        if len(self.bg_cache) > 30:
            self.bg_cache.clear()
        self.bg_cache[key] = bg
        return bg

    # ------------------------------------------------------------ texto manga con borde
    def outlined_text(self, s, font, color, outline=(255, 255, 255), width=3, angle=0, **anchor):
        base = font.render(s, True, color)
        edge = font.render(s, True, outline)
        w, h = base.get_size()
        surf = pygame.Surface((w + width * 2, h + width * 2), pygame.SRCALPHA)
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if dx * dx + dy * dy <= width * width:
                    surf.blit(edge, (dx + width, dy + width))
        surf.blit(base, (width, width))
        if angle:
            surf = pygame.transform.rotozoom(surf, angle, 1)
        rect = surf.get_rect(**anchor)
        self.canvas.blit(surf, rect)
        return rect

    # ------------------------------------------------------------ cara chibi
    def face(self, cx, cy, s, direction=(0, 0), dead=False, blink=False):
        """Ojos grandes con brillos, cachetes y boquita. s = escala (1 = cabeza de juego)."""
        surf = self.canvas
        dx, dy = direction
        ox, oy = dx * 3 * s, dy * 2 * s
        eye_dark = (70, 44, 86)
        for side in (-1, 1):
            ex, ey = cx + side * 7 * s + ox, cy - 2 * s + oy
            if dead:   # ojos > <
                tip, back = ex - side * 3 * s, ex + side * 4 * s
                pygame.draw.lines(surf, eye_dark, False,
                                  [(back, ey - 4 * s), (tip, ey), (back, ey + 4 * s)], max(2, int(2 * s)))
            elif blink:
                pygame.draw.arc(surf, eye_dark, (ex - 5 * s, ey - 3 * s, 10 * s, 7 * s),
                                0.2, math.pi - 0.2, max(2, int(2 * s)))
            else:
                rect = pygame.Rect(0, 0, 9 * s, 12 * s)
                rect.center = (ex, ey)
                pygame.draw.ellipse(surf, eye_dark, rect)
                low = rect.inflate(-3 * s, -6 * s).move(0, 3 * s)
                pygame.draw.ellipse(surf, lerp(eye_dark, self.th["accent"], 0.55), low)
                pygame.draw.circle(surf, (255, 255, 255), (ex - 1.8 * s, ey - 2.8 * s), 2.4 * s)
                pygame.draw.circle(surf, (255, 255, 255), (ex + 2 * s, ey + 2.5 * s), 1.2 * s)
        # cachetes
        blush = (255, 140, 170, 120)
        for side in (-1, 1):
            r = pygame.Rect(0, 0, 8 * s, 4 * s)
            r.center = (cx + side * 11 * s + ox * 0.5, cy + 5 * s + oy * 0.5)
            pygame.draw.ellipse(self.alpha, blush, r)
        # boca
        mx, my = cx + ox * 0.6, cy + 5 * s + oy * 0.6
        if dead:
            pygame.draw.circle(surf, eye_dark, (mx, my + 1 * s), 2.5 * s, max(1, int(1.5 * s)))
        else:
            w = max(1, int(1.5 * s))
            pygame.draw.arc(surf, eye_dark, (mx - 4 * s, my - 2 * s, 4 * s, 4 * s), math.pi, math.tau, w)
            pygame.draw.arc(surf, eye_dark, (mx, my - 2 * s, 4 * s, 4 * s), math.pi, math.tau, w)

    def flush_alpha(self):
        self.canvas.blit(self.alpha, (0, 0))
        self.alpha.fill((0, 0, 0, 0))

    # ------------------------------------------------------------ serpiente
    def draw_snake(self, runs_px, direction, dead=False, tint=None):
        th = self.th
        base = tint or th["snake"]
        body = lerp(base, (200, 200, 210), 0.6) if dead else base
        line = th["line"]
        pts = [p for run in runs_px for p in run]
        n = len(pts)
        radii = [13 - 4 * i / max(1, n - 1) for i in range(n)]
        radii[0] = 20
        for i in range(n - 1, -1, -1):                       # contorno
            pygame.draw.circle(self.canvas, line, pts[i], radii[i] + 3)
        for run in runs_px:                                   # rellenar huecos entre bolitas
            for a, b in zip(run, run[1:]):
                pygame.draw.line(self.canvas, line, a, b, 20)
        for run in runs_px:
            for a, b in zip(run, run[1:]):
                pygame.draw.line(self.canvas, body, a, b, 14)
        for i in range(n - 1, -1, -1):
            pygame.draw.circle(self.canvas, body, pts[i], radii[i])
            if i > 0 and i % 3 == 0:                          # manchitas
                pygame.draw.circle(self.canvas, lerp(body, (255, 255, 255), 0.45), pts[i], radii[i] * 0.4)
            x, y = pts[i]                                     # brillo
            shine = pygame.Rect(0, 0, radii[i] * 0.8, radii[i] * 0.45)
            shine.center = (x - radii[i] * 0.35, y - radii[i] * 0.45)
            pygame.draw.ellipse(self.canvas, lerp(body, (255, 255, 255), 0.7), shine)
        blink = (self.t % 3.2) < 0.13
        hx, hy = pts[0]
        self.face(hx, hy, 1.15, direction, dead=dead, blink=blink and not dead)

    # ------------------------------------------------------------ comida y bonus
    def draw_food(self, cell):
        x, y = cell_center(*cell)
        y += math.sin(self.t * 4) * 2
        kind = FOODS[self.food_idx]
        line = (70, 50, 60)
        if kind == "ONIGIRI":
            pts = [(x, y - 13), (x + 13, y + 10), (x - 13, y + 10)]
            pygame.draw.polygon(self.canvas, line, pts, 0)
            inner = [(x, y - 9), (x + 9.5, y + 8), (x - 9.5, y + 8)]
            pygame.draw.polygon(self.canvas, (255, 255, 255), inner)
            for p in pts:
                pygame.draw.circle(self.canvas, line, p, 3)
            pygame.draw.rect(self.canvas, (40, 60, 50), (x - 6, y + 2, 12, 9), 0, 2)
            self.face(x, y - 2, 0.45)
        elif kind == "FRESA":
            pygame.draw.polygon(self.canvas, line, heart_points(x, y + 1, 15))
            pygame.draw.polygon(self.canvas, (240, 70, 90), heart_points(x, y + 1, 12))
            for sx, sy in ((-5, 0), (4, -2), (0, 5), (-2, -5), (6, 4)):
                pygame.draw.circle(self.canvas, (255, 230, 150), (x + sx, y + sy + 3), 1)
            for a in (-0.7, 0, 0.7):
                pygame.draw.line(self.canvas, (80, 180, 90), (x, y - 9),
                                 (x + math.sin(a) * 8, y - 9 - math.cos(a) * 6), 4)
            self.face(x, y + 2, 0.4)
        else:   # DANGO
            pygame.draw.line(self.canvas, (190, 140, 90), (x - 12, y + 13), (x + 12, y - 13), 3)
            for k, col in enumerate(((255, 170, 200), (255, 255, 250), (160, 220, 140))):
                bx, by = x - 7 + k * 7, y + 7 - k * 7
                pygame.draw.circle(self.canvas, line, (bx, by), 8)
                pygame.draw.circle(self.canvas, col, (bx, by), 6)
            self.face(x, y, 0.35)

    def draw_star(self, g):
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        y += math.sin(self.t * 3) * 3
        rot = math.sin(self.t * 2) * 0.15
        pygame.draw.polygon(self.canvas, (220, 150, 30), star_points(x, y, 22, 11, rot))
        pygame.draw.polygon(self.canvas, (255, 220, 70), star_points(x, y, 18, 9, rot))
        self.face(x, y + 2, 0.55)
        # corazoncitos alrededor = tiempo restante
        left = math.ceil(8 * g.bonus_left / BONUS_TICKS)
        for k in range(left):
            a = -math.pi / 2 + k * math.tau / 8 + self.t
            pygame.draw.polygon(self.canvas, self.th["accent"],
                                heart_points(x + math.cos(a) * 32, y + math.sin(a) * 32, 5))
        if int(self.t * 4) % 2 == 0:                          # destellos
            for sx, sy in ((-26, -18), (24, -22)):
                pygame.draw.polygon(self.canvas, (255, 255, 255), star_points(x + sx, y + sy, 6, 2))

    def draw_walls(self, rects):
        th = self.th
        for c, r, w, h in rects:
            rect = pygame.Rect(FX + c * CELL + 3, FY + r * CELL + 3, w * CELL - 6, h * CELL - 6)
            pygame.draw.rect(self.canvas, th["wall_line"], rect.move(0, 4), 0, 9)
            pygame.draw.rect(self.canvas, th["wall"], rect, 0, 9)
            self.canvas.set_clip(rect.inflate(-6, -6))           # rayas de caramelo
            for off in range(-rect.h, rect.w, 14):
                pygame.draw.line(self.canvas, lerp(th["wall"], (255, 255, 255), 0.6),
                                 (rect.left + off, rect.bottom), (rect.left + off + rect.h, rect.top), 5)
            self.canvas.set_clip(None)
            pygame.draw.rect(self.canvas, th["wall_line"], rect, 3, 9)
            hl = pygame.Rect(rect.left + 6, rect.top + 4, max(4, rect.w - 12), 4)
            pygame.draw.rect(self.canvas, (255, 255, 255), hl, 0, 2)

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        if kind == "eat":
            x, y = cell_center(*ev["pos"])
            self.hearts(x, y, 8)
            self.pops.append([x, y - 30, random.choice(POPS), 0.9, 0.9, random.uniform(-12, 12)])
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = cell_center(c, r)
            self.hearts(x + CELL / 2, y, 18)
            self.pops.append([x + CELL / 2, y - 36, f"+{ev['points']}!", 1.2, 1.2, 0])
            self.lines_fx, self.lines_dark = 0.5, False
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            self.pops.append([x, y - 36, "NOOO~!", 1.3, 1.3, random.uniform(-10, 10)])
            self.lines_fx, self.lines_dark = 0.7, True
            self.shake = 0.4
        elif kind == "stage":
            self.flash = 0.5
            self.lines_fx, self.lines_dark = 0.6, False

    def hearts(self, x, y, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(60, 180)
            life = random.uniform(0.5, 0.9)
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v - 60, life, life,
                                   random.uniform(5, 9)])

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        self.lines_fx = max(0.0, self.lines_fx - s)
        for p in self.petals:                     # sakura cayendo
            p[0] += (25 + 15 * math.sin(self.t + p[2])) * s * p[3]
            p[1] += 35 * s * p[3]
            p[2] += s * 2
            if p[1] > H + 10 or p[0] > W + 10:
                p[0], p[1] = random.uniform(-40, W), -10
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            p[3] += 120 * s
            p[4] -= s
        self.particles = [p for p in self.particles if p[4] > 0]
        for p in self.pops:
            p[1] -= 25 * s
            p[3] -= s
        self.pops = [p for p in self.pops if p[3] > 0]

    def draw_petals(self):
        col = (*self.th["petal"], 200)
        for x, y, a, k in self.petals:
            w, h = 10 * k, 6 * k
            petal = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            pygame.draw.ellipse(petal, col, (1, 1, w, h))
            petal = pygame.transform.rotate(petal, math.degrees(a))
            self.canvas.blit(petal, petal.get_rect(center=(x, y)))

    def draw_effects(self):
        for x, y, _, _, life, life_max, size in self.particles:
            s = size * (0.5 + life / life_max)
            pygame.draw.polygon(self.canvas, self.th["accent"], heart_points(x, y, s))
        for x, y, s, life, life_max, angle in self.pops:
            grow = min(1.0, (life_max - life) * 8)               # aparece con rebote
            font = self.font_big if grow >= 1 else self.font_mid
            self.outlined_text(s, font, self.th["text"], width=4, angle=angle, center=(x, y))

    def draw_speed_lines(self):
        if self.lines_fx <= 0:
            return
        k = min(1.0, self.lines_fx * 2)
        col = (40, 30, 50, int(150 * k)) if self.lines_dark else (255, 255, 255, int(200 * k))
        rnd = random.Random(int(self.t * 20))
        cx, cy = W / 2, H / 2
        for _ in range(46):
            a = rnd.uniform(0, math.tau)
            r_out = 700
            r_in = rnd.uniform(240, 340)
            spread = rnd.uniform(0.008, 0.02)
            pts = [(cx + math.cos(a - spread) * r_out, cy + math.sin(a - spread) * r_out),
                   (cx + math.cos(a + spread) * r_out, cy + math.sin(a + spread) * r_out),
                   (cx + math.cos(a) * r_in, cy + math.sin(a) * r_in)]
            pygame.draw.polygon(self.alpha, col, pts)
        self.flush_alpha()

    # ------------------------------------------------------------ hud y paneles
    def draw_hud(self, g):
        th = self.th
        self.outlined_text(f"{g.score:04d}", self.font_big, th["text"], width=4, midleft=(FX, 46))
        self.outlined_text(g.maze["name"], self.font_mid, th["text"], width=3, center=(W // 2, 46))
        if g.bonus:
            x = W - FX - 110
            pygame.draw.polygon(self.canvas, (220, 150, 30), star_points(x, 46, 18, 9))
            pygame.draw.polygon(self.canvas, (255, 220, 70), star_points(x, 46, 14, 7))
            self.outlined_text(f"{g.bonus_left:02d}", self.font_big, (240, 160, 30), width=4,
                               midleft=(x + 26, 46))
        else:
            self.outlined_text(f"MAPA {g.maze_idx}  NIVEL {g.level}", self.font_small, th["text"],
                               width=3, midright=(W - FX, 46))

    def panel(self, w, h, cy=None):
        th = self.th
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, cy or H // 2)
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((*th["sky"][0], 120))
        self.canvas.blit(veil, (0, 0))
        pygame.draw.rect(self.canvas, th["border"], rect.move(0, 8), 0, 30)
        pygame.draw.rect(self.canvas, (255, 255, 255), rect, 0, 30)
        pygame.draw.rect(self.canvas, th["border"], rect, 6, 30)
        for sx, sy in ((rect.left + 8, rect.top + 8), (rect.right - 8, rect.top + 8)):
            pygame.draw.polygon(self.canvas, (255, 220, 70), star_points(sx, sy, 16, 7))
        pygame.draw.polygon(self.canvas, th["accent"], heart_points(rect.centerx, rect.bottom, 14))
        return rect

    def draw_menu(self, app):
        th = self.th
        self.canvas.blit(self.background(True, "menu"), (0, 0))
        self.draw_petals()
        # mascota: cabeza grande que parpadea
        mx, my = 170, 150
        pygame.draw.circle(self.canvas, th["line"], (mx, my), 74)
        pygame.draw.circle(self.canvas, th["snake"], (mx, my), 68)
        pygame.draw.ellipse(self.canvas, lerp(th["snake"], (255, 255, 255), 0.7), (mx - 48, my - 50, 40, 22))
        self.face(mx, my + 4, 4.2, (0.3, 0.2), blink=(self.t % 3.2) < 0.15)
        self.flush_alpha()
        title = self.outlined_text("Snake-chan", self.font_huge, th["text"], width=6, angle=4,
                                   center=(W // 2 + 110, 92))
        for sx, sy, s in ((title.right - 10, title.top + 10, 16), (title.left + 20, title.bottom - 6, 11)):
            pygame.draw.polygon(self.canvas, (255, 220, 70), star_points(sx, sy, s, s * 0.4, self.t))

        rows = app.menu_rows()
        box = self.panel(520, 40 + len(rows) * 42, cy=H // 2 + 76)
        for i, (label, value) in enumerate(rows):
            y = box.top + 40 + i * 42
            sel = i == app.menu_sel
            if sel:
                bar = pygame.Rect(box.left + 22, y - 20, box.w - 44, 40)
                pygame.draw.rect(self.canvas, lerp((255, 255, 255), th["accent"], 0.2), bar, 0, 20)
                pygame.draw.polygon(self.canvas, th["accent"], heart_points(box.left + 42, y, 9))
                self.outlined_text("<", self.font_mid, th["accent"], width=2, center=(box.left + 262, y))
                self.outlined_text(">", self.font_mid, th["accent"], width=2, center=(box.right - 40, y))
            color = th["text"] if sel else lerp(th["text"], (120, 110, 130), 0.5)
            self.canvas.blit(self.font_mid.render(label, True, color),
                             self.font_mid.render(label, True, color).get_rect(midleft=(box.left + 62, y)))
            img = self.font_mid.render(value, True, color)
            self.canvas.blit(img, img.get_rect(center=(box.left + 380, y)))
        self.outlined_text(f"RECORD {app.game.record:04d}", self.font_small, th["text"], width=3,
                           center=(W - 120, H - 26))
        if int(self.t * 2) % 2 == 0:
            self.outlined_text("ESPACIO PARA JUGAR!", self.font_mid, th["accent"], width=4,
                               center=(W // 2 - 60, H - 26))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.theme_idx, self.food_idx = app.opt(0), app.opt(1)
        self.th = THEMES[self.theme_idx][1]
        th = self.th
        g = app.game

        if g.state == "menu":
            self.draw_menu(app)
        else:
            self.canvas.blit(self.background(g.maze["border"], g.maze_idx), (0, 0))
            self.draw_walls(g.wall_rects)
            if g.food:
                self.draw_food(g.food)
            if g.bonus:
                self.draw_star(g)
            dead = g.state in ("dying", "over")
            blink = g.state == "dying" and (g.state_time // 120) % 2 == 1
            for o in others(g):                                # rivales (modo en linea)
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(o)]
                self.draw_snake(runs, o.direction, o.dead, o.tint)
            if g.snake and not blink:
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]
                self.draw_snake(runs, g.direction, dead)
            self.flush_alpha()
            self.draw_petals()
            self.draw_effects()
            self.draw_hud(g)
            self.draw_speed_lines()

        if g.state == "pause":
            box = self.panel(440, 260)
            self.outlined_text("PAUSA~", self.font_big, th["text"], width=4, center=(W // 2, box.top + 62))
            for i, (s, sel) in enumerate(pause_items(app)):
                self.mark_pause(i, box.top + 140 + i * 52)
                self.outlined_text(s, self.font_mid, th["accent"] if sel else (150, 140, 170), width=3,
                                   center=(W // 2, box.top + 140 + i * 52))
        elif g.state == "stage":
            box = self.panel(540, 250)
            self.outlined_text("SUGOI!! MAPA SUPERADO", self.font_mid, th["accent"], width=3,
                               center=(W // 2, box.top + 56))
            self.outlined_text(f"MAPA {g.maze_idx}: {g.maze['name']}", self.font_big, th["text"],
                               width=4, center=(W // 2, box.centery + 6))
            self.outlined_text(f"PUNTOS {g.score:04d}", self.font_small, th["text"], width=3,
                               center=(W // 2, box.bottom - 46))
        elif g.state == "over":
            box = self.panel(540, 320)
            self.outlined_text("GAME OVER... (>_<)", self.font_mid, th["accent"], width=3,
                               center=(W // 2, box.top + 50))
            self.outlined_text(f"{g.score:04d}", self.font_huge, th["text"], width=6,
                               center=(W // 2, box.top + 130))
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    self.outlined_text("NUEVO RECORD!! \\(^o^)/", self.font_mid, (240, 160, 30),
                                       width=3, center=(W // 2, box.top + 206))
            else:
                self.outlined_text(f"RECORD {g.record:04d}", self.font_small, th["text"], width=3,
                                   center=(W // 2, box.top + 206))
            self.outlined_text("ESPACIO: OTRA VEZ    ESC: MENU", self.font_small, th["text"], width=3,
                               center=(W // 2, box.bottom - 44))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(190 * self.flash / 0.5)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.4 * 9)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill(th["sky"][0])
        self.screen.blit(self.canvas, (ox, oy))
