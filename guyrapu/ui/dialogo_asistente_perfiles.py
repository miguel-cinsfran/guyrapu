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
from guyrapu.ui import formulario, paleta, tecla_escape, tema
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
        panel = wx.Panel(self, name="PanelAsistentePerfiles")
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_explicacion = wx.TextCtrl(
            panel, style=_PROPIEDADES_TEXTO,
            name=nombre_de_etiqueta(_("Cómo funciona")))
        nombre_accesible(self.txt_explicacion, self.txt_explicacion.GetName())
        self.txt_explicacion.SetValue(_(EXPLICACION))
        self.txt_explicacion.SetMinSize((-1, 90))
        formulario.agregar_fila(caja, None, self.txt_explicacion, hueco=0)
        self.casillas = {}
        casillas = []
        for clave, rotulo, marcada in CASILLAS:
            casilla = wx.CheckBox(
                panel, label=_(rotulo), name=nombre_de_etiqueta(_(rotulo)))
            nombre_accesible(casilla, casilla.GetName())
            casilla.SetValue(marcada)
            self.casillas[clave] = casilla
            casillas.append(casilla)
        self.chk_probar = wx.CheckBox(
            panel, label=_("Probar cada perfil con el e&quipo"),
            name=nombre_de_etiqueta(_("Probar cada perfil con el e&quipo")))
        nombre_accesible(self.chk_probar, self.chk_probar.GetName())
        self.chk_probar.SetValue(True)
        casillas.append(self.chk_probar)
        formulario.agregar_casillas(caja, casillas)
        self._fila_botones(panel, caja)
        formulario.ajustar_tamano(self, panel, caja)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        next(iter(self.casillas.values())).SetFocus()

    def _fila_botones(self, panel, caja):
        self.btn_preparar = _boton(panel, _("&Preparar"), self._al_preparar)
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        nombre_accesible(self.btn_cancelar, self.btn_cancelar.GetName())
        self.btn_preparar.SetDefault()
        tema.boton_principal(self.btn_preparar)
        formulario.agregar_pie(caja, [self.btn_preparar, self.btn_cancelar])

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
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoResumenAsistente(wx.Dialog):
    """Lo que quedó hecho, en un texto de solo lectura que recibe el foco."""

    def __init__(self, padre, texto):
        super().__init__(padre, title=_("Resumen de la preparación"),
                         name="DialogoResumenAsistente")
        panel = wx.Panel(self, name="PanelResumenAsistente")
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_resumen = wx.TextCtrl(
            panel, style=_PROPIEDADES_TEXTO,
            name=_("Resumen de la preparación"))
        nombre_accesible(self.txt_resumen, _("Resumen de la preparación"))
        self.txt_resumen.SetMinSize((-1, 160))
        self.txt_resumen.SetValue(texto)
        formulario.agregar_fila(caja, None, self.txt_resumen, hueco=0)
        self.btn_cerrar = _boton(panel, _("&Cerrar"), self._cerrar)
        self.btn_cerrar.SetDefault()
        formulario.agregar_pie(caja, [self.btn_cerrar])
        formulario.ajustar_tamano(self, panel, caja)
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.txt_resumen.SetFocus()

    def _cerrar(self, _evento):
        self.EndModal(wx.ID_OK)

    def _al_tecla(self, evento):
        if tecla_escape.es_escape(evento.GetKeyCode()):
            self._cerrar(evento)
            return
        evento.Skip()


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
