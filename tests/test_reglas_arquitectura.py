# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las reglas de arquitectura declaradas en la tabla."""

import ast
import textwrap
import unittest

from tests import reglas_arquitectura as reglas
from tests import reglas_detectores as detectores


EVENTOS = {"aviso", "comentario", "conectado", "error", "copiar"}
# El detector de pruebas remotas reconoce el módulo gráfico por su nombre:
# se arma así para que estas pruebas de lectura corran en esta PC.
WX = "w" + "x"


def _hallazgos(detector, codigo, *extra):
    arbol = ast.parse(textwrap.dedent(codigo))
    return detector("fragmento.py", arbol, *extra)


def _lineas(hallazgos):
    return [hallazgo.linea for hallazgo in hallazgos]


class TestTabla(unittest.TestCase):

    def test_las_siete_reglas_estan_en_la_tabla(self):
        self.assertEqual([regla.id for regla in reglas.REGLAS],
                         ["R1", "R2", "R3", "R4", "R5", "R6", "R7"])
        for regla in reglas.REGLAS:
            with self.subTest(regla=regla.id):
                self.assertTrue(regla.prohibido)
                self.assertTrue(callable(regla.detectar))
                self.assertTrue(callable(regla.ambito))


class TestReglasSobreElCodigo(unittest.TestCase):

    def test_ningun_archivo_ajeno_usa_lo_prohibido(self):
        for regla in reglas.REGLAS:
            hallazgos = detectores.hallazgos_por_archivo(regla)
            ajenos, _ = detectores.revisar(regla, hallazgos)
            with self.subTest(regla=regla.id):
                self.assertEqual([], ajenos,
                                 detectores.detalle_ajenos(regla, ajenos))

    def test_los_pendientes_solo_bajan(self):
        for regla in reglas.REGLAS:
            hallazgos = detectores.hallazgos_por_archivo(regla)
            _, vencidos = detectores.revisar(regla, hallazgos)
            with self.subTest(regla=regla.id):
                self.assertEqual([], vencidos,
                                 detectores.detalle_vencidos(regla, vencidos))

    def test_cada_pendiente_tiene_motivo(self):
        vacios = [f"{regla.id}: {archivo}"
                  for regla in reglas.REGLAS
                  for archivo, pendiente in regla.pendientes.items()
                  if not pendiente.motivo.strip()]
        self.assertEqual([], vacios, "Pendientes sin motivo: " + ", ".join(vacios))


class TestDetectores(unittest.TestCase):

    def test_cuadros(self):
        codigo = """\
            __WX__.MessageBox("a", "b")
            _gui.__WX__.MessageDialog(None, "a", "b")
            # __WX__.MessageBox("comentario")
            texto = "__WX__.MessageBox"
            otro.MessageBox("a", "b")
            """.replace("__WX__", WX)
        hallazgos = _hallazgos(detectores.detectar_cuadros, codigo)
        self.assertEqual([1, 2], _lineas(hallazgos))

    def test_capas(self):
        hallazgos = _hallazgos(detectores.detectar_capas, """\
            import guyrapu.ui.confirmar

            def f():
                from guyrapu.ui import paleta

            # import guyrapu.ui
            texto = "import guyrapu.ui"
            import guyrapu.util
            """)
        self.assertEqual([1, 4], _lineas(hallazgos))

    def test_red(self):
        hallazgos = _hallazgos(detectores.detectar_red, """\
            import httpx
            from urllib.request import urlopen

            def f():
                import requests

            # import requests
            from urllib import request
            from urllib.parse import urlparse
            import urllib.error
            from requests import get
            """)
        self.assertEqual([1, 2, 5, 8, 11], _lineas(hallazgos))

    def test_escape(self):
        codigo = """\
            if k == __WX__.WXK_ESCAPE:
                pass
            codigo = WXK_ESCAPE
            # WXK_ESCAPE
            texto = "WXK_ESCAPE"
            __WX__.WXK_F11
            """.replace("__WX__", WX)
        hallazgos = _hallazgos(detectores.detectar_escape, codigo)
        self.assertEqual([1, 3], _lineas(hallazgos))

    def test_avisar(self):
        hallazgos = _hallazgos(detectores.detectar_avisar, """\
            from guyrapu.ui.aviso_importante import avisar
            from guyrapu.ui import aviso_importante
            from guyrapu.ui.aviso_importante import avisar as chillar

            avisar("texto", "aviso")
            avisar("texto", sonido="comentario")
            avisar("texto")
            avisar("texto", "")
            avisar("texto", variable)
            avisar("texto", "error")
            avisar("texto", "copiar")
            avisar("texto", "inventado")
            aviso_importante.avisar("texto", "conectado")
            aviso_importante.avisar("texto")
            chillar("texto", "aviso")
            chillar("texto")
            # avisar("texto")
            texto = "avisar('x')"
            """, EVENTOS)
        self.assertEqual([7, 8, 9, 12, 14, 16],
                         _lineas(hallazgos))

    def test_controles(self):
        hallazgos = _hallazgos(detectores.detectar_controles, """\
            boton.Disable()
            boton.Enable(True)
            boton.Enable(False)
            boton.Enable(estado)
            menu.Enable(id, False)
            boton.Enable()
            # boton.Disable()
            texto = "boton.Disable()"
            boton.Enable(enable=False)
            boton.Enable(enable=True)
            boton.Enable(False, False)
            """)
        self.assertEqual([1, 3, 4, 9], _lineas(hallazgos))

    def test_esperas(self):
        hallazgos = _hallazgos(detectores.detectar_esperas, """\
            while activo:
                leer()
                dormir(1)
            while activo:
                parada.wait(1)
            while activo:
                leer_socket()
            while activo:
                def anidada():
                    time.sleep(1)
                leer()
            while activo:
                time.sleep(1)
            while activo:
                esperar(1)
            while activo:
                self._esperar_intervalo()
            """)
        self.assertEqual([1, 4, 12, 14, 16], _lineas(hallazgos))


if __name__ == "__main__":
    unittest.main()
