# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El servicio de traducción del chat: lotes, espera y caída.

El proveedor es falso y el hilo es el de verdad.
"""

import os
import queue
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.capture import traduccion_chat
from guyrapu.core import esperas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.translation.proveedores.base import ErrorTraduccion, Traduccion
from guyrapu.voice import lectura_traducida

CON_RED = os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1"

TEXTO_CAIDA = "La traducción no responde. Se leen los mensajes originales."
TEXTO_VUELTA = "La traducción volvió."


def _config(**cambios):
    base = {"traducir_chat": True, "traducir_que": "voz_lista",
            "traducir_destino": "es", "silenciar_lectura": False}
    base.update(cambios)
    return base


def _proveedor(manejar):
    return SimpleNamespace(traducir=manejar)


def _config_lectura():
    return {"limpiar_emojis": True, "eliminar_urls": True,
            "max_longitud_mensaje": 200,
            "traducir_idioma_original": "completo"}


def _esperar(condicion, timeout=5.0):
    fin = time.monotonic() + timeout
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return condicion()


class TestServicio(unittest.TestCase):

    def _servicio(self, proveedor, config=None):
        servicio = traduccion_chat._Servicio(proveedor)
        self.addCleanup(servicio.detener)
        servicio.configurar(config or _config())
        return servicio

    def test_apagada_no_pide_nada(self):
        llamadas = []

        def traducir(textos, destino, plazo):
            llamadas.append(textos)
            return []

        servicio = self._servicio(
            _proveedor(traducir), _config(traducir_chat=False))
        self.assertIsNone(servicio.pedir("hola mundo"))
        time.sleep(0.1)
        self.assertEqual(llamadas, [])

    def test_el_filtro_deja_pasar_solo_lo_traducible(self):
        llamadas = []
        servicio = self._servicio(
            _proveedor(lambda textos, destino, plazo: llamadas.append(textos)))
        self.assertIsNone(servicio.pedir("ggg"))
        self.assertEqual(llamadas, [])

    def test_silencio_con_solo_voz_no_pide_nada(self):
        llamadas = []
        servicio = self._servicio(
            _proveedor(lambda textos, destino, plazo: llamadas.append(textos)),
            _config(traducir_que="solo_voz", silenciar_lectura=True))
        self.assertIsNone(servicio.pedir("hola mundo"))
        time.sleep(0.1)
        self.assertEqual(llamadas, [])

    def test_dos_pedidos_del_mismo_texto_comparten_el_pedido(self):
        listo = threading.Event()
        llamadas = []

        def traducir(textos, destino, plazo):
            llamadas.append(list(textos))
            listo.wait(5)
            return [Traduccion("HELLO", "en") for _texto in textos]

        servicio = self._servicio(_proveedor(traducir))
        primero = servicio.pedir("Hola mundo")
        segundo = servicio.pedir("hola mundo ")
        self.assertIs(primero, segundo)
        listo.set()
        self.assertEqual(primero.esperar(5), Traduccion("HELLO", "en"))
        self.assertEqual(llamadas, [["Hola mundo"]])

    def test_un_lote_junta_lo_que_llega_junto(self):
        llamadas = []

        def traducir(textos, destino, plazo):
            llamadas.append(list(textos))
            return [Traduccion(texto.upper(), "en") for texto in textos]

        servicio = self._servicio(_proveedor(traducir))
        primero = servicio.pedir("uno dos")
        segundo = servicio.pedir("tres cuatro")
        self.assertEqual(primero.esperar(5), Traduccion("UNO DOS", "en"))
        self.assertEqual(segundo.esperar(5), Traduccion("TRES CUATRO", "en"))
        self.assertEqual(llamadas, [["uno dos", "tres cuatro"]])

    def test_al_terminar_corre_en_el_hilo_del_traductor(self):
        listo = threading.Event()
        hilos = []

        def traducir(textos, destino, plazo):
            listo.wait(5)
            return [Traduccion("HELLO", "en") for _texto in textos]

        servicio = self._servicio(_proveedor(traducir))
        pedido = servicio.pedir("hola mundo")
        pedido.al_terminar(
            lambda: hilos.append(threading.current_thread().name))
        listo.set()
        pedido.esperar(5)
        self.assertTrue(_esperar(lambda: hilos))
        self.assertEqual(hilos, ["TraductorChat"])

    def test_la_memoria_responde_sin_volver_a_pedir(self):
        llamadas = []

        def traducir(textos, destino, plazo):
            llamadas.append(list(textos))
            return [Traduccion("HELLO", "en") for _texto in textos]

        servicio = self._servicio(_proveedor(traducir))
        primero = servicio.pedir("hola mundo")
        self.assertEqual(primero.esperar(5), Traduccion("HELLO", "en"))
        segundo = servicio.pedir("Hola mundo")
        self.assertEqual(segundo.esperar(0), Traduccion("HELLO", "en"))
        time.sleep(0.1)
        self.assertEqual(len(llamadas), 1)

    def test_una_falla_suelta_el_original_y_avisa_caida_y_vuelta_una_vez(self):
        respuestas = [ErrorTraduccion("sin red"), ErrorTraduccion("sin red"),
                      [Traduccion("HELLO", "en")]]
        llamadas = []
        avisos = []

        def traducir(textos, destino, plazo):
            llamadas.append(list(textos))
            respuesta = respuestas.pop(0)
            if isinstance(respuesta, Exception):
                raise respuesta
            return respuesta

        with mock.patch.object(traduccion_chat, "CADENCIA",
                               esperas.Creciente(0.01, 0.02)):
            servicio = self._servicio(_proveedor(traducir))
            fallo = mock.Mock(wraps=servicio._cola.fallo)
            servicio._cola.fallo = fallo
            servicio._al_avisar = lambda frase, sonido: avisos.append(frase)

            primero = servicio.pedir("hola mundo")
            self.assertIsNone(primero.esperar(2))
            self.assertTrue(_esperar(lambda: fallo.called))
            self.assertTrue(_esperar(lambda: TEXTO_CAIDA in avisos))

            segundo = servicio.pedir("otro mensaje")
            self.assertIsNone(segundo.esperar(2))
            self.assertTrue(_esperar(lambda: len(llamadas) >= 2))

            tercero = servicio.pedir("buen dia")
            self.assertIsNone(tercero.esperar(2))
            self.assertTrue(_esperar(
                lambda: tercero.resultado == Traduccion("HELLO", "en")))
            self.assertTrue(_esperar(lambda: not servicio._vigilancia.caido))
            self.assertTrue(_esperar(lambda: TEXTO_VUELTA in avisos))

        self.assertEqual(avisos.count(TEXTO_CAIDA), 1)
        self.assertEqual(avisos.count(TEXTO_VUELTA), 1)


class TestFallaSinEspera(unittest.TestCase):

    def _servicio(self, proveedor):
        servicio = traduccion_chat._Servicio(proveedor)
        self.addCleanup(servicio.detener)
        servicio.configurar(_config())
        return servicio

    def test_en_falla_la_voz_lee_el_original_sin_esperar(self):
        def traducir(textos, destino, plazo):
            raise ErrorTraduccion("sin red")

        with mock.patch.object(traduccion_chat, "CADENCIA",
                               esperas.Creciente(0.01, 0.02)):
            servicio = self._servicio(_proveedor(traducir))
            primero = servicio.pedir("hola mundo")
            self.assertIsNone(primero.esperar(2))
            self.assertTrue(servicio._vigilancia.caido)
            item = {"texto_tts": "Ana: otro mensaje",
                    "ml": "otro mensaje",
                    "pedido": servicio.pedir("otro mensaje")}
            inicio = time.monotonic()
            texto = lectura_traducida.texto(item, _config_lectura())
            self.assertLess(time.monotonic() - inicio, 0.2)
            self.assertEqual(texto, "Ana: otro mensaje")

    def test_despues_de_un_lote_bueno_la_voz_vuelve_a_esperar(self):
        listo = threading.Event()
        llamadas = []

        def traducir(textos, destino, plazo):
            llamadas.append(list(textos))
            if len(llamadas) == 1:
                raise ErrorTraduccion("sin red")
            if len(llamadas) == 2:
                return [Traduccion("HOLA", "en") for _texto in textos]
            listo.wait(5)
            return [Traduccion("HOLA", "en") for _texto in textos]

        with mock.patch.object(traduccion_chat, "CADENCIA",
                               esperas.Creciente(0.01, 0.02)):
            servicio = self._servicio(_proveedor(traducir))
            primero = servicio.pedir("hola mundo")
            self.assertIsNone(primero.esperar(2))
            segundo = servicio.pedir("otro mensaje")
            self.assertTrue(_esperar(
                lambda: segundo.resultado == Traduccion("HOLA", "en")))
            self.assertFalse(servicio._vigilancia.caido)
            item = {"texto_tts": "Ana: tercer mensaje",
                    "ml": "tercer mensaje",
                    "pedido": servicio.pedir("tercer mensaje")}
            inicio = time.monotonic()
            texto = lectura_traducida.texto(item, _config_lectura())
            self.assertGreaterEqual(time.monotonic() - inicio, 1.8)
            self.assertEqual(texto, "Ana: tercer mensaje")
            listo.set()


class TestModoDeLaLista(unittest.TestCase):

    def _servicio(self, config):
        servicio = traduccion_chat._Servicio(_proveedor(lambda *args: []))
        self.addCleanup(servicio.detener)
        servicio.configurar(config)
        return servicio

    def test_voz_y_lista_traduce_la_lista(self):
        self.assertTrue(self._servicio(_config()).traduce_lista())

    def test_solo_voz_no_traduce_la_lista(self):
        self.assertFalse(
            self._servicio(_config(traducir_que="solo_voz")).traduce_lista())

    def test_apagada_no_traduce_la_lista(self):
        self.assertFalse(
            self._servicio(_config(traducir_chat=False)).traduce_lista())


@unittest.skipUnless(CON_RED, "prueba real desactivada: "
                              "GUYRAPU_PRUEBAS_CON_RED=1")
class TestConRed(unittest.TestCase):

    def tearDown(self):
        traduccion_chat.detener()

    def test_good_morning_llega_traducido_a_la_voz(self):
        from main import Stats, procesar_entrante

        config = {
            "usuarios_silenciados": [], "palabras_silenciadas": [],
            "silenciados_ocultar": set(), "silenciados_runtime": set(),
            "silenciar_lectura": False, "limpiar_emojis": True,
            "eliminar_urls": True, "max_longitud_mensaje": 200,
            "umbral_solo_nombre": 0, "formato_prefijo": "nombre_mensaje",
            "estrategia": "todas", "tamanio_maximo": 10,
            "traducir_chat": True, "traducir_que": "voz_lista",
            "traducir_destino": "es", "idioma": "es",
        }
        traduccion_chat.configurar(config, al_avisar=lambda *args: None)
        cola = queue.Queue()
        procesar_entrante("Ana", "good morning", TIPO_TEXTO, "", "canal",
                          cola, config, Stats())
        item = cola.get_nowait()
        texto = lectura_traducida.texto(item, config)
        self.assertIn("buen", texto.lower())
        self.assertNotIn("good morning", texto.lower())
        self.assertTrue(texto.endswith(", del inglés"), texto)


if __name__ == "__main__":
    unittest.main()
