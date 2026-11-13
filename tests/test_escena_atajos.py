# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los atajos de escena e IA fuera de la app.

Todo sin ventanas: el marco es un doble que anota los atajos registrados y
`wx.CallAfter` corre en el acto.
"""

import unittest
from unittest import mock

import wx

from guyrapu.core.atajos import Atajo
from guyrapu.ui import escena_atajos


class MarcoFalso:
    """Marco y ventana de wx a la vez: anota los atajos del sistema."""

    def __init__(self, config=None, atajos=None):
        self._config = dict(config or {})
        self._atajos = dict(atajos or {})
        self.registrados = {}
        self.fallan_vk = set()
        self.manejadores = {}
        self.descripciones = 0

    def _describir_escena(self):
        self.descripciones += 1

    def RegisterHotKey(self, ident, mods, vk):
        if vk in self.fallan_vk:
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


def _atajos(usuario=False):
    return {
        "describir_escena": Atajo(
            "describir_escena", "ctrl+f7" if usuario else "ctrl+f2",
            "f7" if usuario else "f2"),
        "consulta_rapida_ia": Atajo(
            "consulta_rapida_ia",
            "ctrl+shift+f7" if usuario else "ctrl+shift+f2",
            "f7" if usuario else "f2"),
    }


class TestRegistroDeAtajos(unittest.TestCase):

    def _crear(self, marco):
        with mock.patch.object(escena_atajos.wx, "CallAfter",
                               side_effect=lambda fn, *a: fn(*a)), \
                mock.patch.object(escena_atajos, "anunciar"), \
                mock.patch.object(escena_atajos._snd, "reproducir"):
            return escena_atajos.EscenaAtajos(marco)

    def test_registra_las_dos_acciones_con_los_atajos_del_usuario(self):
        marco = MarcoFalso({"escena_atajos_globales": False},
                           _atajos(usuario=True))
        atajos = escena_atajos.EscenaAtajos(marco)
        marco._config["escena_atajos_globales"] = True
        with mock.patch.object(escena_atajos, "anunciar"), \
                mock.patch.object(escena_atajos._snd, "reproducir"):
            atajos.aplicar_preferencias()
        self.assertEqual(
            set(marco.registrados.values()),
            {(wx.MOD_CONTROL, 0x76),
             (wx.MOD_CONTROL | wx.MOD_SHIFT, 0x76)})
        self.assertTrue(atajos._globales.activos)

    def test_arranque_callado_sin_fallos(self):
        marco = MarcoFalso({"escena_atajos_globales": True}, _atajos())
        with mock.patch.object(escena_atajos.wx, "CallAfter",
                               side_effect=lambda fn, *a: fn(*a)), \
                mock.patch.object(escena_atajos, "anunciar") as anunciar, \
                mock.patch.object(escena_atajos._snd,
                                  "reproducir") as reproducir:
            escena_atajos.EscenaAtajos(marco)
        anunciar.assert_not_called()
        reproducir.assert_not_called()
        self.assertEqual(len(marco.registrados), 2)

    def test_arranque_con_fallo_avisa_con_el_tono_de_ocupado(self):
        marco = MarcoFalso({"escena_atajos_globales": True}, _atajos())
        marco.fallan_vk = {0x71}
        with mock.patch.object(escena_atajos.wx, "CallAfter",
                               side_effect=lambda fn, *a: fn(*a)), \
                mock.patch.object(escena_atajos, "anunciar") as anunciar, \
                mock.patch.object(escena_atajos._snd,
                                  "reproducir") as reproducir:
            escena_atajos.EscenaAtajos(marco)
        reproducir.assert_called_once_with("atajos_ocupados")
        self.assertIn("No se pudieron usar en cualquier aplicación",
                      anunciar.call_args.args[0])

    def test_activar_desde_preferencias_anuncia(self):
        marco = MarcoFalso({"escena_atajos_globales": False}, _atajos())
        atajos = escena_atajos.EscenaAtajos(marco)
        marco._config["escena_atajos_globales"] = True
        with mock.patch.object(escena_atajos, "anunciar") as anunciar, \
                mock.patch.object(escena_atajos._snd,
                                  "reproducir") as reproducir:
            atajos.aplicar_preferencias()
        anunciar.assert_called_once_with(
            "Atajos de escena e IA en cualquier aplicación")
        reproducir.assert_not_called()
        self.assertTrue(atajos._globales.activos)

    def test_desactivar_desde_preferencias_anuncia(self):
        marco = MarcoFalso({"escena_atajos_globales": True}, _atajos())
        atajos = self._crear(marco)
        marco._config["escena_atajos_globales"] = False
        with mock.patch.object(escena_atajos, "anunciar") as anunciar, \
                mock.patch.object(escena_atajos._snd,
                                  "reproducir") as reproducir:
            atajos.aplicar_preferencias()
        anunciar.assert_called_once_with(
            "Atajos de escena e IA solo en Guyrapu")
        reproducir.assert_not_called()
        self.assertFalse(atajos._globales.activos)

    def test_cada_accion_llama_a_su_funcion(self):
        marco = MarcoFalso({"escena_atajos_globales": False}, _atajos())
        atajos = escena_atajos.EscenaAtajos(marco)
        with mock.patch.object(escena_atajos.ia_consulta_rapida,
                               "consultar") as consultar:
            acciones = atajos._globales._acciones
            acciones["describir_escena"]()
            acciones["consulta_rapida_ia"]()
        self.assertEqual(marco.descripciones, 1)
        consultar.assert_called_once_with(marco)

    def test_un_fallo_al_aplicar_avisa_con_el_tono_de_ocupado(self):
        marco = MarcoFalso({"escena_atajos_globales": False}, _atajos())
        marco.fallan_vk = {0x71}
        atajos = escena_atajos.EscenaAtajos(marco)
        marco._config["escena_atajos_globales"] = True
        with mock.patch.object(escena_atajos, "anunciar") as anunciar, \
                mock.patch.object(escena_atajos._snd,
                                  "reproducir") as reproducir:
            atajos.aplicar_preferencias()
        reproducir.assert_called_once_with("atajos_ocupados")
        self.assertIn("No se pudieron usar en cualquier aplicación",
                      anunciar.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
