# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los disparadores de evento: su modelo, reglas y cumplimiento."""

import unittest

from guyrapu.core import plataformas
from guyrapu.core.avisos_tiktok import EVENTOS
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction import comandos, disparadores
from guyrapu.interaction.evento import EventoDirecto


def _evento(texto="", tipo="superchat", monto="US$5.00", autor="Ana",
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


def _de_evento(**cambios):
    datos = {"nombre": "aplauso", "cuando": "evento",
             "evento": "superchat", "medio": "fuegos"}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


class TestCampos(unittest.TestCase):

    def test_los_valores_de_fabrica_son_los_del_directo(self):
        disparador = disparadores.Disparador("aplauso")
        self.assertEqual(disparador.cuando, "evento")
        self.assertEqual((disparador.espera_general, disparador.espera_persona),
                         (5, 30))
        self.assertEqual(disparador.permiso, "todos")
        self.assertTrue(disparador.activo)
        self.assertEqual(disparador.estilo, "")
        self.assertEqual(disparador.segundos, 8)

    def test_un_disparador_de_evento_tiene_su_evento_y_su_minimo(self):
        disparador = _de_evento(evento="cofre", minimo=25)
        self.assertEqual(disparador.cuando, "evento")
        self.assertEqual(disparador.evento, "cofre")
        self.assertEqual(disparador.minimo, 25)

    def test_el_nombre_de_un_evento_es_uno_de_los_del_directo(self):
        validos = {tipo for tipo, _modo in EVENTOS if tipo != "comando"}
        self.assertIn("superchat", validos)
        self.assertNotIn("comando", validos)

    def test_solo_queda_el_tipo_evento(self):
        self.assertEqual(("evento",), disparadores.CUANDOS)


class TestCumplidos(unittest.TestCase):

    def test_un_evento_con_el_minimo_cumplido_se_cumple(self):
        disparador = _de_evento(minimo=5)
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador], _evento(monto="US$5.00"),
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
                [disparador], _evento(monto="US$4.99"),
                comandos.Esperas(), 0))

    def test_un_evento_sin_numero_no_cumple_un_minimo(self):
        disparador = _de_evento(minimo=5)
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador], _evento(monto=""),
                comandos.Esperas(), 0))

    def test_los_moderadores_usan_lo_que_es_solo_para_ellos(self):
        disparador = _de_evento(permiso="moderadores")
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
        disparador = _de_evento(espera_general=5, espera_persona=0)
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
        disparador = _de_evento(espera_general=0, espera_persona=30)
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
        disparador = _de_evento(espera_general=60, espera_persona=60)
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
        primero = _de_evento(nombre="uno")
        segundo = _de_evento(nombre="dos")
        self.assertEqual(
            [segundo, primero],
            disparadores.cumplidos([segundo, primero], _evento(),
                                   comandos.Esperas(), 0))

    def test_un_disparador_pausado_no_se_cumple(self):
        disparador = _de_evento(activo=False)
        self.assertEqual(
            [],
            disparadores.cumplidos([disparador], _evento(),
                                   comandos.Esperas(), 0))

    def test_p1_el_regalo_nace_vacio(self):
        self.assertEqual(disparadores.Disparador("aplauso").regalo, "")

    def test_p1_un_regalo_de_tiktok_con_ese_nombre_se_cumple(self):
        disparador = _de_evento(regalo="Lion")
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="Lion", plataforma=plataformas.TIKTOK),
                comandos.Esperas(), 0))

    def test_p1_la_racha_se_compara_sin_su_cantidad(self):
        disparador = _de_evento(regalo="Lion")
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="lion x5", plataforma=plataformas.TIKTOK),
                comandos.Esperas(), 0))

    def test_p1_otro_regalo_no_cumple(self):
        disparador = _de_evento(regalo="Lion")
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="Rose", plataforma=plataformas.TIKTOK),
                comandos.Esperas(), 0))

    def test_p1_un_super_chat_de_youtube_no_cumple(self):
        disparador = _de_evento(regalo="Lion")
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="Lion", plataforma=plataformas.YOUTUBE),
                comandos.Esperas(), 0))

    def test_p1_el_nombre_se_compara_sin_tildes(self):
        disparador = _de_evento(regalo="León")
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="leon x3", plataforma=plataformas.TIKTOK),
                comandos.Esperas(), 0))

    def test_p2_hacen_falta_el_minimo_y_el_regalo(self):
        disparador = _de_evento(regalo="Lion", minimo=5)
        de_tiktok = {"plataforma": plataformas.TIKTOK}
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador], _evento(texto="Lion", monto="", **de_tiktok),
                comandos.Esperas(), 0))
        self.assertEqual(
            [],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="Rose", monto="100 diamantes", **de_tiktok),
                comandos.Esperas(), 0))
        self.assertEqual(
            [disparador],
            disparadores.cumplidos(
                [disparador],
                _evento(texto="Lion x2", monto="100 diamantes", **de_tiktok),
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


class TestTarjeta(unittest.TestCase):

    def test_p1_el_usuario_es_el_autor(self):
        self.assertEqual(
            "Ana", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{usuario}"), _evento(), 1, []))

    def test_p1_el_usuario_sale_con_las_palabras_bloqueadas_tapadas(self):
        self.assertEqual(
            "***", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{usuario}"), _evento(), 1, ["ana"]))

    def test_p2_la_cantidad_es_el_monto_tal_cual(self):
        casos = (
            (_de_evento(tarjeta="{cantidad}"),
             _evento(monto="US$5.00"), "US$5.00"),
            (_de_evento(tarjeta="{cantidad}", regalo="Rosa"),
             _evento(texto="Rosa x5", monto="500 diamantes",
                     plataforma=plataformas.TIKTOK), "500 diamantes"),
            (_de_evento(tarjeta="{cantidad}", evento="me_gusta"),
             _evento(tipo="me_gusta", monto="500"), "500"),
        )
        for disparador, evento, esperado in casos:
            with self.subTest(evento=disparador.evento):
                self.assertEqual(
                    esperado, disparadores.texto_de_tarjeta(
                        disparador, evento, 1, []))

    def test_p3_el_regalo_es_el_nombre_sin_la_racha(self):
        self.assertEqual(
            "Rosa", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{regalo}", regalo="Rosa"),
                _evento(texto="Rosa x5", monto="500 diamantes",
                        plataforma=plataformas.TIKTOK), 1, []))

    def test_p3_el_regalo_esta_vacio_en_los_demas_eventos(self):
        self.assertEqual(
            "", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{regalo}"),
                _evento(texto="Rosa x5", monto="US$5.00"), 1, []))

    def test_p4_el_texto_de_un_evento_es_su_mensaje(self):
        self.assertEqual(
            "Gran directo", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{texto}"),
                _evento(texto="Gran directo", monto="US$5.00"), 1, []))

    def test_p4_el_texto_de_un_regalo_con_racha_es_el_del_evento(self):
        self.assertEqual(
            "Rosa x5", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{texto}", regalo="Rosa"),
                _evento(texto="Rosa x5", monto="500 diamantes",
                        plataforma=plataformas.TIKTOK), 1, []))

    def test_p4_el_texto_sale_con_las_palabras_bloqueadas_tapadas(self):
        self.assertEqual(
            "hola ***", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{texto}"), _evento(texto="hola tonto"),
                1, ["tonto"]))

    def test_p4_el_texto_se_corta_en_cien_caracteres(self):
        self.assertEqual(
            "a" * 100, disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{texto}"), _evento(texto="a" * 120),
                1, []))

    def test_p4_un_texto_casi_todo_simbolos_queda_vacio(self):
        self.assertEqual(
            "", disparadores.texto_de_tarjeta(
                _de_evento(tarjeta="{texto}"), _evento(texto="!!!!!!!!!"),
                1, []))

    def test_p5_el_contador_es_el_que_recibe(self):
        casos = (
            (_de_evento(tarjeta="{contador}"), _evento()),
            (_de_evento(tarjeta="{contador}", regalo="Rosa"),
             _evento(texto="Rosa x5", plataforma=plataformas.TIKTOK)),
        )
        for disparador, evento in casos:
            with self.subTest(regalo=disparador.regalo):
                self.assertEqual(
                    "3", disparadores.texto_de_tarjeta(
                        disparador, evento, 3, []))


class TestErrorYCampo(unittest.TestCase):

    def test_el_primer_error_dice_su_campo_y_su_mensaje(self):
        disparador = _de_evento(nombre="   ", medio="", tarjeta="")
        self.assertEqual(
            ("nombre", "La alerta necesita un nombre."),
            disparadores.error_y_campo(disparador, []))

    def test_cada_error_sabe_su_campo(self):
        casos = (
            (_de_evento(), ""),
            (_de_evento(cuando="tecla", medio="fuegos"), "nombre"),
            (_de_evento(evento="tecla", medio="fuegos"), "evento"),
            (_de_evento(minimo=-1, medio="fuegos"), "minimo"),
            (_de_evento(medio="", tarjeta=""), "tarjeta"),
            (_de_evento(tarjeta="Hola {nada}"), "tarjeta"),
        )
        for disparador, campo_esperado in casos:
            with self.subTest(campo=campo_esperado):
                campo, mensaje = disparadores.error_y_campo(disparador, [])
                self.assertEqual(campo_esperado, campo)
                self.assertEqual(bool(campo_esperado), bool(mensaje))


class TestValidar(unittest.TestCase):

    def test_un_disparador_valido_no_da_error(self):
        self.assertEqual("", disparadores.validar(
            _de_evento(minimo=5), []))

    def test_nombre_vacio(self):
        self.assertTrue(disparadores.validar(
            _de_evento(nombre="   "), []))

    def test_nombre_repetido(self):
        error = disparadores.validar(
            _de_evento(nombre="aplauso"),
            [_de_evento(nombre="APLAUSO")])
        self.assertTrue(error)

    def test_un_cuando_que_todavia_no_existe(self):
        self.assertTrue(disparadores.validar(
            _de_evento(cuando="tecla"), []))

    def test_un_evento_desconocido(self):
        error = disparadores.validar(_de_evento(evento="tecla"), [])
        self.assertIn("tecla", error)

    def test_un_minimo_negativo(self):
        self.assertTrue(disparadores.validar(_de_evento(minimo=-1), []))

    def test_un_que_sin_medio_ni_tarjeta(self):
        error = disparadores.validar(_de_evento(medio=""), [])
        self.assertIn("medio", error)

    def test_p6_una_variable_que_no_existe_da_su_error(self):
        self.assertEqual(
            "La variable {nada} no existe. Puedes usar {usuario}, "
            "{cantidad}, {regalo}, {texto} y {contador}.",
            disparadores.validar(_de_evento(tarjeta="Hola {nada}"), []))

    def test_p6_las_cinco_variables_no_dan_error(self):
        self.assertEqual(
            "", disparadores.validar(
                _de_evento(tarjeta="{usuario} {cantidad} {regalo} {texto} "
                                   "{contador}"), []))


if __name__ == "__main__":
    unittest.main()
