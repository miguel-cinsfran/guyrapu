# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los atajos globales de los disparadores.

Comprueba que se registran las nueve combinaciones, que cada una dispara su
número y que un atajo ocupado se nombra una vez. No abre ventanas: usa una
ventana doble que anota los registros.
"""

import unittest
from unittest import mock

import wx

from guyrapu.ui import botonera_atajos, disparadores_en_vivo
from guyrapu.ui.atajos_captura import atajo_legible

MODS = wx.MOD_CONTROL | wx.MOD_ALT | wx.MOD_SHIFT


class _Ventana:
    """Ventana doble: registra, enlaza y además es el marco de la app."""

    def __init__(self, fallan=()):
        self.fallan = set(fallan)
        self.registrados = {}
        self.manejadores = {}

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


class TestBotoneraAtajos(unittest.TestCase):

    def _atajos(self, ventana=None):
        ventana = ventana or _Ventana()
        with mock.patch.object(botonera_atajos.wx, "CallAfter"):
            atajos = botonera_atajos.BotoneraAtajos(ventana)
            atajos.activar_arranque()
        return atajos, ventana

    def test_registra_las_nueve_combinaciones_con_ids_desde_la_base(self):
        _atajos, ventana = self._atajos()
        self.assertEqual(len(ventana.registrados), 9)
        for numero in range(1, 10):
            ident = botonera_atajos.BASE_IDS + numero - 1
            self.assertEqual(ventana.registrados[ident],
                             (MODS, ord(str(numero))))

    def test_cada_combinacion_dispara_su_numero(self):
        _atajos, ventana = self._atajos()
        with mock.patch.object(disparadores_en_vivo, "disparar") as disparar:
            for manejador in ventana.manejadores.values():
                with mock.patch.object(botonera_atajos.wx, "CallAfter",
                                       side_effect=lambda f: f()):
                    manejador(None)
        self.assertEqual(
            [llamada.args for llamada in disparar.call_args_list],
            [(ventana, numero) for numero in range(1, 10)])

    def test_p7_un_atajo_ocupado_se_nombra_una_vez(self):
        ventana = _Ventana(fallan={ord("4")})
        anuncios = []
        with mock.patch.object(botonera_atajos, "anunciar",
                               side_effect=anuncios.append), \
                mock.patch.object(botonera_atajos._snd,
                                  "reproducir") as reproducir:
            self._atajos(ventana)
        self.assertEqual(len(anuncios), 1)
        self.assertIn(atajo_legible("ctrl+alt+shift+4"), anuncios[0])
        self.assertIn("otra aplicación", anuncios[0])
        reproducir.assert_called_once_with("atajos_ocupados")


if __name__ == "__main__":
    unittest.main()
