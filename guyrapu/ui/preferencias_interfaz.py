# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Interfaz del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
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

        vs.Add(fila_label(p, _("Tamaño de &letra del chat (8 a 24):")),
               0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.sp_fuente = ContadorAccesible(p, min=8, max=24, name=_("Tamaño de letra del chat"))
        vs.Add(self.sp_fuente, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.chk_total_sc = wx.CheckBox(
            p, label=_("Mostrar total de &Super Chats en la barra de estado"),
            name="MostrarTotalSuperChats")
        vs.Add(self.chk_total_sc, 0, wx.ALL, 10)

        self.chk_metadatos = wx.CheckBox(p, label=_("Mostrar pestaña de &información del vídeo"),
                                          name="MostrarMetadatos")
        vs.Add(self.chk_metadatos, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        p.SetSizer(vs)
        return p
