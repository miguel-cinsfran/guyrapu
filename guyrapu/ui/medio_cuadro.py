# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita el nombre y la descripción de un medio.

Recoge los datos y valida: no guarda ni copia el archivo. La colección y el
disco los maneja la página de medios.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.interaction import medios, medios_guardados
from guyrapu.ui import paleta, tecla_escape
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar medio")
TITULO_EDITAR = N_("Editar medio")
AVISO_LARGO = N_("Dura más de 15 segundos: al dispararlo se detiene a los 15")


class DialogoMedio(wx.Dialog):
    """Nombre, descripción, tipo y duración de un medio."""

    def __init__(self, padre, datos, editar=False):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if editar else TITULO_AGREGAR),
            name="DialogoMedio")
        self._datos = medios_guardados.normalizar(datos or {})
        self.aviso = None
        self._crear_controles()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelMedio")
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(panel, _("&Nombre:")), 0, wx.ALL, 8)
        self.txt_nombre = self._campo(panel, "&Nombre:")
        vs.Add(self.txt_nombre, 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("&Descripción:")), 0,
               wx.LEFT | wx.RIGHT, 8)
        self.txt_descripcion = self._campo(panel, "&Descripción:")
        vs.Add(self.txt_descripcion, 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("&Tipo:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt_tipo = self._campo_lectura(panel, "&Tipo:")
        vs.Add(self.txt_tipo, 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("D&uración:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt_duracion = self._campo_lectura(panel, "D&uración:")
        vs.Add(self.txt_duracion, 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._cargar()
        self._agregar_aviso(panel, vs)
        vs.Add(self._botones(panel), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        panel.SetSizer(vs)

    def _campo(self, panel, etiqueta):
        campo = wx.TextCtrl(panel, name=nombre_de_etiqueta(_(etiqueta)))
        nombre_accesible(campo, nombre_de_etiqueta(_(etiqueta)))
        return campo

    def _campo_lectura(self, panel, etiqueta):
        campo = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL,
            name=nombre_de_etiqueta(_(etiqueta)))
        nombre_accesible(campo, nombre_de_etiqueta(_(etiqueta)))
        campo.SetMinSize((-1, campo.GetCharHeight() + 8))
        return campo

    def _agregar_aviso(self, panel, vs):
        tipo = self._datos["tipo"]
        if tipo not in ("sonido", "video") or self._datos["duracion"] <= 15:
            return
        self.aviso = wx.StaticText(panel, label=_(AVISO_LARGO))
        self.aviso.Wrap(360)
        vs.Add(self.aviso, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    def _cargar(self):
        self.txt_nombre.SetValue(self._datos["nombre"])
        self.txt_descripcion.SetValue(self._datos["descripcion"])
        self.txt_tipo.SetValue(medios.etiqueta_tipo(self._datos["tipo"]))
        self.txt_duracion.SetValue(self._texto_duracion())

    def _texto_duracion(self) -> str:
        if self._datos["tipo"] == "imagen":
            return _("No se aplica")
        if not self._datos["duracion"]:
            return _("Duración desconocida")
        return medios.duracion_en_palabras(self._datos["duracion"])

    def _botones(self, panel):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"),
                                     name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_OK))
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        fila.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        return fila

    def datos(self) -> dict:
        """El medio con el nombre y la descripción escritos."""
        return {
            **self._datos,
            "nombre": self.txt_nombre.GetValue(),
            "descripcion": self.txt_descripcion.GetValue(),
        }

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, datos, editar=False):
    """Abre el cuadro y devuelve los datos del medio, o None."""
    dialogo = DialogoMedio(padre, datos, editar)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
    finally:
        dialogo.Destroy()
