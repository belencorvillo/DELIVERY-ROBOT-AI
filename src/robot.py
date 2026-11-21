"""Control del robot: base por velocidad, brazo y pinza."""
import mujoco
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
VEL_ARTICULACION = 1.0  # rad/s: lo rapido que se mueve cada articulacion


def orientacion_pinza(giro):
    """Pinza apuntando hacia abajo; los dedos cierran en la direccion 'giro' (rad) del suelo."""
    c, s = np.cos(giro), np.sin(giro)
    return np.array([[c, s, 0], [s, -c, 0], [0, 0, -1]]).T  # columnas: ejes x, y, z


class Brazo:
    """Brazo de 7 articulaciones + pinza."""

    def __init__(self, modelo, datos, prefijo="robot/"):
        self.modelo = modelo
        self.datos = datos
        self.prefijo = prefijo
        self.dt = modelo.opt.timestep
        self.nombres = [f"{prefijo}joint_{i}" for i in range(1, 8)]
        self.sitio = prefijo + "pinch_site"
        self.objetivo = None  # angulos a los que se dirige ahora (None = quieto)
        self.cola = []        # siguientes objetivos (para moverse en linea recta)
        self.velocidad = VEL_ARTICULACION  # rad/s; bajadla al llevar un paquete para que no se escurra
    # ----- Mover por angulos -----
    def angulos(self):
        """Angulos actuales de las 7 articulaciones (radianes)."""
        return np.array([self.datos.joint(n).qpos[0] for n in self.nombres])

    def mover_a(self, angulos):
        """Ordena ir a estos 7 angulos. El movimiento es suave (ver paso)."""
        self.cola = []
        self.objetivo = np.array(angulos, dtype=float)

    def plegar(self):
        self.mover_a(BRAZO_PLEGADO)

    def desplegar(self):
        self.mover_a(BRAZO_LISTO)

    def ha_llegado(self, tolerancia=0.02):
        """True si el brazo ya esta (casi) en los angulos pedidos y no queda nada en cola."""
        if self.objetivo is None:
            return True
        return not self.cola and np.max(np.abs(self.angulos() - self.objetivo)) < tolerancia

    def paso(self):
        """Llamar en cada paso de simulacion: acerca los motores al objetivo poco a poco."""
        if self.objetivo is None:
            return
        # Si el punto intermedio ya esta casi alcanzado, pasar al siguiente de la cola
        if self.cola and np.max(np.abs(self.angulos() - self.objetivo)) < 0.05:
            self.objetivo = self.cola.pop(0)
        actual = np.array([self.datos.actuator(n).ctrl[0] for n in self.nombres])
        maximo = self.velocidad * self.dt
        nuevo = actual + np.clip(self.objetivo - actual, -maximo, maximo)
        for nombre, valor in zip(self.nombres, nuevo):
            self.datos.actuator(nombre).ctrl = valor

    # ----- Mover por posicion de la pinza (cinematica inversa) -----
    def posicion_pinza(self):
        """Punto entre los dedos de la pinza, en coordenadas del mundo."""
        return self.datos.site(self.sitio).xpos.copy()
    
    def giro_pinza(self):
        """Direccion (rad) en la que cierran ahora los dedos, vista desde arriba."""
        eje_x = self.datos.site(self.sitio).xmat.reshape(3, 3)[:, 0]
        return float(np.arctan2(eje_x[1], eje_x[0]))

    def cinematica_inversa(self, punto, giro=0.0, inicial=None, iteraciones=500):
        """Calcula los 7 angulos que llevan la pinza a 'punto' (x, y, z del mundo),
        apuntando hacia abajo y con los dedos cerrando en la direccion 'giro'.
        'inicial': angulos desde los que empezar a buscar (por defecto, los actuales).
        Devuelve (angulos, exito). No mueve el robot: solo calcula."""
        m = self.modelo
        d = mujoco.MjData(m)            # copia "de pruebas" para no tocar la simulacion
        d.qpos[:] = self.datos.qpos
        qadr = [m.joint(n).qposadr[0] for n in self.nombres]
        vadr = [m.joint(n).dofadr[0] for n in self.nombres]
        ids = [m.joint(n).id for n in self.nombres]
        if inicial is not None:
            d.qpos[qadr] = inicial
        sid = m.site(self.sitio).id
        punto = np.asarray(punto, dtype=float)
        rot_deseada = orientacion_pinza(giro)
        jacp, jacr = np.zeros((3, m.nv)), np.zeros((3, m.nv))

        for inicio in (None, BRAZO_LISTO):   # si falla desde la postura actual, reintenta
            if inicio is not None:
                d.qpos[qadr] = inicio
            for _ in range(iteraciones):
                mujoco.mj_kinematics(m, d)
                mujoco.mj_comPos(m, d)
                rot = d.site_xmat[sid].reshape(3, 3)
                error_pos = punto - d.site_xpos[sid]
                error_rot = 0.5 * sum(np.cross(rot[:, k], rot_deseada[:, k]) for k in range(3))
                if np.linalg.norm(error_pos) < 0.003 and np.linalg.norm(error_rot) < 0.02:
                    return d.qpos[qadr].copy(), True
                # Jacobiano: como se mueve la pinza al mover cada articulacion
                mujoco.mj_jacSite(m, d, jacp, jacr, sid)
                J = np.vstack([jacp[:, vadr], jacr[:, vadr]])
                error = np.concatenate([error_pos, error_rot])
                # Minimos cuadrados amortiguados: el paso que mas reduce el error sin dar tirones
                dq = J.T @ np.linalg.solve(J @ J.T + 0.05 ** 2 * np.eye(6), error)
                q = d.qpos[qadr] + np.clip(dq, -0.2, 0.2)
                for k, j in enumerate(ids):  # respetar los limites de cada articulacion
                    if m.jnt_limited[j]:
                        q[k] = np.clip(q[k], *m.jnt_range[j])
                d.qpos[qadr] = q
        return d.qpos[qadr].copy(), False

    def ir_a(self, punto, giro=0.0, paso_recto=0.02):
        """Mueve la pinza a 'punto' (apuntando hacia abajo) EN LINEA RECTA,
        pasando por puntos intermedios cada 'paso_recto' metros. Devuelve False si no llega.
        Llamarla UNA vez por destino (calcula mucho), no en cada paso."""
        inicio = self.posicion_pinza()
        punto = np.asarray(punto, dtype=float)
        n = max(1, int(np.ceil(np.linalg.norm(punto - inicio) / paso_recto)))
        angulos = self.angulos() if self.objetivo is None else self.objetivo
        trayectoria = []
        for k in range(1, n + 1):
            intermedio = inicio + (punto - inicio) * k / n
            angulos, exito = self.cinematica_inversa(intermedio, giro, inicial=angulos)
            if not exito:
                if k < n:   # un punto intermedio raro: lo saltamos
                    continue
                return False
            trayectoria.append(angulos)
        self.objetivo, self.cola = trayectoria[0], trayectoria[1:]
        return True

    # ----- Pinza -----
    def abrir_pinza(self):
        self.datos.actuator(self.prefijo + "fingers_actuator").ctrl = 0

    def cerrar_pinza(self):
        self.datos.actuator(self.prefijo + "fingers_actuator").ctrl = 255