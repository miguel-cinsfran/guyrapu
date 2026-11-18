# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La unión entre los comandos del chat y la app, de punta a punta."""

import os
import tempfile
import types
import unittest
from unittest import mock

from guyrapu.core import paths
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.interaction import comandos_guardados, filtro_publico
from guyrapu.ui import chat_vivo, comandos_en_vivo, encuesta_en_vivo
from guyrapu.ui import gui, gui_envio_chat
from guyrapu.ui.lista_chat import MensajeChat
from tests.rutas_temporales import redirigir_rutas


def _datos(nombre="discord", respuesta="Hola", destino="video", **cambios):
    datos = {
        "nombre": nombre, "alias": [], "respuesta": respuesta,
        "destino": destino, "permiso": "todos", "nombres": [],
        "espera_general": 5.0, "espera_persona": 30.0, "activo": True,
        "estilo": "clasico", "segundos": 8,
    }
    datos.update(cambios)
    return datos


def _registro(texto, autor="Ana", plataforma="youtube"):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador="C1", texto=texto, hora="12:00",
                       tipo=TIPO_TEXTO, monto="", rol="")


def _hilo_inmediato(objetivo, _nombre):
    hilo = mock.Mock()
    hilo.start.side_effect = objetivo
    return hilo


class _Frame:
    def __init__(self):
        self._conectado = True
        self.sesion = types.SimpleNamespace(
            es_tiktok=False, live_chat_id="LCID", chat_propio=True,
            conexion_propia=False)
        self._capa_video = mock.Mock()
        self._sesion_api = True

    def _sesion_api_disponible(self):
        return self._sesion_api


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        self.ahora = 0.0
        self.frame = _Frame()
        self.lista = mock.Mock()
        self.lista.GetTopLevelParent.return_value = self.frame
        self.control = chat_vivo.ControladorChat(
            self.lista, 500, activo=lambda: True,
            autor_oculto=lambda autor: False,
            formatear=lambda *args: "", al_superchat=mock.Mock(),
            reloj=lambda: self.ahora)

    def _guardar(self, *comandos):
        comandos_guardados.guardar(paths.comandos(), list(comandos))

    def _encolar(self, texto, plataforma="youtube", autor="Ana"):
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()), \
                mock.patch(
                    "guyrapu.capture.traduccion_chat.traduce_lista",
                    return_value=False):
            self.control.encolar(_registro(texto, autor=autor,
                                           plataforma=plataforma))


class TestRespuestaEnElVideo(Base):

    def test_un_comando_que_entra_por_el_chat_llega_a_la_capa(self):
        self._guardar(_datos(respuesta="Nuestro Discord: {usuario}"))
        self._encolar("!discord")
        self.frame._capa_video.agregar_comando.assert_called_once()
        respuesta = self.frame._capa_video.agregar_comando.call_args.args[0]
        self.assertEqual(respuesta.texto, "Nuestro Discord: Ana")
        self.assertEqual(len(self.control._pendientes), 1)


class TestRespuestaEnElChat(Base):

    def test_el_destino_chat_manda_el_texto_final_en_un_hilo(self):
        self._guardar(_datos(
            respuesta="Sígueme, {usuario} ({contador})", destino="chat",
            espera_general=0, espera_persona=0))
        enviado = []
        cliente = mock.Mock()
        cliente.token_actualizado.return_value = None
        cliente.enviar_mensaje_live.side_effect = (
            lambda lcid, texto: enviado.append((lcid, texto)))
        with mock.patch.object(gui, "diagnostico") as diagnostico, \
                mock.patch.object(gui, "youtube_api") as api, \
                mock.patch.object(gui, "credenciales"):
            api.ClienteYouTube.return_value = cliente
            api.sesion_caducada.return_value = False
            diagnostico.crear_hilo.side_effect = _hilo_inmediato
            self._encolar("!discord")
        self.assertEqual(enviado, [("LCID", "Sígueme, Ana (1)")])
        self.frame._capa_video.agregar_comando.assert_not_called()


class TestFrenoDeCuota(Base):

    def test_avisa_una_sola_vez_cuando_la_cuota_corta_los_envios(self):
        self._guardar(
            _datos(nombre="uno", respuesta="Uno", destino="chat"),
            _datos(nombre="dos", respuesta="Dos", destino="chat"))
        avisos = []
        with mock.patch.object(comandos_en_vivo.cuota, "usadas_hoy",
                               return_value=9000), \
                mock.patch.object(
                    gui, "anunciar_con_sonido",
                    side_effect=lambda texto, sonido: avisos.append(
                        (texto, sonido))), \
                mock.patch.object(
                    gui_envio_chat, "enviar_respuesta_chat") as enviar:
            self._encolar("!uno")
            self._encolar("!dos")
        enviar.assert_not_called()
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0][1], "aviso")
        self.assertIn("poca cuota de YouTube", avisos[0][0])
        self.assertEqual(
            self.frame._capa_video.agregar_comando.call_count, 2)


class TestVotoDeEncuesta(Base):

    def test_con_encuesta_abierta_el_numero_no_llega_a_los_comandos(self):
        self._guardar(_datos(nombre="2", respuesta="Respuesta del comando"))
        with mock.patch.object(encuesta_en_vivo, "votar",
                               return_value=True) as votar:
            self._encolar("!2")
        votar.assert_called_once()
        self.frame._capa_video.agregar_comando.assert_not_called()

    def test_sin_encuesta_el_numero_sigue_como_hoy(self):
        self._guardar(_datos(nombre="2", respuesta="Respuesta del comando"))
        self._encolar("!2")
        self.frame._capa_video.agregar_comando.assert_called_once()


class TestRespuestaAlChatDeLaEncuesta(Base):

    def test_usa_el_mismo_envio_que_las_respuestas_de_los_comandos(self):
        with mock.patch.object(
                gui_envio_chat, "enviar_respuesta_chat") as enviar:
            self.assertTrue(comandos_en_vivo.enviar_respuesta(
                self.frame, "Encuesta cerrada."))
        enviar.assert_called_once_with(self.frame, "Encuesta cerrada.")

    def test_con_la_cuota_baja_no_envia_y_avisa(self):
        avisos = []
        with mock.patch.object(comandos_en_vivo.cuota, "usadas_hoy",
                               return_value=9000), \
                mock.patch.object(
                    gui, "anunciar_con_sonido",
                    side_effect=lambda texto, sonido: avisos.append(
                        (texto, sonido))), \
                mock.patch.object(
                    gui_envio_chat, "enviar_respuesta_chat") as enviar:
            self.assertFalse(comandos_en_vivo.enviar_respuesta(
                self.frame, "Encuesta cerrada."))
        enviar.assert_not_called()
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0][1], "aviso")


class TestComandosRespondidos(Base):

    def test_cuenta_las_respuestas_y_recuerda_la_ultima(self):
        self._guardar(
            _datos(nombre="uno", respuesta="Uno", espera_general=0,
                   espera_persona=0),
            _datos(nombre="discord", respuesta="Hola"))
        self._encolar("!uno", autor="Beto")
        self._encolar("!discord", autor="Ana")
        self._encolar("!discord", autor="Beto")
        self.assertEqual(
            self.frame._comandos_en_vivo.frase_estado(),
            "Comandos respondidos: 2, el último !discord de Ana")

    def test_sin_respuestas_no_dice_nada(self):
        self.assertEqual(
            comandos_en_vivo.ComandosEnVivo(self.frame).frase_estado(), "")

    def test_sin_permiso_o_pausado_no_cuenta_ni_cambia_la_ultima(self):
        self._guardar(
            _datos(respuesta="Hola", espera_general=0, espera_persona=0),
            _datos(nombre="privado", respuesta="Privado",
                   permiso="moderadores", espera_general=0,
                   espera_persona=0),
            _datos(nombre="pausado", respuesta="Pausado", activo=False,
                   espera_general=0, espera_persona=0))
        self._encolar("!discord", autor="Ana")
        for texto, caso in (("!privado", "sin permiso"),
                            ("!pausado", "pausado")):
            with self.subTest(caso=caso):
                self._encolar(texto, autor="Beto")
                self.assertEqual(
                    self.frame._comandos_en_vivo.frase_estado(),
                    "Comandos respondidos: 1, el último !discord de Ana")

    def test_cada_sesion_empieza_en_cero(self):
        self._guardar(_datos(respuesta="Hola", espera_general=0,
                             espera_persona=0))
        self._encolar("!discord")
        self.assertNotEqual(
            self.frame._comandos_en_vivo.frase_estado(), "")
        self.assertEqual(
            comandos_en_vivo.ComandosEnVivo(self.frame).frase_estado(), "")


class TestComandosEnPausa(Base):

    def _en_vivo(self):
        en_vivo = comandos_en_vivo.ComandosEnVivo(self.frame)
        self.frame._comandos_en_vivo = en_vivo
        return en_vivo

    def test_en_pausa_no_contesta_ningun_comando(self):
        self._guardar(_datos(respuesta="Hola"))
        self._en_vivo().alternar_pausa()
        self._encolar("!discord")
        self.frame._capa_video.agregar_comando.assert_not_called()

    def test_en_pausa_la_encuesta_sigue_contando_el_voto(self):
        self._guardar(_datos(nombre="2", respuesta="Respuesta del comando"))
        self._en_vivo().alternar_pausa()
        with mock.patch.object(encuesta_en_vivo, "votar",
                               return_value=True) as votar:
            self._encolar("!2")
        votar.assert_called_once()
        self.frame._capa_video.agregar_comando.assert_not_called()

    def test_reanudados_vuelve_a_contestar(self):
        self._guardar(_datos(respuesta="Hola"))
        en_vivo = self._en_vivo()
        en_vivo.alternar_pausa()
        en_vivo.alternar_pausa()
        self._encolar("!discord")
        self.frame._capa_video.agregar_comando.assert_called_once()

    def test_una_sesion_nueva_empieza_sin_pausa(self):
        self._guardar(_datos(respuesta="Hola"))
        self._en_vivo().alternar_pausa()
        self.frame._comandos_en_vivo = comandos_en_vivo.ComandosEnVivo(
            self.frame)
        self._encolar("!discord")
        self.frame._capa_video.agregar_comando.assert_called_once()


class TestRecargaDeComandos(Base):

    def test_relee_el_archivo_cuando_cambia(self):
        self._guardar(_datos(
            respuesta="Uno", espera_general=0, espera_persona=0))
        self._encolar("!discord")
        self._guardar(_datos(
            respuesta="Dos", espera_general=0, espera_persona=0))
        ruta = paths.comandos()
        futuro = ruta.stat().st_mtime + 10
        os.utime(ruta, (futuro, futuro))
        self._encolar("!discord")
        textos = [llamada.args[0].texto for llamada in
                  self.frame._capa_video.agregar_comando.call_args_list]
        self.assertEqual(textos, ["Uno", "Dos"])


class TestRecargaDePalabrasBloqueadas(Base):

    def _guardar_palabras(self, palabras):
        filtro_publico.guardar(paths.palabras_bloqueadas(), palabras)

    def _adelantar(self, ruta):
        futuro = ruta.stat().st_mtime + 10
        os.utime(ruta, (futuro, futuro))

    def test_cambiar_el_archivo_entre_dos_mensajes_cambia_la_respuesta(self):
        self._guardar(_datos(
            respuesta="Hola {texto}", espera_general=0, espera_persona=0))
        self._guardar_palabras(["tonto"])
        self._encolar("!discord tonto")
        self._guardar_palabras([])
        self._adelantar(paths.palabras_bloqueadas())
        self._encolar("!discord tonto")
        textos = [llamada.args[0].texto for llamada in
                  self.frame._capa_video.agregar_comando.call_args_list]
        self.assertEqual(textos, ["Hola ***", "Hola tonto"])


if __name__ == "__main__":
    unittest.main()
