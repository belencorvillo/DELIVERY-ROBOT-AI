"""Demo: etiquetas automaticas (recuadros) para generar datasets.
Uso: python src/demo_etiquetas.py 3

Guarda dos imagenes en capturas/ con un recuadro y su etiqueta encima de cada objeto:
  - paqueteria (camara cenital): color, forma y tamano de cada paquete
  - urbanizacion (camara frontal, con el robot ya mirando a la calle): color de cada casa
"""
import os
import sys

from PIL import Image, ImageDraw

from entorno import Entorno

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 3
os.makedirs("capturas", exist_ok=True)


def dibujar(imagen, etiquetas, texto, archivo):
    lienzo = Image.fromarray(imagen)
    dibujo = ImageDraw.Draw(lienzo)
    for e in etiquetas:
        u0, v0, u1, v1 = e["recuadro"]
        dibujo.rectangle([u0, v0, u1, v1], outline="white", width=2)
        dibujo.text((u0 + 2, max(0, v0 - 12)), texto(e), fill="white")
        print(f"  {e['nombre']:10} {texto(e):25} recuadro {e['recuadro']}  ({e['pixeles']} pixeles)")
    lienzo.save(archivo)
    print(f"  -> {archivo}")


# 1. Paqueteria
env = Entorno("pick", semilla=semilla)
imagen, etiquetas = env.etiquetas()
print("Paqueteria:")
dibujar(imagen, etiquetas, lambda e: f"{e['color']} {e['forma']} {e['tamano']}",
        f"capturas/etiquetas_pick{semilla}.png")
env.cerrar()

# 2. Urbanizacion: girar el robot hacia la calle y avanzar un poco
env = Entorno("reparto", semilla=semilla)
env.base.mover(0, 0, -0.8)
while env.base.pose()[2] > 0.01:
    env.paso()
env.base.mover(0.5, 0, 0)
while env.base.pose()[0] < 2.5:
    env.paso()
env.base.parar()
env.paso(300)
imagen, etiquetas = env.etiquetas()
print("Urbanizacion:")
dibujar(imagen, etiquetas, lambda e: f"casa {e['color']}", f"capturas/etiquetas_reparto{semilla}.png")
env.cerrar()