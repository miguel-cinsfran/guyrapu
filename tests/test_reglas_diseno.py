# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los detectores de armado visual escrito a mano."""

import ast
import textwrap
import unittest

from tests import reglas_arquitectura as reglas
from tests import reglas_diseno as diseno


WX = "w" + "x"


def _hallazgos(detector, codigo):
    arbol = ast.parse(textwrap.dedent(codigo))
    return detector("fragmento.py", arbol)


def _lineas(hallazgos):
    return [hallazgo.linea for hallazgo in hallazgos]


class TestBordes(unittest.TestCase):

    def test_un_borde_numero_salta(self):
        codigo = """\
            sizer.Add(control, 0, __WX__.ALL, 10)
            sizer.Insert(1, control, 0, __WX__.ALL, 8)
            sizer.Add(control, 0, __WX__.ALL, border=6)
            sizer.Add(control, 0, banderas, 4)
            """.replace("__WX__", WX)
        self.assertEqual([1, 2, 3, 4],
                         _lineas(_hallazgos(diseno.detectar_bordes, codigo)))

    def test_cero_y_pieza_no_saltan(self):
        codigo = """\
            sizer.Add(control, 0, __WX__.ALL, 0)
            sizer.Insert(1, control, 0, __WX__.ALL, 0)
            sizer.Add(control, 0, __WX__.ALL, border=botonera.HUECO)
            sizer.Add(control, 0, banderas, formulario.MARGEN)
            sizer.AddStretchSpacer(10)
            """.replace("__WX__", WX)
        self.assertEqual([],
                         _lineas(_hallazgos(diseno.detectar_bordes, codigo)))

    def test_un_nombre_local_con_numero_salta(self):
        codigo = """\
            BORDE = 10
            sizer.Add(control, 0, __WX__.ALL, BORDE)
            """.replace("__WX__", WX)
        self.assertEqual([1],
                         _lineas(_hallazgos(diseno.detectar_bordes, codigo)))


class TestTamanos(unittest.TestCase):

    def test_un_tamano_numero_salta(self):
        codigo = """\
            control.SetSize(100, 30)
            control.SetMinSize((96, 20))
            control.SetMaxSize(400, -1)
            control.SetInitialSize((120, 40))
            tamano = __WX__.Size(80, 24)
            __WX__.Button(self, size=(90, 30))
            __WX__.TextCtrl(self, size=__WX__.Size(200, -1))
            """.replace("__WX__", WX)
        self.assertEqual([1, 2, 3, 4, 5, 6, 7],
                         _lineas(_hallazgos(diseno.detectar_tamanos, codigo)))

    def test_menos_uno_y_pieza_no_saltan(self):
        codigo = """\
            control.SetSize(-1, -1)
            control.SetMinSize((-1, -1))
            control.SetMaxSize(__WX__.Size(-1, -1))
            control.SetInitialSize(formulario.TAMANO)
            __WX__.Button(self, size=botonera.TAMANO)
            tamano = __WX__.Size(formulario.ANCHO, -1)
            """.replace("__WX__", WX)
        self.assertEqual([],
                         _lineas(_hallazgos(diseno.detectar_tamanos, codigo)))

    def test_un_nombre_local_con_numero_salta(self):
        codigo = """\
            ANCHO = 280
            control.SetMinSize((ANCHO, -1))
            """
        self.assertEqual([1],
                         _lineas(_hallazgos(diseno.detectar_tamanos, codigo)))


class TestFuentes(unittest.TestCase):

    def test_un_tamano_de_letra_numero_salta(self):
        codigo = """\
            __WX__.Font(9, __WX__.FONTFAMILY_DEFAULT, __WX__.FONTSTYLE_NORMAL, __WX__.FONTWEIGHT_NORMAL)
            fuente.SetPointSize(12)
            """.replace("__WX__", WX)
        self.assertEqual([1, 2],
                         _lineas(_hallazgos(diseno.detectar_fuentes, codigo)))

    def test_una_fuente_de_pieza_no_salta(self):
        codigo = """\
            fuente = __WX__.Font(tema.PUNTOS, __WX__.FONTFAMILY_DEFAULT, __WX__.FONTSTYLE_NORMAL, __WX__.FONTWEIGHT_NORMAL)
            fuente.SetPointSize(tema.PUNTOS)
            otra = tema.fuente_de_lista(puntos)
            """.replace("__WX__", WX)
        self.assertEqual([],
                         _lineas(_hallazgos(diseno.detectar_fuentes, codigo)))


class TestColores(unittest.TestCase):

    def test_un_color_escrito_a_mano_salta(self):
        codigo = """\
            color = __WX__.Colour(255, 0, 0)
            otro = __WX__.Colour("#123456")
            control.SetForegroundColour((30, 40, 50))
            control.SetBackgroundColour("#FFFFFF")
            """.replace("__WX__", WX)
        self.assertEqual([1, 2, 3, 4],
                         _lineas(_hallazgos(diseno.detectar_colores, codigo)))

    def test_un_color_de_pieza_no_salta(self):
        codigo = """\
            color = __WX__.Colour(paleta.ROJO)
            control.SetForegroundColour(paleta.TEXTO)
            control.SetBackgroundColour(tema.fondo())
            """.replace("__WX__", WX)
        self.assertEqual([],
                         _lineas(_hallazgos(diseno.detectar_colores, codigo)))


class TestCableado(unittest.TestCase):

    def test_las_cuatro_reglas_estan_en_la_tabla(self):
        nuevas = [regla.id for regla in reglas.REGLAS
                  if regla.id in ("R22", "R23", "R24", "R25")]
        self.assertEqual(["R22", "R23", "R24", "R25"], nuevas)

    def test_las_cuatro_reglas_miran_solo_la_interfaz_y_sus_piezas(self):
        for regla in reglas.REGLAS:
            if regla.id not in ("R22", "R23", "R24", "R25"):
                continue
            with self.subTest(regla=regla.id):
                self.assertEqual(diseno.PIEZAS, regla.duenos)
                self.assertTrue(regla.ambito("guyrapu/ui/gui.py"))
                self.assertFalse(regla.ambito("guyrapu/player/reproductor.py"))

    def test_todo_pendiente_tiene_motivo_y_cantidad(self):
        vacios = [f"{regla.id}: {archivo}"
                  for regla in reglas.REGLAS
                  for archivo, pendiente in regla.pendientes.items()
                  if not pendiente.motivo.strip() or pendiente.cantidad < 1]
        self.assertEqual([], vacios)


if __name__ == "__main__":
    unittest.main()
