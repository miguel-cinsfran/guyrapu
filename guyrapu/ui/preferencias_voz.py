# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Voces del diálogo de Preferencias.

Dueña de sus controles, de la prueba de voz, de ElevenLabs y de su guardado
propio. El diálogo la construye por composición.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.youtube import credenciales
from guyrapu.ui import voces_ventana
from guyrapu.ui.gui import ContadorAccesible, _T, _tc, anunciar
from guyrapu.ui.preferencias_comun import crear_panel, fila_label
from guyrapu.ui.preferencias_voz_eleven import BloqueElevenLabs
from guyrapu.ui.preferencias_voz_secundaria import BloqueVozSecundaria
from guyrapu.ui.prueba_voz import PruebaVoz

_SIN_CLAVE_ELEVEN = N_("(comprueba la clave)")
_NO_HAY_VOCES = N_("(no hay voces disponibles)")


class PaginaVoz:
    """Página Voces: motor, clave de ElevenLabs, prueba de voz y su guardado."""

    def __init__(self, ventana, config):
        self._ventana = ventana
        self._config = config

    def construir(self, parent):
        p = crear_panel(parent, "PagVoz")
        self._pag_voz_panel = p
        vs = wx.BoxSizer(wx.VERTICAL)
        from guyrapu.voice import motores

        motor_guardado = self._config.get("motor", "sapi")
        self._motor_idx = (motores.MOTORES.index(motor_guardado)
                           if motor_guardado in motores.MOTORES else 0)
        es_eleven = motores.MOTORES[self._motor_idx] == "elevenlabs"

        self._crear_motor(p, vs)
        self._eleven = BloqueElevenLabs(
            self._ventana, self._config, credenciales,
            lambda texto: anunciar(texto),
            self._al_cambiar_voces_eleven)
        self._eleven.crear_clave(p, vs)
        # Nombres que usan las pruebas de la página; la clave y su botón son
        # del bloque de ElevenLabs.
        self.txt_clave_eleven = self._eleven.txt_clave_eleven
        self.btn_comprobar_clave = self._eleven.btn_comprobar_clave
        self._crear_voz_lectura(p, vs, es_eleven)
        self._crear_ajustes(p, vs)
        self._eleven.crear_ajustes(p, vs)
        self._eleven_ctrls = self._eleven.controles
        self._voz_secundaria = BloqueVozSecundaria(
            self._config, self._probar_voz_secundaria)
        vs.Add(self._voz_secundaria.construir(
            p, self._voces, self._eleven.voces_respaldo), 0, wx.EXPAND | wx.ALL, 10)
        self._prueba = PruebaVoz()
        # El motor de prueba se cierra al cerrar el diálogo por cualquier camino.
        # Se escucha en el panel: el diálogo llega al evento como un wx.Window
        # genérico y `is` no lo reconoce (medido el 27/10/2026).
        p.Bind(wx.EVT_WINDOW_DESTROY, self._al_destruir)
        p.SetSizer(vs)
        self._mostrar_controles_eleven(es_eleven)
        if es_eleven:
            # Con clave guardada, las voces se comprueban solas en segundo
            # plano y se llenan; sin clave, todo queda a la espera.
            self._eleven.preparar_voces()
        return p

    def _crear_motor(self, p, vs):
        from guyrapu.voice import motores

        vs.Add(fila_label(p, _("&Motor de voz:")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.cho_motor = wx.Choice(
            p, choices=[_(motores.NOMBRES[m]) for m in motores.MOTORES],
            name=_("Motor de voz"))
        _tc(self.cho_motor)
        self.cho_motor.SetSelection(self._motor_idx)
        self.cho_motor.Bind(wx.EVT_CHOICE, self._on_motor_cambiado)
        vs.Add(self.cho_motor, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _crear_voz_lectura(self, p, vs, es_eleven):
        from guyrapu.voice import motores

        # Voz del motor elegido. También está en el menú Voz → Seleccionar voz;
        # aquí queda junto al resto de ajustes de lectura para encontrarla más
        # fácil.
        vs.Add(fila_label(p, _("&Voz principal:")), 0, wx.LEFT | wx.RIGHT, 10)
        if es_eleven:
            # Nunca se va a la red en el hilo de la interfaz: la lista queda
            # vacía hasta que se compruebe la clave.
            self._voces = []
            vacio_voz = _SIN_CLAVE_ELEVEN
        else:
            self._voces = motores.listar_voces(motores.MOTORES[self._motor_idx])
            vacio_voz = _NO_HAY_VOCES
        self.cho_voz = wx.Choice(p, choices=self._voces or [vacio_voz],
                                  name=_("Voz principal"))
        _tc(self.cho_voz)
        self._cargar_voces(self.cho_voz, self._config.get("voz"), vacio=vacio_voz)
        vs.Add(self.cho_voz, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_voces = wx.Button(p, label=_("Admi&nistrar voces…"), name=_("Administrar voces…"))
        self.btn_voces.Bind(wx.EVT_BUTTON, lambda _e: voces_ventana.abrir(
            self._ventana, al_cerrar=lambda: self._on_motor_cambiado(None)))
        vs.Add(self.btn_voces, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _crear_ajustes(self, p, vs):
        from guyrapu.voice import escala_voz

        # Velocidad, volumen y tono como valores absolutos 0..100.
        vs.Add(fila_label(p, _("Ve&locidad (0 a 100):")), 0, wx.LEFT | wx.RIGHT, 10)
        self.sp_velocidad = ContadorAccesible(
            p, min=0, max=100, name=_("Velocidad de la voz"),
            initial=escala_voz.ajustar_velocidad(
                int(self._config.get("velocidad_voz", escala_voz.VELOCIDAD_NORMAL)), 0))
        self.sp_velocidad.SetIncrement(5)
        _tc(self.sp_velocidad)
        vs.Add(self.sp_velocidad, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        try:
            vol_pct = max(0, min(100, int(round(float(self._config.get("volumen", 1.0)) * 100))))
        except (TypeError, ValueError):
            vol_pct = 100
        vs.Add(fila_label(p, _("Vol&umen (0 a 100):")), 0, wx.LEFT | wx.RIGHT, 10)
        self.sp_volumen = ContadorAccesible(
            p, min=0, max=100, initial=vol_pct, name=_("Volumen de la voz"))
        self.sp_volumen.SetIncrement(5)
        _tc(self.sp_volumen)
        vs.Add(self.sp_volumen, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(fila_label(p, _("&Tono (0 a 100):")), 0, wx.LEFT | wx.RIGHT, 10)
        self.sp_tono = ContadorAccesible(
            p, min=0, max=100, name=_("Tono de la voz"),
            initial=max(0, min(100, int(self._config.get("tono", 50)))))
        self.sp_tono.SetIncrement(5)
        _tc(self.sp_tono)
        vs.Add(self.sp_tono, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.btn_probar_voz = wx.Button(p, label=_("&Probar voz"), name=_("Probar voz"))
        self.btn_probar_voz.SetBackgroundColour(_T.btn)
        self.btn_probar_voz.SetForegroundColour(_T.btn_t)
        self.btn_probar_voz.Bind(wx.EVT_BUTTON, self._on_probar_voz)
        vs.Add(self.btn_probar_voz, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    def _mostrar_controles_eleven(self, visible: bool) -> None:
        self._eleven.mostrar(visible)
        bloque = getattr(self, "_voz_secundaria", None)
        if bloque is not None:
            bloque.mostrar_respaldo(visible)
        panel = getattr(self, "_pag_voz_panel", None)
        if panel is not None:
            panel.Layout()

    def _al_cambiar_voces_eleven(self, voces, guardada) -> None:
        self._voces = list(voces)
        self._cargar_voces(self.cho_voz, guardada, vacio=_SIN_CLAVE_ELEVEN)
        self._voz_secundaria.recargar_voces(self._voces)

    def _comprobar_clave(self, anunciar_ok: bool) -> None:
        self._eleven.comprobar(anunciar_ok)

    def _clave_ok(self, pares, usados, limite, anunciar_ok: bool) -> None:
        self._eleven.clave_ok(pares, usados, limite, anunciar_ok)

    def _clave_fallo(self, mensaje) -> None:
        self._eleven.clave_fallo(mensaje)

    def _cargar_voces(self, choice, guardada, vacio=_NO_HAY_VOCES) -> None:
        from guyrapu.voice import escala_voz

        if self._voces:
            choice.SetItems(self._voces)
            idx = escala_voz.resolver_voz(guardada, self._voces)
            choice.SetSelection(0 if idx is None else idx)
            choice.Enable(True)
        else:
            choice.SetItems([_(vacio)])
            choice.SetSelection(0)
            choice.Disable()

    def _motor_elegido(self) -> str:
        from guyrapu.voice import motores

        i = self.cho_motor.GetSelection()
        return motores.MOTORES[i] if 0 <= i < len(motores.MOTORES) else "sapi"

    def _on_motor_cambiado(self, event) -> None:
        # Repuebla las voces del motor nuevo sin anunciar: el lector ya lee el
        # valor del combinado al recorrerlo. Con ElevenLabs, además, se ocultan
        # o muestran sus controles y se comprueba la clave en segundo plano.
        from guyrapu.voice import motores

        motor = self._motor_elegido()
        if motor == "elevenlabs":
            self._mostrar_controles_eleven(True)
            self._eleven.preparar_voces()
            return
        self._mostrar_controles_eleven(False)
        self._voces = motores.listar_voces(motor)
        self._cargar_voces(self.cho_voz, self._config.get("voz"))
        self._voz_secundaria.recargar_voces(self._voces)

    def _on_probar_voz(self, event) -> None:
        motor = self._motor_elegido()
        if motor == "elevenlabs":
            self._probar_voz_elevenlabs()
            return
        self._prueba.probar_prism(
            motor, self.cho_voz.GetSelection(), self.sp_velocidad.GetValue(),
            self.sp_volumen.GetValue(), self.sp_tono.GetValue())

    def _probar_voz_elevenlabs(self) -> None:
        if not self._voces:
            anunciar(_("Primero comprueba la clave."))
            return
        self._prueba.probar_elevenlabs(
            self._eleven.clave(),
            self.cho_voz.GetStringSelection(),
            self.sp_velocidad.GetValue(), self.sp_volumen.GetValue())

    def _probar_voz_secundaria(self) -> None:
        from guyrapu.voice import escala_voz

        motor = self._motor_elegido()
        voz, velocidad, volumen = self._voz_secundaria.datos_de_prueba()
        if motor == "elevenlabs":
            if not self._voces:
                anunciar(_("Primero comprueba la clave."))
                return
            self._prueba.probar_elevenlabs(
                self._eleven.clave(),
                voz or self.cho_voz.GetStringSelection(), velocidad, volumen)
            return
        indice = escala_voz.resolver_voz(voz, self._voces) if voz else None
        if indice is None:
            indice = self.cho_voz.GetSelection()
        self._prueba.probar_prism(
            motor, indice, velocidad, volumen, self.sp_tono.GetValue())

    def _cerrar_motor_prueba(self) -> None:
        self._prueba.cerrar()

    def _al_destruir(self, event) -> None:
        # El evento sube desde los hijos, así que solo se atiende cuando el
        # panel mismo se destruye.
        if event.GetEventObject() is self._pag_voz_panel:
            self._cerrar_motor_prueba()
        event.Skip()

    def guardar(self, fijar, en_memoria):
        # Si el motor elegido no tiene voces no se guardan motor ni voz (se
        # conservan los anteriores); el resto de las opciones se guarda igual.
        motor_no_disponible = self._guardar_motor_y_voces(fijar, en_memoria)
        self._voz_secundaria.guardar(fijar, en_memoria, bool(self._voces))
        self._eleven.guardar(fijar, en_memoria)
        self._guardar_ajustes_voz(fijar, en_memoria)
        return motor_no_disponible

    def _guardar_motor_y_voces(self, fijar, en_memoria):
        motor_no_disponible = False
        if self._voces:
            motor = self._motor_elegido()
            fijar("voz", "motor", motor)
            en_memoria["motor"] = motor
            # Se guarda el nombre, no el número: el índice se corre al instalar
            # una voz y la app hablaría con otra sin avisar.
            nom_voz = self.cho_voz.GetStringSelection()
            fijar("voz", "voz", nom_voz)
            en_memoria["voz"] = nom_voz
        else:
            motor_no_disponible = True
        return motor_no_disponible

    def _guardar_ajustes_voz(self, fijar, en_memoria):
        self._cerrar_motor_prueba()
        from guyrapu.voice import escala_voz
        velocidad = escala_voz.ajustar_velocidad(self.sp_velocidad.GetValue(), 0)
        fijar("voz", "velocidad_voz", str(velocidad))
        en_memoria["velocidad_voz"] = velocidad
        volumen = self.sp_volumen.GetValue()
        fijar("voz", "volumen", f"{volumen / 100:.2f}")
        en_memoria["volumen"] = round(volumen / 100.0, 2)
        tono = self.sp_tono.GetValue()
        fijar("voz", "tono", str(tono))
        en_memoria["tono"] = tono
