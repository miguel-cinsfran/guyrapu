# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadros de propiedades de una fuente, para agregar y para Propiedades."""

from __future__ import annotations

import os

import wx

from guyrapu.capture import redaccion
from guyrapu.core.idioma import _
from guyrapu.ui import (agregar_camara, escena_captura_ventana, formulario,
                        paleta, tecla_escape)
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import (
    boton, fila_label, lista_con_nombre, nombre_de_etiqueta)

_COMODIN_IMAGEN = "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp"
_COMODIN_MULTIMEDIA = (
    "*.mp4;*.mkv;*.mov;*.webm;*.avi;*.mp3;*.wav;*.ogg;*.flac;*.m4a")
_TAMANO_MINIMO = 8
_TAMANO_MAXIMO = 300
_TAMANO_INICIAL = 72


class DialogoBase(wx.Dialog):
    """Título, controles, Aceptar y Cancelar al final, Escape cancela."""

    def __init__(self, padre, titulo, nombre, aceptar=None,
                 cancelar=None):
        super().__init__(padre, title=titulo, name=nombre)
        self._etiqueta_aceptar = aceptar or _("&Aceptar")
        self._etiqueta_cancelar = cancelar or _("&Cancelar")
        self._valores = None
        self._panel = wx.Panel(self)
        self.vertical = wx.BoxSizer(wx.VERTICAL)
        self._crear_controles()
        self._crear_botones()
        formulario.ajustar_tamano(self, self._panel, self.vertical)
        self._enlazar_eventos()
        paleta.pintar_ventana(self)
        self.Centre()
        self._enfocar()

    def _crear_controles(self):
        raise NotImplementedError

    def _leer(self):
        raise NotImplementedError

    def _enfocar(self):
        for hijo in self._panel.GetChildren():
            if isinstance(hijo, (wx.Choice, wx.TextCtrl, wx.SpinCtrl)):
                hijo.SetFocus()
                return

    def _crear_botones(self):
        self.btn_aceptar = boton(
            self._panel, self._etiqueta_aceptar,
            nombre_de_etiqueta(self._etiqueta_aceptar), wx.ID_OK)
        self.btn_aceptar.SetDefault()
        self.btn_cancelar = boton(
            self._panel, self._etiqueta_cancelar,
            nombre_de_etiqueta(self._etiqueta_cancelar), wx.ID_CANCEL)
        formulario.agregar_pie(
            self.vertical, [self.btn_aceptar, self.btn_cancelar])

    def _enlazar_eventos(self):
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._al_aceptar)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._al_cancelar)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)

    def valor(self):
        return self._valores

    def _al_aceptar(self, _event):
        valores = self._leer()
        if valores is None:
            return
        self._valores = valores
        self.EndModal(wx.ID_OK)

    def _al_cancelar(self, _event):
        self.EndModal(wx.ID_CANCEL)

    def _al_tecla(self, event):
        tecla_escape.cancelar_si_escape(self, event)


class DialogoEleccion(DialogoBase):
    """Una lista con su rótulo y el mensaje que se muestra si está vacía."""

    def __init__(self, padre, titulo, nombre, etiqueta, opciones,
                 actual="", vacio="", aceptar=None,
                 cancelar=None):
        self._etiqueta = etiqueta
        self._lista_valores = [valor for _texto, valor in opciones or ()]
        self._opciones = tuple(opciones or ())
        self._actual = actual
        self._vacio = vacio
        super().__init__(padre, titulo, nombre, aceptar, cancelar)

    def _crear_controles(self):
        self.rotulo = fila_label(self._panel, self._etiqueta)
        self.lista = lista_con_nombre(
            self._panel, self._etiqueta,
            [texto for texto, _valor in self._opciones])
        if self._actual in self._lista_valores:
            self.lista.SetSelection(self._lista_valores.index(self._actual))
        elif self._lista_valores:
            self.lista.SetSelection(0)
        formulario.agregar_fila(self.vertical, self.rotulo, self.lista)
        self.aviso_vacio = None
        if not self._opciones:
            self.aviso_vacio = wx.StaticText(self._panel, label=self._vacio)
            self.aviso_vacio.Wrap(
                formulario.ANCHO_MINIMO - 2 * formulario.MARGEN)
            formulario.agregar_fila(self.vertical, None, self.aviso_vacio)

    def _enfocar(self):
        if self._opciones:
            self.lista.SetFocus()
        else:
            self.btn_cancelar.SetFocus()

    def _crear_botones(self):
        super()._crear_botones()
        if not self._opciones:
            self.btn_aceptar.SetLabel(redaccion.etiqueta_con_motivo(
                self._etiqueta_aceptar, self._vacio.rstrip(".")))

    def _al_aceptar(self, _event):
        if not self._opciones:
            anunciar(self._vacio)
            return
        super()._al_aceptar(_event)

    def _leer(self):
        indice = self.lista.GetSelection()
        if (indice == wx.NOT_FOUND or indice < 0
                or indice >= len(self._lista_valores)):
            return None
        return self._lista_valores[indice]


class DialogoJuego(DialogoBase):
    """Modo de captura y, si es de una ventana, cuál."""

    def __init__(self, padre, ventanas, valores):
        self._ventanas = tuple(ventanas or ())
        self._valores_ventana = [valor for _texto, valor in self._ventanas]
        valores = valores or {}
        self._modo = valores.get("modo") or "any_fullscreen"
        self._ventana = valores.get("ventana") or ""
        super().__init__(padre, _("Captura de juego"), "DialogoJuego")

    def _crear_controles(self):
        self.rotulo_modo = fila_label(self._panel, _("Cap&turar:"))
        self.cho_modo = lista_con_nombre(
            self._panel, _("Cap&turar:"),
            [_("Cualquier juego a pantalla completa"), _("Una ventana")])
        self.cho_modo.SetSelection(1 if self._modo == "window" else 0)
        formulario.agregar_fila(
            self.vertical, self.rotulo_modo, self.cho_modo)
        self.rotulo_ventana = fila_label(self._panel, _("&Ventana:"))
        self.cho_ventana = lista_con_nombre(
            self._panel, _("&Ventana:"),
            [texto for texto, _valor in self._ventanas])
        if self._ventana in self._valores_ventana:
            self.cho_ventana.SetSelection(
                self._valores_ventana.index(self._ventana))
        elif self._valores_ventana:
            self.cho_ventana.SetSelection(0)
        self.fila_ventana = wx.BoxSizer(wx.VERTICAL)
        formulario.agregar_fila(
            self.fila_ventana, self.rotulo_ventana, self.cho_ventana)
        formulario.agregar_bloque(self.vertical, self.fila_ventana)
        self._vacio = _("No hay ventanas para capturar.")
        self.aviso_vacio = wx.StaticText(self._panel, label=self._vacio)
        self.aviso_vacio.Wrap(
            formulario.ANCHO_MINIMO - 2 * formulario.MARGEN)
        formulario.agregar_fila(self.vertical, None, self.aviso_vacio)
        self._mostrar_ventana(self._modo == "window")

    def _enfocar(self):
        self.cho_modo.SetFocus()

    def _mostrar_ventana(self, mostrar):
        self.rotulo_ventana.Show(mostrar)
        self.cho_ventana.Show(mostrar)
        self.fila_ventana.ShowItems(mostrar)
        self.vertical.Show(self.fila_ventana, mostrar)
        vacia = mostrar and not self._ventanas
        self.aviso_vacio.Show(bool(vacia))
        if hasattr(self, "btn_aceptar"):
            motivo = self._vacio.rstrip(".") if vacia else ""
            self.btn_aceptar.SetLabel(redaccion.etiqueta_con_motivo(
                self._etiqueta_aceptar, motivo))
        if not mostrar and self.cho_ventana.HasFocus():
            self.cho_modo.SetFocus()
        self.Layout()

    def _crear_botones(self):
        super()._crear_botones()
        self._mostrar_ventana(self.cho_modo.GetSelection() == 1)

    def _enlazar_eventos(self):
        super()._enlazar_eventos()
        self.cho_modo.Bind(wx.EVT_CHOICE, self._al_cambiar_modo)

    def _al_cambiar_modo(self, _event):
        self._mostrar_ventana(self.cho_modo.GetSelection() == 1)

    def _al_aceptar(self, _event):
        if self.cho_modo.GetSelection() == 1 and not self._ventanas:
            anunciar(self._vacio)
            return
        super()._al_aceptar(_event)

    def _leer(self):
        if self.cho_modo.GetSelection() != 1:
            return {"modo": "any_fullscreen", "ventana": ""}
        indice = self.cho_ventana.GetSelection()
        if (indice == wx.NOT_FOUND or indice < 0
                or indice >= len(self._valores_ventana)):
            anunciar(_("Elige primero una ventana en Ventana."))
            return None
        return {"modo": "window", "ventana": self._valores_ventana[indice]}


class DialogoArchivo(DialogoBase):
    """Un archivo con Examinar y, para multimedia, si se repite."""

    def __init__(self, padre, clave, valores):
        self._clave = clave
        self._archivo = (valores or {}).get("archivo", "")
        self._repetir = bool((valores or {}).get("repetir", False))
        super().__init__(padre, _("Archivo multimedia") if clave == "multimedia"
                         else _("Imagen"), "DialogoArchivo")

    def _crear_controles(self):
        self.rotulo_archivo = fila_label(self._panel, _("Arch&ivo:"))
        self.txt_archivo = wx.TextCtrl(
            self._panel, value=self._archivo,
            name=nombre_de_etiqueta(_("Arch&ivo:")))
        nombre_accesible(self.txt_archivo, self.txt_archivo.GetName())
        self.btn_examinar = boton(
            self._panel, _("&Examinar…"), nombre_de_etiqueta(_("&Examinar…")))
        campo = wx.BoxSizer(wx.HORIZONTAL)
        campo.Add(self.txt_archivo, 1, wx.EXPAND)
        campo.Add(self.btn_examinar, 0, wx.LEFT, 8)
        formulario.agregar_fila(self.vertical, self.rotulo_archivo, campo)
        self.chk_repetir = None
        if self._clave == "multimedia":
            self.chk_repetir = wx.CheckBox(
                self._panel, label=_("&Repetir"),
                name=nombre_de_etiqueta(_("&Repetir")))
            self.chk_repetir.SetValue(self._repetir)
            formulario.agregar_fila(self.vertical, None, self.chk_repetir)

    def _enfocar(self):
        self.txt_archivo.SetFocus()

    def _enlazar_eventos(self):
        super()._enlazar_eventos()
        self.btn_examinar.Bind(wx.EVT_BUTTON, self._al_examinar)

    def _al_examinar(self, _event):
        comodin = (_COMODIN_MULTIMEDIA if self._clave == "multimedia"
                   else _COMODIN_IMAGEN)
        with wx.FileDialog(
                self, _("Elegir archivo"),
                wildcard=_("Archivos") + "|" + comodin,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialogo:
            if dialogo.ShowModal() == wx.ID_OK:
                self.txt_archivo.SetValue(dialogo.GetPath())

    def _leer(self):
        archivo = self.txt_archivo.GetValue().strip()
        if not archivo or not os.path.isfile(archivo):
            anunciar(_("Elige un archivo que exista."))
            return None
        if self._clave == "multimedia":
            return {"archivo": archivo,
                    "repetir": bool(self.chk_repetir.GetValue())}
        return {"archivo": archivo}


class DialogoTexto(DialogoBase):
    """El texto y el tamaño de letra."""

    def __init__(self, padre, valores):
        valores = valores or {}
        self._texto = valores.get("texto", "")
        self._tamano = int(valores.get("tamano", _TAMANO_INICIAL))
        super().__init__(padre, _("Texto"), "DialogoTexto")

    def _crear_controles(self):
        self.rotulo_texto = fila_label(self._panel, _("&Texto:"))
        self.txt_texto = wx.TextCtrl(
            self._panel, value=self._texto,
            name=nombre_de_etiqueta(_("&Texto:")))
        nombre_accesible(self.txt_texto, self.txt_texto.GetName())
        formulario.agregar_fila(
            self.vertical, self.rotulo_texto, self.txt_texto)
        self.rotulo_tamano = fila_label(self._panel, _("Tamaño de letra:"))
        self.spin_tamano = wx.SpinCtrl(
            self._panel, min=_TAMANO_MINIMO, max=_TAMANO_MAXIMO,
            initial=self._tamano,
            name=nombre_de_etiqueta(_("Tamaño de letra:")))
        nombre_accesible(self.spin_tamano, self.spin_tamano.GetName())
        formulario.agregar_fila(
            self.vertical, self.rotulo_tamano, self.spin_tamano,
            numerico=True)

    def _enfocar(self):
        self.txt_texto.SetFocus()

    def _leer(self):
        return {"texto": self.txt_texto.GetValue(),
                "tamano": int(self.spin_tamano.GetValue())}


def pedir(padre, clave, opciones=None, valores=None):
    """Abre el cuadro del tipo y devuelve sus valores, o None si se cancela."""
    valores = valores or {}
    if clave == "pantalla":
        return _eleccion(
            padre, _("&Pantalla:"), _("Captura de pantalla"),
            "DialogoPantalla",
            opciones, valores.get("pantalla", ""),
            _("No hay pantallas para capturar."), "pantalla")
    if clave == "juego":
        return _con_valor(DialogoJuego(padre, opciones, valores))
    if clave in ("imagen", "multimedia"):
        return _con_valor(DialogoArchivo(padre, clave, valores))
    if clave == "texto":
        return _con_valor(DialogoTexto(padre, valores))
    if clave == "camara":
        valor = agregar_camara.pedir_camara(
            padre, opciones, valores.get("dispositivo", ""))
        return None if valor is None else {"dispositivo": valor}
    if clave == "ventana":
        valor = escena_captura_ventana.pedir_valor(
            padre, opciones, valores.get("ventana", ""))
        return None if valor is None else {"ventana": valor}
    return None


def pedir_fuente(padre, opciones):
    """Elige una fuente de otra escena por su nombre."""
    dialogo = DialogoEleccion(
        padre, _("Fuente de otra escena"), "DialogoFuente",
        _("&Fuente:"), tuple((nombre, nombre) for nombre in opciones or ()),
        vacio=_("No hay fuentes de otras escenas para agregar."))
    return _con_valor(dialogo)


def _eleccion(padre, etiqueta, titulo, nombre, opciones, actual, vacio,
              clave):
    dialogo = DialogoEleccion(
        padre, titulo, nombre, etiqueta, opciones, actual, vacio)
    elegido = _con_valor(dialogo)
    return None if elegido is None else {clave: elegido}


def _con_valor(dialogo):
    try:
        aceptado = dialogo.ShowModal() == wx.ID_OK
        return dialogo.valor() if aceptado else None
    finally:
        dialogo.Destroy()
