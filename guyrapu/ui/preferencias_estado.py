# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Estado (F2) del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y lee sus
casillas para guardarlas aparte de la tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.capture import estado_sesion
from guyrapu.core.idioma import _
from guyrapu.ui.preferencias_comun import ANCHO_NOTA, crear_panel
from guyrapu.ui.tema import _T


class PaginaEstado:
    """Una casilla por componente del anuncio de estado (tecla F2). Sin
    colores en las casillas: en Windows eso rompe su rol accesible."""

    def __init__(self, config):
        self._config = config

    def construir(self, parent):
        p = crear_panel(parent, "PagEstado")
        vs = wx.BoxSizer(wx.VERTICAL)

        nota = wx.StaticText(p, name="NotaEstado", label=_(
            "Elige qué dice la tecla F2 (estado de sesión). Marca lo que quieras "
            "oír; por defecto, los datos del vídeo y del chat. El orden en que se "
            "dice es fijo."))
        nota.SetForegroundColour(_T.dim)
        nota.Wrap(ANCHO_NOTA)
        vs.Add(nota, 0, wx.ALL, 10)

        activos = self._config.get("estado_toggles") or estado_sesion.ACTIVOS_DEFECTO
        self._chk_estado: dict = {}
        for comp in estado_sesion.COMPONENTES:
            chk = wx.CheckBox(p, label=estado_sesion.etiqueta(comp),
                              name=f"EstadoComponente_{comp}")
            chk.SetValue(comp in activos)
            self._chk_estado[comp] = chk
            vs.Add(chk, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        p.SetSizer(vs)
        return p

    def guardar(self, fijar, en_memoria):
        activos = set()
        for comp, chk in self._chk_estado.items():
            on = chk.GetValue()
            fijar("estado", comp, "true" if on else "false")
            if on:
                activos.add(comp)
        en_memoria["estado_toggles"] = activos
