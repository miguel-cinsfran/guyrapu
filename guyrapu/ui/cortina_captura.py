# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ofrece cambiar el método de captura antes de transmitir.

La revisión de OBS deja en `revision.cortina` las capturas de pantalla que
la cortina de NVDA deja en negro. Antes de seguir con cualquier destino se
ofrece cambiarlas a Windows 10. El cambio va en un hilo con su propia
conexión, porque la revisión ya cerró la suya, y vuelve al hilo de la
interfaz para continuar la transmisión.
"""

from __future__ import annotations

from dataclasses import replace

import wx

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.obs import captura_cortina, obs_cliente
from guyrapu.ui import confirmar
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.aviso_importante import avisar
from guyrapu.voice import sound_player as _snd

logger = diagnostico.obtener_logger(__name__)


def ofrecer(padre, revision, continuar) -> None:
    """Pregunta si conviene cambiar las capturas y sigue con la revisión.

    Llama a `continuar` con la revisión sin `cortina` si se cambió, y con la
    misma si se dejó como estaba o si OBS falló.
    """
    nombres = tuple(getattr(revision, "cortina", ()) or ())
    if not nombres:
        continuar(revision)
        return
    mensaje = _(
        "La cortina de pantalla de NVDA deja en negro la captura de pantalla "
        "{nombres}. ¿Cambiar su método de captura a Windows 10? Se puede "
        "volver a cambiar en las propiedades de la fuente, en OBS.").format(
            nombres=", ".join(nombres))
    if not confirmar.preguntar(
            padre, mensaje, _("Antes de transmitir"),
            _("&Cambiar a Windows 10"), _("&Dejar como está"),
            predeterminado_si=True):
        continuar(revision)
        return
    _cambiar(revision, continuar)


def _cambiar(revision, continuar) -> None:
    def _trabajar():
        cliente = None
        try:
            cliente = obs_cliente.ClienteObs(obs_cliente.leer_ajustes())
            cliente.conectar()
            captura_cortina.cambiar(cliente, revision.cortina)
        except Exception as error:
            wx.CallAfter(_fallo, revision, continuar, error)
        else:
            wx.CallAfter(_cambiado, revision, continuar)
        finally:
            if cliente is not None:
                try:
                    cliente.cerrar()
                except Exception as error:
                    logger.debug("no se pudo cerrar OBS: %s", error)

    diagnostico.crear_hilo(_trabajar, "CortinaCapturaCambiar").start()


def _cambiado(revision, continuar) -> None:
    _snd.reproducir("listo")
    anunciar(_("Método de captura cambiado a Windows 10: {nombres}.").format(
        nombres=", ".join(revision.cortina)))
    continuar(replace(revision, cortina=()))


def _fallo(revision, continuar, error) -> None:
    avisar(_("No se pudo cambiar el método de captura a Windows 10. {motivo} "
             "Se puede cambiar a mano en las propiedades de la fuente, en "
             "OBS.").format(motivo=obs_cliente.mensaje_de_fallo_obs(error)),
           "error", error=True)
    continuar(revision)
