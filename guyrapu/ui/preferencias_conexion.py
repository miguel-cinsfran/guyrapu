# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Conexión del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import formulario
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
        formulario.agregar_fila(vs, None, self.chk_reconectar, expandir=False)

        rotulo = fila_label(p, _("&Espera máxima entre intentos, en segundos:"))
        self.sp_espera_reconexion = ContadorAccesible(
            p, min=1, max=300,
            name=_("Espera máxima entre intentos, en segundos"))
        formulario.agregar_fila(vs, rotulo, self.sp_espera_reconexion,
                                numerico=True)

        rotulo = fila_label(p, _("Número máximo de &intentos:"))
        self.sp_max_intentos = ContadorAccesible(
            p, min=0, max=100,
            name=_("Número máximo de intentos"))
        formulario.agregar_fila(vs, rotulo, self.sp_max_intentos, numerico=True)

        formulario.armar_pagina(p, vs)
        return p
