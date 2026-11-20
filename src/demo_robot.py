"""Demo: mueve brazo, pinza y base del robot desde Python.
Uso: python src/demo_robot.py
"""
import time

import mujoco
import mujoco.viewer

from escena import (construir_escena_pick, colocar_robot, PUNTO_RECOGIDA,
                    ARTICULACIONES_BRAZO, BRAZO_PLEGADO)

# Postura "home" del TidyBot: brazo desplegado, listo para trabajar
BRAZO_LISTO = [0, 0.26179939, 3.14159265, -2.26892803, 0, 0.95993109, 1.57079633]

modelo, paquetes = construir_escena_pick(semilla=3)
datos = mujoco.MjData(modelo)
x0, y0, th0 = PUNTO_RECOGIDA
colocar_robot(modelo, datos, x0, y0, th0)

with mujoco.viewer.launch_passive(modelo, datos) as visor:
    inicio = time.time()
    while visor.is_running():
        fase = int(datos.time // 3) % 4  # cambia de fase cada 3 segundos

        brazo = BRAZO_LISTO if fase in (1, 2) else BRAZO_PLEGADO
        for nombre, valor in zip(ARTICULACIONES_BRAZO, brazo):
            datos.actuator(nombre).ctrl = valor

        datos.actuator("robot/fingers_actuator").ctrl = 255 if fase == 2 else 0
        datos.actuator("robot/joint_x").ctrl = x0 + 0.3 if fase == 3 else x0

        mujoco.mj_step(modelo, datos)
        visor.sync()

        # Esperar lo justo para ir a velocidad real
        adelanto = datos.time - (time.time() - inicio)
        if adelanto > 0:
            time.sleep(adelanto)