# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import json
import tempfile
import unittest
from pathlib import Path

from guyrapu.obs import estilos_aviso
from guyrapu.obs.overlay_datos import relacion_de_contraste


CLAVES_DEL_ESTILO = {
    "clave", "nombre", "fuente", "tamano", "negrita", "color_texto",
    "color_contorno", "ancho_contorno", "color_fondo", "opacidad_fondo",
    "alineacion", "zona", "entrada", "salida", "ms_entrada", "ms_salida",
    "esquinas", "sombra",
}


class TestFabrica(unittest.TestCase):
    def test_cuatro_estilos_con_sus_claves_y_nombres(self):
        estilos = estilos_aviso.FABRICA
        self.assertEqual([estilo["clave"] for estilo in estilos],
                         ["clasico", "banda", "tarjeta", "alto_contraste"])
        self.assertEqual([estilo["nombre"] for estilo in estilos],
                         ["Clásico", "Banda", "Tarjeta", "Alto contraste"])

    def test_cada_estilo_tiene_las_claves_del_diseno(self):
        for estilo in estilos_aviso.FABRICA:
            with self.subTest(clave=estilo["clave"]):
                self.assertEqual(set(estilo), CLAVES_DEL_ESTILO)

    def test_valores_del_diseno(self):
        clasico, banda, tarjeta, contraste = estilos_aviso.FABRICA
        self.assertEqual(
            (clasico["fuente"], clasico["tamano"], clasico["negrita"],
             clasico["color_texto"], clasico["color_contorno"],
             clasico["ancho_contorno"], clasico["color_fondo"],
             clasico["opacidad_fondo"], clasico["alineacion"], clasico["zona"]),
            ("Segoe UI", 5, True, "#FFFFFF", "#000000", 4, "#000000", 0,
             "izquierda", "automatica"))
        self.assertEqual(
            (banda["fuente"], banda["tamano"], banda["negrita"],
             banda["ancho_contorno"], banda["color_fondo"],
             banda["opacidad_fondo"], banda["alineacion"], banda["zona"]),
            ("Segoe UI", 4.5, False, 0, "#1E1E1E", 85, "izquierda",
             "automatica"))
        self.assertEqual(
            (tarjeta["fuente"], tarjeta["tamano"], tarjeta["negrita"],
             tarjeta["color_texto"], tarjeta["ancho_contorno"],
             tarjeta["color_fondo"], tarjeta["opacidad_fondo"],
             tarjeta["alineacion"], tarjeta["zona"]),
            ("Segoe UI", 4, False, "#1A1A1A", 0, "#FFFFFF", 90, "centro",
             "automatica"))
        self.assertEqual(
            (contraste["fuente"], contraste["tamano"], contraste["negrita"],
             contraste["color_texto"], contraste["ancho_contorno"],
             contraste["color_fondo"], contraste["opacidad_fondo"],
             contraste["alineacion"], contraste["zona"]),
            ("Arial", 5.5, True, "#FFFF00", 0, "#000000", 100, "centro",
             "automatica"))

    def test_la_tupla_de_fabrica_no_se_modifica(self):
        original = dict(estilos_aviso.FABRICA[0])
        estilos_aviso.todos([])[0]["nombre"] = "Cambiado"
        self.assertEqual(estilos_aviso.FABRICA[0], original)

    def test_todos_pone_la_fabrica_primero_y_copia(self):
        usuario = [dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mío")]
        todos = estilos_aviso.todos(usuario)
        self.assertEqual([estilo["clave"] for estilo in todos],
                         ["clasico", "banda", "tarjeta", "alto_contraste", "mio"])
        self.assertIsNot(todos[0], estilos_aviso.FABRICA[0])
        self.assertIsNot(todos[-1], usuario[0])

    def test_buscar_da_el_estilo_y_si_falta_el_clasico(self):
        usuario = [dict(estilos_aviso.FABRICA[1], clave="mio", nombre="Mío")]
        self.assertEqual(estilos_aviso.buscar("mio", usuario)["nombre"], "Mío")
        self.assertEqual(estilos_aviso.buscar("no_existe", usuario)["clave"],
                         "clasico")


class TestPorTipo(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "estilos_avisos.json"
        self.addCleanup(self.temporal.cleanup)

    def test_cargar_lee_el_archivo_viejo_que_es_una_lista(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": "Mío"}]), encoding="utf-8")
        self.assertEqual(
            [estilo["clave"] for estilo in estilos_aviso.cargar_estilos(
                self.ruta)], ["mio"])

    def test_cargar_lee_el_archivo_nuevo_con_estilos_y_por_tipo(self):
        self.ruta.write_text(json.dumps({
            "estilos": [{"clave": "mio", "nombre": "Mío"}],
            "por_tipo": {"comando": "mio"},
        }), encoding="utf-8")
        self.assertEqual(
            [estilo["clave"] for estilo in estilos_aviso.cargar_estilos(
                self.ruta)], ["mio"])
        self.assertEqual(
            estilos_aviso.cargar_por_tipo(self.ruta)["comando"], "mio")

    def test_sin_archivo_los_cinco_tipos_son_clasico(self):
        self.assertEqual(estilos_aviso.cargar_por_tipo(self.ruta), {
            "mensaje": "clasico", "comando": "clasico",
            "disparador": "clasico", "encuesta": "clasico",
            "meta": "clasico"})

    def test_guardar_estilos_conserva_por_tipo(self):
        self.ruta.write_text(json.dumps({
            "estilos": [], "por_tipo": {"comando": "banda"}}),
            encoding="utf-8")
        estilo = dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mío")
        estilos_aviso.guardar_estilos(self.ruta, [estilo])
        self.assertEqual(
            estilos_aviso.cargar_por_tipo(self.ruta)["comando"], "banda")
        self.assertEqual(
            [e["clave"] for e in estilos_aviso.cargar_estilos(self.ruta)],
            ["mio"])

    def test_guardar_por_tipo_conserva_los_estilos(self):
        estilo = dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mío")
        estilos_aviso.guardar_estilos(self.ruta, [estilo])
        estilos_aviso.guardar_por_tipo(self.ruta, {"comando": "mio"})
        self.assertEqual(
            [e["clave"] for e in estilos_aviso.cargar_estilos(self.ruta)],
            ["mio"])
        self.assertEqual(
            estilos_aviso.cargar_por_tipo(self.ruta)["comando"], "mio")

    def test_buscar_para_con_clave_vacia_usa_el_predeterminado_del_tipo(self):
        self.assertEqual(
            estilos_aviso.buscar_para(
                "", "comando", [], {"comando": "banda"})["clave"], "banda")

    def test_buscar_para_con_clave_propia_la_usa(self):
        self.assertEqual(
            estilos_aviso.buscar_para(
                "tarjeta", "comando", [], {"comando": "banda"})["clave"],
            "tarjeta")

    def test_buscar_para_con_un_predeterminado_que_ya_no_existe(self):
        self.assertEqual(
            estilos_aviso.buscar_para(
                "", "comando", [], {"comando": "borrado"})["clave"],
            "clasico")

    def test_los_cinco_tipos_son_las_claves_de_la_pieza(self):
        self.assertEqual(
            [clave for clave, _nombre in estilos_aviso.TIPOS],
            ["mensaje", "comando", "disparador", "encuesta", "meta"])


class TestZonas(unittest.TestCase):
    def test_diez_zonas_con_automatica_primero(self):
        self.assertEqual(
            [clave for clave, _nombre in estilos_aviso.ZONAS],
            ["automatica", "arriba_izquierda", "arriba_centro",
             "arriba_derecha", "medio_izquierda", "medio_centro",
             "medio_derecha", "abajo_izquierda", "abajo_centro",
             "abajo_derecha"])
        self.assertEqual(estilos_aviso.ZONAS[0],
                         ("automatica", "Según la orientación del vídeo"))
        self.assertTrue(all(nombre for _clave, nombre in estilos_aviso.ZONAS))


class TestZonaAutomatica(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "estilos_avisos.json"
        self.addCleanup(self.temporal.cleanup)

    def test_la_fabrica_usa_la_zona_automatica(self):
        for estilo in estilos_aviso.todos([]):
            with self.subTest(clave=estilo["clave"]):
                self.assertEqual(estilo["zona"], "automatica")

    def test_un_estilo_nuevo_usa_la_zona_automatica(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": "Mío"}]), encoding="utf-8")
        self.assertEqual(
            estilos_aviso.cargar_estilos(self.ruta)[0]["zona"], "automatica")

    def test_una_zona_desconocida_queda_en_automatica(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": "Mío",
                         "zona": "inventada"}]), encoding="utf-8")
        self.assertEqual(
            estilos_aviso.cargar_estilos(self.ruta)[0]["zona"], "automatica")


class TestAnimaciones(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "estilos_avisos.json"
        self.addCleanup(self.temporal.cleanup)

    def _base(self):
        return dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mi estilo")

    def test_la_fabrica_entra_suave_y_sale_con_fundido(self):
        for estilo in estilos_aviso.todos([]):
            with self.subTest(clave=estilo["clave"]):
                self.assertEqual(estilo["entrada"], "suave")
                self.assertEqual(estilo["salida"], "fundido")
                self.assertEqual(estilo["ms_entrada"], 350)
                self.assertEqual(estilo["ms_salida"], 250)

    def test_validar_rechaza_duraciones_fuera_de_rango(self):
        for clave in ("ms_entrada", "ms_salida"):
            for valor in (99, 1001):
                with self.subTest(clave=clave, valor=valor):
                    self.assertTrue(estilos_aviso.validar_estilo(
                        dict(self._base(), **{clave: valor}), []))

    def test_validar_acepta_los_extremos_del_rango(self):
        for clave in ("ms_entrada", "ms_salida"):
            for valor in (100, 1000):
                with self.subTest(clave=clave, valor=valor):
                    self.assertEqual(estilos_aviso.validar_estilo(
                        dict(self._base(), **{clave: valor}), []), "")

    def test_un_archivo_fuera_de_rango_se_acota_al_extremo(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": "Mío",
                         "ms_entrada": 50, "ms_salida": 5000}]),
            encoding="utf-8")
        estilo = estilos_aviso.cargar_estilos(self.ruta)[0]
        self.assertEqual(estilo["ms_entrada"], 100)
        self.assertEqual(estilo["ms_salida"], 1000)

    def test_una_animacion_desconocida_se_lee_como_la_de_fabrica(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": "Mío",
                         "entrada": "inventada", "salida": "otra"}]),
            encoding="utf-8")
        estilo = estilos_aviso.cargar_estilos(self.ruta)[0]
        self.assertEqual(estilo["entrada"], "suave")
        self.assertEqual(estilo["salida"], "fundido")


class TestFondo(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "estilos_avisos.json"
        self.addCleanup(self.temporal.cleanup)

    def test_esquinas_y_sombra_de_fabrica(self):
        estilos = {estilo["clave"]: estilo
                   for estilo in estilos_aviso.todos([])}
        self.assertEqual(
            (estilos["tarjeta"]["esquinas"], estilos["tarjeta"]["sombra"]),
            ("redondeadas", True))
        for clave in ("clasico", "banda", "alto_contraste"):
            with self.subTest(clave=clave):
                self.assertEqual(
                    (estilos[clave]["esquinas"], estilos[clave]["sombra"]),
                    ("rectas", False))

    def test_un_estilo_nuevo_es_redondeado_y_sin_sombra(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": "Mío"}]), encoding="utf-8")
        estilo = estilos_aviso.cargar_estilos(self.ruta)[0]
        self.assertEqual(
            (estilo["esquinas"], estilo["sombra"]), ("redondeadas", False))

    def test_la_banda_tiene_ochenta_y_cinco_de_opacidad(self):
        banda = next(estilo for estilo in estilos_aviso.todos([])
                     if estilo["clave"] == "banda")
        self.assertEqual(banda["opacidad_fondo"], 85)


class TestColores(unittest.TestCase):
    def test_doce_colores_con_nombre(self):
        self.assertEqual(len(estilos_aviso.COLORES), 12)
        self.assertEqual(estilos_aviso.COLORES[0],
                         ("Blanco", "#FFFFFF"))
        self.assertEqual(estilos_aviso.COLORES[-1],
                         ("Gris oscuro", "#1E1E1E"))

    def test_nombre_conocido_sin_distinguir_mayusculas(self):
        self.assertEqual(estilos_aviso.nombre_de_color("#ffffff"), "Blanco")
        self.assertEqual(estilos_aviso.nombre_de_color("#1e1e1e"),
                         "Gris oscuro")

    def test_nombre_desconocido_da_el_codigo(self):
        self.assertEqual(estilos_aviso.nombre_de_color("#123456"), "#123456")


class TestPixeles(unittest.TestCase):
    def test_el_tamano_usa_el_lado_menor_del_lienzo(self):
        estilo = {"tamano": 5}
        self.assertEqual(estilos_aviso.tamano_en_pixeles(estilo, 1920, 1080), 54)
        self.assertEqual(estilos_aviso.tamano_en_pixeles(estilo, 1080, 1920), 54)

    def test_el_tamano_nunca_baja_de_ocho(self):
        self.assertEqual(
            estilos_aviso.tamano_en_pixeles({"tamano": 2}, 100, 100), 8)

    def test_el_contorno_escala_con_el_lado_menor(self):
        estilo = {"ancho_contorno": 4}
        self.assertEqual(
            estilos_aviso.contorno_en_pixeles(estilo, 1920, 1080), 4)
        self.assertEqual(
            estilos_aviso.contorno_en_pixeles(estilo, 1280, 720), 3)


class TestContraste(unittest.TestCase):
    def test_los_cuatro_de_fabrica_no_avisan(self):
        for estilo in estilos_aviso.FABRICA:
            with self.subTest(clave=estilo["clave"]):
                self.assertEqual(estilos_aviso.aviso_contraste(estilo), "")

    def test_avisa_texto_claro_sobre_fondo_claro(self):
        estilo = dict(estilos_aviso.FABRICA[0], color_texto="#FFFF00",
                      color_fondo="#FFFFFF", opacidad_fondo=100,
                      ancho_contorno=0)
        aviso = estilos_aviso.aviso_contraste(estilo)
        self.assertIn("1,1", aviso)
        self.assertIn("4,5", aviso)

    def test_avisa_sin_fondo_ni_contorno(self):
        estilo = dict(estilos_aviso.FABRICA[0], opacidad_fondo=0,
                      ancho_contorno=0)
        self.assertIsNone(estilos_aviso.contraste(estilo))
        self.assertTrue(estilos_aviso.aviso_contraste(estilo))

    def test_manda_la_opacidad_del_fondo_desde_cincuenta(self):
        estilo = dict(estilos_aviso.FABRICA[0], color_texto="#FFFFFF",
                      color_fondo="#000000", opacidad_fondo=50,
                      color_contorno="#FF0000", ancho_contorno=4)
        self.assertAlmostEqual(estilos_aviso.contraste(estilo), 21.0)

    def test_sin_fondo_usa_el_contorno(self):
        estilo = dict(estilos_aviso.FABRICA[0], opacidad_fondo=0,
                      color_texto="#FFFFFF", color_contorno="#000000",
                      ancho_contorno=2)
        self.assertAlmostEqual(
            estilos_aviso.contraste(estilo),
            relacion_de_contraste("#FFFFFF", "#000000"))


class TestFuente(unittest.TestCase):
    def test_fuente_instalada_sin_aviso(self):
        self.assertEqual(
            estilos_aviso.fuente_para({"fuente": "Arial"}, ["arial"]),
            ("Arial", ""))

    def test_fuente_faltante_usa_segoe_y_avisa(self):
        fuente, aviso = estilos_aviso.fuente_para(
            {"fuente": "Arial"}, ["Segoe UI"])
        self.assertEqual(fuente, "Segoe UI")
        self.assertIn("Arial", aviso)
        self.assertIn("Segoe UI", aviso)


class TestCargarYGuardar(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "estilos_avisos.json"
        self.addCleanup(self.temporal.cleanup)

    def test_archivo_ausente(self):
        self.assertEqual(estilos_aviso.cargar_estilos(self.ruta), [])

    def test_json_roto(self):
        self.ruta.write_text("{ roto", encoding="utf-8")
        self.assertEqual(estilos_aviso.cargar_estilos(self.ruta), [])

    def test_json_que_no_es_lista(self):
        self.ruta.write_text("5", encoding="utf-8")
        self.assertEqual(estilos_aviso.cargar_estilos(self.ruta), [])

    def test_numero_donde_va_texto_se_fuerza_sin_romper(self):
        self.ruta.write_text(
            json.dumps([{"clave": "mio", "nombre": 5}]), encoding="utf-8")
        estilos = estilos_aviso.cargar_estilos(self.ruta)
        self.assertEqual(len(estilos), 1)
        self.assertEqual(estilos[0]["nombre"], "5")

    def test_fuerza_los_tipos_de_cada_clave_conocida(self):
        self.ruta.write_text(json.dumps([{
            "clave": "mio", "nombre": "Mío", "fuente": 7, "tamano": "6.5",
            "negrita": "true", "ancho_contorno": "3", "opacidad_fondo": "80",
        }]), encoding="utf-8")
        estilo = estilos_aviso.cargar_estilos(self.ruta)[0]
        self.assertEqual(estilo["fuente"], "7")
        self.assertEqual(estilo["tamano"], 6.5)
        self.assertIs(estilo["negrita"], True)
        self.assertEqual(estilo["ancho_contorno"], 3)
        self.assertEqual(estilo["opacidad_fondo"], 80)

    def test_descarta_un_estilo_con_clave_de_fabrica(self):
        self.ruta.write_text(
            json.dumps([{"clave": "clasico", "nombre": "Otro"}]), encoding="utf-8")
        self.assertEqual(estilos_aviso.cargar_estilos(self.ruta), [])

    def test_guardar_y_cargar_conserva_los_estilos(self):
        estilo = dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mío")
        estilos_aviso.guardar_estilos(self.ruta, [estilo])
        self.assertEqual(estilos_aviso.cargar_estilos(self.ruta), [estilo])

    def test_guardar_reemplaza_de_forma_atomica(self):
        self.ruta.write_text("estilo anterior", encoding="utf-8")
        estilos_aviso.guardar_estilos(self.ruta, [])
        self.assertEqual(estilos_aviso.cargar_estilos(self.ruta), [])
        self.assertEqual(list(self.ruta.parent.glob("*.tmp")), [])


class TestValidarEstilo(unittest.TestCase):
    def _base(self):
        return dict(estilos_aviso.FABRICA[0], clave="mio", nombre="Mi estilo")

    def test_estilo_valido(self):
        self.assertEqual(estilos_aviso.validar_estilo(self._base(), []), "")

    def test_nombre_vacio(self):
        self.assertTrue(estilos_aviso.validar_estilo(
            dict(self._base(), nombre="   "), []))

    def test_nombre_repetido_de_fabrica_sin_distinguir_mayusculas(self):
        self.assertTrue(estilos_aviso.validar_estilo(
            dict(self._base(), nombre="clásico"), []))

    def test_nombre_repetido_de_usuario(self):
        otros = [dict(self._base(), clave="otro", nombre="MI ESTILO")]
        self.assertTrue(estilos_aviso.validar_estilo(self._base(), otros))

    def test_el_mismo_clave_no_cuenta_como_repetido(self):
        otros = [dict(self._base(), nombre="Mi estilo")]
        self.assertEqual(estilos_aviso.validar_estilo(self._base(), otros), "")

    def test_tamano_fuera_de_rango(self):
        for tamano in (1.9, 15.1):
            with self.subTest(tamano=tamano):
                self.assertTrue(estilos_aviso.validar_estilo(
                    dict(self._base(), tamano=tamano), []))

    def test_color_que_no_es_un_codigo_valido(self):
        for clave in ("color_texto", "color_contorno", "color_fondo"):
            with self.subTest(clave=clave):
                self.assertTrue(estilos_aviso.validar_estilo(
                    dict(self._base(), **{clave: "rojo"}), []))

    def test_opacidad_fuera_de_rango(self):
        for opacidad in (-1, 101):
            with self.subTest(opacidad=opacidad):
                self.assertTrue(estilos_aviso.validar_estilo(
                    dict(self._base(), opacidad_fondo=opacidad), []))


if __name__ == "__main__":
    unittest.main()
