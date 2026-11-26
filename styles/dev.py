"""Estilo DEV: el juego como un editor de codigo. La serpiente es codigo, la comida son bugs."""

import math
import random
from pathlib import Path

import pygame

from game import COLS, ROWS, BONUS_TICKS, FOODS_PER_STAGE, UP, DOWN, LEFT, RIGHT
from styles.base import Renderer, WIDTH as W, HEIGHT as H

ASSETS = Path(__file__).resolve().parent.parent / "assets"
CELL = 30
TAB_H, CRUMB_H = 32, 24
FX, FY = 56, TAB_H + CRUMB_H + 4          # tablero: 840 x 420
FW, FH = COLS * CELL, ROWS * CELL
MINI_X = FX + FW + 6
PANEL_Y = FY + FH + 4                     # terminal
STATUS_Y = H - 24

THEMES = [
    ("OSCURO", {"bg": (30, 31, 36), "gutter": (110, 112, 122), "line": (40, 42, 52),
                "sel": (38, 79, 120), "panel": (24, 25, 29), "tabs": (37, 38, 44),
                "status": (0, 110, 190), "status_text": (255, 255, 255), "text": (212, 212, 212),
                "kw": (197, 134, 192), "fn": (220, 220, 170), "str": (206, 145, 120),
                "num": (181, 206, 168), "p": (212, 212, 212), "var": (156, 220, 254),
                "cm": (106, 153, 85), "err": (244, 71, 71), "warn": (205, 173, 0), "ok": (80, 200, 120),
                "dim": (90, 92, 100)}),
    ("CLARO", {"bg": (255, 255, 255), "gutter": (150, 150, 155), "line": (243, 245, 250),
               "sel": (173, 214, 255), "panel": (246, 246, 246), "tabs": (236, 236, 236),
               "status": (0, 110, 190), "status_text": (255, 255, 255), "text": (30, 30, 30),
               "kw": (0, 0, 220), "fn": (121, 94, 38), "str": (163, 21, 21), "num": (9, 134, 88),
               "p": (40, 40, 40), "var": (0, 16, 128), "cm": (0, 128, 0), "err": (215, 30, 30),
               "warn": (190, 140, 0), "ok": (20, 150, 60), "dim": (190, 190, 195)}),
    ("TERMINAL", {"bg": (6, 12, 6), "gutter": (40, 110, 40), "line": (12, 26, 12),
                  "sel": (20, 60, 20), "panel": (3, 8, 3), "tabs": (10, 20, 10),
                  "status": (20, 90, 20), "status_text": (190, 255, 190), "text": (120, 255, 120),
                  "kw": (180, 255, 180), "fn": (140, 255, 140), "str": (100, 220, 100),
                  "num": (160, 255, 160), "p": (90, 200, 90), "var": (130, 240, 130),
                  "cm": (50, 140, 50), "err": (255, 90, 70), "warn": (220, 220, 80), "ok": (150, 255, 150),
                  "dim": (30, 80, 30)}),
    ("SOLAR", {"bg": (0, 43, 54), "gutter": (88, 110, 117), "line": (7, 54, 66),
               "sel": (20, 80, 96), "panel": (0, 34, 43), "tabs": (7, 54, 66),
               "status": (38, 139, 210), "status_text": (253, 246, 227), "text": (147, 161, 161),
               "kw": (133, 153, 0), "fn": (38, 139, 210), "str": (42, 161, 152), "num": (211, 54, 130),
               "p": (147, 161, 161), "var": (181, 137, 0), "cm": (88, 110, 117), "err": (220, 50, 47),
               "warn": (203, 75, 22), "ok": (133, 153, 0), "dim": (60, 85, 92)}),
]

LANGS = {
    "PYTHON": {"file": "snake.py", "run": "$ python snake.py",
               "code": [("def ", "kw"), ("comer", "fn"), ("(", "p"), ("self", "kw"), (", ", "p"),
                        ("bug", "var"), ("): ", "p"), ("return ", "kw"), ("bug", "var"), (".", "p"),
                        ("fix", "fn"), ("(", "p"), ("42", "num"), (") ", "p"), ("# ñam ", "cm")],
               "wall": "# TODO: refactor ",
               "error": ["Traceback (most recent call last):",
                         '  File "snake.py", line {ln}, in step',
                         "CollisionError: la serpiente choco"],
               "exit": "Process finished with exit code 1"},
    "JAVASCRIPT": {"file": "snake.js", "run": "$ node snake.js",
                   "code": [("const ", "kw"), ("snake", "var"), (" = ", "p"), ("() ", "p"), ("=> ", "kw"),
                            ("eat", "fn"), ("(", "p"), ("bug", "var"), (", ", "p"), ("'ñam'", "str"),
                            ("); ", "p")],
                   "wall": "// FIXME no tocar ",
                   "error": ["Uncaught CollisionError: la serpiente choco",
                             "    at Snake.step (snake.js:{ln})",
                             "    at gameLoop (main.js:42)"],
                   "exit": "Node.js v20 - proceso terminado"},
    "SQL": {"file": "snake.sql", "run": "$ psql -f snake.sql",
            "code": [("SELECT ", "kw"), ("* ", "p"), ("FROM ", "kw"), ("bugs ", "var"), ("WHERE ", "kw"),
                     ("fixed", "var"), (" = ", "p"), ("0", "num"), ("; ", "p"), ("-- ñam ", "cm")],
            "wall": "-- DEPRECATED ",
            "error": ["ERROR 1062 (23000): entrada duplicada",
                      "'serpiente' para la llave 'PRIMARY'",
                      "Query abortada en la linea {ln}"],
            "exit": "ROLLBACK"},
    "C": {"file": "snake.c", "run": "$ gcc snake.c && ./a.out",
          "code": [("while", "kw"), ("(", "p"), ("1", "num"), (") ", "p"), ("{ ", "p"), ("snake", "var"),
                   ("->", "p"), ("eat", "fn"), ("(", "p"), ("bug", "var"), ("); ", "p"), ("} ", "p"),
                   ("/*ñam*/ ", "cm")],
          "wall": "/* legacy hack */ ",
          "error": ["snake.c:{ln}: runtime error: choque",
                    "Segmentation fault (core dumped)", ""],
          "exit": "exit status 139"},
}
LANG_NAMES = list(LANGS)


def font(name, size):
    try:
        return pygame.font.Font(str(ASSETS / name), size)
    except Exception:
        return pygame.font.Font(None, int(size * 1.2))


class DevRenderer(Renderer):
    NAME = "DEV"
    KEY = "dev"
    OPTIONS = [("TEMA", [t[0] for t in THEMES]), ("LENGUAJE", LANG_NAMES)]

    def __init__(self, screen):
        super().__init__(screen)
        self.canvas = pygame.Surface((W, H))
        self.f_cell = font("IBMPlexMono-Bold.ttf", 20)
        self.f_ui = font("IBMPlexMono-Regular.ttf", 15)
        self.f_ui_b = font("IBMPlexMono-Bold.ttf", 15)
        self.f_code = font("IBMPlexMono-Regular.ttf", 19)
        self.f_big = font("IBMPlexMono-Bold.ttf", 30)
        self.glyphs = {}
        self.t = 0.0
        self.th = THEMES[0][1]
        self.lang = LANGS["PYTHON"]
        self.log = []                 # [(texto, tipo)]
        self.floaters = []            # [x, y, texto, tipo, vida]
        self.shake = 0.0
        self.flash = 0.0
        self.flash_kind = "ok"
        self.prev_state = "menu"
        self.fixed = 0

    # ------------------------------------------------------------ utilidades
    def glyph(self, ch, color, f=None):
        f = f or self.f_cell
        key = (ch, color, id(f))
        if key not in self.glyphs:
            if len(self.glyphs) > 3000:
                self.glyphs.clear()
            self.glyphs[key] = f.render(ch, True, color)
        return self.glyphs[key]

    def text(self, s, f, color, **anchor):
        img = f.render(s, True, color)
        rect = img.get_rect(**anchor)
        self.canvas.blit(img, rect)
        return rect

    def code_chars(self):
        chars = []
        for tok, kind in self.lang["code"]:
            for ch in tok:
                chars.append(("·", "dim") if ch == " " else (ch, kind))
        return chars

    def squiggle(self, x, y, w, color):
        pts = [(x + k, y + (2 if (k // 3) % 2 else 0)) for k in range(0, int(w) + 1, 3)]
        if len(pts) > 1:
            pygame.draw.lines(self.canvas, color, False, pts, 1)

    def add_log(self, s, kind="text"):
        self.log.append((s, kind))
        self.log = self.log[-3:]

    # ------------------------------------------------------------ eventos
    def on_event(self, ev):
        kind = ev["type"]
        if kind == "eat":
            self.fixed += 1
            c, r = ev["pos"]
            self.add_log(f"[OK] bug #{self.fixed} arreglado en Ln {r + 1}, Col {c + 1}", "ok")
            x, y = FX + c * CELL + CELL / 2, FY + r * CELL
            self.floaters.append([x, y, "bug arreglado", "ok", 0.9])
        elif kind == "bonus":
            c, r = ev["pos"]
            self.add_log(f"[INFO] cafe tomado: productividad +{ev['points']}", "warn")
            self.floaters.append([FX + c * CELL + CELL, FY + r * CELL, f"+{ev['points']} cafe!", "warn", 1.1])
        elif kind == "die":
            self.shake = 0.35
            self.flash, self.flash_kind = 0.3, "err"
        elif kind == "stage":
            self.add_log(f"[BUILD] exitoso - {FOODS_PER_STAGE}/{FOODS_PER_STAGE} pruebas pasaron", "ok")
            self.flash, self.flash_kind = 0.4, "ok"

    def update(self, dt):
        s = dt / 1000
        self.t += s
        self.shake = max(0.0, self.shake - s)
        self.flash = max(0.0, self.flash - s)
        for f in self.floaters:
            f[1] -= 30 * s
            f[4] -= s
        self.floaters = [f for f in self.floaters if f[4] > 0]

    # ------------------------------------------------------------ marco del editor
    def draw_chrome(self, tabs, crumb):
        th = self.th
        c = self.canvas
        c.fill(th["bg"])
        c.fill(th["tabs"], (0, 0, W, TAB_H))
        x = 0
        for i, name in enumerate(tabs):
            w = self.f_ui.size(name)[0] + 46
            if i == 0:
                c.fill(th["bg"], (x, 0, w, TAB_H))
                c.fill(th["status"], (x, 0, w, 2))
            self.text(name, self.f_ui_b if i == 0 else self.f_ui, th["text"] if i == 0 else th["gutter"],
                      midleft=(x + 14, TAB_H // 2))
            self.text("x", self.f_ui, th["gutter"], midright=(x + w - 10, TAB_H // 2))
            x += w
        self.text(crumb, self.f_ui, th["gutter"], midleft=(FX, TAB_H + CRUMB_H // 2))

    def draw_gutter(self, n_lines, current, top=FY, step=CELL):
        th = self.th
        for i in range(n_lines):
            y = top + i * step + step // 2
            col = th["text"] if i == current else th["gutter"]
            self.text(str(i + 1), self.f_ui, col, midright=(FX - 14, y))

    def draw_panel(self, lines):
        th = self.th
        c = self.canvas
        c.fill(th["panel"], (0, PANEL_Y, W, STATUS_Y - PANEL_Y))
        pygame.draw.line(c, th["line"], (0, PANEL_Y), (W, PANEL_Y))
        x = 16
        for i, name in enumerate(("TERMINAL", "PROBLEMAS", "SALIDA")):
            r = self.text(name, self.f_ui, th["text"] if i == 0 else th["gutter"], topleft=(x, PANEL_Y + 2))
            if i == 0:
                c.fill(th["status"], (r.left, r.bottom, r.w, 2))
            x = r.right + 24
        for i, (s, kind) in enumerate(lines[-3:]):
            col = th.get(kind, th["text"])
            self.text(s, self.f_ui, col, topleft=(16, PANEL_Y + 19 + i * 15))

    def draw_status(self, left, right, alert=False):
        th = self.th
        c = self.canvas
        c.fill(th["err"] if alert else th["status"], (0, STATUS_Y, W, H - STATUS_Y))
        x = 10
        for s in left:
            r = self.text(s, self.f_ui, th["status_text"], midleft=(x, STATUS_Y + 12))
            x = r.right + 22
        x = W - 10
        for s in reversed(right):
            r = self.text(s, self.f_ui, th["status_text"], midright=(x, STATUS_Y + 12))
            x = r.left - 22

    # ------------------------------------------------------------ juego
    def draw_bug(self, cx, cy):
        th = self.th
        c = self.canvas
        col = th["err"]
        for k in (-1, 0, 1):                                 # patitas
            pygame.draw.line(c, col, (cx - 10, cy + k * 5), (cx + 10, cy + k * 5), 2)
        pygame.draw.ellipse(c, col, (cx - 7, cy - 8, 14, 18))
        pygame.draw.circle(c, col, (cx, cy - 10), 5)
        pygame.draw.line(c, th["bg"], (cx, cy - 6), (cx, cy + 9), 1)
        pygame.draw.line(c, col, (cx - 2, cy - 14), (cx - 6, cy - 19), 2)   # antenas
        pygame.draw.line(c, col, (cx + 2, cy - 14), (cx + 6, cy - 19), 2)

    def draw_coffee(self, g):
        th = self.th
        c = self.canvas
        col, cc = g.bonus
        x, y = FX + col * CELL + 14, FY + cc * CELL + 8
        cup = pygame.Rect(x, y + 4, 22, 17)
        pygame.draw.rect(c, th["warn"], cup, 0, 0, 0, 0, 6, 6)
        pygame.draw.rect(c, th["fn"], (x + 2, y + 5, 18, 4))
        pygame.draw.circle(c, th["warn"], (x + 24, y + 12), 6, 3)
        for k in range(3):                                   # vapor
            sx = x + 5 + k * 6
            off = math.sin(self.t * 5 + k) * 2
            pygame.draw.line(c, th["gutter"], (sx + off, y - 6), (sx - off, y + 1), 2)
        frac = g.bonus_left / BONUS_TICKS
        c.fill(th["line"], (FX + col * CELL + 4, FY + cc * CELL + CELL - 3, CELL * 2 - 8, 3))
        c.fill(th["warn"], (FX + col * CELL + 4, FY + cc * CELL + CELL - 3, int((CELL * 2 - 8) * frac), 3))

    def draw_walls(self, rects):
        th = self.th
        txt = self.lang["wall"]
        for wc, wr, w, h in rects:
            rect = pygame.Rect(FX + wc * CELL, FY + wr * CELL, w * CELL, h * CELL)
            self.canvas.fill(th["line"], rect)
            for dr in range(h):
                for dc in range(w):
                    ch = txt[(dc + dr * w) % len(txt)]     # el comentario empieza en cada bloque
                    if ch != " ":
                        img = self.glyph(ch, th["cm"])
                        self.canvas.blit(img, img.get_rect(center=(rect.left + dc * CELL + CELL / 2,
                                                                   rect.top + dr * CELL + CELL / 2)))
                self.squiggle(rect.left + 2, rect.top + dr * CELL + CELL - 5, rect.w - 4, th["warn"])

    def draw_snake(self, g, dead):
        th = self.th
        chars = self.code_chars()
        n = len(g.snake)
        sel = th["err"] if dead else th["sel"]
        sel = tuple(int(a * 0.35 + b * 0.65) for a, b in zip(sel, th["bg"])) if dead else sel
        for i, (c, r) in enumerate(g.snake):                 # fondo "seleccionado"
            rect = pygame.Rect(FX + c * CELL + 1, FY + r * CELL + 3, CELL - 2, CELL - 6)
            if i + 1 < n:
                nc, nr = g.snake[i + 1]
                if nr == r and abs(nc - c) == 1:
                    rect.union_ip(rect.move((nc - c) * CELL, 0))
                elif nc == c and abs(nr - r) == 1:
                    rect.union_ip(rect.move(0, (nr - r) * CELL))
            self.canvas.fill(sel, rect)
        for i, (c, r) in enumerate(g.snake[1:], start=1):   # cuerpo = codigo
            # anclado a la cola: se lee bien y al crecer "teclea" el siguiente caracter
            ch, kind = chars[(n - 1 - i) % len(chars)]
            col = th["err"] if dead else th[kind]
            img = self.glyph(ch, col)
            cx, cy = FX + c * CELL + CELL / 2, FY + r * CELL + CELL / 2
            self.canvas.blit(img, img.get_rect(center=(cx, cy)))
            if dead:
                self.squiggle(cx - CELL / 2 + 2, cy + 10, CELL - 4, th["err"])
        # cabeza = cursor
        hc, hr = g.snake[0]
        rect = pygame.Rect(FX + hc * CELL + 2, FY + hr * CELL + 2, CELL - 4, CELL - 4)
        arrow = {RIGHT: ">", LEFT: "<", UP: "^", DOWN: "v"}[g.direction]
        cursor = th["err"] if dead else th["text"]
        if int(self.t * 2.5) % 2 == 0 or dead:
            self.canvas.fill(cursor, rect)
            img = self.glyph(arrow, th["bg"])
        else:
            pygame.draw.rect(self.canvas, cursor, rect, 2)
            img = self.glyph(arrow, cursor)
        self.canvas.blit(img, img.get_rect(center=rect.center))

    def draw_minimap(self, g):
        th = self.th
        c = self.canvas
        sx, sy = 2, 3
        area = pygame.Rect(MINI_X, FY, COLS * sx, ROWS * sy)
        c.fill(th["line"], area.inflate(4, 4))
        for wc, wr in g.walls:
            c.fill(th["cm"], (MINI_X + wc * sx, FY + wr * sy, sx, sy))
        for i, (sc, sr) in enumerate(g.snake):
            c.fill(th["text"] if i == 0 else th["kw"], (MINI_X + sc * sx, FY + sr * sy, sx, sy))
        if g.food:
            c.fill(th["err"], (MINI_X + g.food[0] * sx, FY + g.food[1] * sy, sx, sy))
        pygame.draw.rect(c, th["gutter"], area.inflate(4, 4), 1)

    def draw_game(self, g):
        th = self.th
        lang = self.lang
        dead = g.state in ("dying", "over")
        head_r = g.snake[0][1] if g.snake else -1
        self.draw_chrome([lang["file"], "mapas.json", "README.md"],
                         f"snake  >  mapas  >  {g.maze['name'].lower()}  >  nivel_{g.level}")
        self.canvas.fill(th["line"], (FX, FY + head_r * CELL, FW, CELL))        # linea actual
        self.draw_gutter(ROWS, head_r)
        border = pygame.Rect(FX - 3, FY - 1, FW + 6, FH + 2)
        if g.maze["border"]:
            pygame.draw.rect(self.canvas, th["gutter"], border, 1)
        else:
            for x in range(border.left, border.right, 8):
                self.canvas.fill(th["gutter"], (x, border.top, 4, 1))
                self.canvas.fill(th["gutter"], (x, border.bottom - 1, 4, 1))
        self.draw_walls(g.wall_rects)
        if g.food:
            fx, fy = FX + g.food[0] * CELL + CELL / 2, FY + g.food[1] * CELL + CELL / 2
            self.draw_bug(fx, fy + 2)
            self.squiggle(fx - 12, fy + 13, 24, th["err"])
        if g.bonus:
            self.draw_coffee(g)
        if g.snake and not (g.state == "dying" and (g.state_time // 120) % 2 == 1):
            self.draw_snake(g, dead)
        self.draw_minimap(g)
        for x, y, s, kind, life in self.floaters:
            self.text(s, self.f_ui_b, th[kind], center=(x, y))

        hc, hr = g.snake[0] if g.snake else (0, 0)
        errors = 1 if dead else 0
        left = ["main*", f"{errors} errores  {len(g.wall_rects)} advertencias"]
        right = [f"Ln {hr + 1}, Col {hc + 1}", f"Puntos {g.score}", f"Record {g.record}",
                 f"Nivel {g.level}", g.maze["name"].title()]
        if g.bonus:
            right.insert(0, f"cafe {g.bonus_left}")
        lines = self.log
        if dead:
            ln = hr + 1
            lines = self.log[-1:] + [(s.format(ln=ln), "err") for s in lang["error"] if s][:2]
        self.draw_panel(lines)
        self.draw_status(left, right, alert=dead)

    # ------------------------------------------------------------ menu = settings.json
    def draw_menu(self, app):
        th = self.th
        rows = app.menu_rows()
        self.draw_chrome(["settings.json", self.lang["file"], "README.md"], "snake  >  .config  >  settings.json")
        step = 30
        top = FY + 6
        keys = [label.lower() for label, _ in rows]
        lines = [[("// SNAKE - configuracion del juego", "cm")], [("{", "p")]]
        for i, (key, (_, value)) in enumerate(zip(keys, rows)):
            is_num = value.isdigit()
            comma = "," if i < len(rows) - 1 else ""
            lines.append([("  ", "p"), (f'"{key}"', "var"), (": ", "p"),
                          (value if is_num else f'"{value}"', "num" if is_num else "str"), (comma, "p")])
        lines += [[("}", "p")], [], [(f"// record: {app.game.record}", "cm")],
                  [("// flechas: arriba/abajo elige, izquierda/derecha cambia", "cm")]]
        cur = 2 + app.menu_sel
        self.canvas.fill(th["line"], (FX, top + cur * step, W - FX - 260, step))
        self.draw_gutter(len(lines), cur, top=top, step=step)
        for i, toks in enumerate(lines):
            x = FX + 8
            y = top + i * step + step // 2
            for tok, kind in toks:
                r = self.text(tok, self.f_code, th[kind], midleft=(x, y))
                x = r.right
            if i == cur:
                if int(self.t * 2.5) % 2 == 0:
                    self.canvas.fill(th["text"], (x + 2, y - 11, 2, 22))
                self.text("   // <- ->", self.f_code, th["cm"], midleft=(x + 6, y))

        # titulo en arte ASCII
        from styles.nokia import FONT
        ax, ay = W - 250, FY + 14
        for li, word in enumerate(("SNAKE", ".DEV")):
            for gy in range(5):
                row = "".join(FONT.get(ch, FONT[" "])[gy] + "." for ch in word)
                s = row.replace(".", " ")
                self.text(s, self.f_ui_b, th["kw"] if li == 0 else th["fn"],
                          topleft=(ax, ay + (li * 6 + gy) * 17))

        run = self.lang["run"]
        blink = int(self.t * 2) % 2 == 0
        self.draw_panel([(run, "text"), ("Presiona ESPACIO para ejecutar" + (" _" if blink else ""), "ok")])
        self.draw_status(["main", "0 errores  0 advertencias"],
                         ["JSON", "UTF-8", f"Ln {cur + 1}, Col 1"])

    # ------------------------------------------------------------ dialogos
    def dialog(self, title, lines, color_key):
        th = self.th
        w = 560
        h = 70 + len(lines) * 26
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (FX + FW // 2, FY + FH // 2)
        veil = pygame.Surface((W, PANEL_Y), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 110))
        self.canvas.blit(veil, (0, 0))
        self.canvas.fill(th["panel"], rect)
        self.canvas.fill(th[color_key], (rect.left, rect.top, w, 4))
        pygame.draw.rect(self.canvas, th["gutter"], rect, 1)
        self.text(title, self.f_ui_b, th[color_key], topleft=(rect.left + 20, rect.top + 18))
        for i, (s, kind) in enumerate(lines):
            self.text(s, self.f_code if kind != "big" else self.f_big,
                      th["text"] if kind == "big" else th[kind], topleft=(rect.left + 20, rect.top + 50 + i * 26))

    # ------------------------------------------------------------ frame completo
    def draw(self, app):
        self.th = THEMES[app.opt(0)][1]
        self.lang = LANGS[LANG_NAMES[app.opt(1)]]
        g = app.game
        lang = self.lang

        if g.state == "play" and self.prev_state in ("menu", "over"):
            self.fixed = 0
            self.log = [(lang["run"], "text"), (f"Cargando mapa '{g.maze['name'].lower()}'...", "dim")]
        self.prev_state = g.state

        if g.state == "menu":
            self.draw_menu(app)
        else:
            self.draw_game(g)

        hr = g.snake[0][1] + 1 if g.snake else 1
        if g.state == "pause":
            self.dialog("|| Pausado en breakpoint", [(f"{lang['file']}, linea {hr}", "text"),
                                                     ("Presiona P para continuar (F5)", "dim")], "warn")
        elif g.state == "stage":
            self.dialog("BUILD EXITOSO", [(f"{FOODS_PER_STAGE}/{FOODS_PER_STAGE} pruebas pasaron", "ok"),
                                          (f"$ git commit -m \"mapa {g.maze_idx}: {g.maze['name'].lower()}\"", "text"),
                                          (f"Puntos: {g.score}", "text")], "ok")
        elif g.state == "over":
            err = [(s.format(ln=hr), "err") for s in lang["error"] if s]
            rec = ("Nuevo record!", "warn") if g.new_record else (f"Record: {g.record}", "dim")
            self.dialog("ERROR - " + lang["exit"],
                        err + [(f"Puntos: {g.score}", "big"), ("", "dim"), rec,
                               ("[ESPACIO] re-ejecutar    [ESC] menu", "text")], "err")

        if self.flash > 0:
            col = self.th[self.flash_kind]
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((*col, int(70 * self.flash / 0.4)))
            self.canvas.blit(fl, (0, 0))

        ox = oy = 0
        if self.shake > 0:
            k = int(self.shake / 0.35 * 6)
            ox, oy = random.randint(-k, k), random.randint(-k, k)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (ox, oy))
