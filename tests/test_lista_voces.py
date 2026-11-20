# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué muestran las listas de motores y de voces, sin interfaz ni red."""

import contextlib
import threading
import unittest
from unittest import mock

from guyrapu.core import (diagnostico, idioma, lista_voces,
                          paquetes_instalacion, voces_disponibles)
from guyrapu.ui import voces_instalacion
from guyrapu.voice import sound_player as _snd

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

    def test_la_fila_dice_la_calidad_pero_no_la_edad(self):
        alta = dict(_voz("Ana", "female"), atributos={"calidad": "high"})
        joven = dict(_voz("Noa"), atributos={"edad": "Young Adult"})
        piper = _paquete("piper-a", "piper", [alta])
        fon = _paquete("phonon-es", "phonon", [joven])
        self.assertEqual(
            [fila.texto for fila in lista_voces.filas_voces(
                _entradas([piper]), "piper")],
            ["Ana, femenina, calidad alta, disponible"])
        self.assertEqual(
            [fila.texto for fila in lista_voces.filas_voces(
                _entradas([fon]), "phonon")],
            ["Noa, disponible"])

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


class EsperaLenta:
    """Una espera que no termina hasta que el trabajo avisa del final."""

    def __init__(self, titulo, texto, parada, fin):
        self.titulo = titulo
        self.texto = texto
        self.parada = parada
        self.fin = fin
        self.estados = []

    def ShowModal(self):
        self.fin.wait(5)
        return "fin"

    def estado(self, texto):
        self.estados.append(texto)

    def Destroy(self):
        self.destruida = True


class HiloReal:
    def __init__(self, target, nombre, **kwargs):
        self._target = target

    def start(self):
        self._hilo = threading.Thread(target=self._target)
        self._hilo.start()

    def join(self):
        self._hilo.join(5)


def _ok():
    return paquetes_instalacion.ResultadoInstalacion(True, "instalado")


class TestInstalacionPorLotes(unittest.TestCase):

    def setUp(self):
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)
        self.pila = contextlib.ExitStack()
        self.addCleanup(self.pila.close)
        self.llamadas = []
        self.finales = []
        self.fin = threading.Event()
        self.instancias = []

    def _crear_espera(self, titulo, texto, parada):
        espera = EsperaLenta(titulo, texto, parada, self.fin)
        self.instancias.append(espera)
        return espera

    def _terminar(self, texto, sonido):
        self.finales.append((texto, sonido))
        self.fin.set()

    def _preparar(self, resultados):
        def instalar(paquete, aviso=None, cancelar=None):
            self.llamadas.append(paquete["id"])
            if aviso is not None:
                aviso(10)
            return resultados[len(self.llamadas) - 1]
        self.pila.enter_context(mock.patch.object(
            paquetes_instalacion, "instalar", mock.Mock(side_effect=instalar)))
        self.pila.enter_context(mock.patch.object(
            diagnostico, "crear_hilo", HiloReal))
        self.pila.enter_context(mock.patch.object(
            voces_instalacion.wx, "CallAfter",
            lambda funcion, *args: funcion(*args)))
        self.pila.enter_context(mock.patch.object(
            _snd, "reproducir", mock.Mock()))

    def _paquetes(self):
        fichas = []
        for identificador, nombre in (("a", "Ana"), ("b", "Bruno"),
                                      ("c", "Clara")):
            ficha = _paquete(identificador, "piper", [_voz(nombre)])
            ficha["nombre"] = nombre
            fichas.append(ficha)
        return _entradas(fichas)

    def _empezar(self):
        voces_instalacion.empezar(
            self._paquetes(), "instalar", self._crear_espera,
            lambda espera: None, lambda porcentaje, nombre: None,
            lambda: None, self._terminar)

    def test_el_texto_inicial_nombra_el_primer_paquete(self):
        self._preparar([_ok(), _ok(), _ok()])
        self._empezar()
        self.assertEqual(self.instancias[0].texto,
                         "Descargando Ana, 1 de 3.")

    def test_tres_paquetes_abren_una_espera_y_se_instalan_en_orden(self):
        self._preparar([_ok(), _ok(), _ok()])
        self._empezar()
        self.assertEqual(len(self.instancias), 1)
        self.assertEqual(self.llamadas, ["a", "b", "c"])
        self.assertEqual(self.instancias[0].titulo,
                         "Instalar 3 paquetes de voces")
        self.assertIn("Descargando Bruno, 2 de 3.",
                      self.instancias[0].estados)
        self.assertEqual(self.finales,
                         [("3 paquetes instalados.", "listo")])

    def test_cancelar_en_el_segundo_no_instala_el_tercero(self):
        cancelada = paquetes_instalacion.ResultadoInstalacion(
            False, "cancelada", cancelada=True)
        self._preparar([_ok(), cancelada, _ok()])
        self._empezar()
        self.assertEqual(self.llamadas, ["a", "b"])
        self.assertEqual(self.finales, [("Instalación cancelada.", None)])

    def test_un_fallo_dice_el_nombre_del_paquete(self):
        fallida = paquetes_instalacion.ResultadoInstalacion(False, "sin red")
        self._preparar([_ok(), fallida, _ok()])
        self._empezar()
        self.assertEqual(
            self.finales,
            [("2 de 3 paquetes instalados. No se pudo instalar: Bruno.",
              "error")])


class TestTextosDelLote(unittest.TestCase):

    def setUp(self):
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def test_actualizar_varios_dice_actualizados(self):
        self.assertEqual(
            voces_instalacion.texto_final(3, 3, [], False, "actualizar", ""),
            ("3 paquetes actualizados.", "listo"))
        self.assertEqual(
            voces_instalacion.texto_final(
                3, 2, [("Bruno", "sin red")], False, "actualizar", ""),
            ("2 de 3 paquetes actualizados. No se pudo actualizar: Bruno.",
             "error"))
        self.assertEqual(
            voces_instalacion.texto_final(3, 1, [], True, "actualizar", ""),
            ("Actualización cancelada.", None))


if __name__ == "__main__":
    unittest.main()
