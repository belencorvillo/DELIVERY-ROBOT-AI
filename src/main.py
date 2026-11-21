"""Programa principal: el robot repartidor obedece ordenes por chat.
Uso: python src/main.py 3        (el numero es la semilla)

Ejemplos de ordenes:
  coge el paquete azul y llevalo a la casa verde
  coge la caja roja, llevala a la casa azul y vuelve
  vuelve
  nada   (para terminar)
"""
import sys

from entorno import Entorno
from escena import PUNTO_RECOGIDA
# Mientras las versiones de verdad no esten listas, usamos las trampas.
# Cuando un compi termine, se cambia SOLO esta parte. Por ejemplo:
#   from paqueteria import coger, dejar
from trampas import interpretar, coger, dejar, ir_a_casa, volver_a_paqueteria, la_casa


def preguntar(texto):
    """Lo que usan las funciones para preguntar algo al usuario por el chat."""
    return input(f"Robot: {texto}\nTu: ")


def en_paqueteria(env):
    """True si el robot esta (mas o menos) en el punto de recogida."""
    x, y, _ = env.base.pose()
    return abs(x - PUNTO_RECOGIDA[0]) < 0.1 and abs(y - PUNTO_RECOGIDA[1]) < 0.1


def ejecutar(env, tareas, estado):
    """Ejecuta las tareas en orden y para en cuanto una falle.
    Devuelve "terminar", "hecho" o "fallo"."""
    for tarea in tareas:
        accion = tarea["accion"]

        if accion == "terminar":
            return "terminar"

        elif accion == "coger":
            if estado["llevo"] is not None:
                print("Robot: Ya llevo un paquete. Primero dime a que casa lo llevo.")
                return "fallo"
            if not en_paqueteria(env):
                print("Robot: Primero vuelvo a la paqueteria...")
                volver_a_paqueteria(env)
            print("Robot: Voy a por el paquete...")
            resultado = coger(env, tarea["paquete"], preguntar)
            if resultado["exito"]:
                estado["llevo"] = resultado["paquete"]

        elif accion == "entregar":
            if estado["llevo"] is None:
                print("Robot: No llevo ningun paquete. Dime primero cual coger.")
                return "fallo"
            print(f"Robot: Voy a {la_casa(tarea['casa'])}...")
            resultado = ir_a_casa(env, tarea["casa"], preguntar)
            if resultado["exito"]:
                print(f"Robot: {resultado['mensaje']}")
                resultado = dejar(env, resultado["punto_entrega"])
                estado["llevo"] = None   # bien o mal entregado, ya no esta en la cesta

        elif accion == "volver":
            print("Robot: Vuelvo a la paqueteria...")
            resultado = volver_a_paqueteria(env)

        print(f"Robot: {resultado['mensaje']}")
        if not resultado["exito"]:
            return "fallo"   # algo ha fallado: no seguimos con el resto de tareas
    return "hecho"


def main():
    semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    env = Entorno("completa", semilla=semilla, visor=True)
    estado = {"llevo": None}   # el paquete que lleva el robot en la cesta (o None)
    print("Robot: Hola! Soy el robot repartidor. Que quieres que haga?")

    while env.abierto():
        orden = input("Tu: ")
        interpretacion = interpretar(orden)
        if interpretacion["error"]:
            print(f"Robot: {interpretacion['error']}")
            continue
        resultado = ejecutar(env, interpretacion["tareas"], estado)
        if resultado == "terminar":
            break
        elif resultado == "hecho":
            print("Robot: Hecho. Que mas?")
        else:
            print("Robot: No he podido terminar. Que hago?")

    print("Robot: Hasta luego!")
    env.cerrar()


if __name__ == "__main__":
    main()