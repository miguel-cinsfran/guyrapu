# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del chat adicional de TikTok y de su vista."""

import queue
import threading
import unittest
from unittest import mock

from guyrapu.capture import chat_adicional, tiktok_captura
from guyrapu.capture.conexion import Conexiones
from guyrapu.ui import gui


class VistaGuiFalsa:
    activa = True
    conexion_propia = False

    def __init__(self):
        self.mensajes = []
        self.anuncios = []

    def agregar_mensaje(self, *args, **kwargs):
        self.mensajes.append((args, kwargs))
        return True

    def anunciar(self, texto):
        self.anuncios.append(texto)
        return True

    def set_conectado(self, conectado, sonido=None):
        return True

    def set_titulo(self, titulo):
        return True


class HiloInerte:
    def start(self):
        return None


class HiloEjecuta:
    def __init__(self, objetivo):
        self.objetivo = objetivo

    def start(self):
        self.objetivo()


def crear_hilo_inerte(*args, **kwargs):
    return HiloInerte()


def crear_hilo_ejecuta(objetivo, nombre, **kwargs):
    return HiloEjecuta(objetivo)


def _chat(vista, crear_hilo=crear_hilo_inerte):
    return chat_adicional.ChatAdicional(
        queue.Queue(), {}, mock.Mock(), threading.Event(),
        crear_hilo=crear_hilo, vista_gui=vista)


class TestVistaAdicional(unittest.TestCase):

    def test_solo_deja_pasar_mensajes_y_anuncios(self):
        vista_gui = VistaGuiFalsa()
        vista = chat_adicional.VistaAdicional(vista=vista_gui)
        vista.agregar_mensaje("Ana", "hola", "12:00", "text", "", "C",
                              plataforma="tiktok", rol="")
        vista.anunciar("Conectando al directo.")
        vista.set_titulo("Título")
        vista.set_metadatos({"canal": "x"})
        vista.configurar_tiktok("pepe", "url")
        vista.set_espectadores(3)
        vista.set_tipo_video("live", "v")
        vista.fallo_video({})
        vista.registrar_historial("tiktok", "pepe", "url", "t", "c", True)
        vista.url_invalida()
        self.assertEqual(len(vista_gui.mensajes), 1)
        self.assertEqual(vista_gui.anuncios, ["TikTok: Conectando al directo."])

    def test_conectado_lo_anuncia_con_prefijo(self):
        vista_gui = VistaGuiFalsa()
        vista = chat_adicional.VistaAdicional(vista=vista_gui)
        vista.set_conectado(True)
        self.assertEqual(
            vista_gui.anuncios,
            ["TikTok: Conectado al directo. Leyendo el chat."])


class TestConectarAdicional(unittest.TestCase):

    def setUp(self):
        chat_adicional.usar(None)
        self.addCleanup(chat_adicional.usar, None)

    def test_conecta_por_url_y_por_usuario_suelto(self):
        for entrada in ("https://www.tiktok.com/@pepe/live", "@pepe", "pepe"):
            with self.subTest(entrada=entrada):
                chat_adicional.usar(None)
                conexiones = Conexiones(
                    queue.Queue(), {}, mock.Mock(), threading.Event(),
                    crear_hilo=crear_hilo_inerte, vista=VistaGuiFalsa())
                conexiones._activo = True
                self.assertTrue(conexiones.conectar_adicional(entrada))
                self.assertTrue(chat_adicional.activo())

    def test_pide_la_captura_de_tiktok(self):
        conexiones = Conexiones(
            queue.Queue(), {}, mock.Mock(), threading.Event(),
            crear_hilo=crear_hilo_ejecuta, vista=VistaGuiFalsa())
        conexiones._activo = True
        with mock.patch.object(tiktok_captura, "capturar_con_reconexion") as captura:
            self.assertTrue(conexiones.conectar_adicional("@pepe"))
        captura.assert_called_once()
        self.assertEqual(captura.call_args.args[0], "pepe")

    def test_sin_principal_no_conecta_y_avisa(self):
        vista_gui = VistaGuiFalsa()
        chat = _chat(vista_gui)
        with mock.patch.object(tiktok_captura, "capturar_con_reconexion") as captura, \
                mock.patch.object(chat_adicional._snd, "reproducir") as sonido:
            self.assertFalse(chat.conectar("@pepe", principal_activo=lambda: False))
        captura.assert_not_called()
        sonido.assert_called_once_with("error")
        self.assertEqual(len(vista_gui.anuncios), 1)
        self.assertTrue(vista_gui.anuncios[0].startswith("TikTok: "))

    def test_el_mismo_usuario_no_se_conecta_dos_veces(self):
        vista_gui = VistaGuiFalsa()
        chat = _chat(vista_gui)
        with mock.patch.object(tiktok_captura, "capturar_con_reconexion"), \
                mock.patch.object(chat_adicional._snd, "reproducir"):
            self.assertTrue(chat.conectar("@pepe", principal_activo=lambda: True))
            self.assertFalse(chat.conectar("@pepe", principal_activo=lambda: True))
        self.assertEqual(len(vista_gui.anuncios), 1)
        self.assertTrue(vista_gui.anuncios[0].startswith("TikTok: "))


class TestEstadosDelAdicional(unittest.TestCase):

    def setUp(self):
        chat_adicional.usar(None)
        self.addCleanup(chat_adicional.usar, None)

    def test_los_sonidos_son_los_de_tiktok_y_todo_lleva_prefijo(self):
        vista_gui = VistaGuiFalsa()
        chat = _chat(vista_gui, crear_hilo_ejecuta)

        def captura(usuario, config, parada, **kwargs):
            kwargs["on_estado"]("conectando", "Conectando al directo.")
            kwargs["on_estado"]("conectado", "Conectado.")
            kwargs["on_estado"]("reintentando", "Reintentando.")
            kwargs["on_estado"]("fin_directo", "El directo terminó.")

        with mock.patch.object(tiktok_captura, "capturar_con_reconexion",
                               side_effect=captura), \
                mock.patch.object(chat_adicional._snd, "reproducir") as sonido:
            self.assertTrue(chat.conectar("@pepe",
                                          principal_activo=lambda: True))
        self.assertEqual([llamada.args[0] for llamada in sonido.call_args_list],
                         ["conectando", "conectado", "conectando", "fin_directo"])
        self.assertTrue(vista_gui.anuncios)
        for anuncio in vista_gui.anuncios:
            self.assertTrue(anuncio.startswith("TikTok: "), anuncio)


class TestPararConElPrincipal(unittest.TestCase):

    def setUp(self):
        chat_adicional.usar(None)
        self.addCleanup(chat_adicional.usar, None)

    def test_desconectar_el_principal_para_el_adicional(self):
        conexiones = Conexiones(
            queue.Queue(), {}, mock.Mock(), threading.Event(),
            crear_hilo=crear_hilo_inerte, vista=VistaGuiFalsa())
        with mock.patch.object(chat_adicional, "detener") as detener:
            conexiones.desconectar()
        detener.assert_called_once_with()

    def test_el_fin_del_principal_para_el_adicional(self):
        conexiones = Conexiones(
            queue.Queue(), {}, mock.Mock(), threading.Event(),
            crear_hilo=crear_hilo_inerte, vista=VistaGuiFalsa())
        sesion = conexiones.registro.abrir()
        conexiones._activo = True
        with mock.patch.object(chat_adicional, "detener") as detener:
            conexiones._estado_youtube(
                sesion.gen, "error_permanente", "El directo terminó.")
        detener.assert_called_once_with()

    def test_que_el_adicional_termine_no_toca_al_principal(self):
        principal = Conexiones(
            queue.Queue(), {}, mock.Mock(), threading.Event(),
            crear_hilo=crear_hilo_inerte, vista=VistaGuiFalsa())
        sesion = principal.registro.abrir()
        principal._activo = True
        chat = _chat(VistaGuiFalsa(), crear_hilo_ejecuta)

        def captura(usuario, config, parada, **kwargs):
            kwargs["on_estado"]("fin_directo", "El directo terminó.")

        with mock.patch.object(tiktok_captura, "capturar_con_reconexion",
                               side_effect=captura),                 mock.patch.object(chat_adicional._snd, "reproducir"):
            self.assertTrue(chat.conectar("@pepe",
                                          principal_activo=lambda: True))
        self.assertTrue(principal.registro.vigente(sesion.gen))
        self.assertTrue(principal.activo)

    def test_la_ventana_expone_el_metodo(self):
        self.assertTrue(hasattr(gui.VentanaPrincipal,
                                "conectar_chat_adicional"))


class TestEspectadoresDelAdicional(unittest.TestCase):

    def setUp(self):
        chat_adicional.usar(None)
        self.addCleanup(chat_adicional.usar, None)

    def _chat_activo(self):
        chat = _chat(VistaGuiFalsa())
        chat_adicional.usar(chat)
        chat._activo = True
        return chat

    def test_la_vista_guarda_los_espectadores_que_recibe(self):
        vista = chat_adicional.VistaAdicional(vista=VistaGuiFalsa())
        vista.set_espectadores(30, 120)
        self.assertEqual(vista.espectadores(), (30, 120))
        vista.set_espectadores(31)
        self.assertEqual(vista.espectadores(), (31, None))

    def test_la_funcion_de_modulo_devuelve_los_del_adicional_activo(self):
        chat = self._chat_activo()
        chat._vista.set_espectadores(30, 120)
        self.assertEqual(chat_adicional.espectadores(), (30, 120))

    def test_sin_adicional_activo_la_funcion_devuelve_none(self):
        self.assertIsNone(chat_adicional.espectadores())

    def test_detener_olvida_los_espectadores(self):
        chat = self._chat_activo()
        chat._vista.set_espectadores(30, 120)
        chat.detener()
        self.assertIsNone(chat._vista.espectadores())
        self.assertIsNone(chat_adicional.espectadores())

    def test_pararse_solo_olvida_los_espectadores(self):
        chat = self._chat_activo()
        chat._vista.set_espectadores(30, 120)
        chat._vista.set_conectado_si_existe(False)
        self.assertIsNone(chat._vista.espectadores())
        self.assertIsNone(chat_adicional.espectadores())


if __name__ == "__main__":
    unittest.main()
