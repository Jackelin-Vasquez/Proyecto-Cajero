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

Q = {"Q0", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6"}
Sigma = {
    "insertar_tarjeta", "tarjeta_valida", "ingresar_pin",
    "consultar_saldo", "retiro_efectivo", "transferencia",
    "pago_servicios", "cambio_pin", "deposito", "expulsar_tarjeta"
}
q0 = "Q0"
F = {"Q6"}

# > delta: dict[(estado, evento)] -> set(estados_destino)
delta = {
    ("Q0", "insertar_tarjeta"): {"Q1"},
    ("Q1", "tarjeta_valida"): {"Q2"},
    ("Q2", "ingresar_pin"): {"Q3"},

    # Del menú Q3 pasamos a Q4 (Operación seleccionada)
    ("Q3", "consultar_saldo"): {"Q4"},
    ("Q3", "retiro_efectivo"): {"Q4"},
    ("Q3", "transferencia"): {"Q4"},
    ("Q3", "pago_servicios"): {"Q4"},
    ("Q3", "cambio_pin"): {"Q4"},
    ("Q3", "deposito"): {"Q4"},

    # De Q4 pasamos a Q5 (Operación realizada)
    ("Q4", "consultar_saldo"): {"Q5"},
    ("Q4", "retiro_efectivo"): {"Q5"},
    ("Q4", "transferencia"): {"Q5"},
    ("Q4", "pago_servicios"): {"Q5"},
    ("Q4", "cambio_pin"): {"Q5"},
    ("Q4", "deposito"): {"Q5"},

    # Expulsar tarjeta obligatorio de Q5 a Q6
    ("Q5", "expulsar_tarjeta"): {"Q6"},
}


class Cajero:
    """Autómata finito no determinista que simula un cajero automático."""

    def __init__(self):
        self.Q = Q
        self.Sigma = Sigma
        self.delta = delta
        self.q0 = q0
        self.F = F
        self.PIN_CORRECTO = "1234"  # PIN predeterminado
        self.saldo = 1500.00  # Saldo inicial fijo
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

    def procesar_evento(self, evento, pin_ingresado_usuario=None, monto_operacion=0.0, nuevo_pin_usuario=None):
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
        # 1. Validación de PIN en el estado Q2 (si falla, regresa al inicio Q0)
        if "Q2" in self.estados_actuales and evento == "ingresar_pin":
            if pin_ingresado_usuario != self.PIN_CORRECTO:
                estados_origen = set(self.estados_actuales)
                self.estados_actuales = {self.q0}
                mensaje_error = "PIN incorrecto. Regresando al inicio (Q0)."

                self.historial.append({
                    "paso": len(self.historial),
                    "evento": evento,
                    "estados": set(self.estados_actuales),
                    "mensaje": mensaje_error,
                })

                return {
                    "valido": False,
                    "mensaje": mensaje_error,
                    "evento": evento,
                    "estados_origen": estados_origen,
                    "estados_destino": set(self.estados_actuales),
                }

        # 2. Validación de fondos suficientes para Retiro
        if evento == "retiro_efectivo" and monto_operacion > 0:
            if monto_operacion > self.saldo:
                return {
                    "valido": False,
                    "mensaje": f"Fondos insuficientes. Saldo actual: Q {self.saldo:,.2f}",
                    "evento": evento,
                    "estados_origen": set(self.estados_actuales),
                    "estados_destino": set(),
                }

        # 3. Actualización de PIN si se ejecuta la acción de cambio
        if evento == "cambio_pin" and nuevo_pin_usuario:
            self.PIN_CORRECTO = nuevo_pin_usuario

        # Validación normal mediante el diccionario delta y la función externa
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
            if evento == "retiro_efectivo" and monto_operacion > 0:
                self.saldo -= monto_operacion
                resultado["mensaje"] = f"Retiro exitoso. Nuevo saldo: Q {self.saldo:,.2f}"
            elif evento == "deposito" and monto_operacion > 0:
                self.saldo += monto_operacion
                resultado["mensaje"] = f"Depósito exitoso. Nuevo saldo: Q {self.saldo:,.2f}"
            elif evento == "consultar_saldo":
                resultado["mensaje"] = f"Consulta de saldo: Q {self.saldo:,.2f}"
            elif evento == "cambio_pin":
                resultado["mensaje"] = "Cambio de PIN ejecutado con éxito."

            self.estados_actuales = destinos
            self.historial.append({
                "paso": len(self.historial),
                "evento": evento,
                "estados": set(self.estados_actuales),
                "mensaje": f"Cajero listo, en estado inicial {self.q0}.",
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