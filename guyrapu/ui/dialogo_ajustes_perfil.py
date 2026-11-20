# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro con todos los ajustes de un perfil de OBS y su monitoreo.

No habla con OBS: recibe lo leído y devuelve un `AjustesPerfil` nuevo. El
perfil en modo Avanzado no muestra codificador, bitrate de vídeo ni preset;
en su lugar ofrece pasarlo a modo Sencillo.
"""

from __future__ import annotations

import dataclasses

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.obs import ajustes_perfil
from guyrapu.obs import textos_perfil
from guyrapu.ui import formulario, paleta, tema
from guyrapu.ui.accesibilidad import (
    ContadorAccesible,
    nombre_accesible,
)
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta

TEXTO_AVANZADO = N_(
    "Este perfil está en modo Avanzado. El codificador, la tasa de bits de vídeo "
    "y el preset se cambian pasándolo a modo Sencillo.")


class _Eleccion(wx.Choice):
    """Lista desplegable que guarda el valor y no el índice."""

    def __init__(self, padre, etiqueta, normalizar=None):
        super().__init__(padre, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(self, self.GetName())
        self._normalizar = normalizar or (lambda valor: valor)
        self._valores = ()

    def fijar_opciones(self, opciones):
        self._valores = tuple(valor for valor, _etiqueta in opciones)
        self.Set([etiqueta for _valor, etiqueta in opciones])

    def SetValue(self, valor):
        try:
            self.SetSelection(self._valores.index(self._normalizar(valor)))
        except ValueError:
            self.SetSelection(0 if self._valores else wx.NOT_FOUND)

    def GetValue(self):
        indice = self.GetSelection()
        if 0 <= indice < len(self._valores):
            return self._valores[indice]
        return self._valores[0] if self._valores else None


class DialogoAjustesPerfil(wx.Dialog):

    def __init__(self, padre, ajustes, nombre, avanzado=False,
                 personalizado=True, salidas=(), codificadores=None):
        super().__init__(
            padre, title=_("Ajustes del perfil {nombre}").format(nombre=nombre),
            name="DialogoAjustesPerfil")
        self._original = ajustes
        self._avanzado = bool(avanzado)
        self._personalizado = bool(personalizado)
        self._salidas = tuple(salidas) or (
            (ajustes.monitoreo_id, ajustes.monitoreo_nombre),)
        self._codificadores = (
            tuple(codificadores) if codificadores is not None
            else tuple(valor for valor, _etiqueta
                       in textos_perfil.CODIFICADORES))
        self._pasar = False
        self._crear(ajustes)
        paleta.pintar_ventana(self)
        self.Centre()
        wx.CallAfter(self.rad_orientacion.SetFocus)

    def _crear(self, ajustes):
        panel = wx.Panel(self, name="PanelAjustesPerfil")
        contenido = wx.BoxSizer(wx.VERTICAL)
        zona = wx.ScrolledWindow(panel, style=wx.TAB_TRAVERSAL | wx.VSCROLL)
        zona.SetScrollRate(0, 20)
        secciones = wx.BoxSizer(wx.VERTICAL)
        self._crear_video(zona, secciones, ajustes)
        self._crear_transmision(zona, secciones, ajustes)
        self._crear_grabacion(zona, secciones, ajustes)
        self._crear_audio(zona, secciones, ajustes)
        zona.SetSizer(secciones)
        zona.SetMinSize((-1, secciones.GetMinSize().height))
        contenido.Add(zona, 1, wx.EXPAND)
        self._crear_botones(panel, contenido)
        formulario.ajustar_tamano(self, panel, contenido)
        self.btn_guardar.SetDefault()
        tema.boton_principal(self.btn_guardar)

    def _eleccion(self, caja, zona, texto, normalizar=None):
        rotulo = wx.StaticText(zona, label=_(texto))
        control = (_Eleccion(zona, texto, normalizar) if normalizar
                   else _Eleccion(zona, texto))
        formulario.agregar_fila(caja, rotulo, control)
        return control

    def _numerico(self, caja, zona, texto, minimo, maximo, inicial):
        rotulo = wx.StaticText(zona, label=_(texto))
        control = ContadorAccesible(
            zona, min=minimo, max=maximo, initial=int(inicial),
            name=nombre_de_etiqueta(texto))
        formulario.agregar_fila(caja, rotulo, control, numerico=True)
        return control

    def _campo_texto(self, caja, zona, texto, valor, estilo=0):
        rotulo = wx.StaticText(zona, label=_(texto))
        control = wx.TextCtrl(
            zona, value=valor, style=estilo,
            name=nombre_de_etiqueta(texto))
        nombre_accesible(control, control.GetName())
        formulario.agregar_fila(caja, rotulo, control)
        return control

    def _crear_video(self, zona, contenido, ajustes):
        caja = formulario.agregar_seccion(contenido, zona, _("Vídeo"))
        vertical = ajustes.alto_lienzo > ajustes.ancho_lienzo
        self.rad_orientacion = wx.RadioBox(
            zona, label=_("Orientación"),
            choices=[_("Horizontal"), _("Vertical")], majorDimension=2,
            style=wx.RA_SPECIFY_ROWS, name=_("Orientación"))
        nombre_accesible(self.rad_orientacion, _("Orientación"))
        self.rad_orientacion.SetSelection(1 if vertical else 0)
        formulario.agregar_fila(caja, None, self.rad_orientacion)
        self.cho_lienzo = self._eleccion(caja, zona, _("&Lienzo:"))
        self.cho_salida = self._eleccion(caja, zona, _("&Salida:"))
        self._poner_resoluciones(vertical, (ajustes.ancho_lienzo,
                                            ajustes.alto_lienzo),
                                 (ajustes.ancho_salida,
                                  ajustes.alto_salida))
        self.cho_fps = self._eleccion(
            caja, zona, _("&Fotogramas por segundo:"), int)
        self.cho_fps.fijar_opciones(textos_perfil.opciones_fps())
        self.cho_fps.SetValue(ajustes.fps)
        if self._avanzado:
            self._crear_avanzado(zona, caja)
        else:
            self._crear_codificacion(zona, caja, ajustes)

    def _crear_codificacion(self, zona, caja, ajustes):
        self.cho_codificador = self._eleccion(caja, zona, _("&Codificador:"))
        self.cho_codificador.fijar_opciones(
            textos_perfil.opciones_codificador(self._codificadores))
        self.cho_codificador.SetValue(ajustes.codificador)
        self.sp_bitrate_video = self._numerico(
            caja, zona, _("Tasa de bits de vídeo (&kbps):"), 1, 100000,
            ajustes.bitrate_video)
        self.cho_preset = self._eleccion(caja, zona, _("Pr&eset:"))
        self._poner_presets(ajustes.codificador, ajustes.preset)

    def _crear_avanzado(self, zona, caja):
        self.txt_avanzado = wx.StaticText(zona, label=_(TEXTO_AVANZADO))
        formulario.agregar_fila(caja, None, self.txt_avanzado)
        self.btn_pasar_sencillo = wx.Button(
            zona, label=_("&Cambiar a modo Sencillo"),
            name=nombre_de_etiqueta(_("&Cambiar a modo Sencillo")))
        nombre_accesible(self.btn_pasar_sencillo,
                         self.btn_pasar_sencillo.GetName())
        self.btn_pasar_sencillo.Bind(wx.EVT_BUTTON, self._al_pasar_sencillo)
        formulario.agregar_fila(caja, None, self.btn_pasar_sencillo)

    def _crear_transmision(self, zona, contenido, ajustes):
        caja = formulario.agregar_seccion(contenido, zona, _("Transmisión"))
        estilo = 0 if self._personalizado else wx.TE_READONLY
        self.txt_servidor = self._campo_texto(
            caja, zona, _("Se&rvidor:"), ajustes.servidor, estilo)
        self.txt_clave = self._campo_texto(
            caja, zona, _("Cl&ave:"), ajustes.clave, wx.TE_PASSWORD)
        self.chk_dinamico = self._casilla(
            zona, _("Tasa de bits &dinámica"), ajustes.bitrate_dinamico)
        self.chk_reconectar = self._casilla(
            zona, _("Rec&onectar"), ajustes.reconectar)
        formulario.agregar_casillas(
            caja, (self.chk_dinamico, self.chk_reconectar))
        self.sp_espera = self._numerico(
            caja, zona, _("Espera de recone&xión:"), 0, 600,
            ajustes.espera_reconexion)
        self.sp_reintentos = self._numerico(
            caja, zona, _("Re&intentos:"), 0, 1000, ajustes.reintentos)

    def _crear_grabacion(self, zona, contenido, ajustes):
        caja = formulario.agregar_seccion(contenido, zona, _("Grabación"))
        self.txt_carpeta = self._campo_texto(
            caja, zona, _("Car&peta:"), ajustes.carpeta_grabacion)
        self.cho_formato = self._eleccion(caja, zona, _("For&mato:"))
        self.cho_formato.fijar_opciones(textos_perfil.opciones_formato())
        self.cho_formato.SetValue(ajustes.formato_grabacion)
        self.cho_calidad = self._eleccion(
            caja, zona, _("Calidad de &grabación:"))
        self.cho_calidad.fijar_opciones(textos_perfil.opciones_calidad())
        self.cho_calidad.SetValue(ajustes.calidad_grabacion)
        self.chk_buffer = self._casilla(
            zona, _("B&úfer de clips"), ajustes.buffer_clips)
        formulario.agregar_casillas(caja, (self.chk_buffer,))
        self.sp_segundos = self._numerico(
            caja, zona, _("&Tiempo del búfer:"), 0, 3600,
            ajustes.segundos_buffer)

    def _crear_audio(self, zona, contenido, ajustes):
        caja = formulario.agregar_seccion(contenido, zona, _("Audio"))
        self.cho_bitrate_audio = self._eleccion(
            caja, zona, _("Tasa de &bits de audio:"), int)
        self.cho_bitrate_audio.fijar_opciones(
            textos_perfil.opciones_bitrate_audio())
        self.cho_bitrate_audio.SetValue(ajustes.bitrate_audio)
        self.cho_muestreo = self._eleccion(
            caja, zona, _("Muestreo (H&z):"), int)
        self.cho_muestreo.fijar_opciones(textos_perfil.opciones_muestreo())
        self.cho_muestreo.SetValue(ajustes.muestreo)
        self.cho_canales = self._eleccion(caja, zona, _("Ca&nales:"))
        self.cho_canales.fijar_opciones(textos_perfil.opciones_canales())
        self.cho_canales.SetValue(ajustes.canales)
        self.cho_monitoreo = self._eleccion(
            caja, zona, _("Dispositivo de escuc&ha del monitoreo:"))
        self.cho_monitoreo.fijar_opciones(
            self._opciones_monitoreo(ajustes))
        self.cho_monitoreo.SetValue(ajustes.monitoreo_id)

    def _crear_botones(self, panel, contenido):
        self.btn_guardar = wx.Button(
            panel, wx.ID_OK, _("Guardar &y cerrar"),
            name=nombre_de_etiqueta(_("Guardar &y cerrar")))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("Cancelar y &volver"),
            name=nombre_de_etiqueta(_("Cancelar y &volver")))
        formulario.agregar_pie(contenido,
                               [self.btn_guardar, self.btn_cancelar])
        self._enlazar_eventos()

    def _casilla(self, padre, etiqueta, valor):
        control = wx.CheckBox(
            padre, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(control, control.GetName())
        control.SetValue(bool(valor))
        return control

    def _opciones_monitoreo(self, ajustes):
        opciones = list(self._salidas)
        if all(valor != ajustes.monitoreo_id for valor, _nombre in opciones):
            opciones.insert(0, (ajustes.monitoreo_id,
                                ajustes.monitoreo_nombre))
        return opciones

    def _poner_presets(self, codificador, elegido=None):
        opciones = textos_perfil.opciones_preset(codificador)
        self.cho_preset.fijar_opciones(opciones)
        if elegido is None:
            elegido = ajustes_perfil.preset_intermedio(codificador)
        self.cho_preset.SetValue(elegido)

    def _poner_resoluciones(self, vertical, lienzo, salida):
        lienzos = textos_perfil.opciones_resolucion(vertical, tuple(lienzo))
        self.cho_lienzo.fijar_opciones(
            [(valor, "%d × %d" % valor) for valor in lienzos])
        self.cho_lienzo.SetValue(lienzo)
        opciones = textos_perfil.opciones_salida(
            vertical, tuple(lienzo), tuple(salida))
        self.cho_salida.fijar_opciones(
            [(valor, "%d × %d" % valor) for valor in opciones])
        self.cho_salida.SetValue(
            salida if textos_perfil.cabe(tuple(salida), tuple(lienzo))
            else opciones[0])

    def _enlazar_eventos(self):
        self.rad_orientacion.Bind(wx.EVT_RADIOBOX,
                                  self._al_cambiar_orientacion)
        self.cho_lienzo.Bind(wx.EVT_CHOICE, self._al_cambiar_lienzo)
        if not self._avanzado:
            self.cho_codificador.Bind(wx.EVT_CHOICE,
                                      self._al_cambiar_codificador)
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._al_guardar)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._al_cancelar)

    def _al_cambiar_orientacion(self, _evento):
        vertical = self.rad_orientacion.GetSelection() == 1
        lienzo = textos_perfil.equivalente(
            self.cho_lienzo.GetValue(), vertical)
        salida = textos_perfil.equivalente(
            self.cho_salida.GetValue(), vertical)
        self._poner_resoluciones(vertical, lienzo, salida)

    def _al_cambiar_lienzo(self, _evento):
        vertical = self.rad_orientacion.GetSelection() == 1
        lienzo = self.cho_lienzo.GetValue()
        salida = self.cho_salida.GetValue()
        self._poner_resoluciones(vertical, lienzo, salida)

    def _al_cambiar_codificador(self, _evento):
        self._poner_presets(self.cho_codificador.GetValue())

    def _al_guardar(self, _evento):
        self.EndModal(wx.ID_OK)

    def _al_cancelar(self, _evento):
        self.EndModal(wx.ID_CANCEL)

    def _al_pasar_sencillo(self, _evento):
        self._pasar = True
        self.EndModal(wx.ID_OK)

    def pasar_a_sencillo_pedido(self) -> bool:
        return self._pasar

    def _resolucion(self, control, defecto):
        valor = control.GetValue()
        if not valor:
            return defecto
        return int(valor[0]), int(valor[1])

    def _monitoreo(self):
        elegido = self.cho_monitoreo.GetValue()
        for valor, nombre in self._salidas:
            if valor == elegido:
                return elegido, nombre
        return elegido, self._original.monitoreo_nombre

    def ajustes(self):
        """Devuelve el perfil con lo que quedó en cada control."""
        original = self._original
        lienzo = self._resolucion(
            self.cho_lienzo, (original.ancho_lienzo, original.alto_lienzo))
        salida = self._resolucion(
            self.cho_salida, (original.ancho_salida, original.alto_salida))
        if not textos_perfil.cabe(salida, lienzo):
            salida = lienzo
        monitoreo_id, monitoreo_nombre = self._monitoreo()
        cambios = dict(
            ancho_lienzo=lienzo[0], alto_lienzo=lienzo[1],
            ancho_salida=salida[0], alto_salida=salida[1],
            fps=self.cho_fps.GetValue() or original.fps,
            servidor=self.txt_servidor.GetValue(),
            clave=self.txt_clave.GetValue(),
            bitrate_audio=self.cho_bitrate_audio.GetValue()
            or original.bitrate_audio,
            bitrate_dinamico=self.chk_dinamico.GetValue(),
            reconectar=self.chk_reconectar.GetValue(),
            espera_reconexion=self.sp_espera.GetValue(),
            reintentos=self.sp_reintentos.GetValue(),
            carpeta_grabacion=self.txt_carpeta.GetValue(),
            formato_grabacion=self.cho_formato.GetValue()
            or original.formato_grabacion,
            calidad_grabacion=self.cho_calidad.GetValue()
            or original.calidad_grabacion,
            buffer_clips=self.chk_buffer.GetValue(),
            segundos_buffer=self.sp_segundos.GetValue(),
            muestreo=self.cho_muestreo.GetValue() or original.muestreo,
            canales=self.cho_canales.GetValue() or original.canales,
            monitoreo_id=monitoreo_id,
            monitoreo_nombre=monitoreo_nombre,
        )
        if not self._avanzado:
            cambios.update(
                codificador=self.cho_codificador.GetValue()
                or original.codificador,
                bitrate_video=self.sp_bitrate_video.GetValue(),
                preset=self.cho_preset.GetValue() or original.preset,
            )
        return dataclasses.replace(original, **cambios)
