# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Prueba del aviso sonoro de la actualización de modelos, sin wx de verdad."""

import unittest
from unittest import mock

from guyrapu.ai import catalogo
from guyrapu.ai import opciones_ia
from guyrapu.ai import protocolos
from guyrapu.ai import proveedores
from guyrapu.ui import preferencias_ia_lista


def _muestra():
    base = "https://generativelanguage.googleapis.com/v1beta"
    return {
        "version": catalogo.VERSION,
        "fecha": "2026-10-21",
        "proveedores": {
            "google": {
                "nombre": "Google",
                "modelos": [
                    {"id": "modelo-elegido", "nombre": "Modelo Elegido",
                     "protocolo": protocolos.GEMINI, "base": base},
                    {"id": "otro", "nombre": "Otro",
                     "protocolo": protocolos.GEMINI, "base": base},
                ],
            },
        },
    }


class _Panel:
    def Bind(self, _evento, _manejador, *_argumentos):
        pass


class _Boton:
    def __init__(self):
        self.habilitado = True
        self._padre = _Panel()

    def Bind(self, _evento, _manejador, *_argumentos):
        pass

    def GetParent(self):
        return self._padre

    def Disable(self):
        self.habilitado = False

    def Enable(self):
        self.habilitado = True

    def __bool__(self):
        return True


class _Temporizador:
    def __init__(self, _duenio):
        self.corriendo = False
        self.intervalo = 0

    def Start(self, intervalo):
        self.intervalo = intervalo
        self.corriendo = True

    def Stop(self):
        self.corriendo = False

    def IsRunning(self):
        return self.corriendo

    def GetInterval(self):
        return self.intervalo


class TestActualizacionModelosIA(unittest.TestCase):

    def _actualizacion(self, elegido=lambda: "modelo-elegido"):
        boton = _Boton()
        with mock.patch.object(
                preferencias_ia_lista.wx, "Timer", _Temporizador):
            return preferencias_ia_lista.ActualizacionModelosIA(
                boton, lambda: proveedores.por_id("gemini"),
                lambda muestra, marcas, proveedor: 3, elegido)

    def test_recibir_frena_el_temporizador_al_terminar(self):
        actualizacion = self._actualizacion()
        actualizacion._temporizador.Start(
            preferencias_ia_lista.INTERVALO_ANALIZANDO_MS)
        with mock.patch.object(
                preferencias_ia_lista.sondeo_gratis, "leer",
                return_value={}), \
                mock.patch.object(
                    preferencias_ia_lista._snd, "reproducir"), \
                mock.patch.object(preferencias_ia_lista, "anunciar"):
            actualizacion.recibir({"proveedores": {}})
        self.assertFalse(actualizacion._temporizador.IsRunning())

    def test_recibir_avisa_el_modelo_elegido_que_no_responde(self):
        actualizacion = self._actualizacion()
        resultados = {
            "modelo-elegido": preferencias_ia_lista.sondeo_gratis.SIN_SABER,
            "otro": preferencias_ia_lista.sondeo_gratis.RESPONDE,
        }
        with mock.patch.object(
                preferencias_ia_lista.sondeo_gratis, "leer",
                return_value={}), \
                mock.patch.object(
                    preferencias_ia_lista._snd, "reproducir") as sonar, \
                mock.patch.object(
                    preferencias_ia_lista, "anunciar") as anunciar:
            actualizacion.recibir(_muestra(), resultados)
        anunciar.assert_called_once_with(
            "Lista de modelos actualizada: 2 modelos de Google Gemini, "
            "1 funcionan con tu clave. El modelo elegido, modelo-elegido, "
            "no respondió con tu clave. Elige otro.")
        sonar.assert_called_once_with("ia_error")

    def test_recibir_sin_aviso_para_el_modelo_elegido_que_responde(self):
        actualizacion = self._actualizacion()
        resultados = {
            "modelo-elegido": preferencias_ia_lista.sondeo_gratis.RESPONDE,
            "otro": preferencias_ia_lista.sondeo_gratis.RESPONDE,
        }
        with mock.patch.object(
                preferencias_ia_lista.sondeo_gratis, "leer",
                return_value={}), \
                mock.patch.object(
                    preferencias_ia_lista._snd, "reproducir") as sonar, \
                mock.patch.object(
                    preferencias_ia_lista, "anunciar") as anunciar:
            actualizacion.recibir(_muestra(), resultados)
        anunciar.assert_called_once_with(
            "Lista de modelos actualizada: 2 modelos de Google Gemini, "
            "2 funcionan con tu clave.")
        sonar.assert_called_once_with("ia_respuesta")

    def test_recibir_sin_sondeo_anuncia_como_hoy(self):
        actualizacion = self._actualizacion()
        with mock.patch.object(
                preferencias_ia_lista.sondeo_gratis, "leer",
                return_value={}), \
                mock.patch.object(
                    preferencias_ia_lista._snd, "reproducir") as sonar, \
                mock.patch.object(
                    preferencias_ia_lista, "anunciar") as anunciar:
            actualizacion.recibir(_muestra())
        anunciar.assert_called_once_with(
            opciones_ia.TEXTO_LISTA_ACTUALIZADA.format(
                n=3, proveedor="Google Gemini"))
        sonar.assert_called_once_with("ia_respuesta")


if __name__ == "__main__":
    unittest.main()
