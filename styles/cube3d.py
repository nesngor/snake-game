"""Estilo 3D: tablero en perspectiva con cubos, sombras, gema giratoria y movimiento suave."""

import math
import random

import pygame

from game import COLS, ROWS, MAZES, BONUS_TICKS, UP, DOWN, LEFT, RIGHT
from styles.base import Renderer, WIDTH as W, HEIGHT as H

HUD_H = 64                     # espacio arriba para el marcador
RING = 0.4                     # grosor del muro perimetral
LIGHT = (-0.45, -0.35, 0.82)   # direccion hacia la luz (izquierda, frente, arriba)
SHADOW_OFF = (0.16, 0.14)      # desplazamiento de las sombras en el piso

THEMES = [
    ("CLASICO", {"sky": ((176, 206, 250), (236, 242, 255)), "tiles": ((236, 238, 246), (220, 225, 238)),
                 "slab": (128, 140, 178), "wall": (118, 128, 176), "head": (96, 210, 96),
                 "tail": (36, 140, 100), "food": (232, 56, 60), "gem": (70, 196, 255),
                 "accent": (60, 90, 200)}),
    ("ATARDECER", {"sky": ((255, 150, 110), (96, 62, 146)), "tiles": ((252, 222, 192), (240, 204, 172)),
                   "slab": (150, 84, 110), "wall": (206, 110, 92), "head": (255, 222, 80),
                   "tail": (240, 96, 64), "food": (120, 66, 210), "gem": (255, 90, 170),
                   "accent": (230, 90, 80)}),
    ("OCEANO", {"sky": ((20, 64, 128), (104, 184, 232)), "tiles": ((92, 202, 222), (80, 186, 210)),
                "slab": (28, 88, 140), "wall": (240, 228, 196), "head": (255, 150, 64),
                "tail": (255, 80, 120), "food": (255, 232, 80), "gem": (255, 255, 255),
                "accent": (20, 120, 200)}),
    ("NOCHE", {"sky": ((8, 8, 28), (44, 32, 78)), "tiles": ((62, 62, 94), (54, 54, 84)),
               "slab": (30, 30, 52), "wall": (112, 92, 176), "head": (120, 255, 200),
               "tail": (60, 156, 255), "food": (255, 90, 124), "gem": (255, 220, 90),
               "accent": (120, 90, 220)}),
]

# Camara: (nombre, distancia detras del borde cercano, altura)
CAMERAS = [("NORMAL", 10, 26), ("BAJA", 8, 13), ("ALTA", 4, 40)]

MENU_MAZE = {"name": "MENU", "border": True, "walls": [], "start": (8, 7, RIGHT)}


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def normalize(v):
    n = math.sqrt(sum(x * x for x in v)) or 1
    return tuple(x / n for x in v)


LIGHT = normalize(LIGHT)


def world_y(r):
    """Fila del tablero -> Y del mundo (fila 0 al fondo, Y crece hacia el fondo)."""
    return ROWS - 1 - r


class Camera:
    def __init__(self, back, height):
        self.cx, self.cy, self.cz = COLS / 2, -back, height
        dy, dz = ROWS / 2 - self.cy, height
        pitch = math.atan2(dz, dy)
        self.cos, self.sin = math.cos(pitch), math.sin(pitch)
        # ajustar escala y centro para que todo el tablero quepa en pantalla
        self.F, self.ox, self.oy = 1.0, 0.0, 0.0
        pts = [self.project(x, y, z) for x in (-RING, COLS + RING)
               for y in (-RING, ROWS + RING) for z in (-0.6, 1.1)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        avail_w, avail_h = W - 40, H - HUD_H - 12
        self.F = min(avail_w / (max(xs) - min(xs)), avail_h / (max(ys) - min(ys)))
        self.ox = W / 2 - self.F * (min(xs) + max(xs)) / 2
        self.oy = HUD_H + (avail_h - self.F * (max(ys) - min(ys))) / 2 - self.F * min(ys)

    def depth(self, x, y, z):
        return (y - self.cy) * self.cos - (z - self.cz) * self.sin

    def project(self, x, y, z):
        dx, dy, dz = x - self.cx, y - self.cy, z - self.cz
        depth = dy * self.cos - dz * self.sin
        up = dy * self.sin + dz * self.cos
        return (self.ox + self.F * dx / depth, self.oy - self.F * up / depth)

    def scale_at(self, x, y, z):
        """Pixeles por unidad del mundo en ese punto."""
        return self.F / self.depth(x, y, z)


class Cube3DRenderer(Renderer):
    NAME = "3D"
    KEY = "3d"
    OPTIONS = [("TEMA", [t[0] for t in THEMES]), ("CAMARA", [c[0] for c in CAMERAS])]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        self.shadow = pygame.Surface((W, H))
        self.shadow.set_colorkey((255, 0, 255))
        self.shadow.set_alpha(70)
        self.font_big = pygame.font.Font(None, 64)
        self.font_mid = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 30)
        self.cameras = [Camera(b, h) for _, b, h in CAMERAS]
        self.cache = {}
        self.th = THEMES[0][1]
        self.cam = self.cameras[0]
        self.t = 0.0
        self.particles = []     # [x, y, z, vx, vy, vz, vida, color]
        self.floaters = []      # [x, y, z, texto, vida]
        self.shake = 0.0
        self.flash = 0.0

    # ------------------------------------------------------------ geometria
    def poly(self, surf, color, pts3d, outline=True):
        pts = [self.cam.project(*p) for p in pts3d]
        pygame.draw.polygon(surf, color, pts)
        if outline:
            pygame.draw.polygon(surf, shade(color, 0.72), pts, 1)

    def box(self, surf, x0, y0, z0, x1, y1, z1, color, cull=()):
        cam = self.cam
        if cam.cx < x0 and "l" not in cull:
            self.poly(surf, shade(color, 0.62),
                      [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)])
        if cam.cx > x1 and "r" not in cull:
            self.poly(surf, shade(color, 0.62),
                      [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)])
        if "f" not in cull:
            self.poly(surf, shade(color, 0.8),
                      [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)])
        self.poly(surf, color, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])

    def floor_shadow(self, surf, x0, y0, x1, y1):
        dx, dy = SHADOW_OFF
        pts = [(x0 + dx, y0 - dy, 0.01), (x1 + dx, y0 - dy, 0.01),
               (x1 + dx, y1 - dy, 0.01), (x0 + dx, y1 - dy, 0.01)]
        pygame.draw.polygon(surf, (0, 0, 0), [self.cam.project(*p) for p in pts])

    # ------------------------------------------------------------ escenario estatico
    def static_layers(self, theme_idx, cam_idx, maze, maze_key):
        """Fondo (cielo, base, piso, muros perimetrales lejanos, sombras de muros)
        y el muro perimetral cercano, que va encima de todo."""
        key = (theme_idx, cam_idx, maze_key)
        if key in self.cache:
            return self.cache[key]
        th = self.th
        bg = pygame.Surface((W, H))
        top, bottom = th["sky"]
        for y in range(H):
            pygame.draw.line(bg, lerp(top, bottom, y / H), (0, y), (W, y))

        # base del tablero
        self.box(bg, -RING, -RING, -0.6, COLS + RING, ROWS + RING, 0, th["slab"])
        a, b = th["tiles"]
        for r in range(ROWS):
            for c in range(COLS):
                y = world_y(r)
                self.poly(bg, a if (c + r) % 2 else b,
                          [(c, y, 0), (c + 1, y, 0), (c + 1, y + 1, 0), (c, y + 1, 0)], outline=False)

        # sombras de muros fijos
        sh = pygame.Surface((W, H))
        sh.fill((255, 0, 255))
        sh.set_colorkey((255, 0, 255))
        sh.set_alpha(70)
        cells = set()
        for c, r, w, h in maze["walls"]:
            for dc in range(w):
                for dr in range(h):
                    cells.add((c + dc, r + dr))
        for c, r in cells:
            y = world_y(r)
            self.floor_shadow(sh, c, y, c + 1, y + 1)
        bg.blit(sh, (0, 0))

        front = pygame.Surface((W, H), pygame.SRCALPHA)
        wall = th["wall"]
        if maze["border"]:
            hgt = 0.5
            self.box(bg, -RING, ROWS, 0, COLS + RING, ROWS + RING, hgt, wall)       # fondo
            self.box(bg, -RING, 0, 0, 0, ROWS, hgt, wall)                            # izquierda
            self.box(bg, COLS, 0, 0, COLS + RING, ROWS, hgt, wall)                   # derecha
            self.box(front, -RING, -RING, 0, COLS + RING, 0, hgt, wall)              # cercano
        else:   # se atraviesa: borde con guiones de color
            acc = th["accent"]
            for c in range(0, COLS, 2):
                self.poly(bg, acc, [(c + 0.2, -0.25, 0.01), (c + 0.8, -0.25, 0.01),
                                    (c + 0.8, -0.1, 0.01), (c + 0.2, -0.1, 0.01)], False)
                self.poly(bg, acc, [(c + 0.2, ROWS + 0.1, 0.01), (c + 0.8, ROWS + 0.1, 0.01),
                                    (c + 0.8, ROWS + 0.25, 0.01), (c + 0.2, ROWS + 0.25, 0.01)], False)
            for r in range(0, ROWS, 2):
                self.poly(bg, acc, [(-0.25, r + 0.2, 0.01), (-0.1, r + 0.2, 0.01),
                                    (-0.1, r + 0.8, 0.01), (-0.25, r + 0.8, 0.01)], False)
                self.poly(bg, acc, [(COLS + 0.1, r + 0.2, 0.01), (COLS + 0.25, r + 0.2, 0.01),
                                    (COLS + 0.25, r + 0.8, 0.01), (COLS + 0.1, r + 0.8, 0.01)], False)
        self.cache[key] = (bg, front)
        return bg, front

    # ------------------------------------------------------------ objetos dinamicos
    def snake_items(self, cells, prev_cells, direction, frac, dead=False):
        """Devuelve [(profundidad, funcion_dibujar)] para cada segmento, interpolando."""
        th = self.th
        n = len(cells)
        items = []
        positions = []
        for i, (c, r) in enumerate(cells):
            pc, pr = prev_cells[i]
            if abs(pc - c) > 1 or abs(pr - r) > 1:    # cruzo el borde: no interpolar
                pc, pr = c, r
            fc = pc + (c - pc) * frac
            fr = pr + (r - pr) * frac
            positions.append((fc, fr))

        for i, (fc, fr) in enumerate(positions):
            col = lerp(th["head"], th["tail"], i / max(1, n - 1))
            if dead:
                col = lerp(col, (120, 120, 130), 0.7)
            inset = 0.05 if i == 0 else 0.1 + 0.08 * (i / max(1, n - 1))
            height = 0.85 if i == 0 else 0.75 - 0.15 * (i / max(1, n - 1))
            x0, y0 = fc + inset, world_y(fr) + inset
            x1, y1 = fc + 1 - inset, world_y(fr) + 1 - inset
            d = self.cam.depth((x0 + x1) / 2, (y0 + y1) / 2, height / 2)

            def draw(surf, x0=x0, y0=y0, x1=x1, y1=y1, h=height, col=col, head=(i == 0)):
                self.box(surf, x0, y0, 0, x1, y1, h, col)
                if head:
                    self.draw_eyes(surf, x0, y0, x1, y1, h, direction, dead)
            items.append((d, draw))
            self.floor_shadow(self.shadow, x0, y0, x1, y1)
        return items

    def draw_eyes(self, surf, x0, y0, x1, y1, h, direction, dead):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        fx, fy = direction[0], -direction[1]          # adelante en el mundo
        sx, sy = -fy, fx                               # al costado
        for side in (-1, 1):
            ex = cx + fx * 0.2 + sx * 0.2 * side
            ey = cy + fy * 0.2 + sy * 0.2 * side
            p = self.cam.project(ex, ey, h + 0.01)
            k = self.cam.scale_at(ex, ey, h)
            if dead:
                s = max(2, int(k * 0.08))
                pygame.draw.line(surf, (40, 40, 50), (p[0] - s, p[1] - s), (p[0] + s, p[1] + s), 2)
                pygame.draw.line(surf, (40, 40, 50), (p[0] - s, p[1] + s), (p[0] + s, p[1] - s), 2)
            else:
                pygame.draw.circle(surf, (255, 255, 255), p, max(2, int(k * 0.11)))
                pp = self.cam.project(ex + fx * 0.04, ey + fy * 0.04, h + 0.01)
                pygame.draw.circle(surf, (20, 20, 30), pp, max(1, int(k * 0.06)))

    def food_item(self, cell):
        c, r = cell
        x, y = c + 0.5, world_y(r) + 0.5
        z = 0.45 + 0.08 * math.sin(self.t * 4)
        rad = 0.34
        self.floor_shadow(self.shadow, x - 0.25, y - 0.25, x + 0.25, y + 0.25)
        col = self.th["food"]

        def draw(surf):
            p = self.cam.project(x, y, z)
            k = self.cam.scale_at(x, y, z)
            pr = rad * k
            pygame.draw.circle(surf, shade(col, 0.7), p, pr)
            pygame.draw.circle(surf, col, (p[0] - pr * 0.12, p[1] - pr * 0.12), pr * 0.85)
            pygame.draw.circle(surf, lerp(col, (255, 255, 255), 0.5),
                               (p[0] - pr * 0.35, p[1] - pr * 0.35), pr * 0.3)
            stem = self.cam.project(x, y, z + rad + 0.12)
            top = self.cam.project(x, y, z + rad * 0.8)
            pygame.draw.line(surf, (100, 70, 40), top, stem, max(2, int(k * 0.06)))
        return self.cam.depth(x, y, z), draw

    def gem_item(self, g):
        c, r = g.bonus
        x, y = c + 1.0, world_y(r) + 0.5
        z = 0.75 + 0.1 * math.sin(self.t * 3)
        rad, hh = 0.5, 0.62
        self.floor_shadow(self.shadow, x - 0.35, y - 0.35, x + 0.35, y + 0.35)
        col = self.th["gem"]
        a0 = self.t * 1.8
        ring = [(x + math.cos(a0 + k * math.pi / 2) * rad,
                 y + math.sin(a0 + k * math.pi / 2) * rad, z) for k in range(4)]
        top, bot = (x, y, z + hh), (x, y, z - hh)
        cam_pos = (self.cam.cx, self.cam.cy, self.cam.cz)

        def draw(surf):
            faces = []
            for k in range(4):
                a, b = ring[k], ring[(k + 1) % 4]
                for apex in (top, bot):
                    tri = (a, b, apex)
                    u = [b[j] - a[j] for j in range(3)]
                    v = [apex[j] - a[j] for j in range(3)]
                    nrm = normalize((u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                                     u[0] * v[1] - u[1] * v[0]))
                    cen = [sum(p[j] for p in tri) / 3 for j in range(3)]
                    out = [cen[j] - (x, y, z)[j] for j in range(3)]
                    if sum(nrm[j] * out[j] for j in range(3)) < 0:
                        nrm = tuple(-n for n in nrm)       # normal hacia afuera
                    to_cam = [cam_pos[j] - cen[j] for j in range(3)]
                    if sum(nrm[j] * to_cam[j] for j in range(3)) < 0:
                        continue                           # cara que no mira a la camara
                    light = max(0.0, sum(nrm[j] * LIGHT[j] for j in range(3)))
                    faces.append((self.cam.depth(*cen), tri, 0.55 + 0.6 * light))
            for _, tri, k in sorted(faces, reverse=True):
                self.poly(surf, shade(col, k), list(tri))
            # destello
            if int(self.t * 5) % 4 == 0:
                p = self.cam.project(x - 0.1, y, z + 0.25)
                pygame.draw.circle(surf, (255, 255, 255), p, 3)
        return self.cam.depth(x, y, z), draw

    def wall_items(self, walls):
        items = []
        wall = self.th["wall"]
        for c, r in walls:
            y = world_y(r)
            cull = []
            if (c - 1, r) in walls:
                cull.append("l")
            if (c + 1, r) in walls:
                cull.append("r")
            if (c, r + 1) in walls:
                cull.append("f")
            d = self.cam.depth(c + 0.5, y + 0.5, 0.5)
            items.append((d, lambda s, c=c, y=y, cull=tuple(cull):
                          self.box(s, c, y, 0, c + 1, y + 1, 1.0, wall, cull)))
        return items

    # ------------------------------------------------------------ efectos
    def on_event(self, ev):
        kind = ev["type"]
        if kind in ("eat", "die"):
            c, r = ev["pos"]
            col = self.th["food"] if kind == "eat" else self.th["head"]
            n = 14 if kind == "eat" else 30
            for _ in range(n):
                a = random.uniform(0, math.tau)
                v = random.uniform(1.0, 3.0)
                self.particles.append([c + 0.5, world_y(r) + 0.5, 0.5, math.cos(a) * v,
                                       math.sin(a) * v, random.uniform(2, 5),
                                       random.uniform(0.5, 0.9), col])
            if kind == "die":
                self.shake = 0.4
        elif kind == "bonus":
            c, r = ev["pos"]
            for _ in range(28):
                a = random.uniform(0, math.tau)
                v = random.uniform(1.5, 3.5)
                self.particles.append([c + 1, world_y(r) + 0.5, 0.8, math.cos(a) * v,
                                       math.sin(a) * v, random.uniform(3, 6),
                                       random.uniform(0.6, 1.0), self.th["gem"]])
            self.floaters.append([c + 1, world_y(r) + 0.5, 1.2, f"+{ev['points']}", 1.0])
        elif kind == "stage":
            self.flash = 0.5

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for p in self.particles:
            p[0] += p[3] * s
            p[1] += p[4] * s
            p[2] += p[5] * s
            p[5] -= 12 * s
            if p[2] < 0:                 # rebote en el piso
                p[2], p[5] = 0, -p[5] * 0.4
            p[6] -= s
        self.particles = [p for p in self.particles if p[6] > 0]
        for f in self.floaters:
            f[2] += 0.8 * s
            f[4] -= s
        self.floaters = [f for f in self.floaters if f[4] > 0]

    # ------------------------------------------------------------ 2D: textos y paneles
    def text(self, s, font, color, shadow=True, **anchor):
        img = font.render(s, True, color)
        rect = img.get_rect(**anchor)
        if shadow:
            self.canvas.blit(font.render(s, True, (0, 0, 0)), rect.move(2, 2))
        self.canvas.blit(img, rect)
        return rect

    def pill(self, rect):
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (10, 14, 30, 150), surf.get_rect(), 0, rect.h // 2)
        self.canvas.blit(surf, rect)

    def panel(self, w, h, y=None):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, y or H // 2)
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 90))
        self.canvas.blit(veil, (0, 0))
        sh = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 90), sh.get_rect(), 0, 18)
        self.canvas.blit(sh, rect.move(6, 8))
        pygame.draw.rect(self.canvas, (250, 250, 255), rect, 0, 18)
        pygame.draw.rect(self.canvas, self.th["accent"], rect, 4, 18)
        return rect

    def draw_hud(self, g):
        white = (255, 255, 255)
        self.pill(pygame.Rect(16, 10, 170, 46))
        self.text(f"{g.score:04d}", self.font_big, white, center=(101, 34))
        name = g.maze["name"]
        w = self.font_small.size(name)[0] + 40
        self.pill(pygame.Rect(W // 2 - w // 2, 16, w, 34))
        self.text(name, self.font_small, white, center=(W // 2, 34))
        self.pill(pygame.Rect(W - 236, 10, 220, 46))
        if g.bonus:
            cx, cy = W - 190, 33
            pygame.draw.polygon(self.canvas, self.th["gem"],
                                [(cx, cy - 13), (cx + 11, cy), (cx, cy + 13), (cx - 11, cy)])
            self.text(f"{g.bonus_left:02d}", self.font_big, self.th["gem"], center=(W - 110, 34))
        else:
            self.text(f"MAPA {g.maze_idx}  NIVEL {g.level}", self.font_small, white,
                      center=(W - 126, 34))

    # ------------------------------------------------------------ escena
    def draw_scene(self, maze, maze_key, walls, snake, prev, direction, frac,
                   food=None, game=None, dead=False, show_snake=True):
        bg, front = self.static_layers(self.theme_idx, self.cam_idx, maze, maze_key)
        self.canvas.blit(bg, (0, 0))
        self.shadow.fill((255, 0, 255))
        items = self.wall_items(walls)
        if game:                                  # sombras de las rocas nuevas
            for c, r in game.rocks:
                self.floor_shadow(self.shadow, c, world_y(r), c + 1, world_y(r) + 1)
        if show_snake and snake:
            items += self.snake_items(snake, prev, direction, frac, dead)
        if food:
            items.append(self.food_item(food))
        if game and game.bonus:
            items.append(self.gem_item(game))
        self.canvas.blit(self.shadow, (0, 0))
        for _, draw in sorted(items, key=lambda it: -it[0]):
            draw(self.canvas)
        for x, y, z, _, _, _, life, col in self.particles:
            p = self.cam.project(x, y, z)
            s = max(2, int(self.cam.scale_at(x, y, z) * 0.1 * (0.5 + life)))
            self.canvas.fill(col, (p[0] - s / 2, p[1] - s / 2, s, s))
        self.canvas.blit(front, (0, 0))
        for x, y, z, s, life in self.floaters:
            self.text(s, self.font_big, self.th["gem"], center=self.cam.project(x, y, z))

    def menu_snake(self):
        """Serpiente de demostracion dando vueltas por el contorno del tablero."""
        path = ([(c, 0) for c in range(0, COLS - 1)] + [(COLS - 1, r) for r in range(0, ROWS - 1)]
                + [(c, ROWS - 1) for c in range(COLS - 1, 0, -1)] + [(0, r) for r in range(ROWS - 1, 0, -1)])
        speed = 7
        pos = self.t * speed
        p, frac = int(pos), pos - int(pos)
        n = len(path)
        cells = [path[(p - i) % n] for i in range(12)]
        prev = [path[(p - i - 1) % n] for i in range(12)]
        hc, hr = cells[0]
        pc, pr = prev[0]
        return cells, prev, (hc - pc, hr - pr), frac

    def draw_menu(self, app):
        th = self.th
        cells, prev, d, frac = self.menu_snake()
        self.draw_scene(MENU_MAZE, "menu", set(), cells, prev, d, frac)
        rows = app.menu_rows()
        box = self.panel(460, 70 + len(rows) * 44, y=H // 2 + 30)
        self.text("SNAKE 3D", self.font_big, (255, 255, 255), center=(W // 2, box.top - 40))
        for i, (label, value) in enumerate(rows):
            y = box.top + 40 + i * 44
            sel = i == app.menu_sel
            if sel:
                bar = pygame.Rect(box.left + 16, y - 19, box.w - 32, 38)
                pygame.draw.rect(self.canvas, lerp((255, 255, 255), th["accent"], 0.18), bar, 0, 10)
                self.text("<", self.font_mid, th["accent"], False, center=(box.left + 200, y))
                self.text(">", self.font_mid, th["accent"], False, center=(box.right - 30, y))
            color = th["accent"] if sel else (70, 76, 100)
            self.text(label, self.font_mid, color, False, midleft=(box.left + 30, y))
            self.text(value, self.font_mid, color, False, center=(box.left + 320, y))
        self.text(f"RECORD {app.game.record:04d}", self.font_small, (120, 120, 140), False,
                  center=(W // 2, box.bottom - 24))
        if int(self.t * 2) % 2 == 0:
            self.text("ESPACIO PARA JUGAR", self.font_mid, (255, 255, 255),
                      center=(W // 2, min(H - 18, box.bottom + 26)))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.theme_idx, self.cam_idx = app.opt(0), app.opt(1)
        self.th = THEMES[self.theme_idx][1]
        self.cam = self.cameras[self.cam_idx]
        g = app.game
        th = self.th

        if g.state == "menu":
            self.draw_menu(app)
        else:
            frac = g.move_fraction()
            prev = g.snake[1:] + g.snake[-1:]          # donde estaba cada segmento antes
            dead = g.state in ("dying", "over")
            show = not (g.state == "dying" and (g.state_time // 120) % 2 == 1)
            self.draw_scene(g.maze, g.maze_idx, g.walls, g.snake, prev, g.direction, frac,
                            g.food, g, dead, show)
            self.draw_hud(g)

        dark = (40, 44, 70)
        if g.state == "pause":
            self.panel(320, 120)
            self.text("PAUSA", self.font_big, th["accent"], False, center=(W // 2, H // 2))
        elif g.state == "stage":
            box = self.panel(520, 240)
            self.text("MAPA SUPERADO!", self.font_mid, th["accent"], False,
                      center=(W // 2, box.top + 50))
            self.text(f"MAPA {g.maze_idx}: {g.maze['name']}", self.font_big, dark, False,
                      center=(W // 2, box.centery))
            self.text(f"PUNTOS {g.score:04d}", self.font_small, dark, False,
                      center=(W // 2, box.bottom - 46))
        elif g.state == "over":
            box = self.panel(520, 300)
            self.text("FIN DEL JUEGO", self.font_mid, th["accent"], False,
                      center=(W // 2, box.top + 44))
            big = pygame.font.Font(None, 130)
            self.text(f"{g.score:04d}", big, dark, False, center=(W // 2, box.top + 122))
            if g.new_record:
                if int(self.t * 2.5) % 2 == 0:
                    self.text("NUEVO RECORD!", self.font_mid, (230, 150, 20), False,
                              center=(W // 2, box.top + 196))
            else:
                self.text(f"RECORD {g.record:04d}", self.font_small, (120, 120, 140), False,
                          center=(W // 2, box.top + 196))
            self.text("ESPACIO: OTRA VEZ    ESC: MENU", self.font_small, dark, False,
                      center=(W // 2, box.bottom - 36))

        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(170 * self.flash / 0.5)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.4 * 9)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (ox, oy))
