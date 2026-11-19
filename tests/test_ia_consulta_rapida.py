# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la consulta rápida a la IA (Ctrl+Mayús+F2).

Sin red ni OBS real: lo externo va con dobles y los hilos corren en el
acto. `TestConsultaRapida` y `TestAbrirVentanaTomaConversacion` no crean
controles y corren en cualquier PC. `TestConsultaRapidaVentana` usa
controles reales. Con ventana.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import wx  # noqa: F401
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.ai import consulta
from guyrapu.ai import protocolos
from guyrapu.player import fotograma_video
from guyrapu.ui import ia_consulta_rapida as rapida
from tests.pseudo_prueba import con_pseudo
from tests.ventanas_prueba import app_de_prueba, destruir


def _hilo_directo(target, nombre, **kwargs):
    args = kwargs.get("args", ())
    target(*args)
    hilo = mock.Mock()
    hilo.start.return_value = None
    return hilo


class _TemporizadorFalso:
    def __init__(self, *args, **kwargs):
        self.inicios = []
        self.frenos = 0
        self.andando = False

    def Start(self, intervalo):
        self.inicios.append(intervalo)
        self.andando = True

    def Stop(self):
        self.frenos += 1
        self.andando = False

    def IsRunning(self):
        return self.andando


class TestConsultaRapida(unittest.TestCase):

    def setUp(self):
        rapida._INSTANCIAS.clear()
        self.addCleanup(rapida._INSTANCIAS.clear)
        self.preparar_real = rapida.consulta.preparar
        self.marco = mock.MagicMock()
        self.marco.IsBeingDeleted.return_value = False
        self.retenidos = []
        self._parchar_wx()
        self._parchar_hilo_directo()
        self._aplicar_dobles()

    def _parchar_wx(self):
        llamada = mock.patch.object(
            rapida.wx, "CallAfter",
            side_effect=lambda funcion, *args, **kwargs: funcion(*args,
                                                                 **kwargs))
        llamada.start()
        self.addCleanup(llamada.stop)
        temporizador = mock.patch.object(
            rapida.wx, "Timer", side_effect=_TemporizadorFalso)
        temporizador.start()
        self.addCleanup(temporizador.stop)

    def _parchar_hilo_directo(self):
        hilo = mock.patch.object(
            rapida.diagnostico, "crear_hilo", side_effect=_hilo_directo)
        hilo.start()
        self.addCleanup(hilo.stop)

    def _hilo_retenido(self, target, nombre, **kwargs):
        self.retenidos.append((target, kwargs.get("args", ())))
        hilo = mock.Mock()
        hilo.start.return_value = None
        return hilo

    def _aplicar_dobles(self):
        self.opcion = SimpleNamespace(
            fuente="Escena", etiqueta="Escena al aire: Juego")
        self.captura = SimpleNamespace(jpeg=b"jpg-falso", negra=False,
                                       motivo="", fuente_motivo="")
        self.m_cliente = mock.Mock()
        self.m_gestor = mock.Mock()
        self.m_gestor.descripcion_escena.return_value = (
            "Escena con una cámara.")
        self.ajustes = SimpleNamespace(
            proveedor="gemini", modelo="m", direccion="", pregunta="",
            largo="media", tiempo_espera=60, decir_analizando=True,
            privacidad_aceptada=True)
        self.preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        parches = [
            mock.patch.object(rapida.obs_activacion,
                              "obs_esta_en_ejecucion", return_value=True),
            mock.patch.object(rapida.obs_cliente, "ClienteObs",
                              return_value=self.m_cliente),
            mock.patch.object(rapida.obs_cliente, "leer_ajustes",
                              return_value=object()),
            mock.patch.object(rapida.obs_captura_ia, "opciones",
                              return_value=(self.opcion,)),
            mock.patch.object(rapida.obs_captura_ia, "capturar",
                              return_value=self.captura),
            mock.patch.object(rapida, "GestorPanelObs",
                              return_value=self.m_gestor),
            mock.patch.object(rapida.ajustes_ia, "leer",
                              return_value=self.ajustes),
            mock.patch.object(rapida.catalogo, "cargar", return_value={}),
            mock.patch.object(rapida.claves, "leer", return_value="clave"),
            mock.patch.object(rapida.consulta, "preparar",
                              return_value=self.preparada),
            mock.patch.object(rapida.proveedores, "por_id",
                              return_value=SimpleNamespace(
                                  nombre="Google Gemini")),
            mock.patch.object(rapida.ia_privacidad, "confirmar",
                              return_value=True),
            mock.patch.object(rapida.envio_ia, "enviar",
                              return_value=protocolos.Respuesta(
                                  "Se ve bien.", False)),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self._p_anunciar = mock.patch.object(rapida, "anunciar")
        self.m_anunciar = self._p_anunciar.start()
        self.addCleanup(self._p_anunciar.stop)
        self._p_sonar = mock.patch.object(rapida, "reproducir")
        self.m_sonar = self._p_sonar.start()
        self.addCleanup(self._p_sonar.stop)

    def _instancia(self):
        return rapida._INSTANCIAS[id(self.marco)]

    def test_los_textos_del_fotograma_siguen_en_el_modulo(self):
        self.assertEqual(
            rapida.TEXTO_SIN_VIDEO,
            "OBS no está abierto y el reproductor no muestra vídeo.")
        self.assertEqual(
            rapida.TEXTO_FOTOGRAMA_FALLIDO,
            "No se pudo capturar el fotograma del vídeo.")
        self.assertEqual(rapida.ETIQUETA_FOTOGRAMA, "Fotograma del vídeo")

    def test_camino_feliz_suena_en_orden_anuncia_y_guarda(self):
        rapida.consultar(self.marco)
        self.assertEqual(
            self.m_sonar.mock_calls,
            [mock.call("ia_enviada"), mock.call("ia_respuesta")])
        self.m_anunciar.assert_called_once_with("Se ve bien.")
        instancia = self._instancia()
        self.assertEqual(
            instancia._temporizador.inicios,
            [rapida.ia_ventana.INTERVALO_AVISO_MS])
        self.assertEqual(
            instancia._melodia.inicios,
            [rapida.ia_ventana.INTERVALO_MELODIA_MS])
        self.assertEqual(instancia._temporizador.frenos, 1)
        self.assertEqual(instancia._melodia.frenos, 1)
        self.assertFalse(instancia._en_curso)
        tomada = rapida.tomar_conversacion(self.marco)
        self.assertIsNotNone(tomada)
        charla, descripcion = tomada
        self.assertEqual(descripcion, "Escena con una cámara.")
        self.assertTrue(charla.filas[0].startswith("Captura: Escena, "))
        self.assertEqual(charla.filas[1:], ["Pregunta: ¿qué se ve?",
                                            "Respuesta: Se ve bien."])
        self.assertIsNone(rapida.tomar_conversacion(self.marco))

    def test_obs_abierto_no_toca_el_reproductor(self):
        with mock.patch.object(rapida.fotograma_video,
                               "reproductor_de") as desde, \
                mock.patch.object(rapida.fotograma_video,
                                  "capturar") as capturar:
            rapida.consultar(self.marco)
        desde.assert_not_called()
        capturar.assert_not_called()
        self.assertTrue(rapida.tomar_conversacion(self.marco)[0].filas)

    def _con_video_en_el_reproductor(self):
        reproductor = mock.Mock()
        reproductor.has_vout.return_value = 1
        self.marco._rep_panel = SimpleNamespace(_player=reproductor)
        return reproductor

    def test_obs_cerrado_con_video_captura_y_sigue_como_escena(self):
        reproductor = self._con_video_en_el_reproductor()
        with mock.patch.object(rapida.obs_activacion,
                               "obs_esta_en_ejecucion", return_value=False), \
                mock.patch.object(rapida.fotograma_video, "capturar",
                                  return_value=(b"jpg-falso", 640, 360)) as capturar:
            rapida.consultar(self.marco)
        capturar.assert_called_once_with(reproductor)
        self.m_gestor.descripcion_escena.assert_not_called()
        self.assertEqual(
            self.m_sonar.mock_calls,
            [mock.call("ia_enviada"), mock.call("ia_respuesta")])
        charla, descripcion = rapida.tomar_conversacion(self.marco)
        self.assertEqual(descripcion, "")
        self.assertTrue(charla.filas[0].startswith(
            "Captura: Fotograma del vídeo, "))
        self.assertEqual(charla.filas[1:], ["Pregunta: ¿qué se ve?",
                                            "Respuesta: Se ve bien."])

    def test_obs_cerrado_sin_panel_avisa_y_no_hace_nada(self):
        marco = mock.MagicMock(spec=["IsBeingDeleted", "Bind"])
        marco.IsBeingDeleted.return_value = False
        with mock.patch.object(rapida.obs_activacion,
                               "obs_esta_en_ejecucion", return_value=False), \
                mock.patch.object(rapida.diagnostico,
                                   "crear_hilo") as hilo:
            rapida.consultar(marco)
        self.m_anunciar.assert_called_once_with(
            "OBS no está abierto y el reproductor no muestra vídeo.")
        self.m_sonar.assert_called_once_with("ia_error")
        hilo.assert_not_called()
        self.assertIsNone(rapida.tomar_conversacion(marco))

    def test_obs_cerrado_sin_video_avisa_y_no_hace_nada(self):
        reproductor = mock.Mock()
        reproductor.has_vout.return_value = 0
        self.marco._rep_panel = SimpleNamespace(_player=reproductor)
        with mock.patch.object(rapida.obs_activacion,
                               "obs_esta_en_ejecucion", return_value=False), \
                mock.patch.object(rapida.diagnostico,
                                   "crear_hilo") as hilo:
            rapida.consultar(self.marco)
        self.m_anunciar.assert_called_once_with(
            "OBS no está abierto y el reproductor no muestra vídeo.")
        self.m_sonar.assert_called_once_with("ia_error")
        hilo.assert_not_called()
        self.assertIsNone(rapida.tomar_conversacion(self.marco))

    def test_fallo_del_fotograma_avisa_y_no_envia(self):
        self._con_video_en_el_reproductor()
        with mock.patch.object(rapida.obs_activacion,
                               "obs_esta_en_ejecucion", return_value=False), \
                mock.patch.object(rapida.fotograma_video, "capturar",
                                  side_effect=fotograma_video.FotogramaFallido(
                                      "sin fotograma")), \
                mock.patch.object(rapida.envio_ia, "enviar") as envio:
            rapida.consultar(self.marco)
        self.m_anunciar.assert_called_once_with(
            "No se pudo capturar el fotograma del vídeo.")
        self.m_sonar.assert_called_once_with("ia_error")
        envio.assert_not_called()
        self.assertFalse(self._instancia()._en_curso)
        self.assertIsNone(rapida.tomar_conversacion(self.marco))

    def test_captura_negra_no_envia(self):
        self.captura.negra = True
        self.captura.motivo = "sin_fuente"
        with mock.patch.object(rapida.envio_ia, "enviar") as envio, \
                mock.patch.object(rapida.ia_privacidad,
                                   "confirmar") as confirmar:
            rapida.consultar(self.marco)
        self.m_anunciar.assert_called_once_with(
            rapida.ia_agregar_captura.texto_negra(
                "Escena al aire: Juego", "sin_fuente", ""))
        self.m_sonar.assert_called_once_with("ia_imagen_negra")
        envio.assert_not_called()
        confirmar.assert_not_called()
        self.assertFalse(self._instancia()._en_curso)
        self.assertIsNone(rapida.tomar_conversacion(self.marco))

    def test_fallo_de_conexion_avisa_sin_enviar(self):
        self.m_cliente.conectar.side_effect = Exception(
            "connection refused")
        # La guarda de consultar ve True y el mensaje del fallo ve False.
        with mock.patch.object(rapida.obs_activacion,
                               "obs_esta_en_ejecucion",
                               side_effect=[True, False]), \
                mock.patch.object(rapida.envio_ia, "enviar") as envio:
            rapida.consultar(self.marco)
        self.m_anunciar.assert_called_once_with(
            "No se pudo conectar con OBS. Comprueba que OBS esté abierto y "
            "que su servidor WebSocket esté activado.")
        self.m_sonar.assert_called_once_with("ia_error")
        envio.assert_not_called()
        self.m_cliente.cerrar.assert_called_once_with()

    def test_falta_de_clave_no_pide_confirmar(self):
        with mock.patch.object(rapida.claves, "leer", return_value=None), \
                mock.patch.object(rapida.consulta, "preparar",
                                  side_effect=self.preparar_real) as preparar, \
                mock.patch.object(rapida.ia_privacidad,
                                   "confirmar") as confirmar, \
                mock.patch.object(rapida.envio_ia, "enviar") as envio:
            rapida.consultar(self.marco)
        preparar.assert_called_once()
        self.m_anunciar.assert_called_once_with(
            "Falta la clave de Google Gemini. Guárdala en Preferencias, "
            "Inteligencia artificial.")
        self.m_sonar.assert_called_once_with("ia_error")
        confirmar.assert_not_called()
        envio.assert_not_called()

    def test_sin_confirmar_avisa_la_cancelacion(self):
        with mock.patch.object(rapida.ia_privacidad, "confirmar",
                               return_value=False), \
                mock.patch.object(rapida.envio_ia, "enviar") as envio:
            rapida.consultar(self.marco)
        envio.assert_not_called()
        self.assertEqual(self.m_anunciar.mock_calls,
                         [mock.call("Consulta cancelada.")])
        self.assertEqual(self.m_sonar.mock_calls, [mock.call("ia_error")])
        self.assertFalse(self._instancia()._en_curso)
        self.assertIsNone(rapida.tomar_conversacion(self.marco))

    def test_respuesta_sin_ventana_registra_y_no_anuncia(self):
        rapida.consultar(self.marco)
        instancia = self._instancia()
        self.m_anunciar.reset_mock()
        self.m_sonar.reset_mock()
        self.marco.IsBeingDeleted.return_value = True
        with mock.patch.object(rapida.logger, "warning") as registro:
            instancia._vuelta_envio(
                None, self.preparada, "clave", "Escena con una cámara.",
                protocolos.Respuesta("Se ve bien.", False))
        registro.assert_called_once()
        self.m_anunciar.assert_not_called()
        self.m_sonar.assert_not_called()

    def test_fallo_de_envio_avisa_y_frena_los_dos(self):
        fallo = protocolos.ErrorIA(protocolos.CUOTA, "sin saldo")
        with mock.patch.object(rapida.envio_ia, "enviar",
                               side_effect=fallo):
            rapida.consultar(self.marco)
        self.m_anunciar.assert_called_once_with(
            "Se agotó la cuota del proveedor. Espera unos minutos "
            "o elige otro modelo.")
        self.assertEqual(
            self.m_sonar.mock_calls,
            [mock.call("ia_enviada"), mock.call("ia_error")])
        instancia = self._instancia()
        self.assertEqual(instancia._temporizador.frenos, 1)
        self.assertEqual(instancia._melodia.frenos, 1)
        self.assertIsNone(rapida.tomar_conversacion(self.marco))

    def test_segunda_llamada_en_curso_solo_avisa(self):
        with mock.patch.object(rapida.diagnostico, "crear_hilo",
                               side_effect=self._hilo_retenido):
            rapida.consultar(self.marco)
            rapida.consultar(self.marco)
        self.assertEqual(len(self.retenidos), 1)
        self.m_anunciar.assert_called_once_with(rapida.TEXTO_EN_CURSO)
        self.m_sonar.assert_not_called()

    def test_marco_destruido_a_la_mitad_no_hace_nada(self):
        with mock.patch.object(rapida.diagnostico, "crear_hilo",
                               side_effect=self._hilo_retenido), \
                mock.patch.object(rapida.envio_ia, "enviar") as envio:
            rapida.consultar(self.marco)
            self.marco.IsBeingDeleted.return_value = True
            destino, args = self.retenidos[0]
            destino(*args)
        envio.assert_not_called()
        self.m_anunciar.assert_not_called()
        self.m_sonar.assert_not_called()

    def test_tomar_sin_nada_da_none(self):
        self.assertIsNone(rapida.tomar_conversacion(self.marco))
        self.assertIsNone(
            rapida.tomar_conversacion(mock.MagicMock()))


class TestPseudoEnCurso(unittest.TestCase):
    """Bajo seudotraducción, el aviso de consulta en curso sale marcado."""

    def test_segunda_llamada_sale_marcada(self):
        rapida._INSTANCIAS.clear()
        self.addCleanup(rapida._INSTANCIAS.clear)
        marco = mock.MagicMock()
        marco.IsBeingDeleted.return_value = False
        retenidos = []

        def retenido(target, nombre, **kwargs):
            retenidos.append((target, kwargs.get("args", ())))
            hilo = mock.Mock()
            hilo.start.return_value = None
            return hilo

        with mock.patch.object(rapida.wx, "Timer",
                               side_effect=_TemporizadorFalso), \
                mock.patch.object(rapida.obs_activacion,
                                  "obs_esta_en_ejecucion",
                                  return_value=True), \
                mock.patch.object(rapida.diagnostico, "crear_hilo",
                                  side_effect=retenido), \
                mock.patch.object(rapida, "anunciar") as anunciar, \
                con_pseudo():
            rapida.consultar(marco)
            rapida.consultar(marco)
        anunciar.assert_called_once()
        texto = anunciar.call_args.args[0]
        self.assertTrue(texto.startswith("[¡"), texto)


class TestAbrirVentanaTomaConversacion(unittest.TestCase):

    def test_conversacion_tomada_arranca_con_ella(self):
        from guyrapu.ui import ia_ventana as ventana
        padre = mock.Mock()
        charla = mock.Mock()
        with mock.patch.object(rapida, "tomar_conversacion",
                               return_value=(charla, "Una escena.")) as tomar, \
                mock.patch.object(ventana, "VentanaIA") as clase:
            ventana.abrir_ventana(padre)
        tomar.assert_called_once_with(padre)
        clase.assert_called_once_with(padre, charla, "Una escena.")

    def test_sin_conversacion_arranca_vacia_como_hoy(self):
        from guyrapu.ui import ia_ventana as ventana
        padre = mock.Mock()
        with mock.patch.object(rapida, "tomar_conversacion",
                               return_value=None) as tomar, \
                mock.patch.object(ventana, "VentanaIA") as clase:
            ventana.abrir_ventana(padre)
        tomar.assert_called_once_with(padre)
        clase.assert_called_once_with(padre)


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestConsultaRapidaVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        llamada = mock.patch.object(
            rapida.wx, "CallAfter",
            side_effect=lambda funcion, *args, **kwargs: funcion(*args,
                                                                 **kwargs))
        llamada.start()
        self.addCleanup(llamada.stop)
        hilo = mock.patch.object(
            rapida.diagnostico, "crear_hilo", side_effect=_hilo_directo)
        hilo.start()
        self.addCleanup(hilo.stop)
        opcion = SimpleNamespace(
            fuente="Escena", etiqueta="Escena al aire: Juego")
        gestor = mock.Mock()
        gestor.descripcion_escena.return_value = "Escena con una cámara."
        ajustes = SimpleNamespace(
            proveedor="gemini", modelo="m", direccion="", pregunta="",
            largo="media", tiempo_espera=60, decir_analizando=True,
            privacidad_aceptada=True)
        parches = [
            mock.patch.object(rapida.obs_activacion,
                              "obs_esta_en_ejecucion", return_value=True),
            mock.patch.object(rapida.obs_cliente, "ClienteObs"),
            mock.patch.object(rapida.obs_captura_ia, "opciones",
                              return_value=(opcion,)),
            mock.patch.object(rapida.obs_captura_ia, "capturar",
                              return_value=SimpleNamespace(
                                  jpeg=b"jpg-falso", negra=False)),
            mock.patch.object(rapida, "GestorPanelObs",
                              return_value=gestor),
            mock.patch.object(rapida.ajustes_ia, "leer",
                              return_value=ajustes),
            mock.patch.object(rapida.catalogo, "cargar", return_value={}),
            mock.patch.object(rapida.claves, "leer", return_value="clave"),
            mock.patch.object(rapida.consulta, "preparar",
                              return_value=consulta.Preparada(
                                  object(), "¿qué se ve?", 60)),
            mock.patch.object(rapida.proveedores, "por_id",
                              return_value=SimpleNamespace(
                                  nombre="Google Gemini")),
            mock.patch.object(rapida.ia_privacidad, "confirmar",
                              return_value=True),
            mock.patch.object(rapida.envio_ia, "enviar",
                              return_value=protocolos.Respuesta(
                                  "Se ve bien.", False)),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)

    def test_camino_feliz_frena_los_dos_avisos_reales(self):
        with mock.patch.object(rapida, "anunciar") as anunciar, \
                mock.patch.object(rapida, "reproducir") as sonar:
            rapida.consultar(self.marco)
        instancia = rapida._INSTANCIAS[id(self.marco)]
        try:
            self.assertFalse(instancia._temporizador.IsRunning())
            self.assertFalse(instancia._melodia.IsRunning())
            self.assertEqual(
                sonar.mock_calls,
                [mock.call("ia_enviada"), mock.call("ia_respuesta")])
            anunciar.assert_called_once_with("Se ve bien.")
            tomada = rapida.tomar_conversacion(self.marco)
            self.assertIsNotNone(tomada)
            self.assertEqual(tomada[1], "Escena con una cámara.")
        finally:
            rapida._INSTANCIAS.clear()


if __name__ == "__main__":
    unittest.main()
