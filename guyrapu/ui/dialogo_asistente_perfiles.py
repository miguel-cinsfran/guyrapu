# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los cuadros del asistente de perfiles de OBS y su coordinación.

Su única razón para cambiar es cómo se pregunta, se anuncia y se resume la
preparación de perfiles. El recorrido vive en `asistente_perfiles`; acá se
abre en un hilo con las operaciones del panel y Cancelar dispara la parada.
"""

from __future__ import annotations

import threading

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.obs import asistente_perfiles
from guyrapu.restream import transmitir
from guyrapu.ui import paleta
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta
from guyrapu.ui.ventana_espera import VentanaEspera

_PROPIEDADES_TEXTO = wx.TE_MULTILINE | wx.TE_READONLY

EXPLICACION = N_(
    "Guyrapu crea perfiles nuevos con el mejor codificador de este equipo, "
    "los prueba y los deja asignados. Tus perfiles no se tocan. Puede tardar "
    "unos minutos.")

CASILLAS = (
    ("perfil_horizontal", N_("&Transmitir en horizontal (YouTube)"), True),
    ("perfil_vertical", N_("Transmitir en &vertical (TikTok)"), True),
    ("perfil_grabar", N_("&Grabar"), False),
)

SIN_USO = N_("Marca al menos una de las tres primeras casillas.")

MENSAJE_CANCELADO = N_("Preparación cancelada. No se creó ningún perfil.")


def _boton(dialogo, etiqueta, manejador):
    control = wx.Button(dialogo, label=etiqueta,
                        name=nombre_de_etiqueta(etiqueta))
    nombre_accesible(control, control.GetName())
    control.Bind(wx.EVT_BUTTON, manejador)
    return control


class DialogoAsistentePerfiles(wx.Dialog):
    """Qué se va a preparar: los tres usos y si se prueba el equipo."""

    def __init__(self, padre):
        super().__init__(padre, title=_("Preparar perfiles de OBS"),
                         name="DialogoAsistentePerfiles")
        self._crear_controles()
        paleta.pintar_ventana(self)
        self.Centre()

    def _crear_controles(self):
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_explicacion = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO,
            name=nombre_de_etiqueta(_("Cómo funciona")))
        nombre_accesible(self.txt_explicacion, self.txt_explicacion.GetName())
        self.txt_explicacion.SetValue(_(EXPLICACION))
        self.txt_explicacion.SetMinSize((-1, 70))
        caja.Add(self.txt_explicacion, 0, wx.EXPAND | wx.ALL, 8)
        self.casillas = {}
        for clave, rotulo, marcada in CASILLAS:
            casilla = wx.CheckBox(
                self, label=_(rotulo), name=nombre_de_etiqueta(_(rotulo)))
            nombre_accesible(casilla, casilla.GetName())
            casilla.SetValue(marcada)
            self.casillas[clave] = casilla
            caja.Add(casilla, 0, wx.ALL, 6)
        self.chk_probar = wx.CheckBox(
            self, label=_("Probar cada perfil con el e&quipo"),
            name=nombre_de_etiqueta(_("Probar cada perfil con el e&quipo")))
        nombre_accesible(self.chk_probar, self.chk_probar.GetName())
        self.chk_probar.SetValue(True)
        caja.Add(self.chk_probar, 0, wx.ALL, 6)
        caja.Add(self._fila_botones(), 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((480, -1))
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        next(iter(self.casillas.values())).SetFocus()

    def _fila_botones(self):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_preparar = _boton(self, _("&Preparar"), self._al_preparar)
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        nombre_accesible(self.btn_cancelar, self.btn_cancelar.GetName())
        self.btn_preparar.SetDefault()
        fila.Add(self.btn_preparar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        return fila

    def usos(self):
        """Las claves de los tres usos que quedaron marcadas."""
        return [clave for clave, casilla in self.casillas.items()
                if casilla.GetValue()]

    def probar(self) -> bool:
        return self.chk_probar.GetValue()

    def eleccion(self):
        return self.usos(), self.probar()

    def _al_preparar(self, _evento):
        if not self.usos():
            anunciar(_(SIN_USO))
            next(iter(self.casillas.values())).SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _al_tecla(self, evento):
        if evento.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        evento.Skip()


class DialogoResumenAsistente(wx.Dialog):
    """Lo que quedó hecho, en un texto de solo lectura que recibe el foco."""

    def __init__(self, padre, texto):
        super().__init__(padre, title=_("Resumen de la preparación"),
                         name="DialogoResumenAsistente")
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_resumen = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO,
            name=_("Resumen de la preparación"))
        nombre_accesible(self.txt_resumen, _("Resumen de la preparación"))
        self.txt_resumen.SetMinSize((-1, 160))
        self.txt_resumen.SetValue(texto)
        caja.Add(self.txt_resumen, 1, wx.EXPAND | wx.ALL, 10)
        self.btn_cerrar = _boton(self, _("&Cerrar"), self._cerrar)
        self.btn_cerrar.SetDefault()
        caja.Add(self.btn_cerrar, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((540, -1))
        self.Centre()
        self.txt_resumen.SetFocus()

    def _cerrar(self, _evento):
        self.EndModal(wx.ID_OK)


class AsistentePerfilesPanel:
    """Coordina el asistente con la pestaña: hilo, cuadros y parada."""

    def __init__(self, ventana, operaciones, cliente, config, al_terminar):
        self._ventana = ventana
        self._operaciones = operaciones
        self._cliente = cliente
        self._config = dict(config or {})
        self._al_terminar = al_terminar

    def empezar(self):
        dialogo = DialogoAsistentePerfiles(self._ventana)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return
            usos, probar = dialogo.eleccion()
        finally:
            dialogo.Destroy()
        if not usos:
            return
        self._correr(usos, probar)

    def _correr(self, usos, probar):
        parada = threading.Event()
        progreso = VentanaEspera(
            self._ventana, _("Preparando perfiles de OBS"),
            _("Preparando los perfiles…"), parada)

        def trabajo():
            try:
                return asistente_perfiles.preparar(
                    self._cliente(), usos, probar=probar, parada=parada,
                    anunciar=lambda texto: wx.CallAfter(
                        progreso.estado, texto),
                    anteriores=self._anteriores())
            except Exception as error:
                return error

        try:
            self._operaciones.en_hilo(
                trabajo, lambda resultado: self._terminado(
                    progreso, resultado))
            progreso.ShowModal()
        finally:
            progreso.Destroy()

    def _anteriores(self):
        return {clave: self._config.get(clave, "") or ""
                for clave, _base, _vertical in asistente_perfiles.USOS}

    def _terminado(self, progreso, resultado):
        if isinstance(resultado, Exception):
            self._terminar_en(progreso, str(resultado), error=True)
            return
        if resultado.cancelada:
            self._terminar_en(progreso, _(MENSAJE_CANCELADO))
            return
        try:
            progreso.EndModal(wx.ID_OK)
        except RuntimeError:
            pass
        self._mostrar_resumen(resultado)
        self._al_terminar(resultado)

    def _terminar_en(self, progreso, texto, error=False):
        try:
            progreso.terminar(texto, error=error)
        except RuntimeError:
            anunciar(texto)

    def _sin_restream(self):
        destino = str(self._config.get("transmision_destino") or "")
        return not transmitir.es_restream(destino)

    def _mostrar_resumen(self, resultado):
        lineas = asistente_perfiles.lineas_resumen(
            resultado, tiktok_sin_restream=self._sin_restream())
        dialogo = DialogoResumenAsistente(self._ventana, "\n".join(lineas))
        try:
            dialogo.ShowModal()
        finally:
            dialogo.Destroy()
