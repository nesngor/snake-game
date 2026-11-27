"""
Reglas del modo EN LINEA: de 2 a 4 serpientes en el mismo tablero.

Lo usa el servidor (server/snake_server.py), que es quien lleva la partida: los
jugadores solo mandan sus giros y reciben el estado. No dibuja ni usa pygame.

Gana la ultima serpiente viva. Chocar con una pared, con tu cuerpo o con otra
serpiente te elimina; si dos cabezas chocan, caen las dos.
"""

import random

from game import COLS, ROWS, MAZES, OPPOSITE, UP, DOWN, LEFT, RIGHT, maze_cells, BONUS_TICKS

MAX_PLAYERS = 4
START_LEN = 4
FOODS_PER_BONUS = 4
EAT_POINTS = 1
BONUS_POINTS = 3
DIRS = {(0, -1): UP, (0, 1): DOWN, (-1, 0): LEFT, (1, 0): RIGHT}

# Lugar preferido de salida de cada jugador: (col de la cabeza, fila, direccion).
# Si ahi hay muros, se busca el sitio libre mas cercano.
SPAWNS = [(6, 2, RIGHT), (21, 11, LEFT), (25, 4, DOWN), (2, 9, UP)]


def tick_ms(level):
    """Velocidad de la partida segun el nivel (1..9), igual que el modo RAPIDO."""
    return 190 - max(1, min(9, level)) * 15


class Snake:
    def __init__(self, pid, body, direction):
        self.pid = pid
        self.body = body          # [(c, r), ...] cabeza primero
        self.direction = direction
        self.queue = []
        self.alive = True
        self.grow = 0
        self.score = 0

    def to_json(self):
        return {"id": self.pid, "body": self.body, "dir": self.direction,
                "alive": self.alive, "score": self.score}


class Versus:
    def __init__(self, pids, maze_idx, rnd=None):
        self.rnd = rnd or random.Random()
        self.maze_idx = maze_idx % len(MAZES)
        self.maze = MAZES[self.maze_idx]
        self.walls = maze_cells(self.maze)
        self.snakes = {}
        for slot, pid in enumerate(pids):
            body, d = self.spawn(slot)
            self.snakes[pid] = Snake(pid, body, d)
        self.food = None
        self.bonus = None
        self.bonus_left = 0
        self.eaten = 0
        self.tick = 0
        self.events = []
        self.over = False
        self.winner = None
        self.food = self.free_cell()

    # --- tablero
    def wrap(self, c, r):
        """Celda siguiente o None si se sale de un mapa con borde."""
        if self.maze["border"]:
            return (c, r) if 0 <= c < COLS and 0 <= r < ROWS else None
        return c % COLS, r % ROWS

    def occupied(self):
        cells = set(self.walls)
        for s in self.snakes.values():
            if s.alive:
                cells.update(s.body)
        return cells

    def bonus_cells(self):
        if not self.bonus:
            return ()
        return (self.bonus, (self.bonus[0] + 1, self.bonus[1]))

    def free_cell(self):
        occ = self.occupied() | set(self.bonus_cells())
        free = [(c, r) for c in range(COLS) for r in range(ROWS) if (c, r) not in occ]
        return self.rnd.choice(free) if free else None

    def spawn(self, slot):
        """Cuerpo recto de START_LEN celdas, lejos de muros y de las otras serpientes."""
        pc, pr, d = SPAWNS[slot % len(SPAWNS)]
        taken = set()
        for s in self.snakes.values():
            for c, r in s.body:
                taken.update((c + dc, r + dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1))
        cells = sorted(((c, r) for c in range(COLS) for r in range(ROWS)),
                       key=lambda p: abs(p[0] - pc) + abs(p[1] - pr))
        for hc, hr in cells:
            body = [(hc - i * d[0], hr - i * d[1]) for i in range(START_LEN)]
            ahead = [(hc + k * d[0], hr + k * d[1]) for k in range(1, 4)]
            if all(0 <= c < COLS and 0 <= r < ROWS and (c, r) not in self.walls and (c, r) not in taken
                   for c, r in body + ahead):
                return body, d
        return [(pc, pr)], d     # no deberia pasar: todos los mapas tienen sitio de sobra

    # --- jugadores
    def turn(self, pid, d):
        s = self.snakes.get(pid)
        d = DIRS.get(tuple(d)) if isinstance(d, (list, tuple)) and len(d) == 2 else None
        if not s or not s.alive or d is None:
            return
        last = s.queue[-1] if s.queue else s.direction
        if d != last and d != OPPOSITE[last] and len(s.queue) < 2:
            s.queue.append(d)

    def kill(self, pid):
        """Elimina a un jugador (por ejemplo, si se desconecta)."""
        s = self.snakes.get(pid)
        if s and s.alive:
            s.alive = False
            self.events.append({"type": "die", "id": pid, "pos": s.body[0]})
            self.check_end()

    # --- un paso de la partida
    def step(self):
        if self.over:
            return
        self.tick += 1
        alive = [s for s in self.snakes.values() if s.alive]
        heads = {}
        for s in alive:
            if s.queue:
                s.direction = s.queue.pop(0)
            hc, hr = s.body[0]
            heads[s.pid] = self.wrap(hc + s.direction[0], hr + s.direction[1])

        eating = {pid for pid, h in heads.items() if h is not None and h == self.food}
        # las colas que se mueven dejan libre su celda en este mismo paso
        blocked = set(self.walls)
        for s in alive:
            moves_tail = s.grow == 0 and s.pid not in eating
            blocked.update(s.body[:-1] if moves_tail else s.body)

        dead = set()
        for pid, h in heads.items():
            if h is None or h in blocked:
                dead.add(pid)
            elif any(h == h2 for p2, h2 in heads.items() if p2 != pid):
                dead.add(pid)                       # choque de cabezas: caen las dos

        for s in alive:
            if s.pid in dead:
                s.alive = False
                self.events.append({"type": "die", "id": s.pid, "pos": s.body[0]})
                continue
            head = heads[s.pid]
            s.body.insert(0, head)
            if s.pid in eating:
                s.score += EAT_POINTS
                self.events.append({"type": "eat", "id": s.pid, "pos": head})
            elif s.grow:
                s.grow -= 1
            else:
                s.body.pop()

        if eating - dead:                           # si quien iba a comer murio, la comida sigue ahi
            self.eaten += 1
            self.food = self.free_cell()
            if self.eaten % FOODS_PER_BONUS == 0 and self.bonus is None:
                self.spawn_bonus()

        if self.bonus:
            taker = next((s for s in self.snakes.values() if s.alive and s.body[0] in self.bonus_cells()), None)
            if taker:
                taker.score += BONUS_POINTS
                taker.grow += 2
                self.events.append({"type": "bonus", "id": taker.pid, "pos": self.bonus,
                                    "points": BONUS_POINTS})
                self.bonus = None
            else:
                self.bonus_left -= 1
                if self.bonus_left <= 0:
                    self.bonus = None
        self.check_end()

    def spawn_bonus(self):
        occ = self.occupied() | ({self.food} if self.food else set())
        spots = [(c, r) for c in range(COLS - 1) for r in range(ROWS)
                 if (c, r) not in occ and (c + 1, r) not in occ]
        if spots:
            self.bonus = self.rnd.choice(spots)
            self.bonus_left = BONUS_TICKS

    def check_end(self):
        alive = [s for s in self.snakes.values() if s.alive]
        if len(alive) <= 1 and not self.over:
            self.over = True
            self.winner = alive[0].pid if alive else None   # None = empate

    def to_json(self):
        return {"tick": self.tick, "snakes": [s.to_json() for s in self.snakes.values()],
                "food": self.food, "bonus": self.bonus, "bonus_left": self.bonus_left}
