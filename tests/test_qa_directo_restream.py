# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lógica pura de qa/directo_restream.py, sin red ni ventanas."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.restream import perfiles
from guyrapu.restream.youtube_por_restream import NOMBRE_MANUAL

_RUTA = Path(__file__).resolve().parent.parent / "qa" / "directo_restream.py"
_paquete = importlib.util.spec_from_file_location(
    "directo_restream_qa", _RUTA)
directo_restream = importlib.util.module_from_spec(_paquete)
_paquete.loader.exec_module(directo_restream)

from directo_comun import (  # noqa: E402
    chats_conectados, comparar_destinos_en_vivo, destinos_a_restaurar,
    manuales_nuevos, paso_borrar_manual, paso_restaurar_destinos,
)


class CanalFalso:

    def __init__(self, identificador, plataforma="YouTube", nombre="",
                 plataforma_id=1, activo=True, canal_id=None):
        self.id = canal_id if canal_id is not None else identificador
        self.plataforma = plataforma
        self.nombre = nombre
        self.plataforma_id = plataforma_id
        self.activo = activo
        self.identificador = ""


class TestDestinoTiktok(unittest.TestCase):

    def test_encuentra_el_tiktok_entre_varios_destinos(self):
        canales = [
            CanalFalso(1, "YouTube", "Szeiryu", 5),
            CanalFalso(17448019, "TikTok", "szeiryuGaming", 9),
            CanalFalso(3, "Twitch", "otro", 2),
        ]
        self.assertEqual(
            directo_restream.destino_tiktok(canales).id, 17448019)

    def test_sin_tiktok_da_un_error_claro(self):
        canales = [CanalFalso(1, "YouTube", "Szeiryu", 5)]
        with self.assertRaises(ValueError) as contexto:
            directo_restream.destino_tiktok(canales)
        self.assertIn("TikTok", str(contexto.exception))


class TestArmarPerfil(unittest.TestCase):

    def test_pasa_validar_y_vuelve_igual_con_cargar(self):
        canal = CanalFalso(17448019, "TikTok", "szeiryuGaming", 9)
        perfil = directo_restream.armar_perfil(
            canal, "Prueba de Guyrapu 20:15")
        self.assertEqual(perfiles.validar(perfil, []), [])
        self.assertEqual(perfil.orientacion, "vertical")
        self.assertTrue(perfil.youtube)
        self.assertEqual(perfil.chat, "ambos")
        self.assertEqual(perfil.canales, (17448019,))
        self.assertEqual(perfil.directo["privacidad"], "unlisted")
        descriptor, ruta = tempfile.mkstemp(suffix=".json")
        os.close(descriptor)
        self.addCleanup(os.remove, ruta)
        perfiles.guardar(ruta, [perfil])
        self.assertEqual(perfiles.cargar(ruta), [perfil])


class TestCompararDestinosEnVivo(unittest.TestCase):

    TIKTOK = {"17448019", "szeiryuGaming"}
    YOUTUBE = {"18061190", "Szeiryu"}
    OTROS = {"111", "otroDestino"}

    def test_tiktok_y_el_manual_estan_bien(self):
        bien, _ = comparar_destinos_en_vivo(
            {"17448019", "999999"}, self.TIKTOK, self.YOUTUBE, self.OTROS)
        self.assertTrue(bien)

    def test_acepta_el_identificador_en_vez_del_id(self):
        bien, _ = comparar_destinos_en_vivo(
            {"szeiryuGaming", "manual99"}, self.TIKTOK, self.YOUTUBE,
            self.OTROS)
        self.assertTrue(bien)

    def test_uno_de_mas_da_mal(self):
        bien, detalle = comparar_destinos_en_vivo(
            {"17448019", "999999", "888888"}, self.TIKTOK, self.YOUTUBE,
            self.OTROS)
        self.assertFalse(bien)
        self.assertIn("de más", detalle)

    def test_uno_de_menos_da_mal(self):
        bien, detalle = comparar_destinos_en_vivo(
            {"17448019"}, self.TIKTOK, self.YOUTUBE, self.OTROS)
        self.assertFalse(bien)
        self.assertIn("YouTube manual", detalle)

    def test_el_youtube_conectado_en_vivo_da_mal(self):
        bien, detalle = comparar_destinos_en_vivo(
            {"17448019", "999999", "18061190"}, self.TIKTOK, self.YOUTUBE,
            self.OTROS)
        self.assertFalse(bien)
        self.assertIn("YouTube conectado", detalle)


class TestDestinosARestaurar(unittest.TestCase):

    def test_solo_devuelve_los_que_cambiaron(self):
        antes = {1: True, 2: False, 3: True}
        actuales = [
            CanalFalso(1, activo=True),
            CanalFalso(2, activo=True),
            CanalFalso(3, activo=False),
            CanalFalso(4, activo=True),
        ]
        self.assertEqual(
            destinos_a_restaurar(antes, actuales),
            [(2, False), (3, True)])

    def test_sin_cambios_no_devuelve_nada(self):
        antes = {1: True, 2: False}
        actuales = [CanalFalso(1, activo=True), CanalFalso(2, activo=False)]
        self.assertEqual(
            destinos_a_restaurar(antes, actuales), [])


class TestManualesNuevos(unittest.TestCase):

    def test_solo_sobran_los_manuales_nuevos(self):
        antes = [
            CanalFalso(1, nombre="Szeiryu", plataforma_id=5),
            CanalFalso(2, nombre=NOMBRE_MANUAL, plataforma_id=29),
        ]
        actuales = [
            CanalFalso(1, nombre="Szeiryu", plataforma_id=5),
            CanalFalso(2, nombre=NOMBRE_MANUAL, plataforma_id=29),
            CanalFalso(9, nombre=NOMBRE_MANUAL, plataforma_id=29),
            CanalFalso(10, nombre="TikTok de prueba", plataforma_id=9),
        ]
        self.assertEqual(
            manuales_nuevos(antes, actuales), [9])

    def test_sin_manuales_nuevos_no_sobra_nada(self):
        antes = [CanalFalso(1, nombre="Szeiryu", plataforma_id=5)]
        actuales = [CanalFalso(1, nombre="Szeiryu", plataforma_id=5)]
        self.assertEqual(
            manuales_nuevos(antes, actuales), [])


class TestChatsConectados(unittest.TestCase):

    def test_los_dos_textos_cuentan_como_conectados(self):
        anuncios = (
            "10:00:01 Conectado al directo. Leyendo el chat.\n"
            "10:00:05 TikTok: Conectado al directo. Leyendo el chat.\n")
        bien, _ = chats_conectados(anuncios)
        self.assertTrue(bien)

    def test_solo_youtube_no_alcanza(self):
        bien, detalle = chats_conectados(
            "10:00:01 Conectado al directo. Leyendo el chat.\n")
        self.assertFalse(bien)
        self.assertIn("TikTok", detalle)

    def test_el_texto_de_tiktok_no_cuenta_como_youtube(self):
        bien, detalle = chats_conectados(
            "10:00:05 TikTok: Conectado al directo. Leyendo el chat.\n")
        self.assertFalse(bien)
        self.assertIn("YouTube", detalle)


class TestPasoCeroNoTocaNada(unittest.TestCase):

    def test_con_uno_o_dos_sale_con_dos_sin_preparar(self):
        args = directo_restream._ayuda().parse_args([])
        for codigo in (1, 2):
            with self.subTest(codigo=codigo):
                llamado = {"preparar": False}

                def preparar(*_args, **_kwargs):
                    llamado["preparar"] = True
                    raise AssertionError("no debía preparar nada")

                with mock.patch.object(directo_restream.tempfile, "mkdtemp",
                                       side_effect=AssertionError(
                                           "no debía escribir nada")):
                    _, salida = directo_restream._correr(
                        args, paso_cero=lambda c=codigo: (False, f"salida {c}"),
                        preparar=preparar)
                self.assertEqual(salida, 2)
                self.assertFalse(llamado["preparar"])



class CuentaFalsa:

    def __init__(self, canales):
        self.canales_actuales = list(canales)
        self.activados = []
        self.eliminados = []

    def canales(self):
        return list(self.canales_actuales)

    def activar_canal(self, identificador, activo):
        self.activados.append((identificador, activo))

    def eliminar_canal(self, identificador):
        self.eliminados.append(identificador)


def _pasos(funcion, estado, cuenta):
    pasos = []

    def anotar(nombre, bien, detalle=""):
        pasos.append((nombre, bien, detalle))

    funcion(estado, anotar, cuenta)
    return pasos


def _buscar(pasos, nombre):
    return [paso for paso in pasos if paso[0] == nombre]


class TestLaAppDevuelveLosDestinos(unittest.TestCase):

    def test_con_cambios_la_app_queda_en_mal_y_la_restauracion_en_bien(self):
        antes = {1: True, 2: False}
        actuales = [CanalFalso(1, activo=False), CanalFalso(2, activo=True)]
        cuenta = CuentaFalsa(actuales)
        pasos = _pasos(paso_restaurar_destinos,
                       {"antes": antes, "finalizado": True}, cuenta)
        app = _buscar(pasos, "la app devolvió los destinos")
        self.assertEqual(len(app), 1)
        self.assertFalse(app[0][1])
        self.assertIn("1", app[0][2])
        self.assertIn("2", app[0][2])
        restauracion = _buscar(pasos, "destinos de Restream")
        self.assertEqual(len(restauracion), 1)
        self.assertTrue(restauracion[0][1])
        self.assertEqual(cuenta.activados, [(1, True), (2, False)])

    def test_sin_cambios_la_app_queda_en_bien(self):
        antes = {1: True, 2: False}
        actuales = [CanalFalso(1, activo=True), CanalFalso(2, activo=False)]
        cuenta = CuentaFalsa(actuales)
        pasos = _pasos(paso_restaurar_destinos,
                       {"antes": antes, "finalizado": True}, cuenta)
        app = _buscar(pasos, "la app devolvió los destinos")
        self.assertEqual(len(app), 1)
        self.assertTrue(app[0][1])
        restauracion = _buscar(pasos, "destinos de Restream")
        self.assertTrue(restauracion[0][1])
        self.assertEqual(cuenta.activados, [])

    def test_sin_finalizar_no_se_anota_el_paso_de_la_app(self):
        antes = {1: True}
        actuales = [CanalFalso(1, activo=False)]
        cuenta = CuentaFalsa(actuales)
        pasos = _pasos(paso_restaurar_destinos, {"antes": antes}, cuenta)
        self.assertEqual(_buscar(pasos, "la app devolvió los destinos"), [])
        restauracion = _buscar(pasos, "destinos de Restream")
        self.assertTrue(restauracion[0][1])
        self.assertEqual(cuenta.activados, [(1, True)])


class TestLaAppBorraElManual(unittest.TestCase):

    def _antes(self):
        return [CanalFalso(1, nombre="Szeiryu", plataforma_id=5)]

    def _manual(self):
        return CanalFalso(9, nombre=NOMBRE_MANUAL, plataforma_id=29)

    def test_con_sobrante_la_app_queda_en_mal_y_el_borrado_en_bien(self):
        antes = self._antes()
        cuenta = CuentaFalsa(antes + [self._manual()])
        pasos = _pasos(paso_borrar_manual,
                       {"canales_antes": antes, "finalizado": True}, cuenta)
        app = _buscar(pasos, "la app borró el destino manual")
        self.assertEqual(len(app), 1)
        self.assertFalse(app[0][1])
        self.assertIn("9", app[0][2])
        borrado = _buscar(pasos, "destino manual de YouTube")
        self.assertTrue(borrado[0][1])
        self.assertEqual(cuenta.eliminados, [9])

    def test_sin_sobrantes_la_app_queda_en_bien(self):
        antes = self._antes()
        cuenta = CuentaFalsa(antes)
        pasos = _pasos(paso_borrar_manual,
                       {"canales_antes": antes, "finalizado": True}, cuenta)
        app = _buscar(pasos, "la app borró el destino manual")
        self.assertEqual(len(app), 1)
        self.assertTrue(app[0][1])
        borrado = _buscar(pasos, "destino manual de YouTube")
        self.assertTrue(borrado[0][1])
        self.assertEqual(cuenta.eliminados, [])

    def test_sin_finalizar_no_se_anota_el_paso_de_la_app(self):
        antes = self._antes()
        cuenta = CuentaFalsa(antes + [self._manual()])
        pasos = _pasos(paso_borrar_manual, {"canales_antes": antes}, cuenta)
        self.assertEqual(_buscar(pasos, "la app borró el destino manual"), [])
        borrado = _buscar(pasos, "destino manual de YouTube")
        self.assertTrue(borrado[0][1])
        self.assertEqual(cuenta.eliminados, [9])


if __name__ == "__main__":
    unittest.main()
