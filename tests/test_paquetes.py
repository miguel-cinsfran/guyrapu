# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los paquetes .zip que se comparten entre personas.

Los paquetes se arman con zipfile en una carpeta temporal: son archivos
reales, no dobles.
"""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

from guyrapu.interaction import medios, paquetes

from tests.letras_acceso import ingles


class PaquetesTest(unittest.TestCase):

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.base = Path(self._temporal.name)
        self.carpeta = self.base / "trabajo"
        self.carpeta.mkdir()
        self.ruta = self.carpeta / "paquete.zip"

    def tearDown(self):
        self._temporal.cleanup()

    def _archivo(self, nombre, contenido=b"x"):
        ruta = self.carpeta / nombre
        ruta.write_bytes(contenido)
        return ruta

    def _manifiesto(self, tipo="estilos", formato=1):
        return json.dumps({
            "formato": formato,
            "tipo": tipo,
            "cantidad": 0,
            "app": "Guyrapu",
        })

    def _paquete(self, elementos=None, archivos=(), tipo="estilos",
                 formato=1, compresion=zipfile.ZIP_STORED):
        elementos = [] if elementos is None else elementos
        with zipfile.ZipFile(self.ruta, "w", compresion) as archivo:
            archivo.writestr("manifiesto.json",
                             self._manifiesto(tipo, formato))
            archivo.writestr("datos.json", json.dumps(elementos))
            for nombre, contenido in archivos:
                archivo.writestr("archivos/" + nombre, contenido)

    def _paquete_con(self, entrada):
        with zipfile.ZipFile(self.ruta, "w") as archivo:
            archivo.writestr("manifiesto.json", self._manifiesto())
            archivo.writestr("datos.json", "[]")
            if isinstance(entrada, zipfile.ZipInfo):
                archivo.writestr(entrada, b"x")
            else:
                archivo.writestr(entrada, b"x")

    def _rechazo(self, ruta=None, tipo="estilos", extensiones=("gif",),
                 tope_mb=50):
        with self.assertRaises(paquetes.PaqueteRechazado) as contexto:
            paquetes.leer(ruta or self.ruta, tipo, extensiones=extensiones,
                          tope_mb=tope_mb)
        return str(contexto.exception)

    def test_exportar_escribe_manifiesto_datos_y_archivos(self):
        primera = self._archivo("a.gif", b"AAA")
        segunda = self._archivo("b.png", b"BBB")
        paquetes.exportar(self.ruta, "estilos", [{"nombre": "Uno"}],
                          (primera, segunda))
        with zipfile.ZipFile(self.ruta) as archivo:
            nombres = archivo.namelist()
            manifiesto = json.loads(archivo.read("manifiesto.json"))
            datos = json.loads(archivo.read("datos.json"))
        self.assertEqual(
            ["manifiesto.json", "datos.json",
             "archivos/a.gif", "archivos/b.png"], nombres)
        self.assertEqual(paquetes.FORMATO, manifiesto["formato"])
        self.assertEqual("estilos", manifiesto["tipo"])
        self.assertEqual(1, manifiesto["cantidad"])
        self.assertEqual("Guyrapu", manifiesto["app"])
        self.assertEqual([{"nombre": "Uno"}], datos)

    def test_exportar_no_pisa_el_anterior_si_falla(self):
        paquetes.exportar(self.ruta, "estilos", [])
        antes = self.ruta.read_bytes()
        with self.assertRaises(OSError):
            paquetes.exportar(self.ruta, "estilos", [],
                              (self.carpeta / "no-existe.gif",))
        self.assertEqual(antes, self.ruta.read_bytes())
        self.assertEqual([], list(self.carpeta.glob("*.tmp")))

    def test_ida_y_vuelta_con_dos_archivos(self):
        elementos = [{"nombre": "Claro", "color": "#FFFFFF"},
                     {"nombre": "Oscuro"}]
        primera = self._archivo("a.gif", b"AAA")
        segunda = self._archivo("b.png", b"BBB")
        paquetes.exportar(self.ruta, "estilos", elementos,
                          (primera, segunda))
        leido = paquetes.leer(self.ruta, "estilos",
                              extensiones=(".gif", ".png"))
        self.assertEqual("estilos", leido.tipo)
        self.assertEqual(elementos, leido.elementos)
        self.assertEqual(("a.gif", "b.png"), leido.archivos)

    def test_rechaza_lo_que_no_es_un_paquete(self):
        self.ruta.write_text("no es un zip", encoding="utf-8")
        self.assertEqual("El archivo no es un paquete de Guyrapu.",
                         self._rechazo())
        with zipfile.ZipFile(self.ruta, "w") as archivo:
            archivo.writestr("datos.json", "[]")
        self.assertEqual("El archivo no es un paquete de Guyrapu.",
                         self._rechazo())

    def test_rechaza_una_version_mas_nueva(self):
        self._paquete(formato=2)
        self.assertEqual(
            "El paquete es de una versión posterior de Guyrapu. "
            "Actualiza Guyrapu para importarlo.",
            self._rechazo())

    def test_rechaza_otro_tipo(self):
        self._paquete(tipo="avisos")
        self.assertEqual("El paquete contiene avisos, no estilos.",
                         self._rechazo())

    def test_rechaza_un_paquete_danado(self):
        casos = {
            "manifiesto": [("manifiesto.json", "{"), ("datos.json", "[]")],
            "datos": [("manifiesto.json", self._manifiesto()),
                      ("datos.json", "{")],
            "elemento": [("manifiesto.json", self._manifiesto()),
                         ("datos.json", '[{"color": "#FFFFFF"}]')],
        }
        for nombre, entradas in casos.items():
            with self.subTest(caso=nombre):
                with zipfile.ZipFile(self.ruta, "w") as archivo:
                    for entrada, contenido in entradas:
                        archivo.writestr(entrada, contenido)
                self.assertEqual("El paquete está dañado y no se puede leer.",
                                 self._rechazo())
        with self.subTest(caso="zip"):
            with zipfile.ZipFile(self.ruta, "w") as archivo:
                archivo.writestr("manifiesto.json", self._manifiesto())
                archivo.writestr("datos.json", "[]")
            self.ruta.write_bytes(self.ruta.read_bytes()[:30])
            self.assertEqual("El paquete está dañado y no se puede leer.",
                             self._rechazo())

    def test_rechaza_por_tamano_aunque_el_zip_mienta(self):
        self._paquete(elementos=[{"nombre": "Uno"}],
                      archivos=[("grande.gif", b"\0" * (60 * 1024 * 1024))],
                      compresion=zipfile.ZIP_DEFLATED)
        self.assertLess(self.ruta.stat().st_size, 1024 * 1024)
        self.assertEqual("El paquete supera el tamaño máximo de 50 MB.",
                         self._rechazo(tope_mb=50))

    def test_rechaza_rutas_y_extensiones_ajenas(self):
        casos = ("../fuera.txt", "/abs.txt", "C:/x.txt", "otro.txt",
                 "archivos/sub/", "archivos/sub/x.gif", "archivos/x.exe")
        for nombre in casos:
            with self.subTest(entrada=nombre):
                self._paquete_con(nombre)
                self.assertEqual(
                    "El paquete contiene un archivo que Guyrapu no importa: "
                    f"{nombre}.", self._rechazo())
        self.assertFalse((self.base / "fuera.txt").exists())

    def test_rechaza_una_barra_invertida(self):
        entrada = zipfile.ZipInfo("archivos/x.gif")
        entrada.filename = "archivos" + chr(92) + "x.gif"
        self._paquete_con(entrada)
        self.assertEqual(
            "El paquete contiene un archivo que Guyrapu no importa: "
            "archivos" + chr(92) + "x.gif.", self._rechazo())

    def test_acepta_una_extension_permitida_en_mayusculas(self):
        self._paquete(archivos=[("X.GIF", b"AAA")])
        leido = paquetes.leer(self.ruta, "estilos", extensiones=(".gif",))
        self.assertEqual(("X.GIF",), leido.archivos)

    def test_repetidos_ignora_mayusculas_y_espacios(self):
        elementos = [{"nombre": " Uno "}, {"nombre": "dos"},
                     {"nombre": "tres"}]
        self.assertEqual(
            [" Uno ", "dos"],
            paquetes.repetidos(elementos, ["  uno  ", "DOS "]))
        self.assertEqual(
            [" Uno "],
            paquetes.repetidos(elementos, [{"nombre": "uno"}]))
        self.assertEqual(
            [" Uno "],
            paquetes.repetidos(elementos,
                               [SimpleNamespace(nombre="uno")]))

    def test_extraer_reusa_el_mismo_y_renombra_el_distinto(self):
        original = self._archivo("x.gif", b"AAA")
        paquetes.exportar(self.ruta, "estilos", [], (original,))
        leido = paquetes.leer(self.ruta, "estilos", extensiones=("gif",))
        destino = self.carpeta / "salida"
        destino.mkdir()
        (destino / "x.gif").write_bytes(b"AAA")
        self.assertEqual({"x.gif": "x.gif"},
                         paquetes.extraer_archivos(self.ruta, leido, destino))
        (destino / "x.gif").write_bytes(b"OTRO")
        self.assertEqual({"x.gif": "x (2).gif"},
                         paquetes.extraer_archivos(self.ruta, leido, destino))
        (destino / "x (2).gif").write_bytes(b"TERCERO")
        self.assertEqual({"x.gif": "x (3).gif"},
                         paquetes.extraer_archivos(self.ruta, leido, destino))
        self.assertEqual(b"OTRO", (destino / "x.gif").read_bytes())
        self.assertEqual(b"AAA", (destino / "x (3).gif").read_bytes())

    def test_extraer_solo_escribe_dentro_de_la_carpeta(self):
        self._paquete_con("archivos/../fuera.gif")
        paquete = paquetes.Paquete("estilos", [], ("../fuera.gif",))
        destino = self.carpeta / "salida"
        destino.mkdir()
        self.assertEqual({"../fuera.gif": "fuera.gif"},
                         paquetes.extraer_archivos(self.ruta, paquete,
                                                   destino))
        self.assertEqual(b"x", (destino / "fuera.gif").read_bytes())
        self.assertFalse((self.carpeta / "fuera.gif").exists())

    def test_no_ejecuta_ni_interpreta_los_archivos(self):
        marca = self.carpeta / "ejecutado.txt"
        codigo = (f"from pathlib import Path\n"
                  f"Path({str(marca)!r}).write_text('x')\n").encode("utf-8")
        original = self._archivo("script.py", codigo)
        paquetes.exportar(self.ruta, "estilos", [], (original,))
        leido = paquetes.leer(self.ruta, "estilos", extensiones=("py",))
        destino = self.carpeta / "salida"
        destino.mkdir()
        paquetes.extraer_archivos(self.ruta, leido, destino)
        self.assertEqual(codigo, (destino / "script.py").read_bytes())
        self.assertFalse(marca.exists())

    def _encuestas(self):
        return [
            {"nombre": "¿Qué pizza?", "pregunta": "¿Qué pizza?",
             "opciones": ["muzzarella", "napolitana"], "segundos": 120,
             "destino": "video", "estilo": "clasico"},
            {"nombre": "¿Qué bebida?", "pregunta": "¿Qué bebida?",
             "opciones": ["agua", "vino"], "segundos": 300,
             "destino": "ambos", "estilo": "banda"},
        ]

    def test_ida_y_vuelta_de_encuestas(self):
        elementos = self._encuestas()
        paquetes.exportar(self.ruta, "encuestas", elementos)
        leido = paquetes.leer(self.ruta, "encuestas")
        self.assertEqual("encuestas", leido.tipo)
        self.assertEqual(elementos, leido.elementos)

    def test_un_paquete_de_medios_lleva_sus_archivos(self):
        elementos = [{"nombre": "Risa", "descripcion": "Una risa",
                      "tipo": "sonido", "archivo": "risa.wav",
                      "duracion": 3}]
        archivo = self._archivo("risa.wav", b"AAA")
        paquetes.exportar(self.ruta, "medios", elementos, (archivo,))
        leido = paquetes.leer(self.ruta, "medios",
                              extensiones=medios.EXTENSIONES)
        self.assertEqual("medios", leido.tipo)
        self.assertEqual(elementos, leido.elementos)
        self.assertEqual(("risa.wav",), leido.archivos)

    def test_un_paquete_de_medios_rechaza_un_exe(self):
        self._paquete(tipo="medios", archivos=[("virus.exe", b"x")])
        self.assertEqual(
            "El paquete contiene un archivo que Guyrapu no importa: "
            "archivos/virus.exe.",
            self._rechazo(tipo="medios", extensiones=medios.EXTENSIONES))

    def test_los_tipos_incluyen_medios(self):
        self.assertIn(("medios", "medios"), paquetes.TIPOS)

    def test_el_aviso_de_otro_tipo_nombra_las_encuestas(self):
        paquetes.exportar(self.ruta, "encuestas", self._encuestas())
        with self.assertRaises(paquetes.PaqueteRechazado) as contexto:
            paquetes.leer(self.ruta, "comandos")
        self.assertEqual("El paquete contiene encuestas, no comandos.",
                         str(contexto.exception))
        with ingles():
            with self.assertRaises(paquetes.PaqueteRechazado) as contexto:
                paquetes.leer(self.ruta, "comandos")
            self.assertEqual("The package contains polls, not commands.",
                             str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
