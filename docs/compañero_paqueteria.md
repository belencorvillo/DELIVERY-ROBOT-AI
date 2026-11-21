# Tu parte: la paquetería 📦

¡Hola! El repo ya está montado: el robot entiende órdenes por chat (sin LLM, solo xq identifica paquetes que tiene en una lista de algunas palabras [coger,traer,llevar,colores,formas]), coge paquetes, los lleva a
las casas y vuelve. **Pero hace trampa**: no mira con las cámaras, le pregunta al simulador dónde
está cada cosa. Tu trabajo es que **la paquetería funcione de verdad, mirando con la cámara**,
usando lógica de ia.
## 1. Puesta en marcha

```powershell
git clone <URL-DEL-REPO>
cd robot_reparto
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
git checkout -b paqueteria
```

Prueba que todo va:

```powershell
python src/main.py 3
```

Escribe `coge el paquete rojo` y mira cómo lo hace. Después lee el `README.md` entero,
sobre todo **Arquitectura**, **Cómo usar el Entorno** y **Reglas del juego**.

## 2. Cómo está montado (lo que te interesa pa tu parte)

```
main.py (chat)  →  coger(env, pedido, preguntar)   ← TU función
                →  dejar(env, punto)                ← TU función
                         │
                         ▼
                Entorno (env): cámaras, brazo, base, píxel↔3D, cesta
```

- `env` es tu única puerta a la simulación: no toques MuJoCo directamente.
- Tus funciones **corren la simulación ellas mismas** (llamando a `env.paso()`) hasta terminar.
- Ahora mismo `main.py` usa las versiones de `src/trampas.py`. Cuando las tuyas funcionen,
  se cambia una línea de `main.py` y listo.

## 3. Las funciones que tienes que hacer

Crea `src/paqueteria.py` con **exactamente** estas tres funciones (mismo nombre, mismas
entradas, mismas salidas que en `trampas.py`):

```python
def detectar_paquetes(env):
    """Mira con la camara cenital y devuelve los paquetes que hay en el tablon:
    [{"color": "azul", "forma": "caja", "tamano": "grande",
      "punto": np.array([x, y, z]),   # CENTRO del paquete, en el mundo
      "giro": 0.3,                    # giro sobre el eje vertical (rad)
      "confianza": 0.95}, ...]"""

def coger(env, pedido, preguntar):
    """pedido = {"color": "azul", "forma": None, "tamano": None}   (None = da igual)
    1. detecta los paquetes, 2. se queda con los que encajan,
    3. si hay varios, pregunta: respuesta = preguntar("Hay dos azules: ¿el grande o el pequeño?"),
    4. lo coge y lo deja en la cesta, con el brazo plegado al terminar.
    Devuelve {"exito": bool, "mensaje": str, "paquete": dict o None}"""

def dejar(env, punto):
    """Saca el paquete de la cesta y lo deja en el suelo en 'punto' (x, y, z del mundo),
    delante de la puerta de una casa. Brazo plegado al terminar.
    Devuelve {"exito": bool, "mensaje": str}"""
```

### Lo importante (la IA) es `detectar_paquetes` [ESTO ES LO QUE ME HA DICHO CLAUDE, PERO HAZ LO QUE CONSIDERES OBVIO :D]

Ahí va el trabajo de machine learning, que es lo que más pesa en la nota:

1. **Generar un dataset** con `env.etiquetas()` (ver `demo_etiquetas.py`): la imagen de la
   cámara cenital + el recuadro, el color, la forma y el tamaño de cada paquete, **automáticamente**.
   Con muchas semillas tienes miles de ejemplos sin etiquetar nada a mano. Hazlo en un script
   aparte (por ejemplo, `src/datasets/generar_paquetes.py`) con `Entorno("pick", semilla=s)`
   para muchas `s`.
2. **Entrenar y comparar clasificadores** sobre los recortes de cada paquete: características a
   mano (color HSV, forma) + kNN o Bayes, PCA/Fisher, MLP, autoencoder, CNN… con
   entrenamiento/validación/test, validación cruzada y matrices de confusión. **Guarda las tablas
   de resultados: van a la memoria.**
3. **Encontrar los paquetes en la imagen sin trampas**: el tablón es marrón y liso, así que
   separar "lo que no es tablón" es un buen punto de partida. Luego clasificas cada recorte.
4. **Pasar a 3D** con `env.pixel_a_mundo("cam_cenital", u, v, profundidad)`. Te da el punto de
   la **cara de arriba** del paquete. El tablón está a 2 cm de altura, así que:
   - altura del paquete = z_arriba − 0.02 → **te dice si es pequeño (4 cm) o grande (6 cm)**
   - centro = z_arriba − altura / 2
5. **El giro** (para que la pinza agarre la caja por dos caras opuestas): sácalo de la forma del
   recorte (por ejemplo, el rectángulo de área mínima que lo rodea). En los cilindros da igual.

### `coger` y `dejar`: el brazo ya está resuelto

**No tienes que pelearte con el brazo.** En `trampas.py` tienes `coger` y `dejar` funcionando.
Lo único que hacen trampa es saber dónde está el paquete. La parte del brazo la puedes **copiar
o importar** tal cual:

```python
from trampas import esperar_brazo, soltar_en_cesta, ir_sobre_cesta, salir_de_cesta, VEL_CON_PAQUETE
```

Secuencia para coger un paquete (ya probada):

```python
env.brazo.abrir_pinza()
env.brazo.desplegar(); esperar_brazo(env)
env.brazo.ir_a(punto + [0, 0, 0.15], giro); esperar_brazo(env)   # encima
env.brazo.ir_a(punto, giro); esperar_brazo(env)                  # bajar recto
env.brazo.cerrar_pinza(); env.paso(600)
env.brazo.velocidad = VEL_CON_PAQUETE                            # despacio, que no se escurra
env.brazo.ir_a(punto + [0, 0, 0.25], giro); esperar_brazo(env, 15)
env.brazo.desplegar(); esperar_brazo(env, 15)
soltar_en_cesta(env)                                             # gira por arriba, suelta, pliega
```

**Cómo comprobar sin trampas si lo has cogido:** mira con la cámara de la muñeca
(`env.camara("robot/wrist")`) si el paquete está en la pinza, o con la cenital si ya no está en
el tablón. Si se ha caído, reintenta: hay un problema conocido con **los cilindros grandes, que a
veces se escurren** (sobre todo en la esquina más lejana). Mejorar eso es parte de tu trabajo y
queda muy bien en la memoria.

**En `dejar`**, para saber dónde está el paquete dentro de la cesta, usa la cámara de la muñeca
o recuerda cómo lo dejaste. La trampa usa `giro_de(cuerpo)` y la posición real: eso no vale en
la versión de verdad.

## 4. Archivos que te sirven

| Archivo | Para qué |
|---|---|
| `src/trampas.py` | **Tu plantilla**: tus 3 funciones hechas con trampa + utilidades del brazo para reutilizar |
| `src/demo_coger.py` | Ver `coger` funcionando: `python src/demo_coger.py 3 rojo` |
| `src/demo_etiquetas.py` | Cómo sacar recuadros y etiquetas automáticas para el dataset |
| `src/demo_pixeles.py` | Cómo pasar de píxel a punto 3D con la cámara cenital |
| `src/ver_paquetes.py` | Ver la escena con una semilla y guardar lo que ven las cámaras |
| `src/entorno.py` | Todo lo que puedes usar (está documentado dentro) |
| `src/robot.py` | Cómo funciona el brazo por dentro (no hace falta tocarlo) |

## 5. Reglas

- **Prohibido en tu lógica** usar `env.paquetes`, `env.etiquetas()`, `env.distancia_entrega()`,
  `env.datos.body(...)` de los paquetes o cualquier "verdad" del simulador. Solo en los scripts
  de generar datasets y de evaluar.
- Solo cámaras: `cam_cenital` y `robot/wrist`.
- `env.brazo.ir_a(...)` una vez por destino, nunca en cada paso.
- No toques `entorno.py`, `robot.py`, `escena.py`, `assets/` ni `escenas/`: si necesitas algo,
  pídelo.
- Trabaja en tu rama `paqueteria`. Cuando algo funcione, avisa y lo juntamos.

## 6. Orden recomendado [LO MISMO, LO QUE DICE CLAUDE PERO HAZ LO QUE VEAS ]

1. Generador de dataset con `env.etiquetas()`.
2. Clasificador (color, forma, tamaño) y comparación de modelos. **Guarda resultados.**
3. `detectar_paquetes` sin trampas (encontrar + clasificar + 3D + giro).
4. `coger` usando tu `detectar_paquetes` y las utilidades del brazo de `trampas.py`.
5. `dejar`.
6. Evaluar: porcentaje de paquetes bien reconocidos y bien cogidos con muchas semillas.

Para probar tu versión en el programa completo, en `main.py` cambia:

```python
from paqueteria import coger, dejar
from trampas import interpretar, ir_a_casa, volver_a_paqueteria, la_casa
```

¡Ánimo! Cualquier cosa que necesites del entorno, me la pides 🙂