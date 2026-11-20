"""Genera la urbanizacion con una semilla, guarda lo que ven las camaras y abre el visor.
Uso: python src/ver_reparto.py 3
"""
import os
import sys

import mujoco
import mujoco.viewer
from PIL import Image

from escena import construir_escena_reparto, colocar_robot, PUNTO_RECOGIDA

CAMARAS = ["cam_urbanizacion", "robot/frontal"]

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 0
modelo, casas, paquete = construir_escena_reparto(semilla)
datos = mujoco.MjData(modelo)
colocar_robot(modelo, datos, *PUNTO_RECOGIDA)

print(f"Semilla {semilla}:")
print(f"  Paquete en la cesta: {paquete['color']} {paquete['forma']} {paquete['tamano']}")
for color, casa in sorted(casas.items(), key=lambda c: c[1]):
    print(f"  casa_{casa}: {color}")

mujoco.mj_step(modelo, datos, nstep=500)

os.makedirs("capturas", exist_ok=True)
with mujoco.Renderer(modelo, 480, 640) as renderer:
    for camara in CAMARAS:
        renderer.update_scene(datos, camera=camara)
        nombre_archivo = camara.replace("/", "_")
        Image.fromarray(renderer.render()).save(f"capturas/reparto{semilla}_{nombre_archivo}.png")
print("Imagenes guardadas en capturas/")

mujoco.viewer.launch(modelo, datos)