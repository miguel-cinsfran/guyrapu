# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué muestran las listas de motores y de voces, sin interfaz ni red."""

import unittest

from guyrapu.core import idioma, lista_voces, voces_disponibles

MEGA = 1024 * 1024


def _voz(nombre, genero=None):
    return {"nombre": nombre, "idioma": "es-ES", "genero": genero}


def _paquete(identificador, proveedor, voces, uso=None):
    ficha = {
        "id": identificador, "tipo": "voz", "proveedor": proveedor,
        "nombre": identificador, "idioma": "es", "version": 1,
        "licencia": "CC BY 4.0", "licencia_url": "https://ejemplo.test/lic",
        "voces": voces, "archivos": [{"bytes": 10 * MEGA}],
    }
    if uso is not None:
        ficha["uso"] = uso
    return ficha


def _entradas(catalogo=(), instalados=()):
    return voces_disponibles.ordenar(
        voces_disponibles.reunir(list(catalogo), list(instalados)))


def _instalado(paquete):
    return dict(paquete, instalado="2026-11-14T12:00:00-03:00")


class TestFilasDeMotores(unittest.TestCase):

    def setUp(self):
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def test_cada_motor_dice_cuantas_voces_y_cuantas_estan_instaladas(self):
        fon = _paquete("phonon-es", "phonon",
                       [_voz("Noa"), _voz("Marc"), _voz("Lia")])
        piper_a = _paquete("piper-a", "piper", [_voz("Ana")])
        piper_b = _paquete("piper-b", "piper", [_voz("Bruno")])
        entradas = _entradas(
            [fon, piper_a, piper_b],
            [_instalado(fon), _instalado(piper_b)])
        self.assertEqual(
            lista_voces.filas_motores(entradas),
            [("Phonon, 3 voces, 3 instaladas", "phonon"),
             ("Piper, 2 voces, 1 instalada", "piper")])


class TestFilasDeVoces(unittest.TestCase):

    def setUp(self):
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def test_piper_con_dos_paquetes_y_uno_instalado(self):
        ana = _paquete("piper-a", "piper", [_voz("Ana", "female")])
        bruno = _paquete("piper-b", "piper", [_voz("Bruno", "male")])
        filas = lista_voces.filas_voces(
            _entradas([ana, bruno], [_instalado(bruno)]), "piper")
        self.assertEqual(
            [fila.texto for fila in filas],
            ["Ana, femenina, disponible", "Bruno, masculina, instalado"])

    def test_un_paquete_de_phonon_da_una_fila_por_voz(self):
        fon = _paquete("phonon-es", "phonon",
                       [_voz("Noa"), _voz("Marc"), _voz("Lia")],
                       uso="no_comercial")
        filas = lista_voces.filas_voces(
            _entradas([fon], [_instalado(fon)]), "phonon")
        self.assertEqual(
            [fila.texto for fila in filas],
            ["Noa, instalado, uso no comercial",
             "Marc, instalado, uso no comercial",
             "Lia, instalado, uso no comercial"])

    def test_la_busqueda_ignora_tildes_y_mayusculas(self):
        paquete = _paquete("piper-a", "piper", [_voz("Ángela"), _voz("Bruno")])
        entradas = _entradas([paquete])
        self.assertEqual(
            [fila.texto for fila in lista_voces.filas_voces(
                entradas, "piper", "ANGELA")],
            ["Ángela, disponible"])
        self.assertEqual(
            [fila.texto for fila in lista_voces.filas_voces(
                entradas, "piper", "bruno")],
            ["Bruno, disponible"])

    def test_cada_fila_da_su_paquete_y_su_indice(self):
        fon = _paquete("phonon-es", "phonon", [_voz("Noa"), _voz("Marc")])
        piper = _paquete("piper-a", "piper", [_voz("Ana")])
        filas = lista_voces.filas_voces(_entradas([fon, piper]), "phonon")
        self.assertEqual(
            [(voces_disponibles.identificador(fila.paquete), fila.indice)
             for fila in filas],
            [("phonon-es", 0), ("phonon-es", 1)])


if __name__ == "__main__":
    unittest.main()
