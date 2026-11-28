"""
Conexion con el servidor EN LINEA, igual en PC y en el navegador.

    net = connect(url)       empieza a conectar (no bloquea)
    net.status               "connecting", "open" o "closed"
    net.send({...})          manda un mensaje (se ignora si no hay conexion)
    net.poll()               lista de mensajes recibidos desde la ultima vez
    net.close()

En el navegador (pygbag) se usa el WebSocket de JavaScript; en la PC, la
libreria `websockets` en un hilo aparte para no trabar el juego.
"""

import json
import os
import sys

WEB = sys.platform == "emscripten"
DEFAULT_SERVER = "wss://lyness-gaming.com/snake-ws"

_JS = """
window.snakeNet = window.snakeNet || {
  ws: null, q: [], st: "closed",
  open(url) {
    this.close(); this.q = []; this.st = "connecting";
    try {
      const ws = new WebSocket(url);
      this.ws = ws;
      ws.onopen = () => { if (this.ws === ws) this.st = "open"; };
      ws.onmessage = (e) => { if (this.ws === ws) this.q.push(e.data); };
      ws.onclose = () => { if (this.ws === ws) this.st = "closed"; };
    } catch (e) { this.st = "closed"; }
  },
  send(s) { if (this.ws && this.ws.readyState === 1) this.ws.send(s); },
  poll() { const s = "[" + this.q.join(",") + "]"; this.q = []; return s; },
  status() { return this.st; },
  close() { if (this.ws) { const ws = this.ws; this.ws = null; try { ws.close(); } catch (e) {} } this.st = "closed"; }
};
"""


def server_url():
    """wss://<este sitio>/snake-ws; se puede cambiar con ?server=... (web) o SNAKE_SERVER (PC)."""
    if not WEB:
        return os.environ.get("SNAKE_SERVER", "ws://127.0.0.1:8765")
    import platform
    js = platform.window.eval
    override = str(js("new URLSearchParams(location.search).get('server') || ''"))
    if override:
        return override
    host = str(js("location.host"))
    # en GitHub Pages (u otro sitio sin servidor propio) se usa el de Lyness
    if host.endswith("github.io") or not host:
        return DEFAULT_SERVER
    scheme = "wss" if str(js("location.protocol")) == "https:" else "ws"
    return f"{scheme}://{host}/snake-ws"


class WebNet:
    def __init__(self, url):
        import platform
        platform.window.eval(_JS)
        self.js = platform.window.snakeNet
        self.js.open(url)

    @property
    def status(self):
        return str(self.js.status())

    def send(self, msg):
        self.js.send(json.dumps(msg))

    def poll(self):
        try:
            return json.loads(str(self.js.poll()))
        except ValueError:
            return []

    def close(self):
        self.js.close()


class DesktopNet:
    def __init__(self, url):
        import queue
        import threading
        self.inbox = queue.Queue()
        self.ws = None
        self.status = "connecting"
        self.thread = threading.Thread(target=self.run, args=(url,), daemon=True)
        self.thread.start()

    def run(self, url):
        try:
            from websockets.sync.client import connect as ws_connect
            with ws_connect(url, open_timeout=6, max_size=1 << 20) as ws:
                self.ws = ws
                self.status = "open"
                for raw in ws:
                    self.inbox.put(raw)
        except Exception:
            pass
        self.status = "closed"

    def send(self, msg):
        if self.ws and self.status == "open":
            try:
                self.ws.send(json.dumps(msg))
            except Exception:
                self.status = "closed"

    def poll(self):
        out = []
        while not self.inbox.empty():
            try:
                out.append(json.loads(self.inbox.get_nowait()))
            except ValueError:
                pass
        return out

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.status = "closed"


def connect(url=None):
    url = url or server_url()
    return WebNet(url) if WEB else DesktopNet(url)


# ---------------------------------------------------------------- plataforma de Lyness (solo web)
API_BASE = "https://piercinghell.lyness-gaming.com"

_JS_SESION = """
(function () {
  try {
    var s = JSON.parse(localStorage.getItem("lyness.session") || "null");
    return s && s.token && s.expiresAt > Date.now() ? s.token : "";
  } catch (e) { return ""; }
})()
"""

_JS_API = """
window.snakeApi = window.snakeApi || {
  q: [],
  call(id, method, url, token, body) {
    const h = {};
    if (token) h["Authorization"] = "Bearer " + token;
    if (body) h["Content-Type"] = "application/json";
    fetch(url, { method: method, headers: h, body: body || undefined })
      .then((r) => r.json().then((j) => ({ status: r.status, body: j }), () => ({ status: r.status, body: null })))
      .catch(() => ({ status: 0, body: null }))
      .then((res) => this.q.push(JSON.stringify({ id: id, status: res.status, body: res.body })));
  },
  poll() { const s = "[" + this.q.join(",") + "]"; this.q = []; return s; }
};
"""


def session_token():
    """Token de la sesión que guarda el sitio de Lyness al entrar al panel ("" si no hay).
    Solo existe en la web y cuando el juego se sirve desde el mismo dominio que el sitio."""
    if not WEB:
        return os.environ.get("LYNESS_TOKEN", "")      # solo para pruebas en la PC
    try:
        import platform
        return str(platform.window.eval(_JS_SESION) or "")
    except Exception:
        return ""


def api_base():
    """Dirección del backend; para pruebas se cambia con localStorage["lyness.api"] = "http://..."."""
    if not WEB:
        return API_BASE
    try:
        import platform
        otra = str(platform.window.eval("localStorage.getItem('lyness.api') || ''"))
        return otra.rstrip("/") or API_BASE
    except Exception:
        return API_BASE


class Api:
    """Llamadas HTTP al backend desde el navegador, sin bloquear el juego.

        api.call("GET", "/ruta", token, None, al_responder)   # al_responder(status, body)
        api.update()                                           # en cada fotograma
    """

    def __init__(self):
        import platform
        platform.window.eval(_JS_API)
        self.js = platform.window.snakeApi
        self.base = api_base()
        self.pendientes = {}
        self.siguiente = 0

    def call(self, method, path, token=None, body=None, callback=None):
        self.siguiente += 1
        self.pendientes[self.siguiente] = callback
        self.js.call(self.siguiente, method, self.base + path, token or "", json.dumps(body) if body is not None else "")

    def update(self):
        try:
            respuestas = json.loads(str(self.js.poll()))
        except ValueError:
            return
        for r in respuestas:
            callback = self.pendientes.pop(r.get("id"), None)
            if callback:
                callback(r.get("status", 0), r.get("body"))
