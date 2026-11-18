# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del archivo de los disparadores."""

import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import disparadores, disparadores_guardados


def _datos(**cambios):
    datos = {
        "nombre": "aplauso", "cuando": "comando", "comandos": ["aplauso"],
        "evento": "", "minimo": None, "medio": "fuegos", "tarjeta": "",
        "estilo": "clasico", "segundos": 8, "permiso": "todos",
        "nombres": [], "espera_general": 5.0, "espera_persona": 30.0,
        "activo": True,
    }
    datos.update(cambios)
    return datos


class TestConversion(unittest.TestCase):

    def test_a_disparador_y_de_vuelta_conserva_los_datos(self):
        datos = _datos()
        disparador = disparadores_guardados.a_disparador(datos)
        self.assertIsInstance(disparador, disparadores.Disparador)
        self.assertEqual(disparador.nombre, "aplauso")
        self.assertEqual(disparador.comandos, ("aplauso",))
        self.assertEqual(disparadores_guardados.desde_disparador(disparador),
                         datos)

    def test_un_disparador_de_evento_con_su_minimo(self):
        datos = _datos(nombre="regalo", cuando="evento", comandos=[],
                       evento="superchat", minimo=5, medio="")
        datos["tarjeta"] = "Gracias {usuario}"
        disparador = disparadores_guardados.a_disparador(datos)
        self.assertEqual(disparador.evento, "superchat")
        self.assertEqual(disparador.minimo, 5)
        self.assertEqual(disparadores_guardados.desde_disparador(disparador),
                         datos)

    def test_un_disparador_sin_datos_nace_con_los_valores_de_fabrica(self):
        disparador = disparadores_guardados.a_disparador({})
        self.assertEqual(disparador.cuando, "comando")
        self.assertEqual(disparador.comandos, ())
        self.assertEqual(disparador.evento, "")
        self.assertIsNone(disparador.minimo)
        self.assertEqual(disparador.medio, "")
        self.assertEqual(disparador.permiso, "todos")
        self.assertEqual((disparador.espera_general, disparador.espera_persona),
                         (5, 30))
        self.assertTrue(disparador.activo)
        self.assertEqual(disparador.estilo, "clasico")
        self.assertEqual(disparador.segundos, 8)

    def test_los_tipos_se_fuerzan_y_lo_raro_cae_a_su_defecto(self):
        disparador = disparadores_guardados.a_disparador({
            "nombre": "aplauso", "cuando": "tecla", "comandos": "uno, dos",
            "evento": "comando", "minimo": "mucho", "permiso": "otro",
            "nombres": "Ana, Beto", "espera_general": "7",
            "espera_persona": "no", "activo": "true", "segundos": "90",
        })
        self.assertEqual(disparador.cuando, "comando")
        self.assertEqual(disparador.comandos, ("uno", "dos"))
        self.assertEqual(disparador.evento, "")
        self.assertIsNone(disparador.minimo)
        self.assertEqual(disparador.permiso, "todos")
        self.assertEqual(disparador.nombres, ("Ana", "Beto"))
        self.assertEqual(disparador.espera_general, 7)
        self.assertEqual(disparador.espera_persona, 30)
        self.assertTrue(disparador.activo)
        self.assertEqual(disparador.segundos, 60)


class TestArchivo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "disparadores.json"

    def test_ida_y_vuelta_por_el_archivo(self):
        disparadores_guardados.guardar(self.ruta, [_datos()])
        self.assertEqual(disparadores_guardados.cargar(self.ruta), [_datos()])

    def test_guarda_un_disparador_de_verdad(self):
        disparador = disparadores.Disparador(
            "regalo", cuando="evento", evento="cofre", minimo=25,
            medio="fuegos", tarjeta="Gracias", estilo="banda", segundos=12,
            permiso="moderadores", espera_general=10, espera_persona=20,
            activo=False)
        disparadores_guardados.guardar(self.ruta, [disparador])
        cargado = disparadores_guardados.cargar(self.ruta)
        self.assertEqual(cargado[0]["cuando"], "evento")
        self.assertEqual(cargado[0]["evento"], "cofre")
        self.assertEqual(cargado[0]["minimo"], 25)
        self.assertEqual(cargado[0]["tarjeta"], "Gracias")
        self.assertEqual(cargado[0]["segundos"], 12)
        self.assertFalse(cargado[0]["activo"])

    def test_un_archivo_danado_se_lee_como_lista_vacia(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(disparadores_guardados.cargar(self.ruta), [])

    def test_un_archivo_ausente_se_lee_como_lista_vacia(self):
        self.assertEqual(disparadores_guardados.cargar(self.ruta), [])

    def test_un_json_que_no_es_lista_se_lee_como_lista_vacia(self):
        self.ruta.write_text('{"nombre": "aplauso"}', encoding="utf-8")
        self.assertEqual(disparadores_guardados.cargar(self.ruta), [])


if __name__ == "__main__":
    unittest.main()
