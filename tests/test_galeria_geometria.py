# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de la geometría que escribe la galería de ventanas.

No abren ventanas: los colores, las fuentes y los controles son dobles con
la forma mínima que expone la biblioteca gráfica. La galería usa estas
mismas funciones para armar el JSON de cada captura.
"""

import importlib.util
import unittest
from pathlib import Path

_QA = Path(__file__).resolve().parent.parent / "qa"
_paquete = importlib.util.spec_from_file_location(
    "galeria_geometria_prueba", _QA / "galeria_geometria.py")
geometria = importlib.util.module_from_spec(_paquete)
_paquete.loader.exec_module(geometria)


class Color:
    def __init__(self, rojo, verde, azul):
        self.rojo, self.verde, self.azul = rojo, verde, azul

    def GetRed(self):
        return self.rojo

    def GetGreen(self):
        return self.verde

    def GetBlue(self):
        return self.azul


class Fuente:
    def GetFaceName(self):
        return "Segoe UI"

    def GetPointSize(self):
        return 9

    def GetPixelSize(self):
        return type("Tamano", (), {"GetWidth": lambda self: 12})()

    def GetWeight(self):
        return 400


class FuenteSinPixeles(Fuente):
    def GetPixelSize(self):
        return type("Tamano", (), {"GetWidth": lambda self: 0})()


class TestGeometriaCapturas(unittest.TestCase):

    def test_color_hex_con_ceros_y_mayusculas(self):
        self.assertEqual(geometria.color_hex(Color(11, 6, 99)), "#0B0663")
        self.assertEqual(geometria.color_hex(Color(243, 246, 246)), "#F3F6F6")

    def test_etiqueta_sin_letra_de_acceso(self):
        self.assertEqual(geometria.sin_ampersand("&Aceptar"), "Aceptar")
        self.assertEqual(geometria.sin_ampersand("G&uardar"), "Guardar")
        self.assertEqual(geometria.sin_ampersand(None), "")

    def test_fuente_con_cara_puntos_px_y_peso(self):
        self.assertEqual(geometria.fuente_diccionario(Fuente()), {
            "cara": "Segoe UI", "puntos": 9, "px": 12, "peso": 400})

    def test_px_de_fuente_sin_medir_sale_de_los_puntos_y_el_monitor(self):
        self.assertEqual(
            geometria.fuente_diccionario(FuenteSinPixeles(), (96, 96))["px"],
            12)

    def test_rect_relativo_al_origen_del_cliente(self):
        self.assertEqual(geometria.rect_relativo((300, 220, 80, 25),
                                                 (100, 200)),
                         [200, 20, 80, 25])

    def test_medida_texto_sin_etiqueta_es_cero(self):
        self.assertEqual(geometria.medida_texto(None), [0, 0])
        self.assertEqual(geometria.medida_texto((41, 17)), [41, 17])

    def test_control_incluye_todos_los_campos_del_contrato(self):
        control = geometria.control_diccionario(
            id=7, padre=2, clase="wxButton", nombre="Aceptar",
            etiqueta="&Aceptar", rect=[10, 20, 80, 25], visible=True,
            habilitado=False, enfocable=True, fg="#1C2629", bg="#F3F6F6",
            fuente={"cara": "Segoe UI", "puntos": 9, "px": 12, "peso": 400},
            texto_px=[41, 17])
        self.assertEqual(control, {
            "id": 7, "padre": 2, "clase": "wxButton", "nombre": "Aceptar",
            "etiqueta": "Aceptar", "rect": [10, 20, 80, 25],
            "visible": True, "habilitado": False, "enfocable": True,
            "fg": "#1C2629", "bg": "#F3F6F6",
            "fuente": {"cara": "Segoe UI", "puntos": 9, "px": 12,
                       "peso": 400},
            "texto_px": [41, 17]})

    def test_control_sin_padre_guarda_null(self):
        control = geometria.control_diccionario(
            id=0, padre=None, clase="wxPanel", nombre="", etiqueta="",
            rect=[0, 0, 1, 1], visible=True, habilitado=True,
            enfocable=False, fg="#000000", bg="#FFFFFF", fuente={},
            texto_px=[0, 0])
        self.assertIsNone(control["padre"])

    def test_captura_incluye_la_pagina_y_la_lista_de_controles(self):
        datos = geometria.captura_diccionario(
            muestra="preferencias", clase="PreferenciasDialog",
            variante="con_datos", pagina="Voces", png="07_preferencias.png",
            tamano=[800, 600], cliente=[784, 562], tamano_minimo=[400, 300],
            pantalla=[1920, 1080], controles=[{"id": 1}])
        self.assertEqual(datos["muestra"], "preferencias")
        self.assertEqual(datos["pagina"], "Voces")
        self.assertEqual(datos["controles"], [{"id": 1}])
        self.assertEqual(datos["tamano"], [800, 600])
        self.assertEqual(datos["cliente"], [784, 562])

    def test_captura_sin_pagina_guarda_null(self):
        datos = geometria.captura_diccionario(
            muestra="musica", clase="VentanaMusica", variante="con_datos",
            pagina=None, png="01_musica.png", tamano=[1, 1], cliente=[1, 1],
            tamano_minimo=None, pantalla=[1920, 1080], controles=[])
        self.assertIsNone(datos["pagina"])
        self.assertIsNone(datos["tamano_minimo"])

    def test_indice_trae_una_linea_por_captura(self):
        linea = geometria.linea_indice(
            7, "preferencias", "PreferenciasDialog", "con_datos", "Voces",
            "07_preferencias_voces.png", 800, 600)
        self.assertTrue(linea.startswith("- 07 ·"))
        for pedazo in ("07_preferencias_voces.png", "preferencias",
                       "PreferenciasDialog", "Voces", "800x600"):
            self.assertIn(pedazo, linea)


if __name__ == "__main__":
    unittest.main()
