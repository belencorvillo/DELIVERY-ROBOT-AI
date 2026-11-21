"""Construccion de las escenas: mundo + zona + paquetes + robot."""
import numpy as np
import mujoco

from paquetes import generar_paquetes, anadir_paquetes, COLORES

RUTA_ROBOT = "assets/tidybot/tidybot.xml"

# Pose del robot en el punto de recogida: x, y, orientacion (pi/2 = mirando a +Y, al tablon)
PUNTO_RECOGIDA = (0.0, -0.47, np.pi / 2)

ARTICULACIONES_BRAZO = [f"robot/joint_{i}" for i in range(1, 8)]
# Postura "retract" del TidyBot: brazo plegado para moverse sin chocar
BRAZO_PLEGADO = [0, -0.34906585, 3.14159265, -2.54818071, 0, -0.87266463, 1.57079633]


# ---------------- Robot ----------------
ALTURA_SOPORTE = 0.15   # la cesta va subida en un soporte para que el brazo llegue a su fondo


def anadir_cesta(spec_robot):
    """Cesta en la parte trasera de la base, detras del brazo, subida sobre un soporte."""
    base = spec_robot.body("base_link")
    gris = [0.35, 0.35, 0.4, 1]
    base.add_geom(name="soporte_cesta", type=mujoco.mjtGeom.mjGEOM_BOX,
                  size=[0.03, 0.03, ALTURA_SOPORTE / 2], pos=[-0.16, 0, 0.335 + ALTURA_SOPORTE / 2],
                  rgba=[0.25, 0.25, 0.25, 1])
    cesta = base.add_body(name="cesta", pos=[-0.16, 0, 0.335 + ALTURA_SOPORTE])
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
        
def anadir_camara_frontal(spec_robot):
    """Camara para navegar: en un mastil delante, mirando al frente y un poco hacia abajo."""
    base = spec_robot.body("base_link")
    base.add_geom(name="mastil", type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[0.015, 0.1, 0],
                  pos=[0.2, 0, 0.435], rgba=[0.2, 0.2, 0.2, 1], contype=0, conaffinity=0)
    cam = base.add_camera(name="frontal", pos=[0.22, 0, 0.55], fovy=70)
    cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cam.alt.xyaxes = [0, -1, 0, 0.17, 0, 0.985]  # derecha de la imagen, arriba de la imagen


def anadir_robot(spec):
    """Engancha el TidyBot (con cesta y camara frontal) a la escena. Sus nombres empiezan por 'robot/'."""
    spec_robot = mujoco.MjSpec.from_file(RUTA_ROBOT)
    anadir_cesta(spec_robot)
    anadir_camara_frontal(spec_robot)
    # Opciones de simulacion que recomienda el modelo del TidyBot
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    spec.option.cone = mujoco.mjtCone.mjCONE_ELLIPTIC
    spec.option.impratio = 10
    marco = spec.worldbody.add_frame()
    spec.attach(spec_robot, frame=marco, prefix="robot/")


def colocar_robot(modelo, datos, x, y, th):
    """Pone el robot en (x, y, th) con el brazo plegado y la pinza abierta."""
    valores = {"robot/joint_x": x, "robot/joint_y": y, "robot/joint_th": th}
    valores.update(zip(ARTICULACIONES_BRAZO, BRAZO_PLEGADO))
    for nombre, valor in valores.items():
        datos.joint(nombre).qpos = valor      # donde esta
        datos.actuator(nombre).ctrl = valor   # donde el motor quiere que este
    datos.actuator("robot/fingers_actuator").ctrl = 0  # 0 = abierta, 255 = cerrada
    mujoco.mj_forward(modelo, datos)


# ---------------- Paqueteria ----------------
def construir_escena_pick(semilla, ruta="escenas/escena_pick.xml"):
    """Escena de paqueteria: mundo + zona + 6 paquetes aleatorios + robot."""
    spec = mujoco.MjSpec.from_file(ruta)
    paquetes = generar_paquetes(semilla)
    anadir_paquetes(spec, paquetes)
    anadir_robot(spec)
    return spec.compile(), paquetes

# ---------------- Urbanizacion ----------------
RUTA_CASA = "assets/casa.xml"
ALTURA_CESTA = 0.335 + ALTURA_SOPORTE +0.01   # altura del fondo de la cesta sobre el suelo
CESTA_ATRAS = 0.16            # la cesta esta 16 cm por detras del centro de la base

# Donde va cada casa: (x, y, giro en grados). Las del sur giradas 180 para mirar a la calle.
POSICIONES_CASAS = [
    (5, 3.1, 0), (9, 3.1, 0), (13, 3.1, 0),           # norte: casa_0, casa_1, casa_2
    (5, -4.3, 180), (9, -4.3, 180), (13, -4.3, 180),  # sur:   casa_3, casa_4, casa_5
]


def generar_casas(semilla):
    """Reparte los 6 colores entre las 6 casas al azar. Devuelve {color: numero de casa}."""
    rng = np.random.default_rng([semilla, 1])  # flujo aleatorio distinto al de los paquetes
    colores = list(COLORES)
    orden = rng.permutation(len(POSICIONES_CASAS))
    return {colores[k]: int(i) for i, k in enumerate(orden)}


def anadir_casas(spec, casas):
    """Pega la casa modelo en cada posicion, pintada de su color. Nombres: casa_0/..., casa_1/..."""
    color_de = {i: color for color, i in casas.items()}
    for i, (x, y, giro) in enumerate(POSICIONES_CASAS):
        casa = mujoco.MjSpec.from_file(RUTA_CASA)
        casa.geom("paredes").rgba = COLORES[color_de[i]]
        th = np.radians(giro)
        marco = spec.worldbody.add_frame(pos=[x, y, 0], quat=[np.cos(th / 2), 0, 0, np.sin(th / 2)])
        spec.attach(casa, frame=marco, prefix=f"casa_{i}/")


def construir_escena_reparto(semilla, ruta="escenas/escena_reparto.xml"):
    """Escena de reparto: urbanizacion con casas pintadas y robot con un paquete en la cesta."""
    spec = mujoco.MjSpec.from_file(ruta)
    casas = generar_casas(semilla)
    anadir_casas(spec, casas)

    # El paquete que lleva el robot: el primero que salga con esta semilla, puesto en la cesta
    paquete = generar_paquetes(semilla)[0]
    x, y, th = PUNTO_RECOGIDA
    paquete["nombre"] = "paquete_carga"
    paquete["pos"] = [x - CESTA_ATRAS * np.cos(th), y - CESTA_ATRAS * np.sin(th)]
    paquete["giro"] = th
    anadir_paquetes(spec, [paquete], altura=ALTURA_CESTA)

    anadir_robot(spec)
    return spec.compile(), casas, paquete


def distancia_entrega(modelo, datos, casa, paquete="paquete_carga"):
    """Distancia en el suelo (m) entre un paquete y el punto de entrega de una casa."""
    p = datos.body(paquete).xpos[:2]
    objetivo = datos.site(f"casa_{casa}/entrega").xpos[:2]
    return float(np.linalg.norm(p - objetivo))



# ---------------- Escena completa ----------------
def construir_escena_completa(semilla, ruta="escenas/escena_completa.xml"):
    """Todo junto: 6 paquetes en el tablon, urbanizacion con casas pintadas y robot."""
    spec = mujoco.MjSpec.from_file(ruta)
    paquetes = generar_paquetes(semilla)
    anadir_paquetes(spec, paquetes)
    casas = generar_casas(semilla)
    anadir_casas(spec, casas)
    anadir_robot(spec)
    return spec.compile(), paquetes, casas