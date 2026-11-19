# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Guardar en un archivo de texto la conversación con la IA."""

from __future__ import annotations

import os
from datetime import datetime

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.voice.sound_player import reproducir

TITULO = N_("Guardar conversación")
FILTRO = N_("Archivos de texto (*.txt)|*.txt")
# Traductores: {fecha} es AAAA-MM-DD HH-MM, sin dos puntos, que Windows no
# acepta en nombres de archivo.
NOMBRE_PROPUESTO = N_("Conversación con la IA {fecha}.txt")
MOTIVO_VACIA = N_("La conversación está vacía")
TEXTO_GUARDADA = N_("Conversación guardada en {nombre}.")
TEXTO_NO_GUARDADA = N_("No se pudo guardar la conversación.")


def texto_de(charla) -> str:
    """Cada fila del historial en su párrafo, en el orden en que se ve."""
    return "\n\n".join(charla.filas) + "\n"


def nombre_propuesto(momento) -> str:
    """El nombre por defecto, con la fecha y la hora de ahora."""
    return _(NOMBRE_PROPUESTO).format(
        fecha=momento.strftime("%Y-%m-%d %H-%M"))


def motivo_vacio(charla) -> str:
    """Por qué no se puede guardar una conversación sin filas."""
    return _(MOTIVO_VACIA) if not charla.filas else ""


def guardar(padre, charla) -> None:
    """Pregunta dónde guardar, escribe la conversación y avisa del resultado."""
    try:
        with wx.FileDialog(
                padre, _(TITULO), wildcard=_(FILTRO),
                defaultFile=nombre_propuesto(datetime.now()),
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as cuadro:
            if cuadro.ShowModal() != wx.ID_OK:
                return
            ruta = cuadro.GetPath()
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(texto_de(charla))
        except OSError:
            reproducir("ia_error")
            anunciar(_(TEXTO_NO_GUARDADA))
        else:
            reproducir("listo")
            anunciar(_(TEXTO_GUARDADA).format(nombre=os.path.basename(ruta)))
    finally:
        padre.lst_conversacion.SetFocus()
