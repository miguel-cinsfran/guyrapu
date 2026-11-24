# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La encuesta abierta de la sesión: abrir, votar, poner al día y cerrar."""

import types
import unittest
from unittest import mock

from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import encuesta_en_vivo


def _datos(pregunta="¿Qué pizza?", **cambios):
    datos = {
        "pregunta": pregunta,
        "nombre": pregunta,
        "opciones": ["muzzarella", "napolitana", "fugazzeta"],
        "segundos": 120,
        "destino": "video",
        "estilo": "clasico",
    }
    datos.update(cambios)
    return datos


def _evento(texto, autor="Ana", autor_id="A"):
    return desde_entrante(autor, texto, "texto", "", autor_id, "", "youtube")


class _Timer:
    """Temporizador doble: no crea ventanas ni dispara solo."""

    def __init__(self, _frame, _manejador):
        self.ms = None
        self.activo = False

    def Start(self, ms):
        self.ms = ms
        self.activo = True

    def Stop(self):
        self.activo = False


class _Capa:
    """Capa de prueba: anota lo que le piden para la encuesta."""

    def __init__(self):
        self.fijadas = []
        self.al_dia = []
        self.quitadas = 0
        self.agregadas = []

    def fijar_encuesta(self, pieza):
        self.fijadas.append(pieza)

    def poner_al_dia_encuesta(self, pieza):
        self.al_dia.append(pieza)
        return True

    def quitar_encuesta(self):
        self.quitadas += 1

    def agregar_pieza(self, pieza):
        self.agregadas.append(pieza)


class Base(unittest.TestCase):

    def setUp(self):
        self.capa = _Capa()
        self.frame = types.SimpleNamespace(
            _conectado=True, sesion=object(), Bind=mock.Mock())
        self.reloj = [0.0]
        self.anuncios = []
        self.enviados = []
        parches = (
            mock.patch.object(encuesta_en_vivo, "_capa",
                              return_value=self.capa),
            mock.patch.object(
                encuesta_en_vivo, "_avisar",
                side_effect=lambda texto, sonido: self.anuncios.append(
                    (texto, sonido))),
            mock.patch.object(
                encuesta_en_vivo, "_enviar_chat",
                side_effect=lambda frame, texto: self.enviados.append(texto)),
            mock.patch.object(encuesta_en_vivo, "_temporizador", _Timer),

        )
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)

    def _iniciar(self, **cambios):
        datos = _datos(**cambios)
        encuesta_en_vivo.iniciar(
            self.frame, datos, ahora=self.reloj[0],
            reloj=lambda: self.reloj[0])
        return datos

    def _sesion(self):
        return self.frame._encuesta_en_vivo

    def _votar(self, texto, autor="Ana", autor_id="A"):
        return encuesta_en_vivo.votar(
            self.frame, _evento(texto, autor, autor_id), self.reloj[0])


class TestIniciar(Base):

    def test_abre_con_la_duracion_guardada(self):
        self._iniciar(segundos=180)
        encuesta = self._sesion().encuesta
        self.assertEqual(encuesta.segundos, 180)
        self.assertTrue(encuesta.abierta(179))
        self.assertFalse(encuesta.abierta(180))
        self.assertEqual(self.anuncios[-1][1], "listo")
        self.assertIn("¿Qué pizza?", self.anuncios[-1][0])

    def test_la_pieza_del_video_lleva_pregunta_respuestas_y_tiempo(self):
        self._iniciar()
        pieza = self.capa.fijadas[0]
        self.assertEqual((pieza.tipo, pieza.segundos), ("encuesta", 0))
        self.assertEqual(pieza.datos["estilo"], "clasico")
        self.assertIn("¿Qué pizza?", pieza.texto)
        self.assertIn("1, muzzarella: 0 votos.", pieza.texto)
        self.assertIn("Quedan 120 segundos.", pieza.texto)


class TestVotar(Base):

    def test_tres_votos_de_dos_personas_cuentan_dos(self):
        self._iniciar()
        self.assertTrue(self._votar("!1", "Ana", "A"))
        self.assertTrue(self._votar("!1", "Beto", "B"))
        self.assertTrue(self._votar("!2", "Ana", "A"))
        self.assertEqual(self._sesion().encuesta.votos(), [2, 0, 0])
        self.assertEqual(self._sesion().encuesta.total(), 2)

    def test_una_cifra_fuera_de_rango_no_cuenta(self):
        self._iniciar()
        self.assertTrue(self._votar("!1", "Ana", "A"))
        self.assertTrue(self._votar("!7", "Beto", "B"))
        self.assertEqual(self._sesion().encuesta.votos(), [1, 0, 0])
        self.assertEqual(self._sesion().encuesta.total(), 1)

    def test_un_texto_que_no_es_cifra_no_es_voto(self):
        self._iniciar()
        self.assertFalse(self._votar("!discord"))
        self.assertEqual(self._sesion().encuesta.total(), 0)


class TestPonerAlDia(Base):

    def test_dos_votos_seguidos_ponen_al_dia_una_sola_vez_en_dos_segundos(self):
        self._iniciar()
        self.reloj[0] = 1.0
        self._votar("!1", "Ana", "A")
        self.reloj[0] = 1.5
        self._votar("!2", "Beto", "B")
        self.assertEqual(self.capa.al_dia, [])
        self.reloj[0] = 2.0
        self._sesion()._latido()
        self.assertEqual(len(self.capa.al_dia), 1)
        self.assertIn("1, muzzarella: 1 voto.", self.capa.al_dia[0].texto)
        self.assertIn("2, napolitana: 1 voto.", self.capa.al_dia[0].texto)


class TestCerrar(Base):

    def test_al_cumplirse_el_tiempo_cierra_anuncia_y_suena_el_aviso(self):
        self._iniciar(segundos=120)
        self.reloj[0] = 120.0
        self._sesion()._latido()
        self.assertIsNone(self._sesion().encuesta)
        texto, sonido = self.anuncios[-1]
        self.assertEqual(sonido, "encuesta_cerrada")
        self.assertIn("Cerrada.", texto)
        self.assertEqual(self.capa.quitadas, 1)
        self.assertIn("Cerrada.", self.capa.agregadas[0].texto)

    def test_cerrar_a_mano_reparte_el_resultado_al_video_y_no_al_chat(self):
        self._iniciar(destino="video")
        self.reloj[0] = 10.0
        self.assertTrue(encuesta_en_vivo.cerrar(self.frame))
        self.assertEqual(self.anuncios[-1][1], "listo")
        self.assertIn("Cerrada.", self.anuncios[-1][0])
        self.assertEqual(self.capa.quitadas, 1)
        pieza = self.capa.agregadas[0]
        self.assertEqual((pieza.tipo, pieza.segundos), ("encuesta", 10))
        self.assertIn("Encuesta: ¿Qué pizza?", pieza.texto)
        self.assertEqual(self.enviados, [])

    def test_cerrar_con_destino_chat_usa_el_mismo_envio(self):
        self._iniciar(destino="chat")
        self.reloj[0] = 10.0
        self.assertTrue(encuesta_en_vivo.cerrar(self.frame))
        self.assertEqual(self.capa.agregadas, [])
        self.assertEqual(len(self.enviados), 1)
        self.assertIn("Cerrada.", self.enviados[0])

    def test_sin_chat_conectado_el_resultado_se_anuncia_igual(self):
        self._iniciar(destino="chat")
        self.reloj[0] = 10.0
        with mock.patch.object(encuesta_en_vivo, "_enviar_chat",
                               return_value=False):
            self.assertTrue(encuesta_en_vivo.cerrar(self.frame))
        self.assertIn("Cerrada.", self.anuncios[-1][0])

    def test_sin_encuesta_abierta_no_hace_nada(self):
        self.assertFalse(encuesta_en_vivo.cerrar(self.frame))
        self.assertEqual(self.anuncios, [])


class TestFraseDeF2(Base):

    def test_dice_pregunta_votos_y_tiempo(self):
        self._iniciar(segundos=120)
        self.reloj[0] = 30.0
        self._votar("!2", "Ana", "A")
        frase = encuesta_en_vivo.frase_estado(self.frame)
        self.assertIn("Encuesta: ¿Qué pizza?", frase)
        self.assertIn("2, napolitana: 1 voto.", frase)
        self.assertIn("Quedan 90 segundos.", frase)

    def test_sin_encuesta_queda_vacia(self):
        self.assertEqual(encuesta_en_vivo.frase_estado(self.frame), "")


class TestFinDeLaSesion(Base):

    def test_cambiar_de_sesion_descarta_sin_repartir_resultado(self):
        self._iniciar()
        self.frame.sesion = object()
        self._sesion()._latido()
        self.assertIsNone(self._sesion().encuesta)
        self.assertEqual(self.capa.quitadas, 1)
        self.assertEqual(self.capa.agregadas, [])
        self.assertEqual(self.enviados, [])


class TestAvisosDelAvance(Base):

    def test_un_latido_a_diez_segundos_anuncia_por_terminar_una_sola_vez(self):
        self._iniciar(segundos=120)
        self.anuncios.clear()
        self.reloj[0] = 110.0
        self._sesion()._latido()
        self.assertEqual(self.anuncios[-1], (
            "Quedan 10 segundos de la encuesta.", "encuesta_por_terminar"))
        self.anuncios.clear()
        self.reloj[0] = 109.0
        self._sesion()._latido()
        self.assertEqual(self.anuncios, [])

    def test_un_voto_nuevo_ganador_anuncia_el_cambio_de_opcion(self):
        self._iniciar(segundos=120)
        self.anuncios.clear()
        self._votar("!1", "Ana", "A")
        self.reloj[0] = 15.0
        self._votar("!2", "Beto", "B")
        self._votar("!2", "Cara", "C")
        self.assertEqual(self.anuncios[-1], (
            "Va ganando napolitana, con 2 votos.", "encuesta_ganadora"))

    def test_con_avisar_apagado_no_anuncia_ni_el_tiempo_ni_el_ganador(self):
        self._iniciar(segundos=120, avisar=False)
        self.anuncios.clear()
        self._votar("!1", "Ana", "A")
        self.reloj[0] = 110.0
        self._sesion()._latido()
        self.assertEqual(self.anuncios, [])

    def test_en_ensayo_tambien_anuncia_los_diez_segundos(self):
        self.frame._conectado = False
        self.frame._ensayo = True
        self._iniciar(segundos=120)
        self.anuncios.clear()
        self.reloj[0] = 110.0
        self._sesion()._latido()
        self.assertEqual(self.anuncios[-1][1], "encuesta_por_terminar")


class TestEnsayo(Base):
    """La encuesta del ensayo se ve en el vídeo y cuenta los votos."""

    def setUp(self):
        super().setUp()
        self.frame._conectado = False
        self.frame._ensayo = True

    def test_la_encuesta_se_fija_en_el_video_y_cuenta_el_voto(self):
        self._iniciar()
        self.assertEqual(len(self.capa.fijadas), 1)
        self.assertTrue(self._votar("!1"))
        self.assertEqual(self._sesion().encuesta.total(), 1)

    def test_al_descartar_no_anuncia_no_publica_y_no_envia(self):
        self._iniciar(destino="ambos")
        self.assertTrue(self._votar("!1"))
        self.anuncios.clear()
        self.assertTrue(encuesta_en_vivo.descartar(self.frame))
        self.assertIsNone(self._sesion().encuesta)
        self.assertEqual(self.anuncios, [])
        self.assertEqual(self.capa.agregadas, [])
        self.assertEqual(self.enviados, [])
        self.assertEqual(self.capa.quitadas, 1)

    def test_sin_ensayo_ni_conexion_la_encuesta_no_va_al_video(self):
        self.frame._ensayo = False
        self._iniciar()
        self.assertEqual(self.capa.fijadas, [])


if __name__ == "__main__":
    unittest.main()
