# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la política de reconexión de TikTok (módulo puro)."""

import json
import unittest

from guyrapu.capture import tiktok_errores as errores
from guyrapu.capture import tiktok_reconexion as rec


def _exc(nombre, texto=""):
    return type(nombre, (Exception,), {})(texto)


class TestDesenlace(unittest.TestCase):

    def _base(self, **cambios):
        params = {"err": RuntimeError("corte"), "parado": False,
                  "conecto_alguna": False, "offline_pasajero": False,
                  "reconectar": True}
        params.update(cambios)
        return params

    def test_version_incompatible_termina_permanente(self):
        tipo, texto = rec.desenlace(**self._base(err=ImportError("vieja")))
        self.assertEqual(tipo, "error_permanente")
        self.assertIn("no es compatible", texto)

    def test_version_con_attribute_error(self):
        tipo, _texto = rec.desenlace(**self._base(err=AttributeError("x")))
        self.assertEqual(tipo, "error_permanente")

    def test_parada_pide_silencio(self):
        desenlace = rec.desenlace(**self._base(err=RuntimeError("corte"),
                                               parado=True))
        self.assertIsNotNone(desenlace)
        tipo, _texto = desenlace
        self.assertIsNone(tipo)

    def test_permanente_termina(self):
        exc = _exc("UserOfflineError", "offline")
        tipo, texto = rec.desenlace(**self._base(err=exc))
        self.assertEqual(tipo, "error_permanente")
        self.assertIn("no está en directo", texto)

    def test_offline_pasajero_antes_de_conectar_sigue(self):
        exc = _exc("UserOfflineError", "offline")
        self.assertIsNone(rec.desenlace(**self._base(
            err=exc, offline_pasajero=True, conecto_alguna=False)))

    def test_offline_despues_de_conectar_termina(self):
        exc = _exc("UserOfflineError", "offline")
        tipo, _texto = rec.desenlace(**self._base(
            err=exc, offline_pasajero=True, conecto_alguna=True))
        self.assertEqual(tipo, "error_permanente")

    def test_fin_de_directo(self):
        tipo, texto = rec.desenlace(**self._base(err=None))
        self.assertEqual(tipo, "fin_directo")
        self.assertEqual(texto, "El directo de TikTok terminó.")

    def test_reconectar_desactivado_termina_con_error(self):
        tipo, texto = rec.desenlace(**self._base(
            err=RuntimeError("corte"), reconectar=False))
        self.assertEqual(tipo, "error")
        self.assertIn("No se pudo conectar", texto)

    def test_error_comun_sigue(self):
        self.assertIsNone(rec.desenlace(**self._base(
            err=RuntimeError("microcorte"))))

    def test_orden_version_antes_que_parada(self):
        desenlace = rec.desenlace(**self._base(err=ImportError("vieja"),
                                               parado=True))
        tipo, texto = desenlace
        self.assertEqual(tipo, "error_permanente")
        self.assertIn("no es compatible", texto)


class TestTextos(unittest.TestCase):

    def test_agotado(self):
        self.assertEqual(
            rec.texto_agotado(3), "Se agotaron los 3 intentos de reconexión.")

    def test_reintento_con_maximo(self):
        self.assertEqual(
            rec.texto_reintento(10, 1, 3),
            "Reintentando en 10 segundos (intento 1 de 3)…")

    def test_reintento_sin_maximo(self):
        self.assertEqual(
            rec.texto_reintento(10, 2, 0),
            "Reintentando en 10 segundos (intento 2)…")


class TestSalaNoLista(unittest.TestCase):
    """Un directo recién empezado todavía no da los datos de la sala."""

    def _sala(self):
        return _exc("AgeRestrictedError", "Age restricted stream")

    def test_es_sala_no_lista_reconoce_por_nombre(self):
        self.assertTrue(errores.es_sala_no_lista(self._sala()))
        self.assertFalse(errores.es_sala_no_lista(RuntimeError("corte")))

    def test_el_primero_anuncia_y_espera(self):
        tipo, texto = rec.sala_no_lista(
            self._sala(), conecto_alguna=False, primer_fallo=None, ahora=10.0)
        self.assertEqual(tipo, "reintentando")
        self.assertEqual(texto, "TikTok todavía no deja leer el chat de este "
                                "directo. Se sigue intentando.")

    def test_los_siguientes_esperan_sin_anunciar(self):
        tipo, texto = rec.sala_no_lista(
            self._sala(), conecto_alguna=False, primer_fallo=10.0, ahora=20.0)
        self.assertEqual(tipo, "reintentando")
        self.assertIsNone(texto)

    def test_a_los_180_termina_con_el_error(self):
        tipo, texto = rec.sala_no_lista(
            self._sala(), conecto_alguna=False, primer_fallo=10.0,
            ahora=10.0 + rec.LIMITE_SALA_NO_LISTA)
        self.assertEqual(tipo, "error")
        self.assertEqual(texto, "TikTok no deja leer el chat de este directo. "
                                "Puede estar restringido por edad.")

    def test_si_ya_conecto_decide_como_hoy(self):
        self.assertIsNone(rec.sala_no_lista(
            self._sala(), conecto_alguna=True, primer_fallo=10.0, ahora=20.0))

    def test_otro_error_decide_como_hoy(self):
        self.assertIsNone(rec.sala_no_lista(
            RuntimeError("corte"), conecto_alguna=False, primer_fallo=10.0,
            ahora=20.0))


class TestEsperaTras(unittest.TestCase):

    def test_sin_limite_devuelve_la_espera(self):
        self.assertEqual(rec.espera_tras(RuntimeError("corte"), 10), 10)

    def test_con_limite_sube_a_la_espera_del_bloqueo(self):
        exc = json.JSONDecodeError("Expecting value", "", 0)
        self.assertEqual(rec.espera_tras(exc, 10), errores.ESPERA_LIMITE)

    def test_con_limite_respeta_una_espera_mayor(self):
        exc = json.JSONDecodeError("Expecting value", "", 0)
        self.assertEqual(rec.espera_tras(exc, 120), 120)


if __name__ == "__main__":
    unittest.main()
