# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La unión entre los disparadores del directo y la tarjeta del vídeo."""

import os
import tempfile
import unittest
from unittest import mock

from guyrapu.core import paths
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.interaction import disparadores_guardados, filtro_publico
from guyrapu.ui import disparadores_en_vivo
from guyrapu.ui.lista_chat import MensajeChat
from tests.rutas_temporales import redirigir_rutas


def _datos(nombre="risa", cuando="comando", comandos=("risa",), evento="",
           minimo=None, medio="", tarjeta="Ríe {usuario}", estilo="clasico",
           segundos=8, permiso="todos", nombres=(), espera_general=5.0,
           espera_persona=0.0, activo=True):
    return {
        "nombre": nombre, "cuando": cuando, "comandos": list(comandos),
        "evento": evento, "minimo": minimo, "medio": medio,
        "tarjeta": tarjeta, "estilo": estilo, "segundos": segundos,
        "permiso": permiso, "nombres": list(nombres),
        "espera_general": espera_general, "espera_persona": espera_persona,
        "activo": activo,
    }


def _registro(texto="!risa", autor="Ana", plataforma="youtube",
              tipo=TIPO_TEXTO, monto=""):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador="C1", texto=texto, hora="12:00",
                       tipo=tipo, monto=monto, rol="")


class _Frame:
    def __init__(self, conectado=True):
        self._conectado = conectado
        self._capa_video = mock.Mock()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        self.ahora = 0.0
        self.frame = _Frame()

    def _guardar(self, *disparadores):
        disparadores_guardados.guardar(paths.disparadores(),
                                       list(disparadores))

    def _guardar_palabras(self, palabras):
        filtro_publico.guardar(paths.palabras_bloqueadas(), palabras)

    def _adelantar(self, ruta):
        futuro = ruta.stat().st_mtime + 10
        os.utime(ruta, (futuro, futuro))

    def _atender(self, registro=None, ahora=None):
        disparadores_en_vivo.atender(
            self.frame, registro or _registro(),
            self.ahora if ahora is None else ahora)

    def _textos(self):
        return [llamada.args[0].texto for llamada in
                self.frame._capa_video.agregar_pieza.call_args_list]


class TestPiezaDeDisparador(Base):

    def test_un_comando_cumplido_agrega_su_tarjeta_con_estilo_segundos_y_nombre(self):
        self._guardar(_datos(nombre="risa", tarjeta="Ríe {usuario}",
                             estilo="banda", segundos=12))
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_called_once()
        pieza = self.frame._capa_video.agregar_pieza.call_args.args[0]
        self.assertEqual((pieza.tipo, pieza.texto, pieza.segundos),
                         ("disparador", "Ríe Ana", 12))
        self.assertEqual(pieza.datos,
                         {"estilo": "banda", "nombre": "risa"})

    def test_repetido_antes_de_la_espera_general_no_agrega_otra(self):
        self._guardar(_datos(espera_general=5, espera_persona=0))
        self._atender(ahora=0)
        self._atender(ahora=3)
        self.frame._capa_video.agregar_pieza.assert_called_once()
        self._atender(ahora=5)
        self.assertEqual(
            self.frame._capa_video.agregar_pieza.call_count, 2)


class TestEventoDelDirecto(Base):

    def test_el_superchat_solo_cumple_desde_el_minimo(self):
        self._guardar(_datos(
            nombre="regalo", cuando="evento", comandos=(),
            evento="superchat", minimo=5, tarjeta="Gracias",
            espera_general=0, espera_persona=0))
        self._atender(_registro(texto="", tipo=TIPO_SUPERCHAT,
                                monto="US$4.99"), ahora=0)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._atender(_registro(texto="", tipo=TIPO_SUPERCHAT,
                                monto="US$5.00"), ahora=1)
        self.frame._capa_video.agregar_pieza.assert_called_once()


class TestUsuario(Base):

    def test_el_usuario_sale_con_las_palabras_bloqueadas_tapadas(self):
        self._guardar(_datos(tarjeta="Hola {usuario}", espera_general=0,
                             espera_persona=0))
        self._guardar_palabras(["tonto"])
        self._atender(_registro(autor="Tonto"))
        self.assertEqual(self._textos(), ["Hola ***"])


class TestSinTarjeta(Base):

    def test_sin_tarjeta_no_agrega_pero_su_uso_cuenta_para_la_espera(self):
        self._guardar(_datos(tarjeta="", medio="fuegos", espera_general=5))
        self._atender(ahora=0)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._guardar(_datos(tarjeta="Ríe", medio="fuegos",
                             espera_general=5))
        self._adelantar(paths.disparadores())
        self._atender(ahora=3)
        self.frame._capa_video.agregar_pieza.assert_not_called()
        self._atender(ahora=5)
        self.frame._capa_video.agregar_pieza.assert_called_once()


class TestRecarga(Base):

    def test_cambiar_el_archivo_entre_dos_mensajes_cambia_lo_que_se_agrega(self):
        self._guardar(_datos(tarjeta="Uno", espera_general=0,
                             espera_persona=0))
        self._atender(ahora=0)
        self._guardar(_datos(tarjeta="Dos", espera_general=0,
                             espera_persona=0))
        self._adelantar(paths.disparadores())
        self._atender(ahora=1)
        self.assertEqual(self._textos(), ["Uno", "Dos"])

    def test_cambiar_las_palabras_entre_dos_mensajes_cambia_la_tarjeta(self):
        self._guardar(_datos(tarjeta="Hola {usuario}", espera_general=0,
                             espera_persona=0))
        self._guardar_palabras(["tonto"])
        self._atender(_registro(autor="Tonto"), ahora=0)
        self._guardar_palabras([])
        self._adelantar(paths.palabras_bloqueadas())
        self._atender(_registro(autor="Tonto"), ahora=1)
        self.assertEqual(self._textos(), ["Hola ***", "Hola Tonto"])


class TestDesconectado(Base):

    def test_sin_chat_conectado_no_agrega_nada(self):
        self._guardar(_datos())
        self.frame._conectado = False
        self._atender()
        self.frame._capa_video.agregar_pieza.assert_not_called()


if __name__ == "__main__":
    unittest.main()
