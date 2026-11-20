"""Ejemplo de uso del Entorno: plantilla para las logicas de cada compi.
Uso: python src/ejemplo_entorno.py
"""
from entorno import Entorno

env = Entorno("reparto", semilla=3, visor=True)
print("Casas:", env.casas, "| Paquete en la cesta:", env.paquete["color"])

estado = "girar_a_la_calle"
while env.abierto():
    # 1. Mirar (10 veces por segundo es suficiente; renderizar en cada paso es lento)
    if round(env.tiempo * 1000) % 100 == 0:
        imagen = env.camara("robot/frontal")
        # ... aqui ira la vision: buscar la casa del color pedido en "imagen"

    # 2. Decidir (aqui ira la logica de verdad; esto es un ejemplo a ciegas)
    x, y, th = env.base.pose()
    if estado == "girar_a_la_calle":
        env.base.mover(0, 0, -0.8)
        if th < 0.02:
            estado = "avanzar"
    elif estado == "avanzar":
        env.base.mover(0.5, 0, 0)
        if x > 9:
            estado = "parado"
            print(f"Llegue a x={x:.2f}. Distancia a la entrega de casa_1: {env.distancia_entrega(1):.2f} m")
    else:
        env.base.parar()

    # 3. Avanzar la simulacion
    env.paso()

env.cerrar()