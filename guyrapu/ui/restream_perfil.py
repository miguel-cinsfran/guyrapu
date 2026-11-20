# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Diálogo para crear o editar un perfil de Restream (accesible).

Pide el nombre, la orientación, los destinos como casillas, la casilla de
YouTube de la sesión y, cuando corresponde, qué chat lee Guyrapu. La
validación es de `perfiles.validar`; quien lo abrió guarda con
`perfiles.guardar`.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _, ngettext
from guyrapu.restream import perfiles
from guyrapu.restream.perfiles import ORIENTACIONES, Perfil
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import mostrar_control, nombre_de_etiqueta


def _rotulo(padre, contenido, texto, crear_control):
    """Crea el rótulo antes que su control, para que Alt+letra lo enfoque."""
    rotulo = wx.StaticText(padre, label=texto)
    control = crear_control()
    control.SetName(nombre_de_etiqueta(texto))
    nombre_accesible(control, control.GetName())
    formulario.agregar_fila(contenido, rotulo, control, hueco=0)
    return rotulo, control


class DialogoPerfilRestream(wx.Dialog):

    def __init__(self, parent, perfil=None, canales=None, existentes=None,
                 sin_cuenta=False):
        titulo = (_("Nuevo perfil de Restream") if perfil is None
                  else _("Editar perfil de Restream"))
        super().__init__(parent, title=titulo,
                         name="DialogoPerfilRestream")
        self._perfil = perfil
        self._existentes = list(existentes or ())
        self._canales = list(canales or ())
        self._sin_cuenta = sin_cuenta
        self._ids_validos = {identificador for identificador, _texto
                             in self._canales}
        self._resultado = None
        self._casillas = []
        self._textos = {}
        self._nota_sobrantes = None
        self._crear_ui()
        paleta.pintar_ventana(self)
        self.Centre()

    def _crear_ui(self):
        panel = wx.Panel(self, name="PanelPerfilRestream")
        self._panel = panel
        contenido = wx.BoxSizer(wx.VERTICAL)
        self._agregar_nombre(panel, contenido)
        self._agregar_orientacion(panel, contenido)
        self._agregar_destinos(panel, contenido)
        self._agregar_youtube_y_chat(panel, contenido)

        etiqueta_guardar = _("&Guardar")
        self.btn_guardar = wx.Button(
            panel, wx.ID_OK, etiqueta_guardar,
            name=nombre_de_etiqueta(etiqueta_guardar))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("C&ancelar"), name=_("Cancelar"))
        nombre_accesible(self.btn_guardar, self.btn_guardar.GetName())
        nombre_accesible(self.btn_cancelar, self.btn_cancelar.GetName())
        formulario.agregar_pie(contenido,
                               [self.btn_guardar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, contenido)

        self.btn_guardar.SetDefault()
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._guardar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda evento: self.EndModal(wx.ID_CANCEL))
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)

    def _agregar_nombre(self, zona, contenido):
        valor = self._perfil.nombre if self._perfil is not None else ""
        _rotulo_nombre, self.txt_nombre = _rotulo(
            zona, contenido, _("&Nombre:"),
            lambda: wx.TextCtrl(zona, value=valor))

    def _agregar_orientacion(self, zona, contenido):
        _rotulo_orientacion, self.cho_orientacion = _rotulo(
            zona, contenido, _("&Orientación:"),
            lambda: wx.Choice(zona, choices=[
                _("Horizontal"), _("Vertical"),
                _("Horizontal y vertical a la vez")]))
        orientacion = (self._perfil.orientacion if self._perfil is not None
                       else ORIENTACIONES[0])
        self.cho_orientacion.SetSelection(ORIENTACIONES.index(orientacion))

    def _agregar_destinos(self, panel, contenido):
        interior, caja_sizer = formulario.agregar_seccion_con_caja(
            contenido, panel, _("Destinos"))
        caja = caja_sizer.GetStaticBox()
        self._caja_canales = caja_sizer
        casillas = []
        for identificador, texto in self._canales:
            casilla = wx.CheckBox(caja, label=texto.replace("&", "&&"),
                                  name=texto)
            nombre_accesible(casilla, texto)
            if (self._perfil is not None
                    and identificador in self._perfil.canales):
                casilla.SetValue(True)
            casilla.Bind(wx.EVT_CHECKBOX,
                         lambda evento: self._actualizar_chat())
            self._casillas.append((identificador, casilla))
            self._textos[identificador] = texto
            casillas.append(casilla)
        if casillas:
            formulario.agregar_casillas(interior, casillas, hueco=0)
        else:
            texto = (_("Sin cuenta de Restream. Conéctala en la pestaña "
                       "Cuenta.") if self._sin_cuenta else _(
                 "No hay destinos. Agrégalos en la pestaña Destinos."))
            interior.Add(wx.StaticText(caja, label=texto), 0, wx.EXPAND)
        self._nota_sobrantes = self._crear_nota_sobrantes(panel, contenido)

    def _crear_nota_sobrantes(self, panel, contenido):
        if self._perfil is None or self._sin_cuenta:
            return None
        sobrantes = [identificador for identificador in self._perfil.canales
                     if identificador not in self._ids_validos]
        if not sobrantes:
            return None
        texto = ngettext(
            "Hay {n} destino del perfil de Restream que ya no está en "
            "Restream. Se eliminará al guardar.",
            "Hay {n} destinos del perfil de Restream que ya no están en "
            "Restream. Se eliminarán al guardar.",
            len(sobrantes)).format(n=len(sobrantes))
        nota = wx.StaticText(panel, label=texto)
        contenido.Add(nota, 0, wx.EXPAND)
        return nota

    def _agregar_youtube_y_chat(self, panel, contenido):
        perfil = self._perfil
        texto_youtube = _("YouTube, el canal de tu sesión de Google")
        self.chk_youtube = wx.CheckBox(
            panel, label=_("&YouTube, el canal de tu sesión de Google"),
            name=texto_youtube)
        nombre_accesible(self.chk_youtube, texto_youtube)
        self.chk_youtube.SetValue(bool(perfil.youtube)
                                  if perfil is not None else False)
        self.chk_youtube.Bind(
            wx.EVT_CHECKBOX, lambda evento: self._actualizar_chat())
        formulario.agregar_casillas(contenido, [self.chk_youtube], hueco=0)

        self._rotulo_chat = wx.StaticText(
            panel, label=_("&Chat que lee Guyrapu:"))
        self.cho_chat = wx.Choice(
            panel, choices=[_("YouTube y TikTok"), _("Solo YouTube"),
                            _("Solo TikTok")],
            name=_("Chat que lee Guyrapu"))
        nombre_accesible(self.cho_chat, _("Chat que lee Guyrapu"))
        chat = perfil.chat if perfil is not None else "ambos"
        self.cho_chat.SetSelection({"ambos": 0, "tiktok": 2}.get(chat, 1))
        formulario.agregar_fila(contenido, self._rotulo_chat, self.cho_chat,
                                hueco=0)
        self._actualizar_chat()

    def _actualizar_chat(self):
        youtube = self.chk_youtube.GetValue()
        tiktok = any(
            casilla.GetValue()
            and self._textos[identificador].startswith("TikTok:")
            for identificador, casilla in self._casillas)
        for control in (self._rotulo_chat, self.cho_chat):
            mostrar_control(control, youtube and tiktok, self.chk_youtube)
        self._panel.Layout()

    def perfil(self):
        return self._resultado

    def _armar_perfil(self):
        elegidos = tuple(identificador for identificador, casilla
                         in self._casillas if casilla.GetValue())
        youtube = self.chk_youtube.GetValue()
        chat = ""
        if youtube and self.cho_chat.IsShown():
            chat = ("ambos", "youtube", "tiktok")[
                self.cho_chat.GetSelection()]
        directo = dict(self._perfil.directo) if self._perfil is not None else {}
        return Perfil(
            nombre=self.txt_nombre.GetValue().strip(),
            canales=elegidos,
            orientacion=ORIENTACIONES[self.cho_orientacion.GetSelection()],
            youtube=youtube,
            chat=chat,
            directo=directo,
        )

    def _guardar(self, _evento):
        perfil = self._armar_perfil()
        mensajes = perfiles.validar(perfil, self._existentes)
        if mensajes:
            anunciar(" ".join(mensajes))
            self._enfocar_primer_problema(perfil)
            return
        self._resultado = perfil
        self.EndModal(wx.ID_OK)

    def _enfocar_primer_problema(self, perfil):
        nombre = (perfil.nombre or "").strip().casefold()
        repetido = any(existente.nombre.strip().casefold() == nombre
                       for existente in self._existentes)
        if not nombre or nombre == "youtube" or repetido:
            self.txt_nombre.SetFocus()
        elif not perfil.canales and not perfil.youtube:
            self.chk_youtube.SetFocus()
        elif perfil.orientacion == "ambas" and not perfil.youtube:
            self.chk_youtube.SetFocus()
        elif self._casillas:
            self._casillas[0][1].SetFocus()
        else:
            self.chk_youtube.SetFocus()

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoNombrePerfil(wx.Dialog):
    """Un solo campo para cambiar el nombre de un perfil de Restream."""

    def __init__(self, parent, nombre):
        super().__init__(parent, title=_("Cambiar nombre"), size=(440, 200),
                         name="DialogoNombrePerfil")
        self._resultado = None
        self._crear_ui(nombre)
        paleta.pintar_ventana(self)
        self.Centre()

    def _crear_ui(self, nombre):
        vs = wx.BoxSizer(wx.VERTICAL)
        contenido = wx.BoxSizer(wx.VERTICAL)
        _rotulo(self, contenido, _("&Nombre:"),
                lambda: wx.TextCtrl(
                    self, value=nombre, style=wx.TE_PROCESS_ENTER))
        vs.Add(contenido, 1, wx.EXPAND)

        fila = wx.BoxSizer(wx.HORIZONTAL)
        etiqueta_guardar = _("&Guardar")
        self.btn_guardar = wx.Button(
            self, wx.ID_OK, etiqueta_guardar,
            name=nombre_de_etiqueta(etiqueta_guardar))
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        for boton in (self.btn_guardar, self.btn_cancelar):
            nombre_accesible(boton, boton.GetName())
        fila.Add(self.btn_guardar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        vs.Add(fila, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(vs)
        self.btn_guardar.SetDefault()
        self.btn_guardar.Bind(
            wx.EVT_BUTTON, lambda evento: self._aceptar())
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda evento: self.EndModal(wx.ID_CANCEL))
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.txt_nombre.SetFocus()

    def nombre(self):
        return self._resultado

    def _aceptar(self, _evento=None):
        self._resultado = self.txt_nombre.GetValue().strip()
        self.EndModal(wx.ID_OK)

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)
