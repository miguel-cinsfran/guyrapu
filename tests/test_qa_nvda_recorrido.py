# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del recorrido de una ventana y del pid que escribe al abrirse.

La conducción usa un cliente de mentira que devuelve paradas y habla fijas.
La prueba del pid lanza un proceso mínimo de verdad; ninguna abre ventanas ni
toca NVDA.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qa.nvda import recorrido, transcripcion


class ClienteFalso:
    """Una ventana cíclica de nombres conocidos, sin NVDA de por medio."""

    def __init__(self, nombres, pid=7, ajeno=False):
        self.nombres = list(nombres)
        self.pos = 0
        self.pid = pid
        self.ajeno = ajeno
        self.pasos = []
        self.esperas = []

    def marca(self):
        return len(self.pasos)

    def esperar_frase(self, frase, desde, plazo_s=5.0):
        self.esperas.append((frase, desde, plazo_s, len(self.pasos)))
        return {"oida": True,
                "eventos": [{"tipo": "habla", "texto": frase}]}

    def _foco(self):
        nombre = self.nombres[self.pos]
        return {"nombre": nombre, "rol_nombre": "PUSH_BUTTON",
                "hwnd": self.pos + 1, "pid": self.pid, "estados": [],
                "atajo": "", "texto": nombre,
                "padre": "Lista de categorías"}

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


class ClienteConFoco:
    """Un foco fijo, para probar la espera del primer control."""

    def __init__(self, foco):
        self.foco = foco

    def foco_completo(self):
        return {"ok": True, "foco": self.foco}


class ClienteConFila(ClienteFalso):
    """La primera fila de la lista toma el foco al abrir la ventana."""

    def _foco(self):
        return {"nombre": "Phonon, español", "rol_nombre": "LISTITEM",
                "padre": "Paquetes de voces", "hwnd": self.pos + 1,
                "pid": self.pid, "estados": [], "atajo": "",
                "texto": "Phonon, español"}


class ClienteFilaDistinta:
    """Tab vuelve a la lista en otra fila, con otro hwnd y otro texto."""

    def __init__(self):
        self.focos = [
            {"nombre": "Phonon, español", "rol_nombre": "LISTITEM",
             "padre": "Paquetes de voces", "hwnd": 1, "pid": 7,
             "estados": [], "atajo": ""},
            {"nombre": "Instalar", "rol_nombre": "BUTTON",
             "hwnd": 2, "pid": 7, "estados": [], "atajo": ""},
            {"nombre": "Otra fila, 3 voces", "rol_nombre": "LISTITEM",
             "padre": "Paquetes de voces", "hwnd": 9, "pid": 7,
             "estados": [], "atajo": ""},
        ]
        self.pos = 0

    def foco_completo(self):
        return {"ok": True, "foco": self.focos[self.pos],
                "primer_plano": {"pid": 7, "nombre": "Ventana del carril"}}

    def paso(self, tecla, silencio_ms=400, tope_ms=10000):
        if tecla == "tab":
            self.pos = (self.pos + 1) % len(self.focos)
        elif tecla == "shift+tab":
            self.pos = (self.pos - 1) % len(self.focos)
        return {"tecla": tecla, "agotado": False, "hora": 1.0,
                "eventos": [], "foco": self.focos[self.pos]}


class ClienteConMismoNombre:
    """Dos controles iguales: solo el hwnd distingue al primero."""

    def __init__(self):
        self.focos = [
            {"nombre": "Uno", "rol_nombre": "PUSH_BUTTON", "hwnd": 1,
             "pid": 7, "estados": [], "atajo": ""},
            {"nombre": "Uno", "rol_nombre": "PUSH_BUTTON", "hwnd": 2,
             "pid": 7, "estados": [], "atajo": ""},
        ]
        self.pos = 0

    def foco_completo(self):
        return {"ok": True, "foco": self.focos[self.pos],
                "primer_plano": {"pid": 7, "nombre": "Ventana del carril"}}

    def paso(self, tecla, silencio_ms=400, tope_ms=10000):
        if tecla == "tab":
            self.pos = (self.pos + 1) % len(self.focos)
        elif tecla == "shift+tab":
            self.pos = (self.pos - 1) % len(self.focos)
        return {"tecla": tecla, "agotado": False, "hora": 1.0,
                "eventos": [], "foco": self.focos[self.pos]}


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

    def test_la_espera_toma_la_marca_antes_del_gesto(self):
        nombres = ["Uno", "Dos"]
        cliente = ClienteFalso(nombres)
        datos = recorrido.conducir(cliente, ventana(nombres, [{
            "control": "Dos", "gesto": "space", "espera": "listo"}]))
        frase, desde, plazo, al_esperar = cliente.esperas[0]
        self.assertEqual(frase, "listo")
        self.assertEqual(plazo, 5.0)
        self.assertLess(desde, al_esperar)
        accion = [p for p in datos["pasos"] if p["fase"] == "accion"][0]
        self.assertEqual(accion["espera"], "listo")
        self.assertTrue(accion["oida"])
        self.assertEqual(accion["espera_dicho"], "listo")

    def test_sin_espera_no_llama_a_esperar_frase(self):
        nombres = ["Uno"]
        cliente = ClienteFalso(nombres)
        recorrido.conducir(cliente, ventana(
            nombres, [{"control": "Uno", "gesto": "space"}]))
        self.assertEqual(cliente.esperas, [])

    def test_los_sonidos_nuevos_se_ponen_en_cada_paso(self):
        nombres = ["Uno", "Dos"]
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "sonidos.txt"
            ruta.write_text("anterior\n", encoding="utf-8")
            cliente = ClienteFalso(nombres)
            paso_original = cliente.paso

            def con_sonido(tecla, silencio_ms=400, tope_ms=10000):
                with open(ruta, "a", encoding="utf-8") as archivo:
                    archivo.write("listo\n")
                return paso_original(tecla, silencio_ms, tope_ms)

            cliente.paso = con_sonido
            with mock.patch.dict(os.environ,
                                 {recorrido.VAR_SONIDOS: str(ruta)}):
                datos = recorrido.conducir(cliente, ventana(nombres))
        self.assertEqual(datos["pasos"][0]["sonidos"], ["listo"])
        self.assertTrue(all("anterior" not in p["sonidos"]
                            for p in datos["pasos"]))


class ClienteDePaginas:
    """La ventana Interacción: el contenido, la lista de páginas y sus flechas."""

    def __init__(self, paginas, primeras, actual, pid=7):
        self.paginas = list(paginas)
        self.primeras = dict(primeras)
        self.indice = self.paginas.index(actual)
        self.en_lista = False
        self.entro = False
        self.pid = pid
        self.pasos = []

    def _foco(self):
        if self.en_lista:
            nombre = self.paginas[self.indice]
        else:
            nombre = self.primeras[self.paginas[self.indice]]
        return {"nombre": nombre, "rol_nombre": "LISTITEM", "pid": self.pid,
                "estados": [], "atajo": "", "texto": nombre}

    def foco_completo(self):
        return {"ok": True, "foco": self._foco(),
                "primer_plano": {"pid": self.pid, "nombre": "Interacción"}}

    def paso(self, tecla, silencio_ms=400, tope_ms=10000):
        self.pasos.append(tecla)
        if tecla == "shift+tab" and not self.entro:
            self.en_lista = True
        elif tecla == "downArrow" and self.en_lista:
            self.indice = min(self.indice + 1, len(self.paginas) - 1)
        elif tecla == "upArrow" and self.en_lista:
            self.indice = max(self.indice - 1, 0)
        elif tecla == "tab" and self.en_lista:
            self.en_lista = False
            self.entro = True
        nombre = self._foco()["nombre"]
        return {
            "tecla": tecla,
            "agotado": False,
            "hora": 1.0,
            "eventos": [{"tipo": "habla", "texto": nombre,
                         "partes": [nombre], "hora": 1.05}],
            "foco": self._foco(),
        }


class TestPagina(unittest.TestCase):

    PAGINAS = ["Mensajes automáticos", "Comandos", "Encuestas", "Medios",
               "Estilos", "Palabras bloqueadas"]

    def _cliente(self, actual):
        return ClienteDePaginas(
            self.PAGINAS,
            {pagina: f"primero de {pagina}" for pagina in self.PAGINAS},
            actual)

    def test_la_pagina_se_elige_con_flechas_y_se_entra_con_tab(self):
        for actual, destino, flechas in (
                ("Comandos", "Palabras bloqueadas", ["downArrow"] * 4),
                ("Medios", "Encuestas", ["upArrow"])):
            with self.subTest(destino=destino):
                cliente = self._cliente(actual)
                datos = recorrido.conducir(cliente, {
                    "nombre": "pagina",
                    "pid": 7,
                    "primero": f"primero de {destino}",
                    "pagina": destino,
                    "paginas": self.PAGINAS,
                }, tope=10)
                pagina = [paso["tecla"] for paso in datos["pasos"]
                          if paso["fase"] == "pagina"]
                self.assertEqual(pagina, ["shift+tab"] + flechas + ["tab"])
                self.assertEqual(datos["primero"]["nombre"],
                                 f"primero de {destino}")

    def test_una_pagina_que_no_esta_termina_con_instrumento_roto(self):
        cliente = self._cliente("Comandos")
        with self.assertRaises(recorrido.InstrumentoRoto) as capturado:
            recorrido.conducir(cliente, {
                "nombre": "palabras",
                "pid": 7,
                "primero": "primero de Palabras bloqueadas",
                "pagina": "Palabras bloqueadas",
                "paginas": self.PAGINAS[:4],
            }, tope=10)
        self.assertIn("Palabras bloqueadas", str(capturado.exception))
        self.assertEqual(cliente.pasos, [])


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
        with self.assertRaises(recorrido.InstrumentoRoto) as capturado:
            recorrido.conducir(cliente, ventana(["Esperado"]),
                               tope_foco_s=0.01)
        mensaje = str(capturado.exception)
        self.assertIn("nombre='Otro'", mensaje)
        self.assertIn("rol=None", mensaje)
        self.assertIn("rol_nombre='PUSH_BUTTON'", mensaje)
        self.assertIn("padre='Lista de categorías'", mensaje)
        self.assertEqual(cliente.pasos, [])

    def _foco(self, nombre="Phonon, español", rol="LISTITEM",
              padre="Paquetes de voces"):
        return {"nombre": nombre, "rol_nombre": rol, "padre": padre}

    def _esperar(self, foco):
        return recorrido._esperar_foco(
            ClienteConFoco(foco), "Paquetes de voces", 0.01,
            lambda _segundos: None, "Paquetes de voces")

    def test_acepta_una_fila_de_la_lista_declarada(self):
        foco = self._foco()
        self.assertIs(self._esperar(foco), foco)

    def test_conducir_da_por_bueno_la_fila_de_la_lista(self):
        datos = recorrido.conducir(
            ClienteConFila(["Phonon, español"]),
            {"nombre": "voces", "pid": 7, "primero": "Paquetes de voces",
             "primero_lista": "Paquetes de voces"}, tope_foco_s=0.01)
        self.assertEqual(datos["primero"]["rol_nombre"], "LISTITEM")
        self.assertEqual(datos["primero"]["nombre"], "Phonon, español")

    def test_rechaza_una_fila_de_otra_lista(self):
        with self.assertRaises(recorrido.InstrumentoRoto) as capturado:
            self._esperar(self._foco(padre="Otra lista"))
        self.assertIn("Otra lista", str(capturado.exception))

    def test_rechaza_un_foco_en_otro_control(self):
        for foco in (self._foco(rol="PUSH_BUTTON"),
                     self._foco(nombre="Instalar", rol="PUSH_BUTTON")):
            with self.subTest(foco=foco), self.assertRaises(
                    recorrido.InstrumentoRoto):
                self._esperar(foco)


class TestCierreDelCiclo(unittest.TestCase):

    def test_sin_lista_no_cierra_en_otro_control_del_mismo_nombre(self):
        datos = recorrido.conducir(
            ClienteConMismoNombre(),
            {"nombre": "prueba", "pid": 7, "primero": "Uno"}, tope=4,
            tope_foco_s=0.01)
        ida = [p for p in datos["pasos"] if p["fase"] == "ida"]
        self.assertEqual(len(ida), 2)


class TestVueltaALaLista(unittest.TestCase):

    def test_conducir_cierra_la_ida_y_la_vuelta_en_otra_fila(self):
        datos = recorrido.conducir(
            ClienteFilaDistinta(),
            {"nombre": "voces", "pid": 7, "primero": "Paquetes de voces",
             "primero_lista": "Paquetes de voces"}, tope=6,
            tope_foco_s=0.01)
        ida = [p for p in datos["pasos"] if p["fase"] == "ida"]
        vuelta = [p for p in datos["pasos"] if p["fase"] == "vuelta"]
        self.assertEqual(len(ida), 2)
        self.assertEqual(len(vuelta), 2)
        self.assertEqual(datos["primero_lista"], "Paquetes de voces")


class TestPadreEnTranscripcion(unittest.TestCase):

    def test_el_nombre_del_padre_no_cambia_la_transcripcion(self):
        datos = {"pasos": [{"tecla": "tab", "fase": "ida",
                            "habla": [{"texto": "Phonon botón"}],
                            "foco": {"nombre": "Phonon",
                                     "rol_nombre": "LISTITEM",
                                     "estados": []}}]}
        sin_padre = transcripcion.texto(datos)
        datos["pasos"][0]["foco"]["padre"] = "Paquetes de voces"
        con_padre = transcripcion.texto(datos)
        self.assertEqual(con_padre, sin_padre)
        self.assertNotIn("Paquetes de voces", con_padre)


class TestPidDeLaVentana(unittest.TestCase):

    GUION = """import os
import pathlib
import sys
import time

ruta = pathlib.Path(sys.argv[sys.argv.index("--pid-file") + 1])
ruta.write_text(str(os.getpid()), encoding="utf-8")
segunda = os.environ.get("GUYRAPU_PID_ESCRITOR")
if segunda:
    pathlib.Path(segunda).write_text(str(os.getpid()), encoding="utf-8")
tercera = os.environ.get("GUYRAPU_PID_PADRE")
if tercera:
    pathlib.Path(tercera).write_text(str(os.getppid()), encoding="utf-8")
time.sleep(0.5)
"""

    def test_recorrer_usa_el_pid_que_escribio_la_ventana(self):
        with tempfile.TemporaryDirectory() as base:
            carpeta = Path(base)
            guion = carpeta / "escribe_pid.py"
            guion.write_text(self.GUION, encoding="utf-8")
            escritor = carpeta / "escritor.pid"
            padre = carpeta / "padre.pid"
            datos = {"nombre": "prueba",
                     "comando": [sys.executable, str(guion)],
                     "primero": "Uno", "acciones": []}
            visto = {}

            def conducir_falso(cliente, ventana, *args, **kwargs):
                visto["pid"] = ventana["pid"]
                return {"ventana": "prueba", "pid": ventana["pid"],
                        "primero": {}, "pasos": []}

            with (
                mock.patch.dict(os.environ, {
                    "GUYRAPU_PID_ESCRITOR": str(escritor),
                    "GUYRAPU_PID_PADRE": str(padre)}),
                mock.patch.object(recorrido, "conducir",
                                  side_effect=conducir_falso),
                mock.patch.object(recorrido, "cerrar"),
            ):
                recorrido.recorrer(datos, None, tope_pid_s=2.0)

            pid_escritor = int(escritor.read_text(encoding="utf-8"))
            pid_padre = int(padre.read_text(encoding="utf-8"))
            self.assertEqual(visto["pid"], pid_escritor)
            if pid_escritor == pid_padre:
                print("El venv no interpuso un lanzador: el pid es el del "
                      "proceso lanzado.")

    def test_si_no_aparece_el_pid_es_instrumento_roto(self):
        with tempfile.TemporaryDirectory() as base:
            guion = Path(base) / "no_escribe.py"
            guion.write_text("import time\ntime.sleep(5)\n",
                             encoding="utf-8")
            datos = {"nombre": "prueba",
                     "comando": [sys.executable, str(guion)],
                     "primero": "Uno", "acciones": []}
            with self.assertRaises(recorrido.InstrumentoRoto):
                recorrido.recorrer(datos, None, tope_pid_s=0.2)


if __name__ == "__main__":
    unittest.main()
