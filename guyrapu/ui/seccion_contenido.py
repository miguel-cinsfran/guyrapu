# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La sección Contenido de los cuadros de lo que sale.

Los tres cuadros piden lo mismo en el mismo orden; cada uno elige qué campos
quiere. La pieza decide los rótulos, las letras de acceso y el orden de Tab.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui import formulario
from guyrapu.ui.accesibilidad import ContadorAccesible, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO = N_("Contenido")
CAMPOS = ("texto", "mostrar_en", "medio", "segundos", "estilo")
ROTULOS = {
    "texto": N_("&Texto:"),
    "mostrar_en": N_("&Mostrar en:"),
    "medio": N_("Me&dio:"),
    "segundos": N_("&Segundos en pantalla:"),
    "estilo": N_("&Estilo:"),
}
ELECCIONES = {"mostrar_en": "cho_destino", "medio": "cho_medio",
              "estilo": "cho_estilo"}


class SeccionContenido:
    """Controles de lo que sale, con los campos que pide cada cuadro."""

    def __init__(self, panel, columna, campos, *, nota="", ayuda="",
                 destinos=(), medios=(), estilos=(), segundos=8):
        self.campos = tuple(campos)
        self.espacio = formulario.agregar_seccion(columna, panel, _(TITULO))
        self.txt_texto = None
        self.cho_destino = None
        self.cho_medio = None
        self.sp_segundos = None
        self.cho_estilo = None
        self.nota = None
        self._medios = tuple(medios)
        self._segundos = segundos
        opciones = {"mostrar_en": destinos,
                    "medio": [_("Ninguno"), *medios],
                    "estilo": estilos}
        for campo in CAMPOS:
            if campo not in self.campos:
                continue
            if campo == "texto":
                self._crear_texto(panel, ayuda, nota)
            elif campo == "segundos":
                self._crear_segundos(panel)
            else:
                self._crear_eleccion(panel, campo, opciones[campo])

    def _agregar(self, rotulo, control, campo):
        formulario.agregar_fila(self.espacio, rotulo, control,
                                numerico=campo == "segundos")

    def _crear_texto(self, panel, ayuda, nota):
        rotulo = fila_label(panel, _(ROTULOS["texto"]))
        nombre = nombre_de_etiqueta(_(ROTULOS["texto"]))
        control = wx.TextCtrl(panel, name=nombre)
        nombre_accesible(control, f"{nombre}. {ayuda}" if ayuda else nombre)
        self._agregar(rotulo, control, "texto")
        self.txt_texto = control
        if nota:
            self.nota = wx.StaticText(panel, label=nota)
            formulario.agregar_nota(self.espacio, self.nota)

    def _crear_eleccion(self, panel, campo, opciones):
        rotulo = fila_label(panel, _(ROTULOS[campo]))
        nombre = nombre_de_etiqueta(_(ROTULOS[campo]))
        control = wx.Choice(panel, choices=opciones, name=nombre)
        nombre_accesible(control, nombre)
        self._agregar(rotulo, control, campo)
        setattr(self, ELECCIONES[campo], control)

    def _crear_segundos(self, panel):
        rotulo = fila_label(panel, _(ROTULOS["segundos"]))
        nombre = nombre_de_etiqueta(_(ROTULOS["segundos"]))
        control = ContadorAccesible(
            panel, min=3, max=60, initial=self._segundos, name=nombre)
        nombre_accesible(control, nombre)
        self._agregar(rotulo, control, "segundos")
        self.sp_segundos = control

    def rotulos(self):
        """Los rótulos de la sección, en el orden de Tab."""
        return [item.GetWindow().GetLabel()
                for item in self.espacio.GetChildren()
                if isinstance(item.GetWindow(), wx.StaticText)]

    def valores(self):
        """Los valores de los campos presentes, por nombre de campo."""
        valores = {}
        if "texto" in self.campos:
            valores["texto"] = self.txt_texto.GetValue()
        if "mostrar_en" in self.campos:
            valores["mostrar_en"] = self.cho_destino.GetSelection()
        if "medio" in self.campos:
            valores["medio"] = self.cho_medio.GetStringSelection()
        if "segundos" in self.campos:
            valores["segundos"] = self.sp_segundos.GetValue()
        if "estilo" in self.campos:
            valores["estilo"] = self.cho_estilo.GetSelection()
        return valores

    def poner(self, valores):
        """Pone en los controles los valores recibidos, por nombre de campo."""
        if "texto" in self.campos:
            self.txt_texto.SetValue(valores.get("texto", ""))
        if "mostrar_en" in self.campos:
            self.cho_destino.SetSelection(valores.get("mostrar_en", 0))
        if "medio" in self.campos:
            medio = valores.get("medio", "")
            indice = self._medios.index(medio) + 1 if medio in self._medios else 0
            self.cho_medio.SetSelection(indice)
        if "segundos" in self.campos:
            self.sp_segundos.SetValue(valores.get("segundos", self._segundos))
        if "estilo" in self.campos:
            self.cho_estilo.SetSelection(valores.get("estilo", 0))
