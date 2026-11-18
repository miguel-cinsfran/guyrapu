# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los disparadores: su modelo, sus reglas y cuándo se cumplen."""

import unittest

from guyrapu.core import plataformas
from guyrapu.core.avisos_tiktok import EVENTOS
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction import comandos, disparadores
from guyrapu.interaction.evento import EventoDirecto


def _evento(texto="!aplauso", tipo=TIPO_TEXTO, monto="", autor="Ana",
            autor_id="1", roles=frozenset(),
            plataforma=plataformas.YOUTUBE):
    return EventoDirecto(
        plataforma=plataforma,
        autor_id=autor_id,
        autor=autor,
        roles=roles,
        tipo=tipo,
        texto=texto,
        monto=monto)


def _comando(**cambios):
    datos = {"nombre": "aplauso", "cuando": "comando",
             "comandos": ("aplauso",), "medio": "fuegos"}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


def _de_evento(**cambios):
    datos = {"nombre": "regalo", "cuando": "evento",
             "evento": "superchat", "medio": "fuegos"}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


class TestCampos(unittest.TestCase):

    def test_los_valores_de_fabrica_son_los_de_los_comandos(self):
        disparador = disparadores.Disparador("aplauso")
        self.assertEqual(disparador.cuando, "comando")
        self.assertEqual((disparador.espera_general, disparador.espera_persona),
                         (5, 30))
        self.assertEqual(disparador.permiso, "todos")
        self.assertTrue(disparador.activo)
        self.assertEqual(disparador.estilo, "clasico")
        self.assertEqual(disparador.segundos, 8)

    def test_un_disparador_de_comando_tiene_sus_nombres(self):
        disparador = _comando(comandos=("aplauso", "festejar"))
        self.assertEqual(disparador.cuando, "comando")
        self.assertEqual(disparador.comandos, ("aplauso", "festejar"))

    def test_un_disparador_de_evento_tiene_su_evento_y_su_minimo(self):
        disparador = _de_evento(evento="cofre", minimo=25)
        self.assertEqual(disparador.cuando, "evento")
        self.assertEqual(disparador.evento, "cofre")
        self.assertEqual(disparador.minimo, 25)

    def test_el_nombre_de_un_evento_es_uno_de_los_del_directo(self):
        validos = {tipo for tipo, _modo in EVENTOS if tipo != "comando"}
        self.assertIn("superchat", validos)
        self.assertNotIn("comando", validos)


class TestCumplidos(unittest.TestCase):

    def test_un_comando_que_coincide_se_cumple(self):
        disparador = _comando()
        self.assertEqual(
            [disparador],
            disparadores.cumplidos([disparador], _evento("!APLauso"),
                                   comandos.Esperas(), 0))

    def test_un_comando_que_no_coincide_no_se_cumple(self):
        disparador = _comando()
        self.assertEqual(
            [],
            disparadores.cumplidos([disparador], _evento("!silencio"),
                                   comandos.Esperas(), 0))

    def test_un_evento_con_el_minimo_cumplido_se_cumple(self):
        disparador = _de_evento(minimo=5)
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador], _evento(tipo="superchat", monto="US$5.00"),
                comandos.Esperas(), 0))
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador], _evento(tipo="sticker", monto="ARS 1.000"),
                comandos.Esperas(), 0))

    def test_un_evento_sin_el_minimo_no_se_cumple(self):
        disparador = _de_evento(minimo=5)
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador], _evento(tipo="superchat", monto="US$4.99"),
                comandos.Esperas(), 0))

    def test_un_evento_sin_numero_no_cumple_un_minimo(self):
        disparador = _de_evento(minimo=5)
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador], _evento(tipo="superchat", monto=""),
                comandos.Esperas(), 0))

    def test_los_moderadores_usan_lo_que_es_solo_para_ellos(self):
        disparador = _comando(permiso="moderadores")
        self.assertEqual(
            [],
            disparadores.cumplidos([disparador], _evento(),
                                   comandos.Esperas(), 0))
        for rol in (ROL_MODERADOR, ROL_PROPIETARIO):
            with self.subTest(rol=rol):
                self.assertEqual(
                    [disparador],
                    disparadores.cumplidos(
                        [disparador],
                        _evento(roles=frozenset((rol,))),
                        comandos.Esperas(), 0))

    def test_la_espera_general_frena_a_todos(self):
        disparador = _comando(espera_general=5, espera_persona=0)
        esperas = comandos.Esperas()
        self.assertEqual(
            [disparador],
            disparadores.cumplidos([disparador], _evento(), esperas, 100))
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador], _evento(autor="Beto", autor_id="2"),
                esperas, 103))
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador], _evento(autor="Beto", autor_id="2"),
                esperas, 105))

    def test_la_espera_por_persona_frena_solo_a_esa_persona(self):
        disparador = _comando(espera_general=0, espera_persona=30)
        esperas = comandos.Esperas()
        self.assertEqual(
            [disparador],
            disparadores.cumplidos([disparador], _evento(), esperas, 0))
        self.assertEqual(
            [],
            disparadores.cumplidos([disparador], _evento(), esperas, 10))
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador], _evento(autor="Beto", autor_id="2"),
                esperas, 10))
        self.assertEqual(
            [disparador],
            disparadores.cumplidos([disparador], _evento(), esperas, 30))

    def test_el_dueno_y_los_moderadores_no_esperan(self):
        disparador = _comando(espera_general=60, espera_persona=60)
        esperas = comandos.Esperas()
        for rol in (ROL_PROPIETARIO, ROL_MODERADOR):
            with self.subTest(rol=rol):
                evento = _evento(autor_id=rol, roles=frozenset((rol,)))
                self.assertEqual(
                    [disparador],
                    disparadores.cumplidos([disparador], evento, esperas, 0))
                self.assertEqual(
                    [disparador],
                    disparadores.cumplidos([disparador], evento, esperas, 0))

    def test_devuelve_los_cumplidos_en_el_orden_de_la_lista(self):
        primero = _comando(nombre="uno", comandos=("aplauso",))
        segundo = _comando(nombre="dos", comandos=("aplauso",))
        self.assertEqual(
            [segundo, primero],
            disparadores.cumplidos([segundo, primero], _evento(),
                                   comandos.Esperas(), 0))

    def test_un_disparador_pausado_no_se_cumple(self):
        disparador = _comando(activo=False)
        self.assertEqual(
            [],
            disparadores.cumplidos([disparador], _evento(),
                                   comandos.Esperas(), 0))


class TestCantidad(unittest.TestCase):

    def test_los_ejemplos_de_la_regla(self):
        for monto, esperado in (("US$5.00", 5),
                                ("ARS 1.000", 1000),
                                ("1.234,56 €", 1234.56),
                                ("25 diamantes", 25)):
            with self.subTest(monto=monto):
                self.assertEqual(esperado, disparadores.cantidad_de(monto))

    def test_sin_numero_la_cantidad_es_cero(self):
        self.assertEqual(0, disparadores.cantidad_de(""))
        self.assertEqual(0, disparadores.cantidad_de("sin monto"))

    def test_cualquier_entero_de_la_escala_da_su_cantidad(self):
        for numero in range(0, 1000001):
            with self.subTest(numero=numero):
                self.assertEqual(
                    numero, disparadores.cantidad_de(str(numero)))
                self.assertEqual(
                    numero, disparadores.cantidad_de(f"US${numero}.00"))
                self.assertEqual(
                    numero, disparadores.cantidad_de(f"{numero} diamantes"))


class TestValidar(unittest.TestCase):

    def test_un_disparador_valido_no_da_error(self):
        self.assertEqual("", disparadores.validar(_comando(), []))
        self.assertEqual(
            "", disparadores.validar(_de_evento(minimo=5), []))

    def test_nombre_vacio(self):
        self.assertTrue(disparadores.validar(_comando(nombre="   "), []))

    def test_nombre_repetido(self):
        error = disparadores.validar(
            _comando(nombre="aplauso"),
            [_de_evento(nombre="APLAUSO")])
        self.assertTrue(error)

    def test_un_comando_sin_nombres(self):
        for nombres in ((), ("   ",)):
            with self.subTest(nombres=nombres):
                error = disparadores.validar(_comando(comandos=nombres), [])
                self.assertIn("nombre", error)

    def test_un_cuando_que_todavia_no_existe(self):
        self.assertTrue(disparadores.validar(_comando(cuando="tecla"), []))

    def test_un_nombre_de_comando_que_ya_usa_otro_disparador(self):
        error = disparadores.validar(
            _comando(comandos=("aplauso",)),
            [_de_evento(nombre="otro", comandos=("APLAUSO",))])
        self.assertIn("aplauso", error)

    def test_un_evento_desconocido(self):
        error = disparadores.validar(_de_evento(evento="tecla"), [])
        self.assertIn("tecla", error)

    def test_un_minimo_negativo(self):
        self.assertTrue(disparadores.validar(_de_evento(minimo=-1), []))

    def test_un_que_sin_medio_ni_tarjeta(self):
        error = disparadores.validar(_comando(medio=""), [])
        self.assertIn("medio", error)


if __name__ == "__main__":
    unittest.main()
