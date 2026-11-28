"""
SNAKE con varios estilos visuales (Nokia, Neon, ...).

Escritorio:  python main.py
Navegador:   python -m pygbag snake   (desde la carpeta padre)

Controles:
  Flechas / WASD   mover
  P o ESC          pausa (en la pausa: arriba/abajo + Enter, o M = menu principal)
  Espacio / Enter  empezar / reintentar
  Menu: arriba/abajo elige opcion, izquierda/derecha cambia valor

Celular (o mouse):
  Deslizar         = flechas (mover / elegir y cambiar opciones del menu)
  Tocar            = empezar / reintentar; durante el juego, pausa
  En la pausa      tocar CONTINUAR o MENU PRINCIPAL
  Fin del juego    deslizar = volver al menu
"""

import asyncio
import json
import sys
from array import array
from pathlib import Path

import pygame

from game import Game, MAZES, MODE_NAMES, UP, DOWN, LEFT, RIGHT
from online import Online
from plat import Plataforma
from styles import STYLES
from styles.base import WIDTH, HEIGHT

WEB = sys.platform == "emscripten"
SAVE_FILE = Path(__file__).with_name("record.json")
ONLINE = "EN LINEA"     # valor extra de MODO: abre el menu de partidas en linea


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


# ---------------------------------------------------------------- tactil (celular)
class Touch:
    """Convierte dedo (o mouse) en gestos: deslizar = flecha, toque = Enter / elegir.

    Los deslizamientos se detectan mientras el dedo se mueve (sin esperar a soltarlo),
    asi se pueden encadenar giros sin levantar el dedo.
    """
    SWIPE = 36        # px de pantalla para contar como deslizamiento
    TAP_MOVE = 18     # un toque no puede moverse mas que esto
    TAP_MS = 450      # ni durar mas que esto

    def __init__(self):
        self.anchor = None     # donde empezo el tramo actual del deslizamiento
        self.start = None      # donde se apoyo el dedo
        self.t0 = 0
        self.swiped = False

    @staticmethod
    def event_pos(event):
        """(x, y) en px de pantalla, o None si el evento no es de dedo/mouse."""
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return event.x * WIDTH, event.y * HEIGHT            # vienen normalizados 0..1
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            if getattr(event, "touch", False):                  # copia del dedo: ya se cuenta arriba
                return None
            if event.type != pygame.MOUSEMOTION and event.button != 1:
                return None
            return event.pos
        return None

    def handle(self, event, app):
        pos = self.event_pos(event)
        if pos is None:
            return
        if event.type in (pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
            self.anchor = self.start = pos
            self.t0 = pygame.time.get_ticks()
            self.swiped = False
        elif self.anchor is None:
            return
        elif event.type in (pygame.FINGERMOTION, pygame.MOUSEMOTION):
            dx, dy = pos[0] - self.anchor[0], pos[1] - self.anchor[1]
            if max(abs(dx), abs(dy)) >= self.SWIPE:
                if abs(dx) > abs(dy):
                    app.handle_swipe(RIGHT if dx > 0 else LEFT)
                else:
                    app.handle_swipe(DOWN if dy > 0 else UP)
                self.anchor = pos
                self.swiped = True
        else:   # soltar
            moved = max(abs(pos[0] - self.start[0]), abs(pos[1] - self.start[1]))
            quick = pygame.time.get_ticks() - self.t0 <= self.TAP_MS
            if not self.swiped and moved <= self.TAP_MOVE and quick:
                app.handle_tap(*pos)
            self.anchor = self.start = None


# ---------------------------------------------------------------- app: menu + opciones
class App:
    BASE_ROWS = ["ESTILO", "NIVEL", "MODO", "MAPA"]
    PAUSE_ROWS = ["CONTINUAR", "MENU PRINCIPAL"]

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
        self.pause_sel = 0      # 0 = CONTINUAR, 1 = MENU PRINCIPAL
        self.online_mode = data.get("mode") == ONLINE   # MODO = EN LINEA (juega contra otros)
        self.plat = Plataforma()      # sesion de Lyness: estilos desbloqueados, medallas y misiones
        self.online = Online(self)
        self.aviso_ms = 0             # resalta el aviso de estilo bloqueado al intentar jugar
        self.solo = {"comidas": 0, "mapas": 0}   # lo hecho en la partida en solitario en curso
        self.prev_state = "menu"

    @property
    def bloqueado(self):
        """True si el estilo elegido aun no se tiene (se puede ver en el menu, pero no jugar con el)."""
        return not self.plat.desbloqueado(self.renderer.KEY)

    def seguir_solitario(self, eventos):
        """Lleva la cuenta de la partida en solitario y la reporta a la plataforma al terminar."""
        g = self.game
        for ev in eventos:
            if ev["type"] == "eat":
                self.solo["comidas"] += 1
            elif ev["type"] == "stage":
                self.solo["mapas"] += 1
        if g.state == "play" and self.prev_state in ("menu", "over"):
            self.solo = {"comidas": 0, "mapas": 0}          # partida nueva
        if g.state == "over" and self.prev_state == "dying":
            self.plat.reportar_solitario({"partidas": 1, "comidas": self.solo["comidas"],
                                          "mapas_superados": self.solo["mapas"], "mejor_puntaje": g.score})
        self.prev_state = g.state

    @property
    def renderer(self):
        return self.renderers[self.style_idx]

    def opt(self, i):
        return self.opts[self.renderer.KEY][i]

    def menu_rows(self):
        g = self.game
        rows = [("ESTILO", self.renderer.NAME), ("NIVEL", str(g.level)),
                ("MODO", ONLINE if self.online_mode else g.mode), ("MAPA", g.maze["name"])]
        for i, (label, values) in enumerate(self.renderer.OPTIONS):
            rows.append((label, values[self.opt(i)]))
        return rows

    def save(self):
        write_save({"record": self.game.record, "level": self.game.level,
                    "maze": self.game.maze_idx, "mode": ONLINE if self.online_mode else self.game.mode,
                    "estilo": self.renderer.KEY, "opts": self.opts})

    def change(self, row, step):
        g = self.game
        if row == 0:
            self.style_idx = (self.style_idx + step) % len(self.renderers)
        elif row == 1:
            g.level = min(9, max(1, g.level + step))
        elif row == 2:      # CLASICO, RAPIDO, EXTREMO y EN LINEA
            modes = MODE_NAMES + [ONLINE]
            cur = modes.index(ONLINE if self.online_mode else g.mode)
            new = modes[(cur + step) % len(modes)]
            self.online_mode = new == ONLINE
            if not self.online_mode:
                g.mode = new
        elif row == 3:
            g.maze_idx = (g.maze_idx + step) % len(MAZES)
        else:
            k = row - len(self.BASE_ROWS)
            values = self.renderer.OPTIONS[k][1]
            vals = self.opts[self.renderer.KEY]
            vals[k] = (vals[k] + step) % len(values)
        self.save()

    def handle_key(self, key, unicode=""):
        if self.online.active:
            self.online.handle_key(key, unicode)
            return True
        dirs = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
                pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}
        start_keys = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)
        g = self.game
        d = dirs.get(key)

        if g.state == "menu":
            if key in start_keys:
                if self.bloqueado:
                    self.aviso_ms = 900          # no se juega con un estilo que no se tiene
                elif self.online_mode:
                    self.online.enter()
                else:
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
                self.pause()
        elif g.state == "pause":
            if d in (UP, DOWN):
                self.pause_sel = (self.pause_sel + d[1]) % len(self.PAUSE_ROWS)
            elif key in start_keys:
                if self.pause_sel == 0:
                    g.resume()
                else:
                    g.to_menu()
            elif key in (pygame.K_p, pygame.K_ESCAPE):
                g.resume()
            elif key == pygame.K_m:
                g.to_menu()
        elif g.state == "stage":
            if key in start_keys:
                g.load_stage()
        elif g.state == "over":
            if key in start_keys:
                g.start()
            elif key == pygame.K_ESCAPE:
                g.to_menu()
        return True

    # --- gestos tactiles: se traducen a las mismas acciones que el teclado
    def handle_swipe(self, d):
        if self.online.active:
            self.online.handle_swipe(d)
            return
        if self.game.state == "over":
            self.game.to_menu()          # en la pantalla final, deslizar = volver al menu
            return
        key = {UP: pygame.K_UP, DOWN: pygame.K_DOWN, LEFT: pygame.K_LEFT, RIGHT: pygame.K_RIGHT}[d]
        self.handle_key(key)

    def handle_tap(self, x, y):
        if self.online.active:
            self.online.handle_tap(x, y)
            return
        g = self.game
        if g.state == "play":
            self.pause()
        elif g.state == "pause":
            ys = self.renderer.pause_ys
            if not ys:
                self.handle_key(pygame.K_RETURN)
                return
            i = min(range(len(ys)), key=lambda k: abs(ys[k] - y))
            gap = abs(ys[1] - ys[0]) if len(ys) > 1 else 50
            if abs(ys[i] - y) <= gap * 0.75 and abs(x - WIDTH / 2) <= 300:
                self.pause_sel = i
                self.handle_key(pygame.K_RETURN)
        else:
            self.handle_key(pygame.K_RETURN)   # empezar / reintentar / saltar "mapa superado"

    def pause(self):
        if self.game.state == "play":
            self.pause_sel = 0          # siempre abre en CONTINUAR
            self.game.pause()


async def main():
    pygame.mixer.pre_init(22050, -16, 1, 256)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Snake")
    clock = pygame.time.Clock()
    sounds = Sounds()
    app = App(screen)
    touch = Touch()

    running = True
    while running:
        # tope al dt: si la ventana se congela (arrastrarla, cambiar de pestana)
        # no se simulan de golpe decenas de pasos
        dt = min(clock.tick(60), 100)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                app.pause()             # pausa sola al cambiar de ventana
            elif event.type == pygame.KEYDOWN:
                running = app.handle_key(event.key, getattr(event, "unicode", ""))
            else:
                touch.handle(event, app)

        online = app.online.active
        game = app.online.game if online else app.game
        (app.online if online else app.game).update(dt)
        app.plat.update()
        app.aviso_ms = max(0, app.aviso_ms - dt)
        if not online:
            app.seguir_solitario(game.events)
        for ev in game.events:
            if not ev.get("rival"):         # en linea solo suena lo tuyo
                sounds.play(ev["type"])
            app.renderer.on_event(ev)
            if ev["type"] == "record":
                app.save()
        game.events.clear()

        app.renderer.update(dt)
        if online:
            app.online.draw(app.renderer)
        else:
            app.renderer.draw(app)
            if game.state == "menu" and app.bloqueado:
                app.online.draw_lock(screen, app)
        pygame.display.flip()
        await asyncio.sleep(0)   # cede el control al navegador en la version web

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
