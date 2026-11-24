# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué pedido de música del chat se agrega a la cola.

Puro: sin interfaz, con la búsqueda y la expansión de enlaces dobladas.
"""

import os
import unittest

from guyrapu.core import idioma
from guyrapu.downloads import busqueda_youtube
from guyrapu.interaction import pedido_musica
from guyrapu.music import enlaces
from guyrapu.music.modelo import Tema

ENLACE = "https://www.youtube.com/watch?v=abc123"
OTRO_ENLACE = "https://www.youtube.com/watch?v=def456"
LISTA = "https://www.youtube.com/playlist?list=PLabc123"


class BusquedaDoble:
    """Devuelve los resultados dados y anota cómo la pidieron."""

    def __init__(self, resultados=(), fallar=False):
        self.resultados = list(resultados)
        self.fallar = fallar
        self.llamadas = []

    def __call__(self, texto, filtros, inicio, cantidad):
        if self.fallar:
            raise AssertionError("un enlace no se busca como texto")
        self.llamadas.append((texto, filtros, inicio, cantidad))
        return busqueda_youtube.RespuestaBusqueda(self.resultados, "", False)


class ExpansionDoble:
    """Devuelve los temas del enlace y anota cuál se abrió."""

    def __init__(self, temas=(), fallar=False):
        self.temas = tuple(temas)
        self.fallar = fallar
        self.llamadas = []

    def __call__(self, url):
        if self.fallar:
            raise AssertionError("un texto no se abre como enlace")
        self.llamadas.append(url)
        return self.temas


class InfoDoble:
    """Devuelve duración y estado del vídeo con una sola consulta."""

    def __init__(self, duracion=200, en_directo=False, programado=False,
                 fallar=False):
        self.duracion = duracion
        self.en_directo = en_directo
        self.programado = programado
        self.fallar = fallar
        self.llamadas = []

    def __call__(self, url):
        if self.fallar:
            raise AssertionError("la información del vídeo no se necesitaba")
        self.llamadas.append(url)
        return enlaces.InfoVideo(self.duracion, self.en_directo,
                                  self.programado)


def _video(**cambios):
    datos = dict(
        id="abc123", url=ENLACE, titulo="Tema pedido", canal="Canal",
        duracion=200, vistas=None, marca_tiempo=None, descripcion="",
        tipo="video", en_directo=False, programado=False)
    datos.update(cambios)
    return busqueda_youtube.Resultado(**datos)


def _tema(url=ENLACE, titulo="Tema del enlace", duracion_ms=200000):
    return Tema(origen=url, titulo=titulo, duracion_ms=duracion_ms)


class TestPedidoMusica(unittest.TestCase):

    def setUp(self):
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def _resolver(self, texto, resultados=(), temas=(), buscar_falla=False,
                  expandir_falla=False, info_duracion=200,
                  info_en_directo=False, info_programado=False,
                  info_falla=True):
        busqueda = BusquedaDoble(resultados, buscar_falla)
        expansion = ExpansionDoble(temas, expandir_falla)
        info = InfoDoble(info_duracion, info_en_directo, info_programado,
                         info_falla)
        pedido = pedido_musica.resolver(texto, busqueda, expansion, info=info)
        return pedido, busqueda, expansion, info

    def test_texto_vacio_no_busca_y_se_rechaza(self):
        pedido, busqueda, expansion, _ = self._resolver(
            "   ", buscar_falla=True, expandir_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "falta el nombre o el enlace del tema")
        self.assertEqual(busqueda.llamadas, [])
        self.assertEqual(expansion.llamadas, [])

    def test_busqueda_sin_resultados_se_rechaza(self):
        pedido, busqueda, _, _ = self._resolver("algo", expandir_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "la búsqueda no dio resultados")
        self.assertEqual(busqueda.llamadas[0][0], "algo")
        self.assertEqual(busqueda.llamadas[0][1].tipo, "videos")
        self.assertEqual(busqueda.llamadas[0][2:], (1, 1))

    def test_video_en_directo_se_rechaza(self):
        pedido, _, _, _ = self._resolver(
            "algo", [_video(en_directo=True)], expandir_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el vídeo está en directo")

    def test_video_programado_se_rechaza(self):
        pedido, _, _, _ = self._resolver(
            "algo", [_video(programado=True)], expandir_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el vídeo está programado")

    def test_busqueda_sin_duracion_y_info_en_directo_se_rechaza(self):
        pedido, busqueda, _, info = self._resolver(
            "lofi hip hop radio", [_video(duracion=None, url=OTRO_ENLACE)],
            expandir_falla=True, info_en_directo=True, info_falla=False)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el vídeo está en directo")
        self.assertEqual(busqueda.llamadas[0][0], "lofi hip hop radio")
        self.assertEqual(info.llamadas, [OTRO_ENLACE])

    def test_busqueda_sin_duracion_y_info_con_200_se_acepta(self):
        pedido, _, _, info = self._resolver(
            "lofi hip hop radio", [_video(duracion=None, url=OTRO_ENLACE)],
            expandir_falla=True, info_falla=False)
        self.assertEqual(pedido.motivo, "")
        self.assertEqual(pedido.tema.url, OTRO_ENLACE)
        self.assertEqual(pedido.tema.duracion, 200)
        self.assertEqual(info.llamadas, [OTRO_ENLACE])

    def test_video_de_601_segundos_se_rechaza(self):
        pedido, _, _, _ = self._resolver(
            "algo", [_video(duracion=601)], expandir_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "dura más de 10 minutos")

    def test_enlace_de_lista_se_rechaza_sin_buscar(self):
        pedido, busqueda, expansion, _ = self._resolver(
            LISTA, temas=[_tema(), _tema(url=OTRO_ENLACE)],
            buscar_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el enlace es de una lista de reproducción")
        self.assertEqual(busqueda.llamadas, [])
        self.assertEqual(expansion.llamadas, [LISTA])

    def test_un_enlace_con_dos_temas_se_rechaza(self):
        pedido, busqueda, expansion, _ = self._resolver(
            ENLACE, temas=[_tema(), _tema(url=OTRO_ENLACE)],
            buscar_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el enlace es de una lista de reproducción")
        self.assertEqual(busqueda.llamadas, [])
        self.assertEqual(expansion.llamadas, [ENLACE])

    def test_video_de_600_segundos_se_acepta(self):
        pedido, _, _, _ = self._resolver(
            "algo", [_video(duracion=600, titulo="Justo diez minutos")],
            expandir_falla=True)
        self.assertEqual(pedido.motivo, "")
        self.assertEqual(pedido.tema.url, ENLACE)
        self.assertEqual(pedido.tema.titulo, "Justo diez minutos")
        self.assertEqual(pedido.tema.duracion, 600)

    def test_enlace_de_un_video_usa_ese_video(self):
        pedido, busqueda, expansion, info = self._resolver(
            ENLACE,
            temas=[_tema(url=OTRO_ENLACE, titulo="Tema canónico",
                         duracion_ms=200000)],
            buscar_falla=True, info_falla=False)
        self.assertEqual(expansion.llamadas, [ENLACE])
        self.assertEqual(busqueda.llamadas, [])
        self.assertEqual(info.llamadas, [OTRO_ENLACE])
        self.assertEqual(pedido.motivo, "")
        self.assertEqual(pedido.tema.url, OTRO_ENLACE)
        self.assertEqual(pedido.tema.titulo, "Tema canónico")
        self.assertEqual(pedido.tema.duracion, 200)

    def test_enlace_sin_temas_se_rechaza(self):
        pedido, busqueda, expansion, info = self._resolver(
            ENLACE, buscar_falla=True)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "no se pudo abrir el enlace")
        self.assertEqual(busqueda.llamadas, [])
        self.assertEqual(expansion.llamadas, [ENLACE])
        self.assertEqual(info.llamadas, [])

    def test_enlace_en_directo_se_rechaza(self):
        pedido, _, _, info = self._resolver(
            ENLACE, temas=[_tema()], buscar_falla=True,
            info_en_directo=True, info_falla=False)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el vídeo está en directo")
        self.assertEqual(info.llamadas, [ENLACE])

    def test_enlace_programado_se_rechaza(self):
        pedido, _, _, info = self._resolver(
            ENLACE, temas=[_tema()], buscar_falla=True,
            info_programado=True, info_falla=False)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "el vídeo está programado")
        self.assertEqual(info.llamadas, [ENLACE])

    def test_enlace_sin_duracion_se_rechaza(self):
        pedido, _, _, info = self._resolver(
            ENLACE, temas=[_tema(duracion_ms=0)], buscar_falla=True,
            info_duracion=0, info_falla=False)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo,
                         "no se pudo obtener la duración del vídeo")
        self.assertEqual(info.llamadas, [ENLACE])

    def test_enlace_sin_duracion_en_el_tema_la_toma_de_la_info(self):
        pedido, _, _, info = self._resolver(
            ENLACE,
            temas=[_tema(url=OTRO_ENLACE, titulo="Tema sin duración",
                         duracion_ms=0)],
            buscar_falla=True, info_falla=False)
        self.assertEqual(info.llamadas, [OTRO_ENLACE])
        self.assertEqual(pedido.motivo, "")
        self.assertEqual(pedido.tema.url, OTRO_ENLACE)
        self.assertEqual(pedido.tema.duracion, 200)

    def test_enlace_con_duracion_larga_se_rechaza(self):
        pedido, _, _, info = self._resolver(
            ENLACE, temas=[_tema(duracion_ms=0)], buscar_falla=True,
            info_duracion=700, info_falla=False)
        self.assertIsNone(pedido.tema)
        self.assertEqual(pedido.motivo, "dura más de 10 minutos")
        self.assertEqual(info.llamadas, [ENLACE])

    def test_toma_el_primer_resultado_de_tipo_video(self):
        pedido, _, _, _ = self._resolver(
            "algo", [_video(tipo="canal", titulo="Un canal"),
                     _video(url=OTRO_ENLACE, titulo="El tema")],
            expandir_falla=True)
        self.assertEqual(pedido.tema.titulo, "El tema")
        self.assertEqual(pedido.tema.url, OTRO_ENLACE)


@unittest.skipUnless(
    os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1",
    "prueba real de la frontera: GUYRAPU_PRUEBAS_CON_RED=1")
class TestBusquedaReal(unittest.TestCase):
    """Busca en YouTube de verdad, solo con la red habilitada."""

    def test_un_texto_conocido_devuelve_un_video_con_duracion(self):
        respuesta = busqueda_youtube.buscar(
            "guyrapu musica prueba", busqueda_youtube.Filtros(tipo="videos"),
            1, 1)
        videos = [item for item in respuesta.resultados if item.tipo == "video"]
        self.assertTrue(videos)
        self.assertIsInstance(videos[0].duracion, int)

    def test_un_enlace_conocido_da_un_tema_con_duracion(self):
        pedido = pedido_musica.resolver(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            busqueda_youtube.buscar)
        self.assertEqual(pedido.motivo, "")
        self.assertIsNotNone(pedido.tema)
        self.assertGreater(pedido.tema.duracion, 0)


if __name__ == "__main__":
    unittest.main()
