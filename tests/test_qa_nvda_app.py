# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del doble del lector y de la lista de ventanas de la aplicación.

No se abre ninguna ventana: se comprueba que cada anuncio se reenvíe al lector
real y al grabador de la sonda, que el inicializador deje ese doble donde
`anunciar` lo encuentra y que la lista de ventanas traiga lo que pide el
carril.
"""

import configparser
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from guyrapu.core import paths
from guyrapu.ui import accesibilidad, gui
from guyrapu.voice import sound_player
from qa.nvda import app, recorrido, ventanas_app


class TestVentanas(unittest.TestCase):

    def test_la_tabla_tiene_una_entrada_por_ventana_con_sus_campos(self):
        self.assertEqual(
            [entrada["nombre"] for entrada in ventanas_app.VENTANAS],
             ["preferencias", "interaccion", "comandos", "estilos",
              "historial", "descargas", "musica", "ia", "voces", "obs",
              "ensayo", "palabras", "encuestas", "preguntas",
              "medios", "disparador", "preferencias_interfaz",
              "preferencias_sonidos",
             "preferencias_atajos", "preferencias_voces",
             "preferencias_lectura", "preferencias_cola_de_lectura",
             "preferencias_eventos_del_directo", "preferencias_filtros",
             "preferencias_estado_f2", "preferencias_conexion",
             "preferencias_youtube", "preferencias_reproductor",
             "preferencias_musica", "preferencias_descargas",
             "preferencias_inteligencia_artificial", "preferencias_obs",
             "preferencias_camara"])
        for entrada in ventanas_app.VENTANAS:
            campos = {"nombre", "menu", "titulo", "primero"}
            if "pagina" in entrada:
                campos.add("pagina")
            if "paginas" in entrada:
                campos.add("paginas")
            if "acciones" in entrada:
                campos.add("acciones")
            if "ajustes" in entrada:
                campos.add("ajustes")
            if "tope" in entrada:
                campos.add("tope")
            if "primero_lista" in entrada:
                campos.add("primero_lista")
            if "valor_variable" in entrada:
                campos.add("valor_variable")
            if "titulo_menu" in entrada:
                campos.add("titulo_menu")
            if "pulsar" in entrada:
                campos.add("pulsar")
            self.assertEqual(set(entrada), campos)
            self.assertTrue(all(entrada[clave]
                                for clave in ("nombre", "menu", "titulo")))
        self.assertEqual(
            len({entrada["nombre"] for entrada in ventanas_app.VENTANAS}), 33)
        self.assertEqual(ventanas_app.VENTANAS[0]["titulo"], "Preferencias")
        self.assertEqual(ventanas_app.VENTANAS[0]["primero"], "General")
        self.assertEqual(ventanas_app.VENTANAS[1]["titulo"], "Interacción")

    def test_musica_e_ia_estan_en_la_tabla_con_su_menu_titulo_y_primero(self):
        from guyrapu.core.idioma import _
        from guyrapu.ui import ia_ventana, musica_ventana

        por_nombre = {entrada["nombre"]: entrada
                      for entrada in ventanas_app.VENTANAS}
        self.assertEqual(len(por_nombre), len(ventanas_app.VENTANAS))
        self.assertEqual(
            por_nombre["musica"]["titulo"], _(musica_ventana.TITULO))
        self.assertEqual(
            por_nombre["ia"]["titulo"], _(ia_ventana.TITULO))
        for nombre, menu, primero in (
                ("musica", "Música > Elegir música…", "Buscar en la música"),
                ("ia", "Ver > Preguntar a la IA sobre la imagen…",
                 "Mensaje")):
            with self.subTest(nombre=nombre):
                entrada = por_nombre[nombre]
                self.assertEqual(entrada["menu"], menu)
                self.assertEqual(entrada["primero"], primero)
                self.assertTrue(entrada["titulo"])

    def test_voces_abre_administrar_voces_y_recorre_la_ventana(self):
        por_nombre = {entrada["nombre"]: entrada
                      for entrada in ventanas_app.VENTANAS}
        entrada = por_nombre["voces"]
        self.assertEqual(entrada["menu"], "Voz > Administrar voces…")
        self.assertEqual(entrada["titulo"], "Administrar voces")
        self.assertEqual(entrada["primero"], "Paquetes de voces")
        self.assertEqual(entrada["primero_lista"], "Paquetes de voces")

    def test_obs_abre_el_panel_y_recorre_la_pestana_general(self):
        por_nombre = {entrada["nombre"]: entrada
                      for entrada in ventanas_app.VENTANAS}
        entrada = por_nombre["obs"]
        self.assertEqual(entrada["menu"], "OBS > Panel de OBS…")
        self.assertEqual(entrada["titulo"], "Panel de OBS")
        self.assertEqual(entrada["primero"], "Estado")
        self.assertEqual(entrada["valor_variable"], ["Estado"])

    def test_ensayo_y_disparador_estan_en_la_tabla_con_su_menu_y_primero(self):
        por_nombre = {entrada["nombre"]: entrada
                      for entrada in ventanas_app.VENTANAS}
        ensayo = por_nombre["ensayo"]
        self.assertEqual(ensayo["menu"], "Interacción > Probar sin directo…")
        self.assertEqual(ensayo["titulo"], "Prueba sin directo")
        self.assertEqual(ensayo["primero"], "Autor:")
        disparador = por_nombre["disparador"]
        self.assertEqual(disparador["menu"],
                         "Interacción > Abrir Interacción…")
        self.assertEqual(disparador["titulo"], "Agregar disparador")
        self.assertEqual(disparador["titulo_menu"], "Interacción")
        self.assertEqual(disparador["pagina"], "Disparadores")
        self.assertEqual(disparador["pulsar"], "Agregar")
        self.assertEqual(disparador["primero"], "Nombre:")

    def test_historial_activa_conectar_y_eliminar_con_el_vacio(self):
        historial = next(entrada for entrada in ventanas_app.VENTANAS
                         if entrada["nombre"] == "historial")
        self.assertEqual(
            [(accion["control"], accion["espera"])
             for accion in historial["acciones"]],
            [("Conectar (el historial está vacío)",
              "el historial está vacío"),
             ("Eliminar (el historial está vacío)",
              "el historial está vacío")])

    def test_las_cuatro_paginas_de_interaccion_tienen_su_entrada(self):
        esperadas = {
            "palabras": "Palabras bloqueadas",
            "encuestas": "Encuestas",
            "preguntas": "Preguntas",
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

    def test_una_entrada_por_pagina_de_preferencias_salvo_general(self):
        entradas = [entrada for entrada in ventanas_app.VENTANAS
                    if entrada["nombre"].startswith("preferencias_")]
        self.assertEqual([entrada["pagina"] for entrada in entradas],
                         list(ventanas_app.PAGINAS_PREFERENCIAS[1:]))
        self.assertEqual(len({e["nombre"] for e in entradas}), len(entradas))
        for entrada in entradas:
            with self.subTest(entrada=entrada["nombre"]):
                self.assertEqual(entrada["menu"], "Herramientas > Preferencias")
                self.assertEqual(entrada["titulo"], "Preferencias")
                self.assertIs(entrada["paginas"],
                              ventanas_app.PAGINAS_PREFERENCIAS)
                self.assertTrue(entrada["primero"])

    def test_las_paginas_de_preferencias_coinciden_con_las_de_la_app(self):
        from guyrapu.ui import gui_preferencias

        falso = SimpleNamespace(
            _envolver=lambda fabrica: fabrica, _pagina_de=lambda *args: None,
            _config={}, _ruta="", _pag_interfaz=None, _pag_cola=None,
            _pag_filtros=None, _pag_estado=None, _pag_conexion=None,
            _pag_reproductor=None)
        etiquetas = [etiqueta for etiqueta, _fabrica in
                     gui_preferencias.PreferenciasDialog._entradas(falso)]
        self.assertEqual(list(ventanas_app.PAGINAS_PREFERENCIAS), etiquetas)

    def test_las_acciones_de_atajos_y_sonidos(self):
        por_nombre = {entrada["nombre"]: entrada
                      for entrada in ventanas_app.VENTANAS}
        self.assertEqual(por_nombre["preferencias_atajos"]["acciones"],
                         [{"control": "Bajar velocidad de la voz: F9 (fija)",
                           "espera": "Este atajo es fijo"}])
        self.assertEqual(por_nombre["preferencias_sonidos"]["acciones"],
                         [{"control": "Acción completada; Familia: Completado",
                           "gesto": "upArrow"}])

    def test_cada_pagina_de_interaccion_se_puede_pedir_sola(self):
        for pedida in ("palabras", "encuestas", "preguntas", "medios"):
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


class BancoFalso:
    """Anota las órdenes de `_ventana` y contesta lo justo."""

    def __init__(self, al_frente=True):
        self.resultado_frente = al_frente
        self.llamadas = []

    def pedir(self, op, **extra):
        self.llamadas.append(op)
        return {"datos": {}}

    def esperar_ventana(self, titulo, segundos=15.0):
        self.llamadas.append("esperar_ventana")
        return {"titulo": titulo, "visible": True}

    def al_frente(self):
        self.llamadas.append("al_frente")
        return self.resultado_frente


class TestVentana(unittest.TestCase):

    def test_lleva_la_app_al_frente_antes_de_abrir_el_menu(self):
        banco = BancoFalso(True)
        with (
            mock.patch.object(app.recorrido, "conducir",
                              return_value={"pasos": []}),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            app._ventana(banco, mock.Mock(), ventanas_app.VENTANAS[0],
                         7, set(), False)
        self.assertLess(banco.llamadas.index("al_frente"),
                        banco.llamadas.index("menu_click"))

    def test_pide_el_frente_despues_de_esperar_y_antes_de_conducir(self):
        banco = BancoFalso(True)

        def conducir(_cliente, _datos):
            banco.llamadas.append("conducir")
            return {"pasos": []}

        with (
            mock.patch.object(app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            app._ventana(banco, mock.Mock(), ventanas_app.VENTANAS[0],
                         7, set(), False)
        claves = [llamada for llamada in banco.llamadas
                  if llamada in ("esperar_ventana", "al_frente", "conducir")]
        self.assertEqual(claves,
                         ["al_frente", "esperar_ventana", "al_frente",
                          "conducir"])

    def test_pasa_las_acciones_de_la_entrada_a_conducir(self):
        entrada = next(item for item in ventanas_app.VENTANAS
                       if item["nombre"] == "historial")
        visto = {}

        def conducir(_cliente, datos):
            visto["acciones"] = datos.get("acciones")
            return {"pasos": []}

        with (
            mock.patch.object(app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            app._ventana(BancoFalso(True), mock.Mock(), entrada,
                         7, set(), False)
        self.assertEqual(visto["acciones"], entrada["acciones"])

    def test_espera_la_ventana_del_menu_que_declara_la_entrada(self):
        banco = mock.Mock()
        banco.pedir.return_value = {"datos": {}}
        banco.esperar_ventana.return_value = {"visible": True}
        banco.al_frente.return_value = True
        entrada = next(item for item in ventanas_app.VENTANAS
                       if item["nombre"] == "disparador")
        with (
            mock.patch.object(app.recorrido, "conducir",
                              return_value={"pasos": []}),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            app._ventana(banco, mock.Mock(), entrada, 7, set(), False)
        banco.esperar_ventana.assert_called_once_with(
            "Interacción", segundos=15.0)

    def test_pasa_el_boton_a_pulsar_de_la_entrada_a_conducir(self):
        entrada = next(item for item in ventanas_app.VENTANAS
                       if item["nombre"] == "disparador")
        visto = {}

        def conducir(_cliente, datos):
            visto["pulsar"] = datos.get("pulsar")
            return {"pasos": []}

        with (
            mock.patch.object(app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            app._ventana(BancoFalso(True), mock.Mock(), entrada, 7, set(), False)
        self.assertEqual(visto["pulsar"], "Agregar")

    def test_pasa_el_primero_lista_de_la_entrada_a_conducir(self):
        entrada = next(item for item in ventanas_app.VENTANAS
                       if item["nombre"] == "voces")
        visto = {}

        def conducir(_cliente, datos):
            visto["primero_lista"] = datos.get("primero_lista")
            return {"pasos": []}

        with (
            mock.patch.object(app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            app._ventana(BancoFalso(True), mock.Mock(), entrada,
                         7, set(), False)
        self.assertEqual(visto["primero_lista"], "Paquetes de voces")

    def test_la_transcripcion_de_obs_ignora_el_valor_del_estado(self):
        entrada = next(item for item in ventanas_app.VENTANAS
                       if item["nombre"] == "obs")
        datos = {"pasos": [{
            "tecla": "tab", "fase": "ida",
            "habla": [{"texto":
                       "Estado edición Alt+ e Revisa antes de transmitir"}],
            "foco": {"nombre": "Estado", "rol_nombre": "EDITABLETEXT",
                     "atajo": "Alt+E", "valor": "Revisa antes de transmitir"},
        }]}
        visto = {}

        def comparar(_nombre, nueva, _aprobar):
            visto["nueva"] = nueva
            return ""

        with (
            mock.patch.object(app.recorrido, "conducir", return_value=datos),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              side_effect=comparar),
        ):
            app._ventana(BancoFalso(True), mock.Mock(), entrada, 7, set(), False)
        self.assertIn("dijo='Estado edición Alt+ e'", visto["nueva"])
        self.assertNotIn("Revisa antes", visto["nueva"])

    def test_un_hallazgo_de_verdad_sale_en_la_linea_de_la_transcripcion(self):
        hallazgo = {"regla": "sin_nombre", "nivel": "aviso",
                    "ventana": "voces", "paso": 3, "tecla": "tab",
                    "detalle": "la parada no tiene nombre"}
        entrada = next(item for item in ventanas_app.VENTANAS
                       if item["nombre"] == "voces")
        with (
            mock.patch.object(app.recorrido, "conducir",
                              return_value={"pasos": []}),
            mock.patch.object(app.reglas, "analizar",
                              return_value=[hallazgo]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            lineas, _ = app._ventana(BancoFalso(True), mock.Mock(), entrada,
                                     7, set(), False)
        self.assertTrue(any("hallazgo sin_nombre" in linea
                            for linea in lineas))

    def test_recorrer_anuncia_cada_ventana_con_flush(self):
        banco = mock.Mock()
        banco.pedir.return_value = {"datos": {"pid": 7}}
        banco.esperar_lista.return_value = True
        with (
            mock.patch.object(app, "Aplicacion", return_value=banco),
            mock.patch.object(app.reglas, "leer_catalogo_ingles",
                              return_value=set()),
            mock.patch.object(app, "_ventana", return_value=([], False)),
            mock.patch("builtins.print") as imprimir,
        ):
            app.recorrer(mock.Mock(), SimpleNamespace(
                ventana=None, aprobar=False))
        self.assertEqual(
            [llamada.args[0] for llamada in imprimir.call_args_list],
            [f"ventana {entrada['nombre']}"
             for entrada in ventanas_app.VENTANAS])
        self.assertTrue(all(llamada.kwargs.get("flush")
                            for llamada in imprimir.call_args_list))

    def test_pasa_el_tope_de_la_entrada_a_conducir(self):
        from guyrapu.core import config as cfg

        vistos = []

        def conducir(_cliente, _datos, **opciones):
            vistos.append(opciones)
            return {"pasos": []}

        with (
            mock.patch.object(app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            atajos = next(item for item in ventanas_app.VENTANAS
                          if item["nombre"] == "preferencias_atajos")
            interfaz = next(item for item in ventanas_app.VENTANAS
                            if item["nombre"] == "preferencias_interfaz")
            app._ventana(BancoFalso(True), mock.Mock(), atajos, 7, set(),
                         False)
            app._ventana(BancoFalso(True), mock.Mock(), interfaz, 7, set(),
                         False)
        botones = sum(len(acciones) for _, acciones in cfg.ATAJOS_GRUPOS) + 1
        self.assertEqual(vistos[0]["tope"], atajos["tope"])
        self.assertGreaterEqual(atajos["tope"], botones)
        self.assertEqual(vistos[1], {})

    def test_pasa_la_lista_de_paginas_de_la_entrada_a_conducir(self):
        visto = {}

        def conducir(_cliente, datos, **_opciones):
            visto["paginas"] = datos.get("paginas")
            return {"pasos": []}

        with (
            mock.patch.object(app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            atajos = next(item for item in ventanas_app.VENTANAS
                          if item["nombre"] == "preferencias_atajos")
            palabras = next(item for item in ventanas_app.VENTANAS
                            if item["nombre"] == "palabras")
            app._ventana(BancoFalso(True), mock.Mock(), atajos, 7, set(), False)
            self.assertIs(visto["paginas"],
                          ventanas_app.PAGINAS_PREFERENCIAS)
            app._ventana(BancoFalso(True), mock.Mock(), palabras, 7, set(),
                         False)
            self.assertEqual(visto["paginas"], app._paginas_de_interaccion())

    def test_si_no_queda_al_frente_corta_sin_conducir(self):
        banco = BancoFalso(False)
        with (
            mock.patch.object(app.recorrido, "conducir") as conducir,
            mock.patch.object(app.reglas, "analizar", return_value=[]),
            mock.patch.object(app.transcripcion, "comparar",
                              return_value=""),
        ):
            with self.assertRaises(app.InstrumentoRoto) as capturado:
                app._ventana(banco, mock.Mock(), ventanas_app.VENTANAS[0],
                             7, set(), False)
        self.assertIn("no se pudo traer al frente la app para «Preferencias»",
                      str(capturado.exception))
        conducir.assert_not_called()


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
                esperado = (
                    "[ui]\n\n[musica]\npreguntar_igualar = false\n"
                    f"carpeta = {aislada / 'musica'}\n\n")
                self.assertEqual(
                    (aislada / "config.ini").read_text(encoding="utf-8"),
                    esperado)

    def test_aislar_datos_aplica_los_ajustes_de_la_entrada_sin_tocar_el_real(self):
        musica = next(entrada for entrada in ventanas_app.VENTANAS
                      if entrada["nombre"] == "musica")
        self.assertEqual(
            musica["ajustes"],
            [{"seccion": "musica", "clave": "preguntar_igualar",
              "valor": "false"}])
        with tempfile.TemporaryDirectory() as base:
            original = Path(base) / "original"
            original.mkdir()
            (original / "config.ini").write_text("[ui]\n", encoding="utf-8")
            aislada = Path(base) / "aislada"

            with (
                mock.patch.object(paths, "carpeta_datos",
                                  return_value=original),
                mock.patch.dict(os.environ, {app.VAR_DATOS: str(aislada)}),
            ):
                app._aislar_datos()

            parser = configparser.ConfigParser(interpolation=None,
                                               default_section="__none__")
            parser.read(aislada / "config.ini", encoding="utf-8")
            self.assertEqual(parser.get("musica", "preguntar_igualar"),
                             "false")
            self.assertEqual(
                (original / "config.ini").read_text(encoding="utf-8"),
                "[ui]\n")

    def test_la_carpeta_de_musica_del_carril_no_es_la_del_usuario(self):
        with tempfile.TemporaryDirectory() as base:
            original = Path(base) / "original"
            original.mkdir()
            (original / "config.ini").write_text(
                "[musica]\ncarpeta = C:/Users/Alguien/Music\n", encoding="utf-8")
            aislada = Path(base) / "aislada"

            with (
                mock.patch.object(paths, "carpeta_datos",
                                  return_value=original),
                mock.patch.dict(os.environ, {app.VAR_DATOS: str(aislada)}),
            ):
                app._aislar_datos()

            parser = configparser.ConfigParser(interpolation=None,
                                               default_section="__none__")
            parser.read(aislada / "config.ini", encoding="utf-8")
            usada = parser.get("musica", "carpeta")
            self.assertNotEqual(usada, "C:/Users/Alguien/Music")
            self.assertEqual(Path(usada), aislada / "musica")
            self.assertTrue((aislada / "musica").is_dir())
            self.assertEqual(list((aislada / "musica").iterdir()), [])
            self.assertEqual(
                (original / "config.ini").read_text(encoding="utf-8"),
                "[musica]\ncarpeta = C:/Users/Alguien/Music\n")

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


class TestGrabadorSonidos(unittest.TestCase):

    def tearDown(self):
        logger = logging.getLogger("guyrapu.sound_player")
        for manejador in list(logger.handlers):
            if isinstance(manejador, app._GrabadorSonidos):
                logger.removeHandler(manejador)

    def test_la_cadena_real_anota_el_sonido_con_la_sonda_instalada(self):
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "sonidos.txt"
            entorno = dict(os.environ)
            entorno.update({
                recorrido.VAR_SONIDOS: str(ruta),
                app.VAR_DATOS: str(Path(base) / "datos"),
                app.sonda.VAR_DESTINO: str(Path(base) / "anuncios.txt"),
                app.sonda.VAR_ORDENES: str(Path(base) / "ordenes.json"),
                app.sonda.VAR_RESULTADOS: str(Path(base) / "resultados.txt"),
            })
            programa = (
                "from pathlib import Path;"
                "import qa.nvda.app as carril; carril.preparar();"
                "from guyrapu.core import config; config.configurar_logging();"
                "from guyrapu.voice import sound_player as snd;"
                "snd._eventos = {'orilla': Path('sin-archivo.wav')};"
                "snd.reproducir('orilla')"
            )
            proceso = subprocess.run(
                [sys.executable, "-B", "-c", programa],
                cwd=Path(__file__).resolve().parent.parent, env=entorno,
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=30)
            self.assertEqual(proceso.returncode, 0, proceso.stderr)
            contenido = (ruta.read_text(encoding="utf-8") if ruta.exists()
                         else "")
            self.assertEqual(contenido, "orilla\n")

    def _preparar_con_sonidos(self, ruta):
        with (
            mock.patch.dict(os.environ, {recorrido.VAR_SONIDOS: str(ruta)}),
            mock.patch.object(gui, "_lector_init"),
            mock.patch.object(accesibilidad, "_lector_init"),
            mock.patch.object(app.sonda, "instalar"),
        ):
            app.preparar()

    def test_anota_el_evento_de_un_sonido_real_del_catalogo(self):
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "sonidos.txt"
            self._preparar_con_sonidos(ruta)
            with (
                mock.patch.object(sound_player, "_eventos",
                                  {"listo": Path(base) / "listo.wav"}),
                mock.patch.object(sound_player, "_activo", True),
                mock.patch.object(sound_player, "_silenciado_usuario", False),
                mock.patch.object(sound_player, "_encolar"),
            ):
                sound_player.reproducir("listo")
            self.assertEqual(ruta.read_text(encoding="utf-8"), "listo\n")

    def test_no_anota_un_sonido_omitido(self):
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "sonidos.txt"
            self._preparar_con_sonidos(ruta)
            with (
                mock.patch.object(sound_player, "_eventos",
                                  {"listo": Path(base) / "listo.wav"}),
                mock.patch.object(sound_player, "_activo", True),
                mock.patch.object(sound_player, "_silenciado_usuario", True),
                mock.patch.object(sound_player, "_encolar"),
            ):
                sound_player.reproducir("listo")
            self.assertFalse(ruta.exists())


if __name__ == "__main__":
    unittest.main()
