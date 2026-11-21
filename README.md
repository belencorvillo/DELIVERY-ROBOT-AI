# Robot repartidor — Trabajo de IA (MUAR, UPM)

Robot móvil (Stanford TidyBo) que recibe órdenes en lenguaje natural por chat, recoge paquetes en una zona
de paquetería y los entrega en la puerta de casas de una urbanización. Simulado en MuJoCo 4.0.1.

```
Tú: "Coge el paquete rojo y llévalo a la casa verde"
Robot: Hay 2 paquetes que encajan: 1) rojo cilindro grande, 2) rojo caja pequeño. ¿Cuál quieres?
Tú: la caja
Robot: Tengo el paquete... Voy a la casa verde... Paquete entregado. ¿Qué más?
```

## Instalación (Windows, PowerShell)

```powershell
git clone <URL-DEL-REPO>
cd robot_reparto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Python: el mismo para los tres (ahora mismo 3.14).
- Si PowerShell bloquea `Activate.ps1`: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- Si VS Code subraya los `import`: Ctrl+Shift+P → "Python: Select Interpreter" → `.venv`.
- Si añadís librerías (scikit-learn, torch…), añadidlas también a `requirements.txt`.

Prueba rápida: `python src/main.py 3` (se abre el visor y el robot te habla por la terminal).

## Arquitectura

```
          "Coge el rojo y llévalo a la casa verde"
                          │
              interpretar(texto)            ← interprete.py   (LLM)
                          │  lista de tareas
                          ▼
                main.py  (orquestador)      ← chat + ejecuta tareas una a una + "¿Qué más?"
          ┌───────────────┼──────────────────┐
          ▼               ▼                  ▼
   coger / dejar     ir_a_casa /         (preguntar al
   (paqueteria.py)   volver_a_paqueteria  usuario si hay
                     (reparto.py)          dudas)
          └───────────────┼──────────────────┘
                          ▼
                 Entorno  (entorno.py)      ← ÚNICA puerta a la simulación
        cámaras · base · brazo · píxel↔3D · cesta · métricas
                          ▼
           MuJoCo: escena + robot (escena.py, robot.py, assets/)
```

- **`Entorno`** esconde todo lo de MuJoCo. Las lógicas solo hablan con él.
- **Contrato:** cada parte entrega unas funciones con nombre, entradas y salidas fijas (ver abajo).
- **`trampas.py`:** versión "de mentira" de todas las funciones del contrato. Hacen trampa
  (le preguntan la respuesta al simulador) para que `main.py` funcione, pero no tiene lógica de IA ni percepción detrás.
  Cada compañero sustituye las suyas por las de verdad, y en `main.py` solo cambia el `import`.

## Estructura

| Carpeta / archivo | Qué hay |
|---|---|
| `assets/` | Piezas en XML: `mundo.xml` (suelo, luz), `zona_paquetes.xml` (tablón, cámara cenital, punto de recogida), `urbanizacion.xml` (calle, aceras, cámara aérea), `casa.xml` (casa modelo), `tidybot/` (robot, de MuJoCo Menagerie) |
| `escenas/` | `escena_pick.xml`, `escena_reparto.xml`, `escena_completa.xml` |
| `src/paquetes.py` | Genera los 6 paquetes aleatorios (color, forma, tamaño) con semilla |
| `src/escena.py` | Monta las escenas: paquetes, casas (colores barajados), robot con cesta y cámara frontal |
| `src/robot.py` | `Base` (moverse por velocidad) y `Brazo` (ángulos, cinemática inversa, pinza) |
| `src/entorno.py` | **`Entorno`: lo único que deben usar las lógicas** |
| `src/trampas.py` | Versiones trampa del contrato + utilidades reutilizables (navegar, esperar al brazo, cesta…) |
| `src/main.py` | Programa principal: chat + orquestador |
| `src/demo_*.py`, `src/ver_*.py`, `src/ejemplo_entorno.py` | Demos y ejemplos (ver tabla de demos) |
| `docs/` | Instrucciones para cada compañero |

## Mapa y coordenadas

- Unidades: metros, radianes, segundos. Eje Z hacia arriba.
- **Origen (0, 0)**: centro del tablón de paquetería (60 × 32 cm, 2 cm de alto).
- **Punto de recogida**: (0, −0.47), robot mirando a +Y (al tablón).
- **Calle**: de x = 1 a x = 18, centrada en y = −0.6.
- **Casas**: posiciones fijas, **colores barajados según la semilla**.

```
          casa_0 (x=5)   casa_1 (x=9)   casa_2 (x=13)     ← norte, puerta al sur
   ══════════════ acera norte (y ≈ 1.4) ════════════════
 □ ──────────────── calle (y = −0.6) ──────────────────►  x
   ══════════════ acera sur (y ≈ −2.6) ═════════════════
          casa_3 (x=5)   casa_4 (x=9)   casa_5 (x=13)     ← sur, puerta al norte
 □ = paquetería
```

- Cada casa tiene un punto de entrega invisible (`casa_i/entrega`) 50 cm delante de su puerta.
- **Paquetes**: 6 en una cuadrícula de 3 × 2 con un pequeño desplazamiento y giro aleatorios.
  Colores: rojo, verde, azul, amarillo, naranja, morado (pueden repetirse). Formas: caja o
  cilindro. Tamaño: pequeño (4 cm) o grande (6 cm).
- **Cesta**: detrás del brazo, subida 15 cm sobre un soporte. Un paquete cada vez.

## Cámaras

| Nombre | Dónde | Para qué |
|---|---|---|
| `cam_cenital` | Fija, a 1 m sobre el tablón | Ver y localizar los 6 paquetes |
| `robot/frontal` | Mástil delantero del robot | Navegar y reconocer casas |
| `robot/wrist` | Muñeca del brazo | Ajuste fino al coger y soltar |
| `cam_urbanizacion` | Fija, a 18 m de altura | Solo para depurar y para la memoria (el robot no la usa) |

## Cómo usar el Entorno

```python
from entorno import Entorno

env = Entorno("completa", semilla=3, visor=True)   # "pick", "reparto" o "completa"
while env.abierto():
    imagen = env.camara("robot/frontal")   # 1. mirar
    env.base.mover(0.3, 0, 0)              # 2. decidir
    env.paso()                             # 3. avanzar (2 ms)
env.cerrar()
```

Con `visor=False` va sin ventana y todo lo rápido que pueda (para datasets y evaluaciones).

**Simulación**: `env.paso(n)`, `env.reset()`, `env.abierto()`, `env.cerrar()`, `env.tiempo`.

**Sensores**:
- `env.camara(nombre)` → imagen RGB (480 × 640 × 3). Con `profundidad=True` → metros por píxel.
- `env.pixel_a_mundo(camara, u, v, profundidad)` → punto (x, y, z) del mundo que se ve en ese píxel.
- `env.mundo_a_pixel(camara, punto)` → píxel (u, v) donde aparece un punto.

**Base** (`env.base`): `mover(vx, vy, wz)` (vx adelante, vy izquierda en ejes del robot, wz giro;
máx. 0.5 m/s y 1 rad/s), `parar()`, `pose()` → (x, y, th) en el mundo.

**Brazo** (`env.brazo`):
- `ir_a(punto, giro)`: pinza a ese punto, apuntando hacia abajo, **en línea recta**. Llamarla UNA vez por destino.
- `ha_llegado()`: ¿ha terminado de moverse?
- `cinematica_inversa(punto, giro)`: calcula los 7 ángulos sin mover nada → (ángulos, éxito).
- `mover_a(ángulos)`, `angulos()`, `plegar()`, `desplegar()`.
- `abrir_pinza()`, `cerrar_pinza()`, `posicion_pinza()`, `giro_pinza()`.
- `velocidad`: rad/s de las articulaciones (1.0 normal; bajadla a 0.4 llevando un paquete).

**Otros**: `env.posicion_cesta()` → centro del fondo de la cesta en el mundo.

## Demos

| Script | Qué enseña |
|---|---|
| `python src/main.py 3` | El sistema completo con chat (de momento con trampas) |
| `python src/ejemplo_entorno.py` | Plantilla mínima: mirar → decidir → avanzar, con una máquina de estados |
| `python src/demo_coger.py 3 rojo` | Coger un paquete con el brazo y dejarlo en la cesta |
| `python src/demo_pixeles.py 3` | Píxel ↔ punto 3D con la cámara cenital (error < 1.5 mm) |
| `python src/demo_etiquetas.py 3` | Etiquetas automáticas (recuadros) de paquetes y casas para datasets |
| `python src/demo_base.py` | Mover la base por velocidad |
| `python src/demo_reparto.py` | Recorrer la calle con un paquete en la cesta |
| `python src/demo_robot.py` | Mover brazo, pinza y base a mano |
| `python src/ver_paquetes.py 3` / `ver_reparto.py 3` | Ver cada escena y guardar lo que ven sus cámaras en `capturas/` |

## Contrato de funciones

Cada función recibe `env`, **corre la simulación ella misma** (llamando a `env.paso()`) hasta
terminar, y devuelve un diccionario con al menos `"exito"` (bool) y `"mensaje"` (texto para el
usuario). Si necesita preguntar algo, usa `preguntar(texto)` → respuesta del usuario.

| Archivo | Función | Devuelve |
|---|---|---|
| `paqueteria.py` | `detectar_paquetes(env)` | lista de `{"color", "forma", "tamano", "punto", "giro", "confianza"}` |
| `paqueteria.py` | `coger(env, pedido, preguntar)` | `{"exito", "mensaje", "paquete"}` (deja el paquete en la cesta) |
| `paqueteria.py` | `dejar(env, punto)` | `{"exito", "mensaje"}` (de la cesta al suelo en `punto`) |
| `reparto.py` | `detectar_casas(env)` | lista de `{"color", "punto", "confianza"}` |
| `reparto.py` | `ir_a_casa(env, color, preguntar)` | `{"exito", "mensaje", "punto_entrega"}` |
| `reparto.py` | `volver_a_paqueteria(env)` | `{"exito", "mensaje"}` |
| `interprete.py` | `interpretar(texto)` | `{"tareas": [...], "error": None o texto}` |

Tareas de `interpretar`: `{"accion": "coger", "paquete": {"color", "forma", "tamano"}}`,
`{"accion": "entregar", "casa": color}`, `{"accion": "volver"}`, `{"accion": "terminar"}`.
Lo que no se dice va a `None`. Colores, formas y tamaños, siempre en masculino y sin tildes
(`"rojo"`, `"cilindro"`, `"pequeno"`).

## Reglas del juego

1. **Usad siempre el `Entorno`.** No abráis vuestro propio visor ni vuestro propio bucle de MuJoCo.
2. **Moved la base solo con `env.base.mover(...)`**: así, cambiar a Spot será fácil.
3. **Nada de trampas en la lógica:** `env.paquetes`, `env.casas`, `env.etiquetas()` y
   `env.distancia_entrega()` son la verdad del simulador, **solo para generar datasets y evaluar**
   (en scripts aparte, por ejemplo en `src/datasets/`). La lógica debe descubrirlo todo con las cámaras.
4. **Las cámaras, unas 10 veces por segundo como mucho**: renderizar es lento.
5. **No cambiéis `assets/`, `escenas/`, `entorno.py`, `robot.py` ni `escena.py` sin avisar**:
   afectan a todos. Si necesitáis algo de ahí, se pide y se añade.
6. Cada uno en su rama de Git; se une a `main` cuando funciona.

## Reparto de tareas

| Quién | Qué |
|---|---|
| Compañero paquetería | Visión de paquetes (ML) + `detectar_paquetes`, `coger`, `dejar` → `docs/compañero_paqueteria.md` |
| Compañero urbanización | Visión de casas (ML) + `detectar_casas`, `ir_a_casa`, `volver_a_paqueteria` + `interpretar` (LLM) → `docs/compañero_urbanizacion.md` |
| Integración | Entornos, `Entorno`, brazo y cinemática inversa, trampas, `main.py`, evaluación con muchas semillas |
| Ampliaciones (si da tiempo) | Orden por audio, peatones que cruzan, Spot en lugar del TidyBot |

## Métricas de éxito

- **Entrega correcta**: paquete a menos de 0.3 m del punto de entrega de la casa pedida
  (`env.distancia_entrega(casa, nombre_paquete)`).
- Evaluar con muchas semillas (por ejemplo, 100) sin visor y dar porcentajes de éxito.
- Comparar con las trampas (percepción perfecta) para medir cuánto error mete la parte de IA.

## Limitaciones conocidas

- La base se desliza (no simula ruedas) y el TidyBot no anda como Spot: simplificaciones.
- La posición del robot es exacta (localización perfecta); en un robot real tendría error.

## Licencias

El modelo del TidyBot (`assets/tidybot/`) viene de
[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) y conserva su licencia
(ver `assets/tidybot/LICENSE`).