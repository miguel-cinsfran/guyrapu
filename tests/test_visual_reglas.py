# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las reglas medibles de las geometrías de la galería."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_RUTA = _RAIZ / "qa" / "visual_reglas.py"
for _carpeta in (str(_RAIZ), str(_RAIZ / "qa")):
    if _carpeta not in sys.path:
        sys.path.insert(0, _carpeta)
_especificacion = importlib.util.spec_from_file_location(
    "visual_reglas_qa", _RUTA)
visual = importlib.util.module_from_spec(_especificacion)
_especificacion.loader.exec_module(visual)

FUENTE = {"cara": "Segoe UI", "puntos": 9, "px": 12, "peso": 400}


def control(**cambios):
    """Control que no salta ninguna regla."""
    datos = {
        "id": 0, "padre": None, "clase": "wxStaticText", "nombre": "Etiqueta",
        "etiqueta": "Texto", "rect": [20, 20, 100, 24], "visible": True,
        "habilitado": True, "enfocable": True, "fg": "#1C2629",
        "bg": "#F3F6F6", "fuente": dict(FUENTE), "texto_px": [30, 12],
    }
    datos.update(cambios)
    return datos


def muestra(controles=None, **cambios):
    """Ventana que no salta ninguna regla salvo vacío con un solo control."""
    datos = {
        "muestra": "preferencias", "clase": "PreferenciasDialog",
        "variante": "con_datos", "pagina": "Voces",
        "png": "07_preferencias.png", "tamano": [500, 400],
        "cliente": [400, 300], "tamano_minimo": [400, 300],
        "pantalla": [1366, 768],
        "controles": [] if controles is None else controles,
    }
    datos.update(cambios)
    return datos


class Base(unittest.TestCase):

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.carpeta = Path(self._temporal.name)

    def hallazgos(self, ventana):
        return visual.analizar([ventana])[0]

    def uno(self, ventana, regla):
        return next((h for h in self.hallazgos(ventana)
                     if h["regla"] == regla), None)

    def archivo(self, ventana, nombre="01.json"):
        ruta = self.carpeta / nombre
        ruta.write_text(json.dumps(ventana), encoding="utf-8")
        return ruta

    def correr(self, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = visual.main([str(self.carpeta), *argumentos])
        return codigo, salida.getvalue()


class TestContraste(Base):

    def test_salta(self):
        encontrado = self.uno(muestra([control(fg="#7B7B7B")]), "contraste")
        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado["gravedad"], "error")
        self.assertIn("3,9:1, mínimo 4,5:1", encontrado["detalle"])

    def test_no_salta(self):
        self.assertIsNone(self.uno(muestra([control()]), "contraste"))


class TestRecorte(Base):

    def test_salta(self):
        padre = control(id=1, clase="wxPanel", etiqueta="",
                        rect=[50, 50, 100, 50])
        hijo = control(id=2, padre=1, rect=[140, 60, 60, 20])
        boton = control(id=3, clase="wxButton", etiqueta="Aceptar",
                        rect=[20, 110, 30, 24], texto_px=[80, 12])
        hallazgos = self.hallazgos(muestra([padre, hijo, boton]))
        recortes = [h for h in hallazgos if h["regla"] == "recorte"]
        self.assertEqual(len(recortes), 2)
        self.assertTrue(all(h["gravedad"] == "error" for h in recortes))

    def test_no_salta(self):
        padre = control(id=1, clase="wxPanel", etiqueta="",
                        rect=[50, 50, 100, 50])
        hijo = control(id=2, padre=1, rect=[60, 55, 60, 20])
        boton = control(id=3, clase="wxButton", etiqueta="Aceptar",
                        rect=[20, 110, 100, 24])
        self.assertIsNone(self.uno(muestra([padre, hijo, boton]), "recorte"))

    def test_una_etiqueta_que_cabe_no_lleva_relleno_de_borde(self):
        etiqueta = control(id=1, texto_px=[64, 15], rect=[20, 20, 65, 24])
        self.assertIsNone(self.uno(muestra([etiqueta]), "recorte"))


class TestSolape(Base):

    def test_salta(self):
        controles = [control(id=1), control(id=2, rect=[60, 20, 100, 24])]
        self.assertIsNotNone(self.uno(muestra(controles), "solape"))

    def test_no_salta(self):
        controles = [control(id=1), control(id=2, rect=[130, 20, 100, 24])]
        self.assertIsNone(self.uno(muestra(controles), "solape"))

    def test_un_control_invisible_no_cuenta_para_solape_ni_margen(self):
        visible = control(id=1, rect=[20, 20, 100, 24])
        oculto = control(id=2, visible=False, rect=[4, 20, 100, 24])
        ventana = muestra([visible, oculto])
        self.assertIsNone(self.uno(ventana, "solape"))
        self.assertIsNone(self.uno(ventana, "margen"))

    def test_una_caja_no_pisa_el_campo_que_encierra(self):
        caja = control(id=1, clase="wxStaticBox", nombre="Agregar disparador",
                       etiqueta="", rect=[16, 16, 300, 450])
        nombre = control(id=2, nombre="Nombre", rect=[23, 55, 290, 23])
        vecina = control(id=3, clase="wxStaticBox", nombre="OBS",
                         etiqueta="", rect=[332, 16, 316, 242])
        self.assertIsNone(self.uno(
            muestra([caja, nombre, vecina]), "solape"))

    def test_la_caja_va_primera_y_no_pisa_el_campo_que_encierra(self):
        caja = control(id=1, clase="wxStaticBox", nombre="Agregar disparador",
                       etiqueta="", rect=[16, 16, 300, 450])
        campo = control(id=2, nombre="Nombre", rect=[23, 55, 290, 23])
        self.assertIsNone(self.uno(muestra([caja, campo]), "solape"))

    def test_la_caja_va_segunda_y_no_pisa_el_campo_que_encierra(self):
        caja = control(id=1, clase="wxStaticBox", nombre="Agregar disparador",
                       etiqueta="", rect=[16, 16, 300, 450])
        campo = control(id=2, nombre="Nombre", rect=[23, 55, 290, 23])
        self.assertIsNone(self.uno(muestra([campo, caja]), "solape"))

    def test_dos_cajas_que_se_pisan_si_saltan(self):
        caja = control(id=1, clase="wxStaticBox", nombre="Agregar disparador",
                       etiqueta="", rect=[16, 16, 300, 450])
        otra = control(id=2, clase="wxStaticBox", nombre="Otra caja",
                       etiqueta="", rect=[300, 16, 316, 242])
        hallazgo = self.uno(muestra([caja, otra]), "solape")
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo["control"],
                         "Agregar disparador y Otra caja")
        interior = control(id=3, clase="wxStaticBox", nombre="Caja interior",
                           etiqueta="", rect=[23, 55, 290, 23])
        hallazgo = self.uno(muestra([caja, interior]), "solape")
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo["control"],
                         "Agregar disparador y Caja interior")

    def test_un_campo_que_cruza_la_caja_si_salta(self):
        caja = control(id=1, clase="wxStaticBox", nombre="Agregar disparador",
                       etiqueta="", rect=[16, 16, 300, 450])
        campo = control(id=2, nombre="Nombre", rect=[300, 55, 290, 23])
        hallazgo = self.uno(muestra([caja, campo]), "solape")
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo["control"], "Agregar disparador y Nombre")


class TestControlConDesplazamiento(Base):

    def _ventana(self):
        desplazable = control(
            id=1, clase="wxScrolledWindow", nombre="Desplazable",
            etiqueta="", rect=[172, 10, 640, 498])
        casilla = control(
            id=2, padre=1, clase="wxCheckBox", nombre="Casilla",
            etiqueta="", rect=[182, 621, 117, 15])
        return muestra([desplazable, casilla], cliente=[822, 560])

    def test_un_hijo_no_da_recorte_por_salir_del_area_visible(self):
        self.assertIsNone(self.uno(self._ventana(), "recorte"))

    def test_un_hijo_no_da_margen_contra_el_area_cliente(self):
        self.assertIsNone(self.uno(self._ventana(), "margen"))


class TestPiezasInternas(Base):

    def test_el_campo_de_un_selector_no_da_recorte_y_el_selector_si(self):
        panel = control(id=1, clase="wxPanel", etiqueta="",
                        rect=[0, 0, 400, 300])
        selector = control(
            id=2, padre=1, clase="wxDirPickerCtrl", nombre="Carpeta",
            etiqueta="", rect=[20, 280, 300, 25])
        campo = control(
            id=3, padre=2, clase="wxTextCtrl", nombre="Campo",
            etiqueta="", rect=[22, 305, 200, 23])
        recortes = [h for h in self.hallazgos(muestra([panel, selector, campo]))
                    if h["regla"] == "recorte"]
        self.assertEqual([h["control"] for h in recortes], ["Carpeta"])

    def test_la_lista_de_categorias_de_un_libro_no_da_recorte(self):
        libro = control(id=1, clase="wxListbook", etiqueta="",
                        rect=[10, 10, 802, 498])
        lista = control(
            id=2, padre=1, clase="wxListView", nombre="Categorías",
            etiqueta="", rect=[12, 12, 157, 498])
        ventana = muestra([libro, lista], cliente=[822, 560])
        self.assertIsNone(self.uno(ventana, "recorte"))

    def test_las_piezas_de_un_contador_no_dan_solape(self):
        panel = control(id=1, clase="wxPanel", etiqueta="",
                        rect=[0, 0, 400, 300])
        contador = control(
            id=2, padre=1, clase="wxSpinCtrlDouble", etiqueta="",
            rect=[8, 122, 212, 23])
        texto = control(
            id=3, padre=2, clase="wxTextCtrl", etiqueta="",
            rect=[10, 124, 194, 23])
        boton = control(
            id=4, padre=2, clase="wxSpinButton", etiqueta="",
            rect=[202, 122, 18, 23])
        self.assertIsNone(self.uno(
            muestra([panel, contador, texto, boton]), "solape"))

    def test_la_lista_y_el_orden_de_participacion_siguen_dando_solape(self):
        panel = control(id=1, clase="wxPanel", etiqueta="",
                        rect=[0, 0, 504, 381])
        lista = control(
            id=2, padre=1, clase="wxListBox", nombre="Participación",
            etiqueta="", rect=[10, 34, 488, 287])
        orden = control(
            id=3, padre=1, clase="wxChoice", nombre="Ordenar por",
            etiqueta="", rect=[84, 319, 77, 23])
        hallazgo = self.uno(muestra([panel, lista, orden],
                                    tamano=[504, 381], cliente=[504, 381]),
                            "solape")
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo["control"], "Participación y Ordenar por")


def barra():
    """Una barra de estado, dibujada fuera del área cliente."""
    return control(id=5, clase="wxStatusBar", nombre="BarraEstado",
                   etiqueta="", rect=[0, 618, 500, 23], texto_px=[0, 0])


class TestBarrasFueraDelCliente(Base):

    def test_la_barra_no_da_recorte(self):
        self.assertIsNone(self.uno(muestra([control(), barra()]), "recorte"))

    def test_la_barra_no_da_margen(self):
        self.assertIsNone(self.uno(muestra([control(), barra()]), "margen"))


class TestLetraChica(Base):

    def test_salta(self):
        fuente = dict(FUENTE, px=11)
        self.assertIsNotNone(self.uno(muestra([control(fuente=fuente)]),
                                      "letra_chica"))

    def test_no_salta(self):
        self.assertIsNone(self.uno(muestra([control()]), "letra_chica"))


class TestFueraDePantalla(Base):

    def test_salta(self):
        ventana = muestra([control()], tamano=[1400, 400],
                          tamano_minimo=[400, 900])
        hallazgos = self.hallazgos(ventana)
        fuera = [h for h in hallazgos if h["regla"] == "fuera_de_pantalla"]
        self.assertEqual(len(fuera), 2)
        self.assertTrue(all(h["gravedad"] == "error" for h in fuera))

    def test_no_salta(self):
        ventana = muestra([control()], tamano=[1366, 728],
                          tamano_minimo=[1366, 728])
        self.assertIsNone(self.uno(ventana, "fuera_de_pantalla"))


class TestCasiAlineados(Base):

    def test_salta(self):
        controles = [control(id=1, rect=[20, 20, 100, 24]),
                     control(id=2, rect=[23, 60, 100, 24])]
        self.assertIsNotNone(self.uno(muestra(controles), "casi_alineados"))

    def test_no_salta(self):
        alineados = [control(id=1, rect=[20, 20, 100, 24]),
                     control(id=2, rect=[20, 60, 100, 24])]
        lejos = [control(id=1, rect=[20, 20, 100, 24]),
                 control(id=2, rect=[30, 60, 100, 24])]
        self.assertIsNone(self.uno(muestra(alineados), "casi_alineados"))
        self.assertIsNone(self.uno(muestra(lejos), "casi_alineados"))

    def test_clases_distintas_no_son_casi_alineados(self):
        texto = control(id=1, rect=[20, 20, 100, 24])
        campo = control(id=2, clase="wxTextCtrl", etiqueta="",
                        rect=[22, 60, 100, 24])
        self.assertIsNone(self.uno(muestra([texto, campo]),
                                   "casi_alineados"))


class TestRitmo(Base):

    def test_salta(self):
        cortos = [control(id=1, rect=[20, 20, 100, 20]),
                  control(id=2, rect=[20, 48, 100, 20]),
                  control(id=3, rect=[20, 78, 100, 20])]
        self.assertIsNotNone(self.uno(muestra(cortos), "ritmo"))
        cinco = [control(id=i + 1, rect=[20, y, 100, 4]) for i, y in
                 enumerate((20, 28, 40, 56, 76))]
        self.assertIsNotNone(self.uno(muestra(cinco), "ritmo"))

    def test_no_salta(self):
        regulares = [control(id=i + 1, rect=[20, y, 100, 20]) for i, y in
                     enumerate((20, 48, 76))]
        self.assertIsNone(self.uno(muestra(regulares), "ritmo"))


class TestMargen(Base):

    def test_salta(self):
        encontrado = self.uno(muestra([control(rect=[4, 20, 100, 24])]),
                              "margen")
        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado["gravedad"], "aviso")

    def test_no_salta(self):
        self.assertIsNone(self.uno(muestra([control(rect=[8, 8, 100, 24])]),
                                   "margen"))


class TestPie(Base):

    def test_salta(self):
        aceptar = control(id=1, clase="wxButton", nombre="Aceptar",
                          etiqueta="Aceptar", rect=[324, 260, 60, 24])
        cancelar = control(id=2, clase="wxButton", nombre="Cancelar",
                           etiqueta="Cancelar", rect=[190, 240, 60, 24])
        self.assertIsNotNone(self.uno(muestra([aceptar, cancelar]), "pie"))

    def test_no_salta(self):
        aceptar = control(id=1, clase="wxButton", nombre="Aceptar",
                          etiqueta="Aceptar", rect=[324, 260, 60, 24])
        cancelar = control(id=2, clase="wxButton", nombre="Cancelar",
                           etiqueta="Cancelar", rect=[190, 260, 60, 24])
        self.assertIsNone(self.uno(muestra([aceptar, cancelar]), "pie"))


class TestPrincipales(Base):

    def test_salta(self):
        botones = [control(id=i + 1, clase="wxButton", nombre=f"B{i}",
                           etiqueta=f"B{i}", bg="#0B6E63",
                           rect=[20 + i * 110, 20, 100, 24])
                   for i in range(3)]
        self.assertIsNotNone(self.uno(muestra(botones), "principales"))

    def test_no_salta(self):
        botones = [control(id=i + 1, clase="wxButton", nombre=f"B{i}",
                           etiqueta=f"B{i}", bg="#0B6E63",
                           rect=[20 + i * 110, 20, 100, 24])
                   for i in range(2)]
        self.assertIsNone(self.uno(muestra(botones), "principales"))


class TestFamilias(Base):

    def test_salta(self):
        dos = [control(id=1, fuente=dict(FUENTE, cara="Consolas")),
               control(id=2, rect=[20, 60, 100, 24])]
        self.assertIsNotNone(self.uno(muestra(dos), "familias"))
        tres = [control(id=i + 1, rect=[20, 20 + i * 40, 100, 24],
                        fuente=dict(FUENTE, peso=peso))
                for i, peso in enumerate((400, 600, 700))]
        self.assertIsNotNone(self.uno(muestra(tres), "familias"))

    def test_no_salta(self):
        controles = [control(id=1, fuente=dict(FUENTE, peso=400)),
                     control(id=2, rect=[20, 60, 100, 24],
                             fuente=dict(FUENTE, peso=600))]
        self.assertIsNone(self.uno(muestra(controles), "familias"))


class TestColorAjeno(Base):

    def test_salta(self):
        encontrado = self.uno(muestra([control(fg="#123456")]), "color_ajeno")
        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado["gravedad"], "aviso")
        self.assertIn("#123456", encontrado["detalle"])

    def test_no_salta(self):
        self.assertIsNone(self.uno(muestra([control(bg="#F0F0F0")]),
                                   "color_ajeno"))


class TestVacio(Base):

    def test_salta(self):
        encontrado = self.uno(muestra([control()]), "vacio")
        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado["gravedad"], "aviso")

    def test_no_salta(self):
        grande = control(rect=[8, 8, 384, 284], etiqueta="", texto_px=[100, 12])
        self.assertIsNone(self.uno(muestra([grande]), "vacio"))


def raiz():
    """La ventana de nivel superior: mide el total, no el área cliente."""
    return control(id=99, clase="wxDialog", nombre="Ventana", etiqueta="",
                   rect=[0, 0, 500, 400], texto_px=[0, 0])


class TestRaizNoEsControl(Base):
    """La ventana no entra en las reglas de posición; sus hijos sí."""

    def test_no_da_recorte_por_ser_mas_grande_que_el_area_cliente(self):
        ventana = muestra([raiz(), control(id=1)])
        self.assertIsNone(self.uno(ventana, "recorte"))

    def test_hijo_directo_se_mide_contra_el_area_cliente(self):
        fuera = control(id=1, rect=[396, 20, 10, 24])
        self.assertIsNotNone(self.uno(muestra([raiz(), fuera]), "recorte"))

    def test_no_da_solape_con_sus_hijos(self):
        ventana = muestra([raiz(), control(id=1)])
        self.assertIsNone(self.uno(ventana, "solape"))

    def test_no_da_ritmo_en_la_columna_de_x_cero(self):
        hijos = [control(id=i + 1, rect=[0, y, 100, 20])
                 for i, y in enumerate((22, 50, 78))]
        self.assertIsNone(self.uno(muestra([raiz(), *hijos]), "ritmo"))

    def test_no_da_casi_alineados_con_un_hijo(self):
        cerca = control(id=1, rect=[3, 450, 100, 24])
        self.assertIsNone(self.uno(muestra([raiz(), cerca]),
                                   "casi_alineados"))

    def test_no_da_margen_negativo(self):
        self.assertIsNone(self.uno(muestra([raiz(), control(id=1)]),
                                   "margen"))

    def test_el_resumen_no_cuenta_el_margen_de_la_ventana(self):
        _, resumen = visual.analizar([muestra([raiz(), control(id=1)])])
        self.assertEqual(resumen["margenes"], [(20, 1)])


class TestLineaDeComando(Base):

    def test_uno_con_error_y_linea_con_muestra_pagina_y_control(self):
        self.archivo(muestra([control(fg="#7B7B7B")]))
        codigo, texto = self.correr()
        self.assertEqual(codigo, 1)
        self.assertIn("error contraste preferencias/Voces «Etiqueta»", texto)

    def test_cero_con_solo_avisos(self):
        self.archivo(muestra([control()]))
        codigo, texto = self.correr()
        self.assertEqual(codigo, 0)
        self.assertIn("aviso vacio", texto)
        self.assertNotIn("error ", texto)

    def test_cero_sin_hallazgos(self):
        grande = control(rect=[8, 8, 384, 284], etiqueta="", texto_px=[100, 12])
        self.archivo(muestra([grande]))
        codigo, texto = self.correr()
        self.assertEqual(codigo, 0)
        self.assertIn("Sin hallazgos.", texto)

    def test_json_guarda_los_hallazgos(self):
        self.archivo(muestra([control(fg="#7B7B7B")]))
        destino = self.carpeta / "informe.json"
        codigo, _ = self.correr("--json", str(destino))
        datos = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(codigo, 1)
        self.assertTrue(any(h["regla"] == "contraste" for h in datos))


class TestResumen(Base):

    def test_reune_margenes_fuentes_y_colores_de_todas_las_ventanas(self):
        primero = muestra([control(rect=[8, 8, 384, 284], etiqueta="",
                                   fg="#123456")])
        fuente = dict(FUENTE, cara="Consolas", px=13, peso=600)
        segundo = muestra([control(id=1, rect=[12, 12, 300, 200],
                                   etiqueta="", fuente=fuente)],
                          muestra="principal", pagina=None)
        _, resumen = visual.analizar([primero, segundo])
        self.assertEqual(resumen["ventanas"], 2)
        self.assertEqual(resumen["margenes"], [(8, 1), (12, 1)])
        self.assertEqual(resumen["familias"], ["Consolas", "Segoe UI"])
        self.assertEqual(resumen["tamanos"], [12, 13])
        self.assertEqual(resumen["colores_ajenos"], ["#123456"])
        texto = visual.formatear_resumen(resumen)
        self.assertIn("Margen exterior: 8 px en 1 ventana, 12 px en 1 ventana",
                      texto)
        self.assertIn("Familias de letra: Consolas, Segoe UI", texto)
        self.assertIn("Tamaños de letra: 12, 13 px", texto)
        self.assertIn("Colores fuera de la paleta: #123456", texto)


if __name__ == "__main__":
    unittest.main()
