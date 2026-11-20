"""Generacion aleatoria de los paquetes de la zona de paqueteria."""
import numpy as np
import mujoco

# Paleta de colores (nombre -> rojo, verde, azul, opacidad)
COLORES = {
    "rojo":     [0.85, 0.10, 0.10, 1],
    "verde":    [0.10, 0.65, 0.20, 1],
    "azul":     [0.10, 0.30, 0.90, 1],
    "amarillo": [0.95, 0.85, 0.10, 1],
    "naranja":  [0.95, 0.50, 0.05, 1],
    "morado":   [0.55, 0.15, 0.70, 1],
}
FORMAS = ["caja", "cilindro"]
TAMANOS = {"pequeno": 0.03, "grande": 0.045}  # media medida en metros

# 6 huecos del tablon (x, y): 3 columnas x 2 filas
HUECOS = [(x, y) for y in (0.1, -0.1) for x in (-0.3, 0.0, 0.3)]
ALTURA_TABLON = 0.02


def generar_paquetes(semilla):
    """Decide al azar como es cada paquete. Misma semilla -> mismos paquetes."""
    rng = np.random.default_rng(semilla)
    paquetes = []
    for i, (x, y) in enumerate(HUECOS):
        tamano = str(rng.choice(list(TAMANOS)))
        dx, dy = rng.uniform(-0.03, 0.03, size=2)  # pequeno desplazamiento
        paquetes.append({
            "nombre": f"paquete_{i}",
            "color": str(rng.choice(list(COLORES))),
            "forma": str(rng.choice(FORMAS)),
            "tamano": tamano,
            "medida": TAMANOS[tamano],
            "pos": [x + dx, y + dy],
            "giro": rng.uniform(0, np.pi),  # giro sobre el eje Z, en radianes
        })
    return paquetes


def anadir_paquetes(spec, paquetes, altura=ALTURA_TABLON):
    """Mete los paquetes en la escena como cuerpos libres."""
    for p in paquetes:
        r = p["medida"]
        z = altura + r + 0.002  # justo encima del tablon (o de la cesta)
        quat = [np.cos(p["giro"] / 2), 0, 0, np.sin(p["giro"] / 2)]
        body = spec.worldbody.add_body(name=p["nombre"], pos=[*p["pos"], z], quat=quat)
        body.add_freejoint()
        if p["forma"] == "caja":
            tipo, size = mujoco.mjtGeom.mjGEOM_BOX, [r, r, r]
        else:
            tipo, size = mujoco.mjtGeom.mjGEOM_CYLINDER, [r, r, 0]
        body.add_geom(type=tipo, size=size, rgba=COLORES[p["color"]], mass=0.2)

