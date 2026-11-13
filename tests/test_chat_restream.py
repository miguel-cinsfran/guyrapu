# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de cómo se conectan los chats de un directo por Restream."""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.capture import chat_adicional, tiktok_vivo
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


class HiloInmediato:

    def __init__(self, target, nombre=""):
        self.target = target
        self.nombre = nombre

    def start(self):
        self.target()


class RelojFalso:

    def __init__(self):
        self.ahora = 0.0

    def reloj(self):
        return self.ahora

    def dormir(self, segundos):
        self.ahora += segundos


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

    def test_p1_busca_tiktok_antes_de_conectar_el_principal(self):
        frame = FrameFalso()
        eventos = []

        def esperar(_usuario, _parada, cada, limite):
            eventos.append("buscar")
            chat_restream.parar_espera()
            return _resultado(True)

        def al_conectar(_evento):
            eventos.append("principal")
            frame._conectado = True

        frame._on_conectar.side_effect = al_conectar
        with mock.patch.object(
                chat_restream, "_en_interfaz",
                side_effect=lambda f, funcion, *args: funcion(*args)):
            callback = chat_restream.conectar_chat(
                frame, tiktok="amigo", pedido=True,
                al_anunciar=lambda *args: None, crear_hilo=HiloInmediato,
                esperar_en_vivo=esperar)
            self.assertEqual(eventos, ["buscar"])
            callback("https://youtu.be/video1")

        self.assertEqual(eventos, ["buscar", "principal"])

    def test_p2_espera_sin_plazo_y_conecta_el_adicional(self):
        frame = FrameFalso()
        estados = [(False, False, False)] * 60 + [(True, False, False)]
        reloj = {"ahora": 0.0}

        def dormir(segundos):
            reloj["ahora"] += segundos

        def activo():
            chat_restream.parar_espera()
            return True

        with mock.patch.object(chat_restream, "_leer_estado",
                               side_effect=estados), \
                mock.patch.object(chat_restream, "_dormir",
                                  side_effect=dormir), \
                mock.patch.object(chat_restream, "_reloj",
                                  side_effect=lambda: reloj["ahora"],
                                  create=True), \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))
        self.assertEqual(anuncios, [])

    def test_p2_si_la_interfaz_no_contesta_sigue_esperando(self):
        frame = FrameFalso()
        estados = [None, None, (True, False, False)]

        def activo():
            chat_restream.parar_espera()
            return True

        with mock.patch.object(chat_restream, "_leer_estado",
                               side_effect=estados), \
                mock.patch.object(chat_restream, "_dormir") as dormir, \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            self._conectar(frame, tiktok="amigo", pedido=True)

        self.assertEqual(dormir.call_count, 3)
        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))

    def test_p3_avisa_una_vez_y_sigue_buscando_cada_30_segundos(self):
        frame = FrameFalso()
        llamadas = []
        primera = _resultado(False, cuenta_sin_directos=True)

        def esperar(usuario, parada, cada, limite):
            llamadas.append((usuario, cada, limite))
            if len(llamadas) == 1:
                return primera
            if len(llamadas) == 2:
                return _resultado(False)
            return _resultado(True)

        def activo():
            chat_restream.parar_espera()
            return True

        with mock.patch.object(chat_restream, "_leer_estado",
                               return_value=(True, False, False)), \
                mock.patch.object(chat_restream, "_dormir"), \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            anuncios = self._conectar(frame, esperar_en_vivo=esperar,
                                      tiktok="amigo", pedido=True)

        self.assertEqual(llamadas, [("amigo", 5.0, 120.0),
                                    ("amigo", 30.0, 30.0),
                                    ("amigo", 30.0, 30.0)])
        self.assertEqual(anuncios, [(*tiktok_vivo.aviso_espera(
            primera, "amigo"), False)])
        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))

    def test_p4_reconecta_el_adicional_y_suena_al_pedirlo(self):
        frame = FrameFalso()
        estados_activo = [True, False, True]
        eventos = []
        llamadas = []

        def activo():
            if estados_activo:
                return estados_activo.pop(0)
            chat_restream.parar_espera()
            return True

        def esperar(usuario, parada, cada, limite):
            eventos.append("buscar")
            llamadas.append((usuario, cada, limite))
            return _resultado(True)

        def sonar(sonido):
            eventos.append(("sonar", sonido))

        frame.conectar_chat_adicional.side_effect = (
            lambda url: eventos.append("conectar"))

        with mock.patch.object(chat_restream, "_leer_estado",
                               return_value=(True, False, False)), \
                mock.patch.object(chat_restream, "_dormir"), \
                mock.patch.object(chat_restream, "_sonar", side_effect=sonar), \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            anuncios = self._conectar(frame, esperar_en_vivo=esperar,
                                      tiktok="amigo", pedido=True)

        self.assertEqual(eventos[:5], [
            "buscar", "conectar", "buscar",
            ("sonar", "chat_reconectado"), "conectar"])
        self.assertEqual(frame.conectar_chat_adicional.call_count, 2)
        self.assertEqual(llamadas, [("amigo", 5.0, 120.0),
                                    ("amigo", 30.0, 30.0)])
        self.assertEqual(anuncios, [])

    def test_p4_tres_desconexiones_rapidas_dejan_de_reconectar(self):
        frame = FrameFalso()
        llamadas_activo = 0

        def activo():
            nonlocal llamadas_activo
            llamadas_activo += 1
            if llamadas_activo >= 4:
                chat_restream.parar_espera()
            return False

        with mock.patch.object(chat_restream, "_leer_estado",
                               return_value=(True, False, False)), \
                mock.patch.object(chat_restream, "_dormir"), \
                mock.patch.object(chat_restream, "_reloj",
                                  side_effect=lambda: 0.0, create=True), \
                mock.patch.object(chat_restream, "_sonar"), \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        self.assertEqual(frame.conectar_chat_adicional.call_count, 3)
        self.assertEqual(anuncios, [(
            "El chat de TikTok se dejó de reconectar porque se desconectaba "
            "enseguida.", "transmision_problema", False)])

    def test_p4_una_conexion_larga_reinicia_la_cuenta(self):
        frame = FrameFalso()
        reloj = RelojFalso()
        llamadas_activo = 0

        def activo():
            nonlocal llamadas_activo
            llamadas_activo += 1
            if llamadas_activo <= 12:
                return True
            if llamadas_activo == 16:
                chat_restream.parar_espera()
            return False

        with mock.patch.object(chat_restream, "_leer_estado",
                               return_value=(True, False, False)), \
                mock.patch.object(chat_restream, "_dormir",
                                  side_effect=reloj.dormir), \
                mock.patch.object(chat_restream, "_reloj",
                                  side_effect=reloj.reloj, create=True), \
                mock.patch.object(chat_restream, "_sonar"), \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        self.assertEqual(frame.conectar_chat_adicional.call_count, 4)
        self.assertEqual(anuncios, [])

    def test_p5_la_parada_durante_la_busqueda_no_avisa(self):
        frame = FrameFalso()

        def esperar(_usuario, _parada, cada, limite):
            chat_restream.parar_espera()
            return _resultado(False, cuenta_sin_directos=True)

        anuncios = self._conectar(frame, esperar_en_vivo=esperar,
                                  tiktok="amigo", pedido=True)

        self.assertEqual(anuncios, [])
        frame.conectar_chat_adicional.assert_not_called()

    def test_p5_la_parada_durante_la_vigilancia_no_avisa(self):
        frame = FrameFalso()

        def activo():
            chat_restream.parar_espera()
            return False

        with mock.patch.object(chat_restream, "_leer_estado",
                               return_value=(True, False, False)), \
                mock.patch.object(chat_restream, "_dormir"), \
                mock.patch.object(chat_adicional, "activo",
                                  side_effect=activo):
            anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        self.assertEqual(anuncios, [])
        frame.conectar_chat_adicional.assert_called_once_with(
            tiktok_vivo.url_directo("amigo"))

    def test_p6_si_el_principal_es_tiktok_no_conecta_adicional(self):
        frame = FrameFalso(es_tiktok=True)
        esperado = tiktok_vivo.ResultadoEspera(False, False)

        anuncios = self._conectar(frame, tiktok="amigo", pedido=True)

        frame.conectar_chat_adicional.assert_not_called()
        self.assertIn((*tiktok_vivo.aviso_espera(esperado, "amigo"), False),
                      anuncios)

    def test_p7_sin_usuario_avisa_que_no_se_va_a_leer(self):
        frame = FrameFalso()
        esperar = mock.Mock()

        anuncios = self._conectar(
            frame, esperar_en_vivo=esperar, tiktok="", pedido=True)

        esperar.assert_not_called()
        frame.conectar_chat_adicional.assert_not_called()
        self.assertIn(
            ("El chat de TikTok no se va a leer porque el perfil de Restream "
             "no tiene usuario de TikTok.", "error", False), anuncios)

    def test_sin_ambos_no_espera(self):
        frame = FrameFalso()
        esperar = mock.Mock()

        self._conectar(frame, esperar_en_vivo=esperar, tiktok="", pedido=False)

        esperar.assert_not_called()
        frame.conectar_chat_adicional.assert_not_called()


if __name__ == "__main__":
    unittest.main()
