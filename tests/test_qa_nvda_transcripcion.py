# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del formato de las transcripciones del carril de la aplicación.

Se arman recorridos a mano, con las mismas claves que deja `recorrido.py`, y
se comprueba que el texto no dependa de horas, hwnd ni pid, que el diff nombre
la línea que cambió y que aprobar deje la nueva como aprobada.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qa.nvda import transcripcion


def datos(nombre="Categorías", pid=10, hwnd=1, hora=1.0, ms=120):
    return {
        "ventana": "preferencias",
        "pid": pid,
        "primero": {},
        "pasos": [
            {
                "tecla": "tab",
                "fase": "ida",
                "habla": [{"tipo": "habla", "texto": "Categorías",
                           "hora": hora}],
                "foco": {
                    "nombre": nombre,
                    "rol_nombre": "LIST",
                    "estados": ["focusable", "focused"],
                    "valor": "General",
                    "atajo": "Alt+C",
                    "hwnd": hwnd,
                    "pid": pid,
                },
                "agotado": False,
                "ms_habla": ms,
            },
        ],
    }


class TestFormato(unittest.TestCase):

    def test_la_linea_lleva_tecla_fase_habla_y_los_datos_del_foco(self):
        texto = transcripcion.texto(datos())
        self.assertIn("tab", texto)
        self.assertIn("ida", texto)
        self.assertIn("Categorías", texto)
        self.assertIn("LIST", texto)
        self.assertNotIn("focused", texto)
        self.assertIn("General", texto)
        self.assertIn("Alt+C", texto)

    def test_un_paso_sin_sonidos_ni_espera_escribe_la_linea_de_siempre(self):
        self.assertEqual(
            transcripcion.texto(datos()),
            "tecla=tab fase=ida dijo='Categorías' foco={nombre='Categorías', "
            "rol='LIST', estados=['focusable'], valor='General', "
            "atajo='Alt+C'}\n")

    def test_la_linea_lleva_la_espera_y_los_sonidos_al_final(self):
        caso = datos()
        caso["pasos"][0]["espera"] = "el historial está vacío"
        caso["pasos"][0]["oida"] = True
        caso["pasos"][0]["sonidos"] = ["listo", "aviso"]
        self.assertTrue(transcripcion.texto(caso).rstrip().endswith(
            " espera='el historial está vacío' oída=True "
            "sonó=['listo', 'aviso']"))

    def test_sin_sonidos_no_aparece_la_parte_de_sonidos(self):
        caso = datos()
        caso["pasos"][0]["espera"] = "listo"
        caso["pasos"][0]["oida"] = False
        self.assertNotIn("sonó", transcripcion.texto(caso))

    def test_dos_recorridos_iguales_salvo_horas_hwnd_y_pid_dan_el_mismo_texto(
            self):
        uno = datos(pid=10, hwnd=1, hora=1.0, ms=120)
        otro = datos(pid=99, hwnd=77, hora=8.5, ms=950)
        self.assertEqual(transcripcion.texto(uno), transcripcion.texto(otro))
        self.assertNotIn("77", transcripcion.texto(otro))
        self.assertNotIn("99", transcripcion.texto(otro))

    def test_rutas_temporales_distintas_dan_el_mismo_texto(self):
        corto = datos()
        ruta_corta = (r"C:\Users\MIGUEL~1\AppData\Local\Temp"
                      r"\tmpf0wi2qp_\datos\musica")
        corto["pasos"][0]["habla"] = [{"texto": f"Carpeta de música {ruta_corta}"}]
        corto["pasos"][0]["foco"]["valor"] = ruta_corta
        largo = datos()
        ruta_larga = (r"C:\Users\Miguelito\AppData\Local\Temp"
                      r"\tmps5qmma2l\datos\musica")
        largo["pasos"][0]["habla"] = [{"texto": f"Carpeta de música {ruta_larga}"}]
        largo["pasos"][0]["foco"]["valor"] = ruta_larga
        texto = transcripcion.texto(corto)
        self.assertEqual(texto, transcripcion.texto(largo))
        self.assertIn(r"<temporal>\\datos\\musica", texto)
        self.assertNotIn("tmpf0wi2qp_", texto)
        self.assertNotIn("MIGUEL~1", texto)
        self.assertNotIn("Miguelito", texto)

    def test_focused_no_cambia_la_linea_porque_el_foco_ya_esta_dicho(self):
        con_foco = datos()
        con_foco["pasos"][0]["foco"]["estados"] = ["FOCUSABLE", "FOCUSED"]
        sin_foco = datos()
        sin_foco["pasos"][0]["foco"]["estados"] = ["FOCUSABLE"]
        self.assertEqual(transcripcion.texto(con_foco),
                         transcripcion.texto(sin_foco))
        self.assertNotIn("FOCUSED", transcripcion.texto(con_foco))

    def test_el_nombre_del_foco_repetido_al_final_se_escribe_una_vez(self):
        simple = datos("No hay palabras.")
        simple["pasos"][0]["habla"] = [{"texto": "No hay palabras."}]
        doble = datos("No hay palabras.")
        doble["pasos"][0]["habla"] = [
            {"texto": "No hay palabras. No hay palabras."}]
        self.assertEqual(transcripcion.texto(doble),
                         transcripcion.texto(simple))

    def test_otra_repeticion_que_no_es_el_nombre_del_foco_no_se_toca(self):
        caso = datos("Lista")
        caso["pasos"][0]["habla"] = [
            {"texto": "No hay palabras. No hay palabras."}]
        self.assertIn("dijo='No hay palabras. No hay palabras.'",
                      transcripcion.texto(caso))

    def test_el_nombre_con_la_posicion_repetido_al_final_se_escribe_una_vez(
            self):
        simple = datos("Comandos")
        simple["pasos"][0]["habla"] = [
            {"texto": "Páginas de interacción lista Comandos 2 de 8"}]
        doble = datos("Comandos")
        doble["pasos"][0]["habla"] = [
            {"texto": "Páginas de interacción lista Comandos 2 de 8 "
                      "Comandos 2 de 8"}]
        self.assertEqual(transcripcion.texto(doble),
                         transcripcion.texto(simple))

    def test_dos_entradas_distintas_al_final_no_se_tocan(self):
        caso = datos("Comandos")
        caso["pasos"][0]["habla"] = [
            {"texto": "Comandos 2 de 8 Encuestas 3 de 8"}]
        self.assertIn("dijo='Comandos 2 de 8 Encuestas 3 de 8'",
                      transcripcion.texto(caso))


class TestFasePagina(unittest.TestCase):

    def _llegada(self, tecla, nombre, habla):
        return {
            "tecla": tecla,
            "fase": "pagina",
            "habla": [{"texto": habla}],
            "foco": {"nombre": nombre, "rol_nombre": "LIST",
                     "estados": ["focusable"]},
        }

    def _caso(self, llegada=None):
        caso = datos()
        ida = caso["pasos"][0]
        pasos = [ida, dict(ida, fase="vuelta")]
        if llegada is not None:
            pasos.insert(0, llegada)
        caso["pasos"] = pasos
        return caso

    def test_los_pasos_de_pagina_no_se_escriben(self):
        caso = self._caso(
            self._llegada("down", "Páginas", "Páginas de interacción"))
        texto = transcripcion.texto(caso)
        self.assertEqual(len(texto.splitlines()), 2)
        self.assertNotIn("fase=pagina", texto)
        self.assertIn("fase=ida", texto)
        self.assertIn("fase=vuelta", texto)

    def test_dos_llegadas_distintas_dan_el_mismo_texto(self):
        interaccion = self._caso(
            self._llegada("down", "Páginas", "Páginas de interacción"))
        preferencias = self._caso(
            self._llegada("up", "Menú", "Categorías de preferencias"))
        self.assertEqual(transcripcion.texto(interaccion),
                         transcripcion.texto(preferencias))

    def test_la_transcripcion_no_quita_los_pasos_de_los_datos(self):
        llegada = self._llegada("down", "Páginas", "Páginas de interacción")
        caso = self._caso(llegada)
        transcripcion.texto(caso)
        self.assertIn(llegada, caso["pasos"])


class TestValorVariable(unittest.TestCase):

    def _estado(self, nombre, dicho, valor, rol="EDITABLETEXT"):
        caso = datos(nombre)
        caso["pasos"][0]["habla"] = [{"texto": dicho}]
        caso["pasos"][0]["foco"].update({
            "rol_nombre": rol, "atajo": "Alt+E", "valor": valor})
        return caso

    def test_valores_distintos_del_control_variable_comparan_iguales(self):
        casa = self._estado(
            "Estado", "Estado edición Alt+ e Revisa antes de transmitir",
            "Revisa antes de transmitir")
        oficina = self._estado(
            "Estado", "Estado edición Alt+ e Elige a dónde transmitir",
            "Elige a dónde transmitir")
        texto_casa = transcripcion.texto(casa, ["Estado"])
        texto_oficina = transcripcion.texto(oficina, ["Estado"])
        self.assertEqual(texto_casa, texto_oficina)
        self.assertEqual(
            transcripcion.diferencia(texto_casa, texto_oficina), "")
        self.assertIn("dijo='Estado edición Alt+ e'", texto_casa)
        self.assertNotIn("Revisa antes", texto_casa)
        self.assertNotIn("Elige a dónde", texto_casa)
        self.assertIn("valor=''", texto_casa)

    def test_nombre_o_rol_distinto_del_control_variable_no_comparan_iguales(
            self):
        controles = ["Estado", "Otro estado"]
        base = self._estado(
            "Estado", "Estado edición Alt+ e Revisa antes", "Revisa antes")
        otro_nombre = self._estado(
            "Otro estado", "Otro estado edición Alt+ e Revisa antes",
            "Revisa antes")
        otro_rol = self._estado(
            "Estado", "Estado edición Alt+ e Revisa antes", "Revisa antes",
            rol="EDIT")
        self.assertNotEqual(transcripcion.texto(base, controles),
                            transcripcion.texto(otro_nombre, controles))
        self.assertNotEqual(transcripcion.texto(base, controles),
                            transcripcion.texto(otro_rol, controles))


class TestCarpetaApp(unittest.TestCase):

    def _caso(self, ruta):
        caso = datos()
        caso["pasos"][0]["habla"] = [{"texto": f"Carpeta de descargas {ruta}"}]
        caso["pasos"][0]["foco"]["valor"] = ruta
        return caso

    def test_la_carpeta_de_la_app_en_dicho_y_valor_va_con_marcador(self):
        carpeta = Path(r"C:\Users\Miguelito\Documents\guyrapu")
        ruta = str(carpeta).upper() + r"\Descargas"
        with mock.patch.object(transcripcion, "CARPETA_APP", carpeta,
                               create=True):
            texto = transcripcion.texto(self._caso(ruta))
        self.assertIn(r"<carpeta de la app>\\Descargas", texto)
        self.assertNotIn(r"C:\\USERS\\MIGUELITO", texto)

    def test_una_ruta_que_no_es_la_carpeta_de_la_app_queda_igual(self):
        carpeta = Path(r"C:\Users\Miguelito\Documents\guyrapu")
        ruta = r"C:\Users\Otro\Descargas"
        with mock.patch.object(transcripcion, "CARPETA_APP", carpeta,
                               create=True):
            texto = transcripcion.texto(self._caso(ruta))
        self.assertIn(r"C:\\Users\\Otro\\Descargas", texto)
        self.assertNotIn("<carpeta de la app>", texto)


class TestComparacion(unittest.TestCase):

    def test_un_nombre_distinto_da_un_diff_con_su_linea(self):
        viejo = transcripcion.texto(datos("Categorías"))
        nuevo = transcripcion.texto(datos("Categorías de preferencias"))
        diferencia = transcripcion.diferencia(viejo, nuevo)
        self.assertIn("Categorías de preferencias", diferencia)
        self.assertTrue(any(linea.startswith("+")
                            for linea in diferencia.splitlines()))

    def test_aprobar_deja_la_nueva_como_aprobada(self):
        with tempfile.TemporaryDirectory() as base:
            carpeta = Path(base)
            transcripcion.escribir("preferencias", "vieja\n", carpeta)
            diferencia = transcripcion.comparar("preferencias", "nueva\n",
                                                carpeta=carpeta)
            self.assertIn("nueva", diferencia)
            self.assertEqual(
                transcripcion.leer("preferencias", carpeta), "vieja\n")
            self.assertEqual(
                transcripcion.comparar("preferencias", "nueva\n",
                                       aprobar=True, carpeta=carpeta),
                "")
            self.assertEqual(
                transcripcion.leer("preferencias", carpeta), "nueva\n")

    def test_una_distinta_deja_la_candidata_con_el_texto_exacto(self):
        with tempfile.TemporaryDirectory() as base:
            aprobadas = Path(base) / "aprobadas"
            candidatas = Path(base) / "candidatas"
            transcripcion.escribir("musica", "aprobada\n", aprobadas)
            nueva = "nueva\ncon dos líneas\n"
            with mock.patch.object(transcripcion, "CANDIDATAS", candidatas):
                diferencia = transcripcion.comparar(
                    "musica", nueva, carpeta=aprobadas)
                self.assertTrue(diferencia)
                self.assertEqual(
                    (candidatas / "musica.txt").read_text(encoding="utf-8"),
                    nueva)

    def test_la_igual_o_aprobar_no_deja_candidata(self):
        with tempfile.TemporaryDirectory() as base:
            aprobadas = Path(base) / "aprobadas"
            candidatas = Path(base) / "candidatas"
            transcripcion.escribir("musica", "aprobada\n", aprobadas)
            with mock.patch.object(transcripcion, "CANDIDATAS", candidatas):
                transcripcion.escribir("musica", "vieja candidata\n",
                                       candidatas)
                self.assertEqual(
                    transcripcion.comparar("musica", "aprobada\n",
                                           carpeta=aprobadas), "")
                self.assertFalse((candidatas / "musica.txt").exists())
                transcripcion.escribir("musica", "vieja candidata\n",
                                       candidatas)
                self.assertEqual(
                    transcripcion.comparar("musica", "nueva\n", aprobar=True,
                                           carpeta=aprobadas), "")
                self.assertFalse((candidatas / "musica.txt").exists())
                self.assertEqual(
                    transcripcion.leer("musica", aprobadas), "nueva\n")


if __name__ == "__main__":
    unittest.main()
