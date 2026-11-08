# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del recorrido de la versión vertical desde el Panel de OBS.

Sin ventanas: una página falsa y los hilos del Panel ejecutados en el acto.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.obs import disenos_escena, obs_cliente
from guyrapu.obs.disenos_escena import Diseno
from guyrapu.ui import escena_version_vertical


class PerfilesFalsos:

    def __init__(self):
        self.actual = "Horizontal"
        self.cambios = []

    def listar(self, cliente, parada=None):
        return ["Horizontal", "Vertical"], self.actual

    def cambiar(self, cliente, nombre, parada=None):
        self.cambios.append((cliente, nombre))
        self.actual = nombre


class OperacionesFalsas:

    def __init__(self):
        self.en_vuelo = False
        self.fallos = []

    def en_hilo(self, funcion, al_terminar=None):
        self.en_vuelo = True
        try:
            resultado = funcion()
        except obs_cliente.ObsError as error:
            self.fallos.append(str(error))
            return
        finally:
            self.en_vuelo = False
        if al_terminar is not None:
            al_terminar(resultado)


class GestorFalso:

    def __init__(self):
        self._cliente = SimpleNamespace()
        self.pedidos = []

    def _pedir(self, tipo, datos=None, parada=None):
        self.pedidos.append((tipo, datos))
        return {}


class PaginaFalsa:

    def __init__(self, escena="Escena", nombres=("Escena",), config=None):
        self._escena = escena
        self._nombres_lista = list(nombres)
        self._ventana = SimpleNamespace(
            _principal=SimpleNamespace(_config=config or {}))
        self._gestor = GestorFalso()
        self._operaciones = OperacionesFalsas()
        self._registro = mock.Mock()
        self.lst_escenas = SimpleNamespace(SetFocus=lambda: None)
        self.mostradas = []

    def escena(self):
        return self._escena

    def _nombres(self):
        return tuple(self._nombres_lista)

    def _leer_escenas(self, escena):
        return ("datos", escena)

    def _mostrar_leidas(self, datos):
        self.mostradas.append(datos[1])


def _fuente(nombre="Juego", tipo="otra"):
    return disenos_escena.Fuente(nombre, tipo, 1600, 900)


class PaginaFuentesFalsa:

    def __init__(self, nombres=("Escena", "Escena vertical"), config=None):
        pagina_escena = SimpleNamespace(_nombres=lambda: tuple(nombres))
        self._ventana = SimpleNamespace(
            _principal=SimpleNamespace(_config=config or {"perfil_vertical":
                                                         "Vertical"}),
            _pagina_escena=pagina_escena)
        self._gestor = GestorFalso()
        self._operaciones = OperacionesFalsas()
        self._registro = mock.Mock()
        self.btn_diseno = SimpleNamespace(SetFocus=lambda: None)
        self.lst_escenas = self.btn_diseno
        self.cargadas = []

    def cargar(self, filas, fuente):
        self.cargadas.append((filas, fuente))

    def fuente(self):
        return ""


class CrearTest(unittest.TestCase):

    def setUp(self):
        self.anuncios = []
        self.perfiles = PerfilesFalsos()
        self.parches = [
            mock.patch.object(escena_version_vertical, "anunciar",
                              self.anuncios.append),
            mock.patch.object(escena_version_vertical.perfiles_obs,
                              "listar_perfiles", self.perfiles.listar),
            mock.patch.object(escena_version_vertical.perfiles_obs,
                              "cambiar", self.perfiles.cambiar),
            mock.patch.object(escena_version_vertical.perfiles_obs,
                              "comprobar_salidas"),
            mock.patch.object(escena_version_vertical.escenas_obs, "duplicar"),
            mock.patch.object(escena_version_vertical.escenas_obs, "eliminar"),
            mock.patch.object(escena_version_vertical.aplicar_diseno,
                              "fuentes_y_lienzo",
                              return_value=([_fuente()], True)),
            mock.patch.object(escena_version_vertical.aplicar_diseno,
                              "aplicar_diseno", return_value=([], [])),
            mock.patch.object(escena_version_vertical.disenos_guardados,
                              "cargar", return_value=[]),
            mock.patch.object(escena_version_vertical.disenos_fabrica,
                              "resumen", return_value="Resumen"),
            mock.patch.object(escena_version_vertical, "_puerto",
                              return_value=9000),
        ]
        for parche in self.parches:
            parche.start()
            self.addCleanup(parche.stop)

    def _pagina(self, **extras):
        return PaginaFalsa(config={"perfil_vertical": "Vertical"}, **extras)

    def test_sin_perfil_vertical_no_crea_nada_y_dice_donde_elegirlo(self):
        pagina = PaginaFalsa(config={})
        escena_version_vertical.crear(pagina)
        self.assertEqual(self.anuncios,
                         [escena_version_vertical.MENSAJE_SIN_PERFIL])
        escena_version_vertical.escenas_obs.duplicar.assert_not_called()

    def test_con_una_salida_en_marcha_no_crea_nada_y_dice_por_que(self):
        escena_version_vertical.perfiles_obs.comprobar_salidas.side_effect = (
            obs_cliente.ObsError("No se puede cambiar el perfil de OBS con "
                                 "una salida en marcha."))
        pagina = self._pagina()
        escena_version_vertical.crear(pagina)
        self.assertIn("salida en marcha", pagina._operaciones.fallos[0])
        escena_version_vertical.escenas_obs.duplicar.assert_not_called()

    def test_si_ya_existe_lo_dice_y_no_crea_otra(self):
        pagina = self._pagina(nombres=("Escena", "Escena vertical"))
        escena_version_vertical.crear(pagina)
        self.assertEqual(
            self.anuncios,
            ["Ya existe la escena Escena vertical. Para acomodarla, usa "
             "Aplicar diseño sobre ella."])
        escena_version_vertical.escenas_obs.duplicar.assert_not_called()

    def test_crea_con_las_mismas_fuentes_aplica_el_diseno_y_vuelve(self):
        pagina = self._pagina()
        diseno = Diseno(clase="pantalla_completa", principal="Juego")
        with mock.patch.object(escena_version_vertical.escena_disenos,
                               "pedir_diseno",
                               return_value=("Diseño", diseno)) as pedir:
            escena_version_vertical.crear(pagina)
        escena_version_vertical.escenas_obs.duplicar.assert_called_once_with(
            pagina._gestor._pedir, "Escena", "Escena vertical")
        self.assertEqual([nombre for _cliente, nombre in self.perfiles.cambios],
                         ["Vertical", "Horizontal"])
        self.assertTrue(pedir.call_args.args[3])
        escena_version_vertical.aplicar_diseno.aplicar_diseno.assert_called_once()
        self.assertEqual(pagina.mostradas, ["Escena vertical"])
        self.assertEqual(self.anuncios[0],
                         escena_version_vertical.MENSAJE_EMPEZANDO)
        self.assertEqual(
            self.anuncios[-1],
            "Versión vertical creada: Escena vertical. Diseño: Diseño.")

    def test_cancelar_el_diseno_elimina_la_escena_y_vuelve_al_perfil(self):
        pagina = self._pagina()
        with mock.patch.object(escena_version_vertical.escena_disenos,
                               "pedir_diseno", return_value=None):
            escena_version_vertical.crear(pagina)
        escena_version_vertical.escenas_obs.eliminar.assert_called_once_with(
            pagina._gestor._pedir, "Escena vertical")
        self.assertEqual([nombre for _cliente, nombre in self.perfiles.cambios],
                         ["Vertical", "Horizontal"])
        escena_version_vertical.aplicar_diseno.aplicar_diseno.assert_not_called()
        self.assertEqual(pagina.mostradas, ["Escena"])
        self.assertEqual(self.anuncios[-1],
                         escena_version_vertical.MENSAJE_CANCELADA)

    def test_si_aplicar_falla_vuelve_al_perfil_e_igual_la_escena(self):
        pagina = self._pagina()
        diseno = Diseno(clase="pantalla_completa", principal="Juego")
        escena_version_vertical.aplicar_diseno.aplicar_diseno.side_effect = (
            RuntimeError("no se pudo acomodar"))
        with mock.patch.object(escena_version_vertical.escena_disenos,
                               "pedir_diseno", return_value=("Diseño", diseno)):
            escena_version_vertical.crear(pagina)
        self.assertIn("no se pudo acomodar", pagina._operaciones.fallos[0])
        self.assertIn("OBS volvió al perfil Horizontal.",
                      pagina._operaciones.fallos[0])
        escena_version_vertical.escenas_obs.eliminar.assert_not_called()
        self.assertEqual(self.perfiles.actual, "Horizontal")


class AplicarAGemelaTest(unittest.TestCase):

    def setUp(self):
        self.anuncios = []
        self.perfiles = PerfilesFalsos()
        self.parches = [
            mock.patch.object(escena_version_vertical, "anunciar",
                              self.anuncios.append),
            mock.patch.object(escena_version_vertical.perfiles_obs,
                              "listar_perfiles", self.perfiles.listar),
            mock.patch.object(escena_version_vertical.perfiles_obs,
                              "cambiar", self.perfiles.cambiar),
            mock.patch.object(escena_version_vertical.aplicar_diseno,
                              "fuentes_y_lienzo",
                              return_value=([_fuente()], True)),
            mock.patch.object(escena_version_vertical.aplicar_diseno,
                              "aplicar_diseno", return_value=([], [])),
            mock.patch.object(escena_version_vertical.disenos_guardados,
                              "cargar", return_value=[]),
            mock.patch.object(escena_version_vertical.disenos_fabrica,
                              "resumen", return_value="Resumen"),
            mock.patch.object(escena_version_vertical.consultas_transmision,
                              "leer_filas", return_value=("fila",)),
            mock.patch.object(escena_version_vertical, "_puerto",
                              return_value=9000),
        ]
        for parche in self.parches:
            parche.start()
            self.addCleanup(parche.stop)

    def test_una_gemela_con_original_se_acomoda_con_el_perfil_vertical(self):
        pagina = PaginaFuentesFalsa()
        self.assertTrue(
            escena_version_vertical.es_gemela_con_original(
                pagina, "Escena vertical"))
        diseno = Diseno(clase="pantalla_completa", principal="Juego")
        with mock.patch.object(escena_version_vertical.escena_disenos,
                               "pedir_diseno",
                               return_value=("Diseño", diseno)) as pedir:
            escena_version_vertical.aplicar_a_gemela(pagina, "Escena vertical")
        self.assertEqual([nombre for _cliente, nombre in self.perfiles.cambios],
                         ["Vertical", "Horizontal"])
        self.assertTrue(pedir.call_args.args[3])
        escena_version_vertical.aplicar_diseno.aplicar_diseno.assert_called_once()
        self.assertEqual(pagina.cargadas, [(("fila",), "")])
        self.assertEqual(self.anuncios, ["Resumen"])

    def test_una_escena_normal_no_es_gemela(self):
        pagina = PaginaFuentesFalsa()
        self.assertFalse(
            escena_version_vertical.es_gemela_con_original(pagina, "Escena"))

    def test_cancelar_el_diseno_de_la_gemela_vuelve_al_perfil(self):
        pagina = PaginaFuentesFalsa()
        with mock.patch.object(escena_version_vertical.escena_disenos,
                               "pedir_diseno", return_value=None):
            escena_version_vertical.aplicar_a_gemela(pagina, "Escena vertical")
        self.assertEqual([nombre for _cliente, nombre in self.perfiles.cambios],
                         ["Vertical", "Horizontal"])
        escena_version_vertical.aplicar_diseno.aplicar_diseno.assert_not_called()
        self.assertEqual(self.anuncios, [])


if __name__ == "__main__":
    unittest.main()
