# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Conexión del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import ContadorAccesible
from guyrapu.ui.preferencias_comun import crear_panel, fila_label


# Filas de reconexión de `_OPCIONES_SIMPLES` en `gui_preferencias`: misma tabla,
# mismo orden.
OPCIONES_CONEXION = (
    ("chk_reconectar", "reconexion", "reconectar", "reconectar", bool, True),
    ("sp_espera_reconexion", "reconexion", "espera_entre_intentos",
     "espera_entre_intentos", int, 15),
    ("sp_max_intentos", "reconexion", "max_intentos", "max_intentos", int, 20),
)


class PaginaConexion:
    """Página Conexión: reconectar y los límites de los intentos."""

    def construir(self, parent):
        p = crear_panel(parent, "PagConexion")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.chk_reconectar = wx.CheckBox(
            p, label=_("&Reconectar automáticamente"),
            name=_("Reconectar automáticamente"))
        vs.Add(self.chk_reconectar, 0, wx.ALL, 10)

        vs.Add(fila_label(p, _("&Espera máxima entre intentos, en segundos:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_espera_reconexion = ContadorAccesible(
            p, min=1, max=300,
            name=_("Espera máxima entre intentos, en segundos"))
        vs.Add(self.sp_espera_reconexion, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(fila_label(p, _("Número máximo de &intentos:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_max_intentos = ContadorAccesible(
            p, min=0, max=100,
            name=_("Número máximo de intentos"))
        vs.Add(self.sp_max_intentos, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        p.SetSizer(vs)
        return p
