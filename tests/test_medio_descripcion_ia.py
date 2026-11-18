# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botón Describir imagen del cuadro de un medio.

Sin red: la IA y la espera van con dobles. La lectura de la imagen y el GIF
se ejecuta de verdad. Con ventana.
"""

import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.ai import consulta, protocolos
from guyrapu.ui import confirmar, medio_cuadro
from guyrapu.ui import medio_descripcion_ia as modulo
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg==")
GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

TEXTO_SOLO_IMAGEN = "Solo se propone la descripción de una imagen o un GIF"
TEXTO_SIN_MODELO = ("Elige un modelo en Preferencias, Inteligencia "
                    "artificial.")
TEXTO_SIN_RED = ("No hay conexión con el proveedor. Comprueba la conexión a "
                 "internet.")


def _hilo_directo(funcion, _nombre, **kwargs):
    funcion(*kwargs.get("args", ()))
    return mock.Mock()


class EsperaFalsa:
    instancia = None

    def __init__(self, padre, titulo, texto, parada=None):
        self.padre = padre
        self.titulo = titulo
        self.texto = texto
        self.parada = parada
        self.resultado = wx.ID_CANCEL
        self.destruida = False
        EsperaFalsa.instancia = self

    def Bind(self, _tipo, _manejador, id=None):
        self.cancelar = _manejador

    def ShowModal(self):
        return self.resultado

    def EndModal(self, codigo):
        self.resultado = codigo

    def Destroy(self):
        self.destruida = True


class EsperaQueCancela(EsperaFalsa):
    def ShowModal(self):
        self.parada.set()
        return wx.ID_CANCEL


class TemporizadorFalso:
    def __init__(self, *_args, **_kwargs):
        pass

    def Start(self, _intervalo):
        pass

    def Stop(self):
        pass


def _ajustes(privacidad=True):
    return SimpleNamespace(
        proveedor="gemini", modelo="m", direccion="", pregunta="",
        largo="media", tiempo_espera=60, decir_analizando=True,
        privacidad_aceptada=privacidad)


def _datos(tipo="imagen", archivo="logo.png"):
    return {
        "nombre": "Logo",
        "descripcion": "Vieja",
        "tipo": tipo,
        "archivo": archivo,
        "duracion": 0 if tipo == "imagen" else 3,
    }


class BaseVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        self.base = Path(self.tmp.name)
        EsperaFalsa.instancia = None

    def _archivo(self, nombre, datos):
        ruta = self.base / nombre
        ruta.write_bytes(datos)
        return ruta

    def _config(self, privacidad=False):
        (self.base / "config.ini").write_text(
            "[ia]\nproveedor=gemini\nmodelo=m\nprivacidad_aceptada={}\n".format(
                "true" if privacidad else "false"),
            encoding="utf-8")

    def _cuadro(self, tipo="imagen", archivo="logo.png", ruta=None):
        cuadro = medio_cuadro.DialogoMedio(
            None, _datos(tipo, archivo), ruta=ruta)
        self.addCleanup(destruir, cuadro)
        cuadro.Show()
        self.addCleanup(cuadro.Hide)
        return cuadro

    def _parchear(self, objeto, atributo, valor):
        parche = mock.patch.object(objeto, atributo, valor)
        parche.start()
        self.addCleanup(parche.stop)
        return valor

    def _dobles_felices(self, respuesta):
        self._parchear(EsperaFalsa, "instancia", None)
        self._parchear(modulo, "VentanaEspera", EsperaFalsa)
        self._parchear(modulo.wx, "Timer", TemporizadorFalso)
        self._parchear(modulo.wx, "CallAfter",
                       lambda funcion, *args: funcion(*args))
        self._parchear(modulo.diagnostico, "crear_hilo", _hilo_directo)
        self._parchear(modulo.ajustes_ia, "leer", mock.Mock(
            return_value=_ajustes()))
        self._parchear(modulo.claves, "leer", mock.Mock(return_value="clave"))
        self._parchear(modulo.catalogo, "cargar", mock.Mock(return_value={}))
        self._parchear(modulo.consulta, "preparar", mock.Mock(
            return_value=consulta.Preparada(object(), "pregunta", 60)))
        self._parchear(modulo.proveedores, "por_id", mock.Mock(
            return_value=SimpleNamespace(nombre="Google Gemini")))
        self._parchear(modulo.ia_privacidad, "confirmar",
                       mock.Mock(return_value=True))
        envio = self._parchear(modulo.envio_ia, "enviar",
                               mock.Mock(return_value=respuesta))
        self._parchear(modulo, "reproducir", mock.Mock())
        self._parchear(medio_cuadro, "anunciar", mock.Mock())
        return envio


class TestConversion(BaseVentana):

    def test_una_imagen_png_se_convierte_a_jpeg(self):
        ruta = self._archivo("logo.png", PNG)
        self.assertEqual(modulo.jpeg_de(ruta)[:2], b"\xff\xd8")

    def test_un_gif_se_convierte_a_jpeg(self):
        ruta = self._archivo("logo.gif", GIF)
        self.assertEqual(modulo.jpeg_de(ruta)[:2], b"\xff\xd8")


class TestCuadro(BaseVentana):

    def test_con_una_imagen_escribe_limpia_mueve_el_foco_y_anuncia(self):
        ruta = self._archivo("logo.png", PNG)
        envio = self._dobles_felices(protocolos.Respuesta(
            '  "Una   risa\nfeliz"  ', False))
        cuadro = self._cuadro(ruta=ruta)
        cuadro.txt_descripcion.SetValue("Vieja")
        with mock.patch.object(medio_cuadro, "anunciar") as decir:
            cuadro._describir(None)
        self.assertEqual(cuadro.txt_descripcion.GetValue(), "Una risa feliz")
        self.assertIs(wx.Window.FindFocus(), cuadro.txt_descripcion)
        decir.assert_called_once_with("Descripción propuesta: Una risa feliz")
        envio.assert_called_once()
        self.assertIsNotNone(EsperaFalsa.instancia.parada)

    def test_con_un_video_o_un_sonido_no_manda_y_avisa(self):
        for tipo in ("sonido", "video"):
            with self.subTest(tipo=tipo):
                cuadro = self._cuadro(tipo=tipo, archivo="risa.wav")
                self.assertTrue(cuadro.btn_describir.IsEnabled())
                with mock.patch.object(modulo, "pedir") as pedir, \
                        mock.patch.object(medio_cuadro, "anunciar") as decir:
                    cuadro._describir(None)
                pedir.assert_not_called()
                decir.assert_called_once_with(TEXTO_SOLO_IMAGEN)

    def test_al_cancelar_la_espera_no_escribe_nada(self):
        ruta = self._archivo("logo.png", PNG)
        self._dobles_felices(protocolos.Respuesta("Otra cosa", False))
        self._parchear(modulo, "VentanaEspera", EsperaQueCancela)
        cuadro = self._cuadro(ruta=ruta)
        cuadro.txt_descripcion.SetValue("Vieja")
        with mock.patch.object(medio_cuadro, "anunciar") as decir:
            cuadro._describir(None)
        self.assertEqual(cuadro.txt_descripcion.GetValue(), "Vieja")
        decir.assert_not_called()

    def test_sin_ia_configurada_sale_el_error_y_el_campo_no_cambia(self):
        ruta = self._archivo("logo.png", PNG)
        self._parchear(modulo.claves, "leer", mock.Mock(return_value=None))
        envio = self._parchear(modulo.envio_ia, "enviar", mock.Mock())
        self._parchear(modulo, "reproducir", mock.Mock())
        cuadro = self._cuadro(ruta=ruta)
        cuadro.txt_descripcion.SetValue("Vieja")
        with mock.patch.object(confirmar, "avisar") as avisar:
            cuadro._describir(None)
        envio.assert_not_called()
        self.assertEqual(cuadro.txt_descripcion.GetValue(), "Vieja")
        self.assertEqual(avisar.call_args.args[1], TEXTO_SIN_MODELO)
        self.assertEqual(avisar.call_args.kwargs["icono"],
                         confirmar.ICON_ERROR)

    def test_si_el_envio_falla_sale_el_error_y_el_campo_no_cambia(self):
        ruta = self._archivo("logo.png", PNG)
        error = protocolos.ErrorIA(protocolos.SIN_RED)
        self._dobles_felices(None)
        self._parchear(modulo.envio_ia, "enviar", mock.Mock(side_effect=error))
        cuadro = self._cuadro(ruta=ruta)
        cuadro.txt_descripcion.SetValue("Vieja")
        with mock.patch.object(confirmar, "avisar") as avisar:
            cuadro._describir(None)
        self.assertEqual(cuadro.txt_descripcion.GetValue(), "Vieja")
        self.assertEqual(avisar.call_args.args[1], TEXTO_SIN_RED)

    def test_si_se_rechaza_la_privacidad_no_envia(self):
        ruta = self._archivo("logo.png", PNG)
        self._config()
        self._parchear(modulo.claves, "leer", mock.Mock(return_value="clave"))
        confirmacion = self._parchear(
            modulo.ia_privacidad, "confirmar", mock.Mock(return_value=False))
        envio = self._parchear(modulo.envio_ia, "enviar", mock.Mock())
        cuadro = self._cuadro(ruta=ruta)
        cuadro.txt_descripcion.SetValue("Vieja")
        cuadro._describir(None)
        envio.assert_not_called()
        self.assertEqual(cuadro.txt_descripcion.GetValue(), "Vieja")
        self.assertIs(confirmacion.call_args.args[0], cuadro)
        self.assertEqual(confirmacion.call_args.args[2], "Google Gemini")


if __name__ == "__main__":
    unittest.main()
