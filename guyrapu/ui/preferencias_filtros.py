# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Filtros del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y lee sus
campos para guardarlos aparte de la tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import formulario
from guyrapu.ui.preferencias_comun import ANCHO_NOTA, crear_panel, fila_label
from guyrapu.ui.tema import _T


class PaginaFiltros:
    """Página Filtros: palabras y usuarios que no se leen."""

    def __init__(self, config):
        self._config = config

    def construir(self, parent):
        p = crear_panel(parent, "PagFiltros")
        vs = wx.BoxSizer(wx.VERTICAL)

        rotulo = fila_label(p, _("&Palabras silenciadas (separadas por comas):"))
        self.txt_palabras = wx.TextCtrl(
            p, value=", ".join(self._config.get("palabras_silenciadas", [])),
            name=_("Palabras silenciadas"))
        formulario.agregar_fila(vs, rotulo, self.txt_palabras)

        rotulo = fila_label(p, _("&Usuarios silenciados (separados por comas):"))
        self.txt_usuarios = wx.TextCtrl(
            p, value=", ".join(self._config.get("usuarios_silenciados", [])),
            name=_("Usuarios silenciados"))
        formulario.agregar_fila(vs, rotulo, self.txt_usuarios)

        nota = wx.StaticText(p, label=_(
            "Estos filtros ocultan y no leen los mensajes que contengan esas "
            "palabras o de esos usuarios. Se aplican a partir del próximo mensaje."),
            name="NotaFiltros")
        nota.SetForegroundColour(_T.dim)
        nota.Wrap(ANCHO_NOTA)
        formulario.agregar_nota(vs, nota)

        formulario.armar_pagina(p, vs)
        return p
