import sys
import math
from datetime import datetime
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Circle, RegularPolygon, Polygon, FancyArrowPatch
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QGridLayout,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from automata import Cajero

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
        ax.set_title("Autómata: Sesión de Cajero Automático", fontsize=12,
                     fontweight="bold", color=COLOR_TEXTO, pad=6)

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
                                    orientation=0.7854,
                                    facecolor=COLOR_DECISION, edgecolor=borde,
                                    linewidth=grosor, zorder=3)
            ax.add_patch(parche)
            texto = ETIQUETA_DECISION.get(nodo, nodo)
            ax.text(x, y, texto, ha="center", va="center", fontsize=7.2,
                    color=COLOR_TEXTO, zorder=4, style="italic")
            return

        if tipo in ("circle_start", "circle_final"):
            color = COLOR_INICIAL if tipo == "circle_start" else COLOR_FINAL
            r = _radio_para(tipo)
            parche = Circle((x, y), radius=r, facecolor=color, edgecolor=borde,
                            linewidth=grosor, zorder=3)
            ax.add_patch(parche)
            if tipo == "circle_final":
                anillo = Circle((x, y), radius=r - 0.18, facecolor="none",
                                edgecolor=borde, linewidth=1.3, zorder=3)
                ax.add_patch(anillo)
            texto = FRIENDLY.get(nodo, nodo)
            ax.text(x, y, texto, ha="center", va="center", fontsize=7.2,
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
            ax.text(x, y, texto, ha="center", va="center", fontsize=7.2,
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
        ax.text(x, y, texto, ha="center", va="center", fontsize=7.2,
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
            ax.text(mx, my, evento, ha="center", va="center", fontsize=6.2,
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
            (COLOR_INICIAL, "Inicial"),
            (COLOR_PROCESO, "Proceso"),
            (COLOR_OPERACION, "Operación"),
            (COLOR_DECISION, "Condición"),
            (COLOR_FINAL, "Final"),
        ]
        x0, y0 = -2.0, -6.5
        for i, (color, texto) in enumerate(items):
            yy = y0
            xx = x0 + i * 3.9
            ax.add_patch(Circle((xx, yy), radius=0.16, facecolor=color,
                                edgecolor=COLOR_BORDE, linewidth=1, zorder=6))
            ax.text(xx + 0.35, yy, texto, ha="left", va="center", fontsize=6.2,
                    color=COLOR_TEXTO, zorder=6)


# ---------------------------------------------------------------------------
# INTERFAZ
class CajeroGUIBAC(QMainWindow):
    def __init__(self):
        super().__init__()

        self.cajero = Cajero()

        self.setWindowTitle("Cajero Automático - BAC | AFD")
        self.setFixedSize(1250, 800)

        self.pin_ingresado = ""
        self.monto_ingresado = ""
        self.operacion_actual = None

        self.modo_cambio_pin = False
        self.pin_nuevo_temporal = ""

        self.initUI()
        self.actualizar_visualizacion_afd()

    ROJO = "#C8102E"
    ROJO_OSCURO = "#A50D24"
    FONDO = "#080D16"
    PANEL = "#111827"
    PANEL_2 = "#0B1220"
    BORDE = "#263244"
    TEXTO = "#F3F4F6"
    TEXTO_SEC = "#9CA3AF"
    VERDE = "#22E6A0"

    def initUI(self):
        central = QWidget()
        self.setCentralWidget(central)

        principal = QHBoxLayout(central)
        principal.setContentsMargins(16, 16, 16, 16)
        principal.setSpacing(16)

        # =====================================================
        # PANEL IZQUIERDO - CAJERO
        # =====================================================
        panel_sistema = QFrame()
        panel_sistema.setStyleSheet(f"""
            QFrame {{
                background-color: {self.ROJO};
                border-radius: 16px;
            }}
        """)

        sistema = QVBoxLayout(panel_sistema)
        sistema.setContentsMargins(14, 14, 14, 14)
        sistema.setSpacing(10)

        encabezado = QWidget()
        encabezado.setStyleSheet("background: transparent;")
        h = QHBoxLayout(encabezado)
        h.setContentsMargins(8, 2, 8, 2)

        logo = QLabel()
        logo.setStyleSheet("background: transparent; border: none;")
        pixmap_logo = QPixmap("logo_bac.png")
        if not pixmap_logo.isNull():
            logo.setPixmap(pixmap_logo.scaledToHeight(35, Qt.TransformationMode.SmoothTransformation))
        else:
            logo.setText(
                "<span style='font-size:25pt; font-weight:900; color:white;'>BAC</span>"
                "<span style='font-size:12pt; color:white;'> CREDOMATIC</span>"
            )
        h.addWidget(logo)

        subtitulo = QLabel("SIMULADOR DE CAJERO AUTOMÁTICO")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        subtitulo.setStyleSheet("color:white; font-size:10pt; font-weight:bold; border:none;")
        h.addWidget(subtitulo)

        sistema.addWidget(encabezado)

        pantalla = QFrame()
        pantalla.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 10px;
            }
        """)

        pantalla_layout = QVBoxLayout(pantalla)
        pantalla_layout.setContentsMargins(18, 18, 18, 18)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("border:none; background:transparent;")

        self.stack.addWidget(self.ui_esperando_tarjeta())  # Index 0
        self.stack.addWidget(self.ui_solicitar_pin())  # Index 1
        self.stack.addWidget(self.ui_menu_operaciones())  # Index 2
        self.stack.addWidget(self.ui_ingresar_monto())  # Index 3
        self.stack.addWidget(self.ui_generica_operacion())  # Index 4
        self.stack.addWidget(self.ui_operacion_realizada())  # Index 5

        pantalla_layout.addWidget(self.stack)
        sistema.addWidget(pantalla, 4)

        titulo_historial = QLabel("↻  HISTORIAL DE TRANSICIONES (AFD)")
        titulo_historial.setStyleSheet("color:white; font-size:10pt; font-weight:bold; border:none;")
        sistema.addWidget(titulo_historial)

        self.tabla_historial = QTableWidget(0, 5)
        self.tabla_historial.setHorizontalHeaderLabels(
            ["Hora", "Estado ant.", "Evento", "Estado sig.", "Mensaje"]
        )

        header = self.tabla_historial.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.tabla_historial.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.PANEL_2};
                color: #E5E7EB;
                border: 1px solid #253044;
                border-radius: 8px;
                gridline-color: #253044;
                font-size: 9pt;
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QHeaderView::section {{
                background-color: #0F172A;
                color: white;
                font-weight: bold;
                border:none;
                padding:6px;
            }}
        """)
        self.tabla_historial.setFixedHeight(135)
        self.tabla_historial.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_historial.verticalHeader().setVisible(False)

        sistema.addWidget(self.tabla_historial)

        btn_reiniciar = QPushButton("↻   LIMPIAR AFD")
        btn_reiniciar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reiniciar.setStyleSheet(f"""
            QPushButton {{
                background-color: #111827;
                color:white;
                border:1px solid #273244;
                border-radius:8px;
                padding:11px;
                font-size:11pt;
                font-weight:bold;
            }}
            QPushButton:hover {{
                background-color:#1F2937;
            }}
        """)
        btn_reiniciar.clicked.connect(self.reiniciar_sistema)
        sistema.addWidget(btn_reiniciar)

        principal.addWidget(panel_sistema, 3)

        # =====================================================
        # PANEL DERECHO - ESTADOS DEL AFD + BOTÓN DE PESTAÑA
        # =====================================================
        panel_afd = QFrame()
        panel_afd.setStyleSheet(f"""
            QFrame {{
                background-color: {self.PANEL};
                border:1px solid {self.BORDE};
                border-radius:16px;
            }}
        """)

        afd = QVBoxLayout(panel_afd)
        afd.setContentsMargins(18, 18, 18, 18)
        afd.setSpacing(10)

        header_layout = QHBoxLayout()
        titulo_afd = QLabel("AFD EN TIEMPO REAL")
        titulo_afd.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        titulo_afd.setStyleSheet("color:white; border:none;")
        header_layout.addWidget(titulo_afd)

        header_layout.addStretch()

        self.btn_toggle_diagrama = QPushButton("◀ Ver Diagrama")
        self.btn_toggle_diagrama.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_diagrama.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.PANEL_2};
                color: {self.VERDE};
                border: 1px solid {self.VERDE};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 8pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0C211C;
            }}
        """)
        self.btn_toggle_diagrama.clicked.connect(self.alternar_diagrama_flotante)
        header_layout.addWidget(self.btn_toggle_diagrama)

        afd.addLayout(header_layout)

        linea = QFrame()
        linea.setFixedSize(70, 3)
        linea.setStyleSheet(f"background-color:{self.ROJO}; border:none; border-radius:2px;")

        linea_container = QHBoxLayout()
        linea_container.setContentsMargins(0, 0, 0, 5)
        linea_container.addStretch()
        linea_container.addWidget(linea)
        linea_container.addStretch()
        afd.addLayout(linea_container)

        estado_titulo = QLabel("ESTADOS DEFINIDOS (Q)")
        estado_titulo.setStyleSheet(f"color:{self.ROJO}; font-size:10pt; font-weight:bold; border:none;")
        afd.addWidget(estado_titulo)

        self.labels_estados = {}

        estados_desc = [
            ("Q0", "Cajero en espera"),
            ("Q1", "Tarjeta insertada"),
            ("Q2", "Esperando PIN"),
            ("Q3", "Usuario autenticado"),
            ("Q4", "Operación seleccionada"),
            ("Q5", "Operación realizada"),
            ("Q6", "Expulsar / Finalizar"),
        ]

        for codigo, desc in estados_desc:
            fila = QLabel(f"   ○   {codigo}: {desc}")
            fila.setMinimumHeight(30)
            fila.setStyleSheet(
                f"color:{self.TEXTO_SEC}; font-size:9pt; font-weight:bold; padding:3px; border:none; border-radius:6px;")
            self.labels_estados[codigo] = fila
            afd.addWidget(fila)

        afd.addStretch()

        detalle = QFrame()
        detalle.setStyleSheet(f"""
            QFrame {{
                background-color:{self.FONDO};
                border:1px solid {self.BORDE};
                border-radius:10px;
            }}
        """)

        detalle_layout = QVBoxLayout(detalle)
        detalle_layout.setContentsMargins(14, 14, 14, 14)

        detalle_titulo = QLabel("ESTADO ACTUAL DEL AUTÓMATA")
        detalle_titulo.setStyleSheet(f"color:{self.ROJO}; font-size:10pt; font-weight:bold; border:none;")
        detalle_layout.addWidget(detalle_titulo)

        self.lbl_detalle = QLabel()
        self.lbl_detalle.setWordWrap(True)
        self.lbl_detalle.setStyleSheet(f"color:{self.TEXTO}; font-size:10pt; border:none;")
        detalle_layout.addWidget(self.lbl_detalle)

        afd.addWidget(detalle)

        footer = QLabel("●  Sistema AFD - BAC Credomatic")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color:{self.TEXTO_SEC}; font-size:9pt; border:none; padding:5px;")
        afd.addWidget(footer)

        principal.addWidget(panel_afd, 2)

        # =====================================================
        # CONTENEDOR FLOTANTE (DRAWER) CON MATPLOTLIB
        # =====================================================
        self.panel_flotante = QFrame(self)
        self.panel_flotante.setStyleSheet(f"""
            QFrame {{
                background-color: {self.PANEL_2};
                border: 2px solid {self.VERDE};
                border-radius: 12px;
            }}
        """)
        self.panel_flotante.setGeometry(1250, 50, 420, 700)

        layout_flotante = QVBoxLayout(self.panel_flotante)
        layout_flotante.setContentsMargins(10, 10, 10, 10)

        lbl_tit_flot = QLabel("DIAGRAMA AFD EN TIEMPO REAL")
        lbl_tit_flot.setStyleSheet(f"color: {self.VERDE}; font-weight: bold; font-size: 10pt; border: none;")
        layout_flotante.addWidget(lbl_tit_flot)

        self.generador_diagrama = DiagramaAFD()
        figura_inicial = self.generador_diagrama.construir_figura(estados_actuales={"Q0"})
        self.canvas_matplotlib = FigureCanvasQTAgg(figura_inicial)
        layout_flotante.addWidget(self.canvas_matplotlib)

        btn_cerrar_flotante = QPushButton("✕ Ocultar Diagrama")
        btn_cerrar_flotante.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar_flotante.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.ROJO};
                color: white;
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {self.ROJO_OSCURO};
            }}
        """)
        btn_cerrar_flotante.clicked.connect(self.alternar_diagrama_flotante)
        layout_flotante.addWidget(btn_cerrar_flotante)

        self.panel_flotante_visible = False

    # =========================================================
    # ANIMACIÓN DEL CAJÓN DESLIZANTE LATERAL
    # =========================================================
    def alternar_diagrama_flotante(self):
        self.animacion = QPropertyAnimation(self.panel_flotante, b"geometry")
        self.animacion.setDuration(250)

        if self.panel_flotante_visible:
            self.animacion.setStartValue(QRect(810, 50, 420, 700))
            self.animacion.setEndValue(QRect(1250, 50, 420, 700))
            self.btn_toggle_diagrama.setText("◀ Ver Diagrama")
            self.panel_flotante_visible = False
        else:
            self.animacion.setStartValue(QRect(1250, 50, 420, 700))
            self.animacion.setEndValue(QRect(810, 50, 420, 700))
            self.btn_toggle_diagrama.setText("▶ Ocultar")
            self.panel_flotante_visible = True

        self.animacion.start()

    # =========================================================
    # PANTALLAS DEL CAJERO (MÉTODOS UI)
    # =========================================================
    def ui_esperando_tarjeta(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        icono = QLabel()
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icono.setStyleSheet("border: none;")

        pixmap_tarjeta = QPixmap("tarjeta_cajero.png")
        if not pixmap_tarjeta.isNull():
            icono.setPixmap(pixmap_tarjeta.scaledToWidth(140, Qt.TransformationMode.SmoothTransformation))
        else:
            icono.setText("▣")
            icono.setStyleSheet(f"color:{self.ROJO}; font-size:52pt; border:none;")

        layout.addWidget(icono)

        titulo = QLabel("<span style='color:#C8102E;'>BAC</span> Credomatic")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("font-size:20pt; font-weight:bold; color:#1F2937; border:none;")
        layout.addWidget(titulo)

        descripcion = QLabel("Por favor, inserte su tarjeta para comenzar.")
        descripcion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        descripcion.setStyleSheet("color:#4B5563; font-size:11pt; border:none;")
        layout.addWidget(descripcion)

        boton = QPushButton("▣   INSERTAR TARJETA")
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setStyleSheet(f"""
            QPushButton {{
                background-color:{self.ROJO};
                color:white;
                border-radius:8px;
                padding:12px 26px;
                font-size:11pt;
                font-weight:bold;
            }}
            QPushButton:hover {{
                background-color:{self.ROJO_OSCURO};
            }}
        """)
        boton.clicked.connect(lambda: self.ejecutar_evento("insertar_tarjeta"))
        layout.addWidget(boton, alignment=Qt.AlignmentFlag.AlignCenter)

        return w

    def ui_solicitar_pin(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.lbl_titulo_pin = QLabel("INGRESE SU PIN")
        self.lbl_titulo_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_titulo_pin.setStyleSheet("color:#1F2937; font-size:15pt; font-weight:bold; border:none;")
        layout.addWidget(self.lbl_titulo_pin)

        info = QLabel("PIN de 4 dígitos")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color:#6B7280; font-size:10pt; border:none;")
        layout.addWidget(info)

        self.input_pin = QLabel("—  —  —  —")
        self.input_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_pin.setStyleSheet(f"""
            color:{self.ROJO};
            background:#F8FAFC;
            border:2px solid #D1D5DB;
            border-radius:8px;
            padding:8px;
            font-size:18pt;
            font-weight:bold;
        """)
        layout.addWidget(self.input_pin)

        grid = QGridLayout()
        grid.setSpacing(6)

        numeros = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("C", 3, 0), ("0", 3, 1), ("⌫", 3, 2)
        ]

        for texto_btn, fila, columna in numeros:
            boton = QPushButton(texto_btn)
            boton.setFixedSize(52, 42)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.setStyleSheet("""
                QPushButton {
                    background:#F3F4F6;
                    color:#1F2937;
                    border:1px solid #D1D5DB;
                    border-radius:6px;
                    font-size:11pt;
                    font-weight:bold;
                }
                QPushButton:hover {
                    background:#E5E7EB;
                }
            """)
            boton.clicked.connect(lambda checked=False, t=texto_btn: self.manejar_teclado_pin(t))
            grid.addWidget(boton, fila, columna)

        layout.addLayout(grid)

        self.btn_ingresar_pin = QPushButton("INGRESAR PIN")
        self.btn_ingresar_pin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ingresar_pin.setStyleSheet(f"""
            QPushButton {{
                background:{self.ROJO};
                color:white;
                border-radius:7px;
                padding:10px 20px;
                font-weight:bold;
                font-size:11pt;
            }}
            QPushButton:hover {{
                background:{self.ROJO_OSCURO};
            }}
        """)
        self.btn_ingresar_pin.clicked.connect(self.validar_y_enviar_pin)
        layout.addWidget(self.btn_ingresar_pin, alignment=Qt.AlignmentFlag.AlignCenter)

        return w

    def ui_menu_operaciones(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 15, 12, 10)
        layout.setSpacing(8)

        titulo = QLabel("Seleccione la Operación Deseada")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("color:#1F2937; font-size:13pt; font-weight:bold; border:none;")
        layout.addWidget(titulo)

        grid = QGridLayout()
        grid.setSpacing(6)

        ops = [
            ("1. Consulta de Saldo", "consultar_saldo"),
            ("2. Retiro de Efectivo", "retiro_efectivo"),
            ("3. Transferencia", "transferencia"),
            ("4. Pago de Tarjeta", "pago_servicios"),
            ("5. Cambio de PIN", "cambio_pin"),
            ("6. Depósito", "deposito"),
        ]

        for i, (texto, evento) in enumerate(ops):
            boton = QPushButton(texto)
            boton.setMinimumHeight(45)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.setStyleSheet(f"""
                QPushButton {{
                    background:{self.ROJO};
                    color:white;
                    border-radius:6px;
                    padding:6px 10px;
                    text-align:left;
                    font-size:9.5pt;
                    font-weight:bold;
                }}
                QPushButton:hover {{
                    background:{self.ROJO_OSCURO};
                }}
            """)
            boton.clicked.connect(lambda checked=False, ev=evento: self.manejar_seleccion_operacion(ev))
            grid.addWidget(boton, i // 2, i % 2)

        layout.addLayout(grid)
        return w

    def ui_ingresar_monto(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self.lbl_titulo_monto = QLabel("INGRESE EL MONTO")
        self.lbl_titulo_monto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_titulo_monto.setStyleSheet("color:#1F2937; font-size:15pt; font-weight:bold; border:none;")
        layout.addWidget(self.lbl_titulo_monto)

        self.input_monto_lbl = QLabel("Q  0.00")
        self.input_monto_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_monto_lbl.setStyleSheet(f"""
            color:{self.ROJO};
            background:#F8FAFC;
            border:2px solid #D1D5DB;
            border-radius:8px;
            padding:8px;
            font-size:18pt;
            font-weight:bold;
        """)
        layout.addWidget(self.input_monto_lbl)

        grid = QGridLayout()
        grid.setSpacing(6)

        numeros = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("C", 3, 0), ("0", 3, 1), ("⌫", 3, 2)
        ]

        for texto_btn, fila, columna in numeros:
            boton = QPushButton(texto_btn)
            boton.setFixedSize(52, 42)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.setStyleSheet("""
                QPushButton {
                    background:#F3F4F6;
                    color:#1F2937;
                    border:1px solid #D1D5DB;
                    border-radius:6px;
                    font-size:11pt;
                    font-weight:bold;
                }
                QPushButton:hover {
                    background:#E5E7EB;
                }
            """)
            boton.clicked.connect(lambda checked=False, t=texto_btn: self.manejar_teclado_monto(t))
            grid.addWidget(boton, fila, columna)

        layout.addLayout(grid)

        btn_container = QHBoxLayout()

        btn_volver = QPushButton("Volver")
        btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_volver.setStyleSheet(
            "QPushButton { background:#6B7280; color:white; border-radius:6px; padding:8px 15px; font-weight:bold; }")
        btn_volver.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_container.addWidget(btn_volver)

        self.btn_confirmar_monto = QPushButton("CONFIRMAR")
        self.btn_confirmar_monto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirmar_monto.setStyleSheet(f"""
            QPushButton {{
                background:{self.ROJO};
                color:white;
                border-radius:6px;
                padding:8px 20px;
                font-weight:bold;
            }}
            QPushButton:hover {{
                background:{self.ROJO_OSCURO};
            }}
        """)
        self.btn_confirmar_monto.clicked.connect(self.procesar_monto_ingresado)
        btn_container.addWidget(self.btn_confirmar_monto)

        layout.addLayout(btn_container)
        return w

    def ui_generica_operacion(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        icono = QLabel("✓")
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icono.setStyleSheet("color:#059669; font-size:42pt; font-weight:bold; border:none;")
        layout.addWidget(icono)

        self.lbl_detalle_op = QLabel("Detalle")
        self.lbl_detalle_op.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detalle_op.setWordWrap(True)
        self.lbl_detalle_op.setStyleSheet("color:#1F2937; font-size:12pt; font-weight:bold; border:none;")
        layout.addWidget(self.lbl_detalle_op)

        btn_salir = QPushButton("Expulsar Tarjeta")
        btn_salir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_salir.setStyleSheet(
            "QPushButton { background:#1F2937; color:white; border-radius:7px; padding:11px 25px; font-weight:bold; } QPushButton:hover { background:#111827; }")
        btn_salir.clicked.connect(lambda: self.ejecutar_evento("expulsar_tarjeta"))

        layout.addWidget(btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)

        return w

    def ui_operacion_realizada(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        icono = QLabel("●")
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icono.setStyleSheet("color:#C8102E; font-size:48pt; font-weight:bold; border:none;")
        layout.addWidget(icono)

        self.lbl_resultado_texto = QLabel("Operación finalizada.\nPor favor retire su tarjeta.")
        self.lbl_resultado_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado_texto.setStyleSheet("color:#1F2937; font-size:13pt; font-weight:bold; border:none;")
        layout.addWidget(self.lbl_resultado_texto)

        btn_reiniciar_sesion = QPushButton("Retirar Tarjeta y Reiniciar")
        btn_reiniciar_sesion.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reiniciar_sesion.setStyleSheet(
            "QPushButton { background:#1F2937; color:white; border-radius:7px; padding:11px 25px; font-weight:bold; } QPushButton:hover { background:#111827; }")
        btn_reiniciar_sesion.clicked.connect(self.reiniciar_sistema)
        layout.addWidget(btn_reiniciar_sesion, alignment=Qt.AlignmentFlag.AlignCenter)

        return w

    # =========================================================
    # LÓGICA DE EVENTOS Y ACTUALIZACIÓN
    # =========================================================
    def manejar_teclado_pin(self, caracter):
        if self.modo_cambio_pin:
            if caracter == "C":
                self.pin_nuevo_temporal = ""
            elif caracter == "⌫":
                if len(self.pin_nuevo_temporal) > 0:
                    self.pin_nuevo_temporal = self.pin_nuevo_temporal[:-1]
            else:
                if len(self.pin_nuevo_temporal) < 4:
                    self.pin_nuevo_temporal += caracter

            self.input_pin.setText(
                "  ".join(
                    "●" if i < len(self.pin_nuevo_temporal) else "—"
                    for i in range(4)
                )
            )
        else:
            if caracter == "C":
                self.pin_ingresado = ""
            elif caracter == "⌫":
                if len(self.pin_ingresado) > 0:
                    self.pin_ingresado = self.pin_ingresado[:-1]
            else:
                if len(self.pin_ingresado) < 4:
                    self.pin_ingresado += caracter

            self.input_pin.setText(
                "  ".join(
                    "●" if i < len(self.pin_ingresado) else "—"
                    for i in range(4)
                )
            )

    def validar_y_enviar_pin(self):
        if self.modo_cambio_pin:
            if len(self.pin_nuevo_temporal) < 4:
                QMessageBox.warning(self, "PIN Incompleto", "Debe ingresar un nuevo PIN de exactamente 4 dígitos.")
                return

            res1 = self.cajero.procesar_evento("cambio_pin", nuevo_pin_usuario=self.pin_nuevo_temporal)
            self.agregar_fila_historial(res1)
            self.actualizar_visualizacion_afd()

            self.modo_cambio_pin = False
            self.pin_nuevo_temporal = ""

            if res1["valido"]:
                QTimer.singleShot(350, lambda: self.completar_operacion_en_q5("cambio_pin", "PIN cambiado con éxito"))
            return

        if len(self.pin_ingresado) < 4:
            QMessageBox.warning(self, "PIN Incompleto", "Debe ingresar un PIN de 4 dígitos.")
            return

        resultado = self.cajero.procesar_evento("ingresar_pin", self.pin_ingresado)
        self.agregar_fila_historial(resultado)
        self.actualizar_visualizacion_afd()

        if not resultado["valido"]:
            QMessageBox.critical(self, "Autenticación Fallida", resultado["mensaje"])
            self.pin_ingresado = ""
            self.input_pin.setText("—  —  —  —")
            self.stack.setCurrentIndex(0)
            return

        self.stack.setCurrentIndex(2)

    def manejar_seleccion_operacion(self, evento):
        self.operacion_actual = evento
        self.monto_ingresado = ""

        if evento == "retiro_efectivo":
            self.lbl_titulo_monto.setText("MONTO A RETIRAR")
            self.input_monto_lbl.setText("Q  0.00")
            self.stack.setCurrentIndex(3)
        elif evento == "deposito":
            self.lbl_titulo_monto.setText("MONTO A DEPOSITAR")
            self.input_monto_lbl.setText("Q  0.00")
            self.stack.setCurrentIndex(3)
        elif evento == "cambio_pin":
            self.modo_cambio_pin = True
            self.pin_nuevo_temporal = ""
            self.lbl_titulo_pin.setText("INGRESE SU NUEVO PIN")
            self.input_pin.setText("—  —  —  —")
            self.stack.setCurrentIndex(1)
        else:
            detalles = {
                "consultar_saldo": f"Consulta de saldo exitosa: Q {self.cajero.saldo:,.2f}",
                "transferencia": "Transferencia realizada con éxito",
                "pago_servicios": "Pago de servicios procesado con éxito",
            }
            self.procesar_flujo_operacion(evento, detalles.get(evento, "Operación exitosa"))

    def manejar_teclado_monto(self, caracter):
        if caracter == "C":
            self.monto_ingresado = ""
        elif caracter == "⌫":
            if len(self.monto_ingresado) > 0:
                self.monto_ingresado = self.monto_ingresado[:-1]
        else:
            if len(self.monto_ingresado) < 7:
                self.monto_ingresado += caracter

        if self.monto_ingresado == "":
            self.input_monto_lbl.setText("Q  0.00")
        else:
            self.input_monto_lbl.setText(f"Q  {int(self.monto_ingresado):,}.00")

    def procesar_monto_ingresado(self):
        if self.monto_ingresado == "" or int(self.monto_ingresado) <= 0:
            QMessageBox.warning(self, "Monto Inválido", "Ingrese un monto mayor a 0.")
            return

        monto_val = float(self.monto_ingresado)
        res1 = self.cajero.procesar_evento(self.operacion_actual, monto_operacion=monto_val)
        self.agregar_fila_historial(res1)
        self.actualizar_visualizacion_afd()

        if not res1["valido"]:
            QMessageBox.warning(self, "Operación Denegada", res1["mensaje"])
            return

        QTimer.singleShot(350, lambda: self.completar_operacion_en_q5(self.operacion_actual, res1["mensaje"]))

    def procesar_flujo_operacion(self, evento_operacion, detalle):
        res1 = self.cajero.procesar_evento(evento_operacion)
        self.agregar_fila_historial(res1)
        self.actualizar_visualizacion_afd()

        if not res1["valido"]:
            return

        QTimer.singleShot(350, lambda: self.completar_operacion_en_q5(evento_operacion, detalle))

    def completar_operacion_en_q5(self, evento_operacion, detalle):
        res2 = self.cajero.procesar_evento(evento_operacion)
        self.agregar_fila_historial(res2)
        self.actualizar_visualizacion_afd()

        if not res2["valido"]:
            return

        self.lbl_detalle_op.setText(detalle)
        self.stack.setCurrentIndex(4)

    def ejecutar_evento(self, evento):
        resultado = self.cajero.procesar_evento(evento)
        self.agregar_fila_historial(resultado)
        self.actualizar_visualizacion_afd()

        if not resultado["valido"]:
            QMessageBox.critical(self, "Transición No Válida", resultado["mensaje"])
            return

        estados_str = list(self.cajero.estados_actuales)

        if "Q1" in estados_str:
            QTimer.singleShot(300, lambda: self.forzar_transicion_automatica("tarjeta_valida"))
        elif "Q2" in estados_str:
            self.pin_ingresado = ""
            self.lbl_titulo_pin.setText("INGRESE SU PIN")
            self.input_pin.setText("—  —  —  —")
            self.stack.setCurrentIndex(1)
        elif "Q3" in estados_str:
            self.stack.setCurrentIndex(2)
        elif "Q6" in estados_str or "Q8" in estados_str:
            self.stack.setCurrentIndex(5)

    def forzar_transicion_automatica(self, evento):
        resultado = self.cajero.procesar_evento(evento)
        self.agregar_fila_historial(resultado)
        self.actualizar_visualizacion_afd()
        estados_str = list(self.cajero.estados_actuales)
        if "Q2" in estados_str:
            self.pin_ingresado = ""
            self.lbl_titulo_pin.setText("INGRESE SU PIN")
            self.input_pin.setText("—  —  —  —")
            self.stack.setCurrentIndex(1)

    def agregar_fila_historial(self, res):
        fila = self.tabla_historial.rowCount()
        self.tabla_historial.insertRow(fila)

        hora = datetime.now().strftime("%H:%M:%S")
        origen_str = ",".join(sorted(res["estados_origen"]))
        destino_str = ",".join(sorted(res["estados_destino"])) if res["valido"] else "∅"

        datos = [hora, origen_str, res["evento"], destino_str, res["mensaje"]]

        for columna, valor in enumerate(datos):
            item = QTableWidgetItem(valor)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if columna in (1, 3):
                item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.tabla_historial.setItem(fila, columna, item)

        self.tabla_historial.scrollToBottom()

    def actualizar_visualizacion_afd(self):
        actuales = self.cajero.estados_actuales

        for codigo, label in self.labels_estados.items():
            if codigo in actuales:
                label.setStyleSheet(f"""
                    color:{self.VERDE};
                    background-color:#0C211C;
                    border-left:4px solid {self.VERDE};
                    border-radius:6px;
                    padding:4px;
                    font-size:9pt;
                    font-weight:bold;
                """)
                label.setText(f"   ●   {codigo}: Activo")
            else:
                label.setStyleSheet("""
                    color:#9CA3AF;
                    background:transparent;
                    border:none;
                    padding:4px;
                    font-size:9pt;
                    font-weight:bold;
                """)
                label.setText(f"   ○   {codigo}")

        ultima_trans = None
        if self.tabla_historial.rowCount() > 0:
            row = self.tabla_historial.rowCount() - 1
            origen_txt = self.tabla_historial.item(row, 1).text()
            evento_txt = self.tabla_historial.item(row, 2).text()
            destino_txt = self.tabla_historial.item(row, 3).text()

            ultima_trans = {
                "origen": set(origen_txt.split(",")),
                "evento": evento_txt,
                "destino": set(destino_txt.split(","))
            }

        layout_flotante = self.panel_flotante.layout()
        layout_flotante.removeWidget(self.canvas_matplotlib)
        self.canvas_matplotlib.deleteLater()

        nueva_figura = self.generador_diagrama.construir_figura(
            estados_actuales=actuales,
            ultima_transicion=ultima_trans
        )
        self.canvas_matplotlib = FigureCanvasQTAgg(nueva_figura)
        layout_flotante.insertWidget(1, self.canvas_matplotlib)

        self.lbl_detalle.setText(
            f"<b>Estados Actuales:</b> "
            f"<span style='color:{self.VERDE}; font-size:11pt;'>"
            f"{sorted(list(actuales))}</span><br>"
            f"<b>¿Es Estado Final (F):</b> "
            f"{'Sí' if 'FIN' in actuales or 'Q8' in actuales else 'No'}"
        )

    def reiniciar_sistema(self):
        self.cajero.reset()
        self.pin_ingresado = ""
        self.monto_ingresado = ""
        self.operacion_actual = None
        self.modo_cambio_pin = False
        self.pin_nuevo_temporal = ""
        self.tabla_historial.setRowCount(0)
        self.stack.setCurrentIndex(0)
        if self.panel_flotante_visible:
            self.alternar_diagrama_flotante()
        self.actualizar_visualizacion_afd()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ventana = CajeroGUIBAC()
    ventana.show()
    sys.exit(app.exec())