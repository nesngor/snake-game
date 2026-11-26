"""Estilo PAPEL: todo dibujado a mano sobre una hoja (o pizarra), con trazos que 'hierven'."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS, RIGHT
from styles.base import Renderer, pause_items, WIDTH as W, HEIGHT as H

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
BOIL_FPS = 8                    # cuantas veces por segundo "tiembla" el dibujo
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "PatrickHand-Regular.ttf"

SHEETS = [
    ("CUADROS", {"paper": (250, 248, 240), "grid": (176, 204, 236), "kind": "grid"}),
    ("RAYAS", {"paper": (252, 250, 243), "grid": (170, 196, 232), "kind": "lines"}),
    ("KRAFT", {"paper": (206, 172, 124), "grid": None, "kind": "kraft"}),
    ("PIZARRA", {"paper": (42, 64, 54), "grid": None, "kind": "chalk"}),
]
INKS = ["LAPIZ", "AZUL", "COLORES"]

PAPER_INKS = {
    "LAPIZ": {"ink": (64, 64, 72), "snake": (196, 196, 202), "apple": (150, 150, 156),
              "star": (180, 180, 186), "wall": (110, 110, 118), "accent": (64, 64, 72)},
    "AZUL": {"ink": (28, 58, 160), "snake": (172, 192, 240), "apple": (120, 150, 222),
             "star": (150, 176, 236), "wall": (60, 90, 190), "accent": (206, 46, 46)},
    "COLORES": {"ink": (50, 50, 58), "snake": (110, 200, 90), "apple": (230, 60, 60),
                "star": (250, 200, 40), "wall": (170, 110, 60), "accent": (226, 56, 56)},
}
CHALK_INKS = {
    "LAPIZ": {"ink": (236, 236, 228), "snake": (120, 140, 130), "apple": (170, 180, 175),
              "star": (200, 205, 200), "wall": (200, 205, 200), "accent": (236, 236, 228)},
    "AZUL": {"ink": (160, 206, 255), "snake": (80, 120, 140), "apple": (130, 170, 230),
             "star": (150, 190, 240), "wall": (150, 196, 250), "accent": (255, 150, 150)},
    "COLORES": {"ink": (238, 238, 230), "snake": (120, 200, 130), "apple": (255, 130, 130),
                "star": (255, 232, 130), "wall": (232, 190, 150), "accent": (255, 150, 150)},
}

POPS = ["¡Ñam!", "¡Ñom!", "¡Rico!", "¡Yum!"]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


# ---------------------------------------------------------------- trazos a mano
def wobble(p1, p2, rnd, amp=1.4, step=14):
    (x1, y1), (x2, y2) = p1, p2
    length = math.hypot(x2 - x1, y2 - y1) or 1
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length
    n = max(1, int(length / step))
    pts = []
    for k in range(n + 1):
        t = k / n
        a = rnd.uniform(-amp, amp) * (0.4 if k in (0, n) else 1)
        pts.append((x1 + (x2 - x1) * t + nx * a, y1 + (y2 - y1) * t + ny * a))
    return pts


def stroke(surf, color, p1, p2, rnd, width=2, overshoot=0):
    if overshoot:
        (x1, y1), (x2, y2) = p1, p2
        length = math.hypot(x2 - x1, y2 - y1) or 1
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        o1, o2 = rnd.uniform(0, overshoot), rnd.uniform(0, overshoot)
        p1, p2 = (x1 - ux * o1, y1 - uy * o1), (x2 + ux * o2, y2 + uy * o2)
    pygame.draw.lines(surf, color, False, wobble(p1, p2, rnd), width)
    if width <= 3:   # segunda pasada fina: textura de lapiz
        off = rnd.uniform(-0.9, 0.9)
        pygame.draw.lines(surf, color, False,
                          [(x + off, y - off) for x, y in wobble(p1, p2, rnd, amp=1)], 1)


def sketch_rect(surf, color, rect, rnd, width=2):
    r = pygame.Rect(rect)
    corners = [r.topleft, r.topright, r.bottomright, r.bottomleft]
    for i in range(4):
        stroke(surf, color, corners[i], corners[(i + 1) % 4], rnd, width, overshoot=5)


def circle_points(c, r, rnd, turns=1.0, n=20, wob=0.06):
    start = rnd.uniform(0, math.tau)
    k1, k2 = rnd.uniform(-wob, wob), rnd.uniform(-wob, wob)
    pts = []
    steps = int(n * turns)
    for i in range(steps + 1):
        a = start + math.tau * turns * i / steps
        rr = r * (1 + k1 * math.sin(a * 2) + k2 * math.cos(a * 3))
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    return pts


def sketch_circle(surf, color, c, r, rnd, width=2, turns=1.1):
    pygame.draw.lines(surf, color, False, circle_points(c, r, rnd, turns), width)


def sketch_ellipse(surf, color, rect, rnd, width=2):
    r = pygame.Rect(rect)
    pts = [(r.centerx + x * r.w / 2 / 10, r.centery + y * r.h / 2 / 10)
           for x, y in circle_points((0, 0), 10, rnd, turns=1.12, wob=0.08)]
    pygame.draw.lines(surf, color, False, pts, width)


def hatch(surf, color, rect, rnd, spacing=8, width=1):
    r = pygame.Rect(rect)
    surf.set_clip(r)
    for off in range(-r.h, r.w + spacing, spacing):
        o = off + rnd.uniform(-1.5, 1.5)
        stroke(surf, color, (r.left + o, r.bottom), (r.left + o + r.h, r.top), rnd, width)
    surf.set_clip(None)


def scribble_circle(surf, color, c, r, rnd, width=2):
    pts = []
    y = -r + 2
    side = 1
    while y < r - 1:
        x = math.sqrt(max(0, r * r - y * y)) * 0.92
        pts.append((c[0] + side * x + rnd.uniform(-1, 1), c[1] + y))
        side = -side
        y += 3.2
    if len(pts) > 1:
        pygame.draw.lines(surf, color, False, pts, width)


def star_points(cx, cy, r_out, r_in, rot):
    pts = []
    for k in range(10):
        a = rot + k * math.pi / 5 - math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


class PaperRenderer(Renderer):
    NAME = "PAPEL"
    KEY = "papel"
    OPTIONS = [("HOJA", [s[0] for s in SHEETS]), ("TINTA", INKS)]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_huge = font(130)
        except Exception:
            def font(size):
                return pygame.font.Font(None, int(size * 0.9))
            self.font_huge = font(130)
        self.font_big = font(64)
        self.font_mid = font(42)
        self.font_small = font(32)
        self.paper_cache = {}
        self.static_cache = {}
        self.t = 0.0
        self.effects = []      # [tipo, x, y, vida, vida_max, extra]
        self.shake = 0.0
        self.flash = 0.0
        self.sheet_idx = 0
        self.ink_idx = 0
        self.pal = PAPER_INKS["LAPIZ"]

    @property
    def sheet(self):
        return SHEETS[self.sheet_idx][1]

    def rnd(self, salt):
        return random.Random(int(self.t * BOIL_FPS) * 7919 + salt)

    # ------------------------------------------------------------ hoja (cacheada)
    def paper(self):
        idx = self.sheet_idx
        if idx in self.paper_cache:
            return self.paper_cache[idx]
        sh = self.sheet
        surf = pygame.Surface((W, H))
        surf.fill(sh["paper"])
        rnd = random.Random(11)
        dark = sh["kind"] in ("chalk",)
        for _ in range(3500):                               # textura
            x, y = rnd.randrange(W), rnd.randrange(H)
            k = rnd.uniform(0.9, 1.08) if not dark else rnd.uniform(0.85, 1.25)
            surf.set_at((x, y), tuple(min(255, int(v * k)) for v in sh["paper"]))
        if sh["kind"] == "grid":
            for x in range(FX % CELL, W, CELL):
                pygame.draw.line(surf, sh["grid"], (x, 0), (x, H))
            for y in range(FY % CELL, H, CELL):
                pygame.draw.line(surf, sh["grid"], (0, y), (W, y))
        elif sh["kind"] == "lines":
            for y in range(FY % CELL, H, CELL):
                pygame.draw.line(surf, sh["grid"], (0, y), (W, y))
        if sh["kind"] in ("grid", "lines"):
            pygame.draw.line(surf, (234, 130, 130), (18, 0), (18, H), 2)     # margen
            for x in range(40, W, 46):                                       # espiral
                pygame.draw.ellipse(surf, lerp(sh["paper"], (0, 0, 0), 0.35), (x, 10, 12, 12))
                pygame.draw.arc(surf, (150, 150, 160), (x - 2, -10, 16, 28), 0, math.pi, 3)
        elif sh["kind"] == "kraft":
            for _ in range(400):
                x, y = rnd.randrange(W), rnd.randrange(H)
                pygame.draw.line(surf, lerp(sh["paper"], (120, 90, 50), 0.3),
                                 (x, y), (x + rnd.randint(2, 6), y + rnd.randint(-1, 1)))
        elif sh["kind"] == "chalk":
            for _ in range(14):                                  # manchas de gis borrado
                x, y = rnd.randrange(W), rnd.randrange(H)
                blot = pygame.Surface((160, 60), pygame.SRCALPHA)
                pygame.draw.ellipse(blot, (255, 255, 255, 5), blot.get_rect())
                surf.blit(blot, (x - 80, y - 30))
            pygame.draw.rect(surf, (128, 86, 48), surf.get_rect(), 12)       # marco de madera
            pygame.draw.rect(surf, (96, 62, 34), surf.get_rect(), 3)
        self.paper_cache[idx] = surf
        return surf

    def static_layer(self, maze, maze_key, rects=None):
        """Hoja + muros + borde. Se guardan 3 versiones para que 'hiervan'."""
        variant = int(self.t * BOIL_FPS) % 3
        key = (self.sheet_idx, self.ink_idx, maze_key, variant)
        if key in self.static_cache:
            return self.static_cache[key]
        pal = self.pal
        surf = self.paper().copy()
        rnd = random.Random(variant * 31 + 5)
        field = pygame.Rect(FX - 6, FY - 6, FW + 12, FH + 12)
        if maze["border"]:
            sketch_rect(surf, pal["ink"], field, rnd, 3)
            sketch_rect(surf, pal["ink"], field.inflate(-7, -7), rnd, 1)
        else:   # se atraviesa: borde punteado
            for x in range(field.left, field.right - 10, 22):
                stroke(surf, pal["ink"], (x, field.top), (x + 11, field.top), rnd, 2)
                stroke(surf, pal["ink"], (x, field.bottom), (x + 11, field.bottom), rnd, 2)
            for y in range(field.top, field.bottom - 10, 22):
                stroke(surf, pal["ink"], (field.left, y), (field.left, y + 11), rnd, 2)
                stroke(surf, pal["ink"], (field.right, y), (field.right, y + 11), rnd, 2)
        tint = lerp(self.sheet["paper"], pal["wall"], 0.22)
        for c, r, w, h in (rects if rects is not None else maze["walls"]):
            rect = pygame.Rect(FX + c * CELL + 3, FY + r * CELL + 3, w * CELL - 6, h * CELL - 6)
            surf.fill(tint, rect)
            hatch(surf, pal["wall"], rect, rnd, spacing=8, width=2)
            sketch_rect(surf, pal["ink"], rect, rnd, 3)
        if len(self.static_cache) > 60:
            self.static_cache.clear()
        self.static_cache[key] = surf
        return surf

    # ------------------------------------------------------------ serpiente
    def draw_snake(self, runs, facing, dead=False):
        """runs: listas de puntos (cabeza primero) separadas donde cruza el borde."""
        pal = self.pal
        rnd = self.rnd(3)
        surf = self.canvas
        total = sum(len(r) for r in runs)
        fill = self.sheet["paper"] if dead else pal["snake"]
        idx = 0
        layers = []
        for run in runs:
            pts = [(x + rnd.uniform(-1, 1), y + rnd.uniform(-1, 1)) for x, y in run]
            widths = [24 - 10 * (idx + k) / max(1, total - 1) for k in range(len(pts))]
            layers.append((pts, widths, idx))
            idx += len(pts)
        for extra, color in ((5, pal["ink"]), (0, fill)):      # contorno y relleno
            for pts, widths, _ in layers:
                for k, (x, y) in enumerate(pts):
                    w = widths[k] + extra
                    pygame.draw.circle(surf, color, (x, y), w / 2)
                    if k + 1 < len(pts):
                        w2 = min(w, widths[k + 1] + extra)
                        pygame.draw.line(surf, color, (x, y), pts[k + 1], int(w2))
        for pts, widths, start in layers:                       # rayitas del cuerpo
            for k in range(1, len(pts)):
                if start + k == 0:
                    continue
                (x, y), (px, py) = pts[k], pts[k - 1]
                d = math.hypot(px - x, py - y) or 1
                nx, ny = -(py - y) / d, (px - x) / d
                half = widths[k] / 2 - 4
                if half > 2:
                    stroke(surf, pal["ink"], (x - nx * half, y - ny * half),
                           (x + nx * half, y + ny * half), rnd, 2)

        # cabeza
        hx, hy = runs[0][0]
        fx, fy = facing
        pygame.draw.circle(surf, pal["ink"], (hx, hy), 16)
        pygame.draw.circle(surf, fill, (hx, hy), 13)
        sx, sy = -fy, fx
        for side in (-1, 1):
            ex, ey = hx + fx * 4 + sx * 6 * side, hy + fy * 4 + sy * 6 * side
            if dead:
                stroke(surf, pal["ink"], (ex - 3, ey - 3), (ex + 3, ey + 3), rnd, 2)
                stroke(surf, pal["ink"], (ex - 3, ey + 3), (ex + 3, ey - 3), rnd, 2)
            else:
                pygame.draw.circle(surf, (255, 255, 255), (ex, ey), 4)
                sketch_circle(surf, pal["ink"], (ex, ey), 4, rnd, 1)
                pygame.draw.circle(surf, pal["ink"], (ex + fx * 1.5, ey + fy * 1.5), 2)
        if not dead and (self.t % 2.2) < 0.3:                   # lengua
            tx, ty = hx + fx * 16, hy + fy * 16
            ex, ey = tx + fx * 8, ty + fy * 8
            pygame.draw.line(surf, pal["accent"], (tx, ty), (ex, ey), 2)
            pygame.draw.line(surf, pal["accent"], (ex, ey), (ex + fx * 4 + sx * 4, ey + fy * 4 + sy * 4), 2)
            pygame.draw.line(surf, pal["accent"], (ex, ey), (ex + fx * 4 - sx * 4, ey + fy * 4 - sy * 4), 2)

    def snake_runs(self, g):
        frac = g.move_fraction()
        prev = g.snake[1:] + g.snake[-1:]
        runs, run, last = [], [], None
        for (c, r), (pc, pr) in zip(g.snake, prev):
            if abs(pc - c) > 1 or abs(pr - r) > 1:
                pc, pr = c, r
            p = cell_center(pc + (c - pc) * frac, pr + (r - pr) * frac)
            if last and math.hypot(p[0] - last[0], p[1] - last[1]) > CELL * 1.5:
                runs.append(run)
                run = []
            run.append(p)
            last = p
        runs.append(run)
        return runs

    # ------------------------------------------------------------ comida, bonus, efectos
    def draw_apple(self, cell):
        pal = self.pal
        rnd = self.rnd(5)
        x, y = cell_center(*cell)
        scribble_circle(self.canvas, pal["apple"], (x, y + 1), 10, rnd, 2)
        sketch_circle(self.canvas, pal["ink"], (x, y + 1), 11, rnd, 2)
        stroke(self.canvas, pal["ink"], (x, y - 9), (x + 2, y - 16), rnd, 2)
        leaf = (110, 190, 80) if self.ink_idx == 2 else pal["ink"]
        pygame.draw.ellipse(self.canvas, leaf, (x + 2, y - 17, 9, 5))

    def draw_star(self, g):
        pal = self.pal
        rnd = self.rnd(9)
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        rot = math.sin(self.t * 3) * 0.2
        pts = star_points(x, y, 17, 8, rot)
        pygame.draw.polygon(self.canvas, pal["star"], pts)
        for i in range(10):
            stroke(self.canvas, pal["ink"], pts[i], pts[(i + 1) % 10], rnd, 2)
        frac = g.bonus_left / BONUS_TICKS                    # tiempo restante
        arc = circle_points((x, y), 25, rnd, turns=frac, n=30, wob=0.03)
        if len(arc) > 1:
            pygame.draw.lines(self.canvas, pal["accent"], False, arc, 2)

    def on_event(self, ev):
        kind = ev["type"]
        if kind == "eat":
            x, y = cell_center(*ev["pos"])
            self.effects.append(["burst", x, y, 0.4, 0.4, 8])
            self.effects.append(["text", x, y - 26, 0.9, 0.9, random.choice(POPS)])
        elif kind == "bonus":
            x, y = cell_center(*ev["pos"])
            x += CELL / 2
            self.effects.append(["burst", x, y, 0.6, 0.6, 14])
            self.effects.append(["text", x, y - 30, 1.2, 1.2, f"+{ev['points']}"])
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            self.effects.append(["text", x, y - 30, 1.2, 1.2, "¡Auch!"])
            self.shake = 0.4
        elif kind == "stage":
            self.flash = 0.5

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for e in self.effects:
            e[3] -= s
            if e[0] == "text":
                e[2] -= 30 * s
        self.effects = [e for e in self.effects if e[3] > 0]

    def draw_effects(self):
        rnd = self.rnd(13)
        for kind, x, y, life, life_max, extra in self.effects:
            k = 1 - life / life_max
            if kind == "burst":
                for i in range(extra):
                    a = math.tau * i / extra + 0.3
                    r1, r2 = 14 + 20 * k, 22 + 26 * k
                    stroke(self.canvas, self.pal["accent"],
                           (x + math.cos(a) * r1, y + math.sin(a) * r1),
                           (x + math.cos(a) * r2, y + math.sin(a) * r2), rnd, 2)
            else:
                img = self.font_mid.render(extra, True, self.pal["accent"])
                self.canvas.blit(img, img.get_rect(center=(x, y)))

    # ------------------------------------------------------------ textos y notas
    def text(self, s, font, color, **anchor):
        img = font.render(s, True, color)
        rect = img.get_rect(**anchor)
        self.canvas.blit(img, rect)
        return rect

    def sticky_note(self, lines, w=440, seed=1):
        """Nota adhesiva torcida; su altura se ajusta al texto. lines: [(texto, fuente, color)]"""
        rnd = random.Random(seed)
        h = 60 + sum(font.get_height() + 6 for _, font, _ in lines) + 20
        note = pygame.Surface((w, h), pygame.SRCALPHA)
        note.fill((255, 236, 130))
        pygame.draw.rect(note, (255, 246, 170), (0, 0, w, 34))                    # franja con pegamento
        pygame.draw.polygon(note, (226, 202, 96), [(w - 36, h), (w, h - 36), (w, h)])   # esquina doblada
        y = 60
        for s, font, color in lines:
            img = font.render(s, True, color)
            note.blit(img, img.get_rect(midtop=(w // 2, y - img.get_height() // 2 + 6)))
            y += img.get_height() + 6
        angle = rnd.uniform(-3, 3)
        rotated = pygame.transform.rotozoom(note, angle, 1)
        shadow = pygame.Surface(rotated.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 0))
        mask = pygame.mask.from_surface(rotated)
        shadow = mask.to_surface(setcolor=(0, 0, 0, 60), unsetcolor=(0, 0, 0, 0))
        rect = rotated.get_rect(center=(W // 2, H // 2 + 10))
        self.canvas.blit(shadow, rect.move(6, 8))
        self.canvas.blit(rotated, rect)

    def draw_hud(self, g):
        pal = self.pal
        rnd = self.rnd(17)
        self.text(f"Puntos: {g.score}", self.font_big, pal["ink"], midleft=(FX, 58))
        r = self.text(g.maze["name"].capitalize(), self.font_mid, pal["ink"], center=(W // 2, 56))
        stroke(self.canvas, pal["accent"], (r.left, r.bottom - 2), (r.right, r.bottom - 4), rnd, 2)
        if g.bonus:
            x, y = W - FX - 120, 58
            pygame.draw.polygon(self.canvas, pal["star"], star_points(x, y, 15, 7, 0))
            pts = star_points(x, y, 15, 7, 0)
            for i in range(10):
                stroke(self.canvas, pal["ink"], pts[i], pts[(i + 1) % 10], rnd, 2)
            self.text(str(g.bonus_left), self.font_big, pal["accent"], midleft=(x + 26, y))
        else:
            self.text(f"Mapa {g.maze_idx} · Nivel {g.level}", self.font_mid, pal["ink"],
                      midright=(W - FX, 58))

    # ------------------------------------------------------------ pantallas
    def draw_menu(self, app):
        pal = self.pal
        rnd = self.rnd(21)
        self.canvas.blit(self.paper(), (0, 0))
        r = self.text("Snake", self.font_huge, pal["ink"], center=(W // 2, 78))
        stroke(self.canvas, pal["accent"], (r.left, r.bottom - 14), (r.right, r.bottom - 20), rnd, 3)
        stroke(self.canvas, pal["accent"], (r.left + 10, r.bottom - 6), (r.right - 20, r.bottom - 10),
               rnd, 2)

        # serpiente garabateada ondulando
        n = 14
        pts = [(W // 2 + 210 - k * 30, 168 + math.sin(self.t * 3 + k * 0.6) * 12) for k in range(n)]
        dx, dy = pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]
        d = math.hypot(dx, dy) or 1
        self.draw_snake([pts], (dx / d, dy / d))

        rows = app.menu_rows()
        top = 218
        for i, (label, value) in enumerate(rows):
            y = top + i * 44
            sel = i == app.menu_sel
            color = pal["accent"] if sel else pal["ink"]
            self.text(label.capitalize(), self.font_mid, color, midleft=(W // 2 - 270, y))
            vr = self.text(value.capitalize(), self.font_mid, color, center=(W // 2 + 150, y))
            if sel:
                sketch_ellipse(self.canvas, pal["accent"], vr.inflate(44, 14), rnd, 2)
                stroke(self.canvas, pal["accent"], (W // 2 - 318, y), (W // 2 - 284, y), rnd, 2)
                stroke(self.canvas, pal["accent"], (W // 2 - 294, y - 8), (W // 2 - 284, y), rnd, 2)
                stroke(self.canvas, pal["accent"], (W // 2 - 294, y + 8), (W // 2 - 284, y), rnd, 2)
        y_end = top + len(rows) * 44
        self.text(f"Récord: {app.game.record}", self.font_small, pal["ink"], center=(W // 2, y_end + 6))
        if int(self.t * 2) % 2 == 0:
            self.text("Presiona ESPACIO para jugar", self.font_mid, pal["accent"],
                      center=(W // 2, H - 34))

    def draw(self, app):
        self.sheet_idx, self.ink_idx = app.opt(0), app.opt(1)
        inks = CHALK_INKS if self.sheet["kind"] == "chalk" else PAPER_INKS
        self.pal = inks[INKS[self.ink_idx]]
        pal = self.pal
        g = app.game

        if g.state == "menu":
            self.draw_menu(app)
        else:
            self.canvas.blit(self.static_layer(g.maze, (g.maze_idx, tuple(g.rocks)), g.wall_rects), (0, 0))
            if g.food:
                self.draw_apple(g.food)
            if g.bonus:
                self.draw_star(g)
            dead = g.state in ("dying", "over")
            blink = g.state == "dying" and (g.state_time // 120) % 2 == 1
            if g.snake and not blink:
                self.draw_snake(self.snake_runs(g), g.direction, dead)
            self.draw_effects()
            self.draw_hud(g)

        if g.state == "pause":
            ink = pal["ink"] if self.sheet["kind"] != "chalk" else (60, 60, 70)
            items = pause_items(app, ["Seguir jugando", "Menú principal"])
            self.sticky_note([("Pausa", self.font_huge, ink)] +
                             [(s, self.font_mid, (206, 46, 46) if sel else ink) for s, sel in items],
                             w=420, seed=3)
            # misma cuenta que sticky_note: la nota va centrada en H//2 + 10
            hh, mh = self.font_huge.get_height(), self.font_mid.get_height()
            top = H // 2 + 10 - (60 + hh + 6 + 2 * (mh + 6) + 20) // 2
            for i in range(len(items)):
                self.mark_pause(i, top + 60 + hh + 6 + i * (mh + 6) + 6)
        elif g.state == "stage":
            ink = (60, 60, 70)
            self.sticky_note([("¡Mapa superado!", self.font_mid, (206, 46, 46)),
                              (f"Mapa {g.maze_idx}: {g.maze['name'].capitalize()}", self.font_big, ink),
                              (f"Puntos: {g.score}", self.font_small, ink)], seed=g.maze_idx)
        elif g.state == "over":
            ink = (60, 60, 70)
            rec = ("¡Nuevo récord!", self.font_mid, (206, 46, 46)) if g.new_record else \
                  (f"Récord: {g.record}", self.font_small, ink)
            self.sticky_note([("Fin del juego", self.font_mid, (206, 46, 46)),
                              (str(g.score), self.font_huge, ink), rec,
                              ("ESPACIO: otra vez   ESC: menú", self.font_small, ink)],
                             w=480, seed=7)

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(170 * self.flash / 0.5)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.4 * 8)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((30, 30, 30))
        self.screen.blit(self.canvas, (ox, oy))
