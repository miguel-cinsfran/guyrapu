# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Interfaz del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import formulario
from guyrapu.ui.accesibilidad import ContadorAccesible
from guyrapu.ui.preferencias_comun import crear_panel, fila_label


# Filas de interfaz de `_OPCIONES_SIMPLES` en `gui_preferencias`: misma tabla,
# mismo orden.
OPCIONES_INTERFAZ = (
    ("sp_fuente", "ui", "tamanio_fuente_chat", "tamanio_fuente_chat", int, 12),
    ("chk_total_sc", "ui", "mostrar_total_superchats", "mostrar_total_superchats", bool, True),
    ("chk_metadatos", "ui", "mostrar_metadatos", "mostrar_metadatos", bool, True),
)


class PaginaInterfaz:
    """Página Interfaz: tamaño de letra del chat y lo que se muestra."""

    def construir(self, parent):
        p = crear_panel(parent, "PagInterfaz")
        vs = wx.BoxSizer(wx.VERTICAL)

        rotulo = fila_label(p, _("Tamaño de &letra del chat (8 a 24):"))
        self.sp_fuente = ContadorAccesible(p, min=8, max=24, name=_("Tamaño de letra del chat"))
        formulario.agregar_fila(vs, rotulo, self.sp_fuente, numerico=True)

        self.chk_total_sc = wx.CheckBox(
            p, label=_("Mostrar total de &Super Chats en la barra de estado"),
            name="MostrarTotalSuperChats")
        formulario.agregar_fila(vs, None, self.chk_total_sc, expandir=False)

        self.chk_metadatos = wx.CheckBox(p, label=_("Mostrar pestaña de &información del vídeo"),
                                          name="MostrarMetadatos")
        formulario.agregar_fila(vs, None, self.chk_metadatos, expandir=False)

        formulario.armar_pagina(p, vs)
        return p
