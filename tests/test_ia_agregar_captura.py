# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la subventana para agregar una captura de OBS.

Con ventana: las corre el dueño. No correr aquí, abren diálogos.
"""

import base64
import io
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.capture import redaccion
from guyrapu.ui import espera_sonora
from guyrapu.ui import ia_agregar_captura as agregar
from guyrapu.ui import formulario, tema
from guyrapu.obs import obs_captura_ia
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.ventanas_prueba import app_de_prueba, destruir


_IMAGEN_FALSA = base64.b64encode(b"falso-jpeg-para-la-doble").decode("ascii")


class ClienteDoble:
    """Contesta lo justo para que `opciones` arme escena y una fuente."""

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "GetCurrentProgramScene":
            return {"responseData": {"currentProgramSceneName": "Escena"}}
        if tipo == "GetVideoSettings":
            return {"responseData": {"baseWidth": 1280, "baseHeight": 720}}
        if tipo == "GetSceneItemList":
            return {"responseData": {"sceneItems": [{
                "sourceName": "Cámara",
                "sceneItemEnabled": True,
                "sceneItemTransform": {"sourceWidth": 640,
                                      "sourceHeight": 360},
                "sceneItemIndex": 1}]}}
        if tipo == "GetInputList":
            return {"responseData": {"inputs": [{
                "inputName": "Cámara", "inputKind": "v4l2_input"}]}}
        if tipo == "GetSourceScreenshot":
            return {"responseData": {"imageData": _IMAGEN_FALSA}}
        raise AssertionError(tipo)


def _hilo_directo(target, nombre, **kwargs):
    target()
    hilo = mock.Mock()
    hilo.start.return_value = None
    return hilo


class TestPedirCapturaSinObs(unittest.TestCase):
    # Sin cuadro: un marco doble lleva al reproductor.

    def setUp(self):
        self.reproductor = mock.Mock()
        self.reproductor.has_vout.return_value = 1
        self.marco = mock.MagicMock()
        self.marco._rep_panel = SimpleNamespace(_player=self.reproductor)
        self.padre = mock.Mock()
        self.padre.GetParent.return_value = self.marco
        self.terminado = mock.Mock()
        self.anunciar = self._parchear(agregar, "anunciar")
        self.reproducir = self._parchear(agregar, "reproducir")
        self.mostrar = self._parchear(agregar, "_mostrar")
        self.crear_hilo = self._parchear(
            agregar.diagnostico, "crear_hilo", side_effect=_hilo_directo)
        self.capturar = self._parchear(agregar.ia_captura_video, "capturar")
        self._parchear(agregar.obs_activacion,
                       "obs_esta_en_ejecucion", return_value=False)
        self._parchear(agregar.wx, "CallAfter",
                       side_effect=lambda funcion, *args: funcion(*args))

    def _parchear(self, objetivo, nombre, **kwargs):
        parche = mock.patch.object(objetivo, nombre, **kwargs)
        sustituto = parche.start()
        self.addCleanup(parche.stop)
        return sustituto

    def test_con_video_agrega_el_fotograma_sin_abrir_cuadro(self):
        captura = obs_captura_ia.Captura(b"jpg", 640, 360, None)
        self.capturar.return_value = captura
        agregar.pedir_captura(self.padre, self.terminado)
        opcion = self.capturar.call_args.args[1]
        self.assertEqual(opcion.fuente, "Fotograma del vídeo")
        self.capturar.assert_called_once_with(None, opcion, self.reproductor)
        self.assertTrue(self.crear_hilo.called)
        self.terminado.assert_called_once_with(("Fotograma del vídeo", captura))
        self.mostrar.assert_not_called()
        self.anunciar.assert_not_called()
        self.reproducir.assert_not_called()

    def test_sin_video_anuncia_y_no_agrega(self):
        with self.subTest("solo audio"):
            self.reproductor.has_vout.return_value = 0
            self._comprobar_sin_video()
        self.anunciar.reset_mock()
        self.reproducir.reset_mock()
        self.terminado.reset_mock()
        with self.subTest("sin nada cargado"):
            self.marco._rep_panel = None
            self._comprobar_sin_video()

    def _comprobar_sin_video(self):
        agregar.pedir_captura(self.padre, self.terminado)
        self.anunciar.assert_called_once_with(
            "OBS no está abierto y el reproductor no muestra vídeo.")
        self.reproducir.assert_called_once_with("ia_error")
        self.terminado.assert_called_once_with(None)
        self.capturar.assert_not_called()
        self.crear_hilo.assert_not_called()
        self.mostrar.assert_not_called()

    def test_fallo_del_fotograma_anuncia_y_no_agrega(self):
        self.capturar.side_effect = obs_captura_ia.CapturaFallida(
            "No se pudo capturar el fotograma del vídeo.")
        agregar.pedir_captura(self.padre, self.terminado)
        self.anunciar.assert_called_once_with(
            "No se pudo capturar el fotograma del vídeo.")
        self.reproducir.assert_called_once_with("ia_error")
        self.terminado.assert_called_once_with(None)
        self.mostrar.assert_not_called()


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestDialogoAgregarCapturaVentana(unittest.TestCase):
    # Con ventana: las corre el dueño. No correr aquí.

    def setUp(self):
        self.app = app_de_prueba()
        parche_hilo = mock.patch.object(
            agregar.diagnostico, "crear_hilo", side_effect=_hilo_directo)
        parche_hilo.start()
        self.addCleanup(parche_hilo.stop)
        parche_llamada = mock.patch.object(
            agregar.wx, "CallAfter",
            side_effect=lambda funcion, *args, **kwargs: funcion(*args,
                                                                **kwargs))
        parche_llamada.start()
        self.addCleanup(parche_llamada.stop)

    def _dialogo(self, cliente=None):
        dialogo = agregar.DialogoAgregarCaptura(None, cliente or ClienteDoble())
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _dialogo_sin_cargar(self, cliente=None):
        pendientes = []

        def crear_hilo(target, _nombre, **_kwargs):
            pendientes.append(target)
            return mock.Mock()

        parche = mock.patch.object(agregar.diagnostico, "crear_hilo",
                                   side_effect=crear_hilo)
        parche.start()
        self.addCleanup(parche.stop)
        return self._dialogo(cliente), pendientes

    def test_nombres_accesibles(self):
        dialogo = self._dialogo()
        self.assertEqual(dialogo.GetName(), "DialogoAgregarCaptura")
        self.assertEqual(dialogo.cho_fuente.GetName(), "Capturar de")
        self.assertEqual(dialogo.btn_capturar.GetName(), "Capturar")
        self.assertEqual(dialogo.btn_cancelar.GetName(), "Cancelar")
        self.assertEqual(dialogo.bmp_vista.GetName(), "Vista previa")

    def test_orden_de_tab(self):
        dialogo = self._dialogo()
        navegables = [hijo.GetName() for hijo in dialogo.panel.GetChildren()
                      if isinstance(hijo, (wx.Choice, wx.Button))]
        self.assertEqual(navegables, ["Capturar de", "Capturar", "Cancelar"])
        hijos = list(dialogo.panel.GetChildren())
        self.assertLess(hijos.index(dialogo.cho_fuente),
                        hijos.index(dialogo.bmp_vista))
        self.assertLess(hijos.index(dialogo.bmp_vista),
                        hijos.index(dialogo.btn_capturar))

    def test_mnemonicos_sin_repetir(self):
        dialogo = self._dialogo()
        letras = set()
        for rotulo in (dialogo.rotulo_fuente.GetLabel(),
                       dialogo.btn_capturar.GetLabel(),
                       dialogo.btn_cancelar.GetLabel()):
            posicion = rotulo.find("&")
            self.assertNotEqual(posicion, -1, f"Sin tecla en {rotulo!r}.")
            self.assertLess(posicion + 1, len(rotulo))
            letras.add(rotulo[posicion + 1].lower())
        self.assertEqual(letras, {"c", "r", "n"})

    def test_foco_inicial_y_primera_opcion_elegida(self):
        dialogo = self._dialogo()
        self.assertIs(dialogo.FindFocus(), dialogo.cho_fuente)
        self.assertEqual(dialogo.cho_fuente.GetSelection(), 0)
        self.assertEqual(dialogo.cho_fuente.GetStringSelection(),
                         "Escena actual: Escena")
        self.assertEqual(dialogo._opciones[0].fuente, "Escena")
        self.assertTrue(dialogo.btn_capturar.IsEnabled())

    def _dialogo_con_reproductor(self, con_video=True):
        reproductor = mock.Mock()
        reproductor.has_vout.return_value = 1 if con_video else 0
        dialogo = agregar.DialogoAgregarCaptura(
            None, ClienteDoble(), reproductor)
        self.addCleanup(destruir, dialogo)
        return dialogo, reproductor

    def test_con_video_la_lista_termina_con_el_fotograma(self):
        dialogo, _reproductor = self._dialogo_con_reproductor()
        self.assertEqual(
            dialogo.cho_fuente.GetStrings(),
            ["Escena actual: Escena", "Cámara", "Fotograma del vídeo"])
        opcion = dialogo._opciones[-1]
        self.assertEqual(opcion.fuente, "Fotograma del vídeo")
        self.assertEqual(opcion.etiqueta, "Fotograma del vídeo")

    def test_sin_video_la_lista_queda_como_hoy(self):
        dialogo, _reproductor = self._dialogo_con_reproductor(False)
        self.assertEqual(dialogo.cho_fuente.GetStrings(),
                         ["Escena actual: Escena", "Cámara"])

    def test_vista_previa_del_fotograma_usa_el_reproductor(self):
        dialogo, reproductor = self._dialogo_con_reproductor()
        dialogo.cho_fuente.SetSelection(2)
        salida = io.BytesIO()
        wx.Image(2, 2).SaveFile(salida, wx.BITMAP_TYPE_JPEG)
        with mock.patch.object(agregar.ia_captura_video, "vista_previa",
                               return_value=salida.getvalue()) as vista:
            dialogo._al_temporizador(mock.Mock())
        opcion = vista.call_args.args[1]
        vista.assert_called_once_with(dialogo._cliente, opcion, reproductor)
        self.assertTrue(dialogo.bmp_vista.GetBitmap().IsOk())

    def test_capturar_el_fotograma_guarda_la_etiqueta(self):
        dialogo, reproductor = self._dialogo_con_reproductor()
        dialogo.cho_fuente.SetSelection(2)
        captura = obs_captura_ia.Captura(b"jpg", 640, 360, None)
        with mock.patch.object(dialogo, "EndModal"), \
                mock.patch.object(agregar.ia_captura_video, "capturar",
                                  return_value=captura) as capturar:
            dialogo._al_capturar(mock.Mock())
        opcion = capturar.call_args.args[1]
        capturar.assert_called_once_with(dialogo._cliente, opcion, reproductor)
        self.assertEqual(dialogo.resultado, ("Fotograma del vídeo", captura))

    def test_capturar_nunca_esta_deshabilitado(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        self.assertTrue(dialogo.btn_capturar.IsEnabled())
        pendientes.pop(0)()
        self.assertTrue(dialogo.btn_capturar.IsEnabled())
        dialogo._al_capturar(mock.Mock())
        self.assertTrue(dialogo.btn_capturar.IsEnabled())

    def test_etiqueta_dice_el_motivo(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        self.assertEqual(
            dialogo.btn_capturar.GetLabel(),
            redaccion.etiqueta_con_motivo(
                "Captu&rar", "Cargando las fuentes de OBS"))
        pendientes.pop(0)()
        self.assertEqual(dialogo.btn_capturar.GetLabel(), "Captu&rar")
        dialogo._al_capturar(mock.Mock())
        self.assertEqual(
            dialogo.btn_capturar.GetLabel(),
            redaccion.etiqueta_con_motivo("Captu&rar", "Capturando"))

    def test_activarlo_mientras_carga_anuncia_y_no_captura(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        with mock.patch.object(agregar, "anunciar") as anunciar:
            dialogo.btn_capturar.GetEventHandler().ProcessEvent(
                wx.CommandEvent(wx.EVT_BUTTON.typeId,
                                dialogo.btn_capturar.GetId()))
        self.assertEqual(len(pendientes), 1)
        anunciar.assert_called_once_with("Cargando las fuentes de OBS.")

    def test_activarlo_mientras_captura_anuncia_y_no_lanza_otro_hilo(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        pendientes.pop(0)()
        with mock.patch.object(agregar, "anunciar") as anunciar:
            dialogo._al_capturar(mock.Mock())
            self.assertEqual(len(pendientes), 1)
            dialogo._al_capturar(mock.Mock())
        anunciar.assert_called_once_with("Capturando.")
        self.assertEqual(len(pendientes), 1)

    def test_al_llegar_las_fuentes_vuelve_a_la_base(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        self.assertNotEqual(dialogo.btn_capturar.GetLabel(), "Captu&rar")
        pendientes.pop(0)()
        self.assertEqual(dialogo.btn_capturar.GetLabel(), "Captu&rar")

    def test_cargar_fuentes_suena_espera_y_listo(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            self.assertTrue(dialogo._espera._timer.IsRunning())
            dialogo._espera._al_tiempo(None)
            pendientes.pop(0)()
        self.assertFalse(dialogo._espera._timer.IsRunning())
        self.assertEqual([llamada.args[0] for llamada in sonar.call_args_list],
                         ["espera", "listo"])

    def test_captura_buena_suena_espera_y_listo(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        pendientes.pop(0)()
        captura = obs_captura_ia.Captura(b"x", 320, 180, False)
        with mock.patch.object(dialogo, "EndModal"), \
                mock.patch.object(agregar.obs_captura_ia, "capturar",
                                  return_value=captura), \
                mock.patch.object(
                    espera_sonora.sound_player, "reproducir") as sonar:
            dialogo._al_capturar(mock.Mock())
            self.assertTrue(dialogo._espera._timer.IsRunning())
            dialogo._espera._al_tiempo(None)
            pendientes.pop(0)()
        self.assertFalse(dialogo._espera._timer.IsRunning())
        self.assertEqual([llamada.args[0] for llamada in sonar.call_args_list],
                         ["espera", "listo"])

    def test_captura_fallida_termina_sin_listo(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        pendientes.pop(0)()
        with mock.patch.object(
                agregar.obs_captura_ia, "capturar",
                side_effect=obs_captura_ia.CapturaFallida("nada")), \
                mock.patch.object(agregar, "anunciar"), \
                mock.patch.object(agregar, "reproducir"), \
                mock.patch.object(
                    espera_sonora.sound_player, "reproducir") as sonar:
            dialogo._al_capturar(mock.Mock())
            dialogo._espera._al_tiempo(None)
            pendientes.pop(0)()
        self.assertEqual([llamada.args[0] for llamada in sonar.call_args_list],
                         ["espera"])

    def test_captura_negra_termina_sin_listo(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        pendientes.pop(0)()
        captura = obs_captura_ia.Captura(b"x", 320, 180, True, "sin_elegir",
                                         "Cámara")
        with mock.patch.object(agregar.obs_captura_ia, "capturar",
                               return_value=captura), \
                mock.patch.object(agregar, "anunciar"), \
                mock.patch.object(agregar, "reproducir"), \
                mock.patch.object(
                    espera_sonora.sound_player, "reproducir") as sonar:
            dialogo._al_capturar(mock.Mock())
            dialogo._espera._al_tiempo(None)
            pendientes.pop(0)()
        self.assertEqual([llamada.args[0] for llamada in sonar.call_args_list],
                         ["espera"])

    def test_lista_vacia_lleva_el_motivo_en_la_etiqueta(self):
        dialogo, _pendientes = self._dialogo_sin_cargar()
        dialogo._opciones_listas([])
        self.assertEqual(
            dialogo.btn_capturar.GetLabel(),
            redaccion.etiqueta_con_motivo(
                "Captu&rar", "No hay fuentes para capturar"))
        self.assertTrue(dialogo.btn_capturar.IsEnabled())

    def test_activarlo_sin_fuentes_anuncia_y_no_captura(self):
        dialogo, _pendientes = self._dialogo_sin_cargar()
        dialogo._opciones_listas([])
        with mock.patch.object(agregar, "anunciar") as anunciar, \
                mock.patch.object(agregar.obs_captura_ia,
                                  "capturar") as capturar:
            dialogo._al_capturar(mock.Mock())
        anunciar.assert_called_once_with("No hay fuentes para capturar.")
        capturar.assert_not_called()

    def test_captura_que_falla_vuelve_a_la_base(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        pendientes.pop(0)()
        with mock.patch.object(
                agregar.obs_captura_ia, "capturar",
                side_effect=obs_captura_ia.CapturaFallida("nada")), \
                mock.patch.object(agregar, "anunciar"), \
                mock.patch.object(agregar, "reproducir"):
            dialogo._al_capturar(mock.Mock())
            self.assertEqual(dialogo.btn_capturar.GetLabel(),
                             "Captu&rar (capturando)")
            pendientes.pop(0)()
        self.assertEqual(dialogo.btn_capturar.GetLabel(), "Captu&rar")

    def test_captura_negra_vuelve_a_la_base(self):
        dialogo, pendientes = self._dialogo_sin_cargar()
        pendientes.pop(0)()
        captura = obs_captura_ia.Captura(b"x", 320, 180, True, "sin_elegir",
                                         "Cámara")
        with mock.patch.object(agregar.obs_captura_ia, "capturar",
                               return_value=captura), \
                mock.patch.object(agregar, "anunciar"), \
                mock.patch.object(agregar, "reproducir"):
            dialogo._al_capturar(mock.Mock())
            self.assertEqual(dialogo.btn_capturar.GetLabel(),
                             "Captu&rar (capturando)")
            pendientes.pop(0)()
        self.assertEqual(dialogo.btn_capturar.GetLabel(), "Captu&rar")

    def test_negra_no_cierra_anuncia_y_vuelve(self):
        dialogo = self._dialogo()
        opcion = dialogo._opcion_elegida()
        captura = obs_captura_ia.Captura(b"x", 320, 180, True, "sin_elegir",
                                         "Cámara")
        with mock.patch.object(dialogo, "EndModal") as fin, \
                mock.patch.object(agregar, "anunciar") as anunciar, \
                mock.patch.object(agregar, "reproducir") as sonar, \
                mock.patch.object(agregar.obs_captura_ia, "capturar",
                                  return_value=captura):
            dialogo._al_capturar(mock.Mock())
        fin.assert_not_called()
        anunciar.assert_called_once_with(
            agregar.texto_negra(opcion.etiqueta, "sin_elegir", "Cámara"))
        sonar.assert_called_once_with("ia_imagen_negra")
        self.assertIsNone(dialogo.resultado)
        self.assertTrue(dialogo.btn_capturar.IsEnabled())
        self.assertIs(dialogo.FindFocus(), dialogo.cho_fuente)

    def test_buena_cierra_con_ok_y_guarda_la_fuente(self):
        dialogo = self._dialogo()
        opcion = dialogo._opcion_elegida()
        captura = obs_captura_ia.Captura(b"x", 320, 180, False)
        with mock.patch.object(dialogo, "EndModal") as fin, \
                mock.patch.object(agregar.obs_captura_ia, "capturar",
                                  return_value=captura):
            dialogo._al_capturar(mock.Mock())
        fin.assert_called_once_with(wx.ID_OK)
        self.assertEqual(dialogo.resultado, (opcion.fuente, captura))

    def test_fallo_de_captura_anuncia_y_no_cierra(self):
        dialogo = self._dialogo()
        mensaje = "No se pudo capturar Cámara. Comprueba que esté visible."
        with mock.patch.object(dialogo, "EndModal") as fin, \
                mock.patch.object(agregar, "anunciar") as anunciar, \
                mock.patch.object(agregar, "reproducir") as sonar, \
                mock.patch.object(
                    agregar.obs_captura_ia, "capturar",
                    side_effect=obs_captura_ia.CapturaFallida(mensaje)):
            dialogo._al_capturar(mock.Mock())
        fin.assert_not_called()
        anunciar.assert_called_once_with(mensaje)
        sonar.assert_called_once_with("ia_error")
        self.assertIsNone(dialogo.resultado)
        self.assertTrue(dialogo.btn_capturar.IsEnabled())
        self.assertIs(dialogo.FindFocus(), dialogo.cho_fuente)

    def test_vista_que_falla_deja_vacio_y_no_anuncia(self):
        dialogo = self._dialogo()
        with mock.patch.object(agregar, "anunciar") as anunciar, \
                mock.patch.object(
                    agregar.obs_captura_ia, "vista_previa",
                    side_effect=obs_captura_ia.CapturaFallida("sin luz")):
            dialogo._al_temporizador(mock.Mock())
        anunciar.assert_not_called()
        self.assertFalse(dialogo.bmp_vista.GetBitmap().IsOk())

    # Lo arma guyrapu/obs/obs_captura_ia.py: el nombre de la fuente tal
    # cual lo da OBS es dato del usuario y pasa sin marcar. La etiqueta de
    # la escena actual ya sale marcada porque ese módulo la traduce.
    PENDIENTES_OTRO_MODULO = (
        "Cámara",
    )

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo()
            sin_marcar = textos_sin_marcar(dialogo)

        self.assertEqual(sorted(sin_marcar),
                         sorted(self.PENDIENTES_OTRO_MODULO))

    def test_pseudo_sin_obs_avisa_marcado(self):
        with con_pseudo(), \
                mock.patch.object(agregar.obs_activacion,
                                   "obs_esta_en_ejecucion",
                                   return_value=False), \
                mock.patch.object(agregar, "anunciar") as anunciar, \
                mock.patch.object(agregar, "reproducir"):
            terminado = mock.Mock()
            agregar.pedir_captura(mock.Mock(), terminado)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])
        terminado.assert_called_once_with(None)

    def test_pseudo_negra_anuncia_marcado(self):
        dialogo = self._dialogo()
        opcion = dialogo._opcion_elegida()
        captura = obs_captura_ia.Captura(b"x", 320, 180, True, "sin_elegir",
                                         "Cámara")
        with con_pseudo(), \
                mock.patch.object(agregar, "anunciar") as anunciar, \
                mock.patch.object(agregar, "reproducir"):
            dialogo._captura_lista(opcion, captura)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])

    def test_escape_cierra_con_cancel(self):
        dialogo = self._dialogo()
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with mock.patch.object(dialogo, "EndModal") as fin:
            dialogo._al_tecla(evento)
        fin.assert_called_once_with(wx.ID_CANCEL)

    def test_cancelar_cierra_y_no_toca_despues(self):
        dialogo = self._dialogo()
        antes = dialogo.cho_fuente.GetStringSelection()
        with mock.patch.object(dialogo, "EndModal") as fin:
            dialogo.btn_cancelar.GetEventHandler().ProcessEvent(
                wx.CommandEvent(wx.EVT_BUTTON.typeId,
                                dialogo.btn_cancelar.GetId()))
        fin.assert_called_once_with(wx.ID_CANCEL)
        self.assertTrue(dialogo._cerrado)
        dialogo._opciones_listas([obs_captura_ia.OpcionCaptura(
            "Otra", "Otra", 640, 360)])
        self.assertEqual(dialogo.cho_fuente.GetStringSelection(), antes)


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestDisenioComun(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_geometria_del_cuadro(self):
        cuadro = agregar.DialogoAgregarCaptura(None, ClienteDoble())
        self.addCleanup(destruir, cuadro)
        ancho, alto = cuadro.GetSize()
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO)
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO)
        rotulo = cuadro.rotulo_fuente
        control = cuadro.cho_fuente
        self.assertEqual(
            rotulo.GetPosition().y + rotulo.GetSize().height,
            control.GetPosition().y - formulario.ETIQUETA_A_CONTROL)
        self.assertEqual(rotulo.GetPosition().x, control.GetPosition().x)
        cliente = cuadro.GetClientSize()
        botones = [cuadro.btn_capturar, cuadro.btn_cancelar]
        self.assertEqual(len({b.GetPosition().y for b in botones}), 1)
        self.assertEqual(
            cliente.width - max(b.GetPosition().x + b.GetSize().width
                                for b in botones),
            formulario.MARGEN)
        self.assertEqual(
            cliente.height - (botones[0].GetPosition().y
                              + botones[0].GetSize().height),
            formulario.MARGEN)
        self.assertEqual(cuadro.btn_capturar.GetBackgroundColour(),
                         tema._T.primary)


if __name__ == "__main__":
    unittest.main()
