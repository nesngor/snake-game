# snake-game

Snake hecho con Pygame (pygame-ce), con **11 estilos visuales**, 7 mapas, modos de dificultad y versión web.

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

### Modos de dificultad

- **CLASICO**: velocidad constante.
- **RAPIDO** (por defecto): cada comida acelera un 3 %; la velocidad se conserva entre mapas.
- **EXTREMO**: acelera un 4 % por comida y cada 2 comidas aparece una roca nueva (nunca junto a la cabeza ni en tu camino).

Cada 12 comidas pasas al siguiente mapa (LIBRE, CAJA, PASILLOS, CRUZ, COLUMNAS, MOLINO, REJA). Cada 5 comidas aparece un bonus que da más puntos mientras antes lo agarres.

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
styles/
  base.py        contrato de un estilo visual + utilidades compartidas
  nokia.py ...   un archivo por estilo
assets/          fuentes con sus licencias
```

Para agregar un estilo nuevo: crea una clase que herede de `Renderer` en `styles/`, implementa `draw(app)` y regístrala en `styles/__init__.py`.

## Créditos

Fuentes incluidas en `assets/`, cada una con su licencia:

- [Patrick Hand](https://fonts.google.com/specimen/Patrick+Hand), [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono), [Orbitron](https://fonts.google.com/specimen/Orbitron), [Rye](https://fonts.google.com/specimen/Rye), [Lilita One](https://fonts.google.com/specimen/Lilita+One): SIL Open Font License.
- [Chewy](https://fonts.google.com/specimen/Chewy): Apache License 2.0.
