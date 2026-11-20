# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Toda ventana del paquete tiene muestra o motivo para no tenerla.

Recorre el código fuente con el árbol sintáctico: ni importa la interfaz ni
abre ventanas. Así descubre también las clases que cuelgan de otra ventana
y que no se nombran en ningún registro.
"""

import ast
import contextlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

_RAIZ = Path(__file__).resolve().parent.parent
_QA = _RAIZ / "qa"
sys.path.insert(0, str(_QA))
_paquete = importlib.util.spec_from_file_location(
    "galeria_muestras_prueba", _QA / "galeria_muestras.py")
registro = importlib.util.module_from_spec(_paquete)
_paquete.loader.exec_module(registro)

# Las clases base del toolkit gráfico que hacen de una clase una ventana.
RAICES = {"Dialog", "Frame", "MiniFrame"}

CLASES_PEDIDAS = {
    "VentanaPrincipal", "PreferenciasDialog", "VentanaInteraccion",
    "VentanaMusica", "VentanaObs", "VentanaIA", "GestorDescargasDialog",
    "HistorialDialog", "VentanaVoces", "VentanaRestream", "VentanaEnsayo",
    "VentanaParticipacion", "CuadroBuscarChat", "DialogoComando",
    "DialogoPalabra", "DialogoEncuesta", "DialogoEstilo", "DialogoTipos",
    "DialogoMedio", "DialogoMensaje", "DialogoMeta", "DialogoNombre",
    "DialogoDisparador",
    "DialogoActualizacion", "DialogoAgregarCaptura", "DialogoAjustesPerfil",
    "DialogoArchivo", "DialogoAsistentePerfiles", "DialogoCapturarVentana",
    "DialogoDestinoManual", "DialogoDirectoYoutube", "DialogoEditorLista",
    "DialogoEleccion", "DialogoElegirDestino", "DialogoEnlace",
    "DialogoEstado", "DialogoFormato", "DialogoJuego", "DialogoMetaDestino",
    "DialogoNombrePerfil", "DialogoPerfilRestream", "DialogoPruebaConexion",
    "DialogoPruebaEquipo", "DialogoRedactar", "DialogoResultadoPrueba",
    "DialogoResultadoPruebaConexion", "DialogoResumenAsistente",
    "DialogoTexto", "DialogoUsosPerfil", "DisenoEscenaDialog",
    "FiltrosMicrofonoDialog", "MicrofonoObsDialog", "TamanoFuenteDialog",
    "VentanaEspera",
}


def _nombre_base(nodo):
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        return nodo.attr
    return None


def _clases_del_paquete():
    """Nombre de cada clase y los nombres de sus bases directas."""
    halladas = {}
    for archivo in (_RAIZ / "guyrapu").rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ClassDef):
                bases = halladas.setdefault(nodo.name, set())
                bases.update(b for b in map(_nombre_base, nodo.bases) if b)
    return halladas


def _ventanas(clases):
    """Cierre de las clases que heredan de una base de ventana."""
    encontradas = set()
    cambio = True
    while cambio:
        cambio = False
        for nombre, bases in clases.items():
            if nombre in encontradas:
                continue
            if RAICES & bases or encontradas & bases:
                encontradas.add(nombre)
                cambio = True
    return encontradas


def _con_muestra():
    return {entrada[1] for entrada in registro.MUESTRAS}


class TestCoberturaDeLaGaleria(unittest.TestCase):

    def test_p2_las_clases_pedidas_tienen_muestra(self):
        faltan = CLASES_PEDIDAS - _con_muestra()
        self.assertEqual(sorted(faltan), [],
                         "sin muestra: " + ", ".join(sorted(faltan)))

    def test_p3_toda_ventana_tiene_muestra_o_motivo(self):
        ventanas = _ventanas(_clases_del_paquete())
        cubiertas = _con_muestra() | set(registro.SIN_MUESTRA)
        faltan = ventanas - cubiertas
        self.assertEqual(sorted(faltan), [],
                         "sin registrar: " + ", ".join(sorted(faltan)))

    def test_p3_sin_muestra_no_nombra_clases_inexistentes(self):
        clases = _clases_del_paquete()
        inexistentes = set(registro.SIN_MUESTRA) - set(clases)
        self.assertEqual(sorted(inexistentes), [],
                         "no existen: " + ", ".join(sorted(inexistentes)))

    def test_p3_sin_muestra_no_repite_una_muestra(self):
        repetidas = set(registro.SIN_MUESTRA) & _con_muestra()
        self.assertEqual(sorted(repetidas), [],
                         "ya cubiertas: " + ", ".join(sorted(repetidas)))

    def test_p3_los_motivos_no_estan_vacios(self):
        vacios = [clase for clase, motivo in registro.SIN_MUESTRA.items()
                  if not str(motivo or "").strip()]
        self.assertEqual(vacios, [], "motivo vacío: " + ", ".join(vacios))

    def test_p3_las_clases_pedidas_no_estan_en_sin_muestra(self):
        prohibidas = CLASES_PEDIDAS & set(registro.SIN_MUESTRA)
        self.assertEqual(sorted(prohibidas), [],
                         "pedidas sin mostrar: " + ", ".join(sorted(prohibidas)))

    def test_p3_no_queda_el_motivo_falta_la_muestra(self):
        viejos = [clase for clase, motivo in registro.SIN_MUESTRA.items()
                  if str(motivo or "").strip() == "falta la muestra"]
        self.assertEqual(viejos, [],
                         "sin armar: " + ", ".join(sorted(viejos)))


class TestMuestraConChatDeLaGaleria(unittest.TestCase):

    def setUp(self):
        app_de_prueba()
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.pila = contextlib.ExitStack()
        self.addCleanup(self.pila.close)
        self.pila.enter_context(redirigir_rutas(self.temporal.name))

    def _armar(self, nombre):
        entrada = next(e for e in registro.MUESTRAS if e[0] == nombre)
        ventana = entrada[3](SimpleNamespace(pila=self.pila))
        ventana.ShowWithoutActivating()
        self.addCleanup(destruir, ventana)
        return ventana

    def test_p1_la_muestra_con_chat_deja_la_zona_visible_en_las_tres_paginas(self):
        con_chat = self._armar("principal_con_chat")
        sin_chat = self._armar("principal_desconectada")
        self.assertTrue(con_chat._zona.IsShown())
        self.assertFalse(sin_chat._zona.IsShown())
        self.assertEqual(
            [con_chat.nb.GetPageText(i)
             for i in range(con_chat.nb.GetPageCount())],
            ["Chat del directo", "Comentarios", "Información"])
        for i in range(con_chat.nb.GetPageCount()):
            con_chat.nb.SetSelection(i)
            self.assertTrue(con_chat._zona.IsShown(),
                            con_chat.nb.GetPageText(i))


if __name__ == "__main__":
    unittest.main()
