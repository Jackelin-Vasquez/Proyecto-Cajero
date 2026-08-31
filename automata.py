from main import validar_transicion
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
class estado:
    def __init__(self):
        self.transiciones = [] # transiciones: (no. estado final, requisito)
class Automata:
    def __init__(self):
        self.states = []

    def add_state(self, state):
        self.states.append(state)
