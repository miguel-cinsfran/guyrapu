# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del paso de disparadores viejos a comandos."""

import json
import tempfile
import unittest
from unittest import mock

from guyrapu.core import idioma
from guyrapu.interaction import conversion_disparadores
from tests.rutas_temporales import redirigir_rutas


def _viejo(nombre, cuando, **cambios):
    datos = {
        "nombre": nombre, "cuando": cuando, "comandos": [], "palabras": [],
        "evento": "", "minimo": None, "regalo": "", "atajo": 0,
        "medio": "", "tarjeta": "Gracias", "estilo": "clasico",
        "segundos": 9, "permiso": "todos", "nombres": ["Ana"],
        "espera_general": 7.0, "espera_persona": 20.0, "activo": True,
    }
    datos.update(cambios)
    return datos


def _comando(nombre="otro", **cambios):
    datos = {
        "nombre": nombre, "alias": [], "respuesta": "Respuesta", "medio": "",
        "destino": "video", "permiso": "todos", "nombres": [],
        "espera_general": 5.0, "espera_persona": 30.0, "activo": True,
        "estilo": "clasico", "segundos": 8, "lista": False, "en_lista": True,
    }
    datos.update(cambios)
    return datos


class TestConversion(unittest.TestCase):

    def test_un_comando_viejo_pasa_con_nombre_alias_respuesta_y_medio(self):
        resultado = conversion_disparadores.convertir([], [_viejo(
            "risas", "comando", comandos=["!risa", "!carcajada"],
            medio="aplausos",
            tarjeta="Ja {cantidad} {regalo} {usuario}")])
        self.assertEqual(len(resultado.comandos), 1)
        comando = resultado.comandos[0]
        self.assertEqual(comando["nombre"], "risa")
        self.assertEqual(comando["alias"], ["carcajada"])
        self.assertEqual(comando["respuesta"], "Ja {usuario}")
        self.assertEqual(comando["medio"], "aplausos")
        self.assertEqual(comando["destino"], "video")
        self.assertEqual(comando["ubicacion"], "principio")
        self.assertEqual(comando["segundos"], 9)
        self.assertEqual(comando["permiso"], "todos")
        self.assertEqual(comando["nombres"], ["Ana"])
        self.assertEqual((comando["espera_general"],
                          comando["espera_persona"]), (7.0, 20.0))
        self.assertEqual(resultado.disparadores, [])

    def test_un_disparador_de_palabra_pasa_en_cualquier_parte(self):
        resultado = conversion_disparadores.convertir([], [_viejo(
            "saludos", "palabra", palabras=["hola", "🔥"],
            tarjeta="Dijo {texto}")])
        self.assertEqual(len(resultado.comandos), 1)
        comando = resultado.comandos[0]
        self.assertEqual(comando["nombre"], "hola")
        self.assertEqual(comando["alias"], ["🔥"])
        self.assertEqual(comando["ubicacion"], "cualquiera")
        self.assertEqual(comando["respuesta"], "Dijo {texto}")

    def test_un_disparador_de_atajo_pasa_solo_con_el_atajo(self):
        resultado = conversion_disparadores.convertir([], [_viejo(
            "botonera de risa", "atajo", atajo=3)])
        comando = resultado.comandos[0]
        self.assertEqual(comando["nombre"], "botoneraderisa")
        self.assertEqual(comando["permiso"], "solo_atajo")
        self.assertEqual(comando["atajo"], 3)

    def test_un_disparador_de_evento_queda_igual(self):
        evento = _viejo("regalo", "evento", evento="superchat", minimo=5)
        resultado = conversion_disparadores.convertir([], [evento])
        self.assertEqual(resultado.comandos, [])
        self.assertEqual(resultado.disparadores, [evento])

    def test_lo_que_choca_con_un_comando_se_queda_suyo_y_toma_el_medio(self):
        existente = _comando(nombre="risa", respuesta="Mía")
        resultado = conversion_disparadores.convertir(
            [existente], [_viejo(
                "risas", "comando", comandos=["risa"], medio="aplausos",
                tarjeta="Suya")])
        self.assertEqual(len(resultado.comandos), 1)
        self.assertEqual(resultado.comandos[0]["respuesta"], "Mía")
        self.assertEqual(resultado.comandos[0]["medio"], "aplausos")
        self.assertTrue(resultado.descartados)

    def test_un_medio_que_ya_tenia_el_comando_no_se_cambia(self):
        existente = _comando(nombre="risa", medio="fuegos")
        resultado = conversion_disparadores.convertir(
            [existente], [_viejo(
                "risas", "comando", comandos=["risa"], medio="aplausos")])
        self.assertEqual(resultado.comandos[0]["medio"], "fuegos")


class TestEnDisco(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def _escribir(self, ruta, datos):
        ruta.write_text(json.dumps(datos, ensure_ascii=False),
                        encoding="utf-8")

    def _leer(self, ruta):
        return json.loads(ruta.read_text(encoding="utf-8"))

    def test_guarda_la_copia_y_no_vuelve_a_escribir_nada(self):
        from guyrapu.core import paths
        ruta_disparadores = paths.disparadores()
        ruta_comandos = paths.comandos()
        copia = ruta_disparadores.with_name("disparadores.anterior.json")
        viejos = [_viejo("risas", "comando", comandos=["risa"]),
                  _viejo("regalo", "evento", evento="superchat")]
        self._escribir(ruta_disparadores, viejos)
        self._escribir(ruta_comandos, [_comando()])

        conversion_disparadores.convertir_en_disco()

        self.assertEqual(self._leer(copia), viejos)
        self.assertEqual(self._leer(ruta_disparadores), [viejos[1]])
        nombres = [comando["nombre"] for comando in self._leer(ruta_comandos)]
        self.assertIn("risa", nombres)
        antes = (ruta_disparadores.read_bytes(), ruta_comandos.read_bytes(),
                 copia.read_bytes())
        conversion_disparadores.convertir_en_disco()
        self.assertEqual(antes, (ruta_disparadores.read_bytes(),
                                 ruta_comandos.read_bytes(),
                                 copia.read_bytes()))

    def test_un_archivo_de_comandos_roto_no_convierte_ni_escribe(self):
        from guyrapu.core import paths
        ruta_disparadores = paths.disparadores()
        ruta_comandos = paths.comandos()
        copia = ruta_disparadores.with_name("disparadores.anterior.json")
        viejos = [_viejo("risas", "comando", comandos=["risa"])]
        self._escribir(ruta_disparadores, viejos)
        contenido = b"{esto no es json"
        ruta_comandos.write_bytes(contenido)
        antes_disparadores = ruta_disparadores.read_bytes()

        with mock.patch.object(conversion_disparadores.logger,
                               "exception") as registrar:
            conversion_disparadores.convertir_en_disco()

        registrar.assert_called_once()
        self.assertEqual(contenido, ruta_comandos.read_bytes())
        self.assertEqual(antes_disparadores, ruta_disparadores.read_bytes())
        self.assertFalse(copia.exists())

    def test_un_archivo_de_comandos_ausente_cuenta_como_vacio(self):
        from guyrapu.core import paths
        ruta_disparadores = paths.disparadores()
        ruta_comandos = paths.comandos()
        self._escribir(ruta_disparadores, [_viejo(
            "risas", "comando", comandos=["risa"])])
        with mock.patch.object(conversion_disparadores.logger, "exception") as registrar:
            conversion_disparadores.convertir_en_disco()
        registrar.assert_not_called()
        self.assertEqual(
            [comando["nombre"] for comando in self._leer(ruta_comandos)],
            ["risa"])

    def test_sin_disparadores_viejos_no_escribe_la_copia(self):
        from guyrapu.core import paths
        ruta_disparadores = paths.disparadores()
        copia = ruta_disparadores.with_name("disparadores.anterior.json")
        actuales = [_viejo("regalo", "evento", evento="superchat")]
        self._escribir(ruta_disparadores, actuales)
        antes = ruta_disparadores.stat().st_mtime_ns

        conversion_disparadores.convertir_en_disco()

        self.assertFalse(copia.exists())
        self.assertEqual(antes, ruta_disparadores.stat().st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
