# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Cola de lectura del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import formulario
from guyrapu.ui.accesibilidad import ContadorAccesible
from guyrapu.ui.preferencias_comun import crear_panel, fila_label


# Filas de la cola de `_OPCIONES_SIMPLES` en `gui_preferencias`: misma tabla,
# mismo orden.
OPCIONES_COLA = (
    ("sp_cola_maxima", "cola", "tamanio_maximo", "tamanio_maximo", int, 15),
    ("sp_umbral_nombre", "cola", "umbral_solo_nombre", "umbral_solo_nombre", int, 0),
)


class PaginaCola:
    """Página Cola de lectura: estrategia, tamaño y umbral del nombre."""

    def __init__(self, config):
        self._config = config

    def construir(self, parent):
        p = crear_panel(parent, "PagCola")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.rb_estrategia = wx.RadioBox(
            p, label=_("&Estrategia de la cola"), majorDimension=1,
            choices=[_("Leer todos los mensajes"),
                     _("Descartar los más antiguos si se acumulan")],
            style=wx.RA_SPECIFY_COLS, name=_("Estrategia de la cola"))
        self.rb_estrategia.SetSelection(
            0 if self._config.get("estrategia", "limite") == "todas" else 1)
        formulario.agregar_fila(vs, None, self.rb_estrategia, expandir=False)

        rotulo = fila_label(p, _("Tamaño &máximo de la cola:"))
        self.sp_cola_maxima = ContadorAccesible(
            p, min=1, max=500,
            name=_("Tamaño máximo de la cola"))
        formulario.agregar_fila(vs, rotulo, self.sp_cola_maxima, numerico=True)

        rotulo = fila_label(p, _("Leer solo el &nombre desde esta cantidad de mensajes en cola:"))
        self.sp_umbral_nombre = ContadorAccesible(p, min=0, max=500,
            name=_("Leer solo el nombre desde esta cantidad de mensajes en cola"))
        formulario.agregar_fila(vs, rotulo, self.sp_umbral_nombre, numerico=True)
        nota = wx.StaticText(p, label=_("Con 0, esta opción queda desactivada."))
        formulario.agregar_nota(vs, nota)

        formulario.armar_pagina(p, vs)
        return p
