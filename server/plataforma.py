"""
Conexión del servidor del Snake con la plataforma de Lyness (cuentas, medallas, misiones).

Variables de entorno:
    PLATAFORMA_URL     dirección del backend, p. ej. http://backend-piercinghell:8000
    PLATAFORMA_CLAVE   clave secreta de este juego (la misma que tiene el backend en
                       PLATAFORMA_CLAVES=snake:...)

Si falta alguna, el servidor funciona igual pero sin cuentas ni premios (todos invitados).
Las llamadas se hacen en un hilo aparte para no detener las partidas, y si la plataforma
no responde simplemente no hay premio: el juego nunca se cae por esto.
"""
import asyncio
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger("snake")

JUEGO = "snake"
URL = os.environ.get("PLATAFORMA_URL", "").rstrip("/")
CLAVE = os.environ.get("PLATAFORMA_CLAVE", "")
ACTIVA = bool(URL and CLAVE)


def _post(ruta: str, datos: dict):
    """POST con JSON. Devuelve el JSON de respuesta o None si algo falla."""
    pedido = urllib.request.Request(
        URL + ruta, data=json.dumps(datos).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Clave-Juego": CLAVE})
    try:
        with urllib.request.urlopen(pedido, timeout=6) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code != 401:          # 401 = token vencido o inválido: es normal, entra como invitado
            log.warning("plataforma %s -> HTTP %s", ruta, e.code)
    except Exception as e:
        log.warning("plataforma %s -> %s", ruta, e)
    return None


async def sesion(token: str):
    """¿De quién es este token? Devuelve {"id_account", "nickname", ...} o None."""
    if not ACTIVA or not isinstance(token, str) or not token or len(token) > 400:
        return None
    return await asyncio.to_thread(_post, "/plataforma/interno/sesion", {"game": JUEGO, "token": token})


async def reportar(ref: str, jugadores: list):
    """Manda el resultado de una partida. jugadores: [{"id_account": n, "stats": {...}}, ...]."""
    if not ACTIVA or not jugadores:
        return None
    return await asyncio.to_thread(_post, "/plataforma/interno/reporte",
                                   {"game": JUEGO, "ref": ref, "players": jugadores})
