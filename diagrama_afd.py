import math
import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Circle, RegularPolygon, Polygon, FancyArrowPatch

# ---------------------------------------------------------------------------
# Paleta pastel
# ---------------------------------------------------------------------------
COLOR_FONDO = "#FBF7F0"       # fondo pastel general
COLOR_INICIAL = "#AEDFF7"     # azul pastel - estado inicial
COLOR_PROCESO = "#BFE8C0"     # verde pastel - estados de proceso
COLOR_FINAL = "#FFCB9A"       # naranja pastel - estados finales
COLOR_DECISION = "#FFF3B0"    # amarillo pastel - rombos de condición
COLOR_OPERACION = "#D9C6F0"   # morado pastel - paralelogramos (operación realizada)
COLOR_BORDE = "#6B6B6B"       # borde neutro
COLOR_ACTIVO = "#22C7D6"      # turquesa - resaltado de estado/transición activa
COLOR_TEXTO = "#333333"
COLOR_FLECHA = "#8A8A8A"
COLOR_FLECHA_LABEL_BG = "#FFFFFF"

FRIENDLY = {
    "Q0": "ESPERANDO\nTARJETA",
    "Q1": "TARJETA\nINSERTADA",
    "Q2": "SOLICITANDO\nPIN",
    "Q3": "AUTENTICANDO",
    "Q4": "MENÚ DE\nOPERACIONES",
    "Q5": "CONSULTAR\nSALDO",
    "Q6": "RETIRO",
    "Q7": "OPERACIÓN\nREALIZADA",
    "Q8": "TARJETA\nEXPULSADA",
    "FIN": "FINALIZADO",
}

# Tipo de figura para cada nodo real / visual
# circle_start, circle_final, rect, parallelogram, diamond
TIPO_NODO = {
    "Q0": "circle_start",
    "Q1": "rect",
    "Q2": "rect",
    "Q3": "rect",
    "Q4": "rect",
    "Q5": "parallelogram",
    "Q6": "rect",
    "Q7": "parallelogram",
    "Q8": "circle_final",
    "FIN": "circle_final",
    "D1": "diamond",
    "D2": "diamond",
    "D3": "diamond",
    "D4": "diamond",
}

ETIQUETA_DECISION = {
    "D1": "¿Tarjeta\nválida?",
    "D2": "¿PIN\ncorrecto?",
    "D3": "¿Qué\noperación?",
    "D4": "¿Saldo\nsuficiente?",
}

# Posiciones (x, y) de cada nodo en el lienzo
POS = {
    "Q0": (4.5, 18.0),
    "Q1": (4.5, 15.7),
    "D1": (4.5, 13.3),
    "Q2": (4.5, 11.0),
    "Q3": (4.5, 8.7),
    "D2": (4.5, 6.4),
    "Q4": (4.5, 4.1),
    "D3": (4.5, 1.5),
    "Q5": (0.3, -1.3),
    "Q6": (8.7, -1.3),
    "D4": (8.7, -4.0),
    "Q7": (0.3, -4.0),
    "Q8": (14.5, 7.5),
    "FIN": (14.5, 2.5),
}


ARISTAS = [
    ("Q0", "Q1", "insertar_tarjeta", 0.0, "solid", 0.5),
    ("Q1", "D1", None, 0.0, "solid", 0.5),
    ("D1", "Q2", "tarjeta_valida", -0.15, "solid", 0.5),
    ("D1", "Q8", "tarjeta_invalida", 0.28, "solid", 0.55),
    ("Q2", "Q3", "ingresar_pin", 0.0, "solid", 0.5),
    ("Q3", "D2", None, 0.0, "solid", 0.5),
    ("D2", "Q4", "pin_correcto", -0.15, "solid", 0.5),
    ("D2", "Q8", "pin_incorrecto", 0.28, "solid", 0.55),
    ("Q4", "D3", "operar", 0.0, "solid", 0.5),
    ("D3", "Q5", None, -0.15, "solid", 0.5),
    ("D3", "Q6", None, 0.15, "solid", 0.5),
    ("Q5", "Q7", "ver_saldo", -0.15, "solid", 0.5),
    ("Q6", "D4", None, 0.0, "solid", 0.5),
    ("D4", "Q7", "saldo_suficiente", 0.30, "solid", 0.55),
    ("D4", "Q8", "saldo_insuficiente", 0.22, "solid", 0.5),
    ("Q7", "Q8", "finalizar", 0.20, "solid", 0.5),
    ("Q8", "FIN", None, 0.0, "solid", 0.5),
    ("FIN", "Q0", "nueva_sesion", 0.35, "dashed", 0.14),
]


def _radio_para(tipo):
    return 0.95 if tipo in ("circle_start", "circle_final") else 0.8


class DiagramaAFD:
    """Construye una Figure de matplotlib representando el AFD del cajero."""

    def construir_figura(self, estados_actuales=None, ultima_transicion=None, figsize=(7.6, 9.6)):
        """
        estados_actuales: set de estados reales (Q0..Q8) actualmente activos.
        ultima_transicion: dict {"origen": set, "evento": str, "destino": set}
                            o None si aún no ha ocurrido ninguna.
        """
        estados_actuales = estados_actuales or set()

        fig = Figure(figsize=figsize, dpi=100)
        fig.patch.set_facecolor(COLOR_FONDO)
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLOR_FONDO)
        ax.set_xlim(-2.2, 17.5)
        ax.set_ylim(-7.0, 20.0)
        ax.axis("off")
        ax.set_title("Autómata: Sesión de Cajero Automático", fontsize=13,
                      fontweight="bold", color=COLOR_TEXTO, pad=10)

        evento_activo = ultima_transicion["evento"] if ultima_transicion else None
        destino_activo = ultima_transicion["destino"] if ultima_transicion else set()
        origen_activo = ultima_transicion["origen"] if ultima_transicion else set()

        # --- Dibujar aristas primero (para que queden detrás de los nodos) ---
        for (origen, destino, evento, rad, estilo, t_label) in ARISTAS:
            activa = (
                evento is not None
                and evento == evento_activo
                and destino in destino_activo
                and (origen in origen_activo or TIPO_NODO.get(origen) == "diamond")
            )
            self._dibujar_arista(ax, origen, destino, evento, rad, estilo, activa, t_label)

        # --- Dibujar nodos ---
        for nodo, pos in POS.items():
            tipo = TIPO_NODO[nodo]
            es_actual = nodo in estados_actuales
            self._dibujar_nodo(ax, nodo, pos, tipo, es_actual)

        # --- Leyenda ---
        self._dibujar_leyenda(ax)

        fig.tight_layout()
        return fig

    # ------------------------------------------------------------------
    def _dibujar_nodo(self, ax, nodo, pos, tipo, es_actual):
        x, y = pos
        borde = COLOR_ACTIVO if es_actual else COLOR_BORDE
        grosor = 3.4 if es_actual else 1.4

        if tipo == "diamond":
            r = 1.05
            parche = RegularPolygon((x, y), numVertices=4, radius=r,
                                     orientation=0.7854,  # 45°
                                     facecolor=COLOR_DECISION, edgecolor=borde,
                                     linewidth=grosor, zorder=3)
            ax.add_patch(parche)
            texto = ETIQUETA_DECISION.get(nodo, nodo)
            ax.text(x, y, texto, ha="center", va="center", fontsize=7.6,
                     color=COLOR_TEXTO, zorder=4, style="italic")
            return

        if tipo in ("circle_start", "circle_final"):
            color = COLOR_INICIAL if tipo == "circle_start" else COLOR_FINAL
            r = _radio_para(tipo)
            parche = Circle((x, y), radius=r, facecolor=color, edgecolor=borde,
                             linewidth=grosor, zorder=3)
            ax.add_patch(parche)
            if tipo == "circle_final":
                # doble anillo tradicional de estado final
                anillo = Circle((x, y), radius=r - 0.18, facecolor="none",
                                 edgecolor=borde, linewidth=1.3, zorder=3)
                ax.add_patch(anillo)
            texto = FRIENDLY.get(nodo, nodo)
            ax.text(x, y, texto, ha="center", va="center", fontsize=7.8,
                     fontweight="bold", color=COLOR_TEXTO, zorder=4)
            return

        if tipo == "parallelogram":
            w, h, skew = 2.4, 1.3, 0.5
            puntos = [
                (x - w / 2 + skew, y + h / 2),
                (x + w / 2 + skew, y + h / 2),
                (x + w / 2 - skew, y - h / 2),
                (x - w / 2 - skew, y - h / 2),
            ]
            parche = Polygon(puntos, closed=True, facecolor=COLOR_OPERACION,
                              edgecolor=borde, linewidth=grosor, zorder=3)
            ax.add_patch(parche)
            texto = FRIENDLY.get(nodo, nodo)
            ax.text(x, y, texto, ha="center", va="center", fontsize=7.8,
                     fontweight="bold", color=COLOR_TEXTO, zorder=4)
            return

        # rect (proceso)
        w, h = 2.6, 1.3
        parche = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                 boxstyle="round,pad=0.08,rounding_size=0.22",
                                 facecolor=COLOR_PROCESO, edgecolor=borde,
                                 linewidth=grosor, zorder=3)
        ax.add_patch(parche)
        texto = FRIENDLY.get(nodo, nodo)
        ax.text(x, y, texto, ha="center", va="center", fontsize=7.8,
                 fontweight="bold", color=COLOR_TEXTO, zorder=4)

    # ------------------------------------------------------------------
    def _dibujar_arista(self, ax, origen, destino, evento, rad, estilo, activa, t_label=0.5):
        x1, y1 = POS[origen]
        x2, y2 = POS[destino]

        color = COLOR_ACTIVO if activa else COLOR_FLECHA
        grosor = 3.2 if activa else 1.4
        ls = "dashed" if estilo == "dashed" else "solid"

        flecha = FancyArrowPatch(
            (x1, y1), (x2, y2),
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>", mutation_scale=14,
            linewidth=grosor, color=color, linestyle=ls,
            shrinkA=32, shrinkB=32, zorder=2,
        )
        ax.add_patch(flecha)

        if evento:
            mx, my = self._punto_en_curva(x1, y1, x2, y2, rad, t_label)
            # pequeño empujón adicional perpendicular a la línea recta,
            # para separar la etiqueta del trazo en aristas casi rectas.
            dx, dy = x2 - x1, y2 - y1
            dist = math.hypot(dx, dy) or 1.0
            perp = (-dy / dist, dx / dist)
            signo = 1 if rad >= 0 else -1
            mx += perp[0] * 0.32 * signo
            my += perp[1] * 0.32 * signo
            ax.text(mx, my, evento, ha="center", va="center", fontsize=6.6,
                     color=(COLOR_ACTIVO if activa else "#4A4A4A"),
                     fontweight=("bold" if activa else "normal"),
                     bbox=dict(boxstyle="round,pad=0.15", facecolor=COLOR_FLECHA_LABEL_BG,
                               edgecolor="none", alpha=0.85), zorder=5)

    @staticmethod
    def _punto_en_curva(x1, y1, x2, y2, rad, t):
        """Punto sobre la curva de Bézier cuadrática usada por matplotlib
        para 'arc3,rad=...', dado un parámetro t en [0, 1]."""
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1.0
        perp = (-dy / dist, dx / dist)
        cx = (x1 + x2) / 2 + perp[0] * rad * dist
        cy = (y1 + y2) / 2 + perp[1] * rad * dist
        bx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2
        by = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2
        return bx, by

    # ------------------------------------------------------------------
    def _dibujar_leyenda(self, ax):
        items = [
            (COLOR_INICIAL, "Estado inicial"),
            (COLOR_PROCESO, "Estado de proceso"),
            (COLOR_OPERACION, "Operación realizada"),
            (COLOR_DECISION, "Condición"),
            (COLOR_FINAL, "Estado final"),
        ]
        x0, y0 = -2.0, -6.5
        for i, (color, texto) in enumerate(items):
            yy = y0
            xx = x0 + i * 3.9
            ax.add_patch(Circle((xx, yy), radius=0.16, facecolor=color,
                                 edgecolor=COLOR_BORDE, linewidth=1, zorder=6))
            ax.text(xx + 0.35, yy, texto, ha="left", va="center", fontsize=6.6,
                     color=COLOR_TEXTO, zorder=6)
