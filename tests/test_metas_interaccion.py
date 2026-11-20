# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la base pura de las metas del directo."""

import dataclasses
import random
import unittest

from guyrapu.core import plataformas
from guyrapu.core.tipos_mensaje import (
    TIPO_ME_GUSTA, TIPO_MIEMBRO, TIPO_SEGUIR, TIPO_SUPERCHAT, VARIANTE_REGALO)
from guyrapu.interaction import metas
from guyrapu.interaction.evento import desde_entrante


def _meta(**cambios):
    datos = {"nombre": "Meta", "que_cuenta": "me_gusta", "objetivo": 10}
    datos.update(cambios)
    return metas.Meta(**datos)


def _evento(tipo, monto="", autor="Ana", autor_id="1",
            plataforma=plataformas.TIKTOK):
    return desde_entrante(autor, "", tipo, monto, autor_id, "", plataforma)


class TestMeta(unittest.TestCase):

    def test_congelada_con_estilo_y_festejo_vacios_y_activa(self):
        meta = metas.Meta("100 me gusta", "me_gusta", 100)
        self.assertEqual(meta.estilo, "")
        self.assertEqual(meta.festejo, "")
        self.assertTrue(meta.activa)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meta.objetivo = 200

    def test_que_cuenta_tiene_las_cinco_claves(self):
        self.assertEqual(
            metas.QUE_CUENTA,
            ("me_gusta", "seguidores", "miembros", "regalos", "super_chat"))


class TestProgreso(unittest.TestCase):

    def test_me_gusta_suma_la_cantidad_del_evento(self):
        progreso = metas.Progreso(_meta(objetivo=10))
        self.assertTrue(progreso.sumar(_evento(TIPO_ME_GUSTA, "7")))
        self.assertTrue(progreso.sumar(_evento(TIPO_ME_GUSTA, "3")))
        self.assertEqual(progreso.valor, 10)

    def test_seguidores_cuenta_una_vez_a_cada_persona(self):
        progreso = metas.Progreso(_meta(que_cuenta="seguidores"))
        self.assertTrue(progreso.sumar(
            _evento(TIPO_SEGUIR, autor_id="ana")))
        self.assertFalse(progreso.sumar(
            _evento(TIPO_SEGUIR, autor="Ana", autor_id="ana")))
        self.assertTrue(progreso.sumar(
            _evento(TIPO_SEGUIR, autor="Beto", autor_id="beto")))
        self.assertEqual(progreso.valor, 2)

    def test_miembros_cuenta_las_nuevas_y_las_regaladas(self):
        progreso = metas.Progreso(_meta(que_cuenta="miembros"))
        self.assertTrue(progreso.sumar(_evento(TIPO_MIEMBRO)))
        self.assertTrue(progreso.sumar(
            _evento(TIPO_MIEMBRO, VARIANTE_REGALO)))
        self.assertEqual(progreso.valor, 2)

    def test_regalos_suma_diamantes_y_no_super_chats(self):
        progreso = metas.Progreso(_meta(que_cuenta="regalos"))
        self.assertTrue(progreso.sumar(
            _evento(TIPO_SUPERCHAT, "25 diamantes")))
        self.assertFalse(progreso.sumar(_evento(
            TIPO_SUPERCHAT, "$5.00", plataforma=plataformas.YOUTUBE)))
        self.assertEqual(progreso.valor, 25)

    def test_super_chat_suma_el_monto_y_no_los_regalos(self):
        progreso = metas.Progreso(_meta(que_cuenta="super_chat", objetivo=20))
        self.assertTrue(progreso.sumar(_evento(
            TIPO_SUPERCHAT, "$5.00", plataforma=plataformas.YOUTUBE)))
        self.assertTrue(progreso.sumar(_evento(
            TIPO_SUPERCHAT, "10,50", plataforma=plataformas.YOUTUBE)))
        self.assertFalse(progreso.sumar(
            _evento(TIPO_SUPERCHAT, "25 diamantes")))
        self.assertEqual(progreso.valor, 15.5)

    def test_cumplida_y_recien_cumplida_una_sola_vez(self):
        progreso = metas.Progreso(_meta(objetivo=10))
        self.assertEqual(progreso.valor, 0)
        self.assertFalse(progreso.cumplida)
        self.assertFalse(progreso.recien_cumplida())
        progreso.sumar(_evento(TIPO_ME_GUSTA, "9"))
        self.assertFalse(progreso.cumplida)
        self.assertFalse(progreso.recien_cumplida())
        progreso.sumar(_evento(TIPO_ME_GUSTA, "2"))
        self.assertTrue(progreso.cumplida)
        self.assertTrue(progreso.recien_cumplida())
        self.assertFalse(progreso.recien_cumplida())

    def test_el_valor_nunca_baja_con_ninguna_secuencia(self):
        generador = random.Random(7)
        progreso = metas.Progreso(_meta(que_cuenta="regalos", objetivo=1000))
        anterior = 0
        for _ in range(50):
            tipo = generador.choice(
                (TIPO_ME_GUSTA, TIPO_SEGUIR, TIPO_MIEMBRO, TIPO_SUPERCHAT))
            plataforma = generador.choice(
                (plataformas.TIKTOK, plataformas.YOUTUBE))
            monto = generador.choice(("", "0", "3", "25 diamantes", "$4.50"))
            progreso.sumar(_evento(
                tipo, monto, autor_id=str(generador.randrange(5)),
                plataforma=plataforma))
            self.assertGreaterEqual(progreso.valor, anterior)
            anterior = progreso.valor


class TestTexto(unittest.TestCase):

    def test_sin_decimales_y_con_meta_cumplida(self):
        meta = _meta(nombre="Viaje", objetivo=100)
        self.assertEqual(metas.texto(meta, 40), "Viaje: 40 de 100")
        self.assertEqual(metas.texto(meta, 100), "Viaje: meta cumplida")

    def test_super_chat_lleva_dos_decimales(self):
        meta = _meta(nombre="Apoyo", que_cuenta="super_chat", objetivo=50)
        self.assertEqual(metas.texto(meta, 12.5), "Apoyo: 12.50 de 50")
        self.assertEqual(metas.texto(meta, 50), "Apoyo: meta cumplida")

    def test_el_texto_fijo_lleva_una_linea_por_meta_en_su_orden(self):
        risa = metas.Progreso(_meta(nombre="Risa", objetivo=10))
        risa.sumar(_evento(TIPO_ME_GUSTA, "4"))
        viaje = metas.Progreso(_meta(nombre="Viaje", objetivo=5))
        viaje.sumar(_evento(TIPO_ME_GUSTA, "5"))
        self.assertEqual(
            metas.texto_en_video([risa, viaje]),
            "Risa: 4 de 10\nViaje: meta cumplida")

    def test_sin_metas_el_texto_fijo_queda_vacio(self):
        self.assertEqual(metas.texto_en_video([]), "")


class TestValidar(unittest.TestCase):

    def test_una_meta_valida_no_da_error(self):
        self.assertEqual(metas.validar(_meta(), []), "")

    def test_nombre_vacio(self):
        self.assertTrue(metas.validar(_meta(nombre="   "), []))

    def test_nombre_repetido_sin_mayusculas_ni_tildes(self):
        error = metas.validar(
            _meta(nombre="Viaje"), [_meta(nombre="viajé")])
        self.assertIn("Viaje", error)

    def test_objetivo_que_no_es_entero_mayor_que_cero(self):
        for objetivo in (0, -3, 1.5):
            with self.subTest(objetivo=objetivo):
                error = metas.validar(_meta(objetivo=objetivo), [])
                self.assertIn("objetivo", error)

    def test_que_cuenta_fuera_de_las_claves(self):
        error = metas.validar(_meta(que_cuenta="espectadores"), [])
        self.assertEqual(error, "Ese tipo de meta no existe.")


if __name__ == "__main__":
    unittest.main()
