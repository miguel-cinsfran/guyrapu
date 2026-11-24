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
from guyrapu.core.sonidos_eventos import ROL_MODERADOR
from guyrapu.interaction import (
    comandos_guardados, filtro_publico, medios_guardados)
from guyrapu.ui import chat_vivo, comandos_en_vivo, encuesta_en_vivo
from guyrapu.ui import gui, gui_envio_chat, preguntas_en_vivo
from guyrapu.ui.capa_video import CapaVideo
from guyrapu.ui.lista_chat import MensajeChat
from tests.rutas_temporales import redirigir_rutas


def _datos(nombre="discord", respuesta="Hola", destino="video", **cambios):
    datos = {
        "nombre": nombre, "alias": [], "respuesta": respuesta, "medio": "",
        "destino": destino, "permiso": "todos", "nombres": [],
        "espera_general": 5.0, "espera_persona": 30.0, "activo": True,
        "estilo": "clasico", "segundos": 8,
    }
    datos.update(cambios)
    return datos


def _registro(texto, autor="Ana", plataforma="youtube", rol=""):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador="C1", texto=texto, hora="12:00",
                       tipo=TIPO_TEXTO, monto="", rol=rol)


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


class _CapaQueGuardaPiezas:
    """Usa el armado real de la capa sin crear ventanas."""

    def __init__(self):
        self.piezas = []
        self._en_cola = 0

    def agregar_comando(self, respuesta, medio=None):
        return CapaVideo.agregar_comando(self, respuesta, medio)

    def _agregar(self, pieza):
        self.piezas.append(pieza)
        self._en_cola += 1
        return True


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

    def _guardar_medios(self, *medios):
        medios_guardados.guardar(paths.medios(), list(medios))
        carpeta = paths.carpeta_medios()
        carpeta.mkdir(parents=True, exist_ok=True)
        for medio in medios:
            (carpeta / medio["archivo"]).write_bytes(b"x")

    def _capa_con_piezas(self):
        capa = _CapaQueGuardaPiezas()
        self.frame._capa_video = capa
        return capa

    def _ventana_falsa(self):
        ventana = types.SimpleNamespace(
            cerrado=False, agregar_resultado=mock.Mock())
        self.frame._ventana_ensayo = ventana
        return ventana

    def _encolar(self, texto, plataforma="youtube", autor="Ana", rol=""):
        with mock.patch.object(chat_vivo.wx, "CallLater",
                               return_value=mock.Mock()), \
                mock.patch(
                    "guyrapu.capture.traduccion_chat.traduce_lista",
                    return_value=False):
            self.control.encolar(_registro(texto, autor=autor,
                                           plataforma=plataforma, rol=rol))


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


class TestMedioDelComando(Base):

    def _fuegos(self):
        return {"nombre": "fuegos", "tipo": "video", "archivo": "fuegos.mp4",
                "duracion": 12, "ganancia_db": -6.0}

    def test_un_comando_con_medio_pone_la_pieza_con_el_medio_y_la_duracion(self):
        self._guardar_medios(self._fuegos())
        self._guardar(_datos(medio="fuegos"))
        capa = self._capa_con_piezas()
        self._encolar("!discord")
        self.assertEqual(len(capa.piezas), 1)
        pieza = capa.piezas[0]
        self.assertEqual((pieza.tipo, pieza.texto, pieza.segundos),
                         ("comando", "Hola", 12))
        self.assertEqual(pieza.datos["medio"], {
            "ruta": str(paths.carpeta_medios() / "fuegos.mp4"),
            "tipo": "video", "duracion": 12, "ganancia_db": -6.0,
            "volumen": 100,
        })

    def test_con_mostrar_en_chat_la_pieza_lleva_el_medio_y_texto_vacio_y_al_chat_la_respuesta(self):
        self._guardar_medios(self._fuegos())
        self._guardar(_datos(medio="fuegos", destino="chat"))
        capa = self._capa_con_piezas()
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
        self.assertEqual(len(capa.piezas), 1)
        pieza = capa.piezas[0]
        self.assertEqual((pieza.texto, pieza.segundos), ("", 12))
        self.assertIn("medio", pieza.datos)
        self.assertEqual(enviado, [("LCID", "Hola")])

    def test_un_medio_que_ya_no_esta_deja_la_respuesta_como_sin_medio(self):
        self._guardar(_datos(medio="fuegos"))
        capa = self._capa_con_piezas()
        self._encolar("!discord")
        pieza = capa.piezas[0]
        self.assertEqual((pieza.tipo, pieza.texto, pieza.segundos),
                         ("comando", "Hola", 8))
        self.assertNotIn("medio", pieza.datos)


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


class TestPreguntasDelPublico(Base):

    def test_una_pregunta_suma_y_no_responde_el_comando_del_mismo_nombre(self):
        self._guardar(_datos(nombre="pregunta",
                             respuesta="Respuesta del comando"))
        self._encolar("!pregunta Hola")
        self.frame._capa_video.agregar_comando.assert_not_called()
        pendientes = preguntas_en_vivo.pendientes(self.frame)
        self.assertEqual([pregunta.texto for pregunta in pendientes],
                         ["Hola"])

    def test_con_los_comandos_en_pausa_no_suma(self):
        self._guardar(_datos(nombre="pregunta",
                             respuesta="Respuesta del comando"))
        en_vivo = comandos_en_vivo.ComandosEnVivo(self.frame)
        self.frame._comandos_en_vivo = en_vivo
        en_vivo.alternar_pausa()
        self._encolar("!pregunta Hola")
        self.assertEqual(preguntas_en_vivo.pendientes(self.frame), [])
        self.frame._capa_video.agregar_comando.assert_not_called()


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


class TestEnsayo(Base):
    """Con la ventana de ensayo abierta, sin directo, la tarjeta va al vídeo."""

    def setUp(self):
        super().setUp()
        self.frame._conectado = False
        self.frame._ensayo = True

    def test_el_comando_pone_su_tarjeta_y_no_va_al_chat(self):
        self._guardar(_datos(respuesta="Nuestro Discord: {usuario}"))
        with mock.patch.object(gui_envio_chat, "enviar_respuesta_chat") as enviar:
            self._encolar("!discord")
        self.frame._capa_video.agregar_comando.assert_called_once()
        enviar.assert_not_called()

    def test_sin_ensayo_ni_conexion_no_pone_tarjeta(self):
        self.frame._ensayo = False
        self._guardar(_datos(respuesta="Nuestro Discord: {usuario}"))
        self._encolar("!discord")
        self.frame._capa_video.agregar_comando.assert_not_called()

    def test_cada_envio_anuncia_lo_que_respondio_y_lo_deja_en_resultados(self):
        self._guardar(_datos(nombre="hola", espera_persona=0))
        ventana = self._ventana_falsa()
        with mock.patch.object(chat_vivo, "anunciar_con_sonido") as avisar:
            self._encolar("!hola")
            self.ahora = 1.0
            self._encolar("!hola")
        primero = "Respondió el comando hola."
        segundo = ("Nada respondió: el comando hola está en espera, "
                   "faltan 4 segundos.")
        self.assertEqual(avisar.call_args_list, [
            mock.call(primero, "listo"), mock.call(segundo, "aviso")])
        self.assertEqual([llamada.args[1] for llamada in
                          ventana.agregar_resultado.call_args_list],
                         [primero, segundo])

    def test_el_rol_de_quien_escribe_decide_el_permiso(self):
        self._guardar(_datos(nombre="modo", permiso="moderadores"))
        with mock.patch.object(chat_vivo, "anunciar_con_sonido") as avisar:
            self._encolar("!modo")
            self._encolar("!modo", rol=ROL_MODERADOR)
        self.assertEqual([llamada.args[0] for llamada in avisar.call_args_list],
                         ["Nada respondió: el comando modo es solo para "
                          "solo moderadores.",
                          "Respondió el comando modo."])

    def test_los_comandos_en_pausa_dicen_por_que_no_responden(self):
        self._guardar(_datos(nombre="hola"))
        comandos_en_vivo._en_vivo(self.frame).alternar_pausa()
        with mock.patch.object(chat_vivo, "anunciar_con_sonido") as avisar:
            self._encolar("!hola")
        avisar.assert_called_once_with(
            "Nada respondió: los comandos están en pausa.", "aviso")

    def test_con_un_directo_conectado_no_anota_ni_anuncia(self):
        self._guardar(_datos(nombre="hola"))
        self.frame._ensayo = False
        self.frame._conectado = True
        ventana = self._ventana_falsa()
        with mock.patch.object(chat_vivo, "anunciar_con_sonido") as avisar:
            self._encolar("!hola")
        avisar.assert_not_called()
        ventana.agregar_resultado.assert_not_called()


class TestUbicacionEnCualquierParte(Base):

    def test_una_palabra_en_cualquier_parte_deja_su_pieza(self):
        self._guardar(_datos(nombre="risa", respuesta="Risas",
                             ubicacion="cualquiera"))
        self._encolar("qué risa jaja")
        self.frame._capa_video.agregar_comando.assert_called_once()
        respuesta = self.frame._capa_video.agregar_comando.call_args.args[0]
        self.assertEqual(respuesta.texto, "Risas")

    def test_un_comando_con_signo_no_lo_cumple(self):
        self._guardar(_datos(nombre="risa", respuesta="Risas",
                             ubicacion="cualquiera"))
        self._encolar("!risa")
        self.frame._capa_video.agregar_comando.assert_not_called()


class TestAtajoDelComando(Base):

    def _guardar_solo_con_atajo(self):
        self._guardar(_datos(nombre="risa", respuesta="Risas",
                             permiso="solo_atajo", atajo=3))

    def test_el_atajo_pone_la_pieza_como_si_lo_pidiera_el_dueno(self):
        self._guardar_solo_con_atajo()
        with mock.patch.object(comandos_en_vivo, "anunciar_con_sonido") as avisar:
            comandos_en_vivo.disparar(self.frame, 3, ahora=0)
        self.frame._capa_video.agregar_comando.assert_called_once()
        avisar.assert_not_called()

    def test_el_mismo_comando_escrito_en_el_chat_no_responde(self):
        self._guardar_solo_con_atajo()
        self._encolar("!risa")
        self.frame._capa_video.agregar_comando.assert_not_called()

    def test_sin_comando_en_ese_numero_avisa_con_el_sonido_de_error(self):
        self._guardar_solo_con_atajo()
        with mock.patch.object(comandos_en_vivo, "anunciar_con_sonido") as avisar:
            comandos_en_vivo.disparar(self.frame, 2, ahora=0)
        avisar.assert_called_once_with(
            "Ningún comando usa Ctrl+Alt+Mayús+2", "error")

    def test_sin_directo_ni_prueba_avisa_y_no_hace_nada_mas(self):
        self._guardar_solo_con_atajo()
        self.frame._conectado = False
        with mock.patch.object(comandos_en_vivo, "anunciar_con_sonido") as avisar:
            comandos_en_vivo.disparar(self.frame, 3, ahora=0)
        avisar.assert_called_once_with(
            "Conecta un directo para usar los atajos de los comandos", "error")
        self.frame._capa_video.agregar_comando.assert_not_called()

    def test_con_la_prueba_sin_directo_el_atajo_funciona(self):
        self._guardar_solo_con_atajo()
        self.frame._conectado = False
        self.frame._ensayo = True
        with mock.patch.object(comandos_en_vivo, "anunciar_con_sonido") as avisar:
            comandos_en_vivo.disparar(self.frame, 3, ahora=0)
        self.frame._capa_video.agregar_comando.assert_called_once()
        avisar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
