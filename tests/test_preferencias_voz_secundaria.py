# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Bloque de la voz secundaria de Preferencias.

Abren ventanas. Cubren cómo se cargan las voces, los nombres accesibles, el
guardado de sus cuatro claves, la prueba de voz y el respaldo que solo se ve
con ElevenLabs.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import config
from guyrapu.ui import gui, gui_aplicar_preferencias, gui_preferencias
from guyrapu.ui import preferencias_transmision
from guyrapu.voice import motores
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


IGUAL_PRINCIPAL = "Igual que la voz principal"
IGUAL_RESPALDO = "Igual que el respaldo de la voz principal"
NOMBRES = {
    "cho_motor": "Motor de la voz secundaria",
    "cho_voz": "Voz secundaria",
    "sp_velocidad": "Velocidad de la voz secundaria",
    "sp_volumen": "Volumen de la voz secundaria",
    "btn_probar": "Probar voz secundaria",
    "cho_respaldo": "Voz de Windows de respaldo de la voz secundaria",
}


def _letras_acceso(ventana):
    letras = []
    pendientes = [ventana]
    while pendientes:
        actual = pendientes.pop(0)
        if isinstance(actual, (gui.wx.StaticText, gui.wx.Button,
                               gui.wx.CheckBox, gui.wx.RadioButton)):
            etiqueta = actual.GetLabel()
            if "&" in etiqueta:
                letras.append(etiqueta.split("&", 1)[1][:1].lower())
        pendientes.extend(actual.GetChildren())
    return letras


class TestBloqueVozSecundaria(unittest.TestCase):
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

    def _dialogo(self, configuracion=None, voces=("Voz A", "Voz B")):
        with mock.patch.object(motores, "listar_voces",
                               return_value=list(voces)):
            dialogo = gui_preferencias.PreferenciasDialog(
                None, configuracion or {})
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _bloque(self, dialogo):
        return dialogo.pagina_voz._voz_secundaria

    def test_la_lista_empieza_por_igual_y_trae_las_voces_del_motor(self):
        dialogo = self._dialogo({"voz_secundaria": "Voz B"})
        cho = self._bloque(dialogo).cho_voz
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         [IGUAL_PRINCIPAL, "Voz A", "Voz B"])
        self.assertEqual(cho.GetStringSelection(), "Voz B")

    def test_si_la_voz_guardada_no_existe_queda_en_igual(self):
        dialogo = self._dialogo({"voz_secundaria": "No existe"})
        cho = self._bloque(dialogo).cho_voz
        self.assertEqual(cho.GetStringSelection(), IGUAL_PRINCIPAL)

    def test_los_nombres_accesibles_son_los_pedidos(self):
        dialogo = self._dialogo()
        bloque = self._bloque(dialogo)
        for atributo, nombre in NOMBRES.items():
            with self.subTest(atributo=atributo):
                self.assertEqual(getattr(bloque, atributo).GetName(), nombre)
        self.assertEqual(dialogo.pagina_voz.cho_voz.GetName(),
                         "Voz principal")

    def test_la_velocidad_y_el_volumen_se_cargan_de_la_config(self):
        dialogo = self._dialogo({"velocidad_secundaria": 25,
                                 "volumen_secundaria": 0.4})
        bloque = self._bloque(dialogo)
        self.assertEqual(bloque.sp_velocidad.GetValue(), 25)
        self.assertEqual(bloque.sp_volumen.GetValue(), 40)
        self.assertEqual(bloque.sp_velocidad.GetIncrement(), 5)
        self.assertEqual(bloque.sp_volumen.GetIncrement(), 5)

    def test_guardar_escribe_las_cuatro_claves(self):
        dialogo = self._dialogo()
        bloque = self._bloque(dialogo)
        bloque.cho_voz.SetSelection(2)
        bloque.sp_velocidad.SetValue(60)
        bloque.sp_volumen.SetValue(30)
        bloque.cho_respaldo.SetSelection(2)
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        self.assertEqual(dialogo._config["voz_secundaria"], "Voz B")
        self.assertEqual(dialogo._config["velocidad_secundaria"], 60)
        self.assertEqual(dialogo._config["volumen_secundaria"], 0.3)
        self.assertEqual(dialogo._config["voz_respaldo_secundaria"], "Voz B")
        parser = config._mk_parser()
        parser.read(self.ruta / "config.ini", encoding="utf-8")
        self.assertEqual(parser.get("voz", "voz_secundaria"), "Voz B")
        self.assertEqual(parser.get("voz", "velocidad_secundaria"), "60")
        self.assertEqual(parser.get("voz", "volumen_secundaria"), "0.30")
        self.assertEqual(parser.get("voz", "voz_respaldo_secundaria"), "Voz B")

    def test_sin_voces_no_toca_la_voz_secundaria(self):
        dialogo = self._dialogo({"voz_secundaria": "Voz guardada"}, voces=())
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        self.assertEqual(dialogo._config["voz_secundaria"], "Voz guardada")
        parser = config._mk_parser()
        parser.read(self.ruta / "config.ini", encoding="utf-8")
        self.assertEqual(parser.get("voz", "voz_secundaria"), "")

    def test_el_respaldo_secundario_sigue_al_motor_efectivo(self):
        con_sapi = self._dialogo_por_motor(
            {"motor": "sapi"}, {"sapi": ["Voz A"]})
        bloque = self._bloque(con_sapi)
        self.assertFalse(bloque.lbl_respaldo.IsShown())
        self.assertFalse(bloque.cho_respaldo.IsShown())
        con_phonon = self._dialogo_por_motor(
            {"motor": "phonon"}, {"phonon": ["Phono A"]})
        self.assertTrue(self._bloque(con_phonon).lbl_respaldo.IsShown())
        con_eleven = self._dialogo_por_motor(
            {"motor": "elevenlabs"}, {"elevenlabs": []})
        self.assertTrue(self._bloque(con_eleven).lbl_respaldo.IsShown())
        propio = self._dialogo_por_motor(
            {"motor": "sapi", "motor_secundaria": "phonon"},
            {"sapi": ["Voz A"], "phonon": ["Phono A"]})
        self.assertTrue(self._bloque(propio).lbl_respaldo.IsShown())

    def _dialogo_por_motor(self, configuracion, voces_por_motor):
        with mock.patch.object(
                motores, "listar_voces",
                side_effect=lambda motor: list(voces_por_motor.get(motor, []))):
            dialogo = gui_preferencias.PreferenciasDialog(
                None, configuracion)
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_el_cuadro_de_motor_tiene_las_opciones_locales(self):
        bloque = self._bloque(self._dialogo())
        cho = bloque.cho_motor
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         [IGUAL_PRINCIPAL, "Windows SAPI 5", "Windows OneCore",
                          "Phonon, voces locales", "Piper, voces locales"])
        self.assertEqual(cho.GetName(), "Motor de la voz secundaria")

    def test_cambiar_el_motor_recarga_las_voces_de_ese_motor(self):
        por_motor = {"sapi": ["Voz A"], "phonon": ["Phono A", "Phono B"]}
        dialogo = self._dialogo_por_motor(
            {"motor": "sapi", "motor_secundaria": ""}, por_motor)
        bloque = self._bloque(dialogo)
        with mock.patch.object(
                motores, "listar_voces",
                side_effect=lambda motor: list(por_motor.get(motor, []))):
            bloque.cho_motor.SetStringSelection("Phonon, voces locales")
            bloque._on_motor_cambiado(None)
        cho = bloque.cho_voz
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         [IGUAL_PRINCIPAL, "Phono A", "Phono B"])

    def test_guardar_escribe_motor_secundaria(self):
        dialogo = self._dialogo_por_motor(
            {"motor": "sapi", "motor_secundaria": "phonon"},
            {"sapi": [], "phonon": ["Phono A"]})
        with mock.patch.object(gui_preferencias._snd, "reproducir"),                 mock.patch.object(preferencias_transmision, "anunciar"),                 mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        self.assertEqual(dialogo._config["motor_secundaria"], "phonon")
        parser = config._mk_parser()
        parser.read(self.ruta / "config.ini", encoding="utf-8")
        self.assertEqual(parser.get("voz", "motor_secundaria"), "phonon")

    def test_guardar_con_igual_escribe_motor_vacio(self):
        dialogo = self._dialogo_por_motor(
            {"motor": "sapi", "motor_secundaria": "phonon"},
            {"sapi": [], "phonon": ["Phono A"]})
        bloque = self._bloque(dialogo)
        bloque.cho_motor.SetSelection(0)
        bloque._on_motor_cambiado(None)
        with mock.patch.object(gui_preferencias._snd, "reproducir"),                 mock.patch.object(preferencias_transmision, "anunciar"),                 mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        self.assertEqual(dialogo._config["motor_secundaria"], "")
        parser = config._mk_parser()
        parser.read(self.ruta / "config.ini", encoding="utf-8")
        self.assertEqual(parser.get("voz", "motor_secundaria"), "")

    def test_probar_secundaria_usa_el_motor_elegido(self):
        dialogo = self._dialogo_por_motor(
            {"motor": "sapi", "motor_secundaria": "phonon"},
            {"sapi": ["Voz A"], "phonon": ["Phono A", "Phono B"]})
        pagina = dialogo.pagina_voz
        bloque = self._bloque(dialogo)
        bloque.cho_voz.SetSelection(2)
        bloque.sp_velocidad.SetValue(60)
        bloque.sp_volumen.SetValue(30)
        pagina.sp_tono.SetValue(70)
        pagina._prueba = mock.Mock()
        pagina._probar_voz_secundaria()
        pagina._prueba.probar_motor.assert_called_once_with(
            "phonon", 1, 60, 30, 70)

    def test_sin_voces_en_el_motor_secundario_muestra_el_aviso(self):
        dialogo = self._dialogo_por_motor(
            {"motor": "sapi", "motor_secundaria": "phonon"},
            {"sapi": ["Voz A"], "phonon": []})
        cho = self._bloque(dialogo).cho_voz
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         ["(no hay voces instaladas: usa Administrar voces)"])
        self.assertFalse(cho.IsEnabled())

    def test_el_orden_de_tab_del_grupo(self):
        bloque = self._bloque(self._dialogo())
        padre = bloque.cho_motor.GetParent()
        hijos = list(padre.GetChildren())
        orden = [bloque.cho_motor, bloque.cho_voz, bloque.sp_velocidad,
                 bloque.sp_volumen, bloque.btn_probar, bloque.cho_respaldo]
        posiciones = [hijos.index(control) for control in orden]
        self.assertEqual(posiciones, sorted(posiciones))

    def test_el_respaldo_empieza_por_igual_y_trae_las_voces_de_windows(self):
        dialogo = self._dialogo()
        cho = self._bloque(dialogo).cho_respaldo
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         [IGUAL_RESPALDO, "Voz A", "Voz B"])

    def test_cambiar_de_motor_rellena_la_lista_y_conserva_la_guardada(self):
        def voces(motor):
            return {"sapi": ["Voz A", "Voz B"],
                    "onecore": ["Voz C", "Voz B"]}.get(motor, [])

        with mock.patch.object(motores, "listar_voces", side_effect=voces):
            dialogo = gui_preferencias.PreferenciasDialog(
                None, {"motor": "sapi", "voz_secundaria": "Voz B"})
        self.addCleanup(destruir, dialogo)
        bloque = self._bloque(dialogo)
        pagina = dialogo.pagina_voz
        pagina.cho_motor.SetSelection(motores.MOTORES.index("onecore"))
        with mock.patch.object(motores, "listar_voces", side_effect=voces):
            pagina._on_motor_cambiado(None)
        self.assertEqual(
            [bloque.cho_voz.GetString(i)
             for i in range(bloque.cho_voz.GetCount())],
            [IGUAL_PRINCIPAL, "Voz C", "Voz B"])
        self.assertEqual(bloque.cho_voz.GetStringSelection(), "Voz B")

    def test_cambiar_de_motor_sin_la_voz_guardada_queda_en_igual(self):
        def voces(motor):
            return {"sapi": ["Voz A", "Voz B"],
                    "onecore": ["Voz C"]}.get(motor, [])

        with mock.patch.object(motores, "listar_voces", side_effect=voces):
            dialogo = gui_preferencias.PreferenciasDialog(
                None, {"motor": "sapi", "voz_secundaria": "Voz B"})
        self.addCleanup(destruir, dialogo)
        bloque = self._bloque(dialogo)
        pagina = dialogo.pagina_voz
        pagina.cho_motor.SetSelection(motores.MOTORES.index("onecore"))
        with mock.patch.object(motores, "listar_voces", side_effect=voces):
            pagina._on_motor_cambiado(None)
        self.assertEqual(bloque.cho_voz.GetStringSelection(), IGUAL_PRINCIPAL)

    def test_la_clave_comprobada_rellena_la_lista(self):
        dialogo = self._dialogo({"motor": "elevenlabs",
                                 "voz_secundaria": "Voz B"})
        bloque = self._bloque(dialogo)
        dialogo.pagina_voz._clave_ok(
            [("uno", "Voz A"), ("dos", "Voz B")], 0, None, False)
        self.assertEqual(
            [bloque.cho_voz.GetString(i)
             for i in range(bloque.cho_voz.GetCount())],
            [IGUAL_PRINCIPAL, "Voz A", "Voz B"])
        self.assertEqual(bloque.cho_voz.GetStringSelection(), "Voz B")

    def test_la_clave_fallida_deja_solo_igual_que_la_principal(self):
        dialogo = self._dialogo({"motor": "elevenlabs",
                                 "voz_secundaria": "Voz B"})
        bloque = self._bloque(dialogo)
        with mock.patch("guyrapu.ui.preferencias_voz.anunciar"):
            dialogo.pagina_voz._clave_fallo("no sirve")
        self.assertEqual(
            [bloque.cho_voz.GetString(i)
             for i in range(bloque.cho_voz.GetCount())],
            [IGUAL_PRINCIPAL])
        self.assertEqual(bloque.cho_voz.GetStringSelection(), IGUAL_PRINCIPAL)

    def test_probar_secundaria_usa_su_voz_sus_ajustes_y_el_tono_principal(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_voz
        bloque = self._bloque(dialogo)
        pagina.cho_voz.SetSelection(1)
        pagina.sp_tono.SetValue(70)
        bloque.cho_voz.SetSelection(2)
        bloque.sp_velocidad.SetValue(60)
        bloque.sp_volumen.SetValue(30)
        pagina._prueba = mock.Mock()
        bloque.btn_probar.Command(gui.wx.CommandEvent(
            gui.wx.EVT_BUTTON.typeId, bloque.btn_probar.GetId()))
        pagina._prueba.probar_motor.assert_called_once_with(
            "sapi", 1, 60, 30, 70)

    def test_probar_secundaria_en_igual_usa_la_voz_principal(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_voz
        bloque = self._bloque(dialogo)
        pagina.cho_voz.SetSelection(1)
        bloque.cho_voz.SetSelection(0)
        bloque.sp_velocidad.SetValue(60)
        bloque.sp_volumen.SetValue(30)
        pagina._prueba = mock.Mock()
        pagina._probar_voz_secundaria()
        pagina._prueba.probar_motor.assert_called_once_with(
            "sapi", 1, 60, 30, pagina.sp_tono.GetValue())

    def test_probar_secundaria_con_eleven_sin_clave_avisa_lo_mismo(self):
        dialogo = self._dialogo({"motor": "elevenlabs"})
        pagina = dialogo.pagina_voz
        with mock.patch("guyrapu.ui.preferencias_voz.anunciar") as anunciar:
            pagina._probar_voz_secundaria()
        anunciar.assert_called_once_with("Primero comprueba la clave.")

    def test_el_grupo_va_despues_de_los_controles_de_elevenlabs(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_voz
        bloque = self._bloque(dialogo)
        hijos = pagina._pag_voz_panel.GetChildren()
        self.assertGreater(hijos.index(bloque.cho_voz.GetParent()),
                           hijos.index(pagina._eleven.cho_voz_respaldo))

    def test_los_mnemonicos_de_voces_no_se_repiten(self):
        dialogo = self._dialogo()
        pagina = next(p for p in dialogo._paginas()
                      if p.GetName() == "PagVoz")
        letras = _letras_acceso(pagina)
        self.assertEqual(len(letras), len(set(letras)), letras)


class TestAplicarVozSecundariaEnCaliente(unittest.TestCase):
    """Sin ventanas: la aplicación en caliente llama al worker."""

    def test_aplicar_llama_a_configurar_voz_secundaria(self):
        frame = mock.Mock()
        frame._config = {"motor": "sapi", "voz": "Voz A", "atajos_raw": {},
                         "voz_secundaria": "Voz B",
                         "velocidad_secundaria": 25,
                         "volumen_secundaria": 0.4,
                         "voz_respaldo_secundaria": "Respaldo B"}
        frame._worker.motor_activo.return_value = "sapi"
        frame._conectado = False
        frame._voz_idx = 0
        with mock.patch("guyrapu.ui.gui.anunciar"):
            gui_aplicar_preferencias.aplicar_en_caliente(frame)
        frame._worker.configurar_voz_secundaria.assert_called_once_with(
            "Voz B", 25, 0.4, "Respaldo B", "")


if __name__ == "__main__":
    unittest.main()
