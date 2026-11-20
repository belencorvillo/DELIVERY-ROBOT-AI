# Robot repartidor — Trabajo de IA (MUAR, UPM)

Robot móvil (Stanford TidyBot)
que recoge paquetes en una zona de paquetería y los entrega en una urbanización,
siguiendo órdenes en lenguaje natural. Simulado en MuJoCo 4.0.1.

## Instalación (Windows, PowerShell)

```powershell
git clone <URL-DEL-REPO>
cd robot_reparto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Python recomendado: el mismo para los tres (ahora mismo 3.14).
Si PowerShell bloquea `Activate.ps1`: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

Prueba rápida: `python src/ejemplo_entorno.py`

## Estructura

| Carpeta / archivo | Qué hay |
|---|---|
| `assets/` | Piezas en XML: `mundo.xml`, `zona_paquetes.xml`, `urbanizacion.xml`, `casa.xml` (casa modelo), `tidybot/` (robot) |
| `escenas/` | Combinaciones de piezas: `escena_pick.xml`, `escena_reparto.xml` |
| `src/paquetes.py` | Generación aleatoria de paquetes (color, forma, tamaño) con semilla |
| `src/escena.py` | Montaje de escenas: paquetes, casas, robot, cesta, cámaras |
| `src/robot.py` | `Base` (moverse por velocidad) y `Brazo` (ángulos y pinza) |
| `src/entorno.py` | **`Entorno`: lo único que deben usar las lógicas** |
| `src/ejemplo_entorno.py` | Plantilla para empezar |
| `src/ver_*.py`, `src/demo_*.py` | Scripts para ver y probar las escenas |

## Mapa y coordenadas

- Unidades: metros, radianes, segundos. Eje Z hacia arriba.
- Origen (0, 0): centro del tablón de paquetería.
- **Punto de recogida**: (0, −0.6), robot mirando a +Y (al tablón).
- **Calle**: de x = 1 a x = 18, centrada en y = −0.6.
- **Casas**: posiciones fijas, colores aleatorios según la semilla.

```
          casa_0 (x=5)   casa_1 (x=9)   casa_2 (x=13)     ← norte, puerta al sur
   ══════════════ acera norte (y ≈ 1.4) ════════════════
 □ ──────────────── calle (y = −0.6) ──────────────────►  x
   ══════════════ acera sur (y ≈ −2.6) ═════════════════
          casa_3 (x=5)   casa_4 (x=9)   casa_5 (x=13)     ← sur, puerta al norte
 □ = paquetería
```

- Cada casa tiene un punto de entrega invisible (`casa_i/entrega`) 50 cm delante de su puerta.

## Cámaras

| Nombre | Dónde | Para qué |
|---|---|---|
| `cam_cenital` | Fija sobre el tablón | Ver y localizar los 6 paquetes |
| `robot/wrist` | Muñeca del brazo | Ajuste fino al coger y soltar |
| `robot/frontal` | Mástil delantero del robot | Navegar y reconocer casas |
| `cam_urbanizacion` | Fija a 18 m de altura | Solo para depurar y para la memoria (el robot no la usa) |

`env.camara(nombre)` devuelve la imagen RGB; `env.camara(nombre, profundidad=True)` la distancia en metros de cada píxel.

## Cómo usar el Entorno

```python
from entorno import Entorno

env = Entorno("pick", semilla=3, visor=True)   # "pick" o "reparto"
while env.abierto():
    imagen = env.camara("cam_cenital")   # 1. mirar
    env.base.mover(0, 0, 0)              # 2. decidir
    env.paso()                           # 3. avanzar (2 ms)
env.cerrar()
```

**Base** (`env.base`): `mover(vx, vy, wz)` (vx adelante, vy izquierda en ejes del robot, wz giro; máx. 0,5 m/s y 1 rad/s), `parar()`, `pose()` → (x, y, th) en el mundo.

**Brazo** (`env.brazo`): `mover_a([7 ángulos])`, `angulos()`, `plegar()`, `desplegar()`, `abrir_pinza()`, `cerrar_pinza()`, `posicion_pinza()` → (x, y, z).

**Escena pick**: `env.paquetes` = lista de los 6 paquetes (color, forma, tamaño, posición).
**Escena reparto**: el robot empieza con `env.paquete` en la cesta; `env.casas` = {color: número de casa}.

## A tener en cuenta a la hora de desarrollar vuestra parte

1. **Usad siempre el `Entorno`.** No abráis vuestro propio visor ni vuestro propio bucle de MuJoCo: así la integración será ,más fácil :D
2. **Moved la base solo con `env.base.mover(...)`.** Así, cambiar a Spot será automático.
3. **No usar las referencias en la lógica:** `env.paquetes`, `env.casas` y `env.distancia_entrega()` son la verdad de referencia, **solo para evaluar**. La lógica debe descubrir qué hay y dónde con las cámaras.
4. **Las cámaras, unas 10 veces por segundo**, no en cada paso: renderizar es lento.
5. **No cambiéis `assets/` ni `escenas/` sin avisar**: afectan a todos.
6. Cada uno trabaja en su rama de Git y se une a `main` cuando funciona.

## Reparto de tareas

| Quién | Qué |
|---|---|
| Compañero 1 | Lógica del brazo: ver los paquetes, elegir el pedido (preguntar si hay ambigüedad (no hay caja azul, qué hago? o hay dos paquetes azules, cuál cojo?)), cogerlo y dejarlo en la cesta del robot. Esta lógica debe servir para hacer el place del paquete en la puerta |
| Compañero 2 | Lógica de reparto: ir a la urbanización, encontrar la casa por su color con la cámara frontal, colocarse delante de la puerta |
| Integración | Entornos, escena completa, máquina de estados global, métricas |
| Por decidir | Intérprete de lenguaje natural (módulo único que usan los dos) |

Formato acordado de la salida del intérprete:
```python
{"paquete": {"color": "azul", "forma": "caja", "tamano": None}, "casa": "verde"}
```

## Métricas de éxito

- **Entrega correcta**: paquete a menos de 0,3 m del punto de entrega de la casa pedida (`env.distancia_entrega(casa)`).
- Evaluar con muchas semillas (por ejemplo, 100) sin visor y dar el porcentaje de éxito.

## Licencias

El modelo del TidyBot (`assets/tidybot/`) viene de [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) y conserva su licencia (ver `assets/tidybot/LICENSE`).