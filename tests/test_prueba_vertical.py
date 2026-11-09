# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de cómo se suma el lienzo vertical a la prueba del equipo.

Sin ventanas y sin OBS real: un doble anota el orden de las peticiones y
una carpeta temporal hace de carpeta de grabación del plugin.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.obs import prueba_vertical


class DobleObs:

    def __init__(self, carpeta, bufer=False):
        self.carpeta = Path(carpeta)
        self.bufer = bufer
        self.grabando = False
        self.eventos = []
        self.creadas = 0

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "StartRecord":
            self.eventos.append("principal:inicio")
            return {"responseData": {"outputPath": ""}}
        if tipo == "StopRecord":
            self.eventos.append("principal:fin")
            ruta = self.carpeta / "2026-11-08 21-05-54.mp4"
            ruta.write_text("video", encoding="utf-8")
            return {"responseData": {"outputPath": str(ruta)}}
        if tipo == "GetRecordDirectory":
            return {"responseData": {"recordDirectory": str(self.carpeta)}}
        if tipo == "CallVendorRequest":
            return self._vendor((datos or {}).get("requestType"))
        return {"responseData": {}}

    def _vendor(self, pedido):
        self.eventos.append("vertical:" + pedido)
        if pedido == "status":
            return self._respuesta({
                "success": True, "recording": self.grabando,
                "backtrack": self.bufer})
        if pedido == "start_recording":
            self.grabando = True
            self.creadas += 1
            nombre = "2026-11-08 21-05-5%d-vertical.mp4" % self.creadas
            (self.carpeta / nombre).write_text("video", encoding="utf-8")
        elif pedido == "stop_recording":
            self.grabando = False
        elif pedido == "stop_backtrack":
            self.bufer = False
        return self._respuesta({"success": True})

    @staticmethod
    def _respuesta(datos):
        return {"responseData": {"responseData": dict(datos)}}


class BasePruebaVertical(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)

    def _cliente(self, **kwargs):
        self.doble = DobleObs(self.carpeta, **kwargs)
        return prueba_vertical.ClienteVertical(
            self.doble, carpeta=self.carpeta)

    def _correr_escalon(self, cliente):
        cliente.pedir("StartRecord")
        cliente.pedir("StopRecord")


class OrdenTest(BasePruebaVertical):

    def test_el_vertical_arranca_despues_del_principal_y_se_detiene_antes(
            self):
        cliente = self._cliente()
        self._correr_escalon(cliente)
        eventos = self.doble.eventos
        self.assertLess(eventos.index("principal:inicio"),
                        eventos.index("vertical:start_recording"))
        self.assertLess(eventos.index("vertical:stop_recording"),
                        eventos.index("principal:fin"))
        self.assertGreaterEqual(eventos.count("vertical:status"), 2)


class BorradoTest(BasePruebaVertical):

    def test_borra_solo_las_grabaciones_verticales_nuevas(self):
        vieja = self.carpeta / "2026-11-07 10-00-00-vertical.mp4"
        vieja.write_text("vieja", encoding="utf-8")
        ajena = self.carpeta / "2026-11-07 10-00-00.mp4"
        ajena.write_text("ajena", encoding="utf-8")

        cliente = self._cliente()
        self._correr_escalon(cliente)

        self.assertFalse(list(self.carpeta.glob("2026-11-08*-vertical.mp4")))
        self.assertTrue(vieja.is_file())
        self.assertTrue(ajena.is_file())

    def test_reintenta_borrar_mientras_obs_tiene_el_archivo(self):
        intentos = {"vertical": 0}
        unlink_original = Path.unlink

        def unlink(ruta, missing_ok=False):
            if "-vertical" in Path(ruta).name:
                intentos["vertical"] += 1
                if intentos["vertical"] < 3:
                    raise PermissionError(13, "archivo en uso")
            return unlink_original(ruta, missing_ok=missing_ok)

        cliente = self._cliente()
        with mock.patch.object(prueba_vertical.Path, "unlink", unlink), \
                mock.patch.object(prueba_vertical, "_PASO_BORRADO", 0.0):
            self._correr_escalon(cliente)
        self.assertFalse(list(self.carpeta.glob("*-vertical.mp4")))
        self.assertGreaterEqual(intentos["vertical"], 3)


class BuferTest(BasePruebaVertical):

    def test_apaga_el_bufer_solo_si_lo_encendio_la_prueba(self):
        for estaba in (False, True):
            with self.subTest(estaba=estaba):
                carpeta = self.carpeta / ("bufer-%s" % estaba)
                carpeta.mkdir()
                self.carpeta = carpeta
                cliente = self._cliente(bufer=estaba)
                self._correr_escalon(cliente)
                self.assertEqual(
                    "vertical:stop_backtrack" in self.doble.eventos,
                    not estaba)
                self.assertEqual(self.doble.bufer, estaba)


if __name__ == "__main__":
    unittest.main()
