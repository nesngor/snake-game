"""
Plataforma de Lyness dentro del juego: sesión del jugador, estilos desbloqueados y reporte
de las partidas en solitario (medallas y misiones diarias).

Solo actúa en la versión web. La sesión es la que guarda el sitio lyness-gaming.com al
entrar al panel; el juego la lee porque se sirve desde el mismo dominio. Sin sesión (o en
otra página, como GitHub Pages) se juega como invitado: solo los estilos gratis y sin premios.

En la PC (python main.py) no hay plataforma: todos los estilos están disponibles.
"""
import net

# Estilos que todos tienen (los mismos que el catálogo del servidor marca como gratis).
ESTILOS_GRATIS = ("nokia", "neon", "pixel", "papel", "arcade")


class Plataforma:
    def __init__(self):
        self.web = net.WEB
        self.token = net.session_token()
        self.api = net.Api() if self.web else None
        self.estilos = None          # claves de los estilos que tiene la cuenta (None = aún no se sabe)
        if self.token and self.api:
            self.api.call("GET", "/plataforma/juego/snake/", self.token, None, self._estado)

    @property
    def invitado(self):
        return self.web and not self.token

    def _estado(self, status, body):
        if status == 200 and isinstance(body, dict):
            self.estilos = {s.get("key") for s in body.get("skins", []) if s.get("owned")}
        elif status == 401:          # sesión vencida: se sigue como invitado
            self.token = ""

    def desbloqueado(self, clave):
        """¿Puede usar este estilo? En la PC siempre; en la web, los gratis y los comprados."""
        if not self.web or clave in ESTILOS_GRATIS:
            return True
        return bool(self.estilos) and clave in self.estilos

    def reportar_solitario(self, stats):
        """Cuenta una partida en solitario para medallas y misiones (solo con sesión)."""
        if self.token and self.api:
            self.api.call("POST", "/plataforma/juego/snake/reporte", self.token, {"stats": stats}, None)

    def update(self):
        if self.api:
            self.api.update()
