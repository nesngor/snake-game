"""Estilo PLASTILINA: todo modelado en plastilina, con temblor de stop-motion a 12 fps."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, others, tint_mix, smooth_runs, WIDTH as W, HEIGHT as H

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
STOP_FPS = 12                   # cuadros por segundo del "stop-motion"
FONT_FILE = Path(__file__).resolve().parent.parent / "assets" / "Fredoka-SemiBold.ttf"

# Mesas de trabajo: nombre, color base, color de los muros
TABLES = [
    ("TAPETE", (40, 112, 92), (214, 112, 66)),
    ("MADERA", (176, 124, 78), (88, 122, 200)),
    ("CARTON", (204, 168, 120), (150, 94, 186)),
]
CLAYS = [
    ("VERDE", [(104, 190, 76)]),
    ("ARCOIRIS", [(232, 72, 64), (246, 152, 52), (246, 212, 64), (96, 184, 84),
                  (74, 144, 224), (154, 94, 204)]),
    ("RAYAS", [(74, 144, 224), (242, 238, 228)]),
]
APPLE = (226, 52, 52)
STAR = (250, 204, 52)
PEBBLE = (150, 146, 140)
INK = (52, 36, 40)
CREAM = (250, 242, 226)
POPS = ["¡Ñam!", "¡Ñom!", "¡Rico!", "¡Yum!"]


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


def star_points(cx, cy, r_out, r_in, rot=0.0):
    pts = []
    for k in range(10):
        a = rot + k * math.pi / 5 - math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def fingerprint(surf, color, center, r, rnd, rings=3):
    """Arcos finitos: la huella digital que queda en la plastilina."""
    cx, cy = center
    start = rnd.uniform(0, math.tau)
    for k in range(rings):
        rr = r * (0.35 + 0.22 * k)
        rect = pygame.Rect(0, 0, rr * 2, rr * 1.6)
        rect.center = (cx, cy)
        pygame.draw.arc(surf, color, rect, start + k * 0.4, start + k * 0.4 + 2.2, 1)


class ClayRenderer(Renderer):
    NAME = "PLASTILINA"
    KEY = "plastilina"
    OPTIONS = [("MESA", [t[0] for t in TABLES]), ("COLOR", [c[0] for c in CLAYS])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        self.shadow = pygame.Surface((W, H), pygame.SRCALPHA)
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)    # piezas que se mueven
        try:
            def font(size):
                return pygame.font.Font(str(FONT_FILE), size)
            self.font_huge = font(110)
        except Exception:
            def font(size):
                return pygame.font.Font(None, int(size * 1.1))
            self.font_huge = font(110)
        self.font_big = font(56)
        self.font_mid = font(36)
        self.font_small = font(26)
        self.t = 0.0
        self.table_idx = 0
        self.clay_idx = 0
        self.ball_cache = {}
        self.table_cache = {}
        self.static_cache = {}
        self.text_cache = {}
        self.effects = []      # [tipo, x, y, vx, vy, vida, vida_max, extra]
        self.shake = 0.0
        self.flash = 0.0

    @property
    def frame(self):
        return int(self.t * STOP_FPS)

    def jit(self, seed):
        """Temblor de 1 px que cambia en cada cuadro de stop-motion."""
        r = random.Random(self.frame * 7919 + seed)
        return r.choice((-1, 0, 0, 1)), r.choice((-1, 0, 0, 1))

    # ------------------------------------------------------------ piezas de plastilina
    def ball_sprite(self, color, r, seed=0):
        r = int(r)
        key = (color, r, seed % 3)
        if key in self.ball_cache:
            return self.ball_cache[key]
        size = r * 2 + 4
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        pygame.draw.circle(s, shade(color, 0.62), (c, c), r)                       # lado en sombra
        pygame.draw.circle(s, color, (c - r * 0.1, c - r * 0.12), r * 0.86)          # cuerpo
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*mix(color, (255, 255, 255), 0.35), 120),
                           (c - r * 0.3, c - r * 0.34), r * 0.45)
        s.blit(glow, (0, 0))
        pygame.draw.ellipse(s, (255, 255, 255, 170),
                            (c - r * 0.52, c - r * 0.6, max(2, r * 0.38), max(2, r * 0.22)))
        if r >= 8:
            fingerprint(s, (*shade(color, 0.8), 110), (c + r * 0.15, c + r * 0.1), r * 0.8,
                        random.Random(seed * 13 + r), rings=2 if r < 12 else 3)
        if len(self.ball_cache) > 400:
            self.ball_cache.clear()
        self.ball_cache[key] = s
        return s

    def ball(self, color, r, x, y, seed=0, squash=0.0, shadow=True):
        spr = self.ball_sprite(color, r, seed)
        if squash:
            w, h = spr.get_size()
            spr = pygame.transform.smoothscale(spr, (int(w * (1 + 0.4 * squash)),
                                                     max(2, int(h * (1 - 0.5 * squash)))))
            y += r * 0.5 * squash
        if shadow:
            sw = r * 2 * (1 + 0.4 * squash)
            pygame.draw.ellipse(self.shadow, (0, 0, 0, 60),
                                (x - sw / 2 + 4, y - r * 0.2 + 5, sw, r * 1.3))
        self.canvas.blit(spr, spr.get_rect(center=(x, y)))

    def log(self, surf, rect, color, seed=0, radius=12):
        """Tira de plastilina (muros, marcos, paneles)."""
        rect = pygame.Rect(rect)
        rnd = random.Random(seed)
        sh = pygame.Surface(rect.inflate(12, 12).size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 60), sh.get_rect().inflate(-12, -12), 0, radius)
        surf.blit(sh, rect.move(-6 + 5, -6 + 6))
        pygame.draw.rect(surf, shade(color, 0.62), rect, 0, radius)
        pygame.draw.rect(surf, color, rect.inflate(-5, -6).move(-1, -2), 0, max(2, radius - 2))
        hl = pygame.Rect(rect.left + 6, rect.top + 4, max(4, rect.w - 14), min(6, max(2, rect.h // 5)))
        pygame.draw.rect(surf, mix(color, (255, 255, 255), 0.35), hl, 0, 3)
        for _ in range(max(1, rect.w * rect.h // 2200)):           # huellas
            fx = rnd.uniform(rect.left + 10, max(rect.left + 11, rect.right - 10))
            fy = rnd.uniform(rect.top + 10, max(rect.top + 11, rect.bottom - 8))
            fingerprint(surf, shade(color, 0.85), (fx, fy), min(14, rect.w / 2, rect.h / 2), rnd)

    # ------------------------------------------------------------ mesa (cacheada)
    def table(self):
        idx = self.table_idx
        if idx in self.table_cache:
            return self.table_cache[idx]
        name, base, _ = TABLES[idx]
        surf = pygame.Surface((W, H))
        surf.fill(base)
        rnd = random.Random(5)
        for _ in range(3000):                                       # textura
            x, y = rnd.randrange(W), rnd.randrange(H)
            surf.set_at((x, y), shade(base, rnd.uniform(0.92, 1.07)))
        if name == "TAPETE":                                        # tapete de corte con cuadricula
            thin, thick = shade(base, 1.25), shade(base, 1.55)
            for i, x in enumerate(range(FX % CELL, W, CELL)):
                pygame.draw.line(surf, thick if (x - FX) // CELL % 5 == 0 else thin, (x, 0), (x, H),
                                 2 if (x - FX) // CELL % 5 == 0 else 1)
            for y in range(FY % CELL, H, CELL):
                pygame.draw.line(surf, thick if (y - FY) // CELL % 5 == 0 else thin, (0, y), (W, y),
                                 2 if (y - FY) // CELL % 5 == 0 else 1)
            for k in range(-H, W, 180):                             # diagonales de 45 grados
                pygame.draw.line(surf, shade(base, 1.12), (k, H), (k + H, 0))
        elif name == "MADERA":
            for top in range(0, H, 96):                             # tablones
                tone = shade(base, rnd.uniform(0.9, 1.06))
                surf.fill(tone, (0, top, W, 94))
                for _ in range(16):                                 # vetas
                    y0, amp, ph = top + rnd.uniform(6, 88), rnd.uniform(2, 6), rnd.uniform(0, 6)
                    pts = [(x, y0 + math.sin(x / rnd.uniform(60, 140) + ph) * amp) for x in range(0, W + 20, 20)]
                    pygame.draw.lines(surf, shade(tone, 0.86), False, pts, 1)
                pygame.draw.line(surf, shade(base, 0.6), (0, top + 94), (W, top + 94), 2)
                kx = rnd.randrange(60, W - 60)
                pygame.draw.ellipse(surf, shade(tone, 0.75), (kx, top + 34, 26, 14), 2)
        else:                                                       # carton con manchas de cafe
            for x in range(0, W, 7):
                pygame.draw.line(surf, shade(base, 0.97), (x, 0), (x, H))
            for _ in range(4):
                cx, cy, rr = rnd.randrange(W), rnd.randrange(H), rnd.randrange(30, 60)
                pygame.draw.circle(surf, shade(base, 0.86), (cx, cy), rr, 4)
            for _ in range(3):                                      # cinta adhesiva
                tape = pygame.Surface((150, 34), pygame.SRCALPHA)
                tape.fill((236, 226, 190, 150))
                tape = pygame.transform.rotate(tape, rnd.uniform(-30, 30))
                surf.blit(tape, (rnd.randrange(W - 150), rnd.randrange(H - 40)))
        self.table_cache[idx] = surf
        return surf

    def static_layer(self, g):
        """Mesa + marco + muros. Dos versiones que se alternan (stop-motion)."""
        variant = (self.frame // 2) % 2
        key = (self.table_idx, g.maze_idx, tuple(g.rocks), variant)
        if key in self.static_cache:
            return self.static_cache[key]
        surf = self.table().copy()
        rnd = random.Random(variant * 31 + 7)
        wall = TABLES[self.table_idx][2]
        field = pygame.Rect(FX, FY, FW, FH)
        tint = pygame.Surface(field.size, pygame.SRCALPHA)        # campo un poco mas oscuro
        tint.fill((0, 0, 0, 26))
        surf.blit(tint, field)
        if g.maze["border"]:
            frame = field.inflate(20, 20)
            for side in (pygame.Rect(frame.left, frame.top, frame.w, 12),
                         pygame.Rect(frame.left, frame.bottom - 12, frame.w, 12),
                         pygame.Rect(frame.left, frame.top, 12, frame.h),
                         pygame.Rect(frame.right - 12, frame.top, 12, frame.h)):
                self.log(surf, side.move(rnd.choice((-1, 0, 1)), 0), wall, seed=side.x + side.y, radius=6)
        else:                                                       # se atraviesa: cuentas sueltas
            spr = self.ball_sprite(CREAM, 4, 1)
            for x in range(field.left, field.right + 1, 24):
                for y in (field.top - 8, field.bottom + 8):
                    surf.blit(spr, spr.get_rect(center=(x + rnd.choice((-1, 0, 1)), y)))
            for y in range(field.top, field.bottom + 1, 24):
                for x in (field.left - 8, field.right + 8):
                    surf.blit(spr, spr.get_rect(center=(x, y + rnd.choice((-1, 0, 1)))))
        for c, r, w, h in g.maze["walls"]:
            rect = pygame.Rect(FX + c * CELL + 2, FY + r * CELL + 2, w * CELL - 4, h * CELL - 4)
            self.log(surf, rect.move(rnd.choice((-1, 0, 1)), rnd.choice((-1, 0, 1))), wall,
                     seed=c * 31 + r)
        for c, r in g.rocks:                                        # rocas = piedritas grises
            x, y = cell_center(c, r)
            spr = self.ball_sprite(PEBBLE, 14, c + r)
            sh = pygame.Surface((32, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect())
            surf.blit(sh, (x - 12, y + 2))
            surf.blit(spr, spr.get_rect(center=(x, y)))
        if len(self.static_cache) > 40:
            self.static_cache.clear()
        self.static_cache[key] = surf
        return surf

    def with_shadows(self, draw_fn):
        """Dibuja objetos en una capa aparte y la pega sobre sus sombras,
        asi ninguna sombra queda encima de una pieza."""
        real = self.canvas
        self.shadow.fill((0, 0, 0, 0))
        self.layer.fill((0, 0, 0, 0))
        self.canvas = self.layer
        try:
            draw_fn()
        finally:
            self.canvas = real
        real.blit(self.shadow, (0, 0))
        real.blit(self.layer, (0, 0))

    # ------------------------------------------------------------ texto en relieve
    def text(self, s, font, color, depth=3, **anchor):
        key = (s, id(font), color, depth)
        img = self.text_cache.get(key)
        if img is None:
            base = font.render(s, True, color)
            dark = font.render(s, True, shade(color, 0.55))
            light = font.render(s, True, mix(color, (255, 255, 255), 0.5))
            img = pygame.Surface((base.get_width() + depth + 2, base.get_height() + depth + 2),
                                 pygame.SRCALPHA)
            for d in range(depth, 0, -1):                           # volumen
                img.blit(dark, (1 + d, 1 + d))
            img.blit(light, (0, 0))
            img.blit(base, (1, 1))
            if len(self.text_cache) > 300:
                self.text_cache.clear()
            self.text_cache[key] = img
        rect = img.get_rect(**anchor)
        self.canvas.blit(img, rect)
        return rect

    def slab(self, w, h, color=CREAM, cy=None):
        """Panel: una tortita de plastilina con velo encima del juego."""
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 90))
        self.canvas.blit(veil, (0, 0))
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, cy or H // 2)
        self.log(self.canvas, rect, color, seed=w + h, radius=30)
        return rect

    # ------------------------------------------------------------ serpiente, comida, bonus
    def draw_snake(self, points, facing, dead=False, squash=0.0, tint=None):
        """points: posiciones en px (cabeza primero), cortadas en tramos por los bordes."""
        colors = CLAYS[self.clay_idx][1]
        if tint:                                                    # rival: plastilina de su color
            colors = [tint, mix(tint, (255, 255, 255), 0.25)]
        balls = []
        idx = 0
        total = sum(len(run) for run in points)
        for run in points:
            for k, (x, y) in enumerate(run):
                i = idx + k
                r = 17 - 6 * i / max(1, total - 1)
                col = colors[i % len(colors)]
                if dead:
                    col = mix(col, (150, 150, 150), 0.45)
                if k + 1 < len(run):                                # bolita intermedia: rollo continuo
                    nx, ny = run[k + 1]
                    balls.append((col, r - 1, (x + nx) / 2, (y + ny) / 2, i * 2 + 1))
                balls.append((col, r, x, y, i * 2))
            idx += len(run)
        for col, r, x, y, seed in reversed(balls):                  # de la cola a la cabeza
            jx, jy = self.jit(seed)
            self.ball(col, r, x + jx, y + jy, seed, squash)

        hx, hy = points[0][0]
        jx, jy = self.jit(0)
        hx, hy = hx + jx, hy + jy + 17 * 0.5 * squash
        fx, fy = facing
        sx, sy = -fy, fx
        for side in (-1, 1):
            ex, ey = hx + fx * 5 + sx * 8 * side, hy + fy * 5 + sy * 8 * side - 2
            if dead:
                for a in (1, -1):
                    pygame.draw.line(self.canvas, INK, (ex - 4, ey - 4 * a), (ex + 4, ey + 4 * a), 3)
            else:
                self.ball((250, 250, 250), 6, ex, ey, 2, shadow=False)
                pygame.draw.circle(self.canvas, INK, (ex + fx * 2.5, ey + fy * 2.5), 3)
        if not dead and (self.t % 2.4) < 0.35:                      # lengua de plastilina
            tx, ty = hx + fx * 16, hy + fy * 16
            pygame.draw.line(self.canvas, (220, 60, 90), (tx, ty), (tx + fx * 9, ty + fy * 9), 4)
            for s in (-1, 1):
                pygame.draw.line(self.canvas, (220, 60, 90), (tx + fx * 9, ty + fy * 9),
                                 (tx + fx * 13 + sx * 4 * s, ty + fy * 13 + sy * 4 * s), 3)

    def snake_points(self, g):
        return [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]

    def draw_apple(self, cell):
        x, y = cell_center(*cell)
        jx, jy = self.jit(101)
        x, y = x + jx, y + jy + (2 if self.frame % 6 < 3 else 0)   # rebote a saltos
        self.ball(APPLE, 13, x, y + 1, 5)
        pygame.draw.line(self.canvas, (110, 70, 40), (x, y - 9), (x + 2, y - 15), 4)
        leaf = pygame.Rect(x + 2, y - 18, 12, 7)
        pygame.draw.ellipse(self.canvas, (60, 140, 60), leaf.move(1, 1))
        pygame.draw.ellipse(self.canvas, (96, 184, 84), leaf)

    def draw_star(self, g):
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        jx, jy = self.jit(202)
        x, y = x + jx, y + jy
        rot = (self.frame % 8) * 0.04 - 0.14                       # se mece a saltos
        pygame.draw.ellipse(self.shadow, (0, 0, 0, 60), (x - 18 + 4, y + 6, 36, 14))
        pygame.draw.polygon(self.canvas, shade(STAR, 0.62), star_points(x + 2, y + 3, 23, 11, rot))
        pygame.draw.polygon(self.canvas, STAR, star_points(x, y, 22, 10.5, rot))
        pygame.draw.polygon(self.canvas, mix(STAR, (255, 255, 255), 0.5),
                            star_points(x - 3, y - 3, 6, 3, rot))
        left = math.ceil(5 * g.bonus_left / BONUS_TICKS)            # cuentas de tiempo restante
        for k in range(left):
            self.ball((240, 80, 120), 4, x - 16 + k * 8, y + 24, k, shadow=False)

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        colors = CLAYS[self.clay_idx][1]
        if kind in ("eat", "bonus"):
            x, y = cell_center(*ev["pos"])
            if kind == "bonus":
                x += CELL / 2
            n = 7 if kind == "eat" else 12
            for i in range(n):                                     # migajas de plastilina
                a = random.uniform(math.pi * 1.1, math.pi * 1.9)
                v = random.uniform(120, 240)
                col = APPLE if kind == "eat" and i % 2 else (STAR if kind == "bonus" else colors[i % len(colors)])
                self.effects.append(["crumb", x, y, math.cos(a) * v, math.sin(a) * v, 0.7, 0.7, col])
            label = random.choice(POPS) if kind == "eat" else f"+{ev['points']}"
            self.effects.append(["text", x, y - 28, 0, -40, 0.9, 0.9, label])
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            self.effects.append(["text", x, y - 30, 0, -30, 1.2, 1.2, "¡Splat!"])
            self.shake = 0.45
        elif kind == "stage":
            self.flash = 0.5

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for e in self.effects:
            e[1] += e[3] * s
            e[2] += e[4] * s
            if e[0] == "crumb":
                e[4] += 700 * s                                     # gravedad
            e[5] -= s
        self.effects = [e for e in self.effects if e[5] > 0]

    def draw_effects(self):
        for kind, x, y, vx, vy, life, life_max, extra in self.effects:
            if kind == "crumb":
                self.ball(extra, 4, x, y, int(x) % 3, shadow=False)
            else:
                self.text(extra, self.font_mid, CREAM, 2, center=(x, y))

    # ------------------------------------------------------------ HUD y pantallas
    def draw_hud(self, g):
        self.text(f"{g.score:04d}", self.font_big, STAR, center=(FX + 70, 52))
        self.text(g.maze["name"].capitalize(), self.font_mid, CREAM, center=(W // 2, 52))
        if g.bonus:
            x = W - FX - 110
            pygame.draw.polygon(self.canvas, shade(STAR, 0.62), star_points(x + 2, 54, 16, 8))
            pygame.draw.polygon(self.canvas, STAR, star_points(x, 52, 15, 7))
            self.text(str(g.bonus_left), self.font_big, (240, 80, 120), midleft=(x + 26, 52))
        else:
            self.text(f"Mapa {g.maze_idx} · Nivel {g.level}", self.font_small, CREAM,
                      midright=(W - FX, 52))

    def draw_menu(self, app):
        self.canvas.blit(self.table(), (0, 0))
        colors = CLAYS[1][1]
        x = W // 2 - self.font_huge.size("Snake")[0] // 2
        for i, ch in enumerate("Snake"):                          # letras de colores, cada una brinca
            bounce = 6 if (self.frame + i * 3) % 12 < 6 else 0
            r = self.text(ch, self.font_huge, colors[i % len(colors)], 5, topleft=(x, 6 - bounce))
            x = r.right - 6
        n = 12
        pts = [(W // 2 + 180 - k * 30, 160 + math.sin((self.frame / STOP_FPS) * 4 + k * 0.6) * 10)
               for k in range(n)]
        self.with_shadows(lambda: self.draw_snake([pts], (1, 0)))

        rows = app.menu_rows()
        top = 214
        for i, (label, value) in enumerate(rows):
            y = top + i * 42
            sel = i == app.menu_sel
            if sel:
                pill = pygame.Rect(0, 0, 300, 38)
                pill.center = (W // 2 + 150, y)
                self.log(self.canvas, pill, (240, 80, 120), seed=i, radius=18)
                for s in (-1, 1):                                   # flechitas de plastilina
                    ax = pill.centerx + s * 132
                    pygame.draw.polygon(self.canvas, CREAM, [(ax + s * 8, y), (ax - s * 2, y - 8),
                                                             (ax - s * 2, y + 8)])
            self.text(label.capitalize(), self.font_mid, STAR if sel else CREAM, 2,
                      midleft=(W // 2 - 280, y))
            self.text(value.capitalize(), self.font_mid, CREAM, 2, center=(W // 2 + 150, y))
        y_end = top + len(rows) * 42
        self.text(f"Récord: {app.game.record}", self.font_small, CREAM, 2, center=(W // 2, y_end + 4))
        if (self.frame // 6) % 2 == 0:
            self.text("Presiona ESPACIO para jugar", self.font_mid, STAR, 3, center=(W // 2, H - 30))

    def draw(self, app):
        self.table_idx, self.clay_idx = app.opt(0), app.opt(1)
        g = app.game

        if g.state == "menu":
            self.draw_menu(app)
        else:
            self.canvas.blit(self.static_layer(g), (0, 0))
            dead = g.state in ("dying", "over")
            squash = min(1.0, g.state_time / 350) if g.state == "dying" else (1.0 if dead else 0.0)

            def objects():
                if g.food:
                    self.draw_apple(g.food)
                if g.bonus:
                    self.draw_star(g)
                for o in others(g):                                 # rivales (modo en linea)
                    self.draw_snake(self.snake_points(o), o.direction, o.dead, 1.0 if o.dead else 0.0, o.tint)
                if g.snake:
                    self.draw_snake(self.snake_points(g), g.direction, dead, squash)
                self.draw_effects()
            self.with_shadows(objects)
            self.draw_hud(g)

        if g.state == "pause":
            box = self.slab(420, 250)
            self.text("Pausa", self.font_big, (240, 80, 120), 4, center=(W // 2, box.top + 58))
            for i, (s, sel) in enumerate(pause_items(app, ["Seguir jugando", "Menú principal"])):
                self.mark_pause(i, box.top + 134 + i * 50)
                self.text(s, self.font_mid, (74, 144, 224) if sel else (120, 110, 110), 2,
                          center=(W // 2, box.top + 134 + i * 50))
        elif g.state == "stage":
            box = self.slab(540, 240)
            self.text("¡Mapa superado!", self.font_mid, (240, 80, 120), 3, center=(W // 2, box.top + 52))
            self.text(f"Mapa {g.maze_idx}: {g.maze['name'].capitalize()}", self.font_big, (74, 144, 224), 4,
                      center=(W // 2, box.centery + 4))
            self.text(f"Puntos {g.score}", self.font_small, (110, 96, 96), 2, center=(W // 2, box.bottom - 42))
        elif g.state == "over":
            box = self.slab(560, 320)
            self.text("¡Aplastada!", self.font_mid, (240, 80, 120), 3, center=(W // 2, box.top + 46))
            self.text(f"{g.score}", self.font_huge, (74, 144, 224), 5, center=(W // 2, box.top + 128))
            if g.new_record:
                if (self.frame // 5) % 2 == 0:
                    self.text("¡Nuevo récord!", self.font_mid, (246, 152, 52), 3, center=(W // 2, box.top + 210))
            else:
                self.text(f"Récord {g.record}", self.font_small, (110, 96, 96), 2, center=(W // 2, box.top + 210))
            self.text("ESPACIO: otra vez   ESC: menú", self.font_small, (110, 96, 96), 2,
                      center=(W // 2, box.bottom - 40))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 250, 230, int(170 * self.flash / 0.5)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.45 * 9)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((24, 20, 20))
        self.screen.blit(self.canvas, (ox, oy))
