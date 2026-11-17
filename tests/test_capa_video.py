# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La capa que ejecuta en OBS lo que la cola ordena, y su cableado."""

import types
import unittest
from unittest import mock

from guyrapu.capture import programados
from guyrapu.obs.escena_guyrapu import Tarjeta
from guyrapu.ui import capa_video, gui_envio_chat


class _TimerFalso:
    def __init__(self, *argumentos):
        self.ms = None

    def Start(self, ms):
        self.ms = ms

    def Stop(self):
        pass


class _ClienteFalso:
    def __init__(self):
        self.conectado = False
        self.conexiones = 0
        self.ancho = 1000
        self.alto = 1000

    def conectar(self, parada=None):
        self.conectado = True
        self.conexiones += 1

    def cerrar(self):
        self.conectado = False

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "GetSceneItemId":
            return {"responseData": {"sceneItemId": 7}}
        if tipo == "GetVideoSettings":
            return {"responseData": {"baseWidth": self.ancho,
                                     "baseHeight": self.alto}}
        raise AssertionError("pedido inesperado: " + tipo)


class _EscenaFalsa:
    def __init__(self, eventos):
        self.eventos = eventos
        self.estilos = []
        self.preparaciones = 0
        self.ocultaciones = 0

    def preparar(self):
        self.preparaciones += 1
        self.eventos.append("preparar")

    def mostrar(self, texto, estilo):
        self.eventos.append("mostrar")
        self.estilos.append(estilo)
        return Tarjeta(0, 0, 100, 50, "Juego", "")

    def ocultar(self):
        self.ocultaciones += 1
        self.eventos.append("ocultar")


class _AnimadorFalso:
    def __init__(self, eventos, cliente=None):
        self.eventos = eventos
        self.ordenes = []
        self.fallas = 0
        self.cliente = cliente

    def animar(self, orden, tope):
        self.eventos.append("animar")
        self.ordenes.append((orden, tope))
        if self.fallas:
            self.fallas -= 1
            return False
        if self.cliente is not None and not self.cliente.conectado:
            return False
        return True

    def cerrar(self):
        pass


class Base(unittest.TestCase):
    def setUp(self):
        self.parche_timer = mock.patch.object(capa_video.wx, "Timer",
                                              _TimerFalso)
        self.parche_timer.start()
        self.addCleanup(self.parche_timer.stop)
        self.parche_call = mock.patch.object(
            capa_video.wx, "CallAfter", side_effect=lambda f, *a: f(*a))
        self.parche_call.start()
        self.addCleanup(self.parche_call.stop)
        self.anuncios = []
        self.parche_anuncio = mock.patch.object(
            capa_video, "anunciar_con_sonido",
            side_effect=lambda frase, sonido: self.anuncios.append(
                (frase, sonido)))
        self.parche_anuncio.start()
        self.addCleanup(self.parche_anuncio.stop)
        self.anuncios_simples = []
        self.parche_anunciar = mock.patch.object(
            capa_video, "anunciar", side_effect=self.anuncios_simples.append)
        self.parche_anunciar.start()
        self.addCleanup(self.parche_anunciar.stop)
        self.ahora = 100.0
        self.eventos = []
        self.cliente = _ClienteFalso()
        self.escena = _EscenaFalsa(self.eventos)
        self.animador = _AnimadorFalso(self.eventos, self.cliente)
        self.capa = self._capa()

    def _capa(self):
        marco = types.SimpleNamespace(Bind=mock.Mock())
        return capa_video.CapaVideo(
            marco, cliente=self.cliente, escena=self.escena,
            animador=self.animador, reloj=lambda: self.ahora)

    def _mensaje(self, texto="Hola", nombre="Saludo", destino="video",
                 estilo="tarjeta", segundos=10):
        return {"texto": texto, "nombre": nombre, "destino": destino,
                "estilo": estilo, "segundos_pantalla": segundos,
                "activo": True, "proximo": 0.0, "minutos_min": 10,
                "minutos_max": 10, "mensajes_entre": 0}

    def _esperar(self):
        import time
        limite = time.monotonic() + 5
        while self.capa._ocupado and time.monotonic() < limite:
            time.sleep(0.005)
        self.assertFalse(self.capa._ocupado, "el hilo no terminó")

    def _atender(self):
        self.capa._atender(None)
        self._esperar()

    def _anuncios_de(self, sonido):
        return [frase for frase, usado in self.anuncios if usado == sonido]


class TestAgregar(Base):

    def test_arma_la_pieza_con_el_texto_los_segundos_y_su_estilo(self):
        self.assertTrue(self.capa.agregar(self._mensaje(texto="Hola",
                                                        segundos=7)))
        pieza = self.capa.cola.ordenes(0)[0].pieza
        self.assertEqual((pieza.tipo, pieza.texto, pieza.segundos),
                         ("mensaje", "Hola", 7))
        self.assertEqual(pieza.datos, {"estilo": "tarjeta",
                                       "nombre": "Saludo"})


class TestMostrarYOcultar(Base):

    def test_oculta_antes_poner_al_frente_y_recien_entra(self):
        self.capa.agregar(self._mensaje())
        self._atender()
        self.assertEqual(self.eventos,
                         ["preparar", "animar", "mostrar", "animar"])
        ocultar, entrada = (orden for orden, _tope in self.animador.ordenes)
        self.assertEqual(ocultar["cuadros"], [[0, 10000, 0.0, 0.0]])
        self.assertEqual(entrada["cuadros"][-1], [350, 0.0, 0.0, 1.0])

    def test_el_estilo_sale_de_los_estilos_del_usuario(self):
        self.capa.agregar(self._mensaje(estilo="banda"))
        self._atender()
        self.assertEqual(self.escena.estilos[0]["clave"], "banda")

    def test_al_verse_describe_y_anuncia_con_el_nombre(self):
        self.capa.agregar(self._mensaje(nombre="Saludo"))
        self._atender()
        self.assertEqual(self.capa.describir(), "En el vídeo: Hola.")
        self.assertEqual(self.anuncios,
                         [("En el vídeo: Saludo.", "aviso")])

    def test_la_salida_va_antes_de_ocultar(self):
        self.capa.agregar(self._mensaje(estilo="tarjeta"))
        self._atender()
        self.ahora += 10.0
        self._atender()
        self.assertEqual(self.eventos[-2:], ["animar", "ocultar"])
        salida = self.animador.ordenes[-1][0]
        self.assertEqual(salida["cuadros"][0], [0, 0.0, 0.0, 1.0])
        self.assertEqual(salida["cuadros"][-1], [250, 0.0, 0.0, 0.0])
        self.assertEqual(self.capa.describir(), "Nada en el vídeo.")

    def test_una_falla_en_la_salida_y_el_reintento_quita_la_escena(self):
        self.capa.agregar(self._mensaje())
        self._atender()
        self.cliente.conectado = False
        self.ahora += 10.0
        self._atender()
        self.assertTrue(self.cliente.conectado)
        self.assertEqual(self.escena.ocultaciones, 1)
        self.assertNotIn("En el vídeo:", self.capa.describir())

    def test_con_el_sonido_silenciado_anuncia_sin_sonido(self):
        self.capa.cola.silenciar(True)
        self.capa.agregar(self._mensaje(nombre="Saludo"))
        self._atender()
        self.assertEqual(self.anuncios, [])
        self.assertEqual(self.anuncios_simples, ["En el vídeo: Saludo."])

    def test_la_primera_orden_espera_mas_porque_arranca_el_proceso(self):
        self.capa.agregar(self._mensaje())
        self._atender()
        _, primera = self.animador.ordenes[0]
        _, segunda = self.animador.ordenes[1]
        self.assertAlmostEqual(primera, 13.0)
        self.assertAlmostEqual(segunda, 3.35)


class TestRespuestaDeComando(Base):

    def _respuesta(self, estilo="banda", segundos=5):
        return types.SimpleNamespace(
            texto="Nuestro Discord: Ana", estilo=estilo,
            segundos=segundos, nombre="discord")

    def test_agrega_una_pieza_de_comando_con_su_estilo_y_segundos(self):
        self.assertTrue(self.capa.agregar_comando(self._respuesta()))
        pieza = self.capa.cola.ordenes(0)[0].pieza
        self.assertEqual((pieza.tipo, pieza.texto, pieza.segundos),
                         ("comando", "Nuestro Discord: Ana", 5))
        self.assertEqual(pieza.datos,
                         {"estilo": "banda", "nombre": "discord"})

    def test_no_anuncia_la_respuesta_de_un_comando(self):
        self.capa.agregar_comando(self._respuesta(estilo="clasico"))
        self._atender()
        self.assertEqual(self.capa.describir(),
                         "En el vídeo: Nuestro Discord: Ana.")
        self.assertEqual(self.anuncios, [])
        self.assertEqual(self.anuncios_simples, [])


class TestFallas(Base):

    def test_una_falla_llega_a_la_cola_y_se_anuncia_una_vez(self):
        self.animador.fallas = 2
        self.capa.agregar(self._mensaje())
        self._atender()
        self.assertIn("1 en cola.", self.capa.describir())
        self.ahora += 5.0
        self._atender()
        self.assertEqual(self._anuncios_de("espera"), [
            "No se pudo mostrar en el vídeo. Se vuelve a intentar en unos "
            "segundos."])

    def test_tras_una_falla_se_vuelve_a_preparar(self):
        self.animador.fallas = 1
        self.capa.agregar(self._mensaje())
        self._atender()
        self.assertEqual(self.escena.preparaciones, 1)
        self.assertFalse(self.capa._preparado)
        self.ahora += 5.0
        self._atender()
        self.assertEqual(self.cliente.conexiones, 2)
        self.assertEqual(self.escena.preparaciones, 2)
        self.assertTrue(self.capa._preparado)
        self.assertEqual(self.capa.describir(), "En el vídeo: Hola.")

    def test_una_pieza_mostrada_corta_la_racha_de_avisos(self):
        self.animador.fallas = 1
        self.capa.agregar(self._mensaje())
        self._atender()
        self.ahora += 5.0
        self._atender()
        self.ahora += 10.0
        self._atender()
        self.animador.fallas = 1
        self.capa.agregar(self._mensaje(texto="Otra"))
        self.ahora += 1.0
        self._atender()
        self.assertEqual(len(self._anuncios_de("espera")), 2)


class _SesionFalsa:
    def __init__(self, es_tiktok, live_chat_id, propio):
        self.es_tiktok = es_tiktok
        self.live_chat_id = live_chat_id
        self.chat_propio = propio
        self.conexion_propia = False


class _MarcoFalso:
    def __init__(self, mensaje, es_tiktok=False, live_chat_id="chat",
                 propio=True, sesion_api=True, conectado=True):
        self._config = {"programados_activo": True}
        self._conectado = conectado
        self.sesion = _SesionFalsa(es_tiktok, live_chat_id, propio)
        self.programador = programados.ProgramadorMensajes([mensaje])
        self.programador.reloj_iniciado = True
        self._capa_video = mock.Mock()
        self._enviar_programado = mock.Mock()
        self._programado_enviado = mock.Mock()
        self._iniciar_programados_si_corresponde = mock.Mock()
        self.chat_vivo = types.SimpleNamespace(recibidos=0)
        self._sesion_api = sesion_api

    def _sesion_api_disponible(self):
        return self._sesion_api


class TestCableadoProgramado(unittest.TestCase):

    def _mensaje(self, destino):
        return {"texto": "Hola", "nombre": "Saludo", "destino": destino,
                "estilo": "clasico", "segundos_pantalla": 10,
                "activo": True, "proximo": 0.0, "minutos_min": 10,
                "minutos_max": 10, "mensajes_entre": 0}

    def test_uno_solo_de_video_llega_a_la_capa_sin_chat_de_youtube(self):
        mensaje = self._mensaje("video")
        marco = _MarcoFalso(mensaje, es_tiktok=True, live_chat_id="",
                            propio=False, sesion_api=False)
        gui_envio_chat.procesar_programado(marco)
        marco._capa_video.agregar.assert_called_once_with(mensaje)
        marco._programado_enviado.assert_called_once_with(mensaje)
        marco._enviar_programado.assert_not_called()

    def test_uno_de_chat_y_video_sale_en_los_dos(self):
        mensaje = self._mensaje("ambos")
        marco = _MarcoFalso(mensaje)
        gui_envio_chat.procesar_programado(marco)
        marco._capa_video.agregar.assert_called_once_with(mensaje)
        marco._enviar_programado.assert_called_once()
        self.assertIs(marco._enviar_programado.call_args.args[0], mensaje)
        marco._programado_enviado.assert_not_called()

    def test_uno_solo_de_chat_sigue_como_hoy(self):
        mensaje = self._mensaje("chat")
        marco = _MarcoFalso(mensaje)
        gui_envio_chat.procesar_programado(marco)
        marco._capa_video.agregar.assert_not_called()
        marco._enviar_programado.assert_called_once()
        marco._programado_enviado.assert_not_called()

    def test_pasa_la_cuenta_del_chat_al_programador(self):
        marco = _MarcoFalso(self._mensaje("chat"))
        marco.chat_vivo.recibidos = 7
        marco.programador = mock.Mock()
        marco.programador.siguiente.return_value = None
        gui_envio_chat.procesar_programado(marco)
        marco.programador.fijar_mensajes_chat.assert_called_once_with(7)


if __name__ == "__main__":
    unittest.main()
