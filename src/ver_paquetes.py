"""Genera la zona de paqueteria con robot, guarda lo que ven las camaras y abre el visor.
Uso: python src/ver_paquetes.py 3
"""
import os
import sys

import mujoco
import mujoco.viewer
from PIL import Image

from escena import construir_escena_pick, colocar_robot, PUNTO_RECOGIDA

CAMARAS = ["cam_cenital", "robot/base", "robot/wrist"]

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 0
modelo, paquetes = construir_escena_pick(semilla)
datos = mujoco.MjData(modelo)
colocar_robot(modelo, datos, *PUNTO_RECOGIDA)

print(f"Semilla {semilla}:")
for p in paquetes:
    print(f"  {p['nombre']}: {p['color']:9} {p['forma']:9} {p['tamano']}")

# Simular 1 segundo para que todo se asiente
mujoco.mj_step(modelo, datos, nstep=500)

os.makedirs("capturas", exist_ok=True)
with mujoco.Renderer(modelo, 480, 640) as renderer:
    for camara in CAMARAS:
        renderer.update_scene(datos, camera=camara)
        nombre_archivo = camara.replace("/", "_")  # "/" no vale en nombres de archivo
        Image.fromarray(renderer.render()).save(f"capturas/semilla{semilla}_{nombre_archivo}.png")
print("Imagenes guardadas en capturas/")

mujoco.viewer.launch(modelo, datos)