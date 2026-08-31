#Principal 

#Funciones del AFND

def es_estado_valido(estado):
    return estado in Q


def es_evento_valido(evento):
    return evento in Sigma


def es_transicion_valida(estado_actual, evento):
    return (estado_actual, evento) in delta and len(delta[(estado_actual, evento)]) > 0


def estados_destino(estado_actual, evento):
    return delta.get((estado_actual, evento), set())


def tiene_transicion_epsilon(estado):
    return estado in delta_epsilon and len(delta_epsilon[estado]) > 0


def cierre_epsilon(estados):
    cierre = set(estados)
    pendientes = list(estados)

    while pendientes:
        actual = pendientes.pop()
        for destino in delta_epsilon.get(actual, set()):
            if destino not in cierre:
                cierre.add(destino)
                pendientes.append(destino)

    return cierre


def es_estado_final(estado):
    return estado in F


def interseca_estado_final(conjunto_estados):
    return len(set(conjunto_estados) & F) > 0


def es_estado_inicial(estado):
    return estado == q0


def validar_transicion(conjunto_estados_actual, evento):
    if not es_evento_valido(evento):
        return False, f"Evento '{evento}' no pertenece al alfabeto del autómata.", set()

    for estado in conjunto_estados_actual:
        if not es_estado_valido(estado):
            return False, f"Estado '{estado}' no pertenece al autómata.", set()

    destinos = set()
    for estado in conjunto_estados_actual:
        destinos |= estados_destino(estado, evento)

    if not destinos:
        return False, (f"Transición no válida: desde {sorted(conjunto_estados_actual)} "
                        f"no se puede ejecutar '{evento}'."), set()

    destinos_con_epsilon = cierre_epsilon(destinos)

    return True, (f"Transición válida: {sorted(conjunto_estados_actual)} + {evento} "
                   f"-> {sorted(destinos_con_epsilon)}"), destinos_con_epsilon


if __name__ == "__main__":
    pruebas = [
        ({"Esperando_tarjeta"}, "insertar_tarjeta"),         
        ({"Solicitando_PIN"}, "ingresar_pin"),                
        ({"Esperando_tarjeta"}, "realizar_operacion"),        
        ({"Operacion_seleccionada"}, "cancelar"),             
        ({"Estado_inexistente"}, "ingresar_pin"),             
        ({"Tarjeta_insertada"}, "evento_falso"),              
    ]

    for estados, evento in pruebas:
        valida, mensaje, destinos = validar_transicion(estados, evento)
        print(f"[{'OK' if valida else 'X'}] {mensaje}")

    print("\n¿'Tarjeta_expulsada' es estado final?:", es_estado_final("Tarjeta_expulsada"))
    print("¿{'PIN_incorrecto','Tarjeta_expulsada'} interseca F?:",
          interseca_estado_final({"PIN_incorrecto", "Tarjeta_expulsada"}))
    print("¿'Esperando_tarjeta' es estado inicial?:", es_estado_inicial("Esperando_tarjeta"))