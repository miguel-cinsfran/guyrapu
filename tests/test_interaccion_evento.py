# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del evento único de un mensaje del directo."""

import unittest
from dataclasses import FrozenInstanceError

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction import evento


def _evento(**cambios):
    datos = {
        "plataforma": plataformas.YOUTUBE,
        "autor_id": "canal-1",
        "autor": "Ana",
        "roles": frozenset(),
        "tipo": TIPO_TEXTO,
        "texto": "!hola",
        "monto": "",
    }
    datos.update(cambios)
    return evento.EventoDirecto(**datos)


class TestEventoDirecto(unittest.TestCase):

    def test_lleva_cada_dato_de_una_plataforma(self):
        creado = evento.EventoDirecto(
            plataforma=plataformas.TIKTOK,
            autor_id="7",
            autor="Beto",
            roles=frozenset((ROL_MODERADOR,)),
            tipo=TIPO_TEXTO,
            texto="hola",
            monto="5",
            id_mensaje="m1")
        self.assertEqual(plataformas.TIKTOK, creado.plataforma)
        self.assertEqual("7", creado.autor_id)
        self.assertEqual("Beto", creado.autor)
        self.assertEqual(frozenset((ROL_MODERADOR,)), creado.roles)
        self.assertEqual(TIPO_TEXTO, creado.tipo)
        self.assertEqual("hola", creado.texto)
        self.assertEqual("5", creado.monto)
        self.assertEqual("m1", creado.id_mensaje)

    def test_el_id_del_mensaje_viene_vacio(self):
        self.assertEqual("", _evento().id_mensaje)

    def test_es_congelado(self):
        creado = _evento()
        with self.assertRaises(FrozenInstanceError):
            creado.texto = "otro"


class TestDesdeEntrante(unittest.TestCase):

    def test_arma_el_evento_de_youtube(self):
        creado = evento.desde_entrante(
            "Ana", "!hola", TIPO_TEXTO, "", "canal-1",
            ROL_PROPIETARIO, plataformas.YOUTUBE)
        self.assertEqual(plataformas.YOUTUBE, creado.plataforma)
        self.assertEqual("canal-1", creado.autor_id)
        self.assertEqual("Ana", creado.autor)
        self.assertEqual(frozenset((ROL_PROPIETARIO,)), creado.roles)
        self.assertEqual(TIPO_TEXTO, creado.tipo)
        self.assertEqual("!hola", creado.texto)
        self.assertEqual("", creado.monto)
        self.assertEqual("", creado.id_mensaje)

    def test_sin_rol_no_lleva_roles(self):
        creado = evento.desde_entrante(
            "Beto", "hola", TIPO_TEXTO, "", "", "", plataformas.TIKTOK)
        self.assertEqual(frozenset(), creado.roles)
        self.assertEqual("", creado.autor_id)


class TestPersona(unittest.TestCase):

    def test_usa_el_id_dentro_de_su_plataforma(self):
        uno = _evento(autor_id="1", autor="Ana")
        otro = _evento(autor_id="1", autor="Anita")
        self.assertEqual((plataformas.YOUTUBE, "1"), evento.persona(uno))
        self.assertEqual(evento.persona(uno), evento.persona(otro))

    def test_el_mismo_id_en_otra_plataforma_es_otra_persona(self):
        youtube = _evento(autor_id="1", plataforma=plataformas.YOUTUBE)
        tiktok = _evento(autor_id="1", plataforma=plataformas.TIKTOK)
        self.assertNotEqual(evento.persona(youtube), evento.persona(tiktok))

    def test_sin_id_usa_el_nombre_normalizado(self):
        uno = _evento(autor_id="", autor="  ANA  ")
        otro = _evento(autor_id="", autor="ana")
        self.assertEqual((plataformas.YOUTUBE, "ana"), evento.persona(uno))
        self.assertEqual(evento.persona(uno), evento.persona(otro))


if __name__ == "__main__":
    unittest.main()
