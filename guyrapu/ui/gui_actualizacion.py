# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana genérica de actualización con estado, progreso y cierre.

No sabe nada de yt-dlp ni de ningún origen concreto: quien la abre le
pone el título, le anuncia cada fase con `estado()` y le mueve la barra
con `progreso()`. No modal, se muestra con `Show()`.
"""

from __future__ import annotations

import threading

import wx

from guyrapu.core import diagnostico
from guyrapu.core.actualizacion import notas_legibles
from guyrapu.core.idioma import _
from guyrapu.ui import formulario, paleta, tema
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.espera_sonora import EsperaSonora
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta

logger = diagnostico.obtener_logger(__name__)

_SIN_TERMINAR = object()


class DialogoActualizacion(wx.Dialog):
    _espera_habilitada = True
    _espera_activa = False

    def __init__(self, parent, titulo):
        super().__init__(parent, title=titulo,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                         name="DialogoActualizacion")
        self._cerrado = False
        self._cancelado = threading.Event()
        self._accion = None

        panel = wx.Panel(self, name="PanelActualizacion")
        self.panel = panel
        vs = wx.BoxSizer(wx.VERTICAL)
        self._crear_estado_y_progreso(panel, vs)
        self._crear_novedades(panel, vs)
        self._crear_botones(panel, vs)

        formulario.ajustar_tamano(self, panel, vs)
        self.Centre()
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._al_cerrar)
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        try:
            self.btn_cerrar.SetFocus()
        except Exception as error:
            logger.debug("no se pudo enfocar el cierre: %s", error)

    def _crear_estado_y_progreso(self, panel, vs) -> None:
        self.txt_estado = wx.TextCtrl(
            panel, value="", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL,
            # Traductores: nombre del cuadro de estado.
            name=_("Estado"))
        self.txt_estado.SetMinSize(
            (380, 3 * self.txt_estado.GetCharHeight() + 12))
        # Traductores: nombre del cuadro de estado.
        nombre_accesible(self.txt_estado, _("Estado"))
        formulario.agregar_fila(vs, None, self.txt_estado)

        # Traductores: nombre de la barra de progreso.
        self.gauge = wx.Gauge(panel, range=100, name=_("Progreso"))
        # Traductores: nombre de la barra de progreso.
        nombre_accesible(self.gauge, _("Progreso"))
        formulario.agregar_fila(vs, None, self.gauge)
        self._espera = EsperaSonora(self)

    def _crear_novedades(self, panel, vs) -> None:
        self.txt_notas = wx.TextCtrl(
            panel, value="", style=wx.TE_MULTILINE | wx.TE_READONLY,
            # Traductores: nombre del cuadro de novedades.
            name=_("Novedades"))
        try:
            ancho60 = 60 * self.txt_notas.GetCharWidth()
        except Exception:
            ancho60 = -1
        try:
            alto_notas = 12 * self.txt_notas.GetCharHeight() + 12
        except Exception:
            alto_notas = -1
        self.txt_notas.SetMinSize((ancho60, alto_notas))
        # Traductores: nombre del cuadro de novedades.
        nombre_accesible(self.txt_notas, _("Novedades"))
        formulario.agregar_fila(vs, None, self.txt_notas)
        self.txt_notas.Hide()

    def _crear_botones(self, panel, vs) -> None:
        # Traductores: nombre del botón de acción; no se oye porque nace oculto.
        self.btn_accion = wx.Button(panel, wx.ID_ANY, "", name=_("Acción"))
        self.btn_accion.Hide()

        # Traductores: botón para cerrar la ventana.
        self.btn_cerrar = wx.Button(panel, wx.ID_CANCEL, _("&Cerrar"), name=_("Cerrar"))
        formulario.agregar_pie(vs, [self.btn_accion, self.btn_cerrar])

    @property
    def cerrado(self) -> bool:
        return self._cerrado

    @property
    def cancelado(self) -> threading.Event:
        return self._cancelado

    def Show(self, show=True):
        paleta.pintar_ventana(self)
        resultado = super().Show(show)
        if show:
            try:
                self.btn_cerrar.SetFocus()
            except Exception as error:
                logger.debug("no se pudo enfocar el cierre: %s", error)
        return resultado

    def estado(self, texto, sonido=_SIN_TERMINAR) -> None:
        self.txt_estado.SetValue(texto)
        anunciar(texto)
        if sonido is _SIN_TERMINAR:
            self._empezar_espera()
        else:
            self.terminar_espera(sonido)

    def _empezar_espera(self) -> None:
        if not self._espera_habilitada or self._espera_activa:
            return
        self._espera.empezar()
        self._espera_activa = True

    def terminar_espera(self, sonido) -> None:
        self._espera_habilitada = False
        self._espera_activa = False
        self._espera.terminar(sonido)

    def progreso(self, porcentaje) -> None:
        if porcentaje is None:
            self.gauge.Pulse()
            return
        valor = int(porcentaje)
        self.gauge.SetValue(valor)
        if valor in (0, 100):
            self.terminar_espera(None)

    def _reajustar(self) -> None:
        # Reparte el espacio y agranda o achica la ventana a su contenido,
        # para que todo control visible tenga alto mayor que cero y quede
        # dentro del área cliente. No toca el foco ni re-centra: el foco lo
        # dejan `ofrecer_accion` y `quitar_accion` como siempre.
        try:
            self.panel.Layout()
            self.Layout()
        except Exception as error:
            logger.debug("no se pudo repartir la ventana: %s", error)
        try:
            self.Fit()
        except Exception as error:
            logger.debug("no se pudo ajustar la ventana: %s", error)
        try:
            self.panel.Layout()
            self.Layout()
        except Exception as error:
            logger.debug("no se pudo repartir la ventana: %s", error)

    def notas(self, texto) -> None:
        limpio = notas_legibles(texto)
        self.txt_notas.SetValue(limpio)
        if limpio:
            self.txt_notas.Show()
            try:
                self.txt_notas.SetInsertionPoint(0)
                self.txt_notas.ShowPosition(0)
            except Exception as error:
                logger.debug("no se pudo llevar al inicio las novedades: %s", error)
        else:
            self.txt_notas.Hide()
        self._reajustar()

    def etiqueta_cerrar(self, etiqueta) -> None:
        self.btn_cerrar.SetLabel(etiqueta)
        self.btn_cerrar.SetName(nombre_de_etiqueta(etiqueta))
        self._reajustar()

    def ofrecer_accion(self, etiqueta, al_pulsar) -> None:
        self._accion = al_pulsar
        self.btn_accion.SetLabel(etiqueta)
        self.btn_accion.SetName(nombre_de_etiqueta(etiqueta))
        try:
            self.btn_accion.Unbind(wx.EVT_BUTTON)
        except Exception as error:
            logger.debug("no se pudo soltar la acción anterior: %s", error)
        self.btn_accion.Bind(
            wx.EVT_BUTTON, lambda _event: self._accion())
        self.btn_accion.Show()
        tema.boton_principal(self.btn_accion)
        self._reajustar()
        try:
            self.btn_accion.SetFocus()
        except Exception as error:
            logger.debug("no se pudo enfocar la acción: %s", error)
        self.terminar_espera(None)

    def quitar_accion(self) -> None:
        self._accion = None
        self.btn_accion.Hide()
        self._reajustar()
        self._espera_habilitada = True
        try:
            self.btn_cerrar.SetFocus()
        except Exception as error:
            logger.debug("no se pudo enfocar el cierre: %s", error)

    def en_hilo_principal(self, funcion, *args) -> None:
        def _envoltura():
            if self._cerrado:
                return
            funcion(*args)

        wx.CallAfter(_envoltura)

    def _al_cerrar(self, event) -> None:
        self._cerrado = True
        self._espera.detener()
        try:
            self._cancelado.set()
        except Exception as error:
            logger.debug("no se pudo avisar la cancelación: %s", error)
        try:
            self.Destroy()
        except Exception as error:
            logger.debug("no se pudo destruir la ventana: %s", error)
