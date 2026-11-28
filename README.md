# snake-game

Snake hecho con Pygame (pygame-ce), con **14 estilos visuales**, 7 mapas, modos de dificultad, **multijugador en línea** (2 a 4 jugadores) y versión web.

🎮 **Juega en línea:** https://nesngor.github.io/snake-game/

## Estilos

| Estilo | Descripción | Opciones propias |
|---|---|---|
| **NOKIA** | Pantalla LCD monocroma de celular clásico | Pantalla (5 colores), Serpiente (5 formas) |
| **NEON** | Líneas brillantes con bloom, chispas y temblor | Tema (Synthwave, Tóxico, Fuego, Hielo) |
| **PIXEL** | Pixel art de 16 bits con contornos y sombras | Mundo (Pradera, Desierto, Nieve, Mazmorra), Serpiente |
| **3D** | Tablero en perspectiva con cubos, sombras y gema giratoria | Tema, Cámara (normal, baja, alta) |
| **PAPEL** | Dibujado a mano en cuaderno o pizarra, trazos que "hierven" | Hoja (cuadros, rayas, kraft, pizarra), Tinta |
| **ANIME** | Kawaii pastel: serpiente chibi, sakura y textos manga | Tema, Comida (onigiri, fresa, dango) |
| **ARCADE** | Maquinita de los 80 con efectos de pantalla CRT | Monitor (color, verde, ámbar), CRT |
| **DEV** | Editor de código: la serpiente es código y la comida son bugs | Tema, Lenguaje (Python, JavaScript, SQL, C) |
| **ESPACIO** | Cometa entre planetas y asteroides, salto hiperespacial | Sector, Cometa |
| **MUERTOS** | Día de Muertos: alebrije, papel picado, talavera y calaveritas | Ambiente, Ofrenda |
| **OCEANO** | Serpiente marina entre corales, peces y cofre del tesoro | Agua (incluye Abismo bioluminiscente), Criatura |
| **PLASTILINA** | Todo modelado en plastilina con huellas, sombras y temblor de stop-motion; al morir queda aplastada | Mesa (tapete de corte, madera, cartón), Color (verde, arcoíris, rayas) |
| **VITRAL** | Ventana de catedral: vidrio emplomado, rayos de luz y una serpiente de joyas que se hace añicos | Ventana (rosetón, Tiffany, moderno), Luz (día, atardecer, noche) |
| **CIRCUITO** | Placa electrónica: la serpiente es una pista de cobre con pulsos de señal y cabeza de chip; muros de circuitos integrados, marcador de 7 segmentos y pantallas LCD; al morir hace cortocircuito | Placa (verde, azul, negra, morada), Pulso (cian, rojo, ámbar) |

## Cómo jugar

```bash
pip install -r requirements.txt
python main.py
```

| Tecla | Acción |
|---|---|
| Flechas / WASD | Mover |
| P o ESC | Pausa (y continuar) |
| Pausa: ↑ ↓ + Enter | Continuar o volver al menú principal |
| Pausa: M | Volver al menú principal |
| Espacio / Enter | Empezar / reintentar |
| Menú: ↑ ↓ | Elegir opción |
| Menú: ← → | Cambiar valor |

En el celular (también funciona con el mouse):

| Gesto | Acción |
|---|---|
| Deslizar | Mover la serpiente; en el menú, elegir opción (↑ ↓) y cambiar valor (← →) |
| Tocar | Empezar / reintentar; durante el juego, pausa |
| Pausa: tocar una opción | Continuar o volver al menú principal |
| Fin del juego: deslizar | Volver al menú |

### Modos de dificultad

- **CLASICO**: velocidad constante.
- **RAPIDO** (por defecto): cada comida acelera un 3 %; la velocidad se conserva entre mapas.
- **EXTREMO**: acelera un 4 % por comida y cada 2 comidas aparece una roca nueva (nunca junto a la cabeza ni en tu camino).

Cada 12 comidas pasas al siguiente mapa (LIBRE, CAJA, PASILLOS, CRUZ, COLUMNAS, MOLINO, REJA). Cada 5 comidas aparece un bonus que da más puntos mientras antes lo agarres.

## En línea (multijugador)

En el menú, pon **MODO → EN LINEA** y presiona Espacio. Juegan de 2 a 4 serpientes en el mismo tablero y gana la última que quede viva: chocar con una pared, con tu cuerpo o con otra serpiente te elimina (si dos cabezas chocan, caen las dos). La comida y el bonus funcionan igual que en el juego normal.

- **Partida rápida**: te junta con quien esté esperando; la ronda empieza sola a los pocos segundos de haber 2 jugadores (o al llegar a 4). El mapa es sorpresa.
- **Crear sala**: te da un código de 4 letras para tus amigos; usa el MAPA y el NIVEL que tengas elegidos en el menú. Tú decides cuándo empezar.
- **Unirse con código**: escribe el código (o elígelo con las flechas / deslizando).

Tu serpiente conserva el aspecto del estilo que tengas elegido y las rivales salen en rojo, azul y amarillo (en NOKIA, con otra forma). En la cuenta regresiva, la tuya parpadea. Si te eliminan, sigues viendo la partida.

### Servidor

El servidor lleva todas las partidas (los jugadores solo mandan sus giros), así que nadie puede hacer trampa desde su navegador. Está en `server/` y usa las reglas de `versus.py`:

```bash
pip install -r server/requirements.txt
python server/snake_server.py              # escucha en 0.0.0.0:8765
```

Con contenedores (desde la raíz del repo):

```bash
podman build -f server/Containerfile -t snake-server .
podman run -d --name snake-server --network <red-del-sitio> --restart=always snake-server
```

Variables: `SNAKE_PORT` (8765), `SNAKE_ORIGINS` (orígenes permitidos separados por coma; vacío = todos) y `SNAKE_MAX_ROOMS` (300).

El juego se conecta a `wss://<el mismo sitio>/snake-ws`, así que el nginx del sitio debe reenviar esa ruta al servidor (ver `nginx.conf` de lyness-frontend). Desde GitHub Pages usa el servidor de lyness-gaming.com. Para probar con otro servidor: `?server=ws://127.0.0.1:8765` en la URL (web) o la variable `SNAKE_SERVER` (PC).

## Versión web

El juego corre en el navegador con [pygbag](https://github.com/pygame-web/pygbag) (WebAssembly):

```bash
cd ..                                  # carpeta que contiene a snake-game/
python -m pygbag snake-game            # prueba local en http://localhost:8000
python -m pygbag --archive snake-game  # genera build/web.zip para publicar
```

La versión web descarga el motor de Python desde `pygame-web.github.io`, así que necesita internet.

Cada push a `main` la compila y la publica en GitHub Pages automáticamente (`.github/workflows/pages.yml`).

## Estructura

```
main.py          ventana, menú, sonido, guardado y bucle principal
game.py          reglas del juego (sin dibujo): mapas, movimiento, modos
versus.py        reglas del modo en línea (varias serpientes), las usa el servidor
online.py        pantallas del modo en línea y tablero que dibujan los estilos
net.py           conexión WebSocket (JavaScript en la web, hilo aparte en la PC)
server/          servidor de partidas en línea + Containerfile
styles/
  base.py        contrato de un estilo visual + utilidades compartidas
  nokia.py ...   un archivo por estilo
assets/          fuentes con sus licencias
```

Para agregar un estilo nuevo: crea una clase que herede de `Renderer` en `styles/`, implementa `draw(app)` y regístrala en `styles/__init__.py`.

## Créditos

Fuentes incluidas en `assets/`, cada una con su licencia:

- [Patrick Hand](https://fonts.google.com/specimen/Patrick+Hand), [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono), [Orbitron](https://fonts.google.com/specimen/Orbitron), [Rye](https://fonts.google.com/specimen/Rye), [Lilita One](https://fonts.google.com/specimen/Lilita+One), [Cinzel](https://fonts.google.com/specimen/Cinzel), [Fredoka](https://fonts.google.com/specimen/Fredoka) (instancia fija SemiBold de la fuente variable): SIL Open Font License.
- [Chewy](https://fonts.google.com/specimen/Chewy): Apache License 2.0.

## Licencia

El código del juego está bajo la [licencia MIT](LICENSE): puedes usarlo, modificarlo y compartirlo libremente si conservas el aviso de copyright. Las fuentes de `assets/` mantienen sus propias licencias (ver Créditos).

## Plataforma de Lyness (cuentas, medallas y estilos de pago)

En lyness-gaming.com el juego usa la sesión del sitio: los estilos que no son gratis (Nokia, Neón, Pixel, Papel y Arcade lo son) se desbloquean con monedas desde el panel, y las partidas cuentan para medallas y misiones diarias. Sin sesión se juega como invitado, sin premios. En la PC todo está disponible.

El servidor en línea avisa a la plataforma quién ganó. Para eso necesita dos variables de entorno (sin ellas funciona igual, pero sin premios):

```
PLATAFORMA_URL=http://backend-piercinghell:8000
PLATAFORMA_CLAVE=<la misma clave que el backend tiene en PLATAFORMA_CLAVES=snake:...>
```
