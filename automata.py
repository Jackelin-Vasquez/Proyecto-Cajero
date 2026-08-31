from main import validar_transicion, es_estado_final
"""
    ESTADOS POSIBLES:
    Q0: cajero en espera
    Q1: insertar tarjeta (tiene que estar en espera el cajero)
    Q2: esperar pin (se necesita insertar tarjeta antes)
    Q3: autenticar (se necesita esperar pin antes)
    Q4: menú de operaciones (se necesita autenticar antes)
    Q5: consultar saldo (se necesita acceso al menú)
    Q6: realizar un retiro (se necesita acceso al menú Y saldo suficiente)
    Q7: finalizar la operación (se necesita iniciar una operación)
    Q8: expulsar la tarjeta (puede pasar si: mal pin puesto, autenticación fallida, retiro excesivo u operación finalizada)
"""


Q = {"Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"}
Sigma = {"insertar_tarjeta","tarjeta_valida","tarjeta_invalida","ingresar_pin","pin_correcto","pin_incorrecto","operar","ver_saldo","saldo_suficiente","saldo_insuficiente","finalizar"}
q0 = "Q0"
F = {"Q8"}

# > delta: dict[(estado, evento)] -> set(estados_destino)
delta = {
    ("Q0", "insertar_tarjeta"): {"Q1"},
    ("Q1", "tarjeta_valida"): {"Q2"},
    ("Q1", "tarjeta_invalida"): {"Q8"},
    ("Q2", "ingresar_pin"): {"Q3"},
    ("Q3", "pin_correcto"): {"Q4"},
    ("Q3", "pin_incorrecto"): {"Q8"},
    ("Q4", "operar"): {"Q5", "Q6"},
    ("Q5", "ver_saldo"): {"Q7"},
    ("Q6", "saldo_suficiente"): {"Q7"},
    ("Q6", "saldo_insuficiente"): {"Q8"},
    ("Q7", "finalizar"): {"Q8"},
}


class Cajero:
    """Autómata finito no determinista que simula un cajero automático."""

    def __init__(self):
        self.Q = Q
        self.Sigma = Sigma
        self.delta = delta
        self.q0 = q0
        self.F = F
        self.reset()

    def reset(self):
        """Reinicia la simulación al estado inicial q0."""
        self.estados_actuales = {self.q0}
        self.historial = [{
            "paso": 0,
            "evento": None,
            "estados": set(self.estados_actuales),
            "mensaje": f"Cajero listo, en estado inicial {self.q0}.",
        }]
        return self.estados_actuales

    def eventos_disponibles(self):
        """Eventos que producen al menos una transición válida desde el estado actual."""
        return sorted({
            evento for (estado, evento) in self.delta
            if estado in self.estados_actuales
        })

    def procesar_evento(self, evento):
        """
        Procesa un evento desde el conjunto de estados actuales, usando
        validar_transicion() del documento 1.

        Retorna un dict con la misma información que da validar_transicion,
        pensado para alimentar directamente una interfaz:
            {
                "valido": bool,
                "mensaje": str,
                "evento": str,
                "estados_origen": set,
                "estados_destino": set,
            }
        """
        es_valida, mensaje, destinos = validar_transicion(
            self.estados_actuales, evento, self.Q, self.Sigma, self.delta
        )

        resultado = {
            "valido": es_valida,
            "mensaje": mensaje,
            "evento": evento,
            "estados_origen": set(self.estados_actuales),
            "estados_destino": destinos if es_valida else set(),
        }

        if es_valida:
            self.estados_actuales = destinos
            self.historial.append({
                "paso": len(self.historial),
                "evento": evento,
                "estados": set(self.estados_actuales),
                "mensaje": mensaje,
            })

        return resultado

    def en_estado_final(self):
        """True si alguno de los estados actuales es un estado final (Q8)."""
        return any(es_estado_final(e, self.F) for e in self.estados_actuales)

    def simular(self, secuencia_eventos):
        """
        Corre una secuencia completa de eventos desde el estado inicial y
        devuelve la lista de resultados paso a paso (uno por evento).
        Útil para "reproducir" un recorrido completo en el diagrama.
        """
        self.reset()
        resultados = []
        for evento in secuencia_eventos:
            resultado = self.procesar_evento(evento)
            resultados.append(resultado)
            if not resultado["valido"]:
                break
        return resultados