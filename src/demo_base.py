"""Demo: mueve la base por velocidad siguiendo un recorrido.
Uso: python src/demo_base.py
"""
import time

import mujoco
import mujoco.viewer
import numpy as np

from escena import construir_escena_pick, colocar_robot, PUNTO_RECOGIDA
from robot import Base

PI = np.pi
# Recorrido: (que hace, (vx, vy, wz), cuantos segundos)
RECORRIDO = [
    ("girar 180",      (0, 0, 1.0),   PI),
    ("avanzar 1 m",    (0.5, 0, 0),   2),
    ("girar izq",      (0, 0, 1.0),   PI / 2),
    ("avanzar 1 m",    (0.5, 0, 0),   2),
    ("de lado izq",    (0, 0.5, 0),   1),
    ("de lado der",    (0, -0.5, 0),  1),
    ("girar izq",      (0, 0, 1.0),   PI / 2),
    ("avanzar 1 m",    (0.5, 0, 0),   2),
    ("girar izq",      (0, 0, 1.0),   PI / 2),
    ("avanzar 1 m",    (0.5, 0, 0),   2),
    ("girar izq",      (0, 0, 1.0),   PI / 2),
    ("girar 180",      (0, 0, 1.0),   PI),
    ("parar",          (0, 0, 0),     2),
]

modelo, paquetes = construir_escena_pick(semilla=3)
datos = mujoco.MjData(modelo)
colocar_robot(modelo, datos, *PUNTO_RECOGIDA)
base = Base(modelo, datos)

with mujoco.viewer.launch_passive(modelo, datos) as visor:
    inicio = time.time()
    tramo, fin_tramo = -1, 0.0
    while visor.is_running():
        # Cuando acaba un tramo, pasar al siguiente
        if datos.time >= fin_tramo and tramo < len(RECORRIDO) - 1:
            tramo += 1
            nombre, (vx, vy, wz), duracion = RECORRIDO[tramo]
            fin_tramo = datos.time + duracion
            base.mover(vx, vy, wz)
            x, y, th = base.pose()
            print(f"{nombre:12} | ahora en x={x:+.2f} y={y:+.2f} th={np.degrees(th) % 360:5.0f} grados")

        base.paso()
        mujoco.mj_step(modelo, datos)
        visor.sync()

        adelanto = datos.time - (time.time() - inicio)
        if adelanto > 0:
            time.sleep(adelanto)