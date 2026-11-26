"""Estilo CIRCUITO: placa electronica; la serpiente es una pista de cobre con senal."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS
from styles.base import Renderer, pause_items, smooth_runs, WIDTH as W, HEIGHT as H

CELL = 32
FX, FY = 32, 96
FW, FH = COLS * CELL, ROWS * CELL
ASSETS = Path(__file__).resolve().parent.parent / "assets"

BOARDS = [            # color de la mascara de soldadura
    ("VERDE", (22, 92, 50)),
    ("AZUL", (20, 56, 128)),
    ("NEGRA", (26, 26, 30)),
    ("MORADA", (78, 38, 118)),
]
PULSES = [("CIAN", (80, 230, 255)), ("ROJO", (255, 72, 60)), ("AMBAR", (255, 190, 40))]

GOLD = (226, 180, 88)          # cobre con acabado dorado (ENIG)
SILK = (236, 236, 228)         # serigrafia
CHIP = (30, 30, 34)
PIN = (196, 198, 204)
BURNT = (70, 44, 26)
SEG_RED = (255, 52, 40)
LCD_BG = (150, 190, 46)
LCD_INK = (28, 44, 16)
POPS = ["¡ZAP!", "¡BZZT!", "+5V", "¡CLIC!", "BIT++"]
PARTS = ["NE555", "LM358", "74HC00", "ATMEGA", "ESP32", "Z80", "LM317", "4017"]

SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
            "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def cell_center(c, r):
    return FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2


def seven_seg(surf, x, y, w, h, ch, on, off, t=5):
    """Un digito de 7 segmentos con los segmentos apagados visibles (como un display real)."""
    lit = SEGMENTS.get(ch, "")
    x0, x1, y0, ym, y1 = x, x + w, y, y + h / 2, y + h
    def hseg(xa, xb, yc):
        return [(xa + t / 2, yc), (xa + t, yc - t / 2), (xb - t, yc - t / 2), (xb - t / 2, yc),
                (xb - t, yc + t / 2), (xa + t, yc + t / 2)]
    def vseg(xc, ya, yb):
        return [(xc, ya + t / 2), (xc + t / 2, ya + t), (xc + t / 2, yb - t), (xc, yb - t / 2),
                (xc - t / 2, yb - t), (xc - t / 2, ya + t)]
    segs = {"a": hseg(x0, x1, y0), "g": hseg(x0, x1, ym), "d": hseg(x0, x1, y1),
            "f": vseg(x0, y0, ym), "b": vseg(x1, y0, ym), "e": vseg(x0, ym, y1), "c": vseg(x1, ym, y1)}
    for name, pts in segs.items():
        pygame.draw.polygon(surf, on if name in lit else off, pts)


class CircuitRenderer(Renderer):
    NAME = "CIRCUITO"
    KEY = "circuito"
    OPTIONS = [("PLACA", [b[0] for b in BOARDS]), ("PULSO", [p[0] for p in PULSES])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        self.glow = pygame.Surface((W // 4, H // 4))           # luz a 1/4 de resolucion
        try:
            def font(size, bold=True):
                name = "IBMPlexMono-Bold.ttf" if bold else "IBMPlexMono-Regular.ttf"
                return pygame.font.Font(str(ASSETS / name), size)
            self.font_title = font(92)
        except Exception:
            def font(size, bold=True):
                return pygame.font.Font(None, int(size * 1.2))
            self.font_title = font(92)
        self.font_big = font(46)
        self.font_mid = font(28)
        self.font_small = font(20)
        self.font_tiny = font(12, bold=False)
        self.t = 0.0
        self.board_idx = 0
        self.pulse_idx = 0
        self.bg_cache = {}
        self.static_cache = {}
        self.puffs = {}
        self.effects = []     # [tipo, x, y, vx, vy, vida, vida_max, extra]
        self.shake = 0.0
        self.flash = 0.0

    @property
    def board(self):
        return BOARDS[self.board_idx][1]

    @property
    def pulse(self):
        return PULSES[self.pulse_idx][1]

    # ------------------------------------------------------------ placa (cacheada)
    def trace_under_mask(self, surf, rnd, start, steps, width=4):
        """Pista decorativa: tramos rectos con quiebres de 45 grados, bajo la mascara."""
        col = mix(self.board, GOLD, 0.32)
        x, y = start
        d = rnd.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        pts = [(x, y)]
        for _ in range(steps):
            run = rnd.randrange(30, 120)
            x, y = x + d[0] * run, y + d[1] * run
            pts.append((x, y))
            dx, dy = d                                              # gira 45 grados y luego 90
            diag = (dx - dy, dy + dx) if rnd.random() < 0.5 else (dx + dy, dy - dx)
            diag = (max(-1, min(1, diag[0])), max(-1, min(1, diag[1])))
            k = rnd.randrange(10, 30)
            x, y = x + diag[0] * k, y + diag[1] * k
            pts.append((x, y))
            d = (diag[0], 0) if diag[0] and rnd.random() < 0.5 else ((0, diag[1]) if diag[1] else (diag[0], 0))
        pygame.draw.lines(surf, col, False, pts, width)
        for p in (pts[0], pts[-1]):                                 # via en cada extremo
            pygame.draw.circle(surf, col, p, width + 3)
            pygame.draw.circle(surf, shade(self.board, 0.4), p, max(2, width - 1))

    def background(self):
        key = self.board_idx
        if key in self.bg_cache:
            return self.bg_cache[key]
        rnd = random.Random(29)
        b = self.board
        surf = pygame.Surface((W, H))
        surf.fill(b)
        for k in range(-H, W, 6):                                   # trama de fibra de vidrio
            pygame.draw.line(surf, shade(b, 1.05), (k, H), (k + H, 0))
        for _ in range(2500):
            x, y = rnd.randrange(W), rnd.randrange(H)
            surf.set_at((x, y), shade(b, rnd.uniform(0.9, 1.12)))
        field = pygame.Rect(FX, FY, FW, FH)
        border = field.inflate(60, 30)
        for _ in range(26):                                         # pistas fuera del tablero
            side = rnd.randrange(4)
            if side == 0:
                start = (rnd.randrange(W), rnd.randrange(4, FY - 30))
            elif side == 1:
                start = (rnd.randrange(W), H - rnd.randrange(4, 18))
            elif side == 2:
                start = (rnd.randrange(4, 22), rnd.randrange(H))
            else:
                start = (W - rnd.randrange(4, 22), rnd.randrange(H))
            self.trace_under_mask(surf, rnd, start, rnd.randrange(1, 3), rnd.choice((3, 4, 6)))
        surf.fill(b, field.inflate(-4, -4))                         # el tablero queda limpio
        for x in range(FX + CELL, FX + FW, CELL):                    # rejilla de puntos (pads)
            for y in range(FY + CELL, FY + FH, CELL):
                pygame.draw.circle(surf, mix(b, GOLD, 0.22), (x, y), 2)
        for cx, cy in ((12, 12), (W - 12, 12), (12, H - 12), (W - 12, H - 12)):   # agujeros de montaje
            pygame.draw.circle(surf, GOLD, (cx, cy), 9)
            pygame.draw.circle(surf, (14, 14, 16), (cx, cy), 5)
        labels = ["R12", "C4", "U7", "D2", "Q1", "J3", "TP1", "L2"]
        for i, lab in enumerate(labels):                            # serigrafia, repartida sin encimarse
            img = self.font_tiny.render(lab, True, SILK)
            x = 60 + i * 76 + rnd.randrange(0, 30)
            surf.blit(img, (x, 6 if i % 2 else H - 16))
        img = self.font_tiny.render("SNAKE-PCB REV 1.3", True, SILK)
        surf.blit(img, (W - img.get_width() - 30, H - 16))
        self.bg_cache[key] = surf
        return surf

    def static_layer(self, g):
        key = (self.board_idx, g.maze_idx, tuple(g.rocks))
        if key in self.static_cache:
            return self.static_cache[key]
        surf = self.background().copy()
        field = pygame.Rect(FX, FY, FW, FH)
        if g.maze["border"]:                                        # anillo de tierra con vias
            pygame.draw.rect(surf, GOLD, field.inflate(10, 10), 5, 4)
            for x in range(field.left, field.right + 1, CELL * 2):
                for y in (field.top - 3, field.bottom + 2):
                    pygame.draw.circle(surf, shade(self.board, 0.3), (x, y), 2)
            for y in range(field.top, field.bottom + 1, CELL * 2):
                for x in (field.left - 3, field.right + 2):
                    pygame.draw.circle(surf, shade(self.board, 0.3), (x, y), 2)
        else:                                                       # se atraviesa: linea serigrafiada
            for x in range(field.left, field.right, 14):
                pygame.draw.line(surf, SILK, (x, field.top - 4), (x + 6, field.top - 4), 2)
                pygame.draw.line(surf, SILK, (x, field.bottom + 3), (x + 6, field.bottom + 3), 2)
            for y in range(field.top, field.bottom, 14):
                pygame.draw.line(surf, SILK, (field.left - 4, y), (field.left - 4, y + 6), 2)
                pygame.draw.line(surf, SILK, (field.right + 3, y), (field.right + 3, y + 6), 2)
        for i, (c, r, w, h) in enumerate(g.maze["walls"]):
            self.chip(surf, pygame.Rect(FX + c * CELL, FY + r * CELL, w * CELL, h * CELL), i)
        for c, r in g.rocks:                                        # rocas = resistencias SMD
            x, y = cell_center(c, r)
            body = pygame.Rect(0, 0, 26, 14)
            body.center = (x, y)
            surf.fill(PIN, body)
            surf.fill(CHIP, body.inflate(-10, 0))
            img = self.font_tiny.render("103", True, SILK)
            surf.blit(img, img.get_rect(center=body.center))
        if len(self.static_cache) > 30:
            self.static_cache.clear()
        self.static_cache[key] = surf
        return surf

    def chip(self, surf, rect, seed):
        """Muro = circuito integrado. Patitas en los lados largos (o en los 4 si es cuadrado)."""
        rnd = random.Random(seed * 131 + rect.x * 7 + rect.y * 3)
        body = rect.inflate(-10, -10)
        square = abs(rect.w - rect.h) < CELL
        horizontal = rect.w >= rect.h
        sides = ("top", "bottom", "left", "right") if square else \
                (("top", "bottom") if horizontal else ("left", "right"))
        for side in sides:
            if side in ("top", "bottom"):
                y0 = rect.top + 1 if side == "top" else body.bottom
                for x in range(body.left + 6, body.right - 4, 10):
                    surf.fill(PIN, (x, y0, 5, 5 if side == "top" else 4))
            else:
                x0 = rect.left + 1 if side == "left" else body.right
                for y in range(body.top + 6, body.bottom - 4, 10):
                    surf.fill(PIN, (x0, y, 5 if side == "left" else 4, 5))
        dark_board = sum(self.board) < 120                          # en placa negra el chip se perderia
        pygame.draw.rect(surf, (12, 12, 14), body.move(2, 3), 0, 3)
        pygame.draw.rect(surf, (56, 56, 62) if dark_board else CHIP, body, 0, 3)
        pygame.draw.rect(surf, (96, 96, 104), body, 1, 3)
        if horizontal:                                              # muesca de orientacion
            pygame.draw.circle(surf, (14, 14, 16), (body.left, body.centery), min(6, body.h // 3))
        else:
            pygame.draw.circle(surf, (14, 14, 16), (body.centerx, body.top), min(6, body.w // 3))
        pygame.draw.circle(surf, (70, 70, 76), (body.left + 7, body.top + 7), 2)   # punto del pin 1
        name = rnd.choice(PARTS)
        img = self.font_tiny.render(name, True, (150, 150, 158))
        if not horizontal:
            img = pygame.transform.rotate(img, 90)
        if img.get_width() < body.w - 6 and img.get_height() < body.h - 4:
            surf.blit(img, img.get_rect(center=body.center))

    # ------------------------------------------------------------ luz (glow)
    def glow_dot(self, x, y, r, color, k=1.0):
        pygame.draw.circle(self.glow, shade(color, k), (x / 4, y / 4), max(1, r / 4))

    def apply_glow(self):
        small = pygame.transform.box_blur(self.glow, 2)
        self.canvas.blit(pygame.transform.smoothscale(small, (W, H)), (0, 0),
                         special_flags=pygame.BLEND_RGB_ADD)
        self.glow.fill((0, 0, 0))

    # ------------------------------------------------------------ serpiente = pista con senal
    def draw_snake(self, runs, facing, dead=False):
        copper = BURNT if dead else GOLD
        for run in runs:
            if len(run) > 1:
                pygame.draw.lines(self.canvas, shade(copper, 0.55), False, run, 20)
                pygame.draw.lines(self.canvas, copper, False, run, 15)
                pygame.draw.lines(self.canvas, mix(copper, (255, 255, 255), 0.35), False,
                                  [(x - 2, y - 2) for x, y in run], 3)
            for x, y in run:                                        # junta de soldadura en cada tramo
                pygame.draw.circle(self.canvas, shade(copper, 0.55), (x, y), 9)
                pygame.draw.circle(self.canvas, copper, (x, y), 7)
                pygame.draw.circle(self.canvas, shade(copper, 0.75), (x, y), 3)
        if not dead:                                                # pulsos que viajan de la cola a la cabeza
            path = [p for run in reversed(runs) for p in reversed(run)]
            lens = [0.0]
            for a, b in zip(path, path[1:]):
                d = math.hypot(b[0] - a[0], b[1] - a[1])
                lens.append(lens[-1] + (d if d < CELL * 1.5 else 0))   # el salto del borde no cuenta
            total = lens[-1]
            if total > 0:
                for k in range(max(1, int(total // 130))):
                    s = (self.t * 260 + k * 130) % total
                    i = next(j for j in range(1, len(lens)) if lens[j] >= s) if s > 0 else 1
                    a, b = path[i - 1], path[min(i, len(path) - 1)]
                    seg = lens[i] - lens[i - 1] or 1
                    u = (s - lens[i - 1]) / seg
                    px, py = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                    pygame.draw.circle(self.canvas, mix(self.pulse, (255, 255, 255), 0.6), (px, py), 5)
                    self.glow_dot(px, py, 18, self.pulse)
            for run in runs:                                        # brillo suave a lo largo de la pista
                for x, y in run[::2]:
                    self.glow_dot(x, y, 18, self.pulse, 0.25)
        self.draw_head(runs[0][0], facing, dead)

    def draw_head(self, pos, facing, dead):
        """Cabeza = un chip con dos LEDs por ojos."""
        hx, hy = pos
        fx, fy = facing
        sx, sy = -fy, fx
        def P(u, v):
            return (hx + fx * u + sx * v, hy + fy * u + sy * v)
        for u in (-8, -1, 6):                                       # patitas a los costados
            for v in (-1, 1):
                pygame.draw.line(self.canvas, PIN, P(u, v * 12), P(u, v * 17), 4)
        body = [P(-13, -13), P(13, -13), P(13, 13), P(-13, 13)]
        pygame.draw.polygon(self.canvas, (12, 12, 14), [(x + 2, y + 3) for x, y in body])
        pygame.draw.polygon(self.canvas, BURNT if dead else CHIP, body)
        pygame.draw.polygon(self.canvas, (70, 70, 78), body, 1)
        for v in (-6, 6):
            ex, ey = P(6, v)
            if dead:
                pygame.draw.line(self.canvas, (120, 120, 120), (ex - 3, ey - 3), (ex + 3, ey + 3), 2)
                pygame.draw.line(self.canvas, (120, 120, 120), (ex - 3, ey + 3), (ex + 3, ey - 3), 2)
            else:
                pygame.draw.circle(self.canvas, self.pulse, (ex, ey), 4)
                pygame.draw.circle(self.canvas, (255, 255, 255), (ex - 1, ey - 1), 1.5)
                self.glow_dot(ex, ey, 9, self.pulse)

    def snake_runs(self, g):
        return [[cell_center(c, r) for c, r in run] for run in smooth_runs(g)]

    # ------------------------------------------------------------ comida y bonus
    def draw_led(self, cell):
        x, y = cell_center(*cell)
        on = (self.t * 3) % 1 < 0.7                                # parpadea
        for s in (-1, 1):                                          # patitas
            pygame.draw.line(self.canvas, PIN, (x + s * 5, y + 8), (x + s * 5, y + 15), 3)
        red = (255, 60, 60) if on else (150, 30, 34)
        pygame.draw.circle(self.canvas, shade(red, 0.6), (x, y), 12)
        pygame.draw.circle(self.canvas, red, (x, y), 10)
        pygame.draw.line(self.canvas, shade(red, 0.5), (x - 9, y + 7), (x + 9, y + 7), 3)  # lado plano
        pygame.draw.circle(self.canvas, (255, 220, 220), (x - 3, y - 4), 3)
        if on:
            self.glow_dot(x, y, 24, (255, 60, 60))

    def draw_battery(self, g):
        c, r = g.bonus
        x, y = cell_center(c, r)
        x += CELL / 2
        body = pygame.Rect(0, 0, 52, 24)
        body.center = (x - 2, y)
        pygame.draw.rect(self.canvas, (14, 14, 16), body.move(2, 3), 0, 6)
        pygame.draw.rect(self.canvas, (40, 40, 46), body, 0, 6)
        pygame.draw.rect(self.canvas, PIN, (body.right, body.centery - 5, 5, 10), 0, 2)    # borne +
        pygame.draw.rect(self.canvas, GOLD, (body.right - 12, body.top, 5, body.h))
        frac = g.bonus_left / BONUS_TICKS                          # carga = tiempo restante
        bars = math.ceil(5 * frac)
        col = (90, 230, 90) if bars > 2 else ((255, 190, 40) if bars > 1 else (255, 70, 60))
        for k in range(5):
            cell_rect = (body.left + 5 + k * 7, body.top + 6, 5, body.h - 12)
            pygame.draw.rect(self.canvas, col if k < bars else (60, 60, 66), cell_rect)
        self.glow_dot(x, y, 22, col, 0.5)

    # ------------------------------------------------------------ efectos
    def puff(self, alpha):
        alpha = int(alpha) // 16 * 16
        if alpha not in self.puffs:
            s = pygame.Surface((40, 40), pygame.SRCALPHA)
            for k in range(5):
                pygame.draw.circle(s, (150, 150, 156, max(0, alpha // 5)), (20, 20), 20 - k * 3)
            self.puffs[alpha] = s
        return self.puffs[alpha]

    def on_event(self, ev):
        kind = ev["type"]
        if kind in ("eat", "bonus"):
            x, y = cell_center(*ev["pos"])
            if kind == "bonus":
                x += CELL / 2
            for _ in range(10 if kind == "eat" else 18):
                a = random.uniform(0, math.tau)
                v = random.uniform(120, 300)
                self.effects.append(["spark", x, y, math.cos(a) * v, math.sin(a) * v, 0.35, 0.35, None])
            label = random.choice(POPS) if kind == "eat" else f"+{ev['points']}"
            self.effects.append(["text", x, y - 28, 0, -40, 0.9, 0.9, label])
        elif kind == "die":
            x, y = cell_center(*ev["pos"])
            for _ in range(24):                                     # cortocircuito
                a = random.uniform(0, math.tau)
                v = random.uniform(150, 380)
                self.effects.append(["spark", x, y, math.cos(a) * v, math.sin(a) * v, 0.5, 0.5, None])
            for _ in range(7):
                self.effects.append(["smoke", x + random.uniform(-10, 10), y, random.uniform(-15, 15),
                                     random.uniform(-70, -40), 1.6, 1.6, random.uniform(0.8, 1.4)])
            self.effects.append(["text", x, y - 34, 0, -30, 1.3, 1.3, "¡CORTO!"])
            self.shake = 0.45
            self.flash = 0.25
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
            if e[0] == "spark":
                e[3] *= 0.9
                e[4] = e[4] * 0.9 + 400 * s
            e[5] -= s
        self.effects = [e for e in self.effects if e[5] > 0]

    def draw_effects(self):
        for kind, x, y, vx, vy, life, life_max, extra in self.effects:
            k = life / life_max
            if kind == "spark":
                tail = (x - vx * 0.03, y - vy * 0.03)
                col = mix((255, 255, 255), self.pulse, 1 - k)
                pygame.draw.line(self.canvas, col, tail, (x, y), 2)
                self.glow_dot(x, y, 10, self.pulse, k)
            elif kind == "smoke":
                img = self.puff(170 * k)
                size = int(40 * extra * (1.6 - k * 0.6))
                img = pygame.transform.smoothscale(img, (size, size))
                self.canvas.blit(img, img.get_rect(center=(x, y)))
            else:
                self.text(extra, self.font_mid, SILK, center=(x, y))

    # ------------------------------------------------------------ texto, displays y LCD
    def text(self, s, font, color, shadow=True, **anchor):
        img = font.render(s, True, color)
        rect = img.get_rect(**anchor)
        if shadow:
            self.canvas.blit(font.render(s, True, (0, 0, 0)), rect.move(2, 2))
        self.canvas.blit(img, rect)
        return rect

    def seg_display(self, value, digits, x, y, h=40):
        w = h * 0.5
        gap = w * 0.55
        box = pygame.Rect(x - 10, y - 8, digits * (w + gap) - gap + 20, h + 16)
        pygame.draw.rect(self.canvas, (10, 10, 12), box, 0, 4)
        pygame.draw.rect(self.canvas, (60, 60, 66), box, 2, 4)
        s = str(value).rjust(digits, "0")[-digits:]
        for i, ch in enumerate(s):
            seven_seg(self.canvas, x + i * (w + gap), y, w, h, ch, SEG_RED, (52, 16, 14), t=max(3, h // 9))
            self.glow_dot(x + i * (w + gap) + w / 2, y + h / 2, h * 0.6, SEG_RED, 0.35)
        return box

    def lcd(self, w, h, cy=None):
        """Panel = modulo LCD de caracteres, con su placa y tornillos."""
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 130))
        self.canvas.blit(veil, (0, 0))
        pcb = pygame.Rect(0, 0, w + 40, h + 40)
        pcb.center = (W // 2, cy or H // 2)
        pygame.draw.rect(self.canvas, (8, 8, 10), pcb.move(4, 6), 0, 6)
        pygame.draw.rect(self.canvas, shade(self.board, 1.1), pcb, 0, 6)
        for cx, cy2 in (pcb.topleft, pcb.topright, pcb.bottomleft, pcb.bottomright):
            px, py = cx + (12 if cx == pcb.left else -12), cy2 + (12 if cy2 == pcb.top else -12)
            pygame.draw.circle(self.canvas, GOLD, (px, py), 7)
            pygame.draw.circle(self.canvas, (14, 14, 16), (px, py), 4)
        for k in range(16):                                         # conector de 16 pines arriba
            pygame.draw.circle(self.canvas, GOLD, (pcb.centerx - 120 + k * 16, pcb.top + 8), 3)
        bezel = pygame.Rect(0, 0, w, h)
        bezel.center = pcb.center
        bezel.y += 6
        pygame.draw.rect(self.canvas, (24, 24, 28), bezel, 0, 4)
        glass = bezel.inflate(-20, -20)
        pygame.draw.rect(self.canvas, LCD_BG, glass)
        for x in range(glass.left + 4, glass.right - 4, 14):        # celdas de caracter apenas visibles
            for y in range(glass.top + 4, glass.bottom - 4, 22):
                pygame.draw.rect(self.canvas, shade(LCD_BG, 0.95), (x, y, 11, 19))
        return glass

    def lcd_text(self, s, font, y, glass, dim=False):
        col = shade(LCD_INK, 1.0) if not dim else mix(LCD_INK, LCD_BG, 0.55)
        img = font.render(s, True, col)
        self.canvas.blit(img, img.get_rect(center=(glass.centerx, y)))

    def draw_hud(self, g):
        self.seg_display(g.score, 4, FX + 12, 28, 40)
        self.text(g.maze["name"], self.font_mid, SILK, center=(W // 2, 48))
        if g.bonus:
            self.text(f"BAT {g.bonus_left:02d}", self.font_mid, SILK, midright=(W - FX, 48))
        else:
            self.text(f"MAPA {g.maze_idx}  NIVEL {g.level}", self.font_small, SILK, midright=(W - FX, 48))

    def draw_menu(self, app):
        self.canvas.blit(self.background(), (0, 0))
        r = self.text("SNAKE", self.font_title, SILK, center=(W // 2, 70))
        pygame.draw.line(self.canvas, GOLD, (r.left, r.bottom), (r.right, r.bottom), 4)
        for x in (r.left, r.right):
            pygame.draw.circle(self.canvas, GOLD, (x, r.bottom), 7)
            pygame.draw.circle(self.canvas, shade(self.board, 0.4), (x, r.bottom), 3)
        n = 12
        pts = [(W // 2 + 170 - k * 30, 156 + math.sin(self.t * 3 + k * 0.6) * 9) for k in range(n)]
        self.draw_snake([pts], (1, 0))
        rows = app.menu_rows()
        top = 210
        for i, (label, value) in enumerate(rows):
            y = top + i * 40
            sel = i == app.menu_sel
            led = self.pulse if sel else (50, 50, 56)               # LED de seleccion
            pygame.draw.circle(self.canvas, shade(led, 0.6), (W // 2 - 310, y), 9)
            pygame.draw.circle(self.canvas, led, (W // 2 - 310, y), 7)
            if sel:
                self.glow_dot(W // 2 - 310, y, 18, self.pulse)
            self.text(label, self.font_mid, SILK if sel else shade(SILK, 0.7), midleft=(W // 2 - 280, y))
            box = pygame.Rect(0, 0, 300, 34)
            box.center = (W // 2 + 160, y)
            pygame.draw.rect(self.canvas, self.pulse if sel else shade(SILK, 0.5), box, 2, 4)
            self.text(value, self.font_mid, SILK if sel else shade(SILK, 0.8), center=box.center)
        y_end = top + len(rows) * 40
        self.text(f"RECORD {app.game.record}", self.font_small, SILK, center=(W // 2, y_end + 4))
        if int(self.t * 2) % 2 == 0:
            self.text("> PRESIONA ESPACIO PARA JUGAR_", self.font_mid, self.pulse, center=(W // 2, H - 30))

    def draw(self, app):
        self.board_idx, self.pulse_idx = app.opt(0), app.opt(1)
        g = app.game
        self.glow.fill((0, 0, 0))

        if g.state == "menu":
            self.draw_menu(app)
            self.apply_glow()
        else:
            self.canvas.blit(self.static_layer(g), (0, 0))
            if g.food:
                self.draw_led(g.food)
            if g.bonus:
                self.draw_battery(g)
            dead = g.state in ("dying", "over")
            if g.snake:
                self.draw_snake(self.snake_runs(g), g.direction, dead)
            self.draw_effects()
            self.draw_hud(g)
            self.apply_glow()

        if g.state == "pause":
            glass = self.lcd(400, 190)
            self.lcd_text("** PAUSA **", self.font_big, glass.top + 36, glass)
            for i, (s, sel) in enumerate(pause_items(app)):
                y = glass.top + 96 + i * 40
                self.mark_pause(i, y)
                self.lcd_text(s, self.font_mid, y, glass, dim=not sel)
        elif g.state == "stage":
            glass = self.lcd(520, 190)
            self.lcd_text("CIRCUITO CERRADO", self.font_mid, glass.top + 30, glass)
            self.lcd_text(f"{g.maze_idx}:{g.maze['name']}", self.font_big, glass.centery + 4, glass)
            self.lcd_text(f"PUNTOS {g.score}", self.font_small, glass.bottom - 26, glass)
        elif g.state == "over":
            glass = self.lcd(540, 260, cy=H // 2 + 20)
            self.lcd_text("FALLA DEL SISTEMA", self.font_mid, glass.top + 28, glass)
            self.lcd_text(f"{g.score}", self.font_title, glass.top + 100, glass)
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    self.lcd_text("NUEVO RECORD!", self.font_mid, glass.top + 168, glass)
            else:
                self.lcd_text(f"RECORD {g.record}", self.font_small, glass.top + 168, glass, dim=True)
            self.lcd_text("ESPACIO:OTRA VEZ  ESC:MENU", self.font_small, glass.bottom - 24, glass)

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((*mix(self.pulse, (255, 255, 255), 0.6), int(170 * self.flash / 0.5)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.45 * 9)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((8, 8, 10))
        self.screen.blit(self.canvas, (ox, oy))
