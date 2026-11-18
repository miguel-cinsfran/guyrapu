# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Controles de medios con dobles de Windows y una prueba real de WinRT.

Los dobles reemplazan `get_for_window` y los tipos de WinRT, así que la
lógica se prueba sin el paquete. `TestControlesReales` habla con Windows de
verdad y se salta solo si el paquete no está instalado.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.music.modelo import EstadoMusica, Tema
from guyrapu.ui import controles_medios
from guyrapu.ui.musica_desde_fuera import DesdeFueraMusica
from tests.ventanas_prueba import app_de_prueba, destruir


class _VentanaFalsa:

    def GetHandle(self):
        return 1


class _PropiedadesFalsas:

    def __init__(self):
        self.title = ""
        self.artist = ""


class _ActualizadorFalso:

    def __init__(self):
        self.type = None
        self.music_properties = _PropiedadesFalsas()
        self.actualizado = False

    def update(self):
        self.actualizado = True


class _ControlesFalsos:

    def __init__(self):
        self.is_enabled = False
        for nombre in ("is_play_enabled", "is_pause_enabled",
                       "is_next_enabled", "is_previous_enabled",
                       "is_stop_enabled"):
            setattr(self, nombre, False)
        self.playback_status = None
        self.display_updater = _ActualizadorFalso()
        self.manejadores = []

    def add_button_pressed(self, manejador):
        self.manejadores.append(manejador)
        return len(self.manejadores)


class _BotonFalso:

    def __init__(self, nombre):
        self.name = nombre


ESTADO = EstadoMusica((Tema("C:/tema.mp3", "La canción", "La banda"),),
                      0, False, False, 60, False)
VACIO = EstadoMusica((), None, False, False, 60, False)


class TestControlesMedios(unittest.TestCase):

    def setUp(self):
        self.controles = _ControlesFalsos()
        self.fijar = mock.patch.object(
            controles_medios, "get_for_window",
            return_value=self.controles)
        self.fijar.start()
        self.addCleanup(self.fijar.stop)
        self.tipos = mock.patch.multiple(
            controles_medios,
            MediaPlaybackType=SimpleNamespace(MUSIC="música"),
            MediaPlaybackStatus=SimpleNamespace(PLAYING="reproduciendo",
                                                PAUSED="en pausa"))
        self.tipos.start()
        self.addCleanup(self.tipos.stop)
        self.ejecutadas = []

    def _desde_fuera(self, config=None, estado=None):
        self.caja_estado = [ESTADO if estado is None else estado]
        return DesdeFueraMusica(
            _VentanaFalsa(), config if config is not None else {}, {},
            lambda aviso: None, lambda: self.caja_estado[0],
            self.ejecutadas.append)

    def test_con_cola_prende_y_muestra_titulo_y_artista(self):
        self._desde_fuera().poner_al_dia()
        self.assertTrue(self.controles.is_enabled)
        self.assertTrue(self.controles.is_next_enabled)
        propiedades = self.controles.display_updater.music_properties
        self.assertEqual(propiedades.title, "La canción")
        self.assertEqual(propiedades.artist, "La banda")
        self.assertEqual(self.controles.playback_status, "reproduciendo")

    def test_en_pausa_muestra_el_estado_en_pausa(self):
        pausado = EstadoMusica(ESTADO.cola, 0, True, False, 60, False)
        self._desde_fuera(estado=pausado).poner_al_dia()
        self.assertEqual(self.controles.playback_status, "en pausa")

    def test_cola_vacia_apaga(self):
        desde_fuera = self._desde_fuera()
        desde_fuera.poner_al_dia()
        self.assertTrue(self.controles.is_enabled)
        self.caja_estado[0] = VACIO
        desde_fuera.poner_al_dia()
        self.assertFalse(self.controles.is_enabled)

    def test_casilla_desmarcada_apaga_aunque_haya_cola(self):
        config = {}
        desde_fuera = self._desde_fuera(config)
        desde_fuera.poner_al_dia()
        self.assertTrue(self.controles.is_enabled)
        config["musica_teclas_multimedia"] = False
        desde_fuera.poner_al_dia()
        self.assertFalse(self.controles.is_enabled)

    def test_un_boton_de_siguiente_corre_el_atajo_en_la_interfaz(self):
        self._desde_fuera().poner_al_dia()
        manejador = self.controles.manejadores[0]
        pendientes = []
        with mock.patch.object(
                controles_medios.wx, "CallAfter",
                side_effect=lambda funcion, *a: pendientes.append(
                    (funcion, a))):
            manejador(self.controles,
                      SimpleNamespace(button=_BotonFalso("NEXT")))
        self.assertEqual(self.ejecutadas, [])
        self.assertEqual(len(pendientes), 1)
        funcion, argumentos = pendientes[0]
        funcion(*argumentos)
        self.assertEqual(self.ejecutadas, ["musica_siguiente"])

    def test_un_boton_desconocido_no_hace_nada(self):
        self._desde_fuera().poner_al_dia()
        manejador = self.controles.manejadores[0]
        with mock.patch.object(controles_medios.wx, "CallAfter") as llamar:
            manejador(self.controles,
                      SimpleNamespace(button=_BotonFalso("RECORD")))
        llamar.assert_not_called()

    def test_sin_el_paquete_no_falla_y_lo_anota(self):
        with mock.patch.object(controles_medios, "get_for_window", None):
            with self.assertLogs(controles_medios.logger, "WARNING"):
                self._desde_fuera().poner_al_dia()
        self.assertFalse(self.controles.is_enabled)


@unittest.skipUnless(
    controles_medios.get_for_window is not None,
    "winrt no está instalado")
class TestControlesReales(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_get_for_window_prende_muestra_y_apaga(self):
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        marco.Show()
        wx.SafeYield()
        medios = controles_medios.ControlesMedios(marco, lambda accion: None)
        self.addCleanup(medios.soltar)
        medios.poner_al_dia(ESTADO, True)
        self.assertIsNotNone(medios._controles)
        self.assertTrue(medios._controles.is_enabled)
        propiedades = medios._controles.display_updater.music_properties
        self.assertEqual(propiedades.title, "La canción")
        self.assertEqual(propiedades.artist, "La banda")
        medios.poner_al_dia(VACIO, True)
        self.assertFalse(medios._controles.is_enabled)


if __name__ == "__main__":
    unittest.main()
