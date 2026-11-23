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

    def test_encuentra_un_comando_guardado_con_el_signo(self):
        comando = comandos.Comando("!hola", ("!hi",), "Hola")
        self.assertEqual("hola", comando.nombre)
        self.assertEqual(("hi",), comando.alias)
        self.assertIs(comando,
                      comandos.buscar([comando], comandos.leer("!hola")))
        self.assertIs(comando,
                      comandos.buscar([comando], comandos.leer("!HI")))


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

    def test_un_moderador_usa_aunque_otro_haya_usado(self):
        esperas = comandos.Esperas()
        comando = self._comando(espera_general=60, espera_persona=60)
        comun = _evento(autor_id="1")
        moderador = _evento(autor_id="2", roles=frozenset((ROL_MODERADOR,)))
        esperas.anotar(comando, comun, 0)
        self.assertTrue(esperas.libre(comando, moderador, 1))

    def test_el_uso_del_moderador_no_hace_esperar_a_los_demas(self):
        esperas = comandos.Esperas()
        comando = self._comando(espera_general=60, espera_persona=60)
        moderador = _evento(autor_id="2", roles=frozenset((ROL_MODERADOR,)))
        normal = _evento(autor_id="1")
        esperas.anotar(comando, moderador, 0)
        self.assertTrue(esperas.libre(comando, normal, 0))


class TestCampos(unittest.TestCase):

    def test_los_campos_nuevos_tienen_su_valor_de_fabrica(self):
        comando = comandos.Comando("hola", (), "Hola")
        self.assertEqual(comando.medio, "")
        self.assertEqual(comando.estilo, "")
        self.assertEqual(comando.segundos, 8)
        self.assertEqual(comando.destino, "video")
        self.assertEqual((comando.espera_general, comando.espera_persona),
                         (5, 30))
        self.assertEqual(comando.permiso, "todos")
        self.assertFalse(comando.lista)
        self.assertTrue(comando.en_lista)


class TestListaDeComandos(unittest.TestCase):

    def test_la_lista_de_fabrica_en_espanol_tiene_las_dos_palabras(self):
        comando = comandos.comando_de_lista("es")
        self.assertTrue(comando.lista)
        self.assertEqual(comando.nombre, "commands")
        self.assertEqual(comando.alias, ("comandos",))
        self.assertEqual(comando.respuesta, "Comandos: {lista}.")
        self.assertEqual(comando.destino, "video")
        self.assertEqual(comando.segundos, 8)
        self.assertEqual((comando.espera_general, comando.espera_persona),
                         (5, 30))

    def test_la_lista_de_fabrica_en_ingles_solo_tiene_commands(self):
        comando = comandos.comando_de_lista("en")
        self.assertEqual(comando.nombre, "commands")
        self.assertEqual(comando.alias, ())

    def test_la_lista_de_fabrica_en_portugues_tiene_las_dos_palabras(self):
        self.assertEqual(comandos.comando_de_lista("pt_BR").alias,
                         ("comandos",))

    def test_asegurar_agrega_la_lista_al_principio_cuando_falta(self):
        hola = comandos.Comando("hola", (), "Hola")
        resultado = comandos.asegurar_lista([hola], "es")
        self.assertEqual([comando.nombre for comando in resultado],
                         ["commands", "hola"])
        self.assertTrue(resultado[0].lista)

    def test_asegurar_deja_el_primero_y_pasa_los_demas_a_comunes(self):
        uno = comandos.Comando("uno", (), "Uno", lista=True)
        dos = comandos.Comando("dos", (), "Dos", lista=True)
        resultado = comandos.asegurar_lista([uno, dos], "es")
        self.assertIs(resultado[0], uno)
        self.assertTrue(resultado[0].lista)
        self.assertFalse(resultado[1].lista)

    def test_asegurar_no_toca_una_coleccion_que_ya_tiene_la_lista(self):
        lista = comandos.comando_de_lista("es")
        resultado = comandos.asegurar_lista([lista], "es")
        self.assertEqual(len(resultado), 1)
        self.assertIs(resultado[0], lista)

    def test_la_variable_lista_solo_vale_en_el_comando_de_lista(self):
        self.assertEqual("", comandos.validar(
            comandos.comando_de_lista("es"), []))
        error = comandos.validar(
            comandos.Comando("hola", (), "Comandos: {lista}."), [])
        self.assertIn("{lista}", error)

    def test_los_segundos_quedan_entre_tres_y_sesenta(self):
        self.assertEqual(comandos.Comando("hola", (), "Hola", segundos=1).segundos,
                         3)
        self.assertEqual(comandos.Comando("hola", (), "Hola", segundos=90).segundos,
                         60)

    def test_los_alias_se_separan_con_espacios_o_comas(self):
        self.assertEqual(comandos.separar_alias("uno dos,tres, cuatro"),
                         ("uno", "dos", "tres", "cuatro"))

    def test_los_nombres_conservan_los_espacios_y_separan_por_comas(self):
        self.assertEqual(comandos.separar_nombres("Ana María, Beto"),
                         ("Ana María", "Beto"))


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
        error = comandos.validar(self._comando(respuesta="   "), [])
        self.assertEqual(error,
                         "El comando necesita una respuesta o un medio.")

    def test_con_medio_y_sin_respuesta_se_guarda(self):
        comando = comandos.Comando("hola", (), "", medio="fuegos")
        self.assertEqual("", comandos.validar(comando, []))

    def test_un_nombre_con_el_signo_es_valido(self):
        self.assertEqual("", comandos.validar(
            self._comando(nombre="!hola", alias=("!hi",)), []))

    def test_el_signo_no_esconde_un_nombre_repetido(self):
        self.assertTrue(comandos.validar(
            self._comando(nombre="!hola"),
            [self._comando(nombre="hola")]))

    def test_rechaza_espacios_adentro_del_nombre_o_alias(self):
        self.assertTrue(comandos.validar(
            self._comando(nombre="mi comando"), []))
        self.assertTrue(comandos.validar(
            self._comando(alias=("mi alias",)), []))

    def test_comandos_ya_no_es_una_palabra_prohibida(self):
        for comando in (self._comando(nombre="comandos"),
                        self._comando(nombre="COMANDOS"),
                        self._comando(alias=("comandos",))):
            with self.subTest(comando=comando):
                self.assertEqual("", comandos.validar(comando, []))

    def test_una_variable_desconocida_nombra_las_validas(self):
        error = comandos.validar(
            self._comando(respuesta="Hola {nombre}"), [])
        self.assertIn("{nombre}", error)
        self.assertIn("{usuario}", error)
        self.assertIn("{contador}", error)
        self.assertIn("{texto}", error)

    def test_las_tres_variables_conocidas_pasan(self):
        self.assertEqual("", comandos.validar(
            self._comando(respuesta="{usuario}, {contador}: {texto}"), []))

    def test_en_el_chat_la_respuesta_no_pasa_de_doscientos(self):
        self.assertEqual("", comandos.validar(
            comandos.Comando("hola", (), "a" * 200, destino="chat"), []))
        error = comandos.validar(
            comandos.Comando("hola", (), "a" * 201, destino="chat"), [])
        self.assertIn("201", error)
        self.assertIn("200", error)

    def test_en_el_video_no_hay_limite_de_doscientos(self):
        self.assertEqual("", comandos.validar(
            comandos.Comando("hola", (), "a" * 201, destino="video"), []))

    def test_el_destino_ambos_tambien_cuenta_como_chat(self):
        self.assertTrue(comandos.validar(
            comandos.Comando("hola", (), "a" * 201, destino="ambos"), []))

    def test_con_una_lista_de_nombres_la_lista_no_puede_estar_vacia(self):
        error = comandos.validar(
            self._comando(), [])
        self.assertEqual("", error)
        error = comandos.validar(
            comandos.Comando("hola", (), "Hola", permiso="lista"), [])
        self.assertIn("lista", error)
        self.assertEqual("", comandos.validar(
            comandos.Comando("hola", (), "Hola", permiso="lista",
                             nombres=("Ana",)), []))


class TestUbicacion(unittest.TestCase):

    def _comandos(self):
        return [
            comandos.Comando("saludo", ("hola",), "Hola"),
            comandos.Comando("risa", ("jaja",), "Risas",
                             ubicacion="cualquiera"),
            comandos.Comando("otra", (), "Otra", ubicacion="cualquiera"),
        ]

    def test_el_valor_de_fabrica_es_al_principio(self):
        self.assertEqual(comandos.Comando("hola", (), "Hola").ubicacion,
                         "principio")

    def test_la_palabra_en_cualquier_parte_ignora_tildes_y_mayusculas(self):
        encontrado = comandos.buscar_en_mensaje(
            self._comandos(), "qué RISA jaja")
        self.assertEqual("risa", encontrado.nombre)

    def test_el_alias_en_cualquier_parte_tambien_cuenta(self):
        encontrado = comandos.buscar_en_mensaje(
            self._comandos(), "eso fue un JAJA buenísimo")
        self.assertEqual("risa", encontrado.nombre)

    def test_un_comando_con_signo_no_se_cumple(self):
        self.assertIsNone(comandos.buscar_en_mensaje(
            self._comandos(), "!risa"))

    def test_devuelve_el_primero_de_la_lista(self):
        primero = comandos.Comando("risa", (), "Primero",
                                   ubicacion="cualquiera")
        segundo = comandos.Comando("risa", (), "Segundo",
                                   ubicacion="cualquiera")
        self.assertIs(primero, comandos.buscar_en_mensaje(
            [primero, segundo], "qué risa"))

    def test_un_comando_de_principio_no_responde_a_la_palabra_suelta(self):
        self.assertIsNone(comandos.buscar_en_mensaje(
            self._comandos(), "hola a todos"))

    def test_los_de_cualquiera_no_responden_al_signo(self):
        self.assertIsNone(comandos.buscar(
            self._comandos(), comandos.leer("!risa")))

    def test_en_cualquiera_puede_tener_espacios_y_emoji(self):
        comando = comandos.Comando(
            "🔥 broma", ("ja ja",), "Gracias", ubicacion="cualquiera")
        self.assertEqual("", comandos.validar(comando, []))
        self.assertIs(comando, comandos.buscar_en_mensaje(
            [comando], "vaya 🔥 broma"))

    def test_en_cualquiera_sigue_sin_cifras_ni_repetidos(self):
        self.assertTrue(comandos.validar(
            comandos.Comando("1", (), "Uno", ubicacion="cualquiera"), []))
        self.assertTrue(comandos.validar(
            comandos.Comando("risa", (), "Uno", ubicacion="cualquiera"),
            [comandos.Comando("risa", (), "Otro")]))


class TestAtajo(unittest.TestCase):

    def test_el_valor_de_fabrica_es_ninguno(self):
        self.assertEqual(comandos.Comando("hola", (), "Hola").atajo, 0)

    def test_dos_comandos_activos_no_pueden_usar_el_mismo_atajo(self):
        otro = comandos.Comando("risa", (), "Risas", atajo=3)
        error = comandos.validar(
            comandos.Comando("otro", (), "Otro", atajo=3), [otro])
        self.assertEqual(error,
                         "Ctrl+Alt+Mayús+3 ya lo usa el comando risa.")

    def test_un_atajo_de_otro_pausado_se_puede_usar(self):
        otro = comandos.Comando("risa", (), "Risas", atajo=3, activo=False)
        self.assertEqual("", comandos.validar(
            comandos.Comando("otro", (), "Otro", atajo=3), [otro]))

    def test_solo_con_el_atajo_necesita_un_atajo(self):
        comando = comandos.Comando("risa", (), "Risas", permiso="solo_atajo")
        self.assertEqual(comandos.validar(comando, []),
                         "Elige un atajo para un comando que solo usa el atajo.")

    def test_solo_con_el_atajo_no_responde_en_el_chat(self):
        comando = comandos.Comando(
            "risa", (), "Risas", permiso="solo_atajo", atajo=3)
        self.assertFalse(comandos.puede_usarlo(comando, _evento(
            roles=frozenset((ROL_PROPIETARIO,)))))
        self.assertEqual("", comandos.validar(comando, []))


if __name__ == "__main__":
    unittest.main()
