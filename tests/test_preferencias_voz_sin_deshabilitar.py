# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Controles de las páginas de voz de Preferencias que no se deshabilitan.

Abren ventanas. Cubren las tres listas de voces y «Comprobar clave»: siempre
se alcanzan con Tab y dicen el motivo en lugar de desaparecer del recorrido.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import config
from guyrapu.ui import (clave_elevenlabs, espera_sonora, gui_preferencias,
                       preferencias_voz)
from guyrapu.ui import preferencias_transmision
from guyrapu.voice import motores
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, armar_preferencias, destruir

NO_HAY_VOCES = "(no hay voces instaladas: usa Administrar voces)"
NO_HAY_RESPALDO = "(no hay voces disponibles)"
SIN_CLAVE = "(comprueba la clave)"
BASE = "Compro&bar clave"
COMPROBANDO = BASE + " (comprobando la clave)"


class TestListasDeVozSinDeshabilitar(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name)
        (self.ruta / "config.ini").write_text(config._CONFIG_FALLBACK,
                                              encoding="utf-8")
        parche = redirigir_rutas(self.ruta)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _dialogo(self, configuracion=None, por_motor=None, clave=""):
        por_motor = por_motor or {}
        with mock.patch.object(
                motores, "listar_voces",
                side_effect=lambda motor: list(
                    por_motor.get(motor, ["Voz A"]))), \
                mock.patch.object(
                    preferencias_voz.credenciales, "cargar",
                    return_value={"elevenlabs_clave": clave} if clave else {}):
            dialogo = armar_preferencias(configuracion or {}, "Voces")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _guardar(self, dialogo):
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)

    def _items(self, choice):
        return [choice.GetString(i) for i in range(choice.GetCount())]

    def test_la_voz_principal_sin_voces_queda_habilitada(self):
        dialogo = self._dialogo(por_motor={"sapi": []})
        choice = dialogo.pagina_voz.cho_voz
        self.assertTrue(choice.IsEnabled())
        self.assertEqual(self._items(choice), [NO_HAY_VOCES])

    def test_la_clave_esta_a_cuatro_pixeles_de_su_rotulo(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        campo = dialogo.pagina_voz.txt_clave_eleven
        panel = campo.GetParent()
        panel.Layout()
        etiqueta = [h for h in panel.GetChildren()
                    if isinstance(h, wx.StaticText)
                    and h.GetLabel() == "Cl&ave de ElevenLabs:"][0]
        self.assertEqual(
            campo.GetPosition().y - (
                etiqueta.GetPosition().y + etiqueta.GetSize().GetHeight()), 4)

    def test_el_respaldo_de_elevenlabs_sin_voces_queda_habilitado(self):
        dialogo = self._dialogo({"motor": "elevenlabs"}, {"sapi": []})
        choice = dialogo.pagina_voz._eleven.cho_voz_respaldo
        self.assertTrue(choice.IsEnabled())
        self.assertEqual(self._items(choice), [NO_HAY_RESPALDO])

    def test_la_voz_secundaria_sin_voces_queda_habilitada(self):
        dialogo = self._dialogo(
            {"motor": "sapi", "motor_secundaria": "phonon"},
            {"sapi": ["Voz A"], "phonon": []})
        choice = dialogo.pagina_voz._voz_secundaria.cho_voz
        self.assertTrue(choice.IsEnabled())
        self.assertEqual(self._items(choice), [NO_HAY_VOCES])

    def test_guardar_no_escribe_el_aviso_como_voz_principal(self):
        dialogo = self._dialogo({"voz": "Voz guardada"},
                                por_motor={"sapi": []})
        self._guardar(dialogo)
        self.assertEqual(dialogo._config["voz"], "Voz guardada")

    def test_guardar_no_escribe_el_aviso_como_respaldo_de_elevenlabs(self):
        dialogo = self._dialogo(
            {"motor": "elevenlabs", "voz_respaldo": "Voz guardada"},
            {"sapi": []})
        self._guardar(dialogo)
        self.assertEqual(dialogo._config["voz_respaldo"], "")

    def test_guardar_no_escribe_el_aviso_como_voz_secundaria(self):
        dialogo = self._dialogo(
            {"motor": "sapi", "motor_secundaria": "phonon",
             "voz_secundaria": "Voz guardada"},
            {"sapi": ["Voz A"], "phonon": []})
        self._guardar(dialogo)
        self.assertEqual(dialogo._config["voz_secundaria"], "Voz guardada")

    def test_comprobar_clave_nunca_se_deshabilita_y_lleva_el_motivo(self):
        sin_clave = self._dialogo({"motor": "elevenlabs"})
        self.assertTrue(sin_clave.pagina_voz.btn_comprobar_clave.IsEnabled())
        self.assertEqual(
            sin_clave.pagina_voz.btn_comprobar_clave.GetLabel(), BASE)
        self.assertEqual(
            sin_clave.pagina_voz.cho_voz.GetStringSelection(), SIN_CLAVE)
        self.assertTrue(sin_clave.pagina_voz.cho_voz.IsEnabled())

        with mock.patch.object(clave_elevenlabs, "comprobar") as comprobar:
            with_clave = self._dialogo({"motor": "elevenlabs"}, clave="clave")
        boton = with_clave.pagina_voz.btn_comprobar_clave
        self.assertTrue(boton.IsEnabled())
        self.assertEqual(boton.GetLabel(), COMPROBANDO)
        comprobar.assert_called_once()

    def test_activar_mientras_comprueba_anuncia_y_no_repite(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        pagina = dialogo.pagina_voz
        pagina.txt_clave_eleven.SetValue("clave")
        with mock.patch.object(clave_elevenlabs, "comprobar") as comprobar, \
                mock.patch.object(preferencias_voz, "anunciar") as anunciar:
            pagina._eleven._on_comprobar_clave(None)
            pagina._eleven._on_comprobar_clave(None)
        comprobar.assert_called_once()
        anunciar.assert_called_once_with("Comprobando la clave.")

    def test_comprobar_clave_suena_espera_y_listo(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        pagina = dialogo.pagina_voz
        pagina.txt_clave_eleven.SetValue("clave")
        with mock.patch.object(clave_elevenlabs, "comprobar"), \
                mock.patch.object(
                    espera_sonora.sound_player, "reproducir") as sonar:
            pagina._eleven._on_comprobar_clave(None)
            self.assertTrue(pagina._eleven._espera._timer.IsRunning())
            pagina._eleven._espera._al_tiempo(None)
            with mock.patch.object(preferencias_voz, "anunciar"):
                pagina._eleven.clave_ok([("id1", "Ana")], 0, 0, False)
        self.assertFalse(pagina._eleven._espera._timer.IsRunning())
        self.assertEqual([llamada.args[0] for llamada in sonar.call_args_list],
                         ["espera", "listo"])

    def test_comprobar_clave_que_falla_suena_error(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        pagina = dialogo.pagina_voz
        pagina.txt_clave_eleven.SetValue("clave")
        with mock.patch.object(clave_elevenlabs, "comprobar"), \
                mock.patch.object(
                    espera_sonora.sound_player, "reproducir") as sonar:
            pagina._eleven._on_comprobar_clave(None)
            pagina._eleven._espera._al_tiempo(None)
            with mock.patch.object(preferencias_voz, "anunciar"):
                pagina._eleven.clave_fallo("ElevenLabs no reconoce la clave.")
        self.assertFalse(pagina._eleven._espera._timer.IsRunning())
        self.assertEqual([llamada.args[0] for llamada in sonar.call_args_list],
                         ["espera", "error"])

    def test_al_terminar_con_exito_la_etiqueta_vuelve_a_la_base(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        pagina = dialogo.pagina_voz
        pagina.txt_clave_eleven.SetValue("clave")
        with mock.patch.object(clave_elevenlabs, "comprobar"):
            pagina._eleven._on_comprobar_clave(None)
        self.assertEqual(pagina.btn_comprobar_clave.GetLabel(), COMPROBANDO)
        with mock.patch.object(preferencias_voz, "anunciar"):
            pagina._eleven.clave_ok([("id1", "Ana")], 0, 0, False)
        self.assertEqual(pagina.btn_comprobar_clave.GetLabel(), BASE)
        self.assertTrue(pagina.btn_comprobar_clave.IsEnabled())

    def test_al_terminar_con_error_la_etiqueta_vuelve_a_la_base(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        pagina = dialogo.pagina_voz
        pagina.txt_clave_eleven.SetValue("clave")
        with mock.patch.object(clave_elevenlabs, "comprobar"):
            pagina._eleven._on_comprobar_clave(None)
        self.assertEqual(pagina.btn_comprobar_clave.GetLabel(), COMPROBANDO)
        with mock.patch.object(preferencias_voz, "anunciar"):
            pagina._eleven.clave_fallo("ElevenLabs no reconoce la clave.")
        self.assertEqual(pagina.btn_comprobar_clave.GetLabel(), BASE)
        self.assertTrue(pagina.btn_comprobar_clave.IsEnabled())


if __name__ == "__main__":
    unittest.main()
