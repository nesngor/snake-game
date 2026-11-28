"""
Modo EN LINEA del lado del jugador: pantallas (menu, codigo, sala, resultados)
y el tablero que dibujan los estilos.

El servidor lleva la partida (ver versus.py y server/). Aqui solo se mandan los
giros y se muestra lo que llega. Para que los 14 estilos sirvan sin cambiarlos
mucho, OnlineGame se parece a game.Game: tu serpiente va en `snake` (con el
aspecto normal del estilo) y las rivales en `others`, que cada estilo pinta con
los colores de RIVAL_COLORS (styles/base.py).
"""

from pathlib import Path

import pygame

from game import MAZES, UP, DOWN, LEFT, RIGHT
from net import connect
from styles.base import WIDTH as W, HEIGHT as H, RIVAL_COLORS, RIVAL_NAMES

FONT_FILE = Path(__file__).with_name("assets") / "Fredoka-SemiBold.ttf"
CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
GHOST_MS = 1500            # cuanto se ve una serpiente eliminada antes de desaparecer
ACCENT = (155, 224, 58)
TEXT = (240, 242, 250)
DIM = (150, 156, 180)
WARN = (255, 120, 110)
ME_COLOR = (240, 242, 250)
DIRS = {UP: pygame.K_UP, DOWN: pygame.K_DOWN, LEFT: pygame.K_LEFT, RIGHT: pygame.K_RIGHT}


class Other:
    """Serpiente rival (o la tuya ya eliminada) para que el estilo la dibuje."""

    def __init__(self, snake, direction, tint, dead, frac):
        self.snake = snake
        self.direction = direction
        self.tint = tint          # color de RIVAL_COLORS, o None = tu propio aspecto
        self.k = 0                # 0 = tu serpiente; 1..3 = rivales (para estilos sin color)
        self.dead = dead
        self.frac = frac

    def move_fraction(self):
        return 1.0 if self.dead else self.frac


class OnlineGame:
    """Lo minimo de game.Game que usan los estilos, alimentado por el servidor."""

    def __init__(self, maze_idx=1, level=5):
        self.state = "play"
        self.state_time = 0
        self.maze_idx = maze_idx
        self.level = level
        self.walls = set()
        self.rocks = []
        self.snake = []
        self.direction = RIGHT
        self.food = None
        self.bonus = None
        self.bonus_left = 0
        self.score = 0
        self.record = 0
        self.new_record = False
        self.events = []
        self.others = []
        self.tick_ms = 120
        self.since_tick = 0
        self.frozen = True        # durante la cuenta regresiva no se interpola
        self.set_maze(maze_idx)

    @property
    def maze(self):
        return MAZES[self.maze_idx]

    @property
    def wall_rects(self):
        return self.maze["walls"]

    @property
    def bonus_cells(self):
        if not self.bonus:
            return ()
        return (self.bonus, (self.bonus[0] + 1, self.bonus[1]))

    def set_maze(self, idx):
        from game import maze_cells
        self.maze_idx = idx % len(MAZES)
        self.walls = maze_cells(self.maze)

    def move_fraction(self):
        if self.frozen:
            return 1.0
        return min(1.0, self.since_tick / self.tick_ms)

    def update(self, dt):
        self.state_time += dt
        self.since_tick += dt


class View:
    """Lo que un estilo espera de `app`, apuntando al tablero en linea."""
    PAUSE_ROWS = ["CONTINUAR", "MENU PRINCIPAL"]

    def __init__(self, app, game):
        self.app = app
        self.game = game
        self.pause_sel = 0
        self.menu_sel = 0

    def opt(self, i):
        return self.app.opt(i)

    def menu_rows(self):
        return self.app.menu_rows()


def as_cell(p):
    return (int(p[0]), int(p[1])) if p else None


class Online:
    HOME_ROWS = ["PARTIDA RÁPIDA", "CREAR SALA", "UNIRSE CON CÓDIGO", "VOLVER"]

    def __init__(self, app):
        self.app = app
        self.active = False
        self.net = None
        self.screen = "home"       # home, code, wait, room, round
        self.sel = 0
        self.row_ys = []
        self.code = ["A"] * 4
        self.code_pos = 0
        self.toast = ""
        self.toast_ms = 0
        self.me = None
        self.room = None
        self.round_players = []
        self.phase = None          # countdown, play, over
        self.countdown_ms = 0
        self.result = None
        self.ghosts = {}           # pid -> (body, dir, ms restantes)
        self.alive = {}
        self.game = OnlineGame()
        self.view = View(app, self.game)
        self.fonts = None
        self.t = 0

    # ------------------------------------------------------------ entrar / salir
    def enter(self):
        self.active = True
        self.screen = "home"
        self.sel = 0
        self.room = None
        self.toast = ""
        self.reconnect()

    def reconnect(self):
        if self.net:
            self.net.close()
        self.me = None
        try:
            self.net = connect()
        except Exception:
            self.net = None

    def exit(self):
        if self.net:
            self.net.close()
        self.net = None
        self.active = False

    @property
    def connected(self):
        return bool(self.net) and self.net.status == "open"

    def send(self, msg):
        if self.net:
            self.net.send(msg)

    def say(self, s, ms=3000):
        self.toast, self.toast_ms = s, ms

    # ------------------------------------------------------------ red
    def rival_tint(self, pid):
        """Color de cada rival: segun su orden en la sala, sin contarte a ti."""
        order = [p for p in (self.round_players or (self.room or {}).get("players", [])) if p != self.me]
        k = order.index(pid) + 1 if pid in order else 1
        return k, RIVAL_COLORS[(k - 1) % len(RIVAL_COLORS)]

    def player_label(self, pid):
        if pid == self.me:
            return "TÚ", ME_COLOR
        k, col = self.rival_tint(pid)
        return RIVAL_NAMES[(k - 1) % len(RIVAL_NAMES)], col

    def on_message(self, m):
        t = m.get("t")
        if t == "hello":
            self.me = m.get("you")
            self.nick = None
            if self.app.plat.token:          # con sesion de Lyness: la partida cuenta para medallas y misiones
                self.send({"t": "auth", "token": self.app.plat.token})
        elif t == "auth":
            self.nick = str(m.get("nick") or "") if m.get("ok") else None
        elif t == "error":
            self.say(str(m.get("msg", "ERROR")))
            if self.screen == "wait":
                self.screen = "home"
        elif t == "room":
            self.room = m
            self.me = m.get("you", self.me)
            if m.get("state") == "lobby" and self.screen != "room":
                if self.screen in ("wait", "home", "code") or (self.screen == "round" and self.phase == "over"):
                    self.screen = "room"
                    self.sel = 0
            self.game.set_maze(m.get("maze", 1))
            self.game.level = m.get("level", 5)
        elif t == "round":
            self.screen = "round"
            self.phase = "countdown"
            self.countdown_ms = int(m.get("countdown", 3) * 1000)
            self.round_players = list(m.get("players", []))
            self.result = None
            self.ghosts = {}
            self.alive = {pid: True for pid in self.round_players}
            g = self.game
            g.set_maze(m.get("maze", 1))
            g.level = m.get("level", 5)
            g.tick_ms = max(30, int(m.get("tick_ms", 120)))
            g.frozen = True
            g.score = 0
            g.state_time = 0
        elif t == "state":
            self.apply_state(m)
        elif t == "over":
            self.phase = "over"
            self.result = m
            self.game.frozen = True
            if m.get("winner") == self.me:
                self.game.events.append({"type": "stage"})     # destello y sonido de victoria

    def apply_state(self, m):
        g = self.game
        if self.phase == "countdown" and m.get("tick", 0) > 0:
            self.phase = "play"
        if self.phase == "play":
            g.frozen = False
        g.since_tick = 0
        g.food = as_cell(m.get("food"))
        g.bonus = as_cell(m.get("bonus"))
        g.bonus_left = int(m.get("bonus_left", 0))
        g.snake = []
        others = []
        best = 0
        for s in m.get("snakes", []):
            pid = s.get("id")
            body = [as_cell(p) for p in s.get("body", [])]
            d = tuple(s.get("dir", RIGHT))
            best = max(best, s.get("score", 0))
            if self.alive.get(pid) and not s.get("alive"):
                self.ghosts[pid] = (body, d, GHOST_MS)          # se ve eliminada un momento
            self.alive[pid] = bool(s.get("alive"))
            if pid == self.me:
                g.score = s.get("score", 0)
                if s.get("alive"):
                    g.snake, g.direction = body, d
                self.my_snake = g.snake
            elif s.get("alive"):
                _, tint = self.rival_tint(pid)
                o = Other(body, d, tint, False, 0)
                o.k = self.rival_tint(pid)[0]
                others.append(o)
        g.record = best
        self.live_others = others

        for ev in m.get("ev", []):
            pid, kind = ev.get("id"), ev.get("type")
            pos = as_cell(ev.get("pos"))
            if kind == "eat":
                g.events.append({"type": "eat", "pos": pos, "rival": pid != self.me})
            elif kind == "bonus":
                g.events.append({"type": "bonus", "pos": pos, "points": ev.get("points", 0),
                                 "rival": pid != self.me})
            elif kind == "die" and pid == self.me:
                g.events.append({"type": "die", "pos": pos})

    def refresh_others(self):
        g = self.game
        frac = g.move_fraction()
        out = []
        for o in getattr(self, "live_others", []):
            o.frac = frac
            out.append(o)
        for pid, (body, d, _) in self.ghosts.items():
            if pid == self.me:
                o = Other(body, d, None, True, 1.0)
            else:
                k, tint = self.rival_tint(pid)
                o = Other(body, d, tint, True, 1.0)
                o.k = k
            out.append(o)
        g.others = out

    # ------------------------------------------------------------ tiempo
    def update(self, dt):
        self.t += dt / 1000
        self.toast_ms = max(0, self.toast_ms - dt)
        if self.net:
            for m in self.net.poll():
                if isinstance(m, dict):
                    self.on_message(m)
        if self.screen == "round":
            if self.phase == "countdown":
                self.countdown_ms = max(0, self.countdown_ms - dt)
                # tu serpiente parpadea para que sepas cual eres
                self.game.snake = [] if int(self.t * 4) % 2 else getattr(self, "my_snake", [])
            elif self.game.snake == [] and self.alive.get(self.me):
                self.game.snake = getattr(self, "my_snake", [])
            self.game.update(dt)
            for pid in list(self.ghosts):
                body, d, ms = self.ghosts[pid]
                if ms - dt <= 0:
                    del self.ghosts[pid]
                else:
                    self.ghosts[pid] = (body, d, ms - dt)
            self.refresh_others()
        if self.screen in ("room", "round", "wait") and self.net and self.net.status == "closed":
            self.screen = "home"
            self.room = None
            self.say("SE PERDIÓ LA CONEXIÓN")

    # ------------------------------------------------------------ controles
    def rows(self):
        if self.screen == "home":
            return self.HOME_ROWS
        if self.screen == "room" and self.room:
            mine = self.room.get("host") == self.me and not self.room.get("quick")
            return ["EMPEZAR", "SALIR"] if mine else ["SALIR"]
        if self.screen == "code":
            return ["ENTRAR", "VOLVER"]
        return []

    def handle_key(self, key, unicode=""):
        d = {pygame.K_UP: UP, pygame.K_w: UP, pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
             pygame.K_LEFT: LEFT, pygame.K_a: LEFT, pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT}.get(key)
        enter = key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
        back = key == pygame.K_ESCAPE

        if self.screen == "round":
            if back:
                self.send({"t": "leave"})
                self.screen = "home"
                self.room = None
            elif d and self.phase == "play" and self.alive.get(self.me):
                self.send({"t": "turn", "d": list(d)})
            elif enter and self.phase == "over":
                pass
            return

        if self.screen == "code":
            letter = (unicode or "").upper()
            if letter and letter in CODE_LETTERS:
                self.code[self.code_pos] = letter
                self.code_pos = min(3, self.code_pos + 1)
            elif key == pygame.K_BACKSPACE:
                self.code_pos = max(0, self.code_pos - 1)
            elif d in (LEFT, RIGHT):
                self.code_pos = (self.code_pos + d[0]) % 4
            elif d in (UP, DOWN):
                i = CODE_LETTERS.index(self.code[self.code_pos])
                self.code[self.code_pos] = CODE_LETTERS[(i - d[1]) % len(CODE_LETTERS)]
            elif enter:
                self.choose(0)
            elif back:
                self.screen = "home"
                self.sel = 2
            return

        rows = self.rows()
        if d in (UP, DOWN) and rows:
            self.sel = (self.sel + d[1]) % len(rows)
        elif enter and rows:
            self.choose(min(self.sel, len(rows) - 1))
        elif back:
            if self.screen in ("room", "wait"):
                self.send({"t": "leave"})
                self.screen, self.room, self.sel = "home", None, 0
            else:
                self.exit()

    def choose(self, i):
        rows = self.rows()
        if self.screen != "code" and not rows:
            return
        if self.screen in ("home", "code") and not self.connected:
            if self.net is None or self.net.status == "closed":
                self.reconnect()
                self.say("CONECTANDO DE NUEVO...")
            if self.screen == "home" and self.HOME_ROWS[i] == "VOLVER":
                self.exit()
            elif self.screen == "code" and i == 1:
                self.screen = "home"
            return
        if self.screen == "home":
            row = self.HOME_ROWS[i]
            g = self.app.game
            if row == "PARTIDA RÁPIDA":
                self.send({"t": "quick"})
                self.screen = "wait"
            elif row == "CREAR SALA":
                self.send({"t": "create", "maze": g.maze_idx, "level": g.level})
                self.screen = "wait"
            elif row == "UNIRSE CON CÓDIGO":
                self.screen, self.code_pos = "code", 0
            else:
                self.exit()
        elif self.screen == "code":
            if i == 0:
                self.send({"t": "join", "code": "".join(self.code)})
                self.screen = "wait"
            else:
                self.screen = "home"
                self.sel = 2
        elif self.screen == "room":
            if rows[i] == "EMPEZAR":
                if len(self.room.get("players", [])) < 2:
                    self.say("HACEN FALTA AL MENOS 2 JUGADORES")
                else:
                    self.send({"t": "start"})
            else:
                self.send({"t": "leave"})
                self.screen, self.room, self.sel = "home", None, 0

    def handle_swipe(self, d):
        self.handle_key(DIRS[d])

    def handle_tap(self, x, y):
        if self.screen == "round" or not self.row_ys:
            return
        i = min(range(len(self.row_ys)), key=lambda k: abs(self.row_ys[k] - y))
        if abs(self.row_ys[i] - y) <= 34 and abs(x - W / 2) <= 320:
            self.sel = i
            self.choose(i)

    # ------------------------------------------------------------ dibujo
    def font(self, size):
        if self.fonts is None:
            self.fonts = {}
        if size not in self.fonts:
            try:
                self.fonts[size] = pygame.font.Font(str(FONT_FILE), size)
            except Exception:
                self.fonts[size] = pygame.font.Font(None, int(size * 1.3))
        return self.fonts[size]

    def text(self, surf, s, size, color, **anchor):
        img = self.font(size).render(s, True, color)
        shadow = self.font(size).render(s, True, (0, 0, 0))
        r = img.get_rect(**anchor)
        surf.blit(shadow, r.move(2, 2))
        surf.blit(img, r)
        return r

    def panel(self, surf, w, h, cy=None):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (W // 2, cy or H // 2)
        box = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(box, (14, 16, 28, 232), box.get_rect(), border_radius=22)
        pygame.draw.rect(box, (*ACCENT, 200), box.get_rect(), 3, border_radius=22)
        surf.blit(box, rect)
        return rect

    def dim(self, surf, alpha=150):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((6, 6, 14, alpha))
        surf.blit(veil, (0, 0))

    def draw_rows(self, surf, rows, top, gap=46):
        self.row_ys = []
        for i, s in enumerate(rows):
            y = top + i * gap
            self.row_ys.append(y)
            sel = i == self.sel
            self.text(surf, f"> {s} <" if sel else s, 30, ACCENT if sel else TEXT, center=(W // 2, y))

    def draw(self, renderer):
        screen = renderer.screen
        if self.screen == "round":
            renderer.draw(self.view)
            self.draw_round_overlay(screen)
        else:
            idle = self.game
            idle.snake, idle.others, idle.food, idle.bonus = [], [], None, None
            idle.frozen = True
            if self.screen != "room":
                idle.set_maze(self.app.game.maze_idx)
            renderer.draw(self.view)
            self.dim(screen)
            getattr(self, "draw_" + self.screen)(screen)
        if self.toast_ms > 0:
            r = self.font(24).size(self.toast)
            box = pygame.Rect(0, 0, r[0] + 40, r[1] + 18)
            box.midbottom = (W // 2, H - 22)
            pygame.draw.rect(screen, (40, 14, 18), box, border_radius=14)
            pygame.draw.rect(screen, WARN, box, 2, border_radius=14)
            self.text(screen, self.toast, 24, TEXT, center=box.center)

    def draw_lock(self, surf, app):
        """Aviso sobre el menu cuando el estilo elegido esta bloqueado."""
        fuerte = app.aviso_ms > 0 and int(app.aviso_ms / 110) % 2 == 0
        if app.plat.invitado:
            linea = "INICIA SESIÓN EN LYNESS-GAMING.COM PARA DESBLOQUEARLO"
        elif app.plat.token and app.plat.estilos is None:
            linea = "REVISANDO TUS ESTILOS..."
        else:
            linea = "CONSÍGUELO CON MONEDAS EN TU PANEL DE LYNESS"
        box = pygame.Rect(0, 0, 640, 66)
        box.midbottom = (W // 2, H - 10)
        fondo = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(fondo, (40, 14, 18, 240) if fuerte else (14, 16, 28, 236), fondo.get_rect(), border_radius=16)
        surf.blit(fondo, box)
        pygame.draw.rect(surf, WARN if fuerte else (250, 204, 21), box, 3, border_radius=16)
        self.text(surf, "ESTILO BLOQUEADO", 24, (250, 204, 21), center=(W // 2, box.top + 22))
        self.text(surf, linea, 17, TEXT, center=(W // 2, box.top + 47))

    def status_line(self, surf, y):
        if self.connected:
            if getattr(self, "nick", None):
                estado = f"CONECTADO COMO {self.nick.upper()}"
            elif self.app.plat.web:
                estado = "CONECTADO COMO INVITADO · SIN PREMIOS"
            else:
                estado = "CONECTADO"
            self.text(surf, estado, 18 if len(estado) > 30 else 20, ACCENT, center=(W // 2, y))
        elif self.net and self.net.status == "connecting":
            dots = "." * (int(self.t * 3) % 4)
            self.text(surf, "CONECTANDO" + dots, 20, DIM, center=(W // 2, y))
        else:
            self.text(surf, "SIN CONEXIÓN CON EL SERVIDOR  ·  ENTER: REINTENTAR", 20, WARN, center=(W // 2, y))

    def draw_home(self, surf):
        box = self.panel(surf, 520, 380)
        self.text(surf, "EN LÍNEA", 54, ACCENT, center=(W // 2, box.top + 54))
        self.text(surf, "DE 2 A 4 JUGADORES  ·  GANA LA ÚLTIMA SERPIENTE", 18, DIM, center=(W // 2, box.top + 100))
        self.draw_rows(surf, self.HOME_ROWS, box.top + 160)
        self.status_line(surf, box.bottom - 30)

    def draw_code(self, surf):
        box = self.panel(surf, 520, 380)
        self.text(surf, "CÓDIGO DE LA SALA", 34, ACCENT, center=(W // 2, box.top + 50))
        for i, ch in enumerate(self.code):
            cell = pygame.Rect(0, 0, 76, 96)
            cell.center = (W // 2 + (i - 1.5) * 92, box.top + 150)
            sel = i == self.code_pos
            pygame.draw.rect(surf, (30, 34, 54), cell, border_radius=14)
            pygame.draw.rect(surf, ACCENT if sel else DIM, cell, 3, border_radius=14)
            self.text(surf, ch, 60, TEXT, center=cell.center)
            if sel:
                self.text(surf, "^", 22, ACCENT, center=(cell.centerx, cell.top - 12))
                self.text(surf, "v", 22, ACCENT, center=(cell.centerx, cell.bottom + 12))
        self.text(surf, "ESCRIBE O USA LAS FLECHAS", 18, DIM, center=(W // 2, box.top + 226))
        self.draw_rows(surf, ["ENTRAR", "VOLVER"], box.top + 276, gap=44)
        self.sel = min(self.sel, 1)

    def draw_wait(self, surf):
        box = self.panel(surf, 460, 200)
        dots = "." * (int(self.t * 3) % 4)
        self.text(surf, "BUSCANDO SALA" + dots, 36, ACCENT, center=(W // 2, box.centery - 18))
        self.text(surf, "ESC: CANCELAR", 20, DIM, center=(W // 2, box.centery + 40))
        self.row_ys = []

    def draw_room(self, surf):
        room = self.room or {}
        players = room.get("players", [])
        quick = room.get("quick")
        box = self.panel(surf, 600, 460)
        if quick:
            self.text(surf, "PARTIDA RÁPIDA", 40, ACCENT, center=(W // 2, box.top + 46))
        else:
            self.text(surf, "SALA", 22, DIM, center=(W // 2, box.top + 32))
            self.text(surf, " ".join(room.get("code", "????")), 56, ACCENT, center=(W // 2, box.top + 76))
        info = f"MAPA {room.get('maze_name', '')}  ·  NIVEL {room.get('level', 5)}" if not quick else \
            "MAPA SORPRESA  ·  NIVEL 5"
        self.text(surf, info, 20, DIM, center=(W // 2, box.top + 120))

        for i in range(room.get("max", 4)):
            y = box.top + 164 + i * 40
            if i < len(players):
                pid = players[i]
                name, col = self.player_label(pid)
                tag = "  (ANFITRIÓN)" if pid == room.get("host") and not quick else ""
                pygame.draw.circle(surf, (0, 0, 0), (W // 2 - 150, y + 1), 12)
                pygame.draw.circle(surf, col, (W // 2 - 150, y), 11)
                self.text(surf, name + tag, 26, TEXT if pid != self.me else ACCENT, midleft=(W // 2 - 126, y))
            else:
                pygame.draw.circle(surf, (60, 64, 84), (W // 2 - 150, y), 11, 2)
                self.text(surf, "esperando...", 22, (90, 96, 120), midleft=(W // 2 - 126, y))

        if quick:
            n = room.get("starts_in")
            msg = f"EMPIEZA EN {n}" if n is not None and len(players) >= 2 else "BUSCANDO RIVALES..."
        elif room.get("host") == self.me:
            msg = "COMPARTE EL CÓDIGO CON TUS AMIGOS" if len(players) < 2 else "TODO LISTO"
        else:
            msg = "ESPERANDO A QUE EL ANFITRIÓN EMPIECE"
        if room.get("state") not in (None, "lobby"):
            msg = "TERMINANDO LA RONDA ANTERIOR..."
        self.text(surf, msg, 22, TEXT, center=(W // 2, box.top + 334))
        rows = self.rows()
        self.sel = min(self.sel, len(rows) - 1)
        self.draw_rows(surf, rows, box.top + 380, gap=42)

    def legend(self, surf):
        """Jugadores de la ronda con su color y puntos, abajo al centro."""
        scores = {s: 0 for s in self.round_players}
        if self.result:
            scores.update({int(k): v for k, v in self.result.get("scores", {}).items()})
        items = []
        for pid in self.round_players:
            name, col = self.player_label(pid)
            items.append((name, col, self.alive.get(pid, False)))
        f = self.font(18)
        widths = [f.size(n)[0] + 34 for n, _, _ in items]
        total = sum(widths) + 12 * (len(items) - 1) + 24
        bar = pygame.Rect(0, 0, total, 34)
        bar.midbottom = (W // 2, H - 8)
        s = pygame.Surface(bar.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (10, 10, 20, 190), s.get_rect(), border_radius=17)
        surf.blit(s, bar)
        x = bar.left + 12
        for (name, col, alive), w in zip(items, widths):
            cx = x + 10
            pygame.draw.circle(surf, col if alive else (90, 90, 100), (cx, bar.centery), 8)
            img = f.render(name, True, TEXT if alive else (110, 110, 125))
            surf.blit(img, img.get_rect(midleft=(cx + 16, bar.centery)))
            if not alive:
                pygame.draw.line(surf, WARN, (cx + 14, bar.centery), (cx + 16 + img.get_width(), bar.centery), 2)
            x += w + 12

    def draw_round_overlay(self, surf):
        self.row_ys = []
        if self.phase == "countdown":
            n = max(1, -(-self.countdown_ms // 1000))
            pygame.draw.circle(surf, (8, 8, 16), (W // 2, H // 2), 74)
            pygame.draw.circle(surf, ACCENT, (W // 2, H // 2), 74, 4)
            self.text(surf, str(n), 96, TEXT, center=(W // 2, H // 2 + 4))
            self.text(surf, "LA QUE PARPADEA ERES TÚ", 22, TEXT, center=(W // 2, H // 2 + 108))
        elif self.phase == "play" and not self.alive.get(self.me):
            box = pygame.Rect(0, 0, 440, 40)
            box.midtop = (W // 2, 110)                  # debajo del marcador de cada estilo
            s = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (40, 10, 16, 210), s.get_rect(), border_radius=20)
            surf.blit(s, box)
            self.text(surf, "ELIMINADO  ·  MIRANDO LA PARTIDA", 22, TEXT, center=box.center)
        elif self.phase == "over" and self.result:
            self.dim(surf, 120)
            box = self.panel(surf, 520, 300)
            winner = self.result.get("winner")
            if winner is None:
                title, col = "EMPATE", TEXT
            elif winner == self.me:
                title, col = "¡GANASTE!", ACCENT
            else:
                name, col = self.player_label(winner)
                title = f"GANÓ {name}"
            self.text(surf, title, 56, col, center=(W // 2, box.top + 64))
            scores = sorted(((int(k), v) for k, v in self.result.get("scores", {}).items()),
                            key=lambda kv: -kv[1])
            for i, (pid, pts) in enumerate(scores[:4]):
                name, c = self.player_label(pid)
                y = box.top + 136 + i * 34
                pygame.draw.circle(surf, c, (W // 2 - 110, y), 9)
                self.text(surf, name, 24, TEXT, midleft=(W // 2 - 90, y))
                self.text(surf, str(pts), 24, TEXT, midright=(W // 2 + 120, y))
            return
        self.legend(surf)
