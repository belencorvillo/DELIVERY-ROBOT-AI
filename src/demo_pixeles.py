"""Demo: pasar de pixel a punto del mundo (y al reves) con la camara cenital.
Uso: python src/demo_pixeles.py 3

Para cada paquete:
  1. mundo_a_pixel: donde aparece en la imagen su cara de arriba (lo marcamos con una cruz)
  2. pixel_a_mundo: desde ese pixel, volvemos a calcular el punto 3D y medimos el error
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

from entorno import Entorno

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 3
env = Entorno("pick", semilla=semilla)

imagen = Image.fromarray(env.camara("cam_cenital"))
profundidad = env.camara("cam_cenital", profundidad=True)
dibujo = ImageDraw.Draw(imagen)

print(f"{'paquete':10} {'pixel (u, v)':>14}   {'punto real':>22}   {'punto calculado':>22}   error")
for p in env.paquetes:
    centro = env.datos.body(p["nombre"]).xpos            # verdad de referencia (solo para comprobar)
    arriba = centro + [0, 0, p["medida"]]                  # centro de la cara de arriba
    u, v = env.mundo_a_pixel("cam_cenital", arriba)
    calculado = env.pixel_a_mundo("cam_cenital", round(u), round(v), profundidad)
    error = np.linalg.norm(calculado - arriba)
    print(f"{p['nombre']:10} ({u:5.0f}, {v:5.0f})   {np.round(arriba, 3)!s:>22}   "
          f"{np.round(calculado, 3)!s:>22}   {error * 1000:.1f} mm")
    dibujo.line([(u - 8, v), (u + 8, v)], fill="white", width=2)
    dibujo.line([(u, v - 8), (u, v + 8)], fill="white", width=2)

os.makedirs("capturas", exist_ok=True)
imagen.save(f"capturas/pixeles_semilla{semilla}.png")
print(f"Imagen con las cruces en capturas/pixeles_semilla{semilla}.png")
env.cerrar()