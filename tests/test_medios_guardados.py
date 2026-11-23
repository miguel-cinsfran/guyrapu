# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Copia y borrado de los archivos de la biblioteca de medios."""

import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import medios, medios_guardados, paquetes
from guyrapu.music import sonoridad


def _datos(**cambios):
    datos = {
        "nombre": "Risa",
        "descripcion": "Una risa",
        "tipo": "sonido",
        "archivo": "risa.wav",
        "duracion": 3,
    }
    datos.update(cambios)
    return datos


class BaseMedios(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.carpeta = self.base / "medios"
        self.origenes = self.base / "origenes"
        self.origenes.mkdir()

    def _origen(self, nombre, contenido=b"AAA"):
        ruta = self.origenes / nombre
        ruta.write_bytes(contenido)
        return ruta

    def _agregar(self, nombre="risa.wav", contenido=b"AAA", **cambios):
        origen = self._origen(nombre, contenido)
        return medios_guardados.agregar(self.carpeta, origen, _datos(**cambios))


class TestAgregar(BaseMedios):

    def test_agregar_copia_el_archivo_a_la_carpeta(self):
        medio = self._agregar()
        copia = self.carpeta / medio["archivo"]
        self.assertTrue(copia.is_file())
        self.assertEqual(copia.read_bytes(), b"AAA")
        self.assertEqual(medio["tipo"], "sonido")
        self.assertEqual(medio["duracion"], 3)

    def test_dos_archivos_con_el_mismo_nombre_no_se_pisan(self):
        primera = self._agregar(contenido=b"AAA")
        segunda = self._agregar(contenido=b"BBB")
        self.assertNotEqual(primera["archivo"], segunda["archivo"])
        self.assertEqual((self.carpeta / primera["archivo"]).read_bytes(),
                         b"AAA")
        self.assertEqual((self.carpeta / segunda["archivo"]).read_bytes(),
                         b"BBB")

    def test_eliminar_borra_la_copia(self):
        medio = self._agregar()
        copia = self.carpeta / medio["archivo"]
        self.assertTrue(copia.is_file())
        medios_guardados.eliminar(self.carpeta, medio)
        self.assertFalse(copia.exists())


class TestGanancia(BaseMedios):

    def test_conserva_la_ganancia_medida(self):
        medio = medios_guardados.normalizar(_datos(ganancia_db=-6.5))
        self.assertEqual(medio["ganancia_db"], -6.5)

    def test_la_ganancia_se_limita_al_rango(self):
        for valor, esperado in ((50, sonoridad.GANANCIA_MAXIMA_DB),
                                (-50, sonoridad.GANANCIA_MINIMA_DB)):
            with self.subTest(valor=valor):
                medio = medios_guardados.normalizar(
                    _datos(ganancia_db=valor))
                self.assertEqual(medio["ganancia_db"], esperado)

    def test_sin_ganancia_o_sin_numero_queda_vacia(self):
        for valor in (None, "alto", True, float("inf")):
            with self.subTest(valor=valor):
                medio = medios_guardados.normalizar(
                    _datos(ganancia_db=valor))
                self.assertIsNone(medio["ganancia_db"])

    def test_falta_la_ganancia_queda_vacia(self):
        self.assertIsNone(
            medios_guardados.normalizar(_datos())["ganancia_db"])

    def test_el_paquete_lleva_y_respeta_la_ganancia(self):
        medio = self._agregar(ganancia_db=-6.5)
        paquete = self.base / "medios.zip"
        paquetes.exportar(
            paquete, "medios", [medio],
            (self.carpeta / medio["archivo"],))
        leido = paquetes.leer(paquete, "medios",
                              extensiones=medios.EXTENSIONES)
        self.assertEqual(leido.elementos[0]["ganancia_db"], -6.5)
        self.assertEqual(
            medios_guardados.normalizar(leido.elementos[0])["ganancia_db"],
            -6.5)

    def test_el_indice_sigue_al_medio_editado_por_su_archivo(self):
        guardados = [medios_guardados.normalizar(_datos())]
        guardados[0]["nombre"] = "Otra risa"
        indice = medios_guardados.indice_de_archivo(guardados, "risa.wav")
        self.assertEqual(indice, 0)
        self.assertIs(guardados[indice], guardados[0])
        self.assertEqual(guardados[indice]["nombre"], "Otra risa")

    def test_el_indice_del_medio_eliminado_no_esta(self):
        self.assertIsNone(
            medios_guardados.indice_de_archivo([], "risa.wav"))


class TestMedioParaVideo(BaseMedios):

    def test_devuelve_el_medio_con_su_ruta_tipo_duracion_y_ganancia(self):
        guardado = medios_guardados.normalizar(
            _datos(nombre="fuego", tipo="video", archivo="fuego.mp4",
                   duracion=12, ganancia_db=-6.0))
        self.assertEqual(
            medios_guardados.medio_para_video(
                [guardado], self.carpeta, "fuego"),
            {"ruta": str(self.carpeta / "fuego.mp4"), "tipo": "video",
             "duracion": 12, "ganancia_db": -6.0})

    def test_sin_ese_nombre_no_hay_medio(self):
        guardado = medios_guardados.normalizar(_datos(nombre="fuego"))
        for nombre in ("otro", "", "  "):
            with self.subTest(nombre=nombre):
                self.assertIsNone(medios_guardados.medio_para_video(
                    [guardado], self.carpeta, nombre))


class TestSincronizar(BaseMedios):
    """La carpeta manda: lo que hay en ella es la lista, sin copias aparte."""

    def setUp(self):
        super().setUp()
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def test_nombres_en_carpeta_solo_archivos_de_medio_y_sin_subcarpetas(self):
        (self.carpeta / "risa.wav").write_bytes(b"AAA")
        (self.carpeta / "foto.PNG").write_bytes(b"BBB")
        (self.carpeta / "notas.txt").write_bytes(b"CCC")
        (self.carpeta / "sub").mkdir()
        (self.carpeta / "sub" / "otro.mp3").write_bytes(b"DDD")
        self.assertEqual(
            medios_guardados.nombres_en_carpeta(self.carpeta),
            ["foto.PNG", "risa.wav"])

    def test_nombres_en_carpeta_ordenados_sin_tildes_ni_mayusculas(self):
        for nombre in ("ánimo.png", "Zorro.mp4", "Ébano.wav", "agua.jpg"):
            (self.carpeta / nombre).write_bytes(b"x")
        self.assertEqual(
            medios_guardados.nombres_en_carpeta(self.carpeta),
            ["agua.jpg", "ánimo.png", "Ébano.wav", "Zorro.mp4"])

    def test_un_archivo_nuevo_aparece_con_su_nombre_sin_extension(self):
        self.assertEqual(
            medios_guardados.sincronizar([], ["risa.wav"]),
            [{"nombre": "risa", "descripcion": "", "tipo": "sonido",
              "archivo": "risa.wav", "duracion": 0, "ganancia_db": None}])

    def test_un_archivo_que_falta_desaparece(self):
        guardado = medios_guardados.normalizar(_datos())
        self.assertEqual(medios_guardados.sincronizar([guardado], []), [])

    def test_nombres_repetidos_llevan_sufijo(self):
        resultado = medios_guardados.sincronizar([], ["risa.wav", "risa.mp3"])
        self.assertEqual([medio["nombre"] for medio in resultado],
                         ["risa", "risa (2)"])

    def test_se_conserva_lo_ya_medido_de_un_archivo_que_sigue(self):
        guardado = medios_guardados.normalizar(
            _datos(descripcion="Una risa", duracion=7, ganancia_db=-6.5))
        self.assertEqual(
            medios_guardados.sincronizar([guardado], ["risa.wav"]),
            [guardado])

    def test_orden_sin_tildes_ni_mayusculas(self):
        nombres = ["Zorro.mp4", "ánimo.png", "Ébano.wav", "agua.jpg"]
        resultado = medios_guardados.sincronizar([], nombres)
        self.assertEqual([medio["nombre"] for medio in resultado],
                         ["agua", "ánimo", "Ébano", "Zorro"])


class TestArchivo(BaseMedios):

    def test_guardar_y_cargar_conserva_los_campos(self):
        ruta = self.base / "medios.json"
        medios_guardados.guardar(
            ruta, [_datos(nombre="Logo", tipo="imagen",
                          archivo="logo.png", duracion=0,
                          descripcion="El logo")])
        self.assertEqual(
            medios_guardados.cargar(ruta),
            [{"nombre": "Logo", "descripcion": "El logo", "tipo": "imagen",
              "archivo": "logo.png", "duracion": 0, "ganancia_db": None}])

    def test_un_archivo_danado_se_lee_como_lista_vacia(self):
        ruta = self.base / "medios.json"
        ruta.write_text("{roto", encoding="utf-8")
        self.assertEqual(medios_guardados.cargar(ruta), [])

    def test_un_archivo_ausente_se_lee_como_lista_vacia(self):
        self.assertEqual(
            medios_guardados.cargar(self.base / "no-existe.json"), [])


if __name__ == "__main__":
    unittest.main()
