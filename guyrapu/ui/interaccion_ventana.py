# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Interacción: mensajes, comandos, encuestas, preguntas,
disparadores, medios, estilos y palabras bloqueadas.

Una sola ventana con una lista de páginas, como Preferencias. La página se
elige por su identificador y se recuerda al cerrar.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.interaction import conversion_disparadores
from guyrapu.ui import ensayo_ventana, formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.comandos_ventana import PanelComandos
from guyrapu.ui.disparadores_ventana import PanelDisparadores
from guyrapu.ui.encuestas_ventana import PanelEncuestas
from guyrapu.ui.estilos_ventana import PanelEstilos
from guyrapu.ui.medios_ventana import PanelMedios
from guyrapu.ui.metas_ventana import PanelMetas
from guyrapu.ui.mensajes_automaticos_ventana import PanelMensajesAutomaticos
from guyrapu.ui.palabras_bloqueadas_ventana import PanelPalabrasBloqueadas
from guyrapu.ui.preferencias_comun import ajustar_ancho_categorias
from guyrapu.ui.preguntas_ventana import PanelPreguntas

PAGINAS = (
    ("comandos", N_("Comandos")),
    ("disparadores", N_("Alertas")),
    ("mensajes", N_("Mensajes automáticos")),
    ("encuestas", N_("Encuestas")),
    ("preguntas", N_("Preguntas")),
    ("metas", N_("Metas")),
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
        conversion_disparadores.convertir_en_disco()
        super().__init__(
            padre, title=_("Interacción"), name=_("Interacción"),
            size=(760, 640),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        vs = wx.BoxSizer(wx.VERTICAL)
        self.libro = wx.Listbook(self, name=_("Interacción"))
        self.lista_paginas = self.libro.GetListView()
        nombre_accesible(self.lista_paginas, _("Páginas de interacción"))
        self._paginas = self._crear_paginas(padre)
        for clave, etiqueta in PAGINAS:
            self.libro.AddPage(self._paginas[clave], _(etiqueta))
        self.libro.SetSelection(self._pagina_inicial(padre, pagina))
        ajustar_ancho_categorias(self.libro, self.lista_paginas)
        vs.Add(self.libro, 1, wx.EXPAND | wx.ALL, 10)
        self.btn_probar = wx.Button(
            self, label=_("Probar sin direc&to"), name=_("Probar sin directo"))
        self.btn_probar.Bind(wx.EVT_BUTTON, self._al_probar)
        self.btn_cerrar = wx.Button(
            self, wx.ID_CANCEL, _("&Cerrar"), name=_("Cerrar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._al_cerrar)
        formulario.agregar_pie(vs, [self.btn_probar, self.btn_cerrar])
        self.SetSizer(vs)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        paleta.pintar_ventana(self)
        self.Centre()
        self._paginas[self.pagina_actual()].lista.SetFocus()

    def _crear_paginas(self, padre):
        return {
            "mensajes": PanelMensajesAutomaticos(self.libro, padre),
            "comandos": PanelComandos(self.libro),
            "encuestas": PanelEncuestas(self.libro),
            "preguntas": PanelPreguntas(self.libro, padre),
            "disparadores": PanelDisparadores(self.libro),
            "metas": PanelMetas(self.libro),
            "medios": PanelMedios(self.libro),
            "estilos": PanelEstilos(self.libro),
            "palabras": PanelPalabrasBloqueadas(self.libro),
        }

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

    def _al_probar(self, _evento):
        ensayo_ventana.abrir(self.GetParent())

    def _al_cerrar(self, _evento):
        self._paginas["medios"].soltar()
        self.EndModal(wx.ID_CANCEL)
