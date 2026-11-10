# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cadena de espera nativa de un hilo de Windows, sin dobles en la parte real."""

import ctypes
import os
import subprocess
import sys
import threading
import time
import unittest
import uuid
from ctypes import wintypes
from unittest.mock import patch

from guyrapu.core import cadena_espera


_SYNCHRONIZE = 0x00100000
_WAIT_ABANDONED = 0x80
_ESPERA_INFINITA = 0xFFFFFFFF


class ComponerCadenaTest(unittest.TestCase):
    def test_compone_una_linea_por_nodo_con_los_datos_del_hilo(self):
        nodos = [
            {"tipo": "WctThreadType", "estado": "WctStatusBlocked",
             "proceso": 1234, "ejecutable": "guyrapu.exe", "hilo": 5678,
             "ms_espera": 900},
            {"tipo": "WctMutexType", "estado": "WctStatusOwned"},
        ]
        lineas = cadena_espera.componer_cadena_espera(nodos).splitlines()
        self.assertEqual(len(lineas), 2)
        self.assertIn("nodo 0", lineas[0])
        self.assertIn("WctThreadType", lineas[0])
        self.assertIn("estado=WctStatusBlocked", lineas[0])
        self.assertIn("proceso=1234", lineas[0])
        self.assertIn("ejecutable=guyrapu.exe", lineas[0])
        self.assertIn("hilo=5678", lineas[0])
        self.assertIn("ms_espera=900", lineas[0])
        self.assertIn("WctMutexType", lineas[1])
        self.assertIn("estado=WctStatusOwned", lineas[1])

    def test_sin_nodos_devuelve_el_texto_de_fallo(self):
        self.assertEqual(cadena_espera.componer_cadena_espera([]),
                         cadena_espera.texto_sin_cadena())
        self.assertIn("no se pudo leer", cadena_espera.texto_sin_cadena().lower())

    def test_si_la_lectura_falla_devuelve_el_texto_fijo_sin_lanzar(self):
        with patch.object(cadena_espera, "leer_cadena_espera",
                          side_effect=OSError("fallo simulado")):
            texto = cadena_espera.cadena_espera_de_hilo(1234)
        self.assertEqual(texto, cadena_espera.texto_sin_cadena())


@unittest.skipUnless(os.name == "nt", "solo Windows")
class CadenaEsperaRealTest(unittest.TestCase):
    def test_la_cadena_de_un_hilo_que_espera_un_mutex_nombra_al_duenio(self):
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        listo = threading.Event()
        liberar = threading.Event()
        esperando = threading.Event()
        datos = {}

        def tomar():
            mutex = kernel32.CreateMutexW(None, True, None)
            datos["mutex"] = mutex
            datos["hilo_duenio"] = threading.get_native_id()
            listo.set()
            liberar.wait(10)
            kernel32.ReleaseMutex(mutex)
            kernel32.CloseHandle(mutex)

        def esperar():
            listo.wait(10)
            datos["hilo_espera"] = threading.get_native_id()
            esperando.set()
            kernel32.WaitForSingleObject(datos["mutex"], 0xFFFFFFFF)

        duenio = threading.Thread(target=tomar)
        esperador = threading.Thread(target=esperar)
        duenio.start()
        esperador.start()
        nodos = []
        try:
            self.assertTrue(esperando.wait(5))
            limite = time.monotonic() + 5
            while time.monotonic() < limite:
                nodos = cadena_espera.leer_cadena_espera(datos["hilo_espera"])
                if any(n["tipo"] == "WctMutexType" for n in nodos):
                    break
                time.sleep(0.05)
        finally:
            liberar.set()
            duenio.join(timeout=5)
            esperador.join(timeout=5)

        self.assertTrue(
            any(n["tipo"] == "WctMutexType" for n in nodos), nodos)
        hilos = [n for n in nodos if n["tipo"] == "WctThreadType"]
        self.assertTrue(
            any(n.get("hilo") == datos["hilo_duenio"] for n in hilos), nodos)
        self.assertTrue(
            all(n.get("proceso") == os.getpid() for n in hilos), nodos)

    def test_la_cadena_de_un_hilo_que_espera_un_mutex_de_otro_proceso_trae_su_pid(self):
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenMutexW.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.OpenMutexW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        nombre = f"Local\\GuyrapuPruebaCadena-{os.getpid()}-{uuid.uuid4().hex}"
        guion = (
            "import ctypes, os, sys, time\n"
            "from ctypes import wintypes\n"
            "kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)\n"
            "kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]\n"
            "kernel32.CreateMutexW.restype = wintypes.HANDLE\n"
            "mutex = kernel32.CreateMutexW(None, True, sys.argv[1])\n"
            "sys.stdout.write('LISTO %s\\n' % os.getpid())\n"
            "sys.stdout.flush()\n"
            "time.sleep(120)\n"
        )
        proceso = subprocess.Popen(
            [sys.executable, "-c", guion, nombre],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        linea = []
        lector = threading.Thread(
            target=lambda: linea.append(proceso.stdout.readline()),
            daemon=True)
        lector.start()
        lector.join(10)
        try:
            self.assertTrue(
                linea and linea[0].startswith("LISTO"),
                f"el hijo no avisó que tomó el mutex: {linea!r}")
            pid_hijo = int(linea[0].split()[1])

            listo = threading.Event()
            hilo_espera = []

            def esperar():
                handle = kernel32.OpenMutexW(_SYNCHRONIZE, False, nombre)
                if not handle:
                    listo.set()
                    return
                hilo_espera.append(threading.get_native_id())
                listo.set()
                codigo = kernel32.WaitForSingleObject(
                    handle, _ESPERA_INFINITA)
                if codigo in (0, _WAIT_ABANDONED):
                    kernel32.ReleaseMutex(handle)
                kernel32.CloseHandle(handle)

            hilo = threading.Thread(target=esperar)
            hilo.start()
            try:
                self.assertTrue(listo.wait(5))
                self.assertTrue(hilo_espera, "no se pudo abrir el mutex del hijo")
                nodos = []
                limite = time.monotonic() + 5
                while time.monotonic() < limite:
                    nodos = cadena_espera.leer_cadena_espera(hilo_espera[0])
                    if any(n.get("tipo") == "WctThreadType"
                           and n.get("proceso") == pid_hijo for n in nodos):
                        break
                    time.sleep(0.05)
                self.assertTrue(
                    any(n.get("tipo") == "WctThreadType"
                        and n.get("proceso") == pid_hijo for n in nodos), nodos)
            finally:
                proceso.kill()
                proceso.wait(5)
                hilo.join(5)
        finally:
            if proceso.poll() is None:
                proceso.kill()
                proceso.wait(5)
            lector.join(5)
            proceso.stdout.close()
            proceso.stderr.close()


if __name__ == "__main__":
    unittest.main()
