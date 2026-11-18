# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El comando Probar de una tarjeta, común a las dos páginas."""

import unittest
from unittest import mock

from guyrapu.ui import probar_aviso


class _CapaFalsa:
    def __init__(self):
        self.llamadas = []

    def probar(self, texto, estilo, al_terminar):
        self.llamadas.append((texto, estilo, al_terminar))


class Base(unittest.TestCase):
    def setUp(self):
        self.sonidos = []
        parche = mock.patch.object(
            probar_aviso.sound_player, "reproducir",
            side_effect=self.sonidos.append)
        parche.start()
        self.addCleanup(parche.stop)
        self.capa = _CapaFalsa()
        self.marco = object()
        parche = mock.patch.object(
            probar_aviso.gui_envio_chat, "capa_de_video",
            return_value=self.capa)
        self.capa_de_video = parche.start()
        self.addCleanup(parche.stop)
        parche = mock.patch("guyrapu.ui.gui._gui_frame", self.marco)
        parche.start()
        self.addCleanup(parche.stop)
        self.anuncios = []
        parche = mock.patch.object(
            probar_aviso, "anunciar_con_sonido",
            side_effect=lambda frase, sonido: self.anuncios.append(
                (frase, sonido)))
        parche.start()
        self.addCleanup(parche.stop)
        self.avisos = []
        parche = mock.patch.object(
            probar_aviso.aviso_importante, "avisar",
            side_effect=lambda *args, **kwargs: self.avisos.append(
                (args, kwargs)))
        parche.start()
        self.addCleanup(parche.stop)

    def _terminar(self, frase, error=False):
        texto, _estilo, al_terminar = self.capa.llamadas[0]
        al_terminar(frase, error)
        return texto


class TestProbarAviso(Base):

    def test_p5_pide_espera_y_al_terminar_anuncia_la_revision(self):
        probar_aviso.probar("Hola", {"clave": "banda"})
        self.assertEqual(self.sonidos, ["espera"])
        self.capa_de_video.assert_called_once_with(self.marco)
        self.assertEqual(self.capa.llamadas[0][:2],
                         ("Hola", {"clave": "banda"}))
        self._terminar("Zona: Centro.", False)
        self.assertEqual(self.anuncios, [("Zona: Centro.", "listo")])
        self.assertEqual(self.avisos, [])

    def test_p5_un_error_abre_el_cuadro_con_su_sonido(self):
        probar_aviso.probar("Hola", {"clave": "banda"})
        self._terminar("Hay algo en el vídeo. Prueba cuando termine.", True)
        self.assertEqual(self.avisos, [
            (("Hay algo en el vídeo. Prueba cuando termine.", "error"),
             {"error": True})])
        self.assertEqual(self.anuncios, [])

    def test_p2_solo_chat_no_toca_la_capa_y_dice_que_iria_al_chat(self):
        probar_aviso.probar(None, None, al_chat="Hola")
        self.assertEqual(self.sonidos, ["espera"])
        self.capa_de_video.assert_not_called()
        self.assertEqual(self.anuncios, [("Iría al chat: Hola", "listo")])
        self.assertEqual(self.avisos, [])

    def test_p2_video_y_chat_termina_con_la_frase_del_chat(self):
        probar_aviso.probar("Hola", {"clave": "banda"}, al_chat="Hola")
        self._terminar("Zona: Centro.", False)
        self.assertEqual(self.anuncios,
                         [("Zona: Centro. Iría al chat: Hola", "listo")])


if __name__ == "__main__":
    unittest.main()
