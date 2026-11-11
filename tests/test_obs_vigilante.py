# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import unittest
from unittest import mock

from guyrapu.obs import obs_cliente
from guyrapu.obs import obs_vigilante
from guyrapu.obs.obs_vigilante import (
    EstadoObs, INTERVALO_SIN_OBS, INTERVALO_SONDEO, PLAZO_FRESCURA,
    VigilanteObs, dato_fresco)


class TestFrescura(unittest.TestCase):

    def test_dato_recien_tomado_sirve(self):
        self.assertTrue(dato_fresco(100.0, 100.1))

    def test_dato_justo_en_el_limite_sirve(self):
        self.assertTrue(dato_fresco(100.0, 100.0 + PLAZO_FRESCURA))

    def test_dato_pasado_no_sirve(self):
        self.assertFalse(dato_fresco(100.0, 100.0 + PLAZO_FRESCURA + 0.1))

    def test_sin_sondeo_previo_no_sirve(self):
        self.assertFalse(dato_fresco(None, 100.0))

    def test_estado_con_sondeo_reciente_devuelve_estado_guardado(self):
        vigilante = VigilanteObs()
        vigilante._estado = EstadoObs(escena="Escena actual")
        vigilante._ultimo_sondeo = 100.0

        self.assertEqual(vigilante.estado(100.1), vigilante._estado)

    def test_estado_con_sondeo_caducado_devuelve_none(self):
        vigilante = VigilanteObs()
        vigilante._estado = EstadoObs(escena="Escena vieja")
        vigilante._ultimo_sondeo = 100.0

        self.assertIsNone(vigilante.estado(100.0 + PLAZO_FRESCURA + 0.1))


class TestParada(unittest.TestCase):

    def _vigilar_con(self, fallo_en_vuelo, en_ejecucion=lambda: True):
        gestor = mock.Mock(conectado=True)
        vigilante = VigilanteObs(crear_gestor=lambda: gestor,
                                 en_ejecucion=en_ejecucion)

        def estado_transmision(parada):
            if fallo_en_vuelo:
                vigilante._parada.set()
                raise obs_cliente.ObsError("Operación cancelada.")
            raise RuntimeError("OBS no contesta")

        gestor.estado_transmision.side_effect = estado_transmision
        # El bucle no termina solo: se detiene desde el cierre que sigue al
        # primer fallo.
        gestor.cerrar.side_effect = vigilante._parada.set
        logger = mock.Mock()
        with mock.patch.object(obs_vigilante.diagnostico, "obtener_logger",
                               return_value=logger), \
                mock.patch.object(obs_vigilante, "INTERVALO_SONDEO", 0), \
                mock.patch.object(obs_vigilante, "INTERVALO_SIN_OBS", 0):
            vigilante._vigilar()
        return logger, gestor

    def test_detener_con_peticion_en_vuelo_no_avisa_que_obs_no_responde(self):
        # Esa advertencia se lee en voz alta: al cerrar la app sonaba
        # «OBS no responde» sin que OBS hubiera fallado.
        logger, gestor = self._vigilar_con(fallo_en_vuelo=True)
        logger.warning.assert_not_called()
        gestor.cerrar.assert_called()

    def test_fallo_real_sigue_avisando(self):
        logger, _ = self._vigilar_con(fallo_en_vuelo=False)
        logger.warning.assert_called_once_with("OBS no responde; se reintentará")

    def test_sin_obs_en_ejecucion_no_avisa_que_no_responde(self):
        logger, _ = self._vigilar_con(fallo_en_vuelo=False,
                                      en_ejecucion=lambda: False)
        logger.warning.assert_not_called()
        logger.debug.assert_called()

    def test_si_no_se_puede_comprobar_la_ejecucion_avisa(self):
        def en_ejecucion():
            raise OSError("tasklist")

        logger, _ = self._vigilar_con(fallo_en_vuelo=False,
                                      en_ejecucion=en_ejecucion)
        logger.warning.assert_called_once_with("OBS no responde; se reintentará")


class TestAnuncios(unittest.TestCase):

    def _vigilar(self, en_ejecucion, fallos):
        gestor = mock.Mock(conectado=True)
        gestor.estado_transmision.side_effect = (
            [RuntimeError("OBS no contesta")] * fallos + [{}])
        gestor.estado_grabacion.return_value = {}
        gestor.escena_al_aire.return_value = ""
        anuncios = []
        vigilante = VigilanteObs(
            crear_gestor=lambda: gestor, en_ejecucion=en_ejecucion,
            al_anunciar=lambda frase, sonido: anuncios.append((frase, sonido)))
        vigilante._parada = _ParadaPorEsperas(fallos + 1)
        with mock.patch.object(obs_vigilante.diagnostico, "obtener_logger",
                               return_value=mock.Mock()), \
                mock.patch.object(obs_vigilante, "INTERVALO_SONDEO", 0), \
                mock.patch.object(obs_vigilante, "INTERVALO_SIN_OBS", 0):
            vigilante._vigilar()
        return anuncios

    def test_avisa_la_caida_y_la_vuelta_una_vez_cada_una(self):
        anuncios = self._vigilar(lambda: True, fallos=3)
        self.assertEqual(anuncios, [
            ("OBS no responde. Se sigue intentando.", "obs_sin_respuesta"),
            ("OBS volvió a responder.", "obs_responde"),
        ])

    def test_sin_obs_en_ejecucion_no_avisa_nada(self):
        self.assertEqual(self._vigilar(lambda: False, fallos=3), [])


class _ParadaPorEsperas:
    """Parada que deja correr un número fijo de esperas."""

    def __init__(self, esperas):
        self._esperas = esperas
        self.vistas = []

    def is_set(self):
        return len(self.vistas) >= self._esperas

    def set(self):
        self.vistas = [0] * self._esperas

    def clear(self):
        self.vistas = []

    def wait(self, plazo):
        self.vistas.append(plazo)


class TestRecuperacion(unittest.TestCase):

    def _vigilar(self, en_ejecucion):
        gestor = mock.Mock(conectado=True)
        gestor.estado_transmision.side_effect = [
            RuntimeError("OBS no contesta"), {}]
        gestor.estado_grabacion.return_value = {}
        gestor.escena_al_aire.return_value = ""
        vigilante = VigilanteObs(crear_gestor=lambda: gestor,
                                 en_ejecucion=en_ejecucion)
        vigilante._parada = _ParadaPorEsperas(2)
        logger = mock.Mock()
        with mock.patch.object(obs_vigilante.diagnostico, "obtener_logger",
                               return_value=logger), \
                mock.patch.object(obs_vigilante, "INTERVALO_SONDEO", 0), \
                mock.patch.object(obs_vigilante, "INTERVALO_SIN_OBS", 0):
            vigilante._vigilar()
        return logger

    def test_despues_de_avisar_el_fallo_anuncia_que_volvio(self):
        logger = self._vigilar(lambda: True)
        logger.info.assert_called_once_with("OBS volvió a responder")

    def test_despues_de_un_fallo_sin_obs_no_anuncia_que_volvio(self):
        logger = self._vigilar(lambda: False)
        logger.info.assert_not_called()


class _ParadaFalsa:
    """Parada que anota el plazo pedido y corta el ciclo tras la espera."""

    def __init__(self):
        self.esperas = []
        self._puesta = False

    def is_set(self):
        return self._puesta

    def set(self):
        self._puesta = True

    def clear(self):
        self._puesta = False

    def wait(self, plazo):
        self.esperas.append(plazo)
        self._puesta = True


class TestIntervalo(unittest.TestCase):

    def _ciclo_con(self, gestor):
        vigilante = VigilanteObs(crear_gestor=lambda: gestor)
        vigilante._parada = _ParadaFalsa()
        with mock.patch.object(obs_vigilante.diagnostico, "obtener_logger",
                               return_value=mock.Mock()):
            vigilante._vigilar()
        return vigilante._parada.esperas

    def test_con_obs_sin_responder_espera_quince_segundos(self):
        gestor = mock.Mock(conectado=True)
        gestor.estado_transmision.side_effect = RuntimeError("OBS no contesta")

        self.assertEqual(self._ciclo_con(gestor), [INTERVALO_SIN_OBS])
        self.assertEqual(INTERVALO_SIN_OBS, 15.0)

    def test_con_obs_respondiendo_vuelve_a_cinco_segundos(self):
        gestor = mock.Mock(conectado=True)
        gestor.estado_transmision.return_value = {}
        gestor.estado_grabacion.return_value = {}
        gestor.escena_al_aire.return_value = ""

        self.assertEqual(self._ciclo_con(gestor), [INTERVALO_SONDEO])
        self.assertEqual(INTERVALO_SONDEO, 5.0)
