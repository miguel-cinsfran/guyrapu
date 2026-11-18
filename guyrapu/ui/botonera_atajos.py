# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atajos globales de los disparadores: Ctrl+Alt+Mayús más un número.

Se registran al arrancar, con la ventana principal abierta, y valen en
cualquier programa. Si otro programa ya usa uno, se dice una vez con su
nombre. El número se elige en cada disparador.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.music import anuncios
from guyrapu.ui import atajos_globales, disparadores_en_vivo
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.voice import sound_player as _snd

logger = diagnostico.obtener_logger(__name__)

# Acciones de la botonera, en orden: el índice da el id y el número.
ORDEN = tuple(f"disparador_{numero}" for numero in range(1, 10))

# Base de los ids propios para `RegisterHotKey`, lejos de las otras áreas.
BASE_IDS = 0xB500


def combinacion_ctrl_alt_mayus_numero(
        texto: str | None) -> tuple[int, int] | None:
    """Traduce Ctrl+Alt+Mayús más un número a lo que pide `RegisterHotKey`.

    Devuelve `(wx.MOD_CONTROL | wx.MOD_ALT | wx.MOD_SHIFT, ord(dígito))`.
    Los tres modificadores valen en cualquier orden. Cualquier otra cosa da
    None.
    """
    partes = (texto or "").strip().lower().replace(" ", "").split("+")
    if len(partes) != 4:
        return None
    if set(partes[:3]) != {"ctrl", "alt", "shift"}:
        return None
    tecla = partes[3]
    if len(tecla) != 1 or not tecla.isascii() or not tecla.isdigit():
        return None
    if tecla == "0":
        return None
    return (wx.MOD_CONTROL | wx.MOD_ALT | wx.MOD_SHIFT, ord(tecla))


class BotoneraAtajos:
    """Las nueve combinaciones globales que disparan los disparadores.

    `frame` es la ventana principal: de ella salen la ventana que registra
    las combinaciones y la instancia de disparadores en vivo. Nunca lanza:
    registrar o soltar puede fallar y se informa con el aviso.
    """

    def __init__(self, frame) -> None:
        self._ventana = frame
        self._acciones = {
            accion: (lambda numero=numero:
                     disparadores_en_vivo.disparar(frame, numero))
            for numero, accion in enumerate(ORDEN, start=1)}
        self._globales = atajos_globales.AtajosGlobales(
            frame, self._acciones, orden=ORDEN, base_ids=BASE_IDS,
            traducir=combinacion_ctrl_alt_mayus_numero)
        # Después de que la ventana exista: el registro es del sistema y pide
        # el bucle de eventos.
        try:
            wx.CallAfter(self.activar_arranque)
        except Exception:
            logger.debug(
                "No se pudieron activar los atajos de los disparadores")

    def _textos(self) -> dict:
        """Las nueve combinaciones, acción → texto guardado."""
        return {accion: f"ctrl+alt+shift+{numero}"
                for numero, accion in enumerate(ORDEN, start=1)}

    def activar_arranque(self) -> None:
        """Registra los globales y dice una vez los que usa otro programa."""
        try:
            fallidos = self._globales.activar(self._textos())
        except Exception:
            logger.exception(
                "No se pudieron activar los atajos de los disparadores")
            return
        if fallidos:
            self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))

    def _avisar(self, aviso) -> None:
        if aviso is None:
            return
        if aviso.sonido:
            try:
                _snd.reproducir(aviso.sonido)
            except Exception:
                logger.debug("No se pudo reproducir el sonido %s", aviso.sonido)
        if aviso.texto:
            anunciar(aviso.texto)
