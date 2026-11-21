"""VERSIONES DE MENTIRA ("trampas") de las funciones del contrato.

Hacen lo mismo que haran las funciones de verdad, pero en lugar de MIRAR con las camaras
le preguntan la respuesta al simulador (env.paquetes, env.casas...).
Sirven para que main.py funcione entero (sin la lógica de ia y percepción tho).

Edu y Ale sustituid las funciones trampas estas por las de verdad, con EL MISMO nombre,
lo mismo que reciben y lo mismo que devuelven:
  - paqueteria.py: detectar_paquetes, coger, dejar
  - reparto.py:    detectar_casas, ir_a_casa, volver_a_paqueteria
  - interprete.py: interpretar
"""
import re
import unicodedata

import mujoco
import numpy as np

from escena import PUNTO_RECOGIDA
from robot import BRAZO_LISTO

Y_CALLE = -0.6          # linea central de la calle
DISTANCIA_PUERTA = 0.5  # el robot se para con el punto de entrega 0.5 m por delante


# =====================================================================
# Utilidades comunes (se pueden reutilizar en las versiones de verdad)
# =====================================================================
def esperar_brazo(env, segundos_max=8):
    """Avanza la simulacion hasta que el brazo llegue (o pase el tiempo maximo)."""
    inicio = env.tiempo
    while env.abierto() and not env.brazo.ha_llegado() and env.tiempo - inicio < segundos_max:
        env.paso(10)
    env.paso(100)


def ajustar_angulo(a):
    """Lleva un angulo al rango (-pi, pi]."""
    return (a + np.pi) % (2 * np.pi) - np.pi


def navegar_a(env, x, y, th, tolerancia=0.03, segundos_max=60):
    """Lleva la base a (x, y, th) del mundo en linea recta (la base se mueve en cualquier direccion).
    Control proporcional: cuanto mas lejos esta, mas rapido va (hasta el maximo)."""
    inicio = env.tiempo
    while env.abierto() and env.tiempo - inicio < segundos_max:
        px, py, pth = env.base.pose()
        ex, ey, eth = x - px, y - py, ajustar_angulo(th - pth)
        if np.hypot(ex, ey) < tolerancia and abs(eth) < 0.03:
            break
        vx_mundo, vy_mundo = 1.5 * ex, 1.5 * ey
        # Pasar la velocidad de ejes del mundo a ejes del robot
        vx = np.cos(pth) * vx_mundo + np.sin(pth) * vy_mundo
        vy = -np.sin(pth) * vx_mundo + np.cos(pth) * vy_mundo
        env.base.mover(vx, vy, 2.0 * eth)
        env.paso(5)
    env.base.parar()
    env.paso(100)


def giro_de(cuerpo):
    """Giro (alrededor del eje vertical) de un cuerpo de la simulacion."""
    w, _, _, z = cuerpo.xquat
    return 2 * np.arctan2(z, w)


# La postura "lista" pero girada 180 grados: brazo en alto, apuntando hacia la cesta (detras)
BRAZO_ATRAS = [BRAZO_LISTO[0] + np.pi] + BRAZO_LISTO[1:]
VEL_NORMAL = 1.0        # rad/s, brazo sin paquete
VEL_CON_PAQUETE = 0.4   # rad/s, brazo con paquete: si va rapido, los cilindros se escurren


def pinza_con(env, angulos):
    """Donde quedaria la pinza si el brazo tuviera estos angulos (sin mover nada)."""
    d = mujoco.MjData(env.modelo)
    d.qpos[:] = env.datos.qpos
    for nombre, valor in zip(env.brazo.nombres, angulos):
        d.joint(nombre).qpos = valor
    mujoco.mj_kinematics(env.modelo, d)
    return d.site(env.brazo.sitio).xpos.copy()


def ir_sobre_cesta(env, giro):
    """Lleva la pinza 15 cm por encima del fondo de la cesta: gira el brazo por arriba hacia atras
    y luego va en linea recta (cada punto intermedio se calcula desde el anterior: sin saltos)."""
    env.brazo.mover_a(BRAZO_ATRAS); esperar_brazo(env, 15)
    env.brazo.ir_a(env.posicion_cesta() + [0, 0, 0.15], giro, paso_recto=0.01)
    esperar_brazo(env, 20)


def salir_de_cesta(env):
    """El camino inverso: subir recto, alejarse en linea recta hacia atras y desplegar."""
    giro = env.brazo.giro_pinza()
    env.brazo.ir_a(env.posicion_cesta() + [0, 0, 0.3], giro, paso_recto=0.01); esperar_brazo(env, 15)
    env.brazo.ir_a(pinza_con(env, BRAZO_ATRAS), giro, paso_recto=0.01); esperar_brazo(env, 20)
    env.brazo.mover_a(BRAZO_ATRAS); esperar_brazo(env, 15)
    env.brazo.desplegar(); esperar_brazo(env, 15)


def soltar_en_cesta(env):
    """Con un paquete en la pinza y el brazo desplegado: lo deja caer en la cesta y recoge el brazo."""
    # Se mantiene el giro actual de la pinza: cambiarlo de golpe lanza el paquete
    ir_sobre_cesta(env, env.brazo.giro_pinza())
    env.brazo.abrir_pinza(); env.paso(700)
    env.brazo.velocidad = VEL_NORMAL
    salir_de_cesta(env)
    env.brazo.plegar(); esperar_brazo(env)


def la_casa(color):
    """'la casa roja', 'la casa verde'... (los colores se guardan en masculino)."""
    femenino = {"rojo": "roja", "amarillo": "amarilla", "morado": "morada"}
    return f"la casa {femenino.get(color, color)}"


def describir(p):
    return " ".join(str(p[k]) for k in ("color", "forma", "tamano") if p.get(k))


# =====================================================================
# Paqueteria (las de verdad iran en paqueteria.py)
# =====================================================================
def detectar_paquetes(env):
    """TRAMPA: en vez de mirar la camara cenital, copia la verdad del simulador."""
    detectados = []
    for p in env.paquetes:
        cuerpo = env.datos.body(p["nombre"])
        pos = cuerpo.xpos.copy()
        if abs(pos[0]) > 0.35 or abs(pos[1]) > 0.2 or pos[2] > 0.15:
            continue  # ya no esta en el tablon (esta en la cesta o entregado)
        detectados.append({"color": p["color"], "forma": p["forma"], "tamano": p["tamano"],
                           "punto": pos, "giro": giro_de(cuerpo), "confianza": 1.0,
                           "nombre": p["nombre"]})  # "nombre" solo existe en la trampa
    return detectados


def coger(env, pedido, preguntar):
    """Elige el paquete pedido (preguntando si hay varios), lo coge y lo deja en la cesta."""
    candidatos = [p for p in detectar_paquetes(env)
                  if all(pedido.get(k) in (None, p[k]) for k in ("color", "forma", "tamano"))]
    if not candidatos:
        return {"exito": False, "mensaje": f"No veo ningun paquete {describir(pedido)}.", "paquete": None}

    intentos = 0
    while len(candidatos) > 1 and intentos < 3:
        opciones = ", ".join(f"{i + 1}) {describir(p)}" for i, p in enumerate(candidatos))
        respuesta = preguntar(f"Hay {len(candidatos)} paquetes que encajan: {opciones}. Cual quieres?")
        numero = re.search(r"\d+", respuesta)
        if numero and 1 <= int(numero.group()) <= len(candidatos):
            candidatos = [candidatos[int(numero.group()) - 1]]
        else:
            filtro = rasgos(respuesta)
            filtrados = [p for p in candidatos if all(filtro[k] in (None, p[k]) for k in filtro)]
            candidatos = filtrados or candidatos
        intentos += 1
    paquete = candidatos[0]

    # Brazo: encima, bajar recto, cerrar, subir, llevar sobre la cesta y soltar
    pos, giro = paquete["punto"], paquete["giro"]
    env.brazo.abrir_pinza()
    env.brazo.desplegar(); esperar_brazo(env)
    if not env.brazo.ir_a(pos + [0, 0, 0.15], giro):
        return {"exito": False, "mensaje": "No llego al paquete.", "paquete": None}
    esperar_brazo(env)
    env.brazo.ir_a(pos, giro); esperar_brazo(env)
    env.brazo.cerrar_pinza(); env.paso(600)
    env.brazo.velocidad = VEL_CON_PAQUETE
    env.brazo.ir_a(pos + [0, 0, 0.25], giro); esperar_brazo(env, 15)
    env.brazo.desplegar(); esperar_brazo(env, 15)
    soltar_en_cesta(env)

    en_cesta = np.linalg.norm(env.datos.body(paquete["nombre"]).xpos - env.posicion_cesta()) < 0.12
    if not en_cesta:
        return {"exito": False, "mensaje": "Se me ha caido el paquete.", "paquete": None}
    return {"exito": True, "mensaje": f"Tengo el paquete {describir(paquete)}.", "paquete": paquete}


def dejar(env, punto):
    """Saca el paquete de la cesta y lo deja en el suelo en 'punto'."""
    cesta = env.posicion_cesta()
    todos = list(env.paquetes) + ([env.paquete] if hasattr(env, "paquete") else [])
    en_cesta = [p for p in todos if np.linalg.norm(env.datos.body(p["nombre"]).xpos - cesta) < 0.12]
    if not en_cesta:
        return {"exito": False, "mensaje": "No llevo ningun paquete en la cesta."}
    paquete = en_cesta[0]
    cuerpo = env.datos.body(paquete["nombre"])
    medida = paquete["medida"]
    th = env.base.pose()[2]
    punto = np.array([punto[0], punto[1], 0.0])

    # Sacarlo de la cesta
    giro = giro_de(cuerpo)
    env.brazo.abrir_pinza()
    env.brazo.desplegar(); esperar_brazo(env)
    ir_sobre_cesta(env, giro)
    env.brazo.ir_a(cuerpo.xpos.copy(), giro); esperar_brazo(env)
    env.brazo.cerrar_pinza(); env.paso(600)
    env.brazo.velocidad = VEL_CON_PAQUETE
    salir_de_cesta(env)
    # Dejarlo en el suelo
    if not env.brazo.ir_a(punto + [0, 0, medida + 0.15], th):
        env.brazo.velocidad = VEL_NORMAL
        return {"exito": False, "mensaje": "No llego al punto de entrega."}
    esperar_brazo(env, 15)
    env.brazo.ir_a(punto + [0, 0, medida + 0.005], th); esperar_brazo(env, 15)
    env.brazo.abrir_pinza(); env.paso(500)
    env.brazo.velocidad = VEL_NORMAL
    env.brazo.ir_a(punto + [0, 0, medida + 0.15], th); esperar_brazo(env)
    env.brazo.desplegar(); esperar_brazo(env)
    env.brazo.plegar(); esperar_brazo(env)

    error = np.linalg.norm(cuerpo.xpos[:2] - punto[:2])
    if cuerpo.xpos[2] > 0.15 or error > 0.15:
        return {"exito": False, "mensaje": "El paquete no ha quedado en su sitio."}
    return {"exito": True, "mensaje": "Paquete entregado."}


# =====================================================================
# Reparto (las de verdad iran en reparto.py)
# =====================================================================
def detectar_casas(env):
    """TRAMPA: en vez de mirar la camara frontal, copia la verdad del simulador."""
    return [{"color": color, "punto": env.datos.body(f"casa_{i}/casa").xpos.copy(), "confianza": 1.0}
            for color, i in env.casas.items()]


def ir_a_casa(env, color, preguntar):
    """Va por la calle hasta quedar parado delante de la puerta de la casa de ese color."""
    casas = {c["color"]: c for c in detectar_casas(env)}
    if color not in casas:
        return {"exito": False, "mensaje": f"No encuentro {la_casa(color)}.", "punto_entrega": None}
    # TRAMPA: el punto de entrega de esa casa lo sacamos del simulador
    entrega = env.datos.site(f"casa_{env.casas[color]}/entrega").xpos.copy()
    hacia_calle = (entrega - casas[color]["punto"])[:2]
    hacia_calle /= np.linalg.norm(hacia_calle)
    parada = entrega[:2] + DISTANCIA_PUERTA * hacia_calle
    mirando = np.arctan2(-hacia_calle[1], -hacia_calle[0])

    x, _, _ = env.base.pose()
    navegar_a(env, max(x, 0.8), Y_CALLE, 0.0)        # salir a la calle
    navegar_a(env, parada[0], Y_CALLE, mirando)      # recorrerla hasta la altura de la casa
    navegar_a(env, parada[0], parada[1], mirando)    # acercarse a la puerta
    return {"exito": True, "mensaje": f"Estoy en la puerta de {la_casa(color)}.",
            "punto_entrega": np.array([entrega[0], entrega[1], 0.0])}


def volver_a_paqueteria(env):
    """Vuelve al punto de recogida, mirando al tablon."""
    x, _, _ = env.base.pose()
    navegar_a(env, x, Y_CALLE, np.pi)                # volver a la calle
    navegar_a(env, 0.8, Y_CALLE, np.pi)              # recorrerla hasta la paqueteria
    navegar_a(env, *PUNTO_RECOGIDA)                  # colocarse en el punto de recogida
    return {"exito": True, "mensaje": "He vuelto a la paqueteria."}


# =====================================================================
# Interprete (el de verdad ira en interprete.py, con un LLM)
# =====================================================================
COLORES = {"roj": "rojo", "verd": "verde", "azul": "azul", "amarill": "amarillo",
           "naranj": "naranja", "morad": "morado"}
FORMAS = {"caja": "caja", "cubo": "caja", "cilindr": "cilindro", "bote": "cilindro", "lata": "cilindro"}
TAMANOS = {"grande": "grande", "pequen": "pequeno", "chic": "pequeno"}


def normalizar(texto):
    """Minusculas y sin tildes: 'Llévalo a la CASA' -> 'llevalo a la casa'."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def buscar(texto, diccionario):
    """Primer valor del diccionario cuya raiz aparece al principio de alguna palabra del texto."""
    for raiz, valor in diccionario.items():
        if re.search(r"\b" + raiz, texto):
            return valor
    return None


def rasgos(texto):
    """Color, forma y tamano que aparecen en un trozo de frase (None si no aparecen)."""
    texto = normalizar(texto)
    return {"color": buscar(texto, COLORES), "forma": buscar(texto, FORMAS),
            "tamano": buscar(texto, TAMANOS)}


def interpretar(texto):
    """TRAMPA: busca palabras clave. Parte la frase en trozos por 'y', 'luego', 'despues' y comas."""
    texto = normalizar(texto)
    if re.fullmatch(r"\s*(nada|fin|salir|terminar|ya esta|eso es todo)\W*", texto):
        return {"tareas": [{"accion": "terminar"}], "error": None}
    tareas = []
    for trozo in re.split(r",|\bluego\b|\bdespues\b|\by\b", texto):
        if not trozo.strip():
            continue
        if "casa" in trozo:
            color = buscar(trozo.split("casa", 1)[1], COLORES)
            if color is None:
                return {"tareas": [], "error": "No se a que casa ir: dime su color."}
            tareas.append({"accion": "entregar", "casa": color})
        elif re.search(r"\b(coge|recoge|trae|busca|agarra|pilla)", trozo):
            tareas.append({"accion": "coger", "paquete": rasgos(trozo)})
        elif re.search(r"\b(vuelve|regresa|volver)", trozo):
            tareas.append({"accion": "volver"})
    if not tareas:
        return {"tareas": [], "error": "No te he entendido. Prueba con: "
                                       "'coge el paquete azul y llevalo a la casa verde'."}
    return {"tareas": tareas, "error": None}