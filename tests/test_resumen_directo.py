# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del resumen de un directo terminado.

Es lógica pura salvo `datos_del_perfil`, que habla con un cliente falso de
OBS: no abre ventanas ni sale a la red.
"""

import unittest

from guyrapu.obs import resumen_directo


def estado(perdidos=0, totales=0, activa=True):
    return {"outputActive": activa, "outputSkippedFrames": perdidos,
            "outputTotalFrames": totales}


def estadisticas(perdidos=0, totales=0, dibujados=0, dibujados_totales=0):
    return {"outputSkippedFrames": perdidos, "outputTotalFrames": totales,
            "renderSkippedFrames": dibujados,
            "renderTotalFrames": dibujados_totales}


def red(n):
    return ("Se perdió el {} por ciento de los fotogramas por la red."
            .format(n))


def codificar(n):
    return ("Se perdió el {} por ciento de los fotogramas al codificar."
            .format(n))


def dibujar(n):
    return ("Se perdió el {} por ciento de los fotogramas al dibujar la "
            "escena.".format(n))


REC_RED = ("Para el próximo directo, baja la velocidad de bits de vídeo del perfil "
           "Casa o usa una conexión por cable.")
REC_GRAFICA = ("Para el próximo directo, usa el codificador de la gráfica "
               "en el perfil Casa.")
REC_RESOLUCION = ("Para el próximo directo, baja la resolución o los "
                  "fotogramas por segundo del perfil Casa.")
REC_DIBUJAR = ("Para el próximo directo, baja los fotogramas por segundo "
               "del perfil Casa o cierra programas que usen la gráfica.")


class ResumirTest(unittest.TestCase):

    def resumir(self, inicial=None, final=None, est_inicial=None,
                est_final=None, perfil="Casa", codificador="", disponibles=()):
        return resumen_directo.resumir(
            inicial if inicial is not None else estado(),
            final if final is not None else estado(),
            est_inicial, est_final, perfil, codificador, disponibles)

    def test_red_por_debajo_del_uno_por_ciento(self):
        texto = self.resumir(final=estado(5, 1000))
        self.assertEqual(
            "Se perdió menos del 1 por ciento de los fotogramas.", texto)

    def test_red_desde_el_uno_por_ciento(self):
        self.assertEqual(red(1) + " " + REC_RED,
                         self.resumir(final=estado(10, 1000)))

    def test_codificar_por_debajo_del_uno_por_ciento(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(5, 1000))
        self.assertEqual(
            "Se perdió menos del 1 por ciento de los fotogramas.", texto)

    def test_codificar_desde_el_uno_por_ciento(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(10, 1000))
        self.assertEqual(codificar(1) + " " + REC_RESOLUCION, texto)

    def test_dibujar_por_debajo_del_uno_por_ciento(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(0, 1000, 5, 1000))
        self.assertEqual(
            "Se perdió menos del 1 por ciento de los fotogramas.", texto)

    def test_dibujar_desde_el_uno_por_ciento(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(0, 1000, 10, 1000))
        self.assertEqual(dibujar(1) + " " + REC_DIBUJAR, texto)

    def test_codificar_y_dibujar_sin_red_dicen_de_los_fotogramas(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(290, 1000, 20, 1000))
        self.assertEqual(
            "Se perdió el 29 por ciento de los fotogramas al codificar y "
            "el 2 por ciento al dibujar la escena. " + REC_RESOLUCION, texto)

    def test_solo_dibujar_dice_de_los_fotogramas(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(0, 1000, 20, 1000))
        self.assertEqual(
            "Se perdió el 2 por ciento de los fotogramas al dibujar la "
            "escena. " + REC_DIBUJAR, texto)

    def test_las_tres_causas_juntas(self):
        texto = self.resumir(final=estado(10, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(20, 1000, 30, 1000))
        self.assertEqual(
            "Se perdió el 1 por ciento de los fotogramas por la red, "
            "el 2 por ciento al codificar y el 3 por ciento al dibujar "
            "la escena. " + REC_DIBUJAR, texto)

    def test_menos_de_treinta_fotogramas_no_dice_nada(self):
        texto = self.resumir(final=estado(29, 29),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(29, 29, 29, 29))
        self.assertEqual("", texto)

    def test_contador_de_red_que_baja_cuenta_como_cero(self):
        texto = self.resumir(inicial=estado(100, 1000),
                             final=estado(50, 2000))
        self.assertEqual(
            "Se perdió menos del 1 por ciento de los fotogramas.", texto)

    def test_contador_de_estadisticas_que_baja_cuenta_como_cero(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(500, 1000),
                             est_final=estadisticas(100, 2000))
        self.assertEqual(
            "Se perdió menos del 1 por ciento de los fotogramas.", texto)

    def test_sin_estadisticas_solo_la_red(self):
        self.assertEqual(red(10) + " " + REC_RED,
                         self.resumir(final=estado(100, 1000)))

    def test_recomendacion_solo_para_la_causa_mas_alta(self):
        texto = self.resumir(final=estado(10, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(20, 1000, 30, 1000))
        self.assertTrue(texto.endswith(REC_DIBUJAR))
        self.assertNotIn(REC_RED, texto)
        self.assertNotIn(REC_RESOLUCION, texto)

    def test_empate_gana_red(self):
        texto = self.resumir(final=estado(10, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(10, 1000))
        self.assertEqual(
            "Se perdió el 1 por ciento de los fotogramas por la red y "
            "el 1 por ciento al codificar. " + REC_RED, texto)

    def test_empate_sin_red_gana_codificar(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(10, 1000, 10, 1000))
        self.assertEqual(
            "Se perdió el 1 por ciento de los fotogramas al codificar y "
            "el 1 por ciento al dibujar la escena. " + REC_RESOLUCION, texto)

    def test_sin_perfil_la_recomendacion_dice_de_obs(self):
        texto = self.resumir(final=estado(10, 1000), perfil="")
        self.assertEqual(
            red(1) + " Para el próximo directo, baja la velocidad de bits de "
            "vídeo del perfil de OBS o usa una conexión por cable.", texto)

    def test_p5_x264_con_grafica_recomienda_la_grafica(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(100, 1000),
                             codificador="x264",
                             disponibles=("qsv", "x264"))
        self.assertEqual(codificar(10) + " " + REC_GRAFICA, texto)

    def test_p5_x264_sin_grafica_recomienda_bajar_resolucion(self):
        texto = self.resumir(final=estado(0, 1000),
                             est_inicial=estadisticas(),
                             est_final=estadisticas(100, 1000),
                             codificador="x264",
                             disponibles=("x264",))
        self.assertEqual(codificar(10) + " " + REC_RESOLUCION, texto)


class ClientePerfilFalso:
    def __init__(self, modo="Simple", codificador="obs_qsv11_v2",
                 perfil="Casa", fallo=None):
        self.modo = modo
        self.codificador = codificador
        self.perfil = perfil
        self.fallo = fallo
        self.pedidos = []

    def pedir(self, tipo, datos=None, parada=None):
        self.pedidos.append((tipo, datos))
        if self.fallo is not None:
            raise self.fallo
        if tipo == "GetProfileList":
            return {"responseData": {"currentProfileName": self.perfil}}
        if tipo == "GetProfileParameter":
            nombre = (datos or {}).get("parameterName")
            if nombre == "Mode":
                return {"responseData": {"parameterValue": self.modo}}
            return {"responseData": {
                "parameterValue": self.codificador}}
        return {"responseData": {}}


class DatosDelPerfilTest(unittest.TestCase):

    def test_sencillo_da_perfil_y_codificador_traducido(self):
        cliente = ClientePerfilFalso(codificador="obs_qsv11_v2")
        self.assertEqual(("Casa", "qsv"),
                         resumen_directo.datos_del_perfil(cliente, None))

    def test_avanzado_da_el_perfil_y_codificador_desconocido(self):
        cliente = ClientePerfilFalso(modo="Advanced")
        self.assertEqual(("Casa", ""),
                         resumen_directo.datos_del_perfil(cliente, None))

    def test_error_da_perfil_vacio_y_codificador_desconocido(self):
        cliente = ClientePerfilFalso(fallo=RuntimeError("boom"))
        self.assertEqual(("", ""),
                         resumen_directo.datos_del_perfil(cliente, None))


if __name__ == "__main__":
    unittest.main()
