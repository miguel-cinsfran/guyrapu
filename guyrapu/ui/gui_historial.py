# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Diálogo de historial de directos y vídeos vistos (accesible).

Dos pestañas —YouTube y TikTok— con lo que se ha ido viendo. Enter (o el botón
Conectar) vuelve a ese directo/vídeo; Suprimir (o Eliminar) borra la entrada. La
reconexión la hace la ventana principal vía el callback `on_conectar(url)`.
"""

from __future__ import annotations

import logging

from guyrapu.core import diagnostico
import wx

from guyrapu.capture import redaccion
from guyrapu.core import historial
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import (
    anunciar, enlazar_anuncio_de_pestana, nombre_accesible)
from guyrapu.ui import ayuda_manual, paleta
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.tema import _T, _pintar

logger = diagnostico.obtener_logger(__name__)

_PLATAFORMAS = [("YouTube", "youtube"), ("TikTok", "tiktok")]


class HistorialDialog(wx.Dialog):

    def __init__(self, parent, ruta, on_conectar):
        super().__init__(parent, title=_("Historial de directos"), size=(760, 540),
                         name="DialogoHistorial")
        self._ruta = ruta
        self._on_conectar = on_conectar
        self._lista = historial.cargar(ruta)
        self._build_ui()
        ayuda_manual.enlazar(self, "descargas")
        paleta.pintar_ventana(self)
        self.Centre()
        wx.CallAfter(self._listas["youtube"].SetFocus)

    def _build_ui(self):
        panel = wx.Panel(self, name="PanelHistorial")
        vs = wx.BoxSizer(wx.VERTICAL)

        nota = wx.StaticText(panel, name="NotaHistorial", label=_(
            "Directos y vídeos vistos. Intro o «Conectar» vuelve a abrir uno. "
            "Supr lo elimina. Los marcados «· directo» eran "
            "directos. Los de TikTok se reconectan si el usuario está en directo. "
            "Un directo de YouTube ya terminado no vuelve, pero un vídeo normal sí."))
        _pintar(nota, fg=_T.dim)
        nota.Wrap(560)
        vs.Add(nota, 0, wx.ALL, 10)

        self.nb = wx.Notebook(panel, name="PestanasHistorial")
        self._listas: dict[str, wx.ListBox] = {}
        self._piezas: dict[str, ListaConAcciones] = {}
        for titulo, plat in _PLATAFORMAS:
            self._listas[plat] = self._crear_pagina(titulo, plat)
        enlazar_anuncio_de_pestana(self.nb)
        vs.Add(self.nb, 1, wx.EXPAND | wx.ALL, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_conectar = wx.Button(panel, label=_("&Conectar"), name="ConectarHistorial")
        self.btn_quitar   = wx.Button(panel, label=_("E&liminar"), name="QuitarHistorial")
        btn_cerrar        = wx.Button(panel, wx.ID_CANCEL, _("C&errar"), name="CerrarHistorial")
        for b in (self.btn_conectar, self.btn_quitar, btn_cerrar):
            row.Add(b, 0, wx.RIGHT, 6)
        vs.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(vs)
        self.btn_conectar.Bind(wx.EVT_BUTTON, lambda e: self._conectar())
        self.btn_quitar.Bind(wx.EVT_BUTTON, lambda e: self._quitar())

        self._poblar()

    def _crear_pagina(self, titulo, plat):
        """La pestaña de una plataforma y su lista, ya enlazada."""
        pag = wx.Panel(self.nb, name=f"PagHistorial_{plat}")
        pvs = wx.BoxSizer(wx.VERTICAL)
        # Traductores: nombre accesible de la lista, con el de la plataforma.
        nombre = _("Historial de {plataforma}").format(plataforma=titulo)
        lb = wx.ListBox(pag, style=wx.LB_SINGLE | wx.LB_HSCROLL,
                        name=nombre)
        nombre_accesible(lb, nombre)
        # Traductores: fila que dice que la pestaña del historial no tiene
        # entradas; {plataforma} es el nombre de la plataforma de la pestaña.
        vacio = _("No hay entradas de {plataforma}.").format(plataforma=titulo)
        self._piezas[plat] = ListaConAcciones(lb, (
            Accion("conectar", _("&Conectar"), lambda: self._conectar(),
                   tecla="intro"),
            Accion("eliminar", _("E&liminar"), lambda: self._quitar(),
                   tecla="suprimir"),
        ), vacio)
        pvs.Add(lb, 1, wx.EXPAND | wx.ALL, 8)
        pag.SetSizer(pvs)
        self.nb.AddPage(pag, titulo)
        return lb

    # ── Datos ──────────────────────────────────────────────────────────────

    def _plat_actual(self) -> str:
        return _PLATAFORMAS[max(0, self.nb.GetSelection())][1]

    def _poblar(self, elegido=None):
        actual = self._plat_actual()
        self._entradas = {
            plat: historial.de_plataforma(self._lista, plat)
            for _titulo, plat in _PLATAFORMAS}
        for _titulo, plat in _PLATAFORMAS:
            entradas = self._entradas[plat]
            indice = None
            if plat == actual and elegido is not None:
                indice = min(elegido, len(entradas) - 1)
            self._piezas[plat].fijar(
                [historial.etiqueta(e) for e in entradas], indice)
        motivo = historial.motivo_sin_entradas(any(self._entradas.values()))
        self.btn_conectar.SetLabel(
            redaccion.etiqueta_con_motivo(_("&Conectar"), motivo))
        self.btn_quitar.SetLabel(
            redaccion.etiqueta_con_motivo(_("E&liminar"), motivo))

    def _motivo_sin_seleccion(self) -> str:
        if not any(self._entradas.values()):
            return f"{historial.motivo_sin_entradas(False)}."
        return _("Sin selección")

    def _seleccionada(self):
        plat = self._plat_actual()
        i = self._piezas[plat].indice()
        if i is None:
            return None
        return self._entradas[plat][i]

    # ── Acciones ───────────────────────────────────────────────────────────

    def _conectar(self):
        e = self._seleccionada()
        if not e:
            anunciar(self._motivo_sin_seleccion())
            return
        url = e.get("url") or ""
        if not url:
            # Traductores: aviso al conectar con una entrada del historial que
            # no tiene enlace guardado.
            anunciar(_("Esta entrada no tiene enlace."))
            return
        self.EndModal(wx.ID_OK)
        if self._on_conectar:
            self._on_conectar(url)

    def _quitar(self):
        e = self._seleccionada()
        if not e:
            anunciar(self._motivo_sin_seleccion())
            return
        indice = self._piezas[self._plat_actual()].indice()
        self._lista = [x for x in self._lista if x is not e]
        historial.guardar(self._ruta, self._lista)
        anunciar(_("Entrada eliminada del historial"))
        self._poblar(indice)


def abrir_historial(parent, ruta, on_conectar) -> None:
    dlg = HistorialDialog(parent, ruta, on_conectar)
    try:
        dlg.ShowModal()
    finally:
        dlg.Destroy()
