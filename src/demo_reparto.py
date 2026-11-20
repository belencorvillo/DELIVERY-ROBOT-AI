"""Demo: el robot lleva el paquete por la calle hasta quedar frente a la casa_1.
Uso: python src/demo_reparto.py
"""
import time

import mujoco
import mujoco.viewer
import numpy as np

from escena import construir_escena_reparto, colocar_robot, PUNTO_RECOGIDA, distancia_entrega
from robot import Base

PI = np.pi
RECORRIDO = [
    ("girar a la calle",  (0, 0, -1.0), PI / 2),
    ("avanzar 9 m",       (0.5, 0, 0),  18),
    ("mirar a casa_1",    (0, 0, 1.0),  PI / 2),
    ("acercarse",         (0.5, 0, 0),  2.4),
    ("parar",             (0, 0, 0),    3),
]

modelo, casas, paquete = construir_escena_reparto(semilla=3)
datos = mujoco.MjData(modelo)
colocar_robot(modelo, datos, *PUNTO_RECOGIDA)
base = Base(modelo, datos)
color_casa_1 = [c for c, i in casas.items() if i == 1][0]
print(f"Llevo un paquete {paquete['color']} a la casa_1, que es la {color_casa_1}")

with mujoco.viewer.launch_passive(modelo, datos) as visor:
    inicio = time.time()
    tramo, fin_tramo = -1, 0.0
    while visor.is_running():
        if datos.time >= fin_tramo and tramo < len(RECORRIDO) - 1:
            tramo += 1
            nombre, (vx, vy, wz), duracion = RECORRIDO[tramo]
            fin_tramo = datos.time + duracion
            base.mover(vx, vy, wz)
            print(f"{nombre:16} | distancia del paquete a la entrega: "
                  f"{distancia_entrega(modelo, datos, 1):.2f} m")

        base.paso()
        mujoco.mj_step(modelo, datos)
        visor.sync()

        adelanto = datos.time - (time.time() - inicio)
        if adelanto > 0:
            time.sleep(adelanto)