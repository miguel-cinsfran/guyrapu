# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del doble del lector y de la lista de ventanas de la aplicación.

No se abre ninguna ventana: se comprueba que cada anuncio se reenvíe al lector
real y al grabador de la sonda, que el inicializador deje ese doble donde
`anunciar` lo encuentra y que la lista de ventanas traiga lo que pide el
carril.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from guyrapu.core import paths
from guyrapu.ui import accesibilidad, gui
from qa.nvda import app, ventanas_app


class TestVentanas(unittest.TestCase):

    def test_la_tabla_tiene_las_nueve_ventanas_con_sus_campos(self):
        self.assertEqual(
            [entrada["nombre"] for entrada in ventanas_app.VENTANAS],
            ["preferencias", "interaccion", "comandos", "estilos",
             "historial", "descargas", "palabras", "encuestas", "medios"])
        for entrada in ventanas_app.VENTANAS:
            campos = {"nombre", "menu", "titulo", "primero"}
            if "pagina" in entrada:
                campos.add("pagina")
            self.assertEqual(set(entrada), campos)
            self.assertTrue(all(entrada[clave]
                                for clave in ("nombre", "menu", "titulo")))
        self.assertEqual(
            len({entrada["nombre"] for entrada in ventanas_app.VENTANAS}), 9)
        self.assertEqual(ventanas_app.VENTANAS[0]["titulo"], "Preferencias")
        self.assertEqual(ventanas_app.VENTANAS[0]["primero"], "General")
        self.assertEqual(ventanas_app.VENTANAS[1]["titulo"], "Interacción")

    def test_las_tres_paginas_de_interaccion_tienen_su_entrada(self):
        esperadas = {
            "palabras": "Palabras bloqueadas",
            "encuestas": "Encuestas",
            "medios": "Medios",
        }
        por_nombre = {entrada["nombre"]: entrada
                      for entrada in ventanas_app.VENTANAS}
        for nombre, pagina in esperadas.items():
            with self.subTest(nombre=nombre):
                entrada = por_nombre[nombre]
                self.assertEqual(entrada["pagina"], pagina)
                self.assertEqual(entrada["menu"],
                                 "Interacción > Abrir Interacción…")
                self.assertTrue(entrada["primero"])

    def test_cada_pagina_de_interaccion_se_puede_pedir_sola(self):
        for pedida in ("palabras", "encuestas", "medios"):
            with self.subTest(pedida=pedida):
                banco = mock.Mock()
                banco.pedir.return_value = {"datos": {"pid": 7}}
                banco.esperar_lista.return_value = True
                conducidas = []

                def ventana(_banco, _cliente, entrada, _pid, _catalogo,
                            _aprobar):
                    conducidas.append(entrada["nombre"])
                    return [], False

                with (
                    mock.patch.object(app, "Aplicacion", return_value=banco),
                    mock.patch.object(app.reglas, "leer_catalogo_ingles",
                                      return_value=set()),
                    mock.patch.object(app, "_ventana", side_effect=ventana),
                ):
                    app.recorrer(mock.Mock(), SimpleNamespace(
                        ventana=pedida, aprobar=False))
                self.assertEqual(conducidas, [pedida])

    def test_ventana_comandos_elige_solo_esa(self):
        banco = mock.Mock()
        banco.pedir.return_value = {"datos": {"pid": 7}}
        banco.esperar_lista.return_value = True
        conducidas = []

        def ventana(_banco, _cliente, entrada, _pid, _catalogo, _aprobar):
            conducidas.append(entrada["nombre"])
            return [], False

        with (
            mock.patch.object(app, "Aplicacion", return_value=banco),
            mock.patch.object(app.reglas, "leer_catalogo_ingles",
                              return_value=set()),
            mock.patch.object(app, "_ventana", side_effect=ventana),
        ):
            app.recorrer(mock.Mock(), SimpleNamespace(
                ventana="comandos", aprobar=False))
        self.assertEqual(conducidas, ["comandos"])


class TestAplicacion(unittest.TestCase):

    def test_arrancar_pasa_la_carpeta_de_datos_del_carril(self):
        with tempfile.TemporaryDirectory() as base:
            carpeta = Path(base) / "carril"
            aplicacion = app.Aplicacion(carpeta)
            with (
                mock.patch.object(app.subprocess, "Popen") as popen,
                mock.patch("builtins.open"),
            ):
                aplicacion.arrancar()
            entorno = popen.call_args.kwargs["env"]
            self.assertTrue(
                Path(entorno[app.VAR_DATOS]).is_relative_to(carpeta))


class TestDobleLector(unittest.TestCase):

    def test_pasa_la_misma_frase_al_lector_real_y_al_grabador(self):
        real = mock.Mock()
        grabador = mock.Mock()
        app.DobleLector(real, grabador).speak("Mensaje")
        real.speak.assert_called_once_with("Mensaje", interrupt=False)
        grabador.speak.assert_called_once_with("Mensaje", interrupt=False)

    def test_tambien_manda_el_braille_a_los_dos(self):
        real = mock.Mock()
        grabador = mock.Mock()
        app.DobleLector(real, grabador).braille("Mensaje")
        real.braille.assert_called_once_with("Mensaje")
        grabador.braille.assert_called_once_with("Mensaje")


class TestPreparar(unittest.TestCase):

    def test_la_carpeta_de_datos_del_carril_queda_aislada(self):
        with tempfile.TemporaryDirectory() as base:
            original = Path(base) / "original"
            original.mkdir()
            (original / "config.ini").write_text("[ui]\n", encoding="utf-8")
            aislada = Path(base) / "aislada"

            with (
                mock.patch.object(paths, "carpeta_datos",
                                  return_value=original),
                mock.patch.object(gui, "_lector_init"),
                mock.patch.object(accesibilidad, "_lector_init"),
                mock.patch.dict(os.environ,
                                {app.VAR_DATOS: str(aislada)}),
                mock.patch.object(app.sonda, "instalar"),
            ):
                app.preparar()
                self.assertTrue(paths.comandos().is_relative_to(aislada))
                self.assertEqual(
                    (aislada / "config.ini").read_text(encoding="utf-8"),
                    "[ui]\n")

    def test_el_inicializador_deja_el_doble_que_usa_anunciar(self):
        real = mock.Mock()
        grabador = mock.Mock()

        def init_gui():
            accesibilidad._lector = real

        def init_accesibilidad():
            accesibilidad._lector = real

        anterior = accesibilidad._lector
        self.addCleanup(setattr, accesibilidad, "_lector", anterior)

        def instalar():
            accesibilidad._lector = grabador

        with (
            mock.patch.object(gui, "_lector_init", init_gui),
            mock.patch.object(accesibilidad, "_lector_init",
                              init_accesibilidad),
            mock.patch.object(app.sonda, "instalar", side_effect=instalar),
        ):
            app.preparar()
            gui._lector_init()
            doble = accesibilidad._lector
            self.assertIsInstance(doble, app.DobleLector)
            doble.speak("Hola")

        real.speak.assert_called_once_with("Hola", interrupt=False)
        grabador.speak.assert_called_once_with("Hola", interrupt=False)


if __name__ == "__main__":
    unittest.main()
