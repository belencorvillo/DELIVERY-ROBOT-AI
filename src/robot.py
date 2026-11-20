"""Control del robot: base por velocidad."""
import numpy as np

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