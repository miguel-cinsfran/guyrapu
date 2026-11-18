# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los atajos globales de lo que sale en el vídeo.

Comprueba la traducción a Windows, que cada combinación llame a su acción y
que un atajo ocupado se nombre una vez al arrancar. No abre ventanas: usa
una ventana doble que anota los registros.
"""

import types
import unittest
from unittest import mock

import wx

from guyrapu.core import config
from guyrapu.ui import comando_en_directo, interaccion_atajos
from guyrapu.ui.atajos_captura import atajo_legible
from guyrapu.ui.atajos_globales import combinacion_ctrl_alt_mayus

ORDEN = (
    ("video_pausar", "p"),
    ("video_saltar", "s"),
    ("video_vaciar", "v"),
    ("video_silenciar", "m"),
    ("video_panico", "q"),
    ("mensajes_automaticos_alternar", "a"),
)

MODS = wx.MOD_CONTROL | wx.MOD_ALT | wx.MOD_SHIFT


class _Ventana:
    """Ventana doble: registra, enlaza y además es el marco de la app."""

    def __init__(self, fallan=()):
        self.fallan = set(fallan)
        self.registrados = {}
        self.manejadores = {}
        self._atajos = {
            accion: types.SimpleNamespace(texto=config.ATAJOS_DEFAULTS[accion])
            for accion, _letra in ORDEN}

    def RegisterHotKey(self, ident, mods, vk):
        if vk in self.fallan:
            return False
        self.registrados[ident] = (mods, vk)
        return True

    def UnregisterHotKey(self, ident):
        self.registrados.pop(ident, None)
        return True

    def Bind(self, evento, manejador, id=-1):
        self.manejadores[id] = manejador

    def Unbind(self, evento, id=-1):
        self.manejadores.pop(id, None)


class TestCombinacionCtrlAltMayus(unittest.TestCase):

    def test_las_seis_de_fabrica_dan_su_letra(self):
        for accion, letra in ORDEN:
            with self.subTest(accion=accion):
                self.assertEqual(
                    combinacion_ctrl_alt_mayus(
                        config.ATAJOS_DEFAULTS[accion]),
                    (MODS, ord(letra.upper())))

    def test_acepta_los_ordenes_y_las_mayusculas(self):
        self.assertEqual(combinacion_ctrl_alt_mayus("ALT+SHIFT+CTRL+P"),
                         (MODS, ord("P")))
        self.assertEqual(combinacion_ctrl_alt_mayus(" shift + ctrl + alt + s "),
                         (MODS, ord("S")))

    def test_rechaza_lo_que_no_es_ctrl_alt_mayus_y_letra(self):
        for texto in ("ctrl+alt+p", "ctrl+shift+p", "alt+shift+p",
                      "ctrl+alt+shift+1", "ctrl+alt+shift+left",
                      "ctrl+alt+shift", "", None, "basura"):
            with self.subTest(texto=texto):
                self.assertIsNone(combinacion_ctrl_alt_mayus(texto))


class TestInteraccionAtajos(unittest.TestCase):

    def _atajos(self, ventana=None):
        ventana = ventana or _Ventana()
        with mock.patch.object(interaccion_atajos.wx, "CallAfter"):
            atajos = interaccion_atajos.InteraccionAtajos(ventana)
            atajos.activar_arranque()
        return atajos, ventana

    def test_registra_los_seis_con_su_accion(self):
        ventana = _Ventana()
        acciones = (
            "alternar_pausa", "saltar", "vaciar", "alternar_silencio",
            "alternar_panico", "alternar_mensajes")
        parches = [mock.patch.object(comando_en_directo, nombre)
                   for nombre in acciones]
        iniciados = [parche.start() for parche in parches]
        try:
            _atajos, ventana = self._atajos(ventana)
            self.assertEqual(len(ventana.registrados), 6)
            for accion, letra in ORDEN:
                indice = interaccion_atajos.ORDEN.index(accion)
                ident = interaccion_atajos.BASE_IDS + indice
                self.assertEqual(ventana.registrados[ident],
                                 (MODS, ord(letra.upper())))
            for identificador, manejador in list(ventana.manejadores.items()):
                with mock.patch.object(interaccion_atajos.wx, "CallAfter",
                                       side_effect=lambda f: f()):
                    manejador(None)
        finally:
            for parche in parches:
                parche.stop()
        for doble in iniciados:
            doble.assert_called_once_with(ventana)

    def test_un_atajo_ocupado_se_nombra_una_vez(self):
        ventana = _Ventana(fallan={ord("P")})
        anuncios = []
        with mock.patch.object(interaccion_atajos, "anunciar",
                               side_effect=anuncios.append), \
                mock.patch.object(interaccion_atajos._snd,
                                  "reproducir") as reproducir:
            self._atajos(ventana)
        self.assertEqual(len(anuncios), 1)
        self.assertIn(atajo_legible("ctrl+alt+shift+p"), anuncios[0])
        self.assertIn("otra aplicación", anuncios[0])
        reproducir.assert_called_once_with("atajos_ocupados")


if __name__ == "__main__":
    unittest.main()
