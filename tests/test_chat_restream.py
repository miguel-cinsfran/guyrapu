# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de cómo se conectan los chats de un directo por Restream."""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.capture import tiktok_vivo
from guyrapu.restream import chat_restream


class FrameFalso:

    def __init__(self, es_tiktok=False, vivo=True):
        self._alive = vivo
        self._conectado = False
        self._conectando = False
        self.sesion = SimpleNamespace(es_tiktok=es_tiktok,
                                      conexion_propia=False)
        self.txt_url = mock.Mock()
        self._on_conectar = mock.Mock(side_effect=self._al_conectar)
        self.conectar_chat_adicional = mock.Mock()

    def _al_conectar(self, _evento):
        self._conectado = True


class FrameQueSeConectaDespues(FrameFalso):
    """El principal sigue conectándose después de pedir la conexión."""

    def _al_conectar(self, _evento):
        self._conectando = True


class FrameQueNoConecta(FrameFalso):
    """El principal no queda ni conectado ni conectándose."""

    def _al_conectar(self, _evento):
        self._conectando = False


class RelojFalso:

    def __init__(self):
        self.ahora = 0.0

    def reloj(self):
        return self.ahora

    def dormir(self, segundos):
        self.ahora += segundos


class HiloInmediato:

    def __init__(self, target, nombre=""):
        self.target = target
        self.nombre = nombre

    def start(self):
        self.target()


def _resultado(en_vivo, cuenta_sin_directos=False, limitado=False):
    return tiktok_vivo.ResultadoEspera(en_vivo, cuenta_sin_directos, limitado)


class TestConectarChat(unittest.TestCase):

    def tearDown(self):
        chat_restream.reiniciar_espera()

    def _conectar(self, frame, esperar_en_vivo=None, **cambios):
        anuncios = []

        def al_anunciar(frase, sonido, importante=False):
            anuncios.append((frase, sonido, importante))

        argumentos = dict(
            youtube=False, guardados={}, al_anunciar=al_anunciar,
            crear_hilo=HiloInmediato,
            esperar_en_vivo=esperar_en_vivo
            or (lambda *args, **kwargs: _resultado(True)))
        argumentos.update(cambios)
        with mock.patch.object(
                chat_restream, "_en_interfaz",
                side_effect=lambda frame, funcion, *args: funcion(*args)):
            chat_restream.conectar_chat(frame, **argumentos)(
                "https://youtu.be/video1")
        return anuncios

    def test_p4_con_ambos_espera_y_conecta_el_adicional(self):
        frame = FrameFalso()
        llamadas = []

        def esperar(usuario, parada, cada, limite):
            llamadas.append((usuario, cada, limite))
            return _resultado(True)

        anuncios = self._conectar(frame, esperar_en_vivo=esperar,
                                  tiktok="amigo", pedido=True)

        frame._on_conectar.assert_called_once_with(None)
        self.assertEqual(llamadas, [("amigo", 5.0, 120.0)])
        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))
        self.assertIn(
            ("Esperando a que TikTok muestre el directo para leer su chat.",
             None, False), anuncios)

    def test_sin_ambos_no_espera(self):
        frame = FrameFalso()
        esperar = mock.Mock()

        self._conectar(frame, esperar_en_vivo=esperar, tiktok="", pedido=False)

        esperar.assert_not_called()
        frame.conectar_chat_adicional.assert_not_called()

    def test_p5_sin_directo_avisa_con_aviso_espera(self):
        frame = FrameFalso()
        resultado = _resultado(False, cuenta_sin_directos=True)

        anuncios = self._conectar(
            frame, esperar_en_vivo=lambda *args, **kwargs: resultado,
            tiktok="amigo", pedido=True)

        self.assertIn((*tiktok_vivo.aviso_espera(resultado, "amigo"), True),
                      anuncios)
        frame.conectar_chat_adicional.assert_not_called()

    def test_p6_si_el_principal_se_desconecto_no_conecta(self):
        frame = FrameFalso()

        def esperar(_usuario, _parada, cada, limite):
            frame._conectado = False
            return _resultado(True)

        self._conectar(frame, esperar_en_vivo=esperar, tiktok="amigo",
                       pedido=True)

        frame._on_conectar.assert_called_once_with(None)
        frame.conectar_chat_adicional.assert_not_called()

    def test_p6_si_la_parada_se_disparo_no_conecta(self):
        frame = FrameFalso()

        def esperar(_usuario, _parada, cada, limite):
            chat_restream.parar_espera()
            return _resultado(True)

        self._conectar(frame, esperar_en_vivo=esperar, tiktok="amigo",
                       pedido=True)

        frame.conectar_chat_adicional.assert_not_called()

    def test_p6_si_la_transmision_termina_durante_la_espera_no_avisa(self):
        frame = FrameFalso()

        def esperar(_usuario, _parada, cada, limite):
            chat_restream.parar_espera()
            return _resultado(False, cuenta_sin_directos=True)

        anuncios = self._conectar(frame, esperar_en_vivo=esperar,
                                  tiktok="amigo", pedido=True)

        self.assertEqual(
            [("Esperando a que TikTok muestre el directo para leer su chat.",
              None, False)], anuncios)
        frame.conectar_chat_adicional.assert_not_called()

    def test_p1_espera_a_que_el_principal_termina_de_conectarse(self):
        frame = FrameQueSeConectaDespues()
        dormidas = []

        def dormir(segundos):
            dormidas.append(segundos)
            frame._conectando = False
            frame._conectado = True

        with mock.patch.object(chat_restream, "_dormir", side_effect=dormir), \
                mock.patch.object(chat_restream, "_reloj", return_value=0.0):
            self._conectar(frame, tiktok="amigo", pedido=True)

        self.assertEqual(len(dormidas), 1)
        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))

    def test_p1_si_la_interfaz_no_contesta_sigue_esperando(self):
        frame = FrameQueSeConectaDespues()
        estados = [None, None, (True, False, False)]

        with mock.patch.object(chat_restream, "_leer_estado",
                               side_effect=estados), \
                mock.patch.object(chat_restream, "_dormir") as dormir, \
                mock.patch.object(chat_restream, "_reloj", return_value=0.0):
            self._conectar(frame, tiktok="amigo", pedido=True)

        self.assertEqual(dormir.call_count, 2)
        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))

    def test_p2_si_el_principal_no_se_conecta_a_tiempo_avisa(self):
        frame = FrameQueSeConectaDespues()
        reloj = RelojFalso()
        esperado = tiktok_vivo.ResultadoEspera(False, False)

        with mock.patch.object(chat_restream, "_dormir",
                               side_effect=reloj.dormir), \
                mock.patch.object(chat_restream, "_reloj",
                                  side_effect=reloj.reloj), \
                mock.patch.object(chat_restream.logger, "warning") as aviso:
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        frame.conectar_chat_adicional.assert_not_called()
        aviso.assert_called_once()
        self.assertIn((*tiktok_vivo.aviso_espera(esperado, "amigo"), True),
                      anuncios)

    def test_p2_si_el_principal_esta_desconectado_avisa(self):
        frame = FrameQueNoConecta()
        esperado = tiktok_vivo.ResultadoEspera(False, False)

        with mock.patch.object(chat_restream.logger, "warning") as aviso:
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        frame.conectar_chat_adicional.assert_not_called()
        aviso.assert_called_once()
        self.assertIn((*tiktok_vivo.aviso_espera(esperado, "amigo"), True),
                      anuncios)

    def test_p2_si_la_parada_llega_durante_la_espera_no_avisa(self):
        frame = FrameQueSeConectaDespues()

        def dormir(_segundos):
            chat_restream.parar_espera()

        with mock.patch.object(chat_restream, "_dormir", side_effect=dormir), \
                mock.patch.object(chat_restream.logger, "warning") as aviso:
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        aviso.assert_not_called()
        frame.conectar_chat_adicional.assert_not_called()
        self.assertEqual(
            [("Esperando a que TikTok muestre el directo para leer su chat.",
              None, False)], anuncios)

    def test_p7_sin_usuario_avisa_y_no_espera(self):
        frame = FrameFalso()
        esperar = mock.Mock()

        anuncios = self._conectar(
            frame, esperar_en_vivo=esperar, tiktok="", pedido=True)

        esperar.assert_not_called()
        frame.conectar_chat_adicional.assert_not_called()
        self.assertIn(
            ("No se encontró el usuario de TikTok del perfil: conecta el "
             "chat de TikTok a mano.", "error", False), anuncios)


if __name__ == "__main__":
    unittest.main()
