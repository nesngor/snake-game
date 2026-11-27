"""
Servidor del Snake EN LINEA (WebSocket).

Lleva todas las partidas: los jugadores solo mandan sus giros y reciben el
estado del tablero en cada paso, asi nadie puede hacer trampa desde su navegador.

    python server/snake_server.py            (escucha en 0.0.0.0:8765)

Variables de entorno:
    SNAKE_HOST, SNAKE_PORT   donde escuchar (0.0.0.0, 8765)
    SNAKE_ORIGINS            origenes permitidos separados por coma (vacio = todos),
                             p. ej. "https://lyness-gaming.com,https://nesngor.github.io"
    SNAKE_MAX_ROOMS          salas simultaneas como maximo (300)

Mensajes (JSON). Del jugador al servidor:
    {"t": "quick"}                              partida rapida con quien este esperando
    {"t": "create", "maze": 1, "level": 5}      sala nueva con codigo
    {"t": "join", "code": "ABCD"}               entrar a una sala
    {"t": "start"}                              el anfitrion empieza la ronda
    {"t": "turn", "d": [1, 0]}                  girar
    {"t": "leave"}                              salir de la sala
Del servidor al jugador:
    {"t": "room", ...}     quien esta en la sala y en que estado
    {"t": "round", ...}    empieza una ronda (mapa, velocidad, cuenta regresiva)
    {"t": "state", ...}    tablero en cada paso, con los eventos (comer, morir...)
    {"t": "over", ...}     fin de la ronda: ganador y puntos
    {"t": "error", "msg"}  algo salio mal (sala llena, codigo invalido...)
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
from pathlib import Path

from websockets.asyncio.server import serve, broadcast
from websockets.exceptions import ConnectionClosed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from game import MAZES                                     # noqa: E402
from versus import Versus, MAX_PLAYERS, tick_ms            # noqa: E402

log = logging.getLogger("snake")

CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # sin I ni O (se confunden con 1 y 0)
COUNTDOWN_S = 3
RESULTS_S = 4
QUICK_WAIT_S = 6           # partida rapida: espera a mas rivales antes de empezar
QUICK_LEVEL = 5
MAX_ROOMS = int(os.environ.get("SNAKE_MAX_ROOMS", "300"))
MAX_MSGS_PER_S = 30


class Player:
    def __init__(self, ws, pid):
        self.ws = ws
        self.pid = pid
        self.room = None
        self.msg_times = []

    def flooding(self):
        now = time.monotonic()
        self.msg_times = [t for t in self.msg_times if now - t < 1.0]
        self.msg_times.append(now)
        return len(self.msg_times) > MAX_MSGS_PER_S


class Room:
    def __init__(self, code, quick, maze_idx, level):
        self.code = code
        self.quick = quick
        self.maze_idx = maze_idx
        self.level = level
        self.players = []          # en orden de llegada: el primero es el anfitrion
        self.state = "lobby"       # lobby, countdown, play, results
        self.game = None
        self.task = None
        self.auto_start_at = None  # partida rapida: cuando empieza sola
        self.last_winner = None

    @property
    def host(self):
        return self.players[0] if self.players else None

    def send_all(self, msg):
        broadcast([p.ws for p in self.players], json.dumps(msg, separators=(",", ":")))

    def room_msg(self, p):
        return {"t": "room", "code": self.code, "quick": self.quick, "you": p.pid,
                "host": self.host.pid if self.host else None, "state": self.state,
                "maze": self.maze_idx, "maze_name": MAZES[self.maze_idx]["name"], "level": self.level,
                "players": [q.pid for q in self.players], "max": MAX_PLAYERS,
                "starts_in": max(0, round(self.auto_start_at - time.monotonic())) if self.auto_start_at else None}

    def announce(self):
        for p in self.players:
            asyncio.ensure_future(safe_send(p, self.room_msg(p)))


rooms = {}                 # codigo -> Room
next_pid = 0


async def safe_send(p, msg):
    try:
        await p.ws.send(json.dumps(msg, separators=(",", ":")))
    except ConnectionClosed:
        pass


def new_code():
    for _ in range(1000):
        code = "".join(random.choice(CODE_LETTERS) for _ in range(4))
        if code not in rooms:
            return code
    return None


def make_room(quick, maze_idx, level):
    if len(rooms) >= MAX_ROOMS:
        return None
    code = new_code()
    if not code:
        return None
    room = Room(code, quick, maze_idx, level)
    rooms[code] = room
    return room


def join(p, room):
    leave(p)
    room.players.append(p)
    p.room = room
    if room.quick and room.state == "lobby":
        if len(room.players) >= MAX_PLAYERS:
            room.auto_start_at = time.monotonic()
        elif len(room.players) >= 2 and room.auto_start_at is None:
            room.auto_start_at = time.monotonic() + QUICK_WAIT_S
    room.announce()


def leave(p):
    room = p.room
    if not room:
        return
    p.room = None
    if p in room.players:
        room.players.remove(p)
    if room.game and room.state in ("countdown", "play"):
        room.game.kill(p.pid)
    if not room.players:
        if room.task:
            room.task.cancel()
        rooms.pop(room.code, None)
        return
    if room.quick and room.state == "lobby" and len(room.players) < 2:
        room.auto_start_at = None
    room.announce()


async def run_round(room):
    """Cuenta regresiva, partida y resultados; despues la sala vuelve a esperar."""
    try:
        if room.quick:
            room.maze_idx = random.randrange(len(MAZES))
        pids = [p.pid for p in room.players]
        game = room.game = Versus(pids, room.maze_idx)
        ms = tick_ms(room.level)
        room.state = "countdown"
        room.auto_start_at = None
        room.send_all({"t": "round", "maze": room.maze_idx, "level": room.level, "tick_ms": ms,
                       "players": pids, "countdown": COUNTDOWN_S})
        room.send_all({"t": "state", **game.to_json(), "ev": []})
        await asyncio.sleep(COUNTDOWN_S)

        room.state = "play"
        game.events.clear()          # quien se fue durante la cuenta regresiva ya cuenta como eliminado
        next_t = time.monotonic()
        while not game.over:
            next_t += ms / 1000
            await asyncio.sleep(max(0, next_t - time.monotonic()))
            game.step()
            room.send_all({"t": "state", **game.to_json(), "ev": game.events})
            game.events = []

        room.state = "results"
        room.last_winner = game.winner
        room.send_all({"t": "over", "winner": game.winner,
                       "scores": {s.pid: s.score for s in game.snakes.values()}})
        await asyncio.sleep(RESULTS_S)
    except asyncio.CancelledError:
        return
    except Exception:
        log.exception("error en la sala %s", room.code)
    room.state = "lobby"
    room.game = None
    room.task = None
    if room.quick and len(room.players) >= 2:
        room.auto_start_at = time.monotonic() + QUICK_WAIT_S
    room.announce()


def start_round(room):
    if room.state == "lobby" and len(room.players) >= 2 and room.task is None:
        room.task = asyncio.ensure_future(run_round(room))


async def quick_starter():
    """Arranca solas las partidas rapidas cuando se cumple la espera."""
    while True:
        await asyncio.sleep(0.5)
        now = time.monotonic()
        for room in list(rooms.values()):
            if room.quick and room.state == "lobby" and room.auto_start_at:
                if len(room.players) < 2:
                    room.auto_start_at = None
                elif now >= room.auto_start_at:
                    start_round(room)
                elif int(now * 2) % 2 == 0:
                    room.announce()      # actualiza la cuenta "empieza en N"


def as_int(value, lo, hi, default):
    try:
        return min(hi, max(lo, int(value)))
    except (TypeError, ValueError):
        return default


async def handle(p, msg):
    t = msg.get("t")
    room = p.room
    if t == "turn":
        if room and room.game and room.state == "play":
            room.game.turn(p.pid, msg.get("d"))
    elif t == "quick":
        target = next((r for r in rooms.values()
                       if r.quick and r.state == "lobby" and len(r.players) < MAX_PLAYERS), None)
        target = target or make_room(True, 0, QUICK_LEVEL)
        if target:
            join(p, target)
        else:
            await safe_send(p, {"t": "error", "msg": "SERVIDOR LLENO, INTENTA MÁS TARDE"})
    elif t == "create":
        room = make_room(False, as_int(msg.get("maze"), 0, len(MAZES) - 1, 1),
                         as_int(msg.get("level"), 1, 9, 5))
        if room:
            join(p, room)
        else:
            await safe_send(p, {"t": "error", "msg": "SERVIDOR LLENO, INTENTA MÁS TARDE"})
    elif t == "join":
        code = str(msg.get("code", "")).upper()[:4]
        target = rooms.get(code)
        if not target or target.quick:
            await safe_send(p, {"t": "error", "msg": f"NO EXISTE LA SALA {code}"})
        elif len(target.players) >= MAX_PLAYERS:
            await safe_send(p, {"t": "error", "msg": "LA SALA ESTÁ LLENA"})
        elif target.state != "lobby":
            await safe_send(p, {"t": "error", "msg": "ESA SALA ESTÁ JUGANDO, ESPERA UN MOMENTO"})
        else:
            join(p, target)
    elif t == "start":
        if room and not room.quick and room.host is p:
            start_round(room)
    elif t == "leave":
        leave(p)


async def connection(ws):
    global next_pid
    origins = [o.strip() for o in os.environ.get("SNAKE_ORIGINS", "").split(",") if o.strip()]
    origin = ws.request.headers.get("Origin") if ws.request else None
    if origins and origin not in origins:
        await ws.close(1008, "origen no permitido")
        return
    next_pid += 1
    p = Player(ws, next_pid)
    try:
        await ws.send(json.dumps({"t": "hello", "you": p.pid}))
        async for raw in ws:
            if p.flooding():
                continue
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if isinstance(msg, dict):
                await handle(p, msg)
    except ConnectionClosed:
        pass
    finally:
        leave(p)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    host = os.environ.get("SNAKE_HOST", "0.0.0.0")
    port = int(os.environ.get("SNAKE_PORT", "8765"))
    asyncio.ensure_future(quick_starter())
    async with serve(connection, host, port, max_size=1024, ping_interval=20, ping_timeout=20):
        log.info("Snake en linea escuchando en %s:%s", host, port)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
