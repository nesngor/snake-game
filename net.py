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
