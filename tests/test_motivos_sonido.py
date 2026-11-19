# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Motivos del catálogo de sonidos y nombre del fin de la cola de música."""

import unittest
from pathlib import Path

from babel.messages import pofile

from guyrapu.core import eventos_sonido, motivos_sonido, sonidos_fabrica
from guyrapu.core import sonidos_ini

RAIZ = Path(__file__).resolve().parent.parent
PO_INGLES = RAIZ / "idiomas" / "en" / "LC_MESSAGES" / "guyrapu.po"

MOTIVOS = (
    "sin_texto", "llega_solo", "error", "fin_de_espera",
    "en_espera", "estado", "opcional",
)


def _problemas(motivos, claves):
    """Lo que impide que `motivos` describa el catálogo, en texto."""
    problemas = []
    por_clave = {}
    for motivo, eventos in motivos.items():
        if motivo not in MOTIVOS:
            problemas.append(f"motivo desconocido: {motivo}")
        for clave in eventos:
            if clave not in claves:
                problemas.append(f"{clave} no está en el catálogo")
            por_clave.setdefault(clave, []).append(motivo)
    for clave in claves:
        if clave not in por_clave:
            problemas.append(f"{clave} no tiene motivo")
    for clave, suyos in por_clave.items():
        if len(suyos) > 1:
            problemas.append(f"{clave} tiene más de un motivo: {suyos}")
    return problemas


class TestMotivos(unittest.TestCase):
    def test_catalogo_real_sin_problemas(self):
        self.assertEqual(
            _problemas(motivos_sonido.MOTIVOS, set(eventos_sonido.EVENTOS)),
            [])

    def test_detecta_las_cuatro_fallas(self):
        claves = {"uno", "dos", "tres", "cuatro"}
        casos = {
            "sin motivo": {"sin_texto": ("uno", "dos")},
            "más de uno": {"sin_texto": tuple(claves), "error": ("uno",)},
            "motivo desconocido": {"sin_texto": tuple(claves), "otro": ()},
            "clave ajena": {"sin_texto": tuple(claves) + ("ajena",)},
        }
        for caso, motivos in casos.items():
            with self.subTest(caso=caso):
                self.assertNotEqual(_problemas(motivos, claves), [])


class TestEventosDeLoQueSaleEnElVideo(unittest.TestCase):
    NUEVOS = {
        "video_pausa": ("Cola del vídeo en pausa", "pausa", "desactivado"),
        "video_reanudar": ("Cola del vídeo reanudada", "reanudar",
                           "activado"),
        "video_silenciar": ("Medios silenciados", "pausa", "desactivado"),
        "video_audio": ("Medios activados", "reanudar", "activado"),
        "video_panico": ("Modo pánico activado", "reanudar", "activado"),
        "video_panico_fin": ("Modo pánico desactivado", "pausa",
                             "desactivado"),
        "mensajes_automaticos_activados": (
            "Mensajes automáticos activados", "reanudar", "activado"),
        "mensajes_automaticos_desactivados": (
            "Mensajes automáticos desactivados", "pausa", "desactivado"),
    }

    def test_cada_uno_tiene_su_nombre_su_sonido_y_su_motivo(self):
        catalogo = {evento.clave: evento
                    for evento in eventos_sonido.CATALOGO}
        for clave, (nombre, sonido, familia) in self.NUEVOS.items():
            with self.subTest(clave=clave):
                self.assertIn(clave, catalogo)
                self.assertEqual(eventos_sonido.NOMBRES[clave], nombre)
                self.assertEqual(eventos_sonido.SONIDOS[clave], sonido)
                self.assertEqual(catalogo[clave].familia, familia)
                self.assertEqual(
                    motivos_sonido.MOTIVO_POR_CLAVE[clave], "estado")


class TestEventosDeComandosEnPausa(unittest.TestCase):
    NUEVOS = {
        "comandos_pausa": ("Comandos en pausa", "pausa", "desactivado"),
        "comandos_reanudar": ("Comandos reanudados", "reanudar", "activado"),
    }

    def test_cada_uno_tiene_su_nombre_su_sonido_y_su_motivo(self):
        catalogo = {evento.clave: evento
                    for evento in eventos_sonido.CATALOGO}
        for clave, (nombre, sonido, familia) in self.NUEVOS.items():
            with self.subTest(clave=clave):
                self.assertIn(clave, catalogo)
                self.assertEqual(eventos_sonido.NOMBRES[clave], nombre)
                self.assertEqual(eventos_sonido.SONIDOS[clave], sonido)
                self.assertEqual(catalogo[clave].familia, familia)
                self.assertEqual(
                    motivos_sonido.MOTIVO_POR_CLAVE[clave], "estado")


class TestCierreDeEncuestaPorTiempo(unittest.TestCase):
    def test_usa_el_aviso_y_llega_solo(self):
        self.assertEqual(eventos_sonido.NOMBRES["encuesta_cerrada"],
                         "Encuesta cerrada por tiempo")
        self.assertEqual(eventos_sonido.SONIDOS["encuesta_cerrada"], "aviso")
        self.assertEqual(
            motivos_sonido.MOTIVO_POR_CLAVE["encuesta_cerrada"], "llega_solo")


class TestMetaCumplidaDelDirecto(unittest.TestCase):
    def test_usa_el_aviso_y_llega_solo(self):
        self.assertEqual(eventos_sonido.NOMBRES["meta_cumplida"],
                         "Meta cumplida del directo")
        self.assertEqual(eventos_sonido.SONIDOS["meta_cumplida"], "aviso")
        self.assertEqual(
            motivos_sonido.MOTIVO_POR_CLAVE["meta_cumplida"], "llega_solo")


class TestColaDePreguntasLlena(unittest.TestCase):
    def test_usa_el_aviso_y_llega_solo(self):
        self.assertEqual(eventos_sonido.NOMBRES["preguntas_llena"],
                         "Cola de preguntas llena")
        self.assertEqual(eventos_sonido.SONIDOS["preguntas_llena"], "aviso")
        self.assertEqual(
            motivos_sonido.MOTIVO_POR_CLAVE["preguntas_llena"], "llega_solo")


class TestOpcionales(unittest.TestCase):
    def test_musica_tema_y_musica_fin_son_opcionales(self):
        for clave in ("musica_tema", "musica_fin"):
            self.assertEqual(motivos_sonido.MOTIVO_POR_CLAVE[clave], "opcional")

    def test_ningun_otro_evento_es_opcional(self):
        self.assertEqual(
            {clave for clave, motivo in motivos_sonido.MOTIVO_POR_CLAVE.items()
             if motivo == "opcional"},
            {"musica_tema", "musica_fin"})


class TestOpcionalesCallados(unittest.TestCase):
    """Las dos plantillas de sounds.ini callan los sonidos opcionales."""

    def _plantillas(self):
        return {
            "sounds.ini de la raíz": (RAIZ / "sounds.ini").read_text(
                encoding="utf-8"),
            "texto de respaldo": sonidos_fabrica.TEXTO_FABRICA,
        }

    def test_musica_tema_y_musica_fin_vienen_callados(self):
        for nombre, texto in self._plantillas().items():
            callados = sonidos_ini.silenciados(texto)
            for clave in ("musica_tema", "musica_fin"):
                with self.subTest(plantilla=nombre, clave=clave):
                    self.assertIn(clave, callados)

    def test_todo_opcional_viene_callado(self):
        for nombre, texto in self._plantillas().items():
            callados = sonidos_ini.silenciados(texto)
            for clave in motivos_sonido.MOTIVOS["opcional"]:
                with self.subTest(plantilla=nombre, clave=clave):
                    self.assertIn(clave, callados)


class TestNombre(unittest.TestCase):
    def test_musica_fin_se_llama_fin_de_la_cola_de_musica(self):
        self.assertEqual(eventos_sonido.NOMBRES["musica_fin"],
                         "Fin de la cola de música")

    def test_en_ingles_se_traduce(self):
        with PO_INGLES.open("rb") as archivo:
            catalogo = pofile.read_po(archivo)
        self.assertIsNone(catalogo.get("Canción terminada"))
        self.assertEqual(catalogo.get("Fin de la cola de música").string,
                         "End of the music queue")


if __name__ == "__main__":
    unittest.main()
