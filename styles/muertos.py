"""Estilo DIA DE MUERTOS: papel picado, alebrije con cabeza de calavera, talavera y cempasuchil."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, WIDTH as W, HEIGHT as H, smooth_runs

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "Rye-Regular.ttf"

PINK, ORANGE, YELLOW = (255, 64, 160), (255, 140, 20), (255, 214, 40)
GREEN, TURQ, PURPLE = (60, 200, 100), (40, 196, 220), (150, 80, 225)
FIESTA_COLORS = [PINK, ORANGE, YELLOW, GREEN, TURQ, PURPLE]
INK = (40, 14, 46)
BONE = (250, 244, 232)
COBALT = (30, 64, 168)

AMBIENTES = [
    ("NOCHE", {"bg": ((28, 8, 48), (74, 20, 84)), "board": (44, 16, 62), "text": (255, 222, 120),
               "accent": PINK}),
    ("PANTEON", {"bg": ((6, 18, 30), (20, 52, 64)), "board": (14, 32, 44), "text": (236, 242, 222),
                 "accent": ORANGE}),
    ("FIESTA", {"bg": ((120, 20, 92), (255, 120, 62)), "board": (96, 22, 76), "text": (255, 244, 160),
                "accent": TURQ}),
]
OFRENDAS = ["CEMPASUCHIL", "PAN DE MUERTO", "CALAVERITA"]
GRITOS = ["¡Órale!", "¡Ándale!", "¡Qué rico!", "¡Ajúa!", "¡Sabroso!"]
CALAVERITAS = [   # rimas originales para la pantalla de fin
    ["La víbora muy glotona", "comía sin descansar,", "la Catrina, muy burlona,", "se la vino a llevar."],
    ["Corría y corría la culebra", "presumiendo su velocidad,", "chocó contra una piedra", "y se fue a la eternidad."],
    ["Por comerse una flor", "no miró por dónde andaba,", "la Flaca, con buen humor,", "en el panteón la esperaba."],
]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


class MuertosRenderer(Renderer):
    NAME = "MUERTOS"
    KEY = "muertos"
    OPTIONS = [("AMBIENTE", [a[0] for a in AMBIENTES]), ("OFRENDA", OFRENDAS)]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        self.alpha = pygame.Surface((W, H), pygame.SRCALPHA)
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_title = font(92)
        except Exception:
            def font(size):
                return pygame.font.Font(None, int(size * 1.2))
            self.font_title = font(92)
        self.font_big = font(46)
        self.font_mid = font(30)
        self.font_small = font(22)
        self.font_plain = pygame.font.Font(None, 30)
        self.flags = self.make_flags()
        self.tile = self.make_tile()
        self.bg_cache = {}
        self.th = AMBIENTES[0][1]
        self.amb_idx = 0
        self.ofrenda_idx = 0
        self.t = 0.0
        rnd = random.Random(8)
        self.petals = [[rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(0, math.tau), rnd.uniform(0.6, 1.3)]
                       for _ in range(22)]
        self.particles = []     # [x, y, vx, vy, vida, vida_max, color, forma]
        self.pops = []          # [x, y, texto, vida, vida_max, angulo]
        self.shake = 0.0
        self.flash = 0.0
        self.rhyme = CALAVERITAS[0]

    # ------------------------------------------------------------ piezas pre-dibujadas
    def make_flags(self):
        """Banderitas de papel picado con figuras recortadas (transparentes)."""
        flags = []
        for i in range(16):
            col = FIESTA_COLORS[i % len(FIESTA_COLORS)]
            w, h = 54, 46
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((*col, 235))
            cut = (0, 0, 0, 0)
            for x in range(0, w, 6):                                   # orilla de picos
                pygame.draw.polygon(s, cut, [(x, h), (x + 3, h - 5), (x + 6, h)])
            cx, cy = w // 2, h // 2 - 2
            if i % 2 == 0:                                             # flor
                for a in range(6):
                    ang = a * math.tau / 6
                    pygame.draw.circle(s, cut, (cx + math.cos(ang) * 8, cy + math.sin(ang) * 8), 4)
                pygame.draw.circle(s, cut, (cx, cy), 3)
            else:                                                      # calaverita
                pygame.draw.circle(s, cut, (cx, cy - 2), 10)
                pygame.draw.rect(s, cut, (cx - 6, cy + 5, 12, 6))
                pygame.draw.circle(s, (*col, 235), (cx - 4, cy - 3), 3)
                pygame.draw.circle(s, (*col, 235), (cx + 4, cy - 3), 3)
                pygame.draw.line(s, (*col, 235), (cx - 2, cy + 7), (cx - 2, cy + 11), 1)
                pygame.draw.line(s, (*col, 235), (cx + 2, cy + 7), (cx + 2, cy + 11), 1)
            for dx, dy in ((7, 8), (w - 8, 8), (7, h - 14), (w - 8, h - 14)):   # rombitos
                pygame.draw.polygon(s, cut, [(dx, dy - 3), (dx + 3, dy), (dx, dy + 3), (dx - 3, dy)])
            flags.append(s)
        return flags

    def make_tile(self):
        """Azulejo de talavera de 32x32."""
        t = pygame.Surface((CELL, CELL))
        t.fill(BONE)
        pygame.draw.rect(t, COBALT, (1, 1, CELL - 2, CELL - 2), 2)
        c = CELL // 2
        for a in range(4):
            ang = a * math.pi / 2 + math.pi / 4
            pygame.draw.circle(t, COBALT, (c + math.cos(ang) * 7, c + math.sin(ang) * 7), 4)
        pygame.draw.circle(t, (230, 170, 30), (c, c), 4)
        pygame.draw.circle(t, COBALT, (c, c), 4, 1)
        for x, y in ((4, 4), (CELL - 5, 4), (4, CELL - 5), (CELL - 5, CELL - 5)):
            pygame.draw.circle(t, COBALT, (x, y), 2)
        pygame.draw.rect(t, (120, 100, 90), t.get_rect(), 1)
        return t

    def background(self, border, key):
        ck = (self.amb_idx, key, border)
        if ck in self.bg_cache:
            return self.bg_cache[ck]
        th = self.th
        bg = pygame.Surface((W, H))
        top, bot = th["bg"]
        for y in range(H):
            pygame.draw.line(bg, lerp(top, bot, y / H), (0, y), (W, y))
        rnd = random.Random(5)
        for _ in range(70):                                            # estrellitas
            bg.set_at((rnd.randrange(W), rnd.randrange(H)), lerp(top, (255, 255, 230), rnd.uniform(0.3, 0.8)))
        if self.amb_idx == 1:                                          # luna del panteon
            pygame.draw.circle(bg, (240, 236, 210), (W - 120, 150), 46)
            pygame.draw.circle(bg, lerp(top, bot, 150 / H), (W - 100, 140), 42)
        if key != "menu":
            board = pygame.Rect(FX - 12, FY - 12, FW + 24, FH + 24)
            pygame.draw.rect(bg, th["board"], board, 0, 6)
            for r in range(ROWS):                                      # petalitos sueltos
                for c in range(COLS):
                    if rnd.random() < 0.08:
                        x, y = cell_center(c, r)
                        pygame.draw.ellipse(bg, lerp(th["board"], ORANGE, 0.35),
                                            (x + rnd.uniform(-10, 6), y + rnd.uniform(-10, 6), 6, 4))
            if border:   # borde de sarape: rayas de colores
                for k, col in enumerate((PINK, YELLOW, TURQ, ORANGE)):
                    pygame.draw.rect(bg, col, board.inflate(-k * 6, -k * 6), 3, 6)
            else:        # se atraviesa: hilera de flores de cempasuchil
                for x in range(board.left + 10, board.right, 28):
                    for y in (board.top + 4, board.bottom - 4):
                        pygame.draw.circle(bg, ORANGE, (x, y), 5)
                        pygame.draw.circle(bg, YELLOW, (x, y), 2)
                for y in range(board.top + 30, board.bottom - 10, 28):
                    for x in (board.left + 4, board.right - 4):
                        pygame.draw.circle(bg, ORANGE, (x, y), 5)
                        pygame.draw.circle(bg, YELLOW, (x, y), 2)
        if len(self.bg_cache) > 30:
            self.bg_cache.clear()
        self.bg_cache[ck] = bg
        return bg

    # ------------------------------------------------------------ texto con contorno
    def outlined(self, s, font, color, outline=INK, width=3, angle=0, **anchor):
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

    # ------------------------------------------------------------ calavera de azucar
    def skull(self, cx, cy, s, direction=(0, 0), dead=False):
        c = self.canvas
        dx, dy = direction
        ox, oy = dx * 2 * s, dy * 2 * s
        pygame.draw.circle(c, INK, (cx, cy), 18 * s)
        pygame.draw.circle(c, BONE, (cx, cy - 1 * s), 15.5 * s)
        pygame.draw.rect(c, BONE, (cx - 9 * s, cy + 4 * s, 18 * s, 9 * s), 0, int(4 * s))
        # flor en la frente
        fx, fy = cx + ox * 0.5, cy - 10 * s + oy * 0.5
        for a in range(5):
            ang = a * math.tau / 5 + self.t
            pygame.draw.circle(c, PINK, (fx + math.cos(ang) * 3 * s, fy + math.sin(ang) * 3 * s), 2 * s)
        pygame.draw.circle(c, YELLOW, (fx, fy), 1.5 * s)
        # ojos
        for side, rim in ((-1, TURQ), (1, PINK)):
            ex, ey = cx + side * 6.5 * s + ox, cy - 1 * s + oy
            if dead:
                w = max(2, int(2 * s))
                pygame.draw.line(c, INK, (ex - 3.5 * s, ey - 3.5 * s), (ex + 3.5 * s, ey + 3.5 * s), w)
                pygame.draw.line(c, INK, (ex - 3.5 * s, ey + 3.5 * s), (ex + 3.5 * s, ey - 3.5 * s), w)
            else:
                pygame.draw.circle(c, rim, (ex, ey), 6 * s)
                pygame.draw.circle(c, INK, (ex, ey), 4.5 * s)
                pygame.draw.circle(c, (255, 255, 255), (ex - 1.5 * s, ey - 1.5 * s), 1.4 * s)
        # nariz de corazon invertido
        nx, ny = cx + ox * 0.6, cy + 5 * s + oy * 0.6
        pygame.draw.polygon(c, INK, [(nx - 2.5 * s, ny - 1.5 * s), (nx + 2.5 * s, ny - 1.5 * s), (nx, ny + 2 * s)])
        # boca cosida
        my = cy + 10 * s
        pygame.draw.line(c, INK, (cx - 7 * s, my), (cx + 7 * s, my), max(1, int(1.5 * s)))
        for k in range(-2, 3):
            x = cx + k * 3 * s
            pygame.draw.line(c, INK, (x, my - 2 * s), (x, my + 2 * s), max(1, int(s)))

    # ------------------------------------------------------------ alebrije
    def draw_alebrije(self, runs_px, direction, dead=False):
        pts = [p for run in runs_px for p in run]
        n = len(pts)
        radii = [12 - 4 * i / max(1, n - 1) for i in range(n)]
        for i in range(n - 1, 0, -1):
            pygame.draw.circle(self.canvas, INK, pts[i], radii[i] + 3)
        for run in runs_px:
            for a, b in zip(run, run[1:]):
                pygame.draw.line(self.canvas, INK, a, b, 22)
        for i in range(n - 1, 0, -1):
            col = FIESTA_COLORS[i % len(FIESTA_COLORS)]
            if dead:
                col = lerp(col, (120, 110, 130), 0.75)
            x, y = pts[i]
            pygame.draw.circle(self.canvas, col, (x, y), radii[i])
            accent = FIESTA_COLORS[(i + 3) % len(FIESTA_COLORS)]
            if i % 2:                                       # puntitos
                for a in range(3):
                    ang = a * math.tau / 3 + i
                    pygame.draw.circle(self.canvas, accent,
                                       (x + math.cos(ang) * radii[i] * 0.5, y + math.sin(ang) * radii[i] * 0.5), 2)
            else:                                           # rombo
                r = radii[i] * 0.55
                pygame.draw.polygon(self.canvas, accent, [(x, y - r), (x + r, y), (x, y + r), (x - r, y)])
                pygame.draw.circle(self.canvas, BONE, (x, y), 1.5)
        hx, hy = pts[0]
        self.skull(hx, hy, 1.0, direction, dead)

    # ------------------------------------------------------------ ofrendas y veladora
    def draw_ofrenda(self, cell):
        x, y = cell_center(*cell)
        kind = OFRENDAS[self.ofrenda_idx]
        c = self.canvas
        if kind == "CEMPASUCHIL":
            for a in range(10):
                ang = a * math.tau / 10 + math.sin(self.t * 2) * 0.2
                pygame.draw.circle(c, (230, 110, 10), (x + math.cos(ang) * 9, y + math.sin(ang) * 9), 5)
            pygame.draw.circle(c, ORANGE, (x, y), 9)
            for a in range(7):
                ang = a * math.tau / 7
                pygame.draw.circle(c, (255, 170, 40), (x + math.cos(ang) * 5, y + math.sin(ang) * 5), 3)
            pygame.draw.circle(c, YELLOW, (x, y), 3)
        elif kind == "PAN DE MUERTO":
            pygame.draw.ellipse(c, INK, (x - 14, y - 11, 28, 24))
            pygame.draw.ellipse(c, (206, 134, 62), (x - 12, y - 9, 24, 20))
            bone = (232, 172, 98)
            pygame.draw.line(c, bone, (x - 9, y - 5), (x + 9, y + 5), 4)
            pygame.draw.line(c, bone, (x - 9, y + 5), (x + 9, y - 5), 4)
            pygame.draw.circle(c, bone, (x, y - 1), 4)
            for sx, sy in ((-6, -2), (5, 3), (-3, 5), (6, -4)):
                c.fill((255, 250, 240), (x + sx, y + sy, 1, 1))
        else:
            self.skull(x, y, 0.62)

    def draw_veladora(self, g):
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        frac = g.bonus_left / BONUS_TICKS
        h = 8 + 20 * frac                                   # se derrite con el tiempo
        base = y + 14
        glass = pygame.Rect(x - 11, base - h, 22, h)
        glow_r = 26 + 3 * math.sin(self.t * 9)
        pygame.draw.circle(self.alpha, (255, 190, 80, 60), (x, base - h - 6), glow_r)
        pygame.draw.circle(self.alpha, (255, 220, 120, 70), (x, base - h - 6), glow_r * 0.55)
        pygame.draw.rect(self.canvas, INK, glass.inflate(4, 4), 0, 4)
        pygame.draw.rect(self.canvas, (250, 236, 214), glass, 0, 3)
        pygame.draw.rect(self.canvas, PINK, (glass.left, glass.top + glass.h * 0.35, glass.w, max(3, glass.h * 0.3)))
        flick = math.sin(self.t * 17) * 1.5
        fy = base - h - 2
        pygame.draw.polygon(self.canvas, ORANGE, [(x - 5, fy), (x + flick, fy - 16), (x + 5, fy)])
        pygame.draw.polygon(self.canvas, YELLOW, [(x - 2.5, fy), (x + flick * 0.6, fy - 9), (x + 2.5, fy)])
        pygame.draw.line(self.canvas, INK, (x, fy), (x, fy + 3), 1)

    def draw_walls(self, rects):
        for c, r, w, h in rects:
            for dc in range(w):
                for dr in range(h):
                    self.canvas.blit(self.tile, (FX + (c + dc) * CELL, FY + (r + dr) * CELL))
            pygame.draw.rect(self.canvas, INK, (FX + c * CELL - 1, FY + r * CELL - 1, w * CELL + 2, h * CELL + 2), 2)

    # ------------------------------------------------------------ papel picado y petalos
    def draw_papel_picado(self, y0=4):
        n = len(self.flags)
        step = W / (n - 1)
        pts = [(i * step, y0 + 6 + math.sin(i / (n - 1) * math.pi) * 10) for i in range(n)]
        pygame.draw.lines(self.canvas, (240, 240, 230), False, pts, 2)
        for i, (x, y) in enumerate(pts[:-1]):
            ang = math.sin(self.t * 1.6 + i * 0.7) * 4
            img = pygame.transform.rotozoom(self.flags[i], ang, 1)
            self.canvas.blit(img, img.get_rect(midtop=(x + step / 2, y + 2)))

    def draw_petals(self):
        for x, y, a, k in self.petals:
            w, h = 9 * k, 5 * k
            p = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            pygame.draw.ellipse(p, (255, 150, 30, 210), (1, 1, w, h))
            p = pygame.transform.rotate(p, math.degrees(a))
            self.canvas.blit(p, p.get_rect(center=(x, y)))

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        if kind == "eat":
            x, y = cell_center(*ev["pos"])
            for _ in range(12):
                a = random.uniform(0, math.tau)
                v = random.uniform(60, 170)
                self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v - 50, 0.8, 0.8,
                                       random.choice((ORANGE, YELLOW, (230, 110, 10))), "petal"])
            self.pops = [p for p in self.pops if p[2] not in GRITOS]      # un grito a la vez
            self.pops.append([x, y - 30, random.choice(GRITOS), 1.0, 1.0, random.uniform(-10, 10)])
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = cell_center(c, r)
            x += CELL / 2
            for _ in range(40):                              # cohetes
                a = random.uniform(0, math.tau)
                v = random.uniform(80, 260)
                self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, 1.0, 1.0,
                                       random.choice(FIESTA_COLORS), "spark"])
            self.pops.append([x, y - 36, f"¡Que viva! +{ev['points']}", 1.3, 1.3, 0])
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            self.pops.append([x, y - 36, "¡Ay, nanita!", 1.4, 1.4, random.uniform(-8, 8)])
            self.shake = 0.4
            self.rhyme = random.choice(CALAVERITAS)
        elif kind == "stage":
            self.flash = 0.4
            for _ in range(60):                              # confeti de papel picado
                self.particles.append([random.uniform(0, W), random.uniform(-40, 0), random.uniform(-30, 30),
                                       random.uniform(60, 160), 2.0, 2.0, random.choice(FIESTA_COLORS), "confetti"])

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for p in self.petals:
            p[0] += (20 + 12 * math.sin(self.t + p[2])) * s * p[3]
            p[1] += 30 * s * p[3]
            p[2] += s * 1.5
            if p[1] > H + 10 or p[0] > W + 10:
                p[0], p[1] = random.uniform(-40, W), -10
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            if p[7] != "confetti":
                p[3] += 140 * s
            p[4] -= s
        self.particles = [p for p in self.particles if p[4] > 0]
        for p in self.pops:
            p[1] -= 24 * s
            p[3] -= s
        self.pops = [p for p in self.pops if p[3] > 0]

    def draw_effects(self):
        for x, y, vx, vy, life, life_max, col, shape in self.particles:
            k = life / life_max
            if shape == "petal":
                pygame.draw.ellipse(self.canvas, col, (x - 4, y - 2, 8, 5))
            elif shape == "confetti":
                ang = (x + y) * 0.05
                pts = [(x + math.cos(ang + a) * 5, y + math.sin(ang + a) * 3) for a in (0, 1.6, 3.14, 4.7)]
                pygame.draw.polygon(self.canvas, col, pts)
            else:
                pygame.draw.circle(self.canvas, col, (x, y), max(1, 3 * k))
                pygame.draw.line(self.canvas, col, (x, y), (x - vx * 0.03, y - vy * 0.03), 2)
        for x, y, s, life, life_max, angle in self.pops:
            self.outlined(s, self.font_mid, self.th["text"], width=3, angle=angle, center=(x, y))

    # ------------------------------------------------------------ hud y paneles
    def draw_hud(self, g):
        th = self.th
        self.outlined(f"{g.score:04d}", self.font_mid, th["text"], midleft=(FX, 70))
        self.outlined(g.maze["name"].capitalize(), self.font_small, th["text"], center=(W // 2, 70))
        if g.bonus:
            self.outlined(f"Veladora {g.bonus_left}", self.font_small, YELLOW, midright=(W - FX, 70))
        else:
            self.outlined(f"Mapa {g.maze_idx} · Nivel {g.level}", self.font_small, th["text"], midright=(W - FX, 70))

    def panel(self, w, h, cy=None):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, cy or H // 2)
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 110))
        self.canvas.blit(veil, (0, 0))
        pygame.draw.rect(self.canvas, INK, rect.inflate(8, 8), 0, 10)
        pygame.draw.rect(self.canvas, (60, 22, 76), rect, 0, 8)
        for k, col in enumerate((PINK, YELLOW, TURQ)):                 # sarape
            pygame.draw.rect(self.canvas, col, rect.inflate(-k * 6, -k * 6), 3, 8)
        return rect

    def draw_menu(self, app):
        th = self.th
        # calavera mascota
        self.skull(170, 210, 4.2, (0.2, 0.2))
        self.outlined("Snake", self.font_title, th["text"], width=5, angle=3, center=(W // 2 + 120, 118))
        self.outlined("de Muertos", self.font_big, th["accent"], width=4, angle=3, center=(W // 2 + 150, 182))
        rows = app.menu_rows()
        box = self.panel(540, 34 + len(rows) * 40, cy=H // 2 + 80)
        for i, (label, value) in enumerate(rows):
            y = box.top + 36 + i * 40
            sel = i == app.menu_sel
            col = YELLOW if sel else (230, 214, 236)
            if sel:
                pygame.draw.circle(self.canvas, ORANGE, (box.left + 34, y), 7)
                pygame.draw.circle(self.canvas, YELLOW, (box.left + 34, y), 3)
                self.outlined("<", self.font_small, col, width=2, center=(box.left + 270, y))
                self.outlined(">", self.font_small, col, width=2, center=(box.right - 30, y))
            img = self.font_small.render(label.capitalize(), True, col)
            self.canvas.blit(img, img.get_rect(midleft=(box.left + 54, y)))
            img = self.font_small.render(value.capitalize(), True, col)
            self.canvas.blit(img, img.get_rect(center=(box.left + 390, y)))
        self.outlined(f"Récord {app.game.record}", self.font_small, th["text"], center=(W // 2 - 170, H - 24))
        if int(self.t * 2) % 2 == 0:
            self.outlined("Presiona ESPACIO", self.font_small, th["accent"], center=(W // 2 + 130, H - 24))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.amb_idx, self.ofrenda_idx = app.opt(0), app.opt(1)
        self.th = AMBIENTES[self.amb_idx][1]
        th = self.th
        g = app.game

        if g.state == "menu":
            self.canvas.blit(self.background(True, "menu"), (0, 0))
            self.draw_petals()
            self.draw_papel_picado()
            self.draw_menu(app)
        else:
            self.canvas.blit(self.background(g.maze["border"], g.maze_idx), (0, 0))
            self.draw_walls(g.wall_rects)
            if g.food:
                self.draw_ofrenda(g.food)
            if g.bonus:
                self.draw_veladora(g)
            dead = g.state in ("dying", "over")
            blink = g.state == "dying" and (g.state_time // 120) % 2 == 1
            if g.snake and not blink:
                runs = [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]
                self.draw_alebrije(runs, g.direction, dead)
            self.canvas.blit(self.alpha, (0, 0))
            self.alpha.fill((0, 0, 0, 0))
            self.draw_petals()
            self.draw_papel_picado(-12)
            self.draw_effects()
            self.draw_hud(g)

        if g.state == "pause":
            box = self.panel(400, 230)
            self.outlined("Pausa", self.font_big, th["text"], center=(W // 2, box.top + 54))
            for i, (s, sel) in enumerate(pause_items(app, ["Seguir jugando", "Menú principal"])):
                self.mark_pause(i, box.top + 126 + i * 46)
                self.outlined(s, self.font_mid, YELLOW if sel else th["text"],
                              center=(W // 2, box.top + 126 + i * 46))
        elif g.state == "stage":
            box = self.panel(560, 230)
            self.outlined("¡Ofrenda completa!", self.font_mid, YELLOW, center=(W // 2, box.top + 50))
            self.outlined(f"Mapa {g.maze_idx}: {g.maze['name'].capitalize()}", self.font_big, th["text"],
                          center=(W // 2, box.centery + 4))
            self.outlined(f"Puntos {g.score}", self.font_small, th["text"], center=(W // 2, box.bottom - 40))
        elif g.state == "over":
            box = self.panel(600, 380)
            self.outlined("Calaverita para la víbora", self.font_mid, YELLOW, center=(W // 2, box.top + 42))
            for i, line in enumerate(self.rhyme):
                self.outlined(line, self.font_small, (240, 230, 245), width=2, center=(W // 2, box.top + 92 + i * 32))
            self.outlined(f"Puntos {g.score}", self.font_big, th["text"], center=(W // 2, box.top + 254))
            rec = "¡Nuevo récord!" if g.new_record else f"Récord {g.record}"
            if not g.new_record or int(self.t * 2.5) % 2 == 0:
                self.outlined(rec, self.font_small, th["accent"], center=(W // 2, box.top + 300))
            self.outlined("ESPACIO: otra vez   ESC: menú", self.font_small, (240, 230, 245), width=2,
                          center=(W // 2, box.bottom - 30))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 230, 180, int(160 * self.flash / 0.4)))
            self.canvas.blit(fl, (0, 0))
        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.4 * 9)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill(th["bg"][0])
        self.screen.blit(self.canvas, (ox, oy))
