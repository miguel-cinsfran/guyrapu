# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from guyrapu.core import diagnostico, vigia_interfaz


class _Parada:
    def __init__(self, objetivo):
        self.llamadas = 0
        self.objetivo = objetivo

    def wait(self, _intervalo):
        self.llamadas += 1
        return self.llamadas > self.objetivo


class _RelojParada(_Parada):
    """Avanza el reloj en cada vuelta y lo devuelve como latido."""

    def __init__(self, paso, objetivo):
        super().__init__(objetivo)
        self.momento = 0.0
        self.paso = paso

    def wait(self, _intervalo):
        self.llamadas += 1
        if self.llamadas > self.objetivo:
            return True
        self.momento += self.paso
        return False


class VigiaInterfazTest(unittest.TestCase):
    def test_vigilante_informa_bloqueo_sobre_umbral(self):
        registrar, activo = vigia_interfaz.decidir_bloqueo_interfaz(10.0, 10.6, False)
        texto = vigia_interfaz.componer_bloqueo_interfaz(600, "pila de interfaz")
        self.assertTrue(registrar)
        self.assertTrue(activo)
        self.assertIn("bloqueada_ms=600", texto)

    def test_vigilante_no_informa_demora_normal(self):
        self.assertEqual(
            vigia_interfaz.decidir_bloqueo_interfaz(10.0, 10.4, False), (False, False))

    def test_latido_sin_cambio_no_esta_vivo(self):
        self.assertFalse(vigia_interfaz.esta_vivo_el_latido(1.0, 1.0, False))

    def test_latido_con_cambio_esta_vivo(self):
        self.assertTrue(vigia_interfaz.esta_vivo_el_latido(1.0, 1.1, False))

    def test_latido_vivo_no_muere_si_deja_de_cambiar(self):
        self.assertTrue(vigia_interfaz.esta_vivo_el_latido(1.0, 1.0, True))

    def test_vigilante_ignora_latido_que_nunca_cambia(self):
        with patch.object(vigia_interfaz.time, "monotonic", side_effect=[1.0, 2.0]), \
                patch.object(diagnostico, "archivo_fallos", return_value=None), \
                patch.object(vigia_interfaz.logger, "warning") as registrar:
            vigia_interfaz.vigilar_hilo_interfaz(lambda: 0.0, _Parada(2))
        registrar.assert_not_called()

    def test_vigilante_informa_latido_atrasado_despues_de_moverse(self):
        marcas = iter((0.0, 0.1))
        with patch.object(vigia_interfaz.time, "monotonic", side_effect=[1.0, 1.1]), \
                patch.object(diagnostico, "archivo_fallos", return_value=None), \
                patch.object(vigia_interfaz.sys, "_current_frames", return_value={}), \
                patch.object(vigia_interfaz.logger, "warning") as registrar:
            vigia_interfaz.vigilar_hilo_interfaz(lambda: next(marcas), _Parada(2))
        registrar.assert_called_once()

    def test_vigilante_registra_un_solo_bloqueo_largo(self):
        self.assertEqual(
            vigia_interfaz.decidir_bloqueo_interfaz(10.0, 11.0, False), (True, True))
        self.assertEqual(
            vigia_interfaz.decidir_bloqueo_interfaz(10.0, 11.5, True), (False, True))

    def test_pila_del_vigilante_toma_el_marco_del_hilo_principal(self):
        principal = object()
        vigilante = object()
        with patch.object(
                vigia_interfaz.traceback, "format_stack",
                side_effect=lambda marco: ["GUI"] if marco is principal else ["VIGILANTE"]):
            pila = vigia_interfaz.pila_hilo_interfaz({101: principal, 202: vigilante}, 101)
        self.assertEqual(pila, "GUI")

    def test_pila_no_usa_el_marco_del_vigilante(self):
        with patch.object(vigia_interfaz.traceback, "format_stack", return_value=["VIGILANTE"]):
            pila = vigia_interfaz.pila_hilo_interfaz({202: object()}, 101)
        self.assertEqual(pila, "no disponible")

    def test_vigilante_no_repite_un_bloqueo_largo(self):
        with patch.object(vigia_interfaz.time, "monotonic", side_effect=[1.0, 1.1]), \
                patch.object(diagnostico, "archivo_fallos", return_value=None), \
                patch.object(vigia_interfaz.sys, "_current_frames", return_value={}), \
                patch.object(vigia_interfaz.logger, "warning") as registrar:
            marcas = iter((0.0, 0.1))
            vigia_interfaz.vigilar_hilo_interfaz(lambda: next(marcas), _Parada(2))
        registrar.assert_called_once()

    def test_vigilante_retrata_el_hilo_principal_desde_otro_hilo(self):
        principal = threading.main_thread().ident
        identificadores = []

        def recordar(_marcos, identificador):
            identificadores.append(identificador)
            return "pila"

        marcas = iter((0.0, 0.1))
        with patch.object(vigia_interfaz.time, "monotonic", return_value=1.0), \
                patch.object(diagnostico, "archivo_fallos", return_value=None), \
                patch.object(vigia_interfaz.sys, "_current_frames", return_value={}), \
                patch.object(vigia_interfaz, "pila_hilo_interfaz", side_effect=recordar), \
                patch.object(vigia_interfaz.logger, "warning"):
            hilo = threading.Thread(
                target=vigia_interfaz.vigilar_hilo_interfaz,
                args=(lambda: next(marcas), _Parada(2)))
            hilo.start()
            hilo.join()

        self.assertEqual(identificadores, [principal])
        self.assertNotEqual(principal, hilo.ident)


class VigiaDelInterpreteTest(unittest.TestCase):
    def test_latido_al_dia_rearma_como_mucho_una_vez_por_segundo(self):
        reloj = _RelojParada(paso=0.5, objetivo=4)
        archivo = object()
        with patch.object(vigia_interfaz.time, "monotonic",
                          side_effect=lambda: reloj.momento), \
                patch.object(diagnostico, "archivo_fallos", return_value=archivo), \
                patch.object(vigia_interfaz, "faulthandler") as falso:
            vigia_interfaz.vigilar_hilo_interfaz(
                lambda: reloj.momento, reloj, segundos=30)

        self.assertEqual(falso.dump_traceback_later.call_count, 2)
        for llamada in falso.dump_traceback_later.call_args_list:
            self.assertEqual(llamada.kwargs["file"], archivo)
            self.assertFalse(llamada.kwargs["repeat"])
            self.assertFalse(llamada.kwargs["exit"])

    def test_la_parada_cancela_el_vigia(self):
        with patch.object(vigia_interfaz.time, "monotonic", return_value=0.0), \
                patch.object(diagnostico, "archivo_fallos", return_value=object()), \
                patch.object(vigia_interfaz, "faulthandler") as falso:
            vigia_interfaz.vigilar_hilo_interfaz(lambda: 0.0, _Parada(1))

        falso.dump_traceback_later.assert_called_once()
        falso.cancel_dump_traceback_later.assert_called_once_with()

    def test_sin_archivo_de_fallos_no_se_arma(self):
        with patch.object(vigia_interfaz.time, "monotonic", return_value=0.0), \
                patch.object(diagnostico, "archivo_fallos", return_value=None), \
                patch.object(vigia_interfaz, "faulthandler") as falso:
            vigia_interfaz.vigilar_hilo_interfaz(lambda: 0.0, _Parada(2))

        falso.dump_traceback_later.assert_not_called()

    def test_el_faulthandler_real_volca_la_cabecera_y_la_pila(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = str(Path(tmp) / "fallos.log")
            guion = (
                "import sys, threading, time\n"
                "from guyrapu.core import diagnostico, vigia_interfaz\n"
                "ruta = sys.argv[1]\n"
                "diagnostico.instalar_capturadores(ruta, version='prueba')\n"
                "parada = threading.Event()\n"
                "marca = time.monotonic()\n"
                "hilo = threading.Thread(\n"
                "    target=vigia_interfaz.vigilar_hilo_interfaz,\n"
                "    args=(lambda: marca, parada),\n"
                "    kwargs={'segundos': 1})\n"
                "hilo.start()\n"
                "def sleep(segundos):\n"
                "    time.sleep(segundos)\n"
                "sleep(3.0)\n"
                "parada.set()\n"
                "hilo.join(timeout=5)\n"
            )
            proceso = subprocess.run(
                [sys.executable, "-c", guion, ruta],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(
                proceso.returncode, 0,
                f"el subproceso falló: returncode={proceso.returncode} "
                f"stderr={proceso.stderr[-2000:]}")
            contenido = Path(ruta).read_text(encoding="utf-8", errors="replace")

        self.assertIn("Timeout (0:00:01)!", contenido)
        self.assertIn("in sleep", contenido)


if __name__ == "__main__":
    unittest.main()
