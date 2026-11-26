"""Estilo NEON: lineas brillantes sobre fondo oscuro, con bloom, chispas y temblor."""

import math
import random

import pygame

from game import COLS, ROWS, BONUS_TICKS, UP, DOWN, LEFT, RIGHT
from styles.base import Renderer, pause_items, WIDTH as W, HEIGHT as H

CELL = 32
FX, FY = 32, 96                 # esquina del tablero
FW, FH = COLS * CELL, ROWS * CELL

THEMES = [
    ("SYNTHWAVE", {"bg": ((10, 2, 28), (44, 6, 60)), "grid": (110, 40, 180),
                   "head": (0, 255, 240), "tail": (255, 50, 210), "food": (255, 70, 150),
                   "wall": (170, 90, 255), "bonus": (255, 215, 70),
                   "text": (245, 235, 255), "dim": (160, 120, 210)}),
    ("TOXICO", {"bg": ((2, 14, 6), (8, 38, 14)), "grid": (30, 120, 50),
                "head": (210, 255, 60), "tail": (20, 210, 130), "food": (255, 100, 40),
                "wall": (60, 255, 130), "bonus": (255, 240, 90),
                "text": (225, 255, 225), "dim": (120, 180, 120)}),
    ("FUEGO", {"bg": ((18, 2, 2), (58, 12, 4)), "grid": (130, 35, 10),
               "head": (255, 235, 100), "tail": (255, 50, 20), "food": (90, 220, 255),
               "wall": (255, 120, 30), "bonus": (255, 255, 210),
               "text": (255, 238, 220), "dim": (210, 140, 110)}),
    ("HIELO", {"bg": ((2, 8, 24), (8, 30, 62)), "grid": (40, 90, 160),
               "head": (235, 250, 255), "tail": (60, 140, 255), "food": (255, 120, 220),
               "wall": (120, 200, 255), "bonus": (255, 240, 130),
               "text": (232, 246, 255), "dim": (140, 175, 215)}),
]


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def scale_color(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def center(c, r):
    return FX + c * CELL + CELL // 2, FY + r * CELL + CELL // 2


def star_points(cx, cy, r_out, r_in, rot):
    pts = []
    for k in range(10):
        a = rot + k * math.pi / 5 - math.pi / 2
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


class NeonRenderer(Renderer):
    NAME = "NEON"
    KEY = "neon"
    OPTIONS = [("TEMA", [t[0] for t in THEMES])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H), 0, 32)
        self.glow = pygame.Surface((W, H), 0, 32)     # lo que brilla se dibuja aqui tambien
        self.font_title = pygame.font.Font(None, 150)
        self.font_big = pygame.font.Font(None, 72)
        self.font_mid = pygame.font.Font(None, 44)
        self.font_small = pygame.font.Font(None, 32)
        self.bg_cache = {}
        self.theme_idx = -1
        self.th = THEMES[0][1]
        self.t = 0.0
        self.particles = []      # [x, y, vx, vy, vida, vida_max, color, tamano]
        self.floaters = []       # textos flotantes: [x, y, texto, vida, color]
        self.shake = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------ fondo
    def background(self, idx):
        if idx not in self.bg_cache:
            th = THEMES[idx][1]
            bg = pygame.Surface((W, H), 0, 32)
            top, bot = th["bg"]
            for y in range(H):
                pygame.draw.line(bg, lerp(top, bot, y / H), (0, y), (W, y))
            rnd = random.Random(7)
            for _ in range(90):                       # estrellitas
                x, y = rnd.randrange(W), rnd.randrange(H)
                bg.set_at((x, y), lerp(top, th["text"], rnd.uniform(0.2, 0.7)))
            field = pygame.Rect(FX, FY, FW, FH)
            bg.fill(scale_color(top, 0.6), field)
            grid = lerp(top, th["grid"], 0.35)
            for c in range(COLS + 1):
                x = FX + c * CELL
                pygame.draw.line(bg, grid, (x, FY), (x, FY + FH))
            for r in range(ROWS + 1):
                y = FY + r * CELL
                pygame.draw.line(bg, grid, (FX, y), (FX + FW, y))
            self.bg_cache[idx] = bg
        return self.bg_cache[idx]

    # ------------------------------------------------------------ primitivas con brillo
    def rect(self, color, rect, width=0, radius=6, glow=True):
        pygame.draw.rect(self.canvas, color, rect, width, radius)
        if glow:
            g = pygame.Rect(rect).inflate(6, 6)
            pygame.draw.rect(self.glow, color, g, width + 4 if width else 0, radius + 3)

    def circle(self, color, pos, radius, glow=True):
        pygame.draw.circle(self.canvas, color, pos, radius)
        if glow:
            pygame.draw.circle(self.glow, color, pos, radius + 5)

    def text(self, s, font, color, glow=True, **anchor):
        surf = font.render(s, True, color)
        rect = surf.get_rect(**anchor)
        self.canvas.blit(surf, rect)
        if glow:
            self.glow.blit(surf, rect)
        return rect

    def apply_glow(self):
        small = pygame.transform.smoothscale(self.glow, (W // 4, H // 4))
        small = pygame.transform.box_blur(small, 3)
        big = pygame.transform.smoothscale(small, (W, H))
        self.canvas.blit(big, (0, 0), special_flags=pygame.BLEND_ADD)

    # ------------------------------------------------------------ efectos
    def burst(self, pos, color, n, speed=260, size=4):
        x, y = pos
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1.0) * speed
            life = random.uniform(0.35, 0.8)
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, life, life,
                                   color, random.randint(2, size)])

    def on_event(self, ev):
        th = self.th
        kind = ev["type"]
        if kind == "eat":
            self.burst(center(*ev["pos"]), th["food"], 18)
        elif kind == "bonus":
            c, r = ev["pos"]
            x, y = center(c, r)
            self.burst((x + CELL // 2, y), th["bonus"], 36, speed=340, size=5)
            self.floaters.append([x + CELL // 2, y - 10, f"+{ev['points']}", 1.0, th["bonus"]])
        elif kind == "die":
            self.burst(center(*ev["pos"]), th["head"], 40, speed=380, size=6)
            self.shake = 0.45
        elif kind == "stage":
            self.flash = 0.5

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        alive = []
        for p in self.particles:
            p[0] += p[2] * s
            p[1] += p[3] * s
            p[2] *= 0.92
            p[3] *= 0.92
            p[4] -= s
            if p[4] > 0:
                alive.append(p)
        self.particles = alive
        for f in self.floaters:
            f[1] -= 40 * s
            f[3] -= s
        self.floaters = [f for f in self.floaters if f[3] > 0]

    # ------------------------------------------------------------ piezas del juego
    def draw_frame(self, solid):
        th = self.th
        rect = pygame.Rect(FX - 6, FY - 6, FW + 12, FH + 12)
        if solid:
            self.rect(th["wall"], rect, width=3, radius=10)
            return
        dash, gap = 18, 12                       # se atraviesa: marco punteado
        for x in range(rect.left, rect.right, dash + gap):
            w = min(dash, rect.right - x)
            self.rect(th["dim"], (x, rect.top, w, 3), radius=1)
            self.rect(th["dim"], (x, rect.bottom - 3, w, 3), radius=1)
        for y in range(rect.top, rect.bottom, dash + gap):
            h = min(dash, rect.bottom - y)
            self.rect(th["dim"], (rect.left, y, 3, h), radius=1)
            self.rect(th["dim"], (rect.right - 3, y, 3, h), radius=1)

    def draw_walls(self, rects):
        th = self.th
        fill = lerp(th["bg"][0], th["wall"], 0.18)
        for c, r, w, h in rects:
            rect = pygame.Rect(FX + c * CELL + 3, FY + r * CELL + 3, w * CELL - 6, h * CELL - 6)
            pygame.draw.rect(self.canvas, fill, rect, 0, 6)
            self.rect(th["wall"], rect, width=3, radius=6)

    def draw_snake(self, cells, direction, pos_of=center, seg=None):
        th = self.th
        n = len(cells)
        seg = seg or CELL - 8
        thick = seg - 6
        for i in range(n - 1, -1, -1):          # de la cola a la cabeza
            col = lerp(th["head"], th["tail"], i / max(1, n - 1))
            x, y = pos_of(*cells[i])
            if i > 0:                             # union con el segmento de adelante
                px, py = pos_of(*cells[i - 1])
                if abs(px - x) + abs(py - y) <= CELL * 1.5:   # no unir al cruzar el borde
                    pygame.draw.line(self.canvas, col, (x, y), (px, py), thick)
                    pygame.draw.line(self.glow, col, (x, y), (px, py), thick + 8)
            size = seg + 4 if i == 0 else seg
            self.rect(col, pygame.Rect(x - size // 2, y - size // 2, size, size), radius=9)

        # ojos
        hx, hy = pos_of(*cells[0])
        dx, dy = direction
        px, py = -dy, dx
        for side in (-1, 1):
            ex = hx + dx * 5 + px * 7 * side
            ey = hy + dy * 5 + py * 7 * side
            pygame.draw.circle(self.canvas, (255, 255, 255), (ex, ey), 5)
            pygame.draw.circle(self.canvas, th["bg"][0], (ex + dx * 2, ey + dy * 2), 3)

    def draw_food(self, pos):
        x, y = center(*pos)
        pulse = 1 + 0.15 * math.sin(self.t * 7)
        self.circle(self.th["food"], (x, y), int(9 * pulse))
        pygame.draw.circle(self.canvas, (255, 255, 255), (x - 3, y - 3), 3)

    def draw_bonus(self, g):
        c, r = g.bonus
        x, y = center(c, r)
        x += CELL // 2
        col = self.th["bonus"]
        pts = star_points(x, y, 15, 7, self.t * 2.5)
        pygame.draw.polygon(self.canvas, col, pts)
        pygame.draw.polygon(self.glow, col, star_points(x, y, 20, 10, self.t * 2.5))
        frac = g.bonus_left / BONUS_TICKS
        arc = pygame.Rect(x - 24, y - 24, 48, 48)
        pygame.draw.arc(self.canvas, col, arc, math.pi / 2, math.pi / 2 + math.tau * frac, 3)
        pygame.draw.arc(self.glow, col, arc, math.pi / 2, math.pi / 2 + math.tau * frac, 6)

    def draw_effects(self):
        for x, y, _, _, life, life_max, col, size in self.particles:
            k = life / life_max
            c = scale_color(col, 0.4 + 0.6 * k)
            pygame.draw.circle(self.canvas, c, (int(x), int(y)), max(1, int(size * k + 1)))
            pygame.draw.circle(self.glow, c, (int(x), int(y)), int(size * k + 3))
        for x, y, s, life, col in self.floaters:
            self.text(s, self.font_mid, scale_color(col, min(1, life * 1.5)), center=(x, y))

    def draw_hud(self, g):
        th = self.th
        self.text(f"{g.score:04d}", self.font_big, th["head"], topleft=(FX, 24))
        self.text(g.maze["name"], self.font_small, th["dim"], glow=False, center=(W // 2, 48))
        if g.bonus:
            x, y = W - FX - 90, 48
            pygame.draw.polygon(self.canvas, th["bonus"], star_points(x, y, 14, 6, self.t * 2.5))
            self.text(f"{g.bonus_left:02d}", self.font_big, th["bonus"], midleft=(x + 24, y + 2))
        else:
            self.text(f"MAPA {g.maze_idx}  NIVEL {g.level}", self.font_small, th["text"],
                      midright=(W - FX, 48))

    def draw_field(self, g, show_snake=True):
        self.draw_frame(g.maze["border"])
        self.draw_walls(g.wall_rects)
        if g.food:
            self.draw_food(g.food)
        if g.bonus:
            self.draw_bonus(g)
        if show_snake and g.snake:
            self.draw_snake(g.snake, g.direction)
        self.draw_effects()
        self.draw_hud(g)

    def panel(self, w, h):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, H // 2)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.canvas.blit(shade, (0, 0))
        pygame.draw.rect(self.canvas, scale_color(self.th["bg"][0], 1.0), rect, 0, 16)
        self.rect(self.th["head"], rect, width=3, radius=16)
        return rect

    # ------------------------------------------------------------ menu
    def draw_menu(self, app):
        th = self.th
        self.text("SNAKE", self.font_title, th["head"], center=(W // 2, 88))
        # serpiente de muestra ondulando
        n = 16
        pts = [(W // 2 - n * 13 + k * 26, 172 + math.sin(self.t * 3 - k * 0.55) * 10)
               for k in range(n)]
        cells = [(k,) for k in range(n - 1, -1, -1)]
        self.draw_snake(cells, RIGHT, pos_of=lambda k: (int(pts[k][0]), int(pts[k][1])), seg=22)

        rows = app.menu_rows()
        top = 232
        for i, (label, value) in enumerate(rows):
            y = top + i * 46
            sel = i == app.menu_sel
            if sel:
                bar = pygame.Rect(W // 2 - 300, y - 20, 600, 40)
                pygame.draw.rect(self.canvas, lerp(th["bg"][0], th["head"], 0.15), bar, 0, 10)
                self.rect(th["head"], bar, width=2, radius=10)
                self.text("<", self.font_mid, th["head"], center=(W // 2 + 60, y))
                self.text(">", self.font_mid, th["head"], center=(W // 2 + 260, y))
            self.text(label, self.font_mid, th["text"] if sel else th["dim"], glow=sel,
                      midleft=(W // 2 - 270, y))
            self.text(value, self.font_mid, th["text"] if sel else th["dim"], glow=sel,
                      center=(W // 2 + 160, y))
        y_end = top + len(rows) * 46
        self.text(f"RECORD {app.game.record:04d}", self.font_small, th["bonus"],
                  center=(W // 2, y_end + 24))
        if int(self.t * 2) % 2 == 0:
            self.text("ESPACIO PARA JUGAR", self.font_mid, th["food"], center=(W // 2, H - 36))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        idx = app.opt(0)
        if idx != self.theme_idx:
            self.theme_idx = idx
            self.th = THEMES[idx][1]
        th = self.th
        g = app.game

        self.canvas.blit(self.background(idx), (0, 0))
        self.glow.fill((0, 0, 0))

        if g.state == "menu":
            self.draw_menu(app)
        elif g.state in ("play", "pause"):
            self.draw_field(g)
        elif g.state == "dying":
            self.draw_field(g, show_snake=(g.state_time // 100) % 2 == 0)
        elif g.state in ("stage", "over"):
            self.draw_field(g, show_snake=g.state == "stage")

        self.apply_glow()

        # paneles encima del brillo (para que se lean bien)
        if g.state == "pause":
            self.panel(420, 250)
            self.text("PAUSA", self.font_big, th["head"], center=(W // 2, H // 2 - 64))
            for i, (s, sel) in enumerate(pause_items(app)):
                self.mark_pause(i, H // 2 + 16 + i * 50)
                self.text(s, self.font_mid, th["head"] if sel else th["dim"],
                          center=(W // 2, H // 2 + 16 + i * 50))
        elif g.state == "stage":
            self.panel(520, 260)
            self.text("MAPA SUPERADO!", self.font_mid, th["bonus"], center=(W // 2, H // 2 - 80))
            self.text(f"MAPA {g.maze_idx}: {g.maze['name']}", self.font_big, th["head"],
                      center=(W // 2, H // 2))
            self.text(f"PUNTOS {g.score:04d}", self.font_small, th["text"],
                      center=(W // 2, H // 2 + 76))
        elif g.state == "over":
            self.panel(540, 320)
            self.text("FIN DEL JUEGO", self.font_mid, th["food"], center=(W // 2, H // 2 - 110))
            self.text(f"{g.score:04d}", self.font_title, th["head"], center=(W // 2, H // 2 - 20))
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    self.text("NUEVO RECORD!", self.font_mid, th["bonus"],
                              center=(W // 2, H // 2 + 66))
            else:
                self.text(f"RECORD {g.record:04d}", self.font_small, th["dim"],
                          center=(W // 2, H // 2 + 66))
            self.text("ESPACIO: OTRA VEZ    ESC: MENU", self.font_small, th["text"],
                      center=(W // 2, H // 2 + 120))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((*th["text"], int(160 * self.flash / 0.5)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = self.shake / 0.45 * 10
            ox, oy = random.randint(-int(k), int(k)), random.randint(-int(k), int(k))
        self.screen.fill(th["bg"][0])
        self.screen.blit(self.canvas, (ox, oy))
