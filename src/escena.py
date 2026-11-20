"""Construccion de las escenas: mundo + zona + paquetes + robot."""
import numpy as np
import mujoco

from paquetes import generar_paquetes, anadir_paquetes

RUTA_ROBOT = "assets/tidybot/tidybot.xml"

# Pose del robot en el punto de recogida: x, y, orientacion (pi/2 = mirando a +Y, al tablon)
PUNTO_RECOGIDA = (0.0, -0.6, np.pi / 2)

ARTICULACIONES_BRAZO = [f"robot/joint_{i}" for i in range(1, 8)]
# Postura "retract" del TidyBot: brazo plegado para moverse sin chocar
BRAZO_PLEGADO = [0, -0.34906585, 3.14159265, -2.54818071, 0, -0.87266463, 1.57079633]


def anadir_cesta(spec_robot):
    """Cesta en la parte trasera de la base, detras del brazo."""
    base = spec_robot.body("base_link")
    cesta = base.add_body(name="cesta", pos=[-0.16, 0, 0.335])
    gris = [0.35, 0.35, 0.4, 1]
    piezas = [  # (media medida, posicion) de cada tabla de la cesta
        ([0.07, 0.15, 0.005], [0, 0, 0.005]),        # fondo
        ([0.07, 0.005, 0.03], [0, 0.145, 0.035]),    # pared izquierda
        ([0.07, 0.005, 0.03], [0, -0.145, 0.035]),   # pared derecha
        ([0.005, 0.15, 0.03], [0.065, 0, 0.035]),    # pared delantera
        ([0.005, 0.15, 0.03], [-0.065, 0, 0.035]),   # pared trasera
    ]
    for i, (size, pos) in enumerate(piezas):
        cesta.add_geom(name=f"cesta_{i}", type=mujoco.mjtGeom.mjGEOM_BOX,
                       size=size, pos=pos, rgba=gris)


def anadir_robot(spec):
    """Engancha el TidyBot (con cesta) a la escena. Sus nombres empiezan por 'robot/'."""
    spec_robot = mujoco.MjSpec.from_file(RUTA_ROBOT)
    anadir_cesta(spec_robot)
    # Opciones de simulacion que recomienda el modelo del TidyBot
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    spec.option.cone = mujoco.mjtCone.mjCONE_ELLIPTIC
    spec.option.impratio = 10
    marco = spec.worldbody.add_frame()
    spec.attach(spec_robot, frame=marco, prefix="robot/")


def construir_escena_pick(semilla, ruta="escenas/escena_pick.xml"):
    """Escena de paqueteria: mundo + zona + 6 paquetes aleatorios + robot."""
    spec = mujoco.MjSpec.from_file(ruta)
    paquetes = generar_paquetes(semilla)
    anadir_paquetes(spec, paquetes)
    anadir_robot(spec)
    return spec.compile(), paquetes


def colocar_robot(modelo, datos, x, y, th):
    """Pone el robot en (x, y, th) con el brazo plegado y la pinza abierta."""
    valores = {"robot/joint_x": x, "robot/joint_y": y, "robot/joint_th": th}
    valores.update(zip(ARTICULACIONES_BRAZO, BRAZO_PLEGADO))
    for nombre, valor in valores.items():
        datos.joint(nombre).qpos = valor      # donde esta
        datos.actuator(nombre).ctrl = valor   # donde el motor quiere que este
    datos.actuator("robot/fingers_actuator").ctrl = 0  # 0 = abierta, 255 = cerrada
    mujoco.mj_forward(modelo, datos)