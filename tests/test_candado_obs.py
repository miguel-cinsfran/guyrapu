# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import threading
import time
import unittest

from guyrapu.obs import candado_obs


def esperar_a(condicion, limite=1.0):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return False


class PedidosTest(unittest.TestCase):
    def test_los_pedidos_que_cambian_la_salida(self):
        self.assertEqual(
            candado_obs.PEDIDOS_QUE_CAMBIAN,
            frozenset({"SetCurrentProfile", "CreateProfile", "RemoveProfile",
                       "SetVideoSettings"}))

    def test_los_pedidos_que_leen_el_estado(self):
        self.assertEqual(
            candado_obs.PEDIDOS_QUE_LEEN,
            frozenset({"GetStats", "GetStreamStatus", "GetRecordStatus",
                       "GetReplayBufferStatus", "GetVirtualCamStatus",
                       "GetOutputStatus", "GetOutputList"}))

    def test_los_demas_pedidos_no_se_vigilan(self):
        for tipo in ("GetSceneItemList", "GetVideoSettings",
                     "GetCurrentProgramScene", "GetSourceScreenshot",
                     "GetProfileParameter", "GetProfileList"):
            with self.subTest(tipo=tipo):
                self.assertNotIn(tipo, candado_obs.PEDIDOS_QUE_CAMBIAN)
                self.assertNotIn(tipo, candado_obs.PEDIDOS_QUE_LEEN)


class CandadoDelProcesoTest(unittest.TestCase):
    def test_el_escritor_es_reentrante(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir(escribe=True)
        candado.adquirir(escribe=True)
        candado.liberar(escribe=True)
        candado.liberar(escribe=True)
        tomado = []
        hilo = threading.Thread(
            target=lambda: (candado.adquirir(escribe=True), tomado.append(True)))
        hilo.start()
        hilo.join(1)
        self.assertEqual(tomado, [True])

    def test_el_escritor_puede_leer_sin_soltar(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir(escribe=True)
        candado.adquirir()
        candado.liberar()
        candado.liberar(escribe=True)

    def test_otro_escritor_espera_hasta_que_se_libera(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir(escribe=True)
        tomado = []

        def ejecutar():
            candado.adquirir(escribe=True)
            tomado.append(True)
            candado.liberar(escribe=True)

        hilo = threading.Thread(target=ejecutar)
        hilo.start()
        time.sleep(0.15)
        self.assertEqual(tomado, [])
        candado.liberar(escribe=True)
        hilo.join(1)
        self.assertEqual(tomado, [True])

    def test_la_parada_corta_la_espera_del_escritor(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir(escribe=True)
        parada = threading.Event()
        parada.set()
        resultado = {}
        esperando = threading.Thread(
            target=self._tomar_y_anotar, args=(candado, parada, True, resultado))
        esperando.start()
        esperando.join(1)
        self.assertEqual(resultado.get("error"), candado_obs.EsperaCancelada)
        candado.liberar(escribe=True)

    def test_la_parada_corta_la_espera_del_lector(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir(escribe=True)
        parada = threading.Event()
        parada.set()
        resultado = {}
        esperando = threading.Thread(
            target=self._tomar_y_anotar, args=(candado, parada, False,
                                               resultado))
        esperando.start()
        esperando.join(1)
        self.assertEqual(resultado.get("error"), candado_obs.EsperaCancelada)
        candado.liberar(escribe=True)

    def _tomar_y_anotar(self, candado, parada, escribe, resultado):
        try:
            candado.adquirir(parada, escribe)
        except candado_obs.EsperaCancelada:
            resultado["error"] = candado_obs.EsperaCancelada


class PreferenciaEscritorTest(unittest.TestCase):
    def test_un_lector_en_bucle_no_impide_al_escritor(self):
        candado = candado_obs.CandadoDelProceso()
        detener = threading.Event()
        entradas = []
        entro = []

        def leer_sin_pausa():
            while not detener.is_set():
                candado.adquirir()
                entradas.append(True)
                candado.liberar()

        def escribir():
            candado.adquirir(escribe=True)
            entro.append(True)
            candado.liberar(escribe=True)

        # Un lector adentro mantiene al escritor esperando mientras el otro
        # lector da vueltas.
        candado.adquirir()
        hilo_escritor = threading.Thread(target=escribir)
        hilo_escritor.start()
        self.assertTrue(esperar_a(
            lambda: candado._escritores_esperando == 1))
        hilo_lector = threading.Thread(target=leer_sin_pausa)
        hilo_lector.start()
        try:
            time.sleep(0.1)
            self.assertEqual(entradas, [])
        finally:
            candado.liberar()
            detener.set()
            hilo_lector.join(2)
        hilo_escritor.join(1.0)
        self.assertEqual(entro, [True])

    def test_dos_lectores_estan_adentro_a_la_vez(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir()
        dentro = threading.Event()
        salir = threading.Event()

        def leer():
            candado.adquirir()
            dentro.set()
            salir.wait(1)
            candado.liberar()

        hilo = threading.Thread(target=leer)
        hilo.start()
        try:
            self.assertTrue(dentro.wait(0.5))
        finally:
            salir.set()
            hilo.join(1)
            candado.liberar()

    def test_un_lector_nuevo_espera_si_hay_un_escritor_esperando(self):
        candado = candado_obs.CandadoDelProceso()
        candado.adquirir()
        tomo_escritor = []

        def escribir():
            candado.adquirir(escribe=True)
            tomo_escritor.append(True)
            candado.liberar(escribe=True)

        hilo_escritor = threading.Thread(target=escribir)
        hilo_escritor.start()
        time.sleep(0.15)
        entro_lector = []

        def leer():
            candado.adquirir()
            entro_lector.append(True)
            candado.liberar()

        hilo_lector = threading.Thread(target=leer)
        hilo_lector.start()
        hilo_lector.join(0.15)
        self.assertEqual(entro_lector, [])
        candado.liberar()
        hilo_escritor.join(1)
        hilo_lector.join(1)
        self.assertEqual(tomo_escritor, [True])
        self.assertEqual(entro_lector, [True])
