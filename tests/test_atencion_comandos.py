# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué responde la app a un mensaje del chat con un comando.

Puro: sin wx, sin captura y con la hora como argumento.
"""

import unittest

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.sonidos_eventos import ROL_MODERADOR
from guyrapu.interaction import atencion, comandos
from guyrapu.interaction.evento import EventoDirecto


def _evento(texto, autor="Ana", autor_id="1", roles=frozenset(),
            plataforma=plataformas.YOUTUBE):
    return EventoDirecto(
        plataforma=plataforma, autor_id=autor_id, autor=autor,
        roles=roles, tipo=TIPO_TEXTO, texto=texto, monto="")


def _comando(nombre="saludo", respuesta="Hola", **cambios):
    datos = {"nombre": nombre, "alias": (), "respuesta": respuesta}
    datos.update(cambios)
    return comandos.Comando(**datos)


def _lista(**cambios):
    datos = {"nombre": "commands", "alias": ("comandos",),
             "respuesta": "Comandos: {lista}.", "lista": True}
    datos.update(cambios)
    return comandos.Comando(**datos)


class TestMedio(unittest.TestCase):

    def test_la_respuesta_lleva_el_nombre_del_medio_del_comando(self):
        respuesta = atencion.Atencion([_comando(medio="fuegos")]).atender(
            _evento("!saludo"), 0)
        self.assertEqual(respuesta.medio, "fuegos")


class TestPermisoYEsperas(unittest.TestCase):

    def test_un_comando_activo_responde_y_anota_el_uso(self):
        atencion_ = atencion.Atencion([_comando()])
        self.assertEqual(atencion_.atender(_evento("!saludo"), 0).texto,
                         "Hola")
        self.assertIsNone(atencion_.atender(_evento("!saludo"), 4))
        self.assertIsNotNone(atencion_.atender(
            _evento("!saludo", autor="Bea", autor_id="2"), 5))

    def test_sin_permiso_no_responde_ni_anota(self):
        atencion_ = atencion.Atencion([
            _comando(permiso="lista", nombres=("Ana",))])
        self.assertIsNone(atencion_.atender(
            _evento("!saludo", autor="Bea", autor_id="2"), 0))
        self.assertIsNotNone(atencion_.atender(_evento("!saludo"), 0))

    def test_en_espera_por_persona_no_responde(self):
        atencion_ = atencion.Atencion([_comando()])
        self.assertIsNotNone(atencion_.atender(_evento("!saludo"), 0))
        self.assertIsNone(atencion_.atender(_evento("!saludo"), 29))
        self.assertIsNotNone(atencion_.atender(_evento("!saludo"), 30))

    def test_un_comando_pausado_no_responde(self):
        atencion_ = atencion.Atencion([_comando(activo=False)])
        self.assertIsNone(atencion_.atender(_evento("!saludo"), 0))


class TestVariablesYContador(unittest.TestCase):

    def test_reemplaza_usuario_texto_y_contador(self):
        atencion_ = atencion.Atencion([
            _comando(respuesta="Hola {usuario} ({contador}): {texto}")])
        respuesta = atencion_.atender(
            _evento("!saludo " + "x" * 120), 0)
        self.assertEqual(respuesta.texto,
                         "Hola Ana (1): " + "x" * 100)

    def test_el_contador_sube_por_comando_en_la_sesion(self):
        atencion_ = atencion.Atencion([_comando(respuesta="{contador}")])
        equipo = frozenset({ROL_MODERADOR})
        self.assertEqual(atencion_.atender(
            _evento("!saludo", roles=equipo), 0).texto, "1")
        self.assertEqual(atencion_.atender(
            _evento("!saludo", roles=equipo), 0).texto, "2")


class TestComandosDeLaApp(unittest.TestCase):

    def _atencion(self, **cambios):
        return atencion.Atencion([
            _comando("discord", "D"), _comando("redes", "R"),
            _comando("pausado", "P", activo=False), _lista(**cambios)])

    def test_lista_los_activos_en_su_orden_por_palabra_o_alias(self):
        for texto in ("!commands", "!comandos"):
            with self.subTest(texto=texto):
                respuesta = self._atencion().atender(_evento(texto), 0)
                self.assertEqual(
                    (respuesta.texto, respuesta.al_video, respuesta.al_chat,
                     respuesta.estilo, respuesta.segundos),
                    ("Comandos: !discord, !redes.", True, False, "", 8))

    def test_usa_el_texto_el_destino_el_estilo_y_los_segundos_guardados(self):
        respuesta = self._atencion(
            respuesta="Mira: {lista}.", destino="ambos", estilo="banda",
            segundos=12).atender(_evento("!commands"), 0,
                                 chat_disponible=True)
        self.assertEqual(
            (respuesta.texto, respuesta.al_video, respuesta.al_chat,
             respuesta.estilo, respuesta.segundos),
            ("Mira: !discord, !redes.", True, True, "banda", 12))

    def test_un_comando_fuera_de_la_lista_no_aparece(self):
        atencion_ = atencion.Atencion([
            _comando("discord", "D"),
            _comando("redes", "R", en_lista=False), _lista()])
        respuesta = atencion_.atender(_evento("!commands"), 0)
        self.assertEqual(respuesta.texto, "Comandos: !discord.")

    def test_sin_comandos_en_la_lista_no_responde(self):
        atencion_ = atencion.Atencion([
            _comando("discord", "D", en_lista=False), _lista()])
        self.assertIsNone(atencion_.atender(_evento("!commands"), 0))

    def test_el_comando_de_lista_pausado_no_responde(self):
        atencion_ = atencion.Atencion([
            _comando("discord", "D"), _lista(activo=False)])
        self.assertIsNone(atencion_.atender(_evento("!commands"), 0))

    def test_usa_las_esperas_del_comando_de_lista(self):
        atencion_ = self._atencion()
        self.assertIsNotNone(atencion_.atender(_evento("!commands"), 0))
        self.assertIsNone(atencion_.atender(
            _evento("!commands", autor="Bea", autor_id="2"), 4))
        self.assertIsNotNone(atencion_.atender(
            _evento("!commands", autor="Bea", autor_id="2"), 5))
        self.assertIsNone(atencion_.atender(_evento("!commands"), 5))


class TestDestinoDelChat(unittest.TestCase):

    def test_en_youtube_con_chat_disponible_va_al_chat(self):
        atencion_ = atencion.Atencion([_comando(destino="chat")])
        respuesta = atencion_.atender(
            _evento("!saludo"), 0, chat_disponible=True)
        self.assertTrue(respuesta.al_chat)
        self.assertFalse(respuesta.al_video)

    def test_desde_tiktok_un_destino_chat_sale_en_el_video(self):
        atencion_ = atencion.Atencion([_comando(destino="chat")])
        respuesta = atencion_.atender(
            _evento("!saludo", plataforma=plataformas.TIKTOK), 0,
            chat_disponible=True)
        self.assertFalse(respuesta.al_chat)
        self.assertTrue(respuesta.al_video)


class TestFrenoDeCuota(unittest.TestCase):

    def _equipo(self):
        return _evento("!saludo", roles=frozenset({ROL_MODERADOR}))

    def test_una_respuesta_al_chat_cada_treinta_segundos(self):
        atencion_ = atencion.Atencion([_comando(destino="chat")])
        self.assertTrue(atencion_.atender(
            self._equipo(), 0, chat_disponible=True).al_chat)
        segunda = atencion_.atender(
            self._equipo(), 29, chat_disponible=True)
        self.assertFalse(segunda.al_chat)
        self.assertTrue(segunda.al_video)
        self.assertFalse(segunda.freno_cuota)
        self.assertTrue(atencion_.atender(
            self._equipo(), 30, chat_disponible=True).al_chat)

    def test_con_poca_cuota_no_se_manda_y_lo_dice(self):
        atencion_ = atencion.Atencion([_comando(destino="chat")])
        respuesta = atencion_.atender(
            self._equipo(), 0, chat_disponible=True, cuota_baja=True)
        self.assertFalse(respuesta.al_chat)
        self.assertTrue(respuesta.al_video)
        self.assertTrue(respuesta.freno_cuota)


class TestEco(unittest.TestCase):

    def test_no_se_atiende_su_propia_respuesta_dentro_de_los_120_segundos(self):
        atencion_ = atencion.Atencion([
            _comando("eco", "!otro", destino="chat"),
            _comando("otro", "Contestado")])
        atencion_.atender(_evento("!eco"), 0, chat_disponible=True)
        self.assertIsNone(atencion_.atender(
            _evento("  !OTRO  "), 119))
        self.assertIsNotNone(atencion_.atender(
            _evento("  !OTRO  "), 121))


class TestFiltroDelPublico(unittest.TestCase):

    def test_tapa_el_autor_y_el_texto_bloqueados(self):
        atencion_ = atencion.Atencion([
            _comando(respuesta="Hola {usuario}: {texto}")])
        atencion_.fijar_palabras_bloqueadas(["tonto"])
        respuesta = atencion_.atender(
            _evento("!saludo eres tonto", autor="Tonto"), 0)
        self.assertEqual(respuesta.texto, "Hola ***: eres ***")

    def test_un_texto_casi_todo_simbolos_no_sale(self):
        atencion_ = atencion.Atencion([
            _comando(respuesta="Hola {usuario}: {texto}")])
        respuesta = atencion_.atender(
            _evento("!saludo !!!!!!!!", autor="Ana"), 0)
        self.assertEqual(respuesta.texto, "Hola Ana: ")

    def test_la_respuesta_escrita_por_el_streamer_no_se_filtra(self):
        atencion_ = atencion.Atencion([
            _comando(respuesta="Hola tonto {usuario}")])
        atencion_.fijar_palabras_bloqueadas(["tonto"])
        respuesta = atencion_.atender(_evento("!saludo", autor="Ana"), 0)
        self.assertEqual(respuesta.texto, "Hola tonto Ana")


class TestListaConUbicacionYAtajo(unittest.TestCase):

    def _respuesta(self, *comandos):
        return atencion.Atencion([*comandos, _lista()]).atender(
            _evento("!comandos"), 0)

    def test_los_de_cualquiera_se_nombran_sin_el_signo(self):
        respuesta = self._respuesta(
            _comando("risa", "R", ubicacion="cualquiera"))
        self.assertEqual(respuesta.texto, "Comandos: risa.")

    def test_los_de_solo_con_el_atajo_no_se_nombran(self):
        self.assertIsNone(self._respuesta(
            _comando("risa", "R", permiso="solo_atajo", atajo=3)))


if __name__ == "__main__":
    unittest.main()
