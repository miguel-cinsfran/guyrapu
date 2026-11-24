# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del archivo de los disparadores."""

import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import disparadores, disparadores_guardados, paquetes


def _datos(**cambios):
    datos = {
        "nombre": "aplauso", "cuando": "evento", "evento": "superchat",
        "minimo": None, "regalo": "", "medio": "fuegos", "destino": "video",
        "tarjeta": "",
        "estilo": "clasico", "segundos": 8, "permiso": "todos",
        "nombres": [], "espera_general": 5.0, "espera_persona": 30.0,
        "activo": True, "avisar": False,
    }
    datos.update(cambios)
    return datos


class TestConversion(unittest.TestCase):

    def test_a_disparador_y_de_vuelta_conserva_los_datos(self):
        datos = _datos()
        disparador = disparadores_guardados.a_disparador(datos)
        self.assertIsInstance(disparador, disparadores.Disparador)
        self.assertEqual(disparador.nombre, "aplauso")
        self.assertEqual(disparadores_guardados.desde_disparador(disparador),
                         datos)

    def test_un_disparador_de_evento_con_su_minimo(self):
        datos = _datos(nombre="regalo", evento="superchat", minimo=5,
                       medio="")
        datos["tarjeta"] = "Gracias {usuario}"
        disparador = disparadores_guardados.a_disparador(datos)
        self.assertEqual(disparador.evento, "superchat")
        self.assertEqual(disparador.minimo, 5)
        self.assertEqual(disparadores_guardados.desde_disparador(disparador),
                         datos)

    def test_un_disparador_sin_datos_nace_con_los_valores_de_fabrica(self):
        disparador = disparadores_guardados.a_disparador({})
        self.assertEqual(disparador.cuando, "evento")
        self.assertEqual(disparador.evento, "")
        self.assertIsNone(disparador.minimo)
        self.assertEqual(disparador.medio, "")
        self.assertEqual(disparador.permiso, "todos")
        self.assertEqual((disparador.espera_general, disparador.espera_persona),
                         (5, 30))
        self.assertTrue(disparador.activo)
        self.assertEqual(disparador.estilo, "clasico")
        self.assertEqual(disparador.segundos, 8)
        self.assertFalse(disparador.avisar)

    def test_una_alerta_guardada_sin_destino_se_abre_en_el_video(self):
        datos = _datos()
        del datos["destino"]
        disparador = disparadores_guardados.a_disparador(datos)
        self.assertEqual(disparador.destino, "video")
        self.assertEqual(
            disparadores_guardados.desde_disparador(disparador)["destino"],
            "video")

    def test_un_destino_desconocido_pasa_a_video(self):
        self.assertEqual(
            disparadores_guardados.a_disparador({"destino": "otro"}).destino,
            "video")

    def test_los_tipos_se_fuerzan_y_lo_raro_cae_a_su_defecto(self):
        disparador = disparadores_guardados.a_disparador({
            "nombre": "aplauso", "cuando": "tecla", "evento": "comando",
            "minimo": "mucho", "permiso": "otro", "nombres": "Ana, Beto",
            "espera_general": "7", "espera_persona": "no",
            "activo": "true", "segundos": "90",
        })
        self.assertEqual(disparador.cuando, "evento")
        self.assertEqual(disparador.evento, "")
        self.assertIsNone(disparador.minimo)
        self.assertEqual(disparador.permiso, "todos")
        self.assertEqual(disparador.nombres, ("Ana", "Beto"))
        self.assertEqual(disparador.espera_general, 7)
        self.assertEqual(disparador.espera_persona, 30)
        self.assertTrue(disparador.activo)
        self.assertEqual(disparador.segundos, 60)


class TestAvisar(unittest.TestCase):

    def test_una_alerta_guardada_sin_avisar_se_lee_con_avisar_falso(self):
        datos = _datos()
        del datos["avisar"]
        self.assertFalse(disparadores_guardados.a_disparador(datos).avisar)

    def test_avisar_se_guarda_y_se_lee(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "disparadores.json"
            disparadores_guardados.guardar(
                ruta, [disparadores.Disparador("aviso", avisar=True)])
            self.assertTrue(disparadores_guardados.a_disparador(
                disparadores_guardados.cargar(ruta)[0]).avisar)


class TestEstilo(unittest.TestCase):

    def test_un_estilo_explicito_no_cambia(self):
        self.assertEqual(
            disparadores_guardados.a_disparador(
                {"estilo": "clasico"}).estilo, "clasico")
        self.assertEqual(
            disparadores_guardados.a_disparador({"estilo": "mio"}).estilo,
            "mio")

    def test_el_estilo_vacio_se_conserva(self):
        self.assertEqual(
            disparadores_guardados.a_disparador({"estilo": ""}).estilo, "")

    def test_sin_el_dato_el_estilo_es_clasico(self):
        self.assertEqual(
            disparadores_guardados.a_disparador({}).estilo, "clasico")

    def test_un_disparador_nuevo_nace_con_el_estilo_vacio(self):
        self.assertEqual(disparadores.Disparador("aplauso").estilo, "")


class TestArchivo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "disparadores.json"

    def test_p4_el_regalo_se_guarda_y_se_lee_del_archivo(self):
        datos = _datos(nombre="leon", regalo="León", medio="")
        disparadores_guardados.guardar(
            self.ruta, [disparadores_guardados.a_disparador(datos)])
        self.assertEqual(disparadores_guardados.cargar(self.ruta), [datos])

    def test_p4_un_archivo_sin_regalo_lo_lee_vacio(self):
        sin_regalo = _datos()
        del sin_regalo["regalo"]
        self.assertEqual(
            disparadores_guardados.a_disparador(sin_regalo).regalo, "")

    def test_los_paquetes_llevan_el_evento(self):
        datos = _datos(nombre="regalo", evento="cofre")
        paquetes.exportar(self.ruta.with_suffix(".zip"), "disparadores",
                          [datos])
        paquete = paquetes.leer(self.ruta.with_suffix(".zip"), "disparadores")
        self.assertEqual(paquete.elementos, [datos])

    def test_ida_y_vuelta_por_el_archivo(self):
        disparadores_guardados.guardar(self.ruta, [_datos()])
        self.assertEqual(disparadores_guardados.cargar(self.ruta), [_datos()])

    def test_guarda_un_disparador_de_verdad(self):
        disparador = disparadores.Disparador(
            "regalo", evento="cofre", minimo=25,
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
