"""Genera la zona de paqueteria con una semilla, guarda lo que ven las camaras y abre el visor.
Uso: python src/ver_paquetes.py 3
"""
import os
import sys

import mujoco
import mujoco.viewer
from PIL import Image

from paquetes import construir_escena_pick

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 0
modelo, paquetes = construir_escena_pick(semilla)
datos = mujoco.MjData(modelo)

print(f"Semilla {semilla}:")
for p in paquetes:
    print(f"  {p['nombre']}: {p['color']:9} {p['forma']:9} {p['tamano']}")

# Simular 1 segundo (500 pasos de 2 ms) para que los paquetes se asienten
mujoco.mj_step(modelo, datos, nstep=500)

os.makedirs("capturas", exist_ok=True)
with mujoco.Renderer(modelo, 480, 640) as renderer:
    for camara in ["cam_cenital", "cam_alzado"]:
        renderer.update_scene(datos, camera=camara)
        Image.fromarray(renderer.render()).save(f"capturas/semilla{semilla}_{camara}.png")
print("Imagenes guardadas en capturas/")

mujoco.viewer.launch(modelo, datos)