"""
Reglas del Snake: tablero, mapas, movimiento, comida, bonus, puntos.

No dibuja nada ni hace sonido: solo cambia el estado y anota eventos en
`game.events` (comer, morir, pasar de mapa...). Cada estilo visual decide
como mostrarlos.
"""

import random

COLS, ROWS = 28, 14

FOODS_PER_BONUS = 5
FOODS_PER_STAGE = 12      # comidas para pasar al siguiente mapa
BONUS_TICKS = 20
DYING_MS = 1200           # duracion de la animacion de muerte
STAGE_MS = 2000           # duracion de la pantalla "mapa superado"

# Modos de dificultad: (aceleracion por comida, rocas nuevas cada N comidas o 0)
MODES = {"CLASICO": (1.0, 0), "RAPIDO": (0.97, 0), "EXTREMO": (0.96, 2)}
MODE_NAMES = list(MODES)
ROCKS_MAX = 12            # rocas maximas por mapa en EXTREMO
MIN_TICK_MS = 40          # tope de velocidad

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# Cada mapa: nombre, borde solido (True) o se atraviesa (False),
# rectangulos de pared (col, fila, ancho, alto) e inicio de la serpiente
# (col de la cabeza, fila, direccion).
MAZES = [
    {"name": "LIBRE", "border": False, "walls": [], "start": (8, 7, RIGHT)},
    {"name": "CAJA", "border": True, "walls": [], "start": (8, 7, RIGHT)},
    {"name": "PASILLOS", "border": False,
     "walls": [(0, 3, 11, 1), (17, 3, 11, 1), (0, 10, 11, 1), (17, 10, 11, 1)],
     "start": (8, 7, RIGHT)},
    {"name": "CRUZ", "border": True,
     "walls": [(13, 1, 2, 5), (13, 8, 2, 5), (3, 6, 8, 2), (17, 6, 8, 2)],
     "start": (7, 11, RIGHT)},
    {"name": "COLUMNAS", "border": True,
     "walls": [(5, 0, 1, 9), (11, 5, 1, 9), (17, 0, 1, 9), (23, 5, 1, 9)],
     "start": (5, 11, RIGHT)},
    {"name": "MOLINO", "border": False,
     "walls": [(4, 3, 10, 1), (22, 1, 1, 7), (14, 10, 10, 1), (5, 6, 1, 7)],
     "start": (12, 7, RIGHT)},
    {"name": "REJA", "border": True,
     "walls": [(c, r, 2, 2) for c in (4, 10, 16, 22) for r in (3, 9)],
     "start": (7, 6, RIGHT)},
]


def maze_cells(maze):
    cells = set()
    for c, r, w, h in maze["walls"]:
        for dc in range(w):
            for dr in range(h):
                cells.add((c + dc, r + dr))
    return cells


class Game:
    """Estados: menu, play, pause, dying, stage, over."""

    def __init__(self, level=5, maze_idx=1, record=0, mode="RAPIDO"):
        self.level = level
        self.maze_idx = maze_idx
        self.start_maze = maze_idx   # mapa elegido en el menu (next_stage cambia maze_idx)
        self.record = record
        self.mode = mode if mode in MODES else "RAPIDO"
        self.speed_mult = 1.0      # baja con cada comida (= mas rapido)
        self.rocks = []            # obstaculos que aparecen en modo EXTREMO
        self.events = []
        self.score = 0
        self.new_record = False
        self.snake = []
        self.direction = RIGHT
        self.queue = []
        self.walls = set()
        self.food = None
        self.bonus = None          # (c, r) celda izquierda del bonus (ocupa 2 celdas)
        self.bonus_left = 0
        self.eaten = 0
        self.grow = 0
        self.set_state("menu")

    # --- utilidades
    @property
    def maze(self):
        return MAZES[self.maze_idx]

    @property
    def bonus_cells(self):
        if not self.bonus:
            return ()
        return (self.bonus, (self.bonus[0] + 1, self.bonus[1]))

    @property
    def wall_rects(self):
        """Muros del mapa + rocas (como rectangulos de 1x1) para los estilos que dibujan bloques."""
        return self.maze["walls"] + [(c, r, 1, 1) for c, r in self.rocks]

    def base_tick_ms(self):
        if self.mode == "CLASICO":
            return 270 - self.level * 23          # nivel 1: 247 ms ... nivel 9: 63 ms
        return 190 - self.level * 15              # nivel 1: 175 ms ... nivel 9: 55 ms

    def tick_ms(self):
        base = self.base_tick_ms()
        return max(MIN_TICK_MS, int(base * 0.45), int(base * self.speed_mult))

    def set_state(self, state):
        self.state = state
        self.state_time = 0     # ms en el estado actual (para animaciones)
        self.acc = 0

    def emit(self, kind, **data):
        self.events.append({"type": kind, **data})

    # --- partida
    def start(self):
        # el mapa elegido en el menu es el inicial; al reintentar se vuelve a el
        if self.state == "menu":
            self.start_maze = self.maze_idx
        else:
            self.maze_idx = self.start_maze
        self.score = 0
        self.new_record = False
        self.speed_mult = 1.0      # la velocidad ganada se conserva entre mapas
        self.load_stage()

    def load_stage(self):
        self.rocks = []
        self.walls = maze_cells(self.maze)
        hc, hr, d = self.maze["start"]
        self.snake = [(hc - i * d[0], hr - i * d[1]) for i in range(5)]
        self.direction = d
        self.queue = []
        self.grow = 0
        self.eaten = 0
        self.bonus = None
        self.bonus_left = 0
        self.food = self.free_cell()
        self.set_state("play")

    # pausa sin reiniciar acc: los estilos con movimiento suave no dan saltos
    def pause(self):
        if self.state == "play":
            self.state = "pause"

    def resume(self):
        if self.state == "pause":
            self.state = "play"

    def to_menu(self):
        """Abandona la partida y vuelve al menu con el mapa que se eligio alli."""
        self.maze_idx = self.start_maze
        self.rocks = []
        self.bonus = None
        self.set_state("menu")

    def move_fraction(self):
        """0..1: cuanto ha avanzado el tiempo hacia el siguiente paso (para animar)."""
        if self.state in ("play", "pause"):
            return min(1.0, self.acc / self.tick_ms())
        return 1.0

    def occupied(self):
        return set(self.snake) | self.walls | set(self.bonus_cells)

    def free_cell(self):
        occ = self.occupied()
        free = [(c, r) for c in range(COLS) for r in range(ROWS) if (c, r) not in occ]
        return random.choice(free) if free else None

    def spawn_bonus(self):
        occ = self.occupied() | {self.food}
        spots = [(c, r) for c in range(COLS - 1) for r in range(ROWS)
                 if (c, r) not in occ and (c + 1, r) not in occ]
        if spots:
            self.bonus = random.choice(spots)
            self.bonus_left = BONUS_TICKS

    def spawn_rock(self):
        """Roca nueva lejos de la cabeza y fuera del camino que lleva (para que sea justo)."""
        if len(self.rocks) >= ROCKS_MAX:
            return
        hc, hr = self.snake[0]
        dc, dr = self.direction
        ahead = {((hc + dc * k) % COLS, (hr + dr * k) % ROWS) for k in range(1, 8)}
        occ = self.occupied() | ahead | ({self.food} if self.food else set())
        spots = [(c, r) for c in range(COLS) for r in range(ROWS)
                 if (c, r) not in occ and abs(c - hc) + abs(r - hr) > 4]
        if spots:
            rock = random.choice(spots)
            self.rocks.append(rock)
            self.walls.add(rock)
            self.emit("rock", pos=rock)

    def turn(self, d):
        last = self.queue[-1] if self.queue else self.direction
        if d != last and d != OPPOSITE[last] and len(self.queue) < 2:
            self.queue.append(d)

    def step(self):
        if self.queue:
            self.direction = self.queue.pop(0)
        hc, hr = self.snake[0]
        nc, nr = hc + self.direction[0], hr + self.direction[1]

        if self.maze["border"]:
            if not (0 <= nc < COLS and 0 <= nr < ROWS):
                return self.die()
        else:
            nc %= COLS
            nr %= ROWS
        head = (nc, nr)
        if head in self.walls:
            return self.die()

        eating = head == self.food
        tail_moves = self.grow == 0 and not eating
        body = self.snake[:-1] if tail_moves else self.snake
        if head in body:
            return self.die()

        self.snake.insert(0, head)
        if tail_moves:
            self.snake.pop()
        elif self.grow:
            self.grow -= 1

        if eating:
            self.score += self.level
            self.eaten += 1
            accel, rock_every = MODES[self.mode]
            self.speed_mult *= accel
            self.emit("eat", pos=head)
            if self.maze_idx != 0 and self.eaten >= FOODS_PER_STAGE:
                return self.next_stage()
            if rock_every and self.eaten % rock_every == 0:
                self.spawn_rock()
            self.food = self.free_cell()
            if self.food is None:          # tablero lleno
                return self.die()
            if self.eaten % FOODS_PER_BONUS == 0 and self.bonus is None:
                self.spawn_bonus()

        if self.bonus:
            if head in self.bonus_cells:
                points = self.bonus_left * self.level
                self.score += points
                self.grow += 2
                self.emit("bonus", pos=self.bonus, points=points)
                self.bonus = None
            else:
                self.bonus_left -= 1
                if self.bonus_left <= 0:
                    self.bonus = None

    def next_stage(self):
        self.maze_idx = self.maze_idx % (len(MAZES) - 1) + 1   # LIBRE no entra en el ciclo
        self.set_state("stage")
        self.emit("stage")

    def die(self):
        self.set_state("dying")
        self.emit("die", pos=self.snake[0])
        if self.score > self.record:
            self.record = self.score
            self.new_record = True
            self.emit("record")

    # --- tiempo
    def update(self, dt):
        self.state_time += dt
        if self.state == "play":
            self.acc += dt
            while self.acc >= self.tick_ms() and self.state == "play":
                self.acc -= self.tick_ms()
                self.step()
        elif self.state == "dying" and self.state_time >= DYING_MS:
            self.set_state("over")
        elif self.state == "stage" and self.state_time >= STAGE_MS:
            self.load_stage()
