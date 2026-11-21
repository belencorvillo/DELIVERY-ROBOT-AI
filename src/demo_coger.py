"""Demo: coge un paquete del tablon y lo deja en la cesta (usando la version trampa de coger).
Uso: python src/demo_coger.py 3 rojo      (semilla, color del paquete)
"""
import sys

from entorno import Entorno
from trampas import coger

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 3
color = sys.argv[2] if len(sys.argv) > 2 else "rojo"

env = Entorno("pick", semilla=semilla, visor=True)
resultado = coger(env, {"color": color, "forma": None, "tamano": None},
                  preguntar=lambda texto: input(f"Robot: {texto}\nTu: "))
print(f"Robot: {resultado['mensaje']}")

while env.abierto():   # dejar el visor abierto hasta que lo cierres
    env.paso()
env.cerrar()