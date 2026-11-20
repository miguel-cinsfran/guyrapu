# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las ocho acciones de lo que sale en el vídeo y lo que anuncian.

La capa se sustituye por una de prueba que anota lo que le piden. El pánico
se prueba con una cola real detrás para comprobar que al apagarlo vuelve a
aceptar piezas.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.interaction.cola_pantalla import ColaPantalla, Pieza
from guyrapu.ui import (
    comando_en_directo, comando_mensajes_automaticos, preguntas_en_vivo)
from guyrapu.ui import gui_envio_chat


class _Capa:
    """Capa de prueba: guarda su estado y anota cada pedido."""

    def __init__(self):
        self.estado_cola = {"pausado": False, "silenciado": False,
                            "panico": False}
        self.llamadas = []
        self.habia = True

    def estado(self):
        return dict(self.estado_cola)

    def pausar(self):
        self.llamadas.append("pausar")
        self.estado_cola["pausado"] = True

    def reanudar(self):
        self.llamadas.append("reanudar")
        self.estado_cola["pausado"] = False

    def saltar(self):
        self.llamadas.append("saltar")
        return self.habia

    def vaciar(self):
        self.llamadas.append("vaciar")
        return self.habia

    def silenciar(self, activo):
        self.llamadas.append(("silenciar", activo))
        self.estado_cola["silenciado"] = bool(activo)

    def panico(self, activo):
        self.llamadas.append(("panico", activo))
        self.estado_cola["panico"] = bool(activo)


class _CapaConCola(_Capa):
    """Capa de prueba con una cola real para mirar el efecto del pánico."""

    def __init__(self):
        super().__init__()
        self.cola = ColaPantalla()

    def panico(self, activo):
        super().panico(activo)
        self.cola.panico(activo)


class Base(unittest.TestCase):
    def setUp(self):
        self.capa = _Capa()
        self.anuncios = []
        self.frame = SimpleNamespace(
            _config={},
            mi_video_pausar=mock.Mock(),
            mi_video_silenciar=mock.Mock(),
            mi_video_panico=mock.Mock(),
            mi_comandos_pausar=mock.Mock(),
        )
        self.parche_capa = mock.patch.object(
            gui_envio_chat, "capa_de_video", return_value=self.capa)
        self.parche_capa.start()
        self.addCleanup(self.parche_capa.stop)
        self.parche_anuncio = mock.patch.object(
            comando_en_directo, "anunciar_con_sonido",
            side_effect=lambda texto, sonido:
                self.anuncios.append((texto, sonido)))
        self.parche_anuncio.start()
        self.addCleanup(self.parche_anuncio.stop)

    def _pieza(self):
        return Pieza(tipo="mensaje", texto="Hola", segundos=10, datos={})


class TestPausa(Base):

    def test_pausa_y_reanuda_diciendo_el_estado_nuevo(self):
        comando_en_directo.alternar_pausa(self.frame)
        self.assertEqual(self.capa.llamadas, ["pausar"])
        self.assertEqual(self.anuncios,
                         [("Cola del vídeo en pausa", "video_pausa")])
        self.frame.mi_video_pausar.Check.assert_called_once_with(True)

        comando_en_directo.alternar_pausa(self.frame)
        self.assertEqual(self.capa.llamadas, ["pausar", "reanudar"])
        self.assertEqual(self.anuncios[-1],
                         ("Cola del vídeo reanudada", "video_reanudar"))
        self.frame.mi_video_pausar.Check.assert_called_with(False)


class TestSaltarYVaciar(Base):

    def test_omitir_dice_lo_que_hizo(self):
        comando_en_directo.saltar(self.frame)
        self.assertEqual(self.capa.llamadas, ["saltar"])
        self.assertEqual(self.anuncios,
                         [("Mensaje del vídeo omitido", "listo")])

    def test_omitir_sin_nada_dice_nada_en_el_video(self):
        self.capa.habia = False
        comando_en_directo.saltar(self.frame)
        self.assertEqual(self.anuncios, [("No hay nada en el vídeo.", "listo")])

    def test_vaciar_dice_lo_que_hizo(self):
        comando_en_directo.vaciar(self.frame)
        self.assertEqual(self.capa.llamadas, ["vaciar"])
        self.assertEqual(self.anuncios,
                         [("Cola del vídeo vacía", "listo")])

    def test_vaciar_sin_nada_dice_nada_en_el_video(self):
        self.capa.habia = False
        comando_en_directo.vaciar(self.frame)
        self.assertEqual(self.anuncios, [("No hay nada en el vídeo.", "listo")])


class TestSilencio(Base):

    def test_silencia_y_activa_diciendo_el_estado_nuevo(self):
        comando_en_directo.alternar_silencio(self.frame)
        self.assertEqual(self.capa.llamadas, [("silenciar", True)])
        self.assertEqual(self.anuncios,
                         [("Medios silenciados", "video_silenciar")])
        self.frame.mi_video_silenciar.Check.assert_called_once_with(True)

        comando_en_directo.alternar_silencio(self.frame)
        self.assertEqual(self.capa.llamadas,
                         [("silenciar", True), ("silenciar", False)])
        self.assertEqual(self.anuncios[-1], ("Medios activados", "video_audio"))
        self.frame.mi_video_silenciar.Check.assert_called_with(False)


class TestPanico(Base):

    def test_activa_y_desactiva_diciendo_el_estado_nuevo(self):
        comando_en_directo.alternar_panico(self.frame)
        self.assertEqual(self.capa.llamadas, [("panico", True)])
        self.assertEqual(self.anuncios,
                         [("Modo pánico activado", "video_panico")])
        self.frame.mi_video_panico.Check.assert_called_once_with(True)

        comando_en_directo.alternar_panico(self.frame)
        self.assertEqual(self.capa.llamadas,
                         [("panico", True), ("panico", False)])
        self.assertEqual(self.anuncios[-1],
                         ("Modo pánico desactivado", "video_panico_fin"))
        self.frame.mi_video_panico.Check.assert_called_with(False)

    def test_al_apagarlo_la_cola_vuelve_a_dejar_pasar(self):
        self.capa = _CapaConCola()
        self.parche_capa.stop()
        self.parche_capa = mock.patch.object(
            gui_envio_chat, "capa_de_video", return_value=self.capa)
        self.parche_capa.start()
        self.addCleanup(self.parche_capa.stop)

        comando_en_directo.alternar_panico(self.frame)
        self.assertFalse(self.capa.cola.agregar(self._pieza()))
        comando_en_directo.alternar_panico(self.frame)
        self.assertTrue(self.capa.cola.agregar(self._pieza()))


class TestComandos(Base):

    def test_alternar_dos_veces_anuncia_y_marca_la_casilla(self):
        comando_en_directo.alternar_comandos(self.frame)
        self.assertEqual(self.anuncios,
                         [("Comandos en pausa", "comandos_pausa")])
        self.frame.mi_comandos_pausar.Check.assert_called_once_with(True)
        self.assertIn("Comandos en pausa",
                      self.frame._comandos_en_vivo.frase_estado())

        comando_en_directo.alternar_comandos(self.frame)
        self.assertEqual(self.anuncios[-1],
                         ("Comandos reanudados", "comandos_reanudar"))
        self.frame.mi_comandos_pausar.Check.assert_called_with(False)
        self.assertEqual(self.frame._comandos_en_vivo.frase_estado(), "")


class TestCerrarEncuesta(Base):

    def test_sin_encuesta_dice_que_no_hay_ninguna(self):
        with mock.patch.object(
                comando_en_directo.encuesta_en_vivo, "cerrar",
                return_value=False) as cerrar:
            comando_en_directo.cerrar_encuesta(self.frame)
        cerrar.assert_called_once_with(self.frame)
        self.assertEqual(self.anuncios,
                         [("No hay ninguna encuesta abierta", "listo")])

    def test_con_encuesta_abierta_el_modulo_anuncia_el_resultado(self):
        with mock.patch.object(
                comando_en_directo.encuesta_en_vivo, "cerrar",
                return_value=True) as cerrar:
            comando_en_directo.cerrar_encuesta(self.frame)
        cerrar.assert_called_once_with(self.frame)
        self.assertEqual(self.anuncios, [])


class TestMensajesAutomaticos(Base):

    def test_llama_al_comando_que_ya_existe(self):
        with mock.patch.object(
                comando_mensajes_automaticos, "alternar") as alternar:
            comando_en_directo.alternar_mensajes(self.frame)
        alternar.assert_called_once_with(self.frame)


class TestEstadoInteraccion(Base):

    def _anunciar(self, snap, preguntas):
        self.frame._snapshot_sesion = lambda: snap
        anuncios = []
        with mock.patch.object(preguntas_en_vivo, "pendientes",
                               return_value=preguntas), \
                mock.patch.object(comando_en_directo, "anunciar",
                                  side_effect=anuncios.append):
            comando_en_directo.estado_interaccion(self.frame)
        return anuncios

    def test_con_encuesta_y_dos_preguntas_anuncia_las_dos_cosas(self):
        snap = SimpleNamespace(
            encuesta="Encuesta en curso: X. Opciones: A, B",
            batalla="", meta="", video="")
        self.assertEqual(self._anunciar(snap, [object(), object()]), [
            "Encuesta en curso: X. Opciones: A, B; 2 preguntas en espera."])

    def test_sin_nada_anuncia_p3(self):
        snap = SimpleNamespace(encuesta="", batalla="", meta="", video="")
        self.assertEqual(self._anunciar(snap, []), [
            "No hay nada de la interacción en curso."])


if __name__ == "__main__":
    unittest.main()
