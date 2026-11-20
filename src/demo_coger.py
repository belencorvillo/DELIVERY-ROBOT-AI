"""Demo: coge un paquete del tablon y lo deja en la cesta usando la cinematica inversa.
Uso: python src/demo_coger.py 3 0      (semilla, numero de paquete)

OJO: para la demo usamos env.paquetes (la verdad de referencia) para saber donde esta
el paquete. La logica de verdad tiene que sacarlo de la camara cenital.
"""
import sys

from entorno import Entorno
from robot import BRAZO_LISTO

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 3
numero = int(sys.argv[2]) if len(sys.argv) > 2 else 0

env = Entorno("pick", semilla=semilla, visor=True)
paquete = env.paquetes[numero]
pos = env.datos.body(paquete["nombre"]).xpos.copy()   # trampa solo para la demo
giro = paquete["giro"]
print(f"Voy a por el paquete {paquete['color']} ({paquete['forma']}, {paquete['tamano']})")


def esperar_brazo(segundos_max=8):
    """Avanza la simulacion hasta que el brazo llegue (o pase el tiempo maximo)."""
    inicio = env.tiempo
    while env.abierto() and not env.brazo.ha_llegado() and env.tiempo - inicio < segundos_max:
        env.paso(10)
    env.paso(100)  # un respiro para que se asiente


# 1. Preparar: brazo desplegado y pinza abierta
env.brazo.desplegar()
env.brazo.abrir_pinza()
esperar_brazo()

# 2. Ponerse encima del paquete y bajar en linea recta
env.brazo.ir_a(pos + [0, 0, 0.15], giro)
esperar_brazo()
env.brazo.ir_a(pos, giro)
esperar_brazo()

# 3. Cerrar la pinza y levantar
env.brazo.cerrar_pinza()
env.paso(600)
env.brazo.ir_a(pos + [0, 0, 0.25], giro)
esperar_brazo()

# 4. Llevarlo sobre la cesta (pasando por la postura "lista") y soltarlo
env.brazo.desplegar()
esperar_brazo()
cesta = env.posicion_cesta()
orientacion_robot = env.base.pose()[2]
angulos, exito = env.brazo.cinematica_inversa(cesta + [0, 0, 0.15], orientacion_robot, inicial=BRAZO_LISTO)
env.brazo.mover_a(angulos)
esperar_brazo()
env.brazo.abrir_pinza()
env.paso(700)

# 5. Recoger el brazo
env.brazo.desplegar()
esperar_brazo()
env.brazo.plegar()
esperar_brazo()

dentro = abs(env.datos.body(paquete["nombre"]).xpos - env.posicion_cesta())[2] < 0.06
print("Paquete en la cesta!" if dentro else "Vaya, el paquete no ha caido en la cesta")

while env.abierto():   # dejar el visor abierto hasta que lo cierres
    env.paso()
env.cerrar()