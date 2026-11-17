# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El registro de proveedores de traducción y el proveedor Google."""

import os
import unittest

import httpx

from guyrapu.core import idioma
from guyrapu.translation.proveedores import PROVEEDORES, google, obtener
from guyrapu.translation.proveedores.base import ErrorTraduccion, Traduccion

CON_RED = os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1"

# Medido el 17/11/2026 con client=dict-chrome-ex y tl=es.
LOTE_MEDIDO = [["buen día", "en"], ["buen día", "pt"], ["ggg", "en"],
               ["hola amigo", "es"]]
# Medido el 17/11/2026 con client=gtx, dt=t y tl=es.
SUELTA_MEDIDA = {
    "good morning": [[["buen día", "good morning", None, None, 10]], None,
                     "en", None, None, None, 1, [],
                     [["en"], None, [1], ["en"]]],
    "bom dia": [[["buen día", "bom dia", None, None, 10]], None, "pt", None,
                None, None, 1, [], [["pt"], None, [1], ["pt"]]],
}


def _cliente(manejar):
    return httpx.Client(transport=httpx.MockTransport(manejar))


class TestRegistro(unittest.TestCase):

    def test_google_es_el_proveedor_que_no_pide_clave(self):
        proveedor = obtener("google")
        self.assertIs(proveedor, google.PROVEEDOR_GOOGLE)
        self.assertFalse(proveedor.pide_clave)
        self.assertIn(proveedor, PROVEEDORES)

    def test_obtener_no_inventa_un_proveedor(self):
        self.assertIsNone(obtener("inventado"))

    def test_todo_proveedor_declara_si_pide_clave_y_cual(self):
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                self.assertTrue(proveedor.id)
                self.assertNotEqual(proveedor.id, proveedor.id.upper())
                self.assertTrue(proveedor.nombre.strip())
                self.assertTrue(proveedor.pide_clave is False or (
                    isinstance(proveedor.pide_clave, str)
                    and proveedor.pide_clave.strip()))

    def test_el_nombre_del_proveedor_se_traduce(self):
        idioma.instalar(idioma.IDIOMA_PSEUDO)
        self.addCleanup(idioma._reiniciar)
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                self.assertTrue(
                    idioma._(proveedor.nombre).startswith("[¡"))


class TestGoogleSinRed(unittest.TestCase):

    def test_traduce_el_lote_con_la_respuesta_medida(self):
        vistos = []

        def manejar(pedido):
            vistos.append(pedido)
            return httpx.Response(200, json=LOTE_MEDIDO)

        resultado = google.traducir(
            ["good morning", "bom dia", "gg", "hola amigo"], "es", 5,
            _cliente(manejar))

        self.assertEqual(resultado, [
            Traduccion("buen día", "en"),
            Traduccion("buen día", "pt"),
            Traduccion("ggg", "en"),
            Traduccion("hola amigo", "es"),
        ])
        self.assertEqual(len(vistos), 1)
        pedido = vistos[0]
        self.assertEqual(pedido.url.path, "/translate_a/t")
        self.assertEqual(pedido.url.params["client"], "dict-chrome-ex")
        self.assertEqual(pedido.url.params["sl"], "auto")
        self.assertEqual(pedido.url.params["tl"], "es")
        self.assertEqual(pedido.url.params.get_list("q"),
                         ["good morning", "bom dia", "gg", "hola amigo"])

    def test_usa_el_plazo_recibido(self):
        plazos = []

        def manejar(pedido):
            plazos.append(pedido.extensions["timeout"]["read"])
            return httpx.Response(200, json=[["buen día", "en"]])

        google.traducir(["good morning"], "es", 1.5, _cliente(manejar))
        self.assertEqual(plazos, [1.5])

    def test_si_el_lote_falla_traduce_de_a_uno(self):
        vistos = []
        textos = ["good morning", "bom dia"]

        def manejar(pedido):
            vistos.append(pedido)
            if pedido.url.path == "/translate_a/t":
                return httpx.Response(503)
            return httpx.Response(200,
                                  json=SUELTA_MEDIDA[pedido.url.params["q"]])

        resultado = google.traducir(textos, "es", 5, _cliente(manejar))

        self.assertEqual(resultado, [
            Traduccion("buen día", "en"),
            Traduccion("buen día", "pt"),
        ])
        sueltas = [pedido for pedido in vistos
                   if pedido.url.path == "/translate_a/single"]
        self.assertEqual([pedido.url.params["q"] for pedido in sueltas],
                         textos)
        for pedido in sueltas:
            self.assertEqual(pedido.url.params["client"], "gtx")
            self.assertEqual(pedido.url.params["dt"], "t")
            self.assertEqual(pedido.url.params["tl"], "es")

    def test_las_formas_raras_del_lote_pasan_al_respaldo(self):
        for raro in ([7], [["buen día", "en"]],
                     [["buen día", "en", "extra", "más"]]):
            with self.subTest(raro=raro):
                def manejar(pedido, _raro=raro):
                    if pedido.url.path == "/translate_a/t":
                        return httpx.Response(200, json=_raro)
                    return httpx.Response(
                        200, json=SUELTA_MEDIDA[pedido.url.params["q"]])

                resultado = google.traducir(
                    ["good morning", "bom dia"], "es", 5, _cliente(manejar))
                self.assertEqual(resultado, [
                    Traduccion("buen día", "en"),
                    Traduccion("buen día", "pt"),
                ])

    def test_las_formas_raras_de_la_respuesta_suelta_lanzan_el_error(self):
        for raro in ({"0": []}, [[["buen día"]]], []):
            with self.subTest(raro=raro):
                def manejar(pedido, _raro=raro):
                    if pedido.url.path == "/translate_a/t":
                        return httpx.Response(500)
                    return httpx.Response(200, json=_raro)

                with self.assertRaises(ErrorTraduccion):
                    google.traducir(["good morning"], "es", 5,
                                    _cliente(manejar))

    def test_si_las_dos_fallan_lanza_el_error_del_paquete(self):
        def manejar(_pedido):
            raise httpx.ConnectError("sin red")

        with self.assertRaises(ErrorTraduccion) as caso:
            google.traducir(["good morning"], "es", 5, _cliente(manejar))
        self.assertEqual(
            str(caso.exception),
            "No se pudo traducir. Se lee el mensaje original.")


@unittest.skipUnless(CON_RED, "prueba real desactivada: "
                              "GUYRAPU_PRUEBAS_CON_RED=1")
class TestGoogleReal(unittest.TestCase):

    def test_traduce_dos_saludos_a_espanol_con_su_origen(self):
        resultado = google.traducir(["good morning", "bom dia"], "es", 15)
        self.assertEqual([traduccion.origen for traduccion in resultado],
                         ["en", "pt"])
        for traduccion in resultado:
            self.assertIn("buen", traduccion.texto.lower())


if __name__ == "__main__":
    unittest.main()
