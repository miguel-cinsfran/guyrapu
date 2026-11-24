# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Lectura del diálogo de Preferencias.

Por composición, no como mezcla: recibe en el constructor lo que necesita
del diálogo (el dict de config y dos helpers como funciones) y expone
`construir(parent)`, que devuelve el panel, y `cambios()`, que devuelve lo
que esta página guarda fuera de la tabla para que el diálogo lo aplique
con su `_set` de hoy. Los controles conservan nombre, rótulo, `name=` y
orden; el diálogo los reexporta como atributos propios para las pruebas.
"""

from __future__ import annotations

import wx

from guyrapu.core import config_predeterminada as pred
from guyrapu.core.idioma import N_, _
from guyrapu.translation import idiomas
from guyrapu.ui import formulario
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar
from guyrapu.ui.tema import _T, _tc
from guyrapu.ui.preferencias_comun import EleccionTexto


_FORMATOS = [
    (N_("Nombre y mensaje"), "nombre_mensaje"),
    (N_("Mensaje y después el nombre"), "mensaje_nombre"),
    (N_("Solo el mensaje"),  "solo_mensaje"),
    (N_("Solo el nombre"),   "solo_nombre"),
]


# Filas de lectura de `_OPCIONES_SIMPLES` en `gui_preferencias`: misma tabla,
# mismo orden.
OPCIONES_LECTURA = (
    ("chk_emojis", "texto", "limpiar_emojis", "limpiar_emojis", bool, True),
    ("chk_urls", "texto", "eliminar_urls", "eliminar_urls", bool, True),
    ("sp_long", "texto", "max_longitud_mensaje", "max_longitud_mensaje", int,
     int(pred.obtener("texto", "max_longitud_mensaje"))),
    ("cho_lectura_recientes", "lectura", "recientes", "lectura_recientes", str, "lector"),
    ("chk_lectura_atajos_globales", "lectura", "atajos_globales", "lectura_atajos_globales", bool, False),
    ("chk_traducir", "lectura", "traducir_chat", "traducir_chat", bool, False),
    ("cho_traducir_que", "lectura", "traducir_que", "traducir_que", str, "voz_lista"),
    ("cho_traducir_idioma", "lectura", "traducir_idioma_original",
     "traducir_idioma_original", str, "completo"),
    ("cho_traducir_destino", "lectura", "traducir_destino", "traducir_destino", str, "interfaz"),
)


class PaginaLectura:
    """Página Lectura: qué leer de cada mensaje y hasta cuántos caracteres."""

    def __init__(self, config, fila_label, make_panel):
        self._config = config
        self._fila_label = fila_label
        self._make_panel = make_panel

    def construir(self, parent):
        p = self._make_panel(parent, "PagLectura")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.rb_formato = wx.RadioBox(
            p, label=_("Formato de lectura"),
            choices=[_(f[0]) for f in _FORMATOS], majorDimension=1,
            style=wx.RA_SPECIFY_COLS, name=_("Formato de lectura"))
        self.rb_formato.SetForegroundColour(_T.text)
        self.rb_formato.SetBackgroundColour(_T.bg)
        fa = self._config.get("formato_prefijo", "nombre_mensaje")
        for i, (_sin_uso, v) in enumerate(_FORMATOS):
            if v == fa:
                self.rb_formato.SetSelection(i)
                break
        formulario.agregar_bloque(vs, self.rb_formato)

        self.chk_emojis = wx.CheckBox(p, label=_("Omitir emo&jis en la lista y al leer"),
                                      name="LimpiarEmojis")
        self.chk_urls   = wx.CheckBox(p, label=_("Omitir e&nlaces al leer"), name="EliminarURLs")
        for c in (self.chk_emojis, self.chk_urls):
            c.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (self.chk_emojis, self.chk_urls))

        rotulo = self._fila_label(
            p, _("&Longitud máxima del mensaje (caracteres):"))
        self.sp_long = ContadorAccesible(p, min=20, max=1000,
                                   name=_("Longitud máxima del mensaje"))
        _tc(self.sp_long)
        formulario.agregar_fila(vs, rotulo, self.sp_long, numerico=True)

        self._construir_lecturas(p, vs)

        formulario.armar_pagina(p, vs)
        return p

    def _construir_lecturas(self, p, vs):
        rotulo = self._fila_label(p, _("Leer los mensajes &recientes con:"))
        self.cho_lectura_recientes = EleccionTexto(
            p, (("lector", _("El lector de pantalla")),
                ("voz", _("La voz de la app"))),
            name=_("Leer los mensajes recientes con"))
        _tc(self.cho_lectura_recientes)
        formulario.agregar_fila(vs, rotulo, self.cho_lectura_recientes)

        self.chk_lectura_atajos_globales = wx.CheckBox(
            p, label=_("Usar atajos del chat en cual&quier aplicación"),
            name="LecturaAtajosGlobales")
        self.chk_lectura_atajos_globales.SetForegroundColour(_T.text)
        formulario.agregar_casillas(vs, (self.chk_lectura_atajos_globales,))
        self._construir_traduccion(p, vs)

    def _construir_traduccion(self, p, vs):
        self.chk_traducir = wx.CheckBox(
            p, label=_("&Traducir chat"), name=_("Traducir chat"))
        self.chk_traducir.SetForegroundColour(_T.text)
        self.chk_traducir.Bind(wx.EVT_CHECKBOX, self._al_cambiar_traduccion)
        formulario.agregar_casillas(vs, (self.chk_traducir,))

        rotulo = self._fila_label(p, _("Tra&ducir:"))
        self.cho_traducir_que = EleccionTexto(
            p, (("voz_lista", _("La voz y la lista")),
                ("solo_voz", _("Solo la voz"))),
            name=_("Traducir"))
        _tc(self.cho_traducir_que)
        formulario.agregar_fila(vs, rotulo, self.cho_traducir_que)

        rotulo = self._fila_label(p, _("&Idioma original:"))
        self.cho_traducir_idioma = EleccionTexto(
            p, (("completo", _("Completo")),
                ("abreviado", _("Abreviado")),
                ("no", _("No decirlo"))),
            name=_("Idioma original"))
        _tc(self.cho_traducir_idioma)
        formulario.agregar_fila(vs, rotulo, self.cho_traducir_idioma)

        rotulo = self._fila_label(p, _("Traducir &al:"))
        self.cho_traducir_destino = EleccionTexto(
            p, idiomas.opciones(), name=_("Traducir al"))
        _tc(self.cho_traducir_destino)
        formulario.agregar_fila(vs, rotulo, self.cho_traducir_destino)

    def _al_cambiar_traduccion(self, evento):
        evento.Skip()
        anunciar(_("Traducción del chat activada")
                 if self.chk_traducir.GetValue()
                 else _("Traducción del chat desactivada"))

    def cambios(self):
        """Lo que esta página guarda fuera de la tabla: (sección, clave, valor)."""
        formato = _FORMATOS[self.rb_formato.GetSelection()][1]
        return [("lectura", "formato_prefijo", formato)]
