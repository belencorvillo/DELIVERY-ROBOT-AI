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
import numpy as np

from escena import (construir_escena_pick, construir_escena_reparto, colocar_robot,
                    PUNTO_RECOGIDA, distancia_entrega)
from robot import Base, Brazo

def region_principal(mascara):
    """Se queda con la region conectada principal de la mascara, quitando los pixeles
    sueltos de ruido que deja el renderizado."""
    if not mascara.any():
        return mascara
    # 1. Semilla: el pixel con mas vecinos dentro de la mascara (seguro que es de la mancha)
    m = np.pad(mascara, 1).astype(np.uint8)
    alto, ancho = mascara.shape
    vecinos = sum(m[1 + df:1 + df + alto, 1 + dc:1 + dc + ancho]
                  for df in (-1, 0, 1) for dc in (-1, 0, 1)) * mascara
    semilla = np.unravel_index(np.argmax(vecinos), mascara.shape)
    # 2. Crecer desde la semilla visitando vecinos que esten en la mascara ("relleno")
    dentro = mascara.tolist()
    mancha = np.zeros_like(mascara)
    pendientes = [semilla]
    mancha[semilla] = True
    while pendientes:
        f, c = pendientes.pop()
        for nf in (f - 1, f, f + 1):
            for nc in (c - 1, c, c + 1):
                if 0 <= nf < alto and 0 <= nc < ancho and dentro[nf][nc] and not mancha[nf, nc]:
                    mancha[nf, nc] = True
                    pendientes.append((nf, nc))
    return mancha


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
        self.ancho, self.alto = ancho, alto
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

    def _datos_camara(self, nombre):
        """Posicion, orientacion (columnas = ejes x, y, z de la camara) y focal en pixeles."""
        cam = self.datos.cam(nombre)
        fovy = np.radians(self.modelo.cam(nombre).fovy[0])
        focal = (self.alto / 2) / np.tan(fovy / 2)
        return cam.xpos.copy(), cam.xmat.reshape(3, 3).copy(), focal

    def pixel_a_mundo(self, nombre, u, v, profundidad=None):
        """Punto (x, y, z) del mundo que se ve en el pixel (u, v) de una camara.
        u = columna (0 = izquierda), v = fila (0 = arriba).
        'profundidad': imagen de profundidad de esa camara (si no se da, se calcula ahora)."""
        if profundidad is None:
            profundidad = self.camara(nombre, profundidad=True)
        d = float(profundidad[int(v), int(u)])          # metros, a lo largo del eje de la camara
        pos, rot, focal = self._datos_camara(nombre)
        x = (u + 0.5 - self.ancho / 2) * d / focal       # a la derecha de la camara
        y = -(v + 0.5 - self.alto / 2) * d / focal       # hacia arriba de la camara
        punto_camara = np.array([x, y, -d])              # la camara mira hacia su -Z
        return pos + rot @ punto_camara

    def mundo_a_pixel(self, nombre, punto):
        """Pixel (u, v) donde aparece un punto (x, y, z) del mundo. None si queda detras."""
        pos, rot, focal = self._datos_camara(nombre)
        x, y, z = rot.T @ (np.asarray(punto, dtype=float) - pos)
        if z >= 0:
            return None
        d = -z
        u = x * focal / d + self.ancho / 2 - 0.5
        v = -y * focal / d + self.alto / 2 - 0.5
        return u, v


    def posicion_cesta(self):
        """Centro del fondo de la cesta del robot, en coordenadas del mundo."""
        return self.datos.body("robot/cesta").xpos.copy() + [0, 0, 0.01]

    # ---------- Metricas (para evaluar, NO para que la logica haga trampas) ----------
       # ---------- Metricas y etiquetas (para evaluar y generar datos, NO para la logica) ----------
    def etiquetas(self, nombre_camara=None):
        """Imagen de una camara + la verdad de cada objeto que aparece en ella.
        Escena "pick": los paquetes (por defecto con la camara cenital).
        Escena "reparto": las casas (por defecto con la camara frontal).
        Cada objeto visible trae su recuadro en la imagen [u_min, v_min, u_max, v_max],
        cuantos pixeles se ven de el y su mascara (True en los pixeles donde se ve).
        SOLO para generar datasets y evaluar: la logica del robot no debe usarla."""
        if self.escena == "pick":
            nombre_camara = nombre_camara or "cam_cenital"
            objetos = [dict(p, geom=self.modelo.body(p["nombre"]).geomadr[0]) for p in self.paquetes]
        else:
            nombre_camara = nombre_camara or "robot/frontal"
            objetos = [{"nombre": f"casa_{i}", "color": color,
                        "geom": self.modelo.geom(f"casa_{i}/paredes").id}
                       for color, i in sorted(self.casas.items(), key=lambda c: c[1])]

        imagen = self.camara(nombre_camara)
        # Segmentacion: para cada pixel, que objeto de la escena se ve en el
        self._renderer.enable_segmentation_rendering()
        self._renderer.update_scene(self.datos, camera=nombre_camara)
        segmentacion = self._renderer.render()
        self._renderer.disable_segmentation_rendering()
        es_geom = segmentacion[:, :, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)

        visibles = []
        for objeto in objetos:
            mascara = region_principal(es_geom & (segmentacion[:, :, 0] == objeto["geom"]))
            if not mascara.any():
                continue                      # no se ve (fuera de la imagen o tapado)
            filas, columnas = np.nonzero(mascara)
            etiqueta = {k: v for k, v in objeto.items() if k != "geom"}
            etiqueta["recuadro"] = [int(columnas.min()), int(filas.min()),
                                    int(columnas.max()), int(filas.max())]
            etiqueta["pixeles"] = int(mascara.sum())
            etiqueta["mascara"] = mascara
            visibles.append(etiqueta)
        return imagen, visibles

    def distancia_entrega(self, casa):
        return distancia_entrega(self.modelo, self.datos, casa)