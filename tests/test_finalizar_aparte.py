# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del proceso que finaliza directos con la app cerrada."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paths
from guyrapu.core.tiempo import TiempoDoble
from guyrapu.youtube import finalizar_aparte, fin_pendiente
from tests.rutas_temporales import redirigir_rutas

RAIZ = Path(__file__).resolve().parent.parent


_GUION_MUTEX = """
import sys
sys.path.insert(0, sys.argv[2])
from guyrapu.youtube import finalizar_aparte
finalizar_aparte._NOMBRE_MUTEX = sys.argv[1]
print(finalizar_aparte._tomar_mutex(), flush=True)
sys.stdin.readline()
"""

_GUION_LANZAR = """
import sys
sys.path.insert(0, sys.argv[2])
from pathlib import Path
from guyrapu.core import paths
paths.carpeta_datos = lambda: Path(sys.argv[1])
paths.carpeta_instalacion = lambda: Path(sys.argv[1])
from guyrapu.youtube import finalizar_aparte
sys.exit(finalizar_aparte.principal(["--finalizar-pendientes"]))
"""


class TestModoFinalizarPendientes(unittest.TestCase):

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        parche = redirigir_rutas(self._temporal.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _anotar(self, *ids):
        for id_video in ids:
            fin_pendiente.anotar(paths.fin_pendiente(), id_video)

    def _correr(self, finalizar, reloj, token=None):
        cliente = mock.Mock()
        cliente.token_actualizado.return_value = token
        with mock.patch.object(finalizar_aparte.credenciales, "cargar",
                               return_value={}), \
             mock.patch.object(finalizar_aparte.credenciales, "hay_sesion",
                               return_value=True), \
             mock.patch.object(finalizar_aparte.credenciales, "efectivas",
                               return_value={}), \
             mock.patch.object(finalizar_aparte.credenciales,
                               "guardar_campo") as guardar, \
             mock.patch.object(finalizar_aparte.youtube_api, "ClienteYouTube",
                               return_value=cliente), \
             mock.patch.object(finalizar_aparte, "_tomar_mutex",
                               return_value=True), \
             mock.patch.object(finalizar_aparte.emision,
                               "finalizar_en_youtube",
                               side_effect=finalizar):
            codigo = finalizar_aparte.principal(
                ["--finalizar-pendientes"], reloj=reloj.ahora,
                dormir=reloj.dormir)
        return codigo, guardar

    def test_finaliza_los_dos_y_duerme_30_entre_intentos(self):
        self._anotar("uno", "dos")
        reloj = TiempoDoble()
        intentos = []

        def finalizar(cliente, id_video):
            intentos.append(id_video)
            if id_video == "dos" and intentos.count("dos") < 3:
                raise RuntimeError("http://red?token=secreto")

        codigo, _guardar = self._correr(finalizar, reloj)

        self.assertEqual(codigo, 0)
        self.assertEqual(fin_pendiente.leer(paths.fin_pendiente()), [])
        self.assertEqual(reloj.dormidas, [30.0, 30.0, 30.0, 30.0])

    def test_el_tope_deja_el_id_en_el_archivo(self):
        self._anotar("lento")
        reloj = TiempoDoble()

        def finalizar(cliente, id_video):
            raise RuntimeError("sin red")

        codigo, _guardar = self._correr(finalizar, reloj)

        self.assertEqual(codigo, 0)
        self.assertEqual([e["id"] for e in
                          fin_pendiente.leer(paths.fin_pendiente())], ["lento"])
        self.assertEqual(sum(reloj.dormidas), finalizar_aparte.LIMITE)

    def test_guarda_el_token_nuevo_al_refrescar(self):
        self._anotar("uno")
        reloj = TiempoDoble()

        _codigo, guardar = self._correr(
            lambda cliente, id_video: True, reloj, token="nuevo-token")

        guardar.assert_called_once_with("token", "nuevo-token")

    def test_cada_intento_y_el_resultado_quedan_en_el_registro(self):
        self._anotar("uno", "dos")
        reloj = TiempoDoble()
        intentos = {"dos": 0}

        def finalizar(cliente, id_video):
            if id_video == "dos":
                intentos["dos"] += 1
                if intentos["dos"] < 3:
                    raise RuntimeError("http://red?token=secreto")

        self._correr(finalizar, reloj)
        lineas = paths.fin_pendiente_log().read_text(
            encoding="utf-8").splitlines()

        self.assertEqual(len(lineas), 5)
        for linea in lineas:
            self.assertRegex(linea,
                             r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} ")
            self.assertNotIn("http", linea)
            self.assertNotIn("secreto", linea)

    def test_con_el_mutex_tomado_sale_sin_leer_el_archivo(self):
        nombre = "Guyrapu_FinalizarPendientes_Prueba"
        primero = subprocess.Popen(
            [sys.executable, "-B", "-c", _GUION_MUTEX, nombre, str(RAIZ)],
            cwd=RAIZ, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(primero.stdout.readline().strip(), "True")
            with mock.patch.object(finalizar_aparte, "_NOMBRE_MUTEX", nombre), \
                    mock.patch.object(finalizar_aparte.fin_pendiente,
                                      "leer") as leer:
                codigo = finalizar_aparte.principal(["--finalizar-pendientes"])
            self.assertEqual(codigo, 0)
            leer.assert_not_called()
        finally:
            if primero.poll() is None:
                primero.stdin.write("\n")
                primero.stdin.flush()
            primero.wait(timeout=30)
            primero.stdin.close()
            primero.stdout.close()
            primero.stderr.close()

    def test_el_modo_no_importa_wx_ni_el_mutex_de_instancia(self):
        codigo = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from guyrapu.youtube import finalizar_aparte; "
            "print('wx' in sys.modules, "
            "'guyrapu.core.instancia' in sys.modules)")
        salida = subprocess.run(
            [sys.executable, "-B", "-c", codigo, str(RAIZ)],
            cwd=RAIZ, capture_output=True, text=True, timeout=60)

        self.assertEqual(salida.returncode, 0, salida.stderr)
        self.assertEqual(salida.stdout.strip(), "False False")


class TestLanzar(unittest.TestCase):

    def test_queda_aparte_y_sin_ventana(self):
        with mock.patch.object(finalizar_aparte.subprocess, "Popen",
                               return_value="proceso") as popen, \
             mock.patch.object(finalizar_aparte.paths, "orden_de_la_app",
                               return_value=[r"C:\App.exe"]), \
             mock.patch.object(finalizar_aparte.paths, "carpeta_instalacion",
                               return_value=Path(r"C:\Apps")):
            self.assertEqual(finalizar_aparte.lanzar(), "proceso")

        orden, = popen.call_args.args
        opciones = popen.call_args.kwargs
        self.assertEqual(orden, [r"C:\App.exe", "--finalizar-pendientes"])
        self.assertEqual(opciones["stdin"], subprocess.DEVNULL)
        self.assertEqual(opciones["stdout"], subprocess.DEVNULL)
        self.assertEqual(opciones["stderr"], subprocess.DEVNULL)
        self.assertTrue(opciones["close_fds"])
        self.assertEqual(opciones["cwd"], str(Path(r"C:\Apps")))
        self.assertEqual(
            opciones["creationflags"],
            subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP)

    def test_si_falla_el_lanzamiento_lo_registra(self):
        with mock.patch.object(finalizar_aparte.subprocess, "Popen",
                               side_effect=OSError("sin permiso")), \
             mock.patch.object(finalizar_aparte.logger, "warning") as aviso:
            self.assertIsNone(finalizar_aparte.lanzar())

        aviso.assert_called_once()

    def test_lanzar_arranca_sale_cero_y_deja_la_linea(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirigir_rutas(tmp):
                paths.fin_pendiente().write_text("[]", encoding="utf-8")
                orden = [sys.executable, "-B", "-c", _GUION_LANZAR, tmp,
                         str(RAIZ)]
                with mock.patch.object(finalizar_aparte.paths,
                                       "orden_de_la_app",
                                       return_value=orden):
                    proceso = finalizar_aparte.lanzar()
                self.assertIsNotNone(proceso)
                self.assertEqual(proceso.wait(timeout=120), 0)
                registro = Path(tmp, "fin-pendiente.log").read_text(
                    encoding="utf-8")

        self.assertRegex(registro.strip(),
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} ")


class TestRegistrar(unittest.TestCase):

    def test_crea_la_carpeta_del_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "data" / "fin-pendiente.log"
            with mock.patch.object(finalizar_aparte.paths,
                                   "fin_pendiente_log",
                                   return_value=ruta), \
                 mock.patch.object(finalizar_aparte.logger, "warning") as aviso:
                finalizar_aparte._registrar("una prueba")
            self.assertTrue(ruta.is_file())
            self.assertIn("una prueba", ruta.read_text(encoding="utf-8"))
            aviso.assert_not_called()


if __name__ == "__main__":
    unittest.main()
