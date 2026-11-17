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

from guyrapu.core.idioma import N_, _
from guyrapu.translation import idiomas
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
    ("sp_long", "texto", "max_longitud_mensaje", "max_longitud_mensaje", int, 200),
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
            p, label=_("Qué leer de cada mensaje"),
            choices=[_(f[0]) for f in _FORMATOS], majorDimension=1,
            style=wx.RA_SPECIFY_COLS, name=_("Formato de lectura"))
        self.rb_formato.SetForegroundColour(_T.text)
        self.rb_formato.SetBackgroundColour(_T.bg)
        fa = self._config.get("formato_prefijo", "nombre_mensaje")
        for i, (_sin_uso, v) in enumerate(_FORMATOS):
            if v == fa:
                self.rb_formato.SetSelection(i)
                break
        vs.Add(self.rb_formato, 0, wx.ALL, 10)

        self.chk_emojis = wx.CheckBox(p, label=_("Omitir emo&jis en la lista y al leer"),
                                      name="LimpiarEmojis")
        self.chk_urls   = wx.CheckBox(p, label=_("Omitir e&nlaces al leer"), name="EliminarURLs")
        for c in (self.chk_emojis, self.chk_urls):
            c.SetForegroundColour(_T.text)
        vs.Add(self.chk_emojis, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        vs.Add(self.chk_urls, 0, wx.ALL, 10)

        vs.Add(self._fila_label(p, _("&Longitud máxima del mensaje (caracteres):")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.sp_long = ContadorAccesible(p, min=20, max=1000,
                                   name=_("Longitud máxima del mensaje"))
        _tc(self.sp_long)
        vs.Add(self.sp_long, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._construir_lecturas(p, vs)

        p.SetSizer(vs)
        return p

    def _construir_lecturas(self, p, vs):
        vs.Add(self._fila_label(p, _("Leer los mensajes &recientes con:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.cho_lectura_recientes = EleccionTexto(
            p, (("lector", _("El lector de pantalla")),
                ("voz", _("La voz de la app"))),
            name=_("Leer los mensajes recientes con"))
        _tc(self.cho_lectura_recientes)
        vs.Add(self.cho_lectura_recientes, 0,
               wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.chk_lectura_atajos_globales = wx.CheckBox(
            p, label=_("Leer mensajes recientes en cual&quier aplicación"),
            name="LecturaAtajosGlobales")
        self.chk_lectura_atajos_globales.SetForegroundColour(_T.text)
        vs.Add(self.chk_lectura_atajos_globales, 0,
               wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._construir_traduccion(p, vs)

    def _construir_traduccion(self, p, vs):
        self.chk_traducir = wx.CheckBox(
            p, label=_("&Traducir chat"), name=_("Traducir chat"))
        self.chk_traducir.SetForegroundColour(_T.text)
        self.chk_traducir.Bind(wx.EVT_CHECKBOX, self._al_cambiar_traduccion)
        vs.Add(self.chk_traducir, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        vs.Add(self._fila_label(p, _("Qué se tra&duce:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.cho_traducir_que = EleccionTexto(
            p, (("voz_lista", _("La voz y la lista")),
                ("solo_voz", _("Solo la voz"))),
            name=_("Qué se traduce"))
        _tc(self.cho_traducir_que)
        vs.Add(self.cho_traducir_que, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(self._fila_label(p, _("&Idioma original:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.cho_traducir_idioma = EleccionTexto(
            p, (("completo", _("Completo")),
                ("abreviado", _("Abreviado")),
                ("no", _("No decirlo"))),
            name=_("Idioma original"))
        _tc(self.cho_traducir_idioma)
        vs.Add(self.cho_traducir_idioma, 0,
               wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(self._fila_label(p, _("Traducir &al:")),
               0, wx.LEFT | wx.RIGHT, 10)
        self.cho_traducir_destino = EleccionTexto(
            p, idiomas.opciones(), name=_("Traducir al"))
        _tc(self.cho_traducir_destino)
        vs.Add(self.cho_traducir_destino, 0,
               wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _al_cambiar_traduccion(self, evento):
        evento.Skip()
        anunciar(_("Traducción del chat activada")
                 if self.chk_traducir.GetValue()
                 else _("Traducción del chat desactivada"))

    def cambios(self):
        """Lo que esta página guarda fuera de la tabla: (sección, clave, valor)."""
        formato = _FORMATOS[self.rb_formato.GetSelection()][1]
        return [("lectura", "formato_prefijo", formato)]
