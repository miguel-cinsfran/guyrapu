# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo llegan las pruebas reales del destino al diálogo del directo.

La app puede preguntar algo en el medio, como cuando la cortina de NVDA
deja en negro una captura de la escena. Este módulo contesta esa pregunta sin
tocar la escena y sigue esperando el diálogo del directo en el mismo plazo.
"""

from __future__ import annotations

import time

from banco_app import _textos_de, dialogo_nativo, pulsar_boton_nativo


def _hijo(principal, titulo_parcial):
    """Busca el modal entre los descendientes de la ventana principal."""
    try:
        hijos = principal.descendants(control_type="Window")
    except Exception:
        return None
    for hijo in hijos:
        try:
            texto = hijo.window_text() or ""
        except Exception:
            continue
        if titulo_parcial in texto:
            return hijo
    return None


def _dialogo_hijo(principal, titulo_parcial: str, segundos: int = 20):
    """Los modales cuelgan de la ventana principal, no salen sueltos."""
    fin = time.time() + segundos
    while time.time() < fin:
        hijo = _hijo(principal, titulo_parcial)
        if hijo is not None:
            return hijo
        time.sleep(0.5)
    from directo_real import _ventana
    return _ventana(titulo_parcial, 5)


def esperar_directo(principal, titulo, segundos, anotar,
                    pregunta="Antes de transmitir", dejar="Dejar como está"):
    """Entrega el diálogo del directo o lanza `RuntimeError` con el motivo."""
    fin = time.time() + segundos
    while time.time() < fin:
        hijo = _hijo(principal, titulo)
        if hijo is not None:
            return hijo
        cuadro = dialogo_nativo(pregunta, segundos=0.5)
        if cuadro is not None:
            texto = " ".join(_textos_de(cuadro))
            if not pulsar_boton_nativo(cuadro, dejar):
                motivo = (f"no se pudo pulsar «{dejar}» en "
                          f"«{pregunta}»: {texto}")
                anotar("pregunta antes de transmitir", False, motivo)
                raise RuntimeError(motivo)
            anotar("pregunta antes de transmitir", True, texto)
        time.sleep(0.5)
    raise RuntimeError(f"no apareció el diálogo «{titulo}»")
