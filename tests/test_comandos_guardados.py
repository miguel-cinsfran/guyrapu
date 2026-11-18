# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del archivo de los comandos del chat."""

import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import comandos, comandos_guardados


def _datos(**cambios):
    datos = {
        "nombre": "discord", "alias": ["dc"], "respuesta": "Hola {usuario}",
        "destino": "chat", "permiso": "lista", "nombres": ["Ana"],
        "espera_general": 5.0, "espera_persona": 30.0, "activo": True,
        "estilo": "clasico", "segundos": 8,
    }
    datos.update(cambios)
    return datos


class TestConversion(unittest.TestCase):

    def test_a_comando_y_de_vuelta_conserva_los_datos(self):
        datos = _datos()
        comando = comandos_guardados.a_comando(datos)
        self.assertIsInstance(comando, comandos.Comando)
        self.assertEqual(comando.nombre, "discord")
        self.assertEqual(comando.alias, ("dc",))
        self.assertEqual(comando.nombres, ("Ana",))
        self.assertEqual(comandos_guardados.desde_comando(comando), datos)

    def test_un_comando_sin_datos_nace_con_los_valores_de_fabrica(self):
        comando = comandos_guardados.a_comando({})
        self.assertEqual(comando.destino, "video")
        self.assertEqual(comando.permiso, "todos")
        self.assertEqual((comando.espera_general, comando.espera_persona),
                         (5, 30))
        self.assertTrue(comando.activo)
        self.assertEqual(comando.estilo, "clasico")
        self.assertEqual(comando.segundos, 8)

    def test_los_tipos_se_fuerzan_y_lo_raro_cae_a_su_defecto(self):
        comando = comandos_guardados.a_comando({
            "nombre": "hola", "alias": "uno dos, tres", "nombres": "Ana, Beto",
            "destino": "otro", "permiso": "otro", "espera_general": "7",
            "espera_persona": "no", "activo": "true", "segundos": "90",
        })
        self.assertEqual(comando.alias, ("uno", "dos", "tres"))
        self.assertEqual(comando.nombres, ("Ana", "Beto"))
        self.assertEqual(comando.destino, "video")
        self.assertEqual(comando.permiso, "todos")
        self.assertEqual(comando.espera_general, 7)
        self.assertEqual(comando.espera_persona, 30)
        self.assertTrue(comando.activo)
        self.assertEqual(comando.segundos, 60)


class TestEstilo(unittest.TestCase):

    def test_un_estilo_explicito_no_cambia(self):
        self.assertEqual(
            comandos_guardados.a_comando({"estilo": "clasico"}).estilo,
            "clasico")
        self.assertEqual(
            comandos_guardados.a_comando({"estilo": "mio"}).estilo, "mio")

    def test_el_estilo_vacio_se_conserva(self):
        self.assertEqual(
            comandos_guardados.a_comando({"estilo": ""}).estilo, "")

    def test_sin_el_dato_el_estilo_es_clasico(self):
        self.assertEqual(comandos_guardados.a_comando({}).estilo, "clasico")

    def test_un_comando_nuevo_nace_con_el_estilo_vacio(self):
        self.assertEqual(comandos.Comando("hola", (), "Hola").estilo, "")


class TestArchivo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "comandos.json"

    def test_ida_y_vuelta_por_el_archivo(self):
        comandos_guardados.guardar(self.ruta, [_datos()])
        self.assertEqual(comandos_guardados.cargar(self.ruta), [_datos()])

    def test_guarda_un_comando_de_verdad(self):
        comando = comandos.Comando(
            "!saludo", ("!hola",), "Hola {usuario}", destino="ambos",
            permiso="moderadores", espera_general=10, espera_persona=20,
            activo=False, estilo="banda", segundos=12)
        comandos_guardados.guardar(self.ruta, [comando])
        cargado = comandos_guardados.cargar(self.ruta)
        self.assertEqual(cargado[0]["nombre"], "saludo")
        self.assertEqual(cargado[0]["alias"], ["hola"])
        self.assertEqual(cargado[0]["destino"], "ambos")
        self.assertEqual(cargado[0]["segundos"], 12)
        self.assertFalse(cargado[0]["activo"])

    def test_un_archivo_danado_se_lee_como_lista_vacia(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(comandos_guardados.cargar(self.ruta), [])

    def test_un_archivo_ausente_se_lee_como_lista_vacia(self):
        self.assertEqual(comandos_guardados.cargar(self.ruta), [])

    def test_un_json_que_no_es_lista_se_lee_como_lista_vacia(self):
        self.ruta.write_text('{"nombre": "hola"}', encoding="utf-8")
        self.assertEqual(comandos_guardados.cargar(self.ruta), [])


if __name__ == "__main__":
    unittest.main()
