# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Bloque de la voz secundaria de la página Voces.

Dueño de sus controles, de su motor, de cómo se cargan las voces y de cómo se
guardan. La página Voces le pasa las voces del motor principal y las de Windows,
y le avisa cuándo cambia el motor principal. La prueba de voz la dispara hacia
la página, que es dueña del `PruebaVoz`.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui.accesibilidad import ContadorAccesible
from guyrapu.ui.gui import caja_de_grupo
from guyrapu.ui.preferencias_comun import fila_label
from guyrapu.ui.tema import _T, _tc
from guyrapu.voice import escala_voz
from guyrapu.voice import motores

_IGUAL_PRINCIPAL = N_("Igual que la voz principal")
_IGUAL_RESPALDO = N_("Igual que el respaldo de la voz principal")
_NO_HAY_VOCES = N_("(no hay voces instaladas: usa Administrar voces)")


def _porcentaje_de_volumen(config) -> int:
    try:
        return max(0, min(100, int(round(
            float(config.get("volumen_secundaria", 1.0)) * 100))))
    except (TypeError, ValueError):
        return 100


class BloqueVozSecundaria:
    """Motor, voz, velocidad, volumen, prueba y respaldo de la voz secundaria."""

    def __init__(self, config, al_probar):
        self._config = config
        self._al_probar = al_probar
        self._voces = []
        self._voces_principales = []
        self._voces_respaldo = []
        self._motor_principal = "sapi"
        self._motor = ""

    def construir(self, parent, voces, voces_respaldo, motor_principal):
        box, padre = caja_de_grupo(parent, _("Voz secundaria"))
        self._voces_principales = list(voces or ())
        self._voces_respaldo = list(voces_respaldo or ())
        self._motor_principal = motor_principal
        self._motor = self._motor_guardado()
        self._voces = (self._voces_principales if not self._motor
                       else motores.listar_voces(self._motor))

        box.Add(self._crear_motor(padre), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        box.Add(self._crear_voz(padre), 0, wx.LEFT | wx.RIGHT, 10)
        box.Add(self._crear_ajustes(padre), 0, wx.LEFT | wx.RIGHT, 10)
        box.Add(self._crear_probar(padre), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        box.Add(self._crear_respaldo(padre), 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self._actualizar_respaldo()
        return box

    def _opciones_motor(self) -> list[tuple[str, str]]:
        opciones = [("", _(_IGUAL_PRINCIPAL))]
        for motor in motores.MOTORES:
            if motor != "elevenlabs":
                opciones.append((motor, _(motores.NOMBRES[motor])))
        return opciones

    def _motor_guardado(self) -> str:
        guardado = self._config.get("motor_secundaria") or ""
        validos = [motor for motor, _texto in self._opciones_motor()]
        return guardado if guardado in validos else ""

    def _crear_motor(self, padre):
        fila = wx.BoxSizer(wx.VERTICAL)
        fila.Add(fila_label(padre, _("Motor de vo&z:")), 0, wx.BOTTOM, 6)
        opciones = self._opciones_motor()
        self.cho_motor = wx.Choice(
            padre, choices=[texto for _motor, texto in opciones],
            name=_("Motor de la voz secundaria"))
        _tc(self.cho_motor)
        self.cho_motor.SetSelection(
            next((indice for indice, (motor, _texto) in enumerate(opciones)
                  if motor == self._motor), 0))
        self.cho_motor.Bind(wx.EVT_CHOICE, self._on_motor_cambiado)
        fila.Add(self.cho_motor, 0, wx.EXPAND | wx.BOTTOM, 6)
        return fila

    def _on_motor_cambiado(self, event) -> None:
        # Cambiar de motor no anuncia nada: el lector ya lee el valor del
        # combinado al recorrerlo.
        self._motor = self._motor_elegido()
        if self._motor:
            self.recargar_voces(motores.listar_voces(self._motor))
        else:
            self.recargar_voces(self._voces_principales)
        self._actualizar_respaldo()

    def _motor_elegido(self) -> str:
        indice = self.cho_motor.GetSelection()
        opciones = self._opciones_motor()
        if 0 <= indice < len(opciones):
            return opciones[indice][0]
        return ""

    def _crear_voz(self, padre):
        fila = wx.BoxSizer(wx.VERTICAL)
        fila.Add(fila_label(padre, _("Voz:")), 0, wx.BOTTOM, 6)
        self.cho_voz = wx.Choice(padre, name=_("Voz secundaria"))
        _tc(self.cho_voz)
        self._cargar_voces()
        fila.Add(self.cho_voz, 0, wx.EXPAND | wx.BOTTOM, 6)
        return fila

    def _crear_ajustes(self, padre):
        fila = wx.BoxSizer(wx.VERTICAL)
        fila.Add(fila_label(padre, _("Veloci&dad (0 a 100):")), 0, wx.BOTTOM, 6)
        self.sp_velocidad = ContadorAccesible(
            padre, min=0, max=100,
            name=_("Velocidad de la voz secundaria"),
            initial=escala_voz.ajustar_velocidad(
                int(self._config.get("velocidad_secundaria",
                                     escala_voz.VELOCIDAD_NORMAL)), 0))
        self.sp_velocidad.SetIncrement(5)
        _tc(self.sp_velocidad)
        fila.Add(self.sp_velocidad, 0, wx.BOTTOM, 6)

        fila.Add(fila_label(padre, _("Volum&en (0 a 100):")), 0, wx.BOTTOM, 6)
        self.sp_volumen = ContadorAccesible(
            padre, min=0, max=100, initial=_porcentaje_de_volumen(self._config),
            name=_("Volumen de la voz secundaria"))
        self.sp_volumen.SetIncrement(5)
        _tc(self.sp_volumen)
        fila.Add(self.sp_volumen, 0, wx.BOTTOM, 6)
        return fila

    def _crear_probar(self, padre):
        self.btn_probar = wx.Button(
            padre, label=_("Proba&r voz secundaria"),
            name=_("Probar voz secundaria"))
        self.btn_probar.SetBackgroundColour(_T.btn)
        self.btn_probar.SetForegroundColour(_T.btn_t)
        self.btn_probar.Bind(wx.EVT_BUTTON, lambda _evento: self._al_probar())
        return self.btn_probar

    def _crear_respaldo(self, padre):
        fila = wx.BoxSizer(wx.VERTICAL)
        self.lbl_respaldo = fila_label(
            padre, _("Voz de W&indows de respaldo:"))
        self.cho_respaldo = wx.Choice(
            padre, name=_("Voz de Windows de respaldo de la voz secundaria"))
        _tc(self.cho_respaldo)
        self._cargar_respaldo()
        fila.Add(self.lbl_respaldo, 0, wx.BOTTOM, 6)
        fila.Add(self.cho_respaldo, 0, wx.EXPAND)
        return fila

    def _cargar_respaldo(self):
        guardada = self._config.get("voz_respaldo_secundaria") or ""
        items = [_(_IGUAL_RESPALDO)] + self._voces_respaldo
        self.cho_respaldo.SetItems(items)
        indice = escala_voz.resolver_voz(guardada, self._voces_respaldo)
        self.cho_respaldo.SetSelection(
            0 if indice is None else indice + 1)

    def recargar_voces(self, voces) -> None:
        """Rellena la lista con la voz guardada si sigue existiendo."""
        self._voces = list(voces or ())
        self._cargar_voces()

    def _cargar_voces(self) -> None:
        guardada = self._config.get("voz_secundaria") or ""
        if self._voces:
            self.cho_voz.SetItems([_(_IGUAL_PRINCIPAL)] + self._voces)
            indice = escala_voz.resolver_voz(guardada, self._voces)
            self.cho_voz.SetSelection(0 if indice is None else indice + 1)
            self.cho_voz.Enable(True)
        elif self.motor_efectivo() == "elevenlabs":
            self.cho_voz.SetItems([_(_IGUAL_PRINCIPAL)])
            self.cho_voz.SetSelection(0)
            self.cho_voz.Enable(True)
        else:
            self.cho_voz.SetItems([_(_NO_HAY_VOCES)])
            self.cho_voz.SetSelection(0)
            self.cho_voz.Disable()

    def motor_efectivo(self) -> str:
        """El motor propio o, con «Igual», el de la voz principal."""
        return self._motor or self._motor_principal

    def actualizar_principal(self, motor, voces) -> None:
        """El motor o las voces de la página principal cambiaron."""
        self._motor_principal = motor
        self._voces_principales = list(voces or ())
        if not self._motor:
            self.recargar_voces(self._voces_principales)
        self._actualizar_respaldo()

    def _actualizar_respaldo(self) -> None:
        self.mostrar_respaldo(self.motor_efectivo() != "sapi")

    def mostrar_respaldo(self, visible: bool) -> None:
        self.lbl_respaldo.Show(visible)
        self.cho_respaldo.Show(visible)

    def datos_de_prueba(self):
        """La voz elegida (vacía es la principal), la velocidad y el volumen."""
        return (self._voz_elegida(), self.sp_velocidad.GetValue(),
                self.sp_volumen.GetValue())

    def voces(self) -> list[str]:
        return list(self._voces)

    def _voz_elegida(self) -> str:
        indice = self.cho_voz.GetSelection()
        if 1 <= indice <= len(self._voces):
            return self._voces[indice - 1]
        return ""

    def guardar(self, fijar, en_memoria) -> None:
        fijar("voz", "motor_secundaria", self._motor)
        en_memoria["motor_secundaria"] = self._motor
        if self._voces:
            voz = self._voz_elegida()
            fijar("voz", "voz_secundaria", voz)
            en_memoria["voz_secundaria"] = voz
        velocidad = escala_voz.ajustar_velocidad(
            self.sp_velocidad.GetValue(), 0)
        fijar("voz", "velocidad_secundaria", str(velocidad))
        en_memoria["velocidad_secundaria"] = velocidad
        volumen = self.sp_volumen.GetValue()
        fijar("voz", "volumen_secundaria", f"{volumen / 100:.2f}")
        en_memoria["volumen_secundaria"] = round(volumen / 100.0, 2)
        respaldo = self._respaldo_elegido()
        fijar("voz", "voz_respaldo_secundaria", respaldo)
        en_memoria["voz_respaldo_secundaria"] = respaldo

    def _respaldo_elegido(self) -> str:
        indice = self.cho_respaldo.GetSelection()
        if 1 <= indice <= len(self._voces_respaldo):
            return self._voces_respaldo[indice - 1]
        return ""
