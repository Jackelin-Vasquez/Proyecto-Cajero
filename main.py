
def es_estado_valido(estado, Q):
    """Valida si un estado pertenece al conjunto de estados Q."""
    return estado in Q


def es_evento_valido(evento, alfabeto):
    """Valida si un evento pertenece al alfabeto."""
    return evento in alfabeto


def es_transicion_valida(estado_actual, evento, delta):
    """Valida si delta(estado_actual, evento) existe y no está vacía."""
    return (estado_actual, evento) in delta and len(delta[(estado_actual, evento)]) > 0


def estados_destino(estado_actual, evento, delta):
    """Devuelve el conjunto de estados posibles según delta. Vacío si no existe."""
    return delta.get((estado_actual, evento), set())


def es_estado_final(estado, F):
    """Valida si un estado pertenece al conjunto de estados finales F."""
    return estado in F


def es_estado_inicial(estado, q0):
    """Valida si un estado corresponde al estado inicial q0."""
    return estado == q0


def validar_transicion(conjunto_estados_actual, evento, Q, Sigma, delta):
    """
    Validación completa de una transición no determinista.
    Retorna (es_valida: bool, mensaje: str, destinos: set).
    """
    if not es_evento_valido(evento, Sigma):
        return False, f"Evento '{evento}' no pertenece al alfabeto del autómata.", set()

    for estado in conjunto_estados_actual:
        if not es_estado_valido(estado, Q):
            return False, f"Estado '{estado}' no pertenece al autómata.", set()

    destinos = set()
    for estado in conjunto_estados_actual:
        destinos |= estados_destino(estado, evento, delta)

    if not destinos:
        return False, (f"Transición no válida: desde {sorted(conjunto_estados_actual)} "
                        f"no se puede ejecutar '{evento}'."), set()

    return True, (f"Transición válida: {sorted(conjunto_estados_actual)} + {evento} "
                   f"-> {sorted(destinos)}"), destinos
