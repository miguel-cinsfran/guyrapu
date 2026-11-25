# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lo que el registro detallado cuenta del directo y de la capa de vídeo."""

import unittest
from unittest import mock

from guyrapu.interaction import rastro_en_vivo


class TestLineasDelDirecto(unittest.TestCase):

    def test_el_evento_dice_tipo_cantidad_y_motivo(self):
        self.assertEqual(
            rastro_en_vivo.evento("superchat", 2, ""),
            'ALERTA_EVENTO tipo=superchat alertas=2 motivo=""')

    def test_un_evento_sin_alerta_dice_el_motivo_calculado(self):
        linea = rastro_en_vivo.evento(
            "text", 0, "La alerta Risa está en espera 3 segundos")
        self.assertEqual(
            linea, 'ALERTA_EVENTO tipo=text alertas=0 '
                   'motivo="La alerta Risa está en espera 3 segundos"')

    def test_un_evento_que_no_es_chat_siempre_deja_linea(self):
        self.assertEqual(
            rastro_en_vivo.evento("like", 0, ""),
            'ALERTA_EVENTO tipo=like alertas=0 motivo=""')

    def test_un_mensaje_de_chat_sin_alerta_ni_motivo_no_deja_linea(self):
        self.assertEqual(rastro_en_vivo.evento("text", 0, "",
                                               mensaje=True), "")

    def test_un_mensaje_de_chat_con_alerta_o_motivo_si_deja_linea(self):
        self.assertIn("ALERTA_EVENTO", rastro_en_vivo.evento(
            "text", 1, "", mensaje=True))
        self.assertIn('motivo="Espera"', rastro_en_vivo.evento(
            "text", 0, "Espera", mensaje=True))

    def test_el_evento_no_lleva_el_autor_ni_el_texto_del_cableado(self):
        linea = rastro_en_vivo.evento("superchat", 1, "")
        self.assertNotIn("Ana", linea)
        self.assertNotIn("mensaje privado de Ana", linea)


class TestLineasDeAlertasYMetas(unittest.TestCase):

    def test_la_alerta_dice_nombre_evento_y_destino(self):
        self.assertEqual(
            rastro_en_vivo.alerta("Risa", "superchat", True, False),
            'ALERTA nombre="Risa" evento=superchat destino=video')

    def test_la_alerta_que_va_a_los_dos_y_la_que_no_va_a_ninguno(self):
        self.assertIn("destino=ambos", rastro_en_vivo.alerta(
            "Risa", "like", True, True))
        self.assertIn("destino=ninguno", rastro_en_vivo.alerta(
            "Risa", "like", False, False))

    def test_la_alerta_sin_tarjeta_ni_medio_lo_dice(self):
        self.assertEqual(
            rastro_en_vivo.alerta("Risa", "like", False, False, True),
            'ALERTA nombre="Risa" evento=like destino=ninguno '
            'sin_tarjeta_medio=si')

    def test_un_nombre_con_comillas_se_escribe_escapado(self):
        self.assertEqual(
            rastro_en_vivo.alerta('Risa "grande"', "like", True, False),
            'ALERTA nombre="Risa \\"grande\\"" evento=like destino=video')

    def test_la_meta_dice_nombre_anterior_nuevo_y_objetivo(self):
        self.assertEqual(
            rastro_en_vivo.meta("Risa", 2, 3, 5),
            'META nombre="Risa" anterior=2 nuevo=3 objetivo=5')

    def test_la_meta_cumplida_dice_el_nombre(self):
        self.assertEqual(
            rastro_en_vivo.meta_cumplida("Risa"),
            'META_CUMPLIDA nombre="Risa"')

    def test_la_alerta_no_lleva_el_autor_ni_el_texto_del_cableado(self):
        linea = rastro_en_vivo.alerta("Risa", "superchat", True, False)
        self.assertNotIn("Ana", linea)
        self.assertNotIn("mensaje privado de Ana", linea)


class TestLineasDeComandos(unittest.TestCase):

    def test_el_comando_que_respondio_dice_nombre_y_destino(self):
        self.assertEqual(
            rastro_en_vivo.comando("discord", al_video=True),
            'COMANDO nombre="discord" respondio=si destino=video')
        self.assertIn("destino=ambos", rastro_en_vivo.comando(
            "discord", al_video=True, al_chat=True))
        self.assertIn("destino=chat", rastro_en_vivo.comando(
            "discord", al_chat=True))
        self.assertIn("destino=ninguno", rastro_en_vivo.comando("discord"))

    def test_el_comando_que_no_respondio_dice_el_motivo(self):
        self.assertEqual(
            rastro_en_vivo.comando(
                "hola", "el comando hola está en espera, faltan 4 segundos."),
            'COMANDO nombre="hola" respondio=no '
            'motivo="el comando hola está en espera, faltan 4 segundos."')

    def test_un_nombre_y_un_motivo_con_comillas_se_escriben_escapados(self):
        linea = rastro_en_vivo.comando('risa "grande"', 'dice "espera"')
        self.assertIn('nombre="risa \\"grande\\""', linea)
        self.assertIn('motivo="dice \\"espera\\""', linea)

    def test_el_pedido_aceptado_dice_donde_entra_en_la_cola(self):
        for donde in ("final", "continuacion", "ahora"):
            with self.subTest(donde=donde):
                self.assertEqual(
                    rastro_en_vivo.pedido_musica(True, destino=donde),
                    f'PEDIDO_MUSICA aceptado=si destino={donde}')

    def test_el_pedido_rechazado_dice_el_motivo(self):
        self.assertEqual(
            rastro_en_vivo.pedido_musica(
                False, motivo="la búsqueda no dio resultados"),
            'PEDIDO_MUSICA aceptado=no '
            'motivo="la búsqueda no dio resultados"')

    def test_ninguna_linea_lleva_el_autor_el_texto_la_busqueda_ni_el_titulo(self):
        lineas = [
            rastro_en_vivo.comando("discord", al_video=True),
            rastro_en_vivo.comando("hola", "está en espera"),
            rastro_en_vivo.pedido_musica(True, destino="final"),
            rastro_en_vivo.pedido_musica(False, motivo="sin resultados"),
        ]
        texto = " ".join(lineas)
        for dato in ("Ana", "!musica algo", "Tema pedido"):
            self.assertNotIn(dato, texto)


class TestLineasDelVideo(unittest.TestCase):

    def test_la_cola_dice_tipo_nombre_aceptacion_y_pendientes(self):
        self.assertEqual(
            rastro_en_vivo.video_cola("disparador", "Risa", True, 3),
            'VIDEO_COLA tipo=disparador nombre="Risa" aceptada=si '
            'pendientes=3')
        self.assertIn("aceptada=no", rastro_en_vivo.video_cola(
            "mensaje", "Saludo", False, 0))

    def test_la_pieza_mostrada_dice_tipo_y_nombre(self):
        self.assertEqual(
            rastro_en_vivo.video_mostrada("meta", "Risa"),
            'VIDEO_MOSTRADA tipo=meta nombre="Risa"')

    def test_el_fallo_dice_tipo_nombre_y_error(self):
        self.assertEqual(
            rastro_en_vivo.video_fallo("meta", "Risa", "OBS no respondió"),
            'VIDEO_FALLO tipo=meta nombre="Risa" '
            'error="OBS no respondió"')

    def test_la_pieza_descartada_dice_tipo_nombre_y_segundos(self):
        self.assertEqual(
            rastro_en_vivo.video_descartada("disparador", "Risa", 61),
            'VIDEO_DESCARTADA tipo=disparador nombre="Risa" segundos=61')

    def test_el_estado_dice_pausa_silencio_y_panico(self):
        self.assertEqual(
            rastro_en_vivo.video_estado(True, False, True),
            "VIDEO_ESTADO pausado=True silenciado=False panico=True")

    def test_ninguna_linea_lleva_el_texto_del_mensaje(self):
        lineas = [
            rastro_en_vivo.video_cola("mensaje", "Saludo", True, 1),
            rastro_en_vivo.video_mostrada("mensaje", "Saludo"),
            rastro_en_vivo.video_fallo("mensaje", "Saludo", "fallo"),
            rastro_en_vivo.video_estado(False, False, False),
        ]
        self.assertNotIn("Ana", " ".join(lineas))
        self.assertNotIn("privado", " ".join(lineas))


class TestEscritura(unittest.TestCase):

    def test_la_linea_va_al_registro_detallado_en_debug(self):
        with self.assertLogs(rastro_en_vivo.logger, level="DEBUG") as registro:
            rastro_en_vivo.escribir("PRUEBA clave=valor")
        self.assertEqual(registro.output,
                         ["DEBUG:guyrapu.rastro_en_vivo:PRUEBA clave=valor"])

    def test_una_linea_vacia_no_va_al_registro(self):
        with mock.patch.object(rastro_en_vivo.logger, "debug") as debug:
            rastro_en_vivo.escribir("")
        debug.assert_not_called()
