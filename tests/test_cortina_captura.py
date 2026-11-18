# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la oferta de cambiar el método de captura, sin ventana."""

import unittest
from unittest import mock

from guyrapu.obs import obs_prevuelo
from guyrapu.ui import cortina_captura


def _revision(cortina=("Pantalla",)):
    return obs_prevuelo.Revision(
        "TikTok", "TikTok", "TikTok", 720, 1280, "Escena",
        (), (), False, (), cortina=cortina)


class _Hilo:
    def __init__(self, target, nombre):
        self._target = target

    def start(self):
        self._target()


class OfrecerTest(unittest.TestCase):
    def _parches(self, respuesta=True, cambiar=None):
        cliente = mock.Mock()
        parches = [
            mock.patch.object(cortina_captura.confirmar, "preguntar",
                              return_value=respuesta),
            mock.patch.object(cortina_captura.obs_cliente, "leer_ajustes",
                              return_value=mock.sentinel.ajustes),
            mock.patch.object(cortina_captura.obs_cliente, "ClienteObs",
                              return_value=cliente),
            mock.patch.object(cortina_captura.captura_cortina, "cambiar",
                              cambiar or mock.Mock()),
            mock.patch.object(cortina_captura.diagnostico, "crear_hilo",
                              side_effect=lambda f, n: _Hilo(f, n)),
            mock.patch.object(cortina_captura.wx, "CallAfter",
                              side_effect=lambda f, *a: f(*a)),
            mock.patch.object(cortina_captura, "anunciar"),
            mock.patch.object(cortina_captura._snd, "reproducir"),
            mock.patch.object(cortina_captura, "avisar"),
            mock.patch.object(cortina_captura.obs_cliente,
                              "mensaje_de_fallo_obs"),
        ]
        iniciados = [parche.start() for parche in parches]
        for parche in parches:
            self.addCleanup(parche.stop)
        return cliente, dict(zip((
            "preguntar", "leer_ajustes", "cliente", "cambiar", "crear_hilo",
            "call_after", "anunciar", "sonar", "avisar", "traducir"),
            iniciados))

    def test_cambiar_continua_sin_cortina_y_anuncia_con_el_sonido_listo(self):
        revision = _revision()
        continuadas = []
        cliente, parches = self._parches()
        cortina_captura.ofrecer(mock.sentinel.padre, revision,
                                continuadas.append)
        args, kwargs = parches["preguntar"].call_args
        self.assertEqual(args[0], mock.sentinel.padre)
        self.assertEqual(
            args[1],
            "La cortina de pantalla de NVDA deja en negro la captura de "
            "pantalla Pantalla. ¿Cambiar su método de captura a Windows 10? "
            "Se puede volver a cambiar en las propiedades de la fuente, en "
            "OBS.")
        self.assertEqual(args[2], "Antes de transmitir")
        self.assertEqual(args[3], "&Cambiar a Windows 10")
        self.assertEqual(args[4], "&Dejar como está")
        self.assertTrue(kwargs.get("predeterminado_si", True))
        parches["cambiar"].assert_called_once_with(cliente, ("Pantalla",))
        parches["sonar"].assert_called_once_with("listo")
        parches["anunciar"].assert_called_once_with(
            "Método de captura cambiado a Windows 10: Pantalla.")
        self.assertEqual(len(continuadas), 1)
        self.assertEqual(continuadas[0].cortina, ())

    def test_dejar_como_esta_continua_con_la_misma_sin_tocar_obs(self):
        revision = _revision()
        continuadas = []
        _cliente, parches = self._parches(respuesta=False)
        cortina_captura.ofrecer(mock.sentinel.padre, revision,
                                continuadas.append)
        parches["cliente"].assert_not_called()
        parches["cambiar"].assert_not_called()
        self.assertEqual(continuadas, [revision])

    def test_si_obs_falla_abre_el_cuadro_y_continua_con_la_misma(self):
        revision = _revision()
        continuadas = []
        fallo = RuntimeError("OBS no responde")
        parches = self._parches(cambiar=mock.Mock(side_effect=fallo))[1]
        parches["traducir"].return_value = "OBS no responde."
        cortina_captura.ofrecer(mock.sentinel.padre, revision,
                                continuadas.append)
        parches["avisar"].assert_called_once_with(
            "No se pudo cambiar el método de captura a Windows 10. OBS no "
            "responde. Se puede cambiar a mano en las propiedades de la "
            "fuente, en OBS.", "error", error=True)
        self.assertEqual(continuadas, [revision])

    def test_sin_cortina_no_pregunta_ni_toca_obs(self):
        revision = _revision(cortina=())
        continuadas = []
        _cliente, parches = self._parches()
        cortina_captura.ofrecer(mock.sentinel.padre, revision,
                                continuadas.append)
        parches["preguntar"].assert_not_called()
        parches["cliente"].assert_not_called()
        self.assertEqual(continuadas, [revision])


if __name__ == "__main__":
    unittest.main()
