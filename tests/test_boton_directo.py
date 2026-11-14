# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del botón directo de transmisión.

Las clases con ventana abren ventanas de verdad y aquí no se corren:
aquí solo se corre TestGuardarDestino, sin ventana.
"""

import queue
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.ui import gui
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.ventanas_prueba import app_de_prueba, destruir


class TestGuardarDestino(unittest.TestCase):
    # Sin ventana: _guardar_destino_transmision solo toca el dict y el INI.

    def _frame(self):
        frame = gui.VentanaPrincipal.__new__(gui.VentanaPrincipal)
        frame._config = {}
        return frame

    def test_destino_valido_se_guarda(self):
        frame = self._frame()
        with mock.patch.object(gui, "guardar_opcion") as guardar:
            resultado = frame._guardar_destino_transmision("TikTok")
        self.assertEqual(resultado, "TikTok")
        self.assertEqual(frame._config["transmision_destino"], "TikTok")
        guardar.assert_called_once_with(
            gui.RUTA_CONFIG, "transmision", "destino", "TikTok")

    def test_destino_invalido_se_guarda_vacio(self):
        frame = self._frame()
        with mock.patch.object(gui, "guardar_opcion") as guardar:
            resultado = frame._guardar_destino_transmision("Twitch")
        self.assertEqual(resultado, "")
        self.assertEqual(frame._config["transmision_destino"], "")
        guardar.assert_called_once_with(
            gui.RUTA_CONFIG, "transmision", "destino", "")


class TestActualizarDeteniendoSinVentana(unittest.TestCase):
    # Sin ventana: el botón es un doble, así se mira lo que dice sin crearlo.

    def _boton(self):
        from guyrapu.ui import boton_directo
        boton = boton_directo.BotonDirecto.__new__(boton_directo.BotonDirecto)
        boton._conectar = mock.Mock()
        boton._comando = mock.Mock()
        boton._marco = mock.Mock()
        boton._marco.mi_directo = None
        boton.boton = mock.Mock()
        boton.boton.GetParent.return_value = mock.Mock()
        boton.boton.HasFocus.return_value = False
        return boton

    def test_actualizar_con_deteniendo_cambia_etiqueta_y_guarda_el_estado(self):
        boton = self._boton()
        boton.actualizar(False, False, False, True, deteniendo=True)
        boton._comando.sincronizar.assert_called_once_with(True, True)
        boton.boton.SetLabel.assert_called_once_with("Finalizando el directo")
        boton.boton.SetName.assert_called_once_with(
            "Finalizando el directo, esperando a OBS")
        boton.boton.Hide.assert_not_called()

    def test_actualizar_sin_deteniendo_vuelve_a_finalizar(self):
        boton = self._boton()
        boton.actualizar(False, False, False, True)
        boton._comando.sincronizar.assert_called_once_with(True, False)
        boton.boton.SetLabel.assert_called_once_with("&Finalizar directo")

    def test_actualizar_copia_la_etiqueta_al_comando_del_menu(self):
        boton = self._boton()
        item = mock.Mock()
        boton._marco.mi_directo = item
        boton.actualizar(False, False, True, False)
        item.SetItemLabel.assert_called_once_with("Transm&itir en directo…")

    def test_el_comando_lleva_puntos_al_iniciar_y_no_al_detener(self):
        for argumentos, etiqueta in (
                ((False, False, True, False), "Transm&itir en directo…"),
                ((False, False, True, True), "&Finalizar directo"),
                ((False, False, True, True, True), "Finalizando el directo")):
            with self.subTest(etiqueta=etiqueta):
                boton = self._boton()
                item = mock.Mock()
                boton._marco.mi_directo = item
                boton.actualizar(*argumentos)
                item.SetItemLabel.assert_called_once_with(etiqueta)

    def test_actualizar_deshabilita_el_comando_cuando_el_boton_se_oculta(self):
        boton = self._boton()
        item = mock.Mock()
        boton._marco.mi_directo = item
        boton.actualizar(True, False, False, False)
        boton.boton.Hide.assert_called_once()
        item.Enable.assert_called_once_with(False)

    def test_actualizar_vuelve_a_habilitar_el_comando(self):
        boton = self._boton()
        item = mock.Mock()
        boton._marco.mi_directo = item
        boton.actualizar(False, False, False, False)
        item.Enable.assert_called_once_with(True)


class TestPulsarDelegaSinVentana(unittest.TestCase):
    # Sin ventana: pulsar es el único camino que comparten el botón y el menú.

    def test_pulsar_delega_en_el_comando_con_el_marco(self):
        from guyrapu.ui import boton_directo
        boton = boton_directo.BotonDirecto.__new__(boton_directo.BotonDirecto)
        boton._comando = mock.Mock()
        boton._marco = mock.Mock()
        boton.pulsar()
        boton._comando.pulsar.assert_called_once_with(boton._marco)

    def test_al_pulsar_delega_en_pulsar(self):
        from guyrapu.ui import boton_directo
        boton = boton_directo.BotonDirecto.__new__(boton_directo.BotonDirecto)
        with mock.patch.object(boton, "pulsar") as pulsar:
            boton._al_pulsar(mock.Mock())
        pulsar.assert_called_once_with()


class TestMenuDirectoSinVentana(unittest.TestCase):
    # Sin ventana: el comando del menú llama a pulsar, el mismo camino.

    def _frame(self, boton):
        from guyrapu.ui import menu_transmision

        class Menu:
            def __init__(self):
                self.items = []

            def Append(self, *args):
                item = mock.Mock()
                self.items.append(item)
                return item

            def AppendCheckItem(self, *args):
                item = mock.Mock()
                self.items.append(item)
                return item

            def AppendSeparator(self):
                self.items.append(None)

        enlaces = {}
        frame = mock.Mock()
        frame._config = {"grabar_al_transmitir": False}
        frame._accel.return_value = ""
        frame._bind_menu.side_effect = lambda item, fn, *a: enlaces.__setitem__(
            item, (fn, a))
        frame._boton_directo = boton
        with mock.patch.object(menu_transmision.wx, "Menu", Menu):
            menu_transmision.construir(frame, mock.Mock())
        return frame, enlaces

    def test_elegir_mi_directo_llama_a_pulsar(self):
        boton = mock.Mock()
        frame, enlaces = self._frame(boton)
        fn, args = enlaces[frame.mi_directo]
        fn(*args)
        boton.pulsar.assert_called_once_with()


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestBotonDirectoVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _ventana(self, **config_extra):
        configuracion = {
            "atajos_raw": {}, "filtro_activo": "todos",
            "mostrar_botones_reproductor": False, "mostrar_metadatos": True,
            "mostrar_total_superchats": True, "overlay_activo": False,
            "programados_activo": False, "tiktok_usuario": "",
            "transmision_destino": "",
        }
        configuracion.update(config_extra)
        stats = SimpleNamespace(leidos=0, superchats=0, descartados=0)
        worker = SimpleNamespace(get_rate=lambda: 0, get_volume=lambda: 100)
        with mock.patch.object(gui.diagnostico, "crear_hilo"):
            frame = gui.VentanaPrincipal(None, configuracion, queue.Queue(),
                                    stats, worker, threading.Event())
        self.addCleanup(destruir, frame)
        frame.ShowWithoutActivating()
        gui.wx.Yield()
        return frame

    @staticmethod
    def _sin_reproductor_ni_comentarios(frame):
        # configurar_tiktok no necesita el reproductor de verdad para lo
        # que aquí se comprueba (visibilidad del botón).
        frame._rep_panel = mock.Mock()
        frame._com_panel = mock.Mock()

    def test_en_inicio_hijo_del_panel_visible_tras_conectar_y_con_nombre(self):
        frame = self._ventana()
        boton = frame._boton_directo.boton
        self.assertIs(boton.GetParent(), frame._panel_principal)
        self.assertTrue(boton.IsShown())
        hijos = list(frame._panel_principal.GetChildren())
        self.assertEqual(hijos.index(boton),
                         hijos.index(frame.btn_conectar) + 1)
        self.assertEqual(boton.GetLabel(), "Transm&itir en directo")
        self.assertEqual(boton.GetName(), "Transmitir en directo")

    def test_con_usuario_ajeno_queda_oculto(self):
        frame = self._ventana(tiktok_usuario="mio")
        self._sin_reproductor_ni_comentarios(frame)
        frame.set_conectado(True)
        gui.wx.Yield()
        frame.configurar_tiktok("otro", "http://flujo")
        gui.wx.Yield()
        self.assertFalse(frame._boton_directo.boton.IsShown())

    def test_con_usuario_guardado_queda_visible(self):
        frame = self._ventana(tiktok_usuario="mio")
        self._sin_reproductor_ni_comentarios(frame)
        frame.set_conectado(True)
        gui.wx.Yield()
        frame.configurar_tiktok("mio", "http://flujo")
        gui.wx.Yield()
        boton = frame._boton_directo.boton
        self.assertTrue(boton.IsShown())
        self.assertEqual(boton.GetLabel(), "Transm&itir en directo")
        self.assertEqual(boton.GetName(), "Transmitir en directo")

    def test_set_conectado_sin_conexion_propia_oculta(self):
        # Prueba de cableado: sin la llamada a _actualizar_boton_directo
        # en _set_conectado_ui, el botón seguiría visible y fallaría.
        frame = self._ventana()
        self.assertTrue(frame._boton_directo.boton.IsShown())
        frame.set_conectado(True)
        gui.wx.Yield()
        self.assertFalse(frame._boton_directo.boton.IsShown())


# Las etiquetas del botón las arma `transmision_directa.etiqueta`, fuera
# del alcance: quedan como pendientes. La comparación es exacta en los dos
# sentidos: falla si aparece un texto nuevo sin envolver y si un pendiente
# ya no está en el recorrido, para vaciar la lista cuando ese módulo pase
# por gettext.
PENDIENTES_BOTON_DIRECTO = ()


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestPseudoBotonDirectoVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_no_queda_ningun_texto_propio_sin_envolver(self):
        from guyrapu.ui import boton_directo
        with con_pseudo():
            cuadro = wx.Frame(None)
            panel = wx.Panel(cuadro)
            conectar = wx.Button(panel, label="Conectar")
            boton = boton_directo.BotonDirecto(
                panel, conectar, mock.Mock(), mock.Mock())
            vistos = list(textos_sin_marcar(boton.boton))
            boton.actualizar(False, False, False, True)
            vistos.extend(textos_sin_marcar(boton.boton))
            boton.actualizar(False, False, False, True, deteniendo=True)
            vistos.extend(textos_sin_marcar(boton.boton))
        self.addCleanup(destruir, cuadro)
        self.assertEqual(sorted(vistos), sorted(PENDIENTES_BOTON_DIRECTO))


if __name__ == "__main__":
    unittest.main()
