# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Búsqueda de una voz que de verdad produzca audio en un motor real.

La voz 0 puede ser un puente al lector (SAPI2SR) que no produce audio: se
prueba cada voz y se sigue con la primera que de verdad se pone a hablar. Un
motor sin lista de voces usa la que trae.
"""

import time

FRASE = ("Prueba de voz con volumen cero, una frase larga para que el motor "
         "tenga tiempo de ponerse a hablar.")
PLAZO = 2.0


def elegir_voz_que_suena(motor):
    """Deja elegida la primera voz con la que el motor se pone a hablar.

    Falla con las voces probadas si ninguna llega a `hablando()`.
    """
    nombres = motor.voces() or ["la que trae"]
    probadas = []
    for idx, nombre in enumerate(nombres):
        if not motor.elegir_voz(idx):
            continue
        probadas.append(nombre)
        if motor.hablar(FRASE):
            limite = time.monotonic() + PLAZO
            while not motor.hablando() and time.monotonic() < limite:
                time.sleep(0.01)
            if motor.hablando():
                motor.parar()
                limite = time.monotonic() + 1.0
                while motor.hablando() and time.monotonic() < limite:
                    time.sleep(0.01)
                return
        motor.parar()
    raise AssertionError("Ninguna voz del motor llegó a hablar: "
                         + (", ".join(probadas) or "sin voces elegibles"))
