"""
Contrato de un estilo visual.

Para crear un estilo nuevo:
  1. Hereda de Renderer y pon NAME, KEY y OPTIONS.
  2. Implementa draw(app): dibuja TODO en self.screen segun app.game.state
     (menu, play, pause, dying, stage, over). No hagas flip, lo hace main.py.
  3. Opcional: on_event(ev) para efectos (particulas al comer, temblor al morir)
     y update(dt) para animarlos.
  4. Registralo en styles/__init__.py.

Datos utiles dentro de draw(app):
  app.game             estado del juego (snake, food, walls, score, maze...)
  app.menu_rows()      [(etiqueta, valor), ...] para dibujar el menu
  app.menu_sel         fila seleccionada del menu
  app.opt(i)           indice elegido de la opcion i de este estilo
  pause_items(app)     opciones del menu de pausa (CONTINUAR / MENU PRINCIPAL)
"""

WIDTH, HEIGHT = 960, 576   # tamano de ventana comun a todos los estilos


def smooth_runs(g):
    """Posiciones (col, fila) con decimales para que la serpiente se deslice entre casillas.
    Devuelve tramos (listas de (c, r), cabeza primero) cortados donde cruza el borde."""
    frac = g.move_fraction()
    prev = g.snake[1:] + g.snake[-1:]          # donde estaba cada segmento antes
    runs, run, last = [], [], None
    for (c, r), (pc, pr) in zip(g.snake, prev):
        if abs(pc - c) > 1 or abs(pr - r) > 1:  # cruzo el borde: no interpolar
            pc, pr = c, r
        p = (pc + (c - pc) * frac, pr + (r - pr) * frac)
        if last and abs(p[0] - last[0]) + abs(p[1] - last[1]) > 1.5:
            runs.append(run)
            run = []
        run.append(p)
        last = p
    runs.append(run)
    return runs


def pause_items(app, labels=None):
    """[(texto, seleccionada), ...] para el menu de pausa. La opcion elegida va entre > <.
    labels permite que un estilo use sus propios textos (mismo orden que App.PAUSE_ROWS)."""
    labels = labels or app.PAUSE_ROWS
    return [(f"> {s} <" if i == app.pause_sel else s, i == app.pause_sel)
            for i, s in enumerate(labels)]


class Renderer:
    NAME = "?"          # nombre en el menu
    KEY = "?"           # clave para guardar opciones
    OPTIONS = []        # [(etiqueta, [valores...]), ...] opciones propias del estilo

    def __init__(self, screen):
        self.screen = screen

    def on_event(self, ev):
        pass

    def update(self, dt):
        pass

    def draw(self, app):
        raise NotImplementedError
