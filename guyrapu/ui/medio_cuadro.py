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
from guyrapu.ui import formulario, medio_descripcion_ia, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.deslizador import deslizador_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar medio")
TITULO_EDITAR = N_("Editar medio")
ETIQUETA_VOLUMEN = N_("&Volumen:")
AVISO_LARGO = N_("Dura más de 15 segundos: al activarlo se detiene a los 15 segundos.")
TEXTO_SOLO_IMAGEN = N_("Solo se propone la descripción de una imagen o un GIF")
# Traductores: anuncio de la descripción que propone la IA; {texto} es la frase.
TEXTO_PROPUESTA = N_("Descripción propuesta: {texto}")


class DialogoMedio(wx.Dialog):
    """Nombre, descripción, tipo y duración de un medio."""

    def __init__(self, padre, datos, editar=False, ruta=None):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if editar else TITULO_AGREGAR),
            name="DialogoMedio")
        self._datos = medios_guardados.normalizar(datos or {})
        self._ruta = ruta
        self.aviso = None
        self.sp_volumen = None
        self._crear_controles()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelMedio")
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = self._campo(panel, "&Nombre:")
        formulario.agregar_fila(vs, rotulo, self.txt_nombre)
        rotulo = fila_label(panel, _("&Descripción:"))
        self.txt_descripcion = self._campo(panel, "&Descripción:")
        formulario.agregar_fila(vs, rotulo, self.txt_descripcion)
        self.btn_describir = wx.Button(
            panel, label=_("Describir &imagen"),
            name=nombre_de_etiqueta(_("Describir &imagen")))
        self.btn_describir.Bind(wx.EVT_BUTTON, self._describir)
        formulario.agregar_fila(vs, None, self.btn_describir, expandir=False)
        rotulo = fila_label(panel, _("&Tipo:"))
        self.txt_tipo = self._campo_lectura(panel, "&Tipo:")
        formulario.agregar_fila(vs, rotulo, self.txt_tipo)
        rotulo = fila_label(panel, _("D&uración:"))
        self.txt_duracion = self._campo_lectura(panel, "D&uración:")
        larga = (self._datos["tipo"] in ("sonido", "video")
                 and self._datos["duracion"] > 15)
        formulario.agregar_fila(vs, rotulo, self.txt_duracion)
        if self._datos["tipo"] in ("sonido", "video"):
            rotulo = fila_label(panel, _(ETIQUETA_VOLUMEN))
            self.sp_volumen = deslizador_accesible(
                panel, minimo=0, maximo=200, paso=1,
                inicial=self._datos["volumen"],
                nombre=nombre_de_etiqueta(_(ETIQUETA_VOLUMEN)))
            formulario.agregar_fila(vs, rotulo, self.sp_volumen)
        self._cargar()
        if larga:
            self.aviso = wx.StaticText(panel, label=_(AVISO_LARGO))
            self.aviso.Wrap(formulario.ANCHO_MINIMO - 2 * formulario.MARGEN)
            formulario.agregar_nota(vs, self.aviso)
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_OK))
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        formulario.agregar_pie(
            vs, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, vs)

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

    def _cargar(self):
        self.txt_nombre.SetValue(self._datos["nombre"])
        self.txt_descripcion.SetValue(self._datos["descripcion"])
        self.txt_tipo.SetValue(medios.etiqueta_tipo(self._datos["tipo"]))
        self.txt_duracion.SetValue(self._texto_duracion())

    def _describir(self, _evento):
        if self._datos["tipo"] != "imagen":
            anunciar(_(TEXTO_SOLO_IMAGEN))
            return
        medio_descripcion_ia.pedir(self, self._ruta, self._descripcion_propuesta)

    def _descripcion_propuesta(self, texto):
        self.txt_descripcion.SetValue(texto)
        self.txt_descripcion.SetFocus()
        anunciar(_(TEXTO_PROPUESTA).format(texto=texto))

    def _texto_duracion(self) -> str:
        if self._datos["tipo"] == "imagen":
            return _("No se aplica")
        if not self._datos["duracion"]:
            return _("Duración desconocida")
        return medios.duracion_en_palabras(self._datos["duracion"])

    def datos(self) -> dict:
        """El medio con el nombre, la descripción y el volumen escritos."""
        datos = {
            **self._datos,
            "nombre": self.txt_nombre.GetValue(),
            "descripcion": self.txt_descripcion.GetValue(),
        }
        if self.sp_volumen is not None:
            datos["volumen"] = self.sp_volumen.GetValue()
        return datos

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, datos, editar=False, ruta=None):
    """Abre el cuadro y devuelve los datos del medio, o None."""
    dialogo = DialogoMedio(padre, datos, editar, ruta)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
    finally:
        dialogo.Destroy()
