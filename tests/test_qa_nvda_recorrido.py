# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del recorrido de una ventana con un cliente de mentira.

No abren ventanas ni tocan NVDA: el cliente doble devuelve paradas y habla
fijas, y se comprueba cómo se conduce la ida, la vuelta y las acciones.
"""

import unittest

from qa.nvda import recorrido


class ClienteFalso:
    """Una ventana cíclica de nombres conocidos, sin NVDA de por medio."""

    def __init__(self, nombres, pid=7, ajeno=False):
        self.nombres = list(nombres)
        self.pos = 0
        self.pid = pid
        self.ajeno = ajeno
        self.pasos = []

    def _foco(self):
        nombre = self.nombres[self.pos]
        return {"nombre": nombre, "rol_nombre": "PUSH_BUTTON",
                "hwnd": self.pos + 1, "pid": self.pid, "estados": [],
                "atajo": "", "texto": nombre}

    def foco_completo(self):
        plano = {
            "pid": 99 if self.ajeno else self.pid,
            "nombre": "Ventana ajena" if self.ajeno else "Ventana del carril",
        }
        return {"ok": True, "foco": self._foco(), "primer_plano": plano}

    def paso(self, tecla, silencio_ms=400, tope_ms=10000):
        self.pasos.append(tecla)
        if tecla == "tab":
            self.pos = (self.pos + 1) % len(self.nombres)
        elif tecla == "shift+tab":
            self.pos = (self.pos - 1) % len(self.nombres)
        texto = (self.nombres[self.pos]
                 if tecla in ("tab", "shift+tab") else "listo")
        return {
            "tecla": tecla,
            "agotado": False,
            "hora": 1.0,
            "eventos": [{"tipo": "habla", "texto": texto,
                         "partes": [texto], "hora": 1.05}],
            "foco": self._foco(),
        }


class ClienteSinVuelta(ClienteFalso):
    """Cada Tab deja un control nuevo: nunca vuelve a la primera parada."""

    def _foco(self):
        return {"nombre": f"Control {self.pos}", "rol_nombre": "PUSH_BUTTON",
                "hwnd": self.pos + 1, "pid": self.pid, "estados": [],
                "atajo": "", "texto": f"Control {self.pos}"}

    def paso(self, tecla, silencio_ms=400, tope_ms=10000):
        self.pos += 1
        return {
            "tecla": tecla,
            "agotado": False,
            "hora": 1.0,
            "eventos": [],
            "foco": self._foco(),
        }


def ventana(nombres, acciones=()):
    return {"nombre": "prueba", "titulo": "Prueba", "pid": 7,
            "primero": nombres[0], "acciones": list(acciones)}


def _nombres(pasos):
    return [paso["foco"]["nombre"] for paso in pasos]


class TestIda(unittest.TestCase):

    def test_la_ida_vuelve_a_la_primera_parada(self):
        cliente = ClienteFalso(["Uno", "Dos", "Tres"])
        datos = recorrido.conducir(cliente, ventana(["Uno", "Dos", "Tres"]))
        ida = [p for p in datos["pasos"] if p["fase"] == "ida"]
        self.assertEqual(_nombres(ida), ["Dos", "Tres", "Uno"])
        self.assertEqual(datos["primero"]["nombre"], "Uno")

    def test_la_ida_se_corta_en_el_tope_si_no_vuelve(self):
        cliente = ClienteSinVuelta(["Control 0"])
        datos = recorrido.conducir(
            cliente, ventana(["Control 0"]), tope=3)
        ida = [p for p in datos["pasos"] if p["fase"] == "ida"]
        self.assertEqual(len(ida), 3)
        self.assertNotEqual(_nombres(ida)[-1], "Control 0")


class TestVuelta(unittest.TestCase):

    def test_la_vuelta_da_las_mismas_paradas_al_reves(self):
        nombres = ["Uno", "Dos", "Tres"]
        datos = recorrido.conducir(ClienteFalso(nombres), ventana(nombres))
        vuelta = [p for p in datos["pasos"] if p["fase"] == "vuelta"]
        self.assertEqual(_nombres(vuelta), ["Tres", "Dos", "Uno"])


class TestAccion(unittest.TestCase):

    def test_llega_con_tab_al_control_y_manda_el_gesto(self):
        nombres = ["Uno", "Dos", "Tres"]
        datos = recorrido.conducir(
            ClienteFalso(nombres), ventana(
                nombres, [{"control": "Dos", "gesto": "space"}]))
        accion = [p for p in datos["pasos"] if p["fase"] == "accion"]
        self.assertEqual(len(accion), 1)
        self.assertEqual(accion[0]["tecla"], "space")
        self.assertEqual(accion[0]["foco"]["nombre"], "Dos")
        self.assertEqual(accion[0]["habla"][0]["texto"], "listo")

    def test_guarda_los_milisegundos_hasta_la_ultima_habla(self):
        nombres = ["Uno", "Dos"]
        datos = recorrido.conducir(ClienteFalso(nombres), ventana(nombres))
        self.assertEqual(datos["pasos"][0]["ms_habla"], 50)


class TestPrimerPlano(unittest.TestCase):

    def test_un_primer_plano_ajeno_corta_con_instrumento_roto(self):
        cliente = ClienteFalso(["Uno"], ajeno=True)
        with self.assertRaises(recorrido.InstrumentoRoto) as capturado:
            recorrido.conducir(cliente, ventana(["Uno"]))
        self.assertIn("Ventana ajena", str(capturado.exception))
        self.assertEqual(cliente.pasos, [])

    def test_el_primer_plano_de_la_ventana_deja_seguir(self):
        datos = recorrido.conducir(
            ClienteFalso(["Uno"]), ventana(["Uno"]))
        self.assertEqual(len(datos["pasos"]), 2)


class TestEsperaDeFoco(unittest.TestCase):

    def test_si_el_primer_control_no_toma_el_foco_es_instrumento_roto(self):
        cliente = ClienteFalso(["Otro"])
        with self.assertRaises(recorrido.InstrumentoRoto):
            recorrido.conducir(cliente, ventana(["Esperado"]),
                               tope_foco_s=0.01)
        self.assertEqual(cliente.pasos, [])


if __name__ == "__main__":
    unittest.main()
