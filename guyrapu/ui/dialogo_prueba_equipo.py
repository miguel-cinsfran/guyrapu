# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los cuadros de la prueba del equipo: antes, durante y después.

Su única razón para cambiar es cómo se presenta la prueba. La prueba corre
en un hilo con las operaciones del panel y Cancelar dispara la parada.
"""

from __future__ import annotations

import threading

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.obs import (escalones_equipo, lienzo_vertical, perfiles_obs,
                         prueba_equipo, prueba_vertical)
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import boton, nombre_de_etiqueta

_PROPIEDADES_TEXTO = wx.TE_MULTILINE | wx.TE_READONLY

ROTULO_VERTICAL = N_(
    "Incluir el lienzo &vertical, para transmitir en horizontal y vertical "
    "a la vez")
DETALLE_VERTICAL = N_(
    "Si incluyes el lienzo vertical, se graban los dos y se borran las dos "
    "grabaciones.")


def _boton(dialogo, etiqueta, manejador):
    control = boton(dialogo, etiqueta, nombre_de_etiqueta(etiqueta))
    control.Bind(wx.EVT_BUTTON, manejador)
    return control


def _texto_detalle(perfil, ajustes, segundos) -> str:
    return _(
        "Se va a probar el perfil «{perfil}» con {ajustes}. La prueba "
        "tarda como mucho {segundos} segundos.").format(
            perfil=perfil, ajustes=escalones_equipo.describir(ajustes),
            segundos=segundos)


def texto_resultado(resultado) -> str:
    """La frase del cuadro de resultado, según lo que aguantó."""
    ultimo = resultado.ultimo
    if resultado.aguantaron is None:
        if ultimo is None:
            texto = _("Ningún escalón llegó a medirse.")
        else:
            texto = _(
                "Ningún ajuste aguantó. En el último escalón se perdió el "
                "{dibujar} % de los fotogramas al dibujar y el {codificar} % "
                "al codificar.").format(dibujar=ultimo.porcentaje_dibujar,
                                        codificar=ultimo.porcentaje_codificar)
    else:
        porcentajes = _(
            "Se perdió el {dibujar} % de los fotogramas al dibujar y el "
            "{codificar} % al codificar.").format(
                dibujar=ultimo.porcentaje_dibujar,
                codificar=ultimo.porcentaje_codificar)
        if resultado.aguanta_tal_cual:
            texto = _("El perfil «{perfil}» aguantó tal como está. "
                      "{porcentajes}").format(perfil=resultado.perfil,
                                              porcentajes=porcentajes)
        else:
            cambios = escalones_equipo.diferencias(resultado.original,
                                                   resultado.aguantaron)
            texto = _("El perfil «{perfil}» aguantó con estos cambios: "
                      "{cambios} {porcentajes}").format(
                          perfil=resultado.perfil, cambios=cambios,
                          porcentajes=porcentajes)
    if resultado.grabaciones:
        # Traductores: {rutas} son las rutas de los archivos que quedaron.
        texto += " " + _(
            "No se pudo eliminar la grabación de la prueba: {rutas}."
        ).format(rutas=", ".join(resultado.grabaciones))
    return texto


class DialogoPruebaEquipo(wx.Dialog):
    """El cuadro previo: qué perfil y qué ajustes se van a probar."""

    def __init__(self, padre, perfil, ajustes, segundos_maximos,
                 vertical=False):
        super().__init__(padre, title=_("Probar el equipo"),
                         name="DialogoPruebaEquipo")
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_detalle = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO, name=_("Detalle de la prueba"))
        nombre_accesible(self.txt_detalle, _("Detalle de la prueba"))
        self.txt_detalle.SetMinSize((-1, 120))
        detalle = _texto_detalle(perfil, ajustes, segundos_maximos)
        self.chk_vertical = None
        if vertical:
            self.chk_vertical = wx.CheckBox(
                self, label=_(ROTULO_VERTICAL),
                name=nombre_de_etiqueta(_(ROTULO_VERTICAL)))
            nombre_accesible(self.chk_vertical, self.chk_vertical.GetName())
            detalle += " " + _(DETALLE_VERTICAL)
        self.txt_detalle.SetValue(detalle)
        caja.Add(self.txt_detalle, 1, wx.EXPAND | wx.ALL, 10)
        if self.chk_vertical is not None:
            caja.Add(self.chk_vertical, 0, wx.LEFT | wx.RIGHT, 10)
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
        self.SetMinSize((460, -1))
        self.Centre()
        self.btn_empezar.SetFocus()

    def _empezar(self, _evento):
        self.EndModal(wx.ID_OK)

    def incluir_vertical(self) -> bool:
        return bool(self.chk_vertical is not None
                    and self.chk_vertical.IsChecked())

    def texto(self) -> str:
        return self.txt_detalle.GetValue()


class DialogoProgresoPrueba(wx.Dialog):
    """El cuadro de la prueba en curso, con Cancelar para detenerla."""

    def __init__(self, padre, parada):
        super().__init__(padre, title=_("Probando el equipo"),
                         name="DialogoProgresoPrueba")
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
        self.SetMinSize((460, -1))
        self.Centre()
        self.btn_cancelar.SetFocus()

    def mostrar_paso(self, ajustes):
        # Traductores: {ajustes} son el codificador, los fotogramas por
        # segundo y la salida que se están probando.
        frase = _("Probando {ajustes}…").format(
            ajustes=escalones_equipo.describir(ajustes))
        self.txt_estado.SetValue(frase)
        anunciar(frase)

    def _cancelar(self, _evento):
        self._parada.set()
        self.btn_cancelar.Disable()


class DialogoResultadoPrueba(wx.Dialog):
    """El cuadro de resultado y, si hubo cambios, si se guardan."""

    def __init__(self, padre, resultado):
        super().__init__(padre, title=_("Resultado de la prueba"),
                         name="DialogoResultadoPrueba")
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
        if resultado.aguantaron is None or resultado.aguanta_tal_cual:
            self.btn_cerrar = _boton(self, _("&Cerrar"), self._cerrar)
            fila.Add(self.btn_cerrar, 0)
        else:
            self.btn_guardar = _boton(self, _("&Guardar en el perfil"),
                                      self._al_guardar)
            self.btn_dejar = _boton(self, _("&Dejar como estaba"),
                                    self._cerrar)
            self.btn_guardar.SetDefault()
            fila.Add(self.btn_guardar, 0, wx.RIGHT, 6)
            fila.Add(self.btn_dejar, 0)
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


class PruebaEquipoPanel:
    """Coordina la prueba con el panel: hilo, cuadros, parada y guardado."""

    def __init__(self, ventana, en_hilo, cliente, refrescar, anunciar_texto):
        self._ventana = ventana
        self._en_hilo = en_hilo
        self._cliente = cliente
        self._refrescar = refrescar
        self._anunciar_texto = anunciar_texto

    def empezar(self):
        self._en_hilo(self._preparar, self._preparado)

    def _preparar(self):
        try:
            preparacion = prueba_equipo.preparar(self._cliente)
            hay_vertical = lienzo_vertical.detectar(self._cliente) is not None
            return preparacion, hay_vertical
        except Exception as error:
            return error

    def _preparado(self, preparacion):
        if isinstance(preparacion, Exception):
            self._anunciar_texto(self._texto_fallo(preparacion), error=True)
            return
        preparacion, hay_vertical = preparacion
        cuadro = DialogoPruebaEquipo(
            self._ventana, preparacion.perfil, preparacion.ajustes,
            preparacion.segundos_maximos, vertical=hay_vertical)
        incluir_vertical = False
        try:
            if cuadro.ShowModal() != wx.ID_OK:
                return
            incluir_vertical = cuadro.incluir_vertical()
        finally:
            cuadro.Destroy()
        self._correr(preparacion, incluir_vertical)

    def _correr(self, preparacion, incluir_vertical=False):
        parada = threading.Event()
        progreso = DialogoProgresoPrueba(self._ventana, parada)
        cliente = (prueba_vertical.ClienteVertical(self._cliente)
                   if incluir_vertical else self._cliente)

        def al_escalon(ajustes):
            wx.CallAfter(progreso.mostrar_paso, ajustes)

        def trabajo():
            try:
                return prueba_equipo.ejecutar(
                    cliente, parada=parada,
                    disponibles=preparacion.disponibles,
                    al_escalon=al_escalon)
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
            anunciar(_("Prueba cancelada. OBS quedó como estaba."))
            return
        cuadro = DialogoResultadoPrueba(self._ventana, resultado)
        try:
            cuadro.ShowModal()
            if cuadro.guardar():
                self._guardar(resultado)
        finally:
            cuadro.Destroy()

    def _guardar(self, resultado):
        self._en_hilo(
            lambda: perfiles_obs.guardar_ajustes(
                self._cliente, resultado.aguantaron, resultado.perfil),
            lambda _valor: self._guardado(resultado.perfil))

    def _guardado(self, perfil):
        anunciar(_("Ajustes guardados en el perfil {perfil}.").format(
            perfil=perfil))
        self._refrescar()

    def _texto_fallo(self, error):
        if isinstance(error, prueba_equipo.ErrorPruebaEquipo):
            return str(error)
        return _("La prueba dio un error: {error} OBS quedó como estaba.").format(
            error=error)
