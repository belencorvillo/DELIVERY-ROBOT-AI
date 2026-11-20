"""Entorno comun para todas las escenas. Edu y Ale esto es lo que tenéis que usar :)

Ejemplo en la escena de la urbanizacion ("reparto"):
    env = Entorno("reparto", semilla=3, visor=True)
    while env.abierto():
        imagen = env.camara("robot/frontal")   # mirar
        env.base.mover(0.3, 0, 0)              # decidir: avanzar a 0.3 m/s
        env.paso()                             # avanzar la simulacion
    env.cerrar()

Ejemplo en la escena de paqueteria ("pick"):
    env = Entorno("pick", semilla=3, visor=True)
    imagen = env.camara("cam_cenital")
    profundidad = env.camara("cam_cenital", profundidad=True)
    # ... la vision calcula donde esta el paquete pedido: punto (x, y, z) y su giro
    env.brazo.ir_a(punto, giro)                # UNA vez por destino, no en cada paso
    while env.abierto() and not env.brazo.ha_llegado():
        env.paso()
    env.brazo.cerrar_pinza()
    env.cerrar()
"""
import time

import mujoco
import mujoco.viewer

from escena import (construir_escena_pick, construir_escena_reparto, colocar_robot,
                    PUNTO_RECOGIDA, distancia_entrega)
from robot import Base, Brazo


class Entorno:
    def __init__(self, escena, semilla=0, visor=False, ancho=640, alto=480):
        """escena: "pick" o "reparto". visor=True abre la ventana y va a velocidad real."""
        self.escena = escena
        self.semilla = semilla
        if escena == "pick":
            self.modelo, self.paquetes = construir_escena_pick(semilla)
        elif escena == "reparto":
            self.modelo, self.casas, self.paquete = construir_escena_reparto(semilla)
        else:
            raise ValueError(f"Escena desconocida: {escena}")

        self.datos = mujoco.MjData(self.modelo)
        self.base = Base(self.modelo, self.datos)
        self.brazo = Brazo(self.modelo, self.datos)
        self._renderer = mujoco.Renderer(self.modelo, alto, ancho)
        self._visor = mujoco.viewer.launch_passive(self.modelo, self.datos) if visor else None
        self.reset()

    # ---------- Control de la simulacion ----------
    def reset(self):
        """Vuelve al estado inicial: robot en el punto de recogida, todo asentado."""
        mujoco.mj_resetData(self.modelo, self.datos)
        colocar_robot(self.modelo, self.datos, *PUNTO_RECOGIDA)
        self.base.parar()
        self.brazo.objetivo, self.brazo.cola = None, []
        for _ in range(250):  # medio segundo para que todo se asiente
            mujoco.mj_step(self.modelo, self.datos)
        self._inicio_real = time.time() - self.datos.time

    def paso(self, n=1):
        """Avanza n pasos de simulacion (cada uno dura modelo.opt.timestep = 2 ms)."""
        for _ in range(n):
            self.base.paso()
            self.brazo.paso()
            mujoco.mj_step(self.modelo, self.datos)
        if self._visor is not None:
            self._visor.sync()
            adelanto = self.datos.time - (time.time() - self._inicio_real)
            if adelanto > 0:
                time.sleep(adelanto)

    def abierto(self):
        """True mientras el visor siga abierto (o siempre, si no hay visor)."""
        return self._visor is None or self._visor.is_running()

    def cerrar(self):
        if self._visor is not None:
            self._visor.close()
        self._renderer.close()

    @property
    def tiempo(self):
        return self.datos.time

    # ---------- Sensores ----------
    def camara(self, nombre, profundidad=False):
        """Imagen de una camara (alto x ancho x 3, valores 0-255).
        Con profundidad=True devuelve la distancia en metros de cada pixel."""
        if profundidad:
            self._renderer.enable_depth_rendering()
        self._renderer.update_scene(self.datos, camera=nombre)
        imagen = self._renderer.render()
        if profundidad:
            self._renderer.disable_depth_rendering()
        return imagen

    def posicion_cesta(self):
        """Centro del fondo de la cesta del robot, en coordenadas del mundo."""
        return self.datos.body("robot/cesta").xpos.copy() + [0, 0, 0.01]

    # ---------- Metricas (para evaluar, NO para que la logica haga trampas) ----------
    def distancia_entrega(self, casa):
        return distancia_entrega(self.modelo, self.datos, casa)