# Tu parte: la urbanización y el lenguaje 

¡Hola! El repo ya está montado: el robot entiende órdenes por chat, coge paquetes, los lleva a
las casas y vuelve. **Pero hace trampa**: no mira con las cámaras (le pregunta al simulador qué
casa es de cada color) y "entiende" las órdenes buscando palabras clave. Tu trabajo es que
**encuentre las casas mirando con la cámara** (machine learning) y que **entienda de verdad lo
que se le pide** (LLM).

## 1. Puesta en marcha

```powershell
git clone <URL-DEL-REPO>
cd robot_reparto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
git checkout -b reparto
```

Prueba que todo va:

```powershell
python src/main.py 3
```

Escribe `coge el paquete rojo y llevalo a la casa verde y vuelve` y mira el viaje. Después lee
el `README.md` entero, sobre todo **Arquitectura**, **Mapa y coordenadas**, **Cómo usar el
Entorno** y **Reglas del juego**.

## 2. Cómo está montado (lo que es relevante pa tu parte)

```
texto ──► interpretar(texto)               ← TU función (interprete.py)
              │ lista de tareas
              ▼
main.py ──► ir_a_casa(env, color, preguntar) ← TU función (reparto.py)
        ──► volver_a_paqueteria(env)         ← TU función (reparto.py)
                    │
                    ▼
           Entorno (env): cámaras, base, píxel↔3D
```

- `env` es tu única puerta a la simulación: no toques MuJoCo directamente.
- Tus funciones de reparto **corren la simulación ellas mismas** (llamando a `env.paso()`).
- Ahora mismo `main.py` usa las versiones de `src/trampas.py`. Cuando las tuyas funcionen,
  se cambia una línea de `main.py` y listo.
- Al llegar a la casa, **soltar el paquete en la puerta lo hace `dejar()`**, del compañero de
  paquetería. Tú solo tienes que dejar el robot **parado delante de la puerta** y devolver
  dónde hay que dejarlo (`punto_entrega`).

## 3. Las funciones que tienes que hacer

### 3.1 `src/reparto.py`

```python
def detectar_casas(env):
    """Mira con la camara frontal y devuelve las casas que ve:
    [{"color": "verde", "punto": np.array([x, y, z]), "confianza": 0.9}, ...]"""

def ir_a_casa(env, color, preguntar):
    """Busca la casa de ese color MIRANDO y va hasta quedar parado delante de su puerta
    (unos 0.5 m), mirando hacia ella.
    Devuelve {"exito": bool, "mensaje": str, "punto_entrega": np.array([x, y, 0])}
    (punto_entrega = donde dejar el paquete, en el suelo delante de la puerta)"""

def volver_a_paqueteria(env):
    """Vuelve al punto de recogida (0, -0.47) mirando al tablon.
    Devuelve {"exito": bool, "mensaje": str}"""
```

[ESTO DE ABAJO ES LO QUE DICE CLAUDE, PERO MÓNTALO COMO CONSIDERES :D]

**Lo que ya sabes (no es trampa):** el **mapa** es fijo y está en el README: dónde está la calle,
dónde están las 6 casas y hacia dónde mira cada puerta. Lo que **no** sabes es **de qué color es
cada casa**: cambia con la semilla. Eso tienes que descubrirlo con la cámara frontal.

**Lo importante (la IA) es `detectar_casas`:**
1. **Dataset** con `env.etiquetas()` en la escena `"reparto"` o `"completa"` (ver
   `demo_etiquetas.py`): imagen de la cámara frontal + recuadro y color de cada casa visible.
   Para variar el punto de vista, mueve el robot a distintos sitios de la calle antes de cada
   foto (con `env.base.mover` o pidiéndome un `env.colocar_robot(x, y, th)` que lo teletransporte).
2. **Clasificador** del color de la casa sobre los recortes, comparando métodos (kNN, Bayes,
   MLP, CNN…) con validación. **Guarda las tablas de resultados: van a la memoria.**
3. **Encontrar casas en la imagen sin trampas**: el cielo, la calle y las aceras tienen colores
   muy distintos a las fachadas, así que separarlos es un buen punto de partida. También puedes
   partir la imagen en ventanas y clasificar cada una.
4. **Pasar a 3D** con `env.pixel_a_mundo("robot/frontal", u, v, profundidad)` y **asociar** cada
   casa vista con la casa del mapa más cercana. Ahí sabes qué casa del mapa es de cada color.

**`ir_a_casa` y `volver_a_paqueteria`:** el movimiento ya está resuelto en `trampas.py`. Puedes
importar `navegar_a(env, x, y, th)`, que lleva la base a un punto del mundo con un control
proporcional:

```python
from trampas import navegar_a, la_casa
```

Idea de `ir_a_casa`: salir a la calle → recorrerla mirando con la cámara → cuando reconozcas la
casa del color pedido, calcular el punto delante de su puerta (con el mapa) → `navegar_a` hasta
ahí. Si no la encuentras, puedes preguntar al usuario o devolver `exito: False`.

Ojo: la trampa saca el punto de entrega del simulador (`env.datos.site(...)`). La tuya debe
calcularlo **a partir del mapa** (posición de la casa + 1.7 m hacia la calle) o de lo que ve.

### 3.2 `src/interprete.py` (el LLM)

```python
def interpretar(texto):
    """'Coge el paquete azul, llevalo a la casa verde y vuelve' ->
    {"tareas": [{"accion": "coger", "paquete": {"color": "azul", "forma": None, "tamano": None}},
                {"accion": "entregar", "casa": "verde"},
                {"accion": "volver"}],
     "error": None}
    Acciones: "coger", "entregar", "volver", "terminar".
    Si no entiende la orden: {"tareas": [], "error": "explicacion para el usuario"}"""
```

- Valores siempre en **masculino y sin tildes**: colores `rojo, verde, azul, amarillo, naranja,
  morado`; formas `caja, cilindro`; tamaños `pequeno, grande`. Lo que no se diga, `None`.
- LLM local recomendado (es el que pusimos en la propuesta al profe): **Qwen3-8B con Ollama**,
  pidiéndole que responda **en JSON con un esquema fijo**. Después **valida** lo que devuelve
  (acciones y colores permitidos) antes de dárselo a `main.py`.
- El `interpretar` de `trampas.py` (palabras clave) es tu **referencia para comparar**: haz un
  banco de 50–100 órdenes de prueba (con sinónimos, negaciones, órdenes raras o imposibles) y
  mide el porcentaje de acierto de cada uno. Lo prometimos en la propuesta y va a la memoria.

## 4. Archivos que te sirven

| Archivo | Para qué |
|---|---|
| `src/trampas.py` | **Tu plantilla**: tus funciones hechas con trampa + `navegar_a` e `interpretar` por palabras clave |
| `src/demo_etiquetas.py` | Cómo sacar recuadros y colores de las casas para el dataset |
| `src/demo_pixeles.py` | Cómo funciona píxel ↔ punto 3D (con la frontal es igual) |
| `src/ejemplo_entorno.py` | Plantilla mínima de bucle: mirar → decidir → avanzar |
| `src/demo_reparto.py`, `src/demo_base.py` | Mover la base por la calle |
| `src/ver_reparto.py` | Ver la urbanización con una semilla y guardar lo que ve la cámara frontal |
| `src/entorno.py` | Todo lo que puedes usar (está documentado dentro) |

## 5. Reglas

- **Prohibido en tu lógica** usar `env.casas`, `env.etiquetas()`, `env.distancia_entrega()`,
  `env.datos.site(...)`, `env.datos.body(...)` de las casas o cualquier "verdad" del simulador.
  Solo en los scripts de generar datasets y de evaluar.
- Para saber dónde está el robot sí puedes usar `env.base.pose()`: es su odometría.
- Mueve la base solo con `env.base.mover(...)` (o `navegar_a`, que la usa por dentro).
- Cámara frontal unas 10 veces por segundo como mucho.
- No toques `entorno.py`, `robot.py`, `escena.py`, `assets/` ni `escenas/`: si necesitas algo
  (por ejemplo, `colocar_robot`), pídelo.
- Trabaja en tu rama `reparto`. Cuando algo funcione, avisa y lo juntamos.

## 6. Orden recomendado [LO MISMO, LO QUE RECOMIENDA CLAUDE, PERO HAZ LO QUE VEAS :)]

1. Generador de dataset de casas con `env.etiquetas()`.
2. Clasificador de color de casas y comparación de modelos. **Guarda resultados.**
3. `detectar_casas` sin trampas (encontrar + clasificar + 3D + asociar con el mapa).
4. `ir_a_casa` y `volver_a_paqueteria` usando `navegar_a`.
5. `interpretar` con el LLM + banco de órdenes de prueba + comparación con las palabras clave.
6. Evaluar: porcentaje de casas bien reconocidas y de llegadas correctas con muchas semillas.

Para probar tu versión en el programa completo, en `main.py` cambia:

```python
from reparto import ir_a_casa, volver_a_paqueteria
from interprete import interpretar
from trampas import coger, dejar, la_casa
```

¡Ánimo! Cualquier cosa que necesites del entorno, me la pides 🙂