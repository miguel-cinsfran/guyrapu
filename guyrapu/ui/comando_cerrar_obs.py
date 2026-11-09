# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Comando Cerrar OBS del menú y del panel: cierra OBS sin forzarlo."""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_activacion, obs_lanzador
from guyrapu.obs.obs_panel import GestorPanelObs
from guyrapu.voice import sound_player

logger = diagnostico.obtener_logger(__name__)

TEXTO_SIN_OBS = N_("OBS no está abierto.")
TEXTO_OCUPADO = N_("OBS está transmitiendo o grabando. Detenlo antes de "
                   "cerrar OBS.")
TEXTO_CERRANDO = N_("Cerrando OBS…")
TEXTO_CERRADO = N_("OBS cerrado.")
TEXTO_NO_SE_CERRO = N_("OBS no se cerró. Ciérralo desde su ventana.")


def _diferir(funcion):
    wx.CallAfter(funcion)


def _esta_ocupado() -> bool:
    """Indica si OBS transmite o graba; si no se puede consultar, False.

    Un OBS que no contesta es justo el caso en que el usuario quiere
    cerrarlo, así que el fallo de la consulta no frena el cierre.
    """
    gestor = None
    try:
        gestor = GestorPanelObs()
        gestor.conectar()
        transmision = gestor.estado_transmision()
        grabacion = gestor.estado_grabacion()
        return (bool(transmision.get("outputActive"))
                or bool(grabacion.get("outputActive")))
    except Exception as error:
        logger.debug("no se pudo consultar el estado de OBS; se cierra "
                     "igual: %s", error)
        return False
    finally:
        if gestor is not None:
            try:
                gestor.cerrar()
            except Exception as error:
                logger.debug("no se pudo cerrar el gestor de OBS: %s", error)


def cerrar(anunciar_en_hilo_principal):
    """Cierra OBS por pedido del usuario, sin forzarlo.

    Corre en su hilo porque la consulta y el cierre pueden tardar; los
    anuncios vuelven al hilo principal.
    """
    def _anunciar(texto, error=False):
        def _en_hilo_principal():
            if error:
                sound_player.reproducir("error")
            anunciar_en_hilo_principal(texto)
        _diferir(_en_hilo_principal)

    def _trabajar():
        if not obs_activacion.obs_esta_en_ejecucion():
            _anunciar(_(TEXTO_SIN_OBS))
            return
        if _esta_ocupado():
            _anunciar(_(TEXTO_OCUPADO), error=True)
            return
        _anunciar(_(TEXTO_CERRANDO))
        if obs_lanzador.cerrar_obs():
            _anunciar(_(TEXTO_CERRADO))
        else:
            _anunciar(_(TEXTO_NO_SE_CERRO), error=True)

    diagnostico.crear_hilo(_trabajar, "CerrarObs").start()
