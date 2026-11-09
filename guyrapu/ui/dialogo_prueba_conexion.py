# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los cuadros de la prueba de conexión: antes, durante y después.

Su única razón para cambiar es cómo se presenta la prueba. La prueba corre
en un hilo con las operaciones del panel y Cancelar dispara la parada.
"""

from __future__ import annotations

import threading
from dataclasses import replace

import wx

from guyrapu.core.idioma import _
from guyrapu.obs import perfiles_obs, prueba_conexion
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import boton, nombre_de_etiqueta
from guyrapu.youtube import youtube_api

_PROPIEDADES_TEXTO = wx.TE_MULTILINE | wx.TE_READONLY


def _boton(dialogo, etiqueta, manejador):
    control = boton(dialogo, etiqueta, nombre_de_etiqueta(etiqueta))
    control.Bind(wx.EVT_BUTTON, manejador)
    return control


def texto_resultado(resultado) -> str:
    """La frase del cuadro de resultado, según lo que aguantó la conexión."""
    if resultado.aguantaron is None:
        ultimo = resultado.ultimo
        if ultimo is None:
            texto = _("La prueba no llegó a medir ninguna tasa de bits.")
        else:
            texto = _(
                "Ninguna tasa de bits aguantó. En el último intento se perdió el "
                "{porcentaje} % de los cuadros por la red.").format(
                    porcentaje=ultimo.porcentaje)
    elif resultado.aguanta_tal_cual:
        texto = _("El perfil «{perfil}» aguantó con {tasa} kbps.").format(
            perfil=resultado.perfil, tasa=resultado.bitrate_perfil)
        if resultado.mayor and resultado.mayor > resultado.bitrate_perfil:
            texto += " " + _(
                "La conexión aguantó hasta {mayor} kbps.").format(
                    mayor=resultado.mayor)
        else:
            texto += " " + _("La conexión no aguantó una tasa de bits mayor.")
    else:
        texto = _(
            "El perfil «{perfil}» no aguantó con {tasa_perfil} kbps. "
            "Aguanta con {tasa} kbps.").format(
                perfil=resultado.perfil,
                tasa_perfil=resultado.bitrate_perfil,
                tasa=resultado.aguantaron)
    if resultado.errores:
        texto += " " + _("Quedó pendiente: {errores}").format(
            errores=" ".join(resultado.errores))
    return texto


class DialogoPruebaConexion(wx.Dialog):
    """El cuadro previo: qué se va a hacer y con qué perfil."""

    def __init__(self, padre, perfil, bitrate, segundos_maximos):
        super().__init__(padre, title=_("Probar la conexión"),
                         name="DialogoPruebaConexion")
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_detalle = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO, name=_("Detalle de la prueba"))
        nombre_accesible(self.txt_detalle, _("Detalle de la prueba"))
        self.txt_detalle.SetMinSize((-1, 130))
        self.txt_detalle.SetValue(_(
            "Se va a hacer un directo privado de prueba en YouTube, que nadie "
            "ve y que se borra al terminar. Se probará el perfil «{perfil}», "
            "con {tasa} kbps. La prueba tarda como mucho {segundos} "
            "segundos.").format(perfil=perfil, tasa=bitrate,
                                segundos=segundos_maximos))
        caja.Add(self.txt_detalle, 1, wx.EXPAND | wx.ALL, 10)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_empezar = _boton(self, _("&Empezar"), self._empezar)
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        self.btn_empezar.SetDefault()
        fila.Add(self.btn_empezar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        caja.Add(fila, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((480, -1))
        self.Centre()
        self.btn_empezar.SetFocus()

    def _empezar(self, _evento):
        self.EndModal(wx.ID_OK)

    def texto(self) -> str:
        return self.txt_detalle.GetValue()


class DialogoProgresoPruebaConexion(wx.Dialog):
    """El cuadro de la prueba en curso, con Cancelar para detenerla."""

    def __init__(self, padre, parada):
        super().__init__(padre, title=_("Probando la conexión"),
                         name="DialogoProgresoPruebaConexion")
        self._parada = parada
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_estado = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO, name=_("Estado de la prueba"))
        nombre_accesible(self.txt_estado, _("Estado de la prueba"))
        self.txt_estado.SetMinSize((-1, 90))
        caja.Add(self.txt_estado, 1, wx.EXPAND | wx.ALL, 10)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cancelar = _boton(self, _("&Cancelar"), self._cancelar)
        fila.Add(self.btn_cancelar, 0)
        caja.Add(fila, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((480, -1))
        self.Centre()
        self.btn_cancelar.SetFocus()

    def mostrar_bitrate(self, bitrate):
        frase = _("Probando la conexión a {tasa} kbps…").format(
            tasa=bitrate)
        self.txt_estado.SetValue(frase)
        anunciar(frase)

    def _cancelar(self, _evento):
        self._parada.set()
        self.btn_cancelar.Disable()


class DialogoResultadoPruebaConexion(wx.Dialog):
    """El cuadro de resultado y, si aguantó uno menor, si se guarda."""

    def __init__(self, padre, resultado):
        super().__init__(padre, title=_("Resultado de la prueba"),
                         name="DialogoResultadoPruebaConexion")
        self._resultado = resultado
        self._guardar = False
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_resultado = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO,
            name=_("Resultado de la prueba"))
        nombre_accesible(self.txt_resultado, _("Resultado de la prueba"))
        self.txt_resultado.SetMinSize((-1, 120))
        self.txt_resultado.SetValue(texto_resultado(resultado))
        caja.Add(self.txt_resultado, 1, wx.EXPAND | wx.ALL, 10)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        if resultado.puede_guardar:
            self.btn_guardar = _boton(self, _("&Guardar en el perfil"),
                                      self._al_guardar)
            self.btn_dejar = _boton(self, _("&Dejar como estaba"),
                                    self._cerrar)
            self.btn_guardar.SetDefault()
            fila.Add(self.btn_guardar, 0, wx.RIGHT, 6)
            fila.Add(self.btn_dejar, 0)
        else:
            self.btn_cerrar = _boton(self, _("&Cerrar"), self._cerrar)
            fila.Add(self.btn_cerrar, 0)
        caja.Add(fila, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((520, -1))
        self.Centre()
        self.txt_resultado.SetFocus()

    def _al_guardar(self, _evento):
        self._guardar = True
        self.EndModal(wx.ID_OK)

    def _cerrar(self, _evento):
        self.EndModal(wx.ID_CANCEL)

    def guardar(self) -> bool:
        return self._guardar

    def texto(self) -> str:
        return self.txt_resultado.GetValue()


class PruebaConexionPanel:
    """Coordina la prueba con el panel: hilo, cuadros, parada y guardado."""

    def __init__(self, ventana, en_hilo, cliente_obs, cliente_yt, hay_sesion,
                 refrescar, anunciar_texto):
        self._ventana = ventana
        self._en_hilo = en_hilo
        self._cliente_obs = cliente_obs
        self._cliente_yt = cliente_yt
        self._hay_sesion = hay_sesion
        self._refrescar = refrescar
        self._anunciar_texto = anunciar_texto

    def empezar(self):
        self._en_hilo(self._preparar, self._preparado)

    def _preparar(self):
        try:
            return prueba_conexion.preparar(self._cliente_obs,
                                            self._hay_sesion)
        except Exception as error:
            return error

    def _preparado(self, preparacion):
        if isinstance(preparacion, Exception):
            self._anunciar_texto(self._texto_fallo(preparacion), error=True)
            return
        cuadro = DialogoPruebaConexion(
            self._ventana, preparacion.perfil, preparacion.bitrate,
            preparacion.segundos_maximos)
        try:
            if cuadro.ShowModal() != wx.ID_OK:
                return
        finally:
            cuadro.Destroy()
        self._correr()

    def _correr(self):
        parada = threading.Event()
        progreso = DialogoProgresoPruebaConexion(self._ventana, parada)

        def al_bitrate(bitrate):
            wx.CallAfter(progreso.mostrar_bitrate, bitrate)

        def trabajo():
            try:
                return prueba_conexion.ejecutar(
                    self._cliente_obs, self._cliente_yt, parada=parada,
                    al_bitrate=al_bitrate)
            except Exception as error:
                return error

        try:
            self._en_hilo(trabajo, lambda resultado: self._terminada(
                progreso, resultado))
            progreso.ShowModal()
        finally:
            progreso.Destroy()

    def _terminada(self, progreso, resultado):
        try:
            progreso.EndModal(wx.ID_OK)
        except RuntimeError:
            pass
        self._refrescar()
        if isinstance(resultado, Exception):
            self._anunciar_texto(self._texto_fallo(resultado), error=True)
            return
        if resultado.cancelada:
            frase = _("Prueba cancelada. OBS quedó como estaba y la prueba "
                      "se borró de YouTube.")
            if resultado.errores:
                frase += " " + _("Quedó pendiente: {errores}").format(
                    errores=" ".join(resultado.errores))
            anunciar(frase)
            return
        cuadro = DialogoResultadoPruebaConexion(self._ventana, resultado)
        try:
            cuadro.ShowModal()
            if cuadro.guardar():
                self._guardar(resultado)
        finally:
            cuadro.Destroy()

    def _guardar(self, resultado):
        ajustes = replace(resultado.original,
                          bitrate_video=resultado.aguantaron)
        self._en_hilo(
            lambda: perfiles_obs.guardar_ajustes(
                self._cliente_obs, ajustes, resultado.perfil),
            lambda _valor: self._guardado(resultado))

    def _guardado(self, resultado):
        anunciar(_("Tasa de bits guardada en el perfil {nombre}: {tasa} "
                   "kbps.").format(nombre=resultado.perfil,
                                   tasa=resultado.aguantaron))
        self._refrescar()

    def _texto_fallo(self, error):
        if youtube_api.sesion_caducada(error):
            return youtube_api.mensaje_error_api(error)
        if isinstance(error, prueba_conexion.ErrorPruebaConexion):
            return str(error)
        return _("La prueba de conexión dio un error: {error}").format(
            error=error)
