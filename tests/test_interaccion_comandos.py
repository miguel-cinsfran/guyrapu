# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del lector de comandos y de sus permisos y esperas."""

import unittest

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction import comandos
from guyrapu.interaction.evento import EventoDirecto


def _evento(autor="Ana", autor_id="1", roles=frozenset(),
            plataforma=plataformas.YOUTUBE, texto="!hola"):
    return EventoDirecto(
        plataforma=plataforma,
        autor_id=autor_id,
        autor=autor,
        roles=roles,
        tipo=TIPO_TEXTO,
        texto=texto,
        monto="")


class TestLeer(unittest.TestCase):

    def test_reconoce_el_comando_sin_distinguir_mayusculas_ni_tildes(self):
        for texto in ("!Hola", "  !hola  mundo  ", "!HÓLA"):
            with self.subTest(texto=texto):
                invocacion = comandos.leer(texto)
                self.assertIsNotNone(invocacion)
                self.assertEqual("hola", invocacion.nombre)

    def test_los_argumentos_van_tal_cual_recortados(self):
        invocacion = comandos.leer("  !decir  hola  mundo  ")
        self.assertEqual("decir", invocacion.nombre)
        self.assertEqual("hola  mundo", invocacion.argumentos)

    def test_sin_argumentos_quedan_vacios(self):
        self.assertEqual("", comandos.leer("!hola").argumentos)

    def test_no_es_comando(self):
        for texto in ("!", "! x", "hola !x", "", "   "):
            with self.subTest(texto=texto):
                self.assertIsNone(comandos.leer(texto))

    def test_la_ene_no_se_confunde(self):
        self.assertEqual("año", comandos.leer("!AÑO").nombre)
        self.assertEqual("ano", comandos.leer("!ano").nombre)
        self.assertNotEqual(comandos.leer("!año").nombre,
                            comandos.leer("!ano").nombre)


class TestBuscar(unittest.TestCase):

    def _comandos(self):
        return [
            comandos.Comando("saludo", ("hola", "hi"), "Hola"),
            comandos.Comando("pausado", (), "No", activo=False),
        ]

    def test_encuentra_por_nombre(self):
        encontrado = comandos.buscar(self._comandos(), comandos.leer("!saludo"))
        self.assertEqual("saludo", encontrado.nombre)

    def test_encuentra_por_alias_sin_tildes_ni_mayusculas(self):
        encontrado = comandos.buscar(self._comandos(), comandos.leer("!HÓLA"))
        self.assertEqual("saludo", encontrado.nombre)

    def test_no_encuentra_uno_pausado(self):
        self.assertIsNone(
            comandos.buscar(self._comandos(), comandos.leer("!pausado")))

    def test_devuelve_el_primero(self):
        primero = comandos.Comando("hola", (), "Primero")
        segundo = comandos.Comando("hola", (), "Segundo")
        self.assertIs(primero,
                      comandos.buscar([primero, segundo], comandos.leer("!hola")))


class TestPermisos(unittest.TestCase):

    def _comando(self, **cambios):
        datos = {"nombre": "hola", "alias": (), "respuesta": "Hola"}
        datos.update(cambios)
        return comandos.Comando(**datos)

    def test_todos_deja_a_cualquiera(self):
        self.assertTrue(
            comandos.puede_usarlo(self._comando(), _evento()))

    def test_moderadores_solo_a_ellos(self):
        comando = self._comando(permiso="moderadores")
        self.assertFalse(comandos.puede_usarlo(comando, _evento()))
        for rol in (ROL_MODERADOR, ROL_PROPIETARIO):
            with self.subTest(rol=rol):
                self.assertTrue(comandos.puede_usarlo(
                    comando, _evento(roles=frozenset((rol,)))))

    def test_lista_compara_el_nombre_visible_normalizado(self):
        comando = self._comando(permiso="lista", nombres=("Ana María",))
        self.assertTrue(comandos.puede_usarlo(
            comando, _evento(autor="  ANA MARIA  ")))
        self.assertFalse(comandos.puede_usarlo(comando, _evento(autor="Beto")))

    def test_el_dueno_y_los_moderadores_siempre_pueden(self):
        comando = self._comando(permiso="lista", nombres=())
        for rol in (ROL_MODERADOR, ROL_PROPIETARIO):
            with self.subTest(rol=rol):
                self.assertTrue(comandos.puede_usarlo(
                    comando, _evento(roles=frozenset((rol,)))))

    def test_en_tiktok_no_hay_roles(self):
        comando = self._comando(permiso="moderadores")
        self.assertFalse(comandos.puede_usarlo(
            comando, _evento(plataforma=plataformas.TIKTOK)))


class TestEsperas(unittest.TestCase):

    def _comando(self, espera_general=0, espera_persona=30):
        return comandos.Comando(
            "hola", (), "Hola",
            espera_general=espera_general, espera_persona=espera_persona)

    def test_la_misma_persona_espera_y_otra_no(self):
        esperas = comandos.Esperas()
        comando = self._comando()
        ana = _evento(autor_id="1", autor="Ana")
        beto = _evento(autor_id="2", autor="Beto")
        esperas.anotar(comando, ana, 0)
        self.assertFalse(esperas.libre(comando, ana, 10))
        self.assertTrue(esperas.libre(comando, beto, 10))
        self.assertTrue(esperas.libre(comando, ana, 30))

    def test_la_espera_general_frena_a_todos(self):
        esperas = comandos.Esperas()
        comando = self._comando(espera_general=5, espera_persona=0)
        ana = _evento(autor_id="1")
        beto = _evento(autor_id="2")
        esperas.anotar(comando, ana, 100)
        self.assertFalse(esperas.libre(comando, beto, 103))
        self.assertTrue(esperas.libre(comando, beto, 105))

    def test_el_dueno_y_los_moderadores_no_esperan(self):
        esperas = comandos.Esperas()
        comando = self._comando(espera_general=60, espera_persona=60)
        for rol in (ROL_PROPIETARIO, ROL_MODERADOR):
            with self.subTest(rol=rol):
                persona_rol = _evento(
                    autor_id=rol, roles=frozenset((rol,)))
                esperas.anotar(comando, persona_rol, 0)
                self.assertTrue(esperas.libre(comando, persona_rol, 0))

    def test_el_uso_del_moderador_no_hace_esperar_a_los_demas(self):
        esperas = comandos.Esperas()
        comando = self._comando(espera_general=60, espera_persona=60)
        moderador = _evento(autor_id="2", roles=frozenset((ROL_MODERADOR,)))
        normal = _evento(autor_id="1")
        esperas.anotar(comando, moderador, 0)
        self.assertTrue(esperas.libre(comando, normal, 0))


class TestValidar(unittest.TestCase):

    def _comando(self, nombre="hola", alias=(), respuesta="Hola"):
        return comandos.Comando(nombre, alias, respuesta)

    def test_un_comando_valido_no_da_error(self):
        self.assertEqual("", comandos.validar(
            self._comando(alias=("hi",)), []))

    def test_nombre_vacio(self):
        self.assertTrue(comandos.validar(
            self._comando(nombre="   "), []))

    def test_nombre_o_alias_solo_cifras(self):
        self.assertTrue(comandos.validar(
            self._comando(nombre="1"), []))
        self.assertTrue(comandos.validar(
            self._comando(alias=("2",)), []))

    def test_nombre_o_alias_repetido_con_otro_comando(self):
        self.assertTrue(comandos.validar(
            self._comando(nombre="HÓLA"), [self._comando(nombre="hola")]))
        self.assertTrue(comandos.validar(
            self._comando(alias=("hi",)),
            [self._comando(nombre="saludo", alias=("hi",))]))

    def test_respuesta_vacia(self):
        self.assertTrue(comandos.validar(
            self._comando(respuesta="   "), []))


if __name__ == "__main__":
    unittest.main()
