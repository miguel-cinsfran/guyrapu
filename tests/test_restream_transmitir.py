# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de las opciones de transmisión con perfiles de Restream."""

import unittest

from guyrapu.restream import transmitir
from guyrapu.restream.canal_youtube import PLATAFORMA_YOUTUBE
from guyrapu.restream.perfiles import Perfil
from guyrapu.restream.api import Canal


def _perfil(nombre="Uno", orientacion="vertical", canales=(1,), youtube=False,
            chat=""):
    return Perfil(nombre=nombre, canales=canales, orientacion=orientacion,
                  youtube=youtube, chat=chat)


def _canal(identificador, plataforma, activo=True, url="", nombre="",
           plataforma_id=0):
    return Canal(id=identificador, plataforma_id=plataforma_id,
                 plataforma=plataforma, nombre=nombre or f"canal {identificador}",
                 url=url, activo=activo)


class TestOpciones(unittest.TestCase):

    def test_sin_perfiles_solo_los_destinos_de_obs(self):
        self.assertEqual(transmitir.opciones([]), ("TikTok", "YouTube"))

    def test_con_uno_y_dos_perfiles_respeta_el_orden(self):
        uno = _perfil("Uno")
        dos = _perfil("Dos", "horizontal", (2,))
        self.assertEqual(transmitir.opciones([uno]),
                         ("TikTok", "YouTube", "restream:Uno"))
        self.assertEqual(transmitir.opciones([uno, dos]),
                         ("TikTok", "YouTube", "restream:Uno",
                          "restream:Dos"))

    def test_texto_visible_de_cada_opcion(self):
        self.assertEqual(transmitir.texto("TikTok"), "TikTok")
        self.assertEqual(transmitir.texto("YouTube"), "YouTube")
        self.assertEqual(transmitir.texto("restream:Uno"),
                         "Restream: Uno")

    def test_es_opcion_valida(self):
        for opcion in ("TikTok", "YouTube", "restream:Uno"):
            with self.subTest(opcion=opcion):
                self.assertTrue(transmitir.es_opcion_valida(opcion))
        for opcion in ("", "Twitch", "restream:", None):
            with self.subTest(opcion=opcion):
                self.assertFalse(transmitir.es_opcion_valida(opcion))

    def test_es_restream_y_su_nombre(self):
        self.assertTrue(transmitir.es_restream("restream:Uno"))
        self.assertEqual(transmitir.nombre_perfil("restream:Uno"), "Uno")
        self.assertFalse(transmitir.es_restream("TikTok"))
        self.assertEqual(transmitir.nombre_perfil("TikTok"), "")


class TestDestinoObs(unittest.TestCase):

    def test_destinos_de_obs_sin_perfil(self):
        self.assertEqual(transmitir.destino_obs("TikTok", []), "TikTok")
        self.assertEqual(transmitir.destino_obs("YouTube", []), "YouTube")

    def test_vertical_da_tiktok_y_horizontal_da_youtube(self):
        vertical = _perfil("Vertical", "vertical")
        horizontal = _perfil("Horizontal", "horizontal")
        self.assertEqual(
            transmitir.destino_obs("restream:Vertical",
                                   [vertical, horizontal]),
            "TikTok")
        self.assertEqual(
            transmitir.destino_obs("restream:Horizontal",
                                   [vertical, horizontal]),
            "YouTube")

    def test_p5_ambas_da_youtube(self):
        ambas = _perfil("Ambas", "ambas", canales=(1,), youtube=True)
        self.assertEqual(
            transmitir.destino_obs("restream:Ambas", [ambas]), "YouTube")

    def test_perfil_de_una_opcion(self):
        uno = _perfil("Uno")
        dos = _perfil("Dos")
        self.assertIs(transmitir.perfil_de_opcion("restream:Dos", [uno, dos]),
                      dos)
        self.assertIsNone(transmitir.perfil_de_opcion("restream:Tres", [uno]))
        self.assertIsNone(transmitir.perfil_de_opcion("TikTok", [uno]))


class TestPlanDeCanales(unittest.TestCase):

    def test_los_que_ya_estan_bien_no_se_tocan(self):
        perfil = _perfil(canales=(1, 3))
        canales = [_canal(1, "YouTube", True), _canal(2, "YouTube", False),
                   _canal(3, "TikTok", True)]
        self.assertEqual(transmitir.plan_canales(perfil, canales), ())

    def test_activa_los_del_perfil_y_desactiva_los_demas(self):
        perfil = _perfil(canales=(1, 3))
        canales = [_canal(1, "YouTube", False), _canal(2, "YouTube", True),
                   _canal(3, "TikTok", False)]
        cambios = transmitir.plan_canales(perfil, canales)
        self.assertEqual(
            [(cambio.canal_id, cambio.activo, cambio.antes) for cambio in cambios],
            [(1, True, False), (2, False, True), (3, True, False)])

    def test_p6_ambas_apaga_el_youtube_de_restream_y_enciende_los_demas(self):
        perfil = _perfil("Ambas", "ambas", canales=(1, 2), youtube=True)
        canales = [
            _canal(1, "YouTube", True, plataforma_id=PLATAFORMA_YOUTUBE),
            _canal(2, "TikTok", False),
        ]
        cambios = transmitir.plan_canales(perfil, canales)
        self.assertEqual(
            [(cambio.canal_id, cambio.activo, cambio.antes)
             for cambio in cambios],
            [(1, False, True), (2, True, False)])

    def test_aplicar_el_plan_deja_activos_solo_los_del_perfil(self):
        perfil = _perfil(canales=(1, 3, 9))
        base = [_canal(1, "YouTube", True), _canal(2, "YouTube", True),
                _canal(3, "TikTok", False), _canal(4, "YouTube", False)]
        activos = {canal.id: canal.activo for canal in base}
        for cambio in transmitir.plan_canales(perfil, base):
            activos[cambio.canal_id] = cambio.activo
        self.assertEqual({canal_id for canal_id, activo in activos.items()
                          if activo}, {1, 3})


class TestChat(unittest.TestCase):

    def test_p10_con_youtube_y_chat_vacio_el_chat_es_youtube(self):
        perfil = _perfil(canales=(1,), youtube=True)
        canales = [_canal(1, "TikTok")]
        self.assertEqual(transmitir.chat_del_perfil(perfil, canales),
                         "youtube")

    def test_p10_sin_youtube_y_con_tiktok_el_chat_es_tiktok(self):
        perfil = _perfil(canales=(1,), youtube=False)
        canales = [_canal(1, "TikTok")]
        self.assertEqual(transmitir.chat_del_perfil(perfil, canales),
                         "tiktok")

    def test_p10_sin_youtube_ni_tiktok_no_hay_chat(self):
        perfil = _perfil(canales=(1,), youtube=False)
        canales = [_canal(1, "YouTube")]
        self.assertEqual(transmitir.chat_del_perfil(perfil, canales), "")

    def test_el_chat_elegido_gana_sobre_el_automatico(self):
        perfil = _perfil(canales=(1,), youtube=True, chat="tiktok")
        canales = [_canal(1, "TikTok")]
        self.assertEqual(transmitir.chat_del_perfil(perfil, canales),
                         "tiktok")

    def test_ambos_con_youtube_el_chat_principal_es_youtube(self):
        perfil = _perfil(canales=(1,), youtube=True, chat="ambos")
        canales = [_canal(1, "TikTok")]
        self.assertEqual(transmitir.chat_del_perfil(perfil, canales),
                         "youtube")

    def test_ambos_sin_youtube_sigue_el_automatico(self):
        perfil = _perfil(canales=(1,), youtube=False, chat="ambos")
        canales = [_canal(1, "TikTok")]
        self.assertEqual(transmitir.chat_del_perfil(perfil, canales),
                         "tiktok")

    def test_chat_youtube_y_tiktok_con_y_sin_youtube(self):
        canales = [_canal(1, "TikTok")]
        for youtube in (True, False):
            with self.subTest(youtube=youtube):
                con_youtube = _perfil(canales=(1,), youtube=youtube,
                                      chat="youtube")
                con_tiktok = _perfil(canales=(1,), youtube=youtube,
                                     chat="tiktok")
                self.assertEqual(
                    transmitir.chat_del_perfil(con_youtube, canales),
                    "youtube")
                self.assertEqual(
                    transmitir.chat_del_perfil(con_tiktok, canales), "tiktok")

    def test_vacio_sigue_el_automatico_con_y_sin_youtube(self):
        canales = [_canal(1, "TikTok")]
        con_youtube = _perfil(canales=(1,), youtube=True)
        sin_youtube = _perfil(canales=(1,), youtube=False)
        self.assertEqual(
            transmitir.chat_del_perfil(con_youtube, canales), "youtube")
        self.assertEqual(
            transmitir.chat_del_perfil(sin_youtube, canales), "tiktok")


class TestTiktokAdicional(unittest.TestCase):

    def _canales(self):
        return [_canal(1, "TikTok", url="https://www.tiktok.com/@amigo")]

    def test_con_ambos_youtube_y_usuario_devuelve_el_usuario(self):
        perfil = _perfil(canales=(1,), youtube=True, chat="ambos")
        self.assertEqual(
            transmitir.tiktok_adicional(perfil, self._canales()), "amigo")

    def test_con_ambos_youtube_y_sin_usuario_devuelve_vacio(self):
        perfil = _perfil(canales=(1,), youtube=True, chat="ambos")
        canales = [_canal(1, "TikTok", url="", nombre="")]
        self.assertEqual(transmitir.tiktok_adicional(perfil, canales), "")

    def test_con_ambos_sin_youtube_devuelve_vacio(self):
        perfil = _perfil(canales=(1,), youtube=False, chat="ambos")
        self.assertEqual(transmitir.tiktok_adicional(perfil,
                                                     self._canales()), "")

    def test_con_otro_chat_devuelve_vacio(self):
        for chat in ("", "youtube", "tiktok"):
            with self.subTest(chat=chat):
                perfil = _perfil(canales=(1,), youtube=True, chat=chat)
                self.assertEqual(
                    transmitir.tiktok_adicional(perfil, self._canales()), "")


class TestUsuarioTikTok(unittest.TestCase):

    def test_sale_de_la_direccion_del_primer_tiktok_del_perfil(self):
        perfil = _perfil(canales=(1, 2))
        canales = [
            _canal(1, "YouTube", url="https://youtube.com/@canal"),
            _canal(2, "TikTok", url="https://www.tiktok.com/@amigo"),
        ]
        self.assertEqual(transmitir.usuario_tiktok(perfil, canales), "amigo")

    def test_respeta_el_orden_del_perfil(self):
        perfil = _perfil(canales=(2, 1))
        canales = [
            _canal(1, "TikTok", url="https://www.tiktok.com/@primero"),
            _canal(2, "TikTok", url="https://www.tiktok.com/@segundo"),
        ]
        self.assertEqual(transmitir.usuario_tiktok(perfil, canales), "segundo")

    def test_sin_direccion_prueba_con_el_nombre(self):
        perfil = _perfil(canales=(1,))
        canales = [_canal(1, "TikTok", url="", nombre="@otro")]
        self.assertEqual(transmitir.usuario_tiktok(perfil, canales), "otro")

    def test_sin_tiktok_devuelve_vacio(self):
        perfil = _perfil(canales=(1,))
        canales = [_canal(1, "YouTube", url="https://youtube.com/@canal")]
        self.assertEqual(transmitir.usuario_tiktok(perfil, canales), "")

    def test_canales_del_perfil_respeta_el_orden_y_salta_los_ajenos(self):
        perfil = _perfil(canales=(3, 1, 9))
        canales = [_canal(1, "YouTube"), _canal(2, "YouTube"),
                   _canal(3, "TikTok")]
        self.assertEqual([canal.id for canal in
                          transmitir.canales_del_perfil(perfil, canales)],
                         [3, 1])


if __name__ == "__main__":
    unittest.main()
