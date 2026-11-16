# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botones de grabación del panel de transmisión.

Iniciar o detener la grabación y pausarla o reanudarla, con las etiquetas,
los anuncios y los sonidos que ya usa el panel.
"""

from __future__ import annotations

import wx

from guyrapu.capture import redaccion
from guyrapu.core.idioma import N_, _
from guyrapu.ui import comandos_grabacion
from guyrapu.ui.aviso_importante import avisar
from guyrapu.ui.preferencias_comun import mostrar_control, nombre_de_etiqueta


_INICIAR_GRABACION = N_("Iniciar &grabación")
_DETENER_GRABACION = N_("Detener &grabación")
_PAUSAR_GRABACION = N_("&Pausar grabación")
_REANUDAR_GRABACION = N_("&Reanudar grabación")


def _crear_botones(padre):
    boton = wx.Button(padre, label=_(_INICIAR_GRABACION),
                      name=nombre_de_etiqueta(_(_INICIAR_GRABACION)))
    pausar = wx.Button(padre, label=_(_PAUSAR_GRABACION),
                       name=nombre_de_etiqueta(_(_PAUSAR_GRABACION)))
    boton._etiqueta_base = _(_INICIAR_GRABACION)
    pausar._etiqueta_base = _(_PAUSAR_GRABACION)
    return boton, pausar


class ControlGrabacion:
    """Botones de grabación del panel: iniciar o detener, y pausar o reanudar."""

    def __init__(self, padre, operaciones, gestor, al_cambiar, foco, perfil):
        self._operaciones = operaciones
        self._gestor = gestor
        self._al_cambiar = al_cambiar
        self._foco = foco
        self._perfil = perfil
        self.grabando = False
        self.en_pausa = False
        self.boton, self.pausar = _crear_botones(padre)
        self.boton.Bind(wx.EVT_BUTTON, self._alternar)
        self.pausar.Bind(wx.EVT_BUTTON, self._alternar_pausa)

    def fijar(self, grabando, en_pausa):
        self.grabando = bool(grabando)
        self.en_pausa = bool(en_pausa)
        etiqueta = (_DETENER_GRABACION if self.grabando else _INICIAR_GRABACION)
        self._fijar_boton(self.boton, etiqueta)
        etiqueta = (_REANUDAR_GRABACION if self.en_pausa
                    else _PAUSAR_GRABACION)
        self._fijar_boton(self.pausar, etiqueta)
        mostrar_control(self.pausar, self.grabando, self._foco)

    @staticmethod
    def _fijar_boton(control, etiqueta):
        control._etiqueta_base = _(etiqueta)
        texto = redaccion.etiqueta_con_motivo(
            _(etiqueta), getattr(control, "_motivo", ""))
        control.SetLabel(texto)
        control.SetName(nombre_de_etiqueta(texto))

    def _alternar(self, event):
        if not self._operaciones.puede_correr():
            return
        self._operaciones.en_hilo(
            lambda: comandos_grabacion.alternar_grabacion_obs(
                self._gestor, self._perfil()),
            self._alternada)

    def _alternada(self, resultado):
        frase, sonido, activa = resultado
        self.fijar(activa, False)
        self._avisar(frase, sonido)
        self._al_cambiar()

    def _alternar_pausa(self, event):
        if not self._operaciones.puede_correr():
            return
        self._operaciones.en_hilo(
            lambda: comandos_grabacion.alternar_pausa_obs(self._gestor),
            self._pausa_alternada)

    def _pausa_alternada(self, resultado):
        frase, sonido, en_pausa = resultado
        if sonido == "error":
            self._avisar(frase, sonido)
            return
        self.fijar(self.grabando, en_pausa)
        self._avisar(frase, sonido)
        self._al_cambiar()

    def _avisar(self, frase, sonido):
        if sonido == "error":
            avisar(frase, sonido, error=True)
        else:
            avisar(frase, sonido)
