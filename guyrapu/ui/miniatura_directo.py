# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La miniatura del directo de YouTube: cómo se elige y cómo se muestra.

Recibe el cuadro del directo y trabaja sobre su texto y su ruta de miniatura.
Su única razón para cambiar es cómo se elige y se muestra esa miniatura.
"""

from __future__ import annotations

import os

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.youtube.emision import error_de_miniatura

_FILTRO_IMAGENES = N_("Imágenes JPG y PNG (*.jpg;*.jpeg;*.png)|"
                      "*.jpg;*.jpeg;*.png")


def texto_miniatura(ruta) -> str:
    if not ruta:
        return _("Ninguna")
    return os.path.basename(ruta)


def elegir_miniatura(ventana) -> None:
    # Traductores: traduce solo «Imágenes JPG y PNG»; no cambies «(*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png».
    with wx.FileDialog(
            ventana, _("Elegir miniatura"), wildcard=_(_FILTRO_IMAGENES),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as cuadro:
        if cuadro.ShowModal() != wx.ID_OK:
            return
        ruta = cuadro.GetPath()
    error = error_de_miniatura(ruta)
    if error:
        anunciar(error)
        return
    ventana._miniatura = ruta
    nombre = os.path.basename(ruta)
    ventana.txt_miniatura.SetValue(nombre)
    anunciar(_("Miniatura: {nombre}").format(nombre=nombre))


def quitar_miniatura(ventana) -> None:
    ventana._miniatura = ""
    ventana.txt_miniatura.SetValue(_("Ninguna"))
    anunciar(_("Sin miniatura."))
