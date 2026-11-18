# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La capa que ejecuta en OBS lo que la cola ordena, y su cableado."""

import types
import unittest
from unittest import mock

from guyrapu.capture import programados
from guyrapu.obs import estilos_aviso, obs_cliente
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
        self.llamadas = []
        self.falla_conexion = None

    def conectar(self, parada=None):
        if self.falla_conexion is not None:
            raise self.falla_conexion
        self.conectado = True
        self.conexiones += 1

    def cerrar(self):
        self.conectado = False

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append(tipo)
        if tipo == "GetSceneItemId":
            return {"responseData": {"sceneItemId": 7}}
        if tipo == "GetVideoSettings":
            return {"responseData": {"baseWidth": self.ancho,
                                     "baseHeight": self.alto}}
        raise AssertionError("pedido inesperado: " + tipo)

    def pedidos(self, tipo):
        return [llamado for llamado in self.llamadas if llamado == tipo]


class _EscenaFalsa:
    def __init__(self, eventos):
        self.eventos = eventos
        self.estilos = []
        self.textos = []
        self.preparaciones = 0
        self.ocultaciones = 0
        self.en_programa = False
        self.tarjeta = Tarjeta(0, 0, 100, 50, "", "")

    def preparar(self):
        self.preparaciones += 1
        self.eventos.append("preparar")

    def armar(self, texto, estilo):
        self.eventos.append("armar")
        self.textos.append(texto)
        self.estilos.append(estilo)
        return self.tarjeta

    def en_el_programa(self):
        return self.en_programa

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


class TestProbar(Base):

    def setUp(self):
        super().setUp()
        self.revisiones = []

    def _probar(self, texto="Hola"):
        self.capa.probar(texto, dict(estilos_aviso.FABRICA[0]),
                         lambda frase, error: self.revisiones.append(
                             (frase, error)))
        self._esperar()

    def test_p1_arma_la_tarjeta_sin_poner_la_escena_al_frente(self):
        self._probar("Así se ve un mensaje con este estilo.")
        self.assertEqual(self.eventos, ["preparar", "armar"])
        self.assertEqual(self.escena.textos,
                         ["Así se ve un mensaje con este estilo."])
        for tipo in ("CreateSceneItem", "SetSceneItemIndex",
                     "GetCurrentProgramScene"):
            self.assertEqual(self.cliente.pedidos(tipo), [])
        self.assertEqual(len(self.revisiones), 1)
        self.assertIn("Zona:", self.revisiones[0][0])
        self.assertFalse(self.revisiones[0][1])

    def test_p3_con_una_tarjeta_visible_se_niega_sin_tocar_obs(self):
        self.capa.agregar(self._mensaje())
        self._atender()
        antes = (list(self.eventos), list(self.cliente.llamadas))
        self._probar()
        self.assertEqual(self.revisiones, [
            ("Hay algo en el vídeo. Prueba cuando termine.", True)])
        self.assertEqual(self.eventos, antes[0])
        self.assertEqual(self.cliente.llamadas, antes[1])

    def test_p3_con_la_escena_en_el_programa_se_niega_sin_tocar_obs(self):
        self.escena.en_programa = True
        self._probar()
        self.assertEqual(self.revisiones, [
            ("La escena de Guyrapu está en la escena que sale al aire. "
             "Quítala de esa escena en OBS y vuelve a probar.", True)])
        self.assertEqual(self.eventos, [])
        self.assertEqual(self.cliente.llamadas, [])

    def test_p3_con_la_cola_trabajando_se_niega_sin_tocar_obs(self):
        self.capa._ocupado = True
        try:
            self.capa.probar("Hola", dict(estilos_aviso.FABRICA[0]),
                             lambda frase, error: self.revisiones.append(
                                 (frase, error)))
        finally:
            self.capa._ocupado = False
        self.assertEqual(self.revisiones, [
            ("La cola del vídeo está ocupada. Prueba en unos segundos.",
             True)])
        self.assertEqual(self.eventos, [])
        self.assertEqual(self.cliente.llamadas, [])

    def test_p3_sin_conexion_usa_el_mensaje_de_fallo_de_obs(self):
        fallo = obs_cliente.ObsError("falla técnica")
        self.cliente.falla_conexion = fallo
        with mock.patch.object(
                obs_cliente, "mensaje_de_fallo_obs",
                return_value="Sin conexión con OBS.") as traducir:
            self._probar()
        traducir.assert_called_once_with(fallo)
        self.assertEqual(self.revisiones,
                         [("Sin conexión con OBS.", True)])
        self.assertEqual(self.eventos, [])
        self.assertEqual(self.cliente.llamadas, [])

    def test_p3_sin_conexion_traduce_el_error_que_no_es_de_obs(self):
        fallo = OSError("falla técnica")
        self.cliente.falla_conexion = fallo
        with mock.patch.object(
                obs_cliente, "mensaje_de_fallo_obs",
                return_value="Sin conexión con OBS.") as traducir:
            self._probar()
        traducir.assert_called_once_with(fallo)
        self.assertEqual(self.revisiones,
                         [("Sin conexión con OBS.", True)])
        self.assertEqual(self.eventos, [])
        self.assertEqual(self.cliente.llamadas, [])


class TestEncuestaFija(Base):

    def _pieza(self, texto):
        from guyrapu.interaction.cola_pantalla import Pieza
        return Pieza(tipo="encuesta", texto=texto, segundos=0,
                     datos={"estilo": "clasico"})

    def test_fijar_y_poner_al_dia_cambia_el_texto_sin_ocultar(self):
        encuesta = self._pieza("¿Sí o no?")
        self.capa.fijar_encuesta(encuesta)
        self._atender()
        self.assertEqual(self.capa.describir(),
                         "Encuesta en el vídeo: ¿Sí o no?.")
        nueva = self._pieza("¿Sí o no? 2 votos")
        self.assertTrue(self.capa.poner_al_dia_encuesta(nueva))
        self._atender()
        self.assertEqual(self.capa.describir(),
                         "Encuesta en el vídeo: ¿Sí o no? 2 votos.")
        self.assertEqual(self.escena.ocultaciones, 0)
        self.assertEqual(self.anuncios, [])
        self.assertEqual(self.anuncios_simples, [])

    def test_agrega_la_encuesta_terminada_como_una_pieza(self):
        from guyrapu.interaction.cola_pantalla import Pieza
        pieza = Pieza(tipo="encuesta", texto="Resultado", segundos=10,
                      datos={"estilo": "clasico"})
        self.assertTrue(self.capa.agregar_pieza(pieza))
        self._atender()
        self.assertEqual(self.capa.describir(), "En el vídeo: Resultado.")

    def test_quitar_la_encuesta_la_oculta(self):
        encuesta = self._pieza("¿Sí o no?")
        self.capa.fijar_encuesta(encuesta)
        self._atender()
        self.capa.quitar_encuesta()
        self._atender()
        self.assertEqual(self.escena.ocultaciones, 1)
        self.assertEqual(self.capa.describir(), "Nada en el vídeo.")


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


class TestEstadoParaAcciones(Base):

    def test_pausar_y_reanudar_se_reflejan_en_el_estado_y_en_f2(self):
        self.capa.pausar()
        self.assertTrue(self.capa.estado()["pausado"])
        self.assertIn("La cola está en pausa.", self.capa.describir())
        self.capa.reanudar()
        self.assertFalse(self.capa.estado()["pausado"])
        self.assertNotIn("La cola está en pausa.", self.capa.describir())

    def test_silenciar_se_refleja_en_el_estado_y_en_f2(self):
        self.capa.silenciar(True)
        self.assertTrue(self.capa.estado()["silenciado"])
        self.assertIn("Sonido de los medios silenciado.", self.capa.describir())
        self.capa.silenciar(False)
        self.assertFalse(self.capa.estado()["silenciado"])

    def test_el_panico_vacia_y_al_apagarlo_la_cola_sigue(self):
        self.capa.agregar(self._mensaje())
        self.capa.panico(True)
        self.assertTrue(self.capa.estado()["panico"])
        self.assertIn("Pánico activado", self.capa.describir())
        self.assertFalse(self.capa.vaciar())
        self.capa.panico(False)
        self.assertFalse(self.capa.estado()["panico"])
        self.assertTrue(self.capa.agregar(self._mensaje()))

    def test_saltar_dice_si_habia_algo_en_el_video(self):
        self.assertFalse(self.capa.saltar())
        self.capa.agregar(self._mensaje())
        self._atender()
        self.assertTrue(self.capa.saltar())
        self._atender()
        self.assertNotIn("En el vídeo:", self.capa.describir())

    def test_vaciar_dice_si_habia_algo_en_la_cola(self):
        self.assertFalse(self.capa.vaciar())
        self.capa.agregar(self._mensaje())
        self.assertTrue(self.capa.vaciar())
        self.assertEqual(self.capa.describir(), "Nada en el vídeo.")


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
