# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Interacción: mensajes, comandos, encuestas, disparadores, medios,
estilos y palabras bloqueadas.

Una sola ventana con una lista de páginas, como Preferencias. La página se
elige por su identificador y se recuerda al cerrar.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui import paleta, tecla_escape
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.comandos_ventana import PanelComandos
from guyrapu.ui.disparadores_ventana import PanelDisparadores
from guyrapu.ui.encuestas_ventana import PanelEncuestas
from guyrapu.ui.estilos_ventana import PanelEstilos
from guyrapu.ui.medios_ventana import PanelMedios
from guyrapu.ui.mensajes_automaticos_ventana import PanelMensajesAutomaticos
from guyrapu.ui.palabras_bloqueadas_ventana import PanelPalabrasBloqueadas
from guyrapu.ui.preferencias_comun import ajustar_ancho_categorias

PAGINAS = (
    ("mensajes", N_("Mensajes automáticos")),
    ("comandos", N_("Comandos")),
    ("encuestas", N_("Encuestas")),
    ("disparadores", N_("Disparadores")),
    ("medios", N_("Medios")),
    ("estilos", N_("Estilos")),
    ("palabras", N_("Palabras bloqueadas")),
)


def _indice_de(pagina):
    return next((indice for indice, (clave, _etiqueta) in enumerate(PAGINAS)
                 if clave == pagina), None)


class VentanaInteraccion(wx.Dialog):
    """Las páginas de interacción con una lista para elegirlas."""

    def __init__(self, padre, pagina=None):
        super().__init__(
            padre, title=_("Interacción"), name=_("Interacción"),
            size=(760, 640),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._paginas = {}
        vs = wx.BoxSizer(wx.VERTICAL)
        self.libro = wx.Listbook(self, name=_("Interacción"))
        self.lista_paginas = self.libro.GetListView()
        nombre_accesible(self.lista_paginas, _("Páginas de interacción"))
        self._paginas["mensajes"] = PanelMensajesAutomaticos(
            self.libro, padre)
        self._paginas["comandos"] = PanelComandos(self.libro)
        self._paginas["encuestas"] = PanelEncuestas(self.libro)
        self._paginas["disparadores"] = PanelDisparadores(self.libro)
        self._paginas["medios"] = PanelMedios(self.libro)
        self._paginas["estilos"] = PanelEstilos(self.libro)
        self._paginas["palabras"] = PanelPalabrasBloqueadas(self.libro)
        for clave, etiqueta in PAGINAS:
            self.libro.AddPage(self._paginas[clave], _(etiqueta))
        self.libro.SetSelection(self._pagina_inicial(padre, pagina))
        ajustar_ancho_categorias(self.libro, self.lista_paginas)
        vs.Add(self.libro, 1, wx.EXPAND | wx.ALL, 10)
        self.btn_cerrar = wx.Button(
            self, wx.ID_CANCEL, _("&Cerrar"), name=_("Cerrar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._al_cerrar)
        vs.Add(self.btn_cerrar, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT
               | wx.BOTTOM, 10)
        self.SetSizer(vs)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        paleta.pintar_ventana(self)
        self.Centre()
        self._paginas[self.pagina_actual()].lista.SetFocus()

    def _pagina_inicial(self, padre, pagina):
        indice = _indice_de(pagina)
        if indice is None:
            indice = _indice_de(padre._config.get("interaccion_pagina"))
        return indice if indice is not None else 0

    def pagina_actual(self) -> str:
        """El identificador de la página a la vista."""
        return PAGINAS[self.libro.GetSelection()][0]

    def _al_tecla(self, evento):
        if (tecla_escape.es_escape(evento.GetKeyCode())
                and self._paginas["medios"].detener_escucha()):
            return
        tecla_escape.cancelar_si_escape(self, evento)

    def _al_cerrar(self, _evento):
        self._paginas["medios"].soltar()
        self.EndModal(wx.ID_CANCEL)
