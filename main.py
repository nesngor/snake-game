"""
SNAKE con varios estilos visuales (Nokia, Neon, ...).

Escritorio:  python main.py
Navegador:   python -m pygbag snake   (desde la carpeta padre)

Controles:
  Flechas / WASD   mover
  P o ESC          pausa
  Espacio / Enter  empezar / reintentar
  Menu: arriba/abajo elige opcion, izquierda/derecha cambia valor
"""

import asyncio
import json
import sys
from array import array
from pathlib import Path

import pygame

from game import Game, MAZES, MODE_NAMES, UP, DOWN, LEFT, RIGHT
from styles import STYLES
from styles.base import WIDTH, HEIGHT

WEB = sys.platform == "emscripten"
SAVE_FILE = Path(__file__).with_name("record.json")


# ---------------------------------------------------------------- guardado
def load_save():
    try:
        if WEB:
            import platform
            raw = platform.window.localStorage.getItem("snake_save")
        else:
            raw = SAVE_FILE.read_text()
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_save(data):
    try:
        raw = json.dumps(data)
        if WEB:
            import platform
            platform.window.localStorage.setItem("snake_save", raw)
        else:
            SAVE_FILE.write_text(raw)
    except Exception:
        pass


def clamp_int(value, lo, hi, default):
    try:
        return min(hi, max(lo, int(value)))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- sonido
def make_beep(freq, ms, volume=0.25):
    rate = 22050
    n = int(rate * ms / 1000)
    half = max(1, rate // freq // 2)
    amp = int(32767 * volume)
    samples = array("h", (amp if (i // half) % 2 else -amp for i in range(n)))
    return pygame.mixer.Sound(buffer=samples.tobytes())


class Sounds:
    def __init__(self):
        self.bank = {}
        try:
            self.bank = {"eat": make_beep(880, 40), "bonus": make_beep(1320, 90),
                         "die": make_beep(140, 350), "stage": make_beep(660, 200)}
        except Exception:   # sin audio (o el navegador lo bloquea): jugar en silencio
            pass

    def play(self, name):
        try:
            if name in self.bank:
                self.bank[name].play()
        except Exception:
            pass


# ---------------------------------------------------------------- app: menu + opciones
class App:
    BASE_ROWS = ["ESTILO", "NIVEL", "MODO", "MAPA"]

    def __init__(self, screen):
        data = load_save()
        self.renderers = [cls(screen) for cls in STYLES]
        keys = [r.KEY for r in self.renderers]
        self.style_idx = keys.index(data["estilo"]) if data.get("estilo") in keys else 0

        saved = data.get("opts") if isinstance(data.get("opts"), dict) else {}
        if "palette" in data:   # formato viejo (solo existia Nokia)
            saved.setdefault("nokia", [data.get("palette", 0), data.get("style", 0)])
        self.opts = {}
        for r in self.renderers:
            vals = saved.get(r.KEY)
            vals = vals if isinstance(vals, list) else []
            self.opts[r.KEY] = [clamp_int(vals[i] if i < len(vals) else 0, 0, len(values) - 1, 0)
                                for i, (_, values) in enumerate(r.OPTIONS)]

        self.game = Game(level=clamp_int(data.get("level"), 1, 9, 5),
                         maze_idx=clamp_int(data.get("maze"), 0, len(MAZES) - 1, 1),
                         record=clamp_int(data.get("record"), 0, 99999, 0),
                         mode=data.get("mode", "RAPIDO"))
        self.menu_sel = 0

    @property
    def renderer(self):
        return self.renderers[self.style_idx]

    def opt(self, i):
        return self.opts[self.renderer.KEY][i]

    def menu_rows(self):
        g = self.game
        rows = [("ESTILO", self.renderer.NAME), ("NIVEL", str(g.level)), ("MODO", g.mode),
                ("MAPA", g.maze["name"])]
        for i, (label, values) in enumerate(self.renderer.OPTIONS):
            rows.append((label, values[self.opt(i)]))
        return rows

    def save(self):
        write_save({"record": self.game.record, "level": self.game.level,
                    "maze": self.game.maze_idx, "mode": self.game.mode,
                    "estilo": self.renderer.KEY, "opts": self.opts})

    def change(self, row, step):
        g = self.game
        if row == 0:
            self.style_idx = (self.style_idx + step) % len(self.renderers)
        elif row == 1:
            g.level = min(9, max(1, g.level + step))
        elif row == 2:
            g.mode = MODE_NAMES[(MODE_NAMES.index(g.mode) + step) % len(MODE_NAMES)]
        elif row == 3:
            g.maze_idx = (g.maze_idx + step) % len(MAZES)
        else:
            k = row - len(self.BASE_ROWS)
            values = self.renderer.OPTIONS[k][1]
            vals = self.opts[self.renderer.KEY]
            vals[k] = (vals[k] + step) % len(values)
        self.save()

    def handle_key(self, key):
        dirs = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
                pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}
        start_keys = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)
        g = self.game
        d = dirs.get(key)

        if g.state == "menu":
            if key in start_keys:
                g.start()
            elif d in (UP, DOWN):
                self.menu_sel = (self.menu_sel + d[1]) % len(self.menu_rows())
            elif d in (LEFT, RIGHT):
                self.change(self.menu_sel, d[0])
            elif key == pygame.K_ESCAPE and not WEB:
                return False
        elif g.state == "play":
            if d:
                g.turn(d)
            elif key in (pygame.K_p, pygame.K_ESCAPE):
                g.pause()
        elif g.state == "pause":
            if key in (pygame.K_p, pygame.K_ESCAPE) or key in start_keys:
                g.resume()
        elif g.state == "stage":
            if key in start_keys:
                g.load_stage()
        elif g.state == "over":
            if key in start_keys:
                g.start()
            elif key == pygame.K_ESCAPE:
                g.set_state("menu")
        return True


async def main():
    pygame.mixer.pre_init(22050, -16, 1, 256)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Snake")
    clock = pygame.time.Clock()
    sounds = Sounds()
    app = App(screen)

    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                running = app.handle_key(event.key)

        app.game.update(dt)
        for ev in app.game.events:
            sounds.play(ev["type"])
            app.renderer.on_event(ev)
            if ev["type"] == "record":
                app.save()
        app.game.events.clear()

        app.renderer.update(dt)
        app.renderer.draw(app)
        pygame.display.flip()
        await asyncio.sleep(0)   # cede el control al navegador en la version web

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
