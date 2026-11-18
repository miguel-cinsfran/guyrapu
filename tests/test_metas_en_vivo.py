# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El avance de las metas del directo y su tarjeta en el vídeo."""

import os
import tempfile
import unittest
from unittest import mock

from guyrapu.core import paths
from guyrapu.core.config import TIPO_ME_GUSTA, TIPO_TEXTO
from guyrapu.interaction import medios_guardados, metas_guardadas
from guyrapu.ui import gui_sesion, metas_en_vivo
from guyrapu.ui.lista_chat import MensajeChat
from tests.rutas_temporales import redirigir_rutas


def _meta(nombre="Risa", que_cuenta="me_gusta", objetivo=3, estilo="",
          festejo="", activa=True):
    return {
        "nombre": nombre, "que_cuenta": que_cuenta, "objetivo": objetivo,
        "estilo": estilo, "festejo": festejo, "activa": activa,
    }


def _medio(nombre="fuegos", tipo="video", archivo="fuegos.mp4", duracion=12,
           ganancia_db=None):
    return {"nombre": nombre, "tipo": tipo, "archivo": archivo,
            "duracion": duracion, "ganancia_db": ganancia_db}


def _registro(texto="hola", autor="Ana", plataforma="tiktok",
              tipo=TIPO_ME_GUSTA, monto="1"):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador="C1", texto=texto, hora="12:00",
                       tipo=tipo, monto=monto, rol="")


class _Frame:
    def __init__(self, conectado=True):
        self._conectado = conectado
        self._capa_video = mock.Mock()
        self.sesion = None
        self.chat_vivo = mock.Mock()
        self.chat_vivo.participacion.vacia.return_value = True
        self.lb_chat = mock.Mock()
        self._sc_totales = {}
        self._metadatos = {}
        self.txt_info = mock.Mock()
        self._rep_panel = mock.Mock()
        self._com_panel = mock.Mock()
        self._worker = mock.Mock()
        self._stats = mock.Mock()
        self._actualizar_sb = mock.Mock()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        self.frame = _Frame()

    def _guardar(self, *metas):
        metas_guardadas.guardar(paths.metas(), list(metas))

    def _guardar_medios(self, *medios):
        medios_guardados.guardar(paths.medios(), list(medios))
        carpeta = paths.carpeta_medios()
        carpeta.mkdir(parents=True, exist_ok=True)
        for medio in medios:
            (carpeta / medio["archivo"]).write_bytes(b"x")

    def _adelantar(self, ruta):
        futuro = ruta.stat().st_mtime + 10
        os.utime(ruta, (futuro, futuro))

    def _atender(self, registro=None):
        metas_en_vivo.atender(self.frame, registro or _registro())

    def _piezas(self):
        return [llamada.args[0] for llamada in
                self.frame._capa_video.agregar_pieza.call_args_list]

    def _progreso(self, nombre="Risa"):
        return metas_en_vivo._en_vivo(self.frame)._progresos[nombre]


class TestAvance(Base):

    def test_p1_un_me_gusta_suma_a_la_meta_activa(self):
        self._guardar(_meta(objetivo=10))
        self._atender(_registro(monto="2"))
        self.assertEqual(self._progreso().valor, 2)
        self._atender(_registro(monto="3"))
        self.assertEqual(self._progreso().valor, 5)

    def test_p1_una_meta_en_pausa_no_suma(self):
        self._guardar(_meta(objetivo=1, activa=False))
        self._atender(_registro(monto="1"))
        self.assertEqual(self._progreso().valor, 0)
        self.assertEqual(self._piezas(), [])

    def test_p1_solo_cuenta_los_eventos_de_su_que_cuenta(self):
        self._guardar(_meta(objetivo=1))
        self._atender(_registro(tipo=TIPO_TEXTO, texto="hola", monto=""))
        self.assertEqual(self._progreso().valor, 0)


class TestMetaCumplida(Base):

    def _avisos(self):
        return [llamada.args for llamada in
                self.frame._avisar.call_args_list]

    def setUp(self):
        super().setUp()
        self.frame._avisar = mock.Mock()

    def test_p2_anuncia_una_sola_vez_al_cumplirse(self):
        self._guardar(_meta(objetivo=2))
        with mock.patch.object(metas_en_vivo, "anunciar_con_sonido",
                               self.frame._avisar):
            self._atender(_registro(monto="1"))
            self._atender(_registro(monto="1"))
            self._atender(_registro(monto="5"))
        self.assertEqual(self._avisos(),
                         [("Meta cumplida: Risa.", "meta_cumplida")])


class TestTarjeta(Base):

    def test_p3_con_festejo_en_la_biblioteca_la_pieza_lleva_su_medio(self):
        self._guardar_medios(_medio(ganancia_db=-6.0))
        self._guardar(_meta(objetivo=1, estilo="banda", festejo="fuegos"))
        self._atender()
        pieza = self._piezas()[0]
        self.assertEqual((pieza.tipo, pieza.texto),
                         ("meta", "Risa: meta cumplida"))
        self.assertEqual(pieza.segundos, 12)
        self.assertEqual(pieza.datos["estilo"], "banda")
        self.assertEqual(pieza.datos["nombre"], "Risa")
        self.assertEqual(pieza.datos["medio"], {
            "ruta": str(paths.carpeta_medios() / "fuegos.mp4"),
            "tipo": "video", "duracion": 12, "ganancia_db": -6.0})

    def test_p3_sin_festejo_la_pieza_dura_diez_segundos_y_no_lleva_medio(self):
        self._guardar(_meta(objetivo=1))
        self._atender()
        pieza = self._piezas()[0]
        self.assertEqual(pieza.segundos, 10)
        self.assertNotIn("medio", pieza.datos)

    def test_p3_un_festejo_que_ya_no_esta_sale_sin_medio(self):
        self._guardar(_meta(objetivo=1, festejo="fuegos"))
        self._atender()
        pieza = self._piezas()[0]
        self.assertEqual((pieza.tipo, pieza.texto),
                         ("meta", "Risa: meta cumplida"))
        self.assertEqual(pieza.segundos, 10)
        self.assertNotIn("medio", pieza.datos)

    def test_p3_un_sonido_de_festejo_dura_lo_que_su_archivo(self):
        self._guardar_medios(_medio(tipo="sonido", archivo="fuegos.wav",
                                    duracion=4))
        self._guardar(_meta(objetivo=1, festejo="fuegos"))
        self._atender()
        self.assertEqual(self._piezas()[0].segundos, 4)

    def test_p3_un_estilo_vacio_queda_vacio_para_el_predeterminado(self):
        self._guardar(_meta(objetivo=1, estilo=""))
        self._atender()
        self.assertEqual(self._piezas()[0].datos["estilo"], "")


class TestReinicioYRecarga(Base):

    def test_p5_reiniciar_los_datos_de_la_sesion_vuelve_el_avance_a_cero(self):
        self._guardar(_meta(objetivo=10))
        self._atender(_registro(monto="2"))
        gui_sesion.reiniciar_datos_sesion(self.frame)
        self._atender(_registro(monto="1"))
        self.assertEqual(self._progreso().valor, 1)

    def test_p5_reiniciar_vacia_la_cola_y_detiene_lo_que_se_lee(self):
        self._guardar(_meta(objetivo=10))
        self._atender(_registro(monto="1"))
        gui_sesion.reiniciar_datos_sesion(self.frame)
        self.frame._worker.vaciar_cola.assert_called_once_with()
        self.frame._worker.detener_actual.assert_called_once_with()

    def test_p5_recargar_el_archivo_conserva_el_avance_de_las_que_siguen(self):
        self._guardar(_meta(nombre="Risa", objetivo=10),
                      _meta(nombre="Otra", objetivo=10))
        self._atender(_registro(monto="2"))
        self._guardar(_meta(nombre="Risa", objetivo=5),
                      _meta(nombre="Otra", objetivo=10),
                      _meta(nombre="Nueva", objetivo=10))
        self._adelantar(paths.metas())
        self._atender(_registro(monto="1"))
        self.assertEqual(self._progreso("Risa").valor, 3)
        self.assertEqual(self._progreso("Otra").valor, 3)
        self.assertEqual(self._progreso("Nueva").valor, 1)


if __name__ == "__main__":
    unittest.main()
