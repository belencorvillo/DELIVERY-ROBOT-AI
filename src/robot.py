"""Control del robot: base por velocidad, brazo y pinza."""
import numpy as np
from escena import BRAZO_PLEGADO

VEL_MAX = 0.5      # m/s, velocidad maxima de avance y lateral
GIRO_MAX = 1.0     # rad/s, velocidad maxima de giro
CORREA_POS = 0.1   # m: lo maximo que el objetivo puede adelantarse al robot
CORREA_GIRO = 0.3  # rad


class Base:
    """Base movil controlada por velocidad (vx adelante, vy izquierda, wz giro)."""

    def __init__(self, modelo, datos, prefijo="robot/"):
        self.datos = datos
        self.dt = modelo.opt.timestep
        self.nombres = [prefijo + "joint_x", prefijo + "joint_y", prefijo + "joint_th"]
        self.velocidad = np.zeros(3)

    def pose(self):
        """Posicion actual en el mundo: (x, y, th)."""
        return np.array([self.datos.joint(n).qpos[0] for n in self.nombres])

    def mover(self, vx, vy, wz):
        """Ordena moverse. vx, vy en ejes del robot (m/s), wz en rad/s."""
        self.velocidad[:] = [np.clip(vx, -VEL_MAX, VEL_MAX),
                             np.clip(vy, -VEL_MAX, VEL_MAX),
                             np.clip(wz, -GIRO_MAX, GIRO_MAX)]

    def parar(self):
        self.mover(0, 0, 0)

    def paso(self):
        """Llamar en cada paso de simulacion, antes de mj_step."""
        vx, vy, wz = self.velocidad
        objetivo = np.array([self.datos.actuator(n).ctrl[0] for n in self.nombres])
        th = objetivo[2]
        # Pasar la velocidad de ejes del robot a ejes del mundo y avanzar un paso
        objetivo += np.array([vx * np.cos(th) - vy * np.sin(th),
                              vx * np.sin(th) + vy * np.cos(th),
                              wz]) * self.dt
        # La "correa": el objetivo no se aleja demasiado de donde esta el robot
        actual = self.pose()
        correa = np.array([CORREA_POS, CORREA_POS, CORREA_GIRO])
        objetivo = np.clip(objetivo, actual - correa, actual + correa)
        for nombre, valor in zip(self.nombres, objetivo):
            self.datos.actuator(nombre).ctrl = valor


            

# ---------------- Brazo y pinza ----------------
# Postura "home" del TidyBot: brazo desplegado, listo para trabajar
BRAZO_LISTO = [0, 0.26179939, 3.14159265, -2.26892803, 0, 0.95993109, 1.57079633]


class Brazo:
    """Brazo de 7 articulaciones + pinza. Motores de posicion: se les da angulos (radianes)."""

    def __init__(self, modelo, datos, prefijo="robot/"):
        self.datos = datos
        self.prefijo = prefijo
        self.nombres = [f"{prefijo}joint_{i}" for i in range(1, 8)]

    def angulos(self):
        """Angulos actuales de las 7 articulaciones."""
        return [float(self.datos.joint(n).qpos[0]) for n in self.nombres]

    def mover_a(self, angulos):
        """Ordena ir a estos 7 angulos (los motores se encargan de llegar)."""
        for nombre, valor in zip(self.nombres, angulos):
            self.datos.actuator(nombre).ctrl = valor

    def plegar(self):
        self.mover_a(BRAZO_PLEGADO)

    def desplegar(self):
        self.mover_a(BRAZO_LISTO)

    def abrir_pinza(self):
        self.datos.actuator(self.prefijo + "fingers_actuator").ctrl = 0

    def cerrar_pinza(self):
        self.datos.actuator(self.prefijo + "fingers_actuator").ctrl = 255

    def posicion_pinza(self):
        """Punto entre los dedos de la pinza, en coordenadas del mundo."""
        return self.datos.site(self.prefijo + "pinch_site").xpos.copy()