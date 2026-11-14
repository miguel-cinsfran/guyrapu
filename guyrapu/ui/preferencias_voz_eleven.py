# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ajustes de ElevenLabs de la página Voces.

Dueño de la clave, su comprobación, el tope, «solo lo importante» y la voz de
respaldo. La página lo crea, le pide mostrar u ocultar sus controles y guardar,
y le avisa cuándo cambia su lista de voces. Su única razón para cambiar es
ElevenLabs.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui import clave_elevenlabs
from guyrapu.ui.gui import ContadorAccesible, _T, _tc
from guyrapu.ui.preferencias_comun import fila_label
from guyrapu.voice import escala_voz
from guyrapu.voice import motores

_NO_HAY_VOCES = N_("(no hay voces disponibles)")


class BloqueElevenLabs:
    """Clave, tope, «solo lo importante» y voz de respaldo de ElevenLabs."""

    def __init__(self, ventana, config, credenciales, anunciar,
                 al_cambiar_voces):
        self._ventana = ventana
        self._config = config
        self._credenciales = credenciales
        self._anunciar = anunciar
        self._al_cambiar_voces = al_cambiar_voces
        self.controles = []
        self.voces_respaldo = []

    def crear_clave(self, p, vs):
        lbl_clave = fila_label(p, _("Cl&ave de ElevenLabs:"))
        self.txt_clave_eleven = wx.TextCtrl(
            p, value=self._credenciales.cargar().get("elevenlabs_clave", "") or "",
            style=wx.TE_PASSWORD, name=_("Clave de ElevenLabs"))
        _tc(self.txt_clave_eleven)
        vs.Add(lbl_clave, 0, wx.LEFT | wx.RIGHT, 10)
        vs.Add(self.txt_clave_eleven, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_comprobar_clave = wx.Button(
            p, label=_("Compro&bar clave"), name=_("Comprobar clave"))
        self.btn_comprobar_clave.SetBackgroundColour(_T.btn)
        self.btn_comprobar_clave.SetForegroundColour(_T.btn_t)
        self.btn_comprobar_clave.Bind(wx.EVT_BUTTON, self._on_comprobar_clave)
        vs.Add(self.btn_comprobar_clave, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.controles.extend((lbl_clave, self.txt_clave_eleven,
                               self.btn_comprobar_clave))

    def crear_ajustes(self, p, vs):
        # Tope de caracteres por sesión (0 sin tope), «solo lo importante» y
        # la voz de Windows de respaldo. Solo se ven con ElevenLabs.
        lbl_tope = fila_label(p, _("Límite de caracteres p&or sesión (0 sin límite):"))
        self.sp_tope_eleven = ContadorAccesible(
            p, min=0, max=1000000, name=_("Límite de caracteres de ElevenLabs"),
            initial=max(0, int(self._config.get("elevenlabs_tope", 0) or 0)))
        self.sp_tope_eleven.SetIncrement(1000)
        _tc(self.sp_tope_eleven)
        vs.Add(lbl_tope, 0, wx.LEFT | wx.RIGHT, 10)
        vs.Add(self.sp_tope_eleven, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.chk_solo_importantes = wx.CheckBox(
            p, name=_("Solo lo importante con ElevenLabs"),
            label=_("U&sar ElevenLabs solo con Super Chats, miembros, cofres, "
                    "propietario y moderadores"))
        self.chk_solo_importantes.SetForegroundColour(_T.text)
        self.chk_solo_importantes.SetValue(
            bool(self._config.get("elevenlabs_solo_importantes", False)))
        vs.Add(self.chk_solo_importantes, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        lbl_respaldo = fila_label(p, _("Voz de &Windows de respaldo:"))
        self.voces_respaldo = motores.listar_voces("sapi")
        self.cho_voz_respaldo = wx.Choice(
            p, choices=self.voces_respaldo or [_(_NO_HAY_VOCES)],
            name=_("Voz de Windows de respaldo"))
        _tc(self.cho_voz_respaldo)
        if self.voces_respaldo:
            idx_respaldo = escala_voz.resolver_voz(
                self._config.get("voz_respaldo"), self.voces_respaldo)
            self.cho_voz_respaldo.SetSelection(
                0 if idx_respaldo is None else idx_respaldo)
        else:
            self.cho_voz_respaldo.SetSelection(0)
            self.cho_voz_respaldo.Disable()
        vs.Add(lbl_respaldo, 0, wx.LEFT | wx.RIGHT, 10)
        vs.Add(self.cho_voz_respaldo, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.controles.extend((lbl_tope, self.sp_tope_eleven,
                               self.chk_solo_importantes, lbl_respaldo,
                               self.cho_voz_respaldo))

    def mostrar(self, visible: bool) -> None:
        for ctrl in self.controles:
            ctrl.Show(visible)

    def clave(self) -> str:
        return self.txt_clave_eleven.GetValue().strip()

    def preparar_voces(self, anunciar_ok: bool = False) -> None:
        self._al_cambiar_voces((), self._config.get("voz"))
        if self.clave():
            self.btn_comprobar_clave.Disable()
            self.comprobar(anunciar_ok)

    def _on_comprobar_clave(self, event) -> None:
        if not self.clave():
            self._anunciar(_("Escribe la clave de ElevenLabs."))
            return
        self.btn_comprobar_clave.Disable()
        self.comprobar(anunciar_ok=True)

    def comprobar(self, anunciar_ok: bool) -> None:
        clave_elevenlabs.comprobar(
            self.clave(),
            lambda pares, usados, limite: self.clave_ok(
                pares, usados, limite, anunciar_ok),
            self.clave_fallo)

    def clave_ok(self, pares, usados, limite, anunciar_ok: bool) -> None:
        if not self._ventana:   # el diálogo pudo cerrarse mientras se comprobaba
            return
        self.btn_comprobar_clave.Enable()
        voces = [nombre for _id, nombre in pares]
        self._al_cambiar_voces(voces, self._config.get("voz"))
        if anunciar_ok:
            self._anunciar(clave_elevenlabs.texto_clave_valida(
                len(voces), usados, limite))

    def clave_fallo(self, mensaje) -> None:
        if not self._ventana:
            return
        self.btn_comprobar_clave.Enable()
        self._al_cambiar_voces((), None)
        self._anunciar(mensaje)

    def guardar(self, fijar, en_memoria) -> None:
        # Clave de ElevenLabs: es un secreto y va a credenciales.json, nunca al
        # ini. Solo se escribe si cambió.
        clave_eleven = self.clave()
        if clave_eleven != (self._credenciales.cargar().get(
                "elevenlabs_clave", "") or ""):
            self._credenciales.guardar_campo("elevenlabs_clave", clave_eleven)
        # Tope, «solo lo importante» y voz de respaldo de ElevenLabs se guardan
        # siempre, haya o no clave comprobada.
        tope_eleven = self.sp_tope_eleven.GetValue()
        fijar("voz", "elevenlabs_tope", str(tope_eleven))
        en_memoria["elevenlabs_tope"] = tope_eleven
        solo_importantes = self.chk_solo_importantes.GetValue()
        fijar("voz", "elevenlabs_solo_importantes",
              "true" if solo_importantes else "false")
        en_memoria["elevenlabs_solo_importantes"] = solo_importantes
        voz_respaldo = (self.cho_voz_respaldo.GetStringSelection()
                        if self.voces_respaldo else "")
        fijar("voz", "voz_respaldo", voz_respaldo)
        en_memoria["voz_respaldo"] = voz_respaldo
