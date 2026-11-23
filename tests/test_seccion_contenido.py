# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La sección Contenido de los cuadros de lo que sale.

Abre ventanas.
"""

import unittest

import wx

from guyrapu.ui import seccion_contenido
from tests.ventanas_prueba import app_de_prueba, destruir

CINCO = ("texto", "mostrar_en", "medio", "segundos", "estilo")
ROTULOS = ("&Texto:", "&Mostrar en:", "Me&dio:",
           "&Segundos en pantalla:", "&Estilo:")


class BaseSeccion(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.panel = wx.Panel(self.marco)
        self.columna = wx.BoxSizer(wx.VERTICAL)

    def _seccion(self, campos, **opciones):
        return seccion_contenido.SeccionContenido(
            self.panel, self.columna, campos, **opciones)


class TestSeccionContenido(BaseSeccion):

    def test_los_cinco_campos_van_en_el_orden_de_p1(self):
        seccion = self._seccion(CINCO)
        self.assertEqual(tuple(seccion.rotulos()), ROTULOS)
        cajas = [hijo.GetLabel() for hijo in self.panel.GetChildren()
                 if isinstance(hijo, wx.StaticBox)]
        self.assertEqual(cajas, ["Contenido"])

    def test_cada_subconjunto_respeta_el_orden_de_p1(self):
        for elegidos in (("texto", "medio", "segundos", "estilo"),
                         ("texto", "mostrar_en", "segundos", "estilo"),
                         ("texto",), ("medio",), ("estilo",)):
            with self.subTest(campos=elegidos):
                esperados = tuple(rotulo for campo, rotulo in zip(CINCO, ROTULOS)
                                  if campo in elegidos)
                self.assertEqual(tuple(self._seccion(elegidos).rotulos()),
                                 esperados)

    def test_la_nota_va_despues_del_texto(self):
        seccion = self._seccion(("texto", "medio"), nota="{usuario}")
        self.assertEqual(tuple(seccion.rotulos()),
                         ("&Texto:", "{usuario}", "Me&dio:"))

    def test_devuelve_los_valores_que_se_le_ponen(self):
        seccion = self._seccion(
            CINCO, destinos=["Vídeo", "Chat"], medios=["fuegos"],
            estilos=["Predeterminado", "Banda"])
        seccion.poner({"texto": "Hola", "mostrar_en": 1, "medio": "fuegos",
                       "segundos": 15, "estilo": 1})
        self.assertEqual(seccion.valores(), {
            "texto": "Hola", "mostrar_en": 1, "medio": "fuegos",
            "segundos": 15, "estilo": 1})

    def test_cada_control_tiene_el_nombre_de_su_rotulo(self):
        seccion = self._seccion(CINCO)
        self.assertEqual(
            (seccion.txt_texto.GetName(), seccion.cho_destino.GetName(),
             seccion.cho_medio.GetName(), seccion.sp_segundos.GetName(),
             seccion.cho_estilo.GetName()),
            ("Texto", "Mostrar en", "Medio", "Segundos en pantalla", "Estilo"))


if __name__ == "__main__":
    unittest.main()
