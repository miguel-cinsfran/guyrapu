# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo una página de Interacción pide el archivo de un paquete y avisa
si no se pudo escribir o leer.

No decide qué se exporta ni cómo se incorpora: eso sigue en cada página.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.interaction import paquetes
from guyrapu.ui import confirmar

WILDCARD = N_("Paquete de Guyrapu (*.zip)|*.zip")


def pedir_ruta(padre, titulo, guardar):
    estilo = ((wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if guardar
              else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST))
    dialogo = wx.FileDialog(padre, titulo, wildcard=_(WILDCARD), style=estilo)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetPath()
    finally:
        dialogo.Destroy()


def escribir(padre, ruta, tipo, elementos, titulo, archivos=None):
    try:
        if archivos is None:
            paquetes.exportar(ruta, tipo, elementos)
        else:
            paquetes.exportar(ruta, tipo, elementos, archivos)
    except Exception as exc:
        confirmar.avisar(
            padre, _("No se pudo escribir el paquete:\n\n{exc}").format(exc=exc),
            titulo, _("Aceptar"), icono=confirmar.ICON_ERROR)
        return False
    return True


def leer(padre, ruta, tipo, titulo, extensiones=None):
    try:
        if extensiones is None:
            paquete = paquetes.leer(ruta, tipo)
        else:
            paquete = paquetes.leer(ruta, tipo, extensiones=extensiones)
    except paquetes.PaqueteRechazado as exc:
        confirmar.avisar(
            padre, str(exc), titulo, _("Aceptar"),
            icono=confirmar.ICON_ERROR)
        return None
    return paquete
