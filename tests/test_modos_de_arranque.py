# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las salidas tempranas de `main.py`, sin abrir ventanas."""

import unittest
from unittest import mock

import main
from guyrapu.core import autocomprobacion, instalador, modos_de_arranque
from guyrapu.obs import animador
from guyrapu.youtube import finalizar_aparte


class TestCorrer(unittest.TestCase):

    def test_arranque_normal_no_es_un_modo_especial(self):
        self.assertIsNone(modos_de_arranque.correr([]))
        self.assertIsNone(modos_de_arranque.correr(["--otra-cosa"]))

    def test_autocomprobar_pasa_los_argumentos(self):
        with mock.patch.object(autocomprobacion, "principal",
                               return_value=4) as principal:
            codigo = modos_de_arranque.correr(
                ["--autocomprobar", "ruta.txt"])
        self.assertEqual(codigo, 4)
        principal.assert_called_once_with(["ruta.txt"])

    def test_instalador_conserva_su_orden_sin_argumentos(self):
        with mock.patch.object(instalador, "principal_instalador",
                               return_value=5) as principal:
            codigo = modos_de_arranque.correr(
                ["--instalar-actualizacion", "otro"])
        self.assertEqual(codigo, 5)
        principal.assert_called_once_with()

    def test_animador_recibe_la_direccion_del_canal(self):
        with mock.patch.object(animador, "principal",
                               return_value=6) as principal:
            codigo = modos_de_arranque.correr(
                ["--animador", "direccion"])
        self.assertEqual(codigo, 6)
        principal.assert_called_once_with(["direccion"])

    def test_finalizar_pendientes_corre_su_modo(self):
        with mock.patch.object(finalizar_aparte, "principal",
                               return_value=7) as principal:
            codigo = modos_de_arranque.correr(["--finalizar-pendientes"])
        self.assertEqual(codigo, 7)
        principal.assert_called_once_with(["--finalizar-pendientes"])


class TestMainUsaLosModos(unittest.TestCase):

    def test_main_sale_con_el_codigo_del_modo_antes_de_migrar(self):
        with mock.patch.object(main.modos_de_arranque, "correr",
                               return_value=9) as correr, \
                mock.patch.object(main.migracion_datos, "migrar") as migrar:
            with self.assertRaises(SystemExit) as salida:
                main.main()

        self.assertEqual(salida.exception.code, 9)
        correr.assert_called_once_with(main.sys.argv[1:])
        migrar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
