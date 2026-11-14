# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se presenta el catálogo de voces al usuario, sin interfaz ni red."""

import unittest
from unittest import mock

from guyrapu.core import voces_disponibles


MEGA = 1024 * 1024


def _voz(nombre, idioma, genero=None):
    return {"nombre": nombre, "idioma": idioma, "genero": genero}


def _paquete(identificador, proveedor, nombre, idioma, voces, megas,
             licencia="CC BY 4.0", licencia_url="https://ejemplo.test/lic"):
    return {
        "id": identificador,
        "tipo": "voz",
        "proveedor": proveedor,
        "nombre": nombre,
        "idioma": idioma,
        "version": 1,
        "licencia": licencia,
        "licencia_url": licencia_url,
        "voces": voces,
        "archivos": [{"bytes": megas * MEGA}],
    }


def _entrada(paquete, instalado=None):
    return voces_disponibles.reunir(
        [paquete], [] if instalado is None else [instalado])[0]


class TestFilasDePaquete(unittest.TestCase):

    def test_una_voz_lleva_su_nombre_y_el_motor(self):
        paquete = _paquete(
            "piper-davefx", "piper", "Piper Davefx", "es-ES",
            [_voz("Davefx", "es-ES")], 61)
        self.assertEqual(
            voces_disponibles.fila(_entrada(paquete)),
            "Davefx, Piper, español (España), 61 MB, disponible")

    def test_varias_voces_llevan_el_motor_y_su_cantidad(self):
        voces = ([_voz(f"Voz {n}", "es-ES") for n in range(12)]
                 + [_voz(f"Voz {n}", "es-MX") for n in range(12, 25)])
        paquete = _paquete(
            "phonon-es", "phonon", "Phonon español", "es", voces, 81)
        instalado = dict(paquete, instalado="2026-11-14T12:00:00-03:00")
        self.assertEqual(
            voces_disponibles.fila(_entrada(paquete, instalado)),
            "Phonon, español, 25 voces, 81 MB, instalado")

    def test_por_debajo_de_un_megabyte(self):
        paquete = _paquete(
            "piper-chico", "piper", "Piper Chico", "es-ES",
            [_voz("Chico", "es-ES")], 0)
        paquete["archivos"] = [{"bytes": 100}]
        self.assertIn("menos de 1 MB", voces_disponibles.fila(_entrada(paquete)))


class TestNombreDeIdioma(unittest.TestCase):

    def test_region_conocida(self):
        self.assertEqual(voces_disponibles.nombre_idioma("es-MX"),
                         "español (México)")

    def test_region_desconocida_solo_el_idioma(self):
        self.assertEqual(voces_disponibles.nombre_idioma("es-CL"), "español")

    def test_codigo_sin_region(self):
        self.assertEqual(voces_disponibles.nombre_idioma("es"), "español")

    def test_idioma_que_no_esta_devuelve_el_codigo(self):
        self.assertEqual(voces_disponibles.nombre_idioma("de"), "de")


class TestEstados(unittest.TestCase):

    def setUp(self):
        self.paquete = _paquete(
            "piper-davefx", "piper", "Piper Davefx", "es-ES",
            [_voz("Davefx", "es-ES")], 61)

    def test_disponible_sin_instalar(self):
        self.assertEqual(voces_disponibles.estado(_entrada(self.paquete)),
                         "disponible")

    def test_instalado_al_dia(self):
        instalado = dict(self.paquete, instalado="2026-11-14T12:00:00-03:00")
        self.assertEqual(
            voces_disponibles.estado(_entrada(self.paquete, instalado)),
            "instalado")

    def test_actualizacion_disponible(self):
        instalado = dict(self.paquete, version=0,
                         instalado="2026-11-14T12:00:00-03:00")
        self.assertEqual(
            voces_disponibles.estado(_entrada(self.paquete, instalado)),
            "actualización disponible")

    def test_instalado_fuera_del_catalogo(self):
        ficha = dict(self.paquete, instalado="2026-11-14T12:00:00-03:00")
        entrada = voces_disponibles.reunir([], [ficha])[0]
        self.assertEqual(voces_disponibles.estado(entrada), "instalado")
        self.assertEqual(voces_disponibles.fila(entrada),
                         "Davefx, Piper, español (España), 61 MB, instalado")


class TestOrden(unittest.TestCase):

    def _entradas(self):
        return voces_disponibles.reunir(
            [
                _paquete("piper-es", "piper", "Piper Davefx", "es-ES",
                         [_voz("Davefx", "es-ES")], 10),
                _paquete("phonon-pt", "phonon", "Phonon portugués", "pt",
                         [_voz("Ana", "pt-BR")], 10),
                _paquete("phonon-es", "phonon", "Phonon español", "es",
                         [_voz("Noa", "es-ES")], 10),
                _paquete("phonon-en", "phonon", "Phonon inglés", "en",
                         [_voz("Ana", "en-US")], 10),
            ], [])

    def _ids(self, entradas):
        return [voces_disponibles.identificador(entrada)
                for entrada in entradas]

    def test_primero_el_idioma_de_la_interfaz(self):
        with mock.patch.object(voces_disponibles, "idioma_actual",
                               return_value="es"):
            self.assertEqual(
                self._ids(voces_disponibles.ordenar(self._entradas())),
                ["phonon-es", "piper-es", "phonon-en", "phonon-pt"])

    def test_en_ingles_primero_el_ingles(self):
        with mock.patch.object(voces_disponibles, "idioma_actual",
                               return_value="en"):
            self.assertEqual(
                self._ids(voces_disponibles.ordenar(self._entradas())),
                ["phonon-en", "phonon-es", "piper-es", "phonon-pt"])


class TestFiltros(unittest.TestCase):

    def _entradas(self):
        return voces_disponibles.reunir(
            [
                _paquete("phonon-es", "phonon", "Phonon español", "es",
                         [_voz("Noa", "es-ES")], 10),
                _paquete("piper-es", "piper", "Piper Davefx", "es-ES",
                         [_voz("Davefx", "es-ES")], 10),
                _paquete("phonon-en", "phonon", "Phonon inglés", "en",
                         [_voz("Ana", "en-US")], 10),
            ], [])

    def _ids(self, entradas):
        return [voces_disponibles.identificador(entrada)
                for entrada in entradas]

    def test_por_idioma(self):
        self.assertEqual(
            self._ids(voces_disponibles.filtrar(
                self._entradas(), idioma="en")),
            ["phonon-en"])

    def test_por_motor(self):
        self.assertEqual(
            self._ids(voces_disponibles.filtrar(
                self._entradas(), motor="piper")),
            ["piper-es"])

    def test_por_los_dos(self):
        self.assertEqual(
            self._ids(voces_disponibles.filtrar(
                self._entradas(), idioma="es", motor="phonon")),
            ["phonon-es"])

    def test_las_opciones_solo_tienen_lo_que_hay(self):
        entradas = self._entradas()
        self.assertEqual(
            voces_disponibles.opciones_idioma(entradas),
            [("Todos los idiomas", ""), ("Español", "es"),
             ("Inglés", "en")])
        self.assertEqual(
            voces_disponibles.opciones_motor(entradas),
            [("Todos los motores", ""), ("Phonon", "phonon"),
             ("Piper", "piper")])

    def test_el_idioma_inicial_es_el_de_la_interfaz_si_hay(self):
        with mock.patch.object(voces_disponibles, "idioma_actual",
                               return_value="en"):
            self.assertEqual(
                voces_disponibles.idioma_inicial(self._entradas()), "en")

    def test_sin_paquetes_del_idioma_empieza_en_todos(self):
        solo_es = [entrada for entrada in self._entradas()
                   if voces_disponibles.identificador(entrada) != "phonon-en"]
        with mock.patch.object(voces_disponibles, "idioma_actual",
                               return_value="en"):
            self.assertEqual(
                voces_disponibles.idioma_inicial(solo_es), "")


class TestFilasYDetalles(unittest.TestCase):

    def test_fila_de_voz_con_genero(self):
        self.assertEqual(
            voces_disponibles.fila_voz(_voz("Noa", "es-ES", "female")),
            "Noa, femenina, español (España)")
        self.assertEqual(
            voces_disponibles.fila_voz(_voz("Marc", "en-US", "male")),
            "Marc, masculina, inglés (Estados Unidos)")

    def test_fila_de_voz_sin_genero(self):
        self.assertEqual(
            voces_disponibles.fila_voz(_voz("Davefx", "es-ES")),
            "Davefx, español (España)")

    def test_los_detalles_traen_licencia_enlace_y_uso_comercial(self):
        paquete = _paquete(
            "phonon-es", "phonon", "Phonon español", "es",
            [_voz("Noa", "es-ES", "female"), _voz("Marc", "es-MX", "male")],
            25, licencia="CC BY-NC 4.0",
            licencia_url="https://ejemplo.test/cc-by-nc")
        detalles = voces_disponibles.detalles(_entrada(paquete))
        self.assertIn("Nombre: Phonon español", detalles)
        self.assertIn("Motor de voz: Phonon", detalles)
        self.assertIn("Idioma: Español (España), español (México)", detalles)
        self.assertIn("Voces: 2", detalles)
        self.assertIn("Tamaño: 25 MB", detalles)
        self.assertIn("Estado: disponible", detalles)
        self.assertIn("Licencia: CC BY-NC 4.0", detalles)
        self.assertIn("Esta licencia no permite el uso comercial.", detalles)
        self.assertIn("Enlace de la licencia: https://ejemplo.test/cc-by-nc",
                      detalles)

    def test_sin_nc_no_aparece_la_linea_de_uso_comercial(self):
        paquete = _paquete(
            "piper-davefx", "piper", "Piper Davefx", "es-ES",
            [_voz("Davefx", "es-ES")], 61, licencia="CC BY 4.0")
        detalles = voces_disponibles.detalles(_entrada(paquete))
        self.assertNotIn("Esta licencia no permite el uso comercial.", detalles)


if __name__ == "__main__":
    unittest.main()
