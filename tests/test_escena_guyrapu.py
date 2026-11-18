# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la escena propia de Guyrapu, con un cliente falso de OBS."""

import base64
import os
import struct
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paths
from guyrapu.obs import escena_guyrapu, estilos_aviso, fondo_guardado, fondo_tarjeta
from guyrapu.obs import fuentes_windows, medio_obs
from guyrapu.obs.obs_cliente import ObsError


TEXTO = escena_guyrapu.TEXTO
FONDO = escena_guyrapu.FONDO
TARJETA = escena_guyrapu.TARJETA
ESCENA = escena_guyrapu.ESCENA
OPACIDAD = escena_guyrapu.OPACIDAD


class ClienteFalso:
    """Guarda cada pedido y responde como OBS, con escenas y entradas."""

    def __init__(self, ancho=1000, alto=1000, programa="Juego"):
        self.ancho = ancho
        self.alto = alto
        self.programa = programa
        self.escenas = {"Juego": []}
        self.entradas = {}
        self.filtros = {}
        self.llamadas = []
        self.ancho_por_caracter = 10
        self.alto_de_linea = 20
        self.fondo_pixel = (255, 255, 255, 230)
        self.fondo_consultas = 0
        self.fondo_falla = 0
        self._siguiente = 1

    def pedir(self, tipo, datos=None, parada=None):
        datos = dict(datos or {})
        self.llamadas.append((tipo, datos))
        manejador = getattr(self, "_" + tipo, None)
        return {"responseData": manejador(datos) if manejador else {}}

    def pedidos(self, tipo):
        return [datos for llamado, datos in self.llamadas if llamado == tipo]

    def agregar_item(self, escena, fuente):
        item = self._item(fuente)
        self.escenas[escena].append(item)
        return item

    def fuentes_de(self, escena):
        return [item["sourceName"] for item in self.escenas[escena]]

    def _item(self, fuente, transformacion=None):
        item = {
            "sceneItemId": self._siguiente,
            "sceneItemIndex": 0,
            "sourceName": fuente,
            "sceneItemEnabled": True,
            "sceneItemTransform": transformacion or {
                "positionX": 0, "positionY": 0, "alignment": 5,
                "scaleX": 1, "scaleY": 1},
        }
        self._siguiente += 1
        return item

    @staticmethod
    def _renumerar(items):
        for indice, item in enumerate(items):
            item["sceneItemIndex"] = indice

    def _buscar(self, datos):
        for item in self.escenas.get(datos.get("sceneName", ""), ()):
            if item["sceneItemId"] == datos.get("sceneItemId"):
                return item
        raise ObsError("no existe", 600)

    def _GetSceneList(self, datos):
        return {"scenes": [{"sceneName": nombre}
                           for nombre in self.escenas],
                "currentProgramSceneName": self.programa}

    def _GetCurrentProgramScene(self, datos):
        return {"currentProgramSceneName": self.programa}

    def _GetVideoSettings(self, datos):
        return {"baseWidth": self.ancho, "baseHeight": self.alto}

    def _CreateScene(self, datos):
        nombre = datos["sceneName"]
        if nombre in self.escenas:
            raise ObsError("ya existe", 601)
        self.escenas[nombre] = []
        return {}

    def _RemoveScene(self, datos):
        nombre = datos["sceneName"]
        if nombre not in self.escenas:
            raise ObsError("no existe", 600)
        del self.escenas[nombre]
        self.filtros.pop(nombre, None)
        for items in self.escenas.values():
            items[:] = [item for item in items
                        if item["sourceName"] != nombre]
            self._renumerar(items)
        return {}

    def _GetSceneItemList(self, datos):
        nombre = datos["sceneName"]
        if nombre not in self.escenas:
            raise ObsError("no existe", 600)
        items = sorted(self.escenas[nombre],
                       key=lambda item: item["sceneItemIndex"])
        return {"sceneItems": [dict(item) for item in items]}

    def _CreateSceneItem(self, datos):
        escena = datos["sceneName"]
        if escena not in self.escenas:
            raise ObsError("no existe", 600)
        item = self._item(datos["sourceName"])
        item["sceneItemIndex"] = len(self.escenas[escena])
        self.escenas[escena].append(item)
        return {"sceneItemId": item["sceneItemId"]}

    def _RemoveSceneItem(self, datos):
        escena = datos["sceneName"]
        if escena not in self.escenas:
            raise ObsError("no existe", 600)
        item = self._buscar(datos)
        self.escenas[escena].remove(item)
        self._renumerar(self.escenas[escena])
        return {}

    def _SetSceneItemIndex(self, datos):
        escena = datos["sceneName"]
        item = self._buscar(datos)
        self.escenas[escena].remove(item)
        self.escenas[escena].insert(datos["sceneItemIndex"], item)
        self._renumerar(self.escenas[escena])
        return {}

    def _SetSceneItemEnabled(self, datos):
        self._buscar(datos)["sceneItemEnabled"] = datos["sceneItemEnabled"]
        return {}

    def _SetSceneItemTransform(self, datos):
        self._buscar(datos)["sceneItemTransform"].update(
            datos["sceneItemTransform"])
        return {}

    def _GetSceneItemTransform(self, datos):
        item = self._buscar(datos)
        transformacion = dict(item["sceneItemTransform"])
        if item["sourceName"] == TEXTO:
            texto = self.entradas.get(TEXTO, {}).get(
                "inputSettings", {}).get("text", "")
            lineas = str(texto).split("\n")
            transformacion["sourceWidth"] = (
                max((len(linea) for linea in lineas), default=0)
                * self.ancho_por_caracter)
            transformacion["sourceHeight"] = (
                len(lineas) * self.alto_de_linea)
        return {"sceneItemTransform": transformacion}

    def _CreateInput(self, datos):
        nombre = datos["inputName"]
        if nombre in self.entradas:
            raise ObsError("ya existe", 601)
        self.entradas[nombre] = {
            "inputKind": datos.get("inputKind", ""),
            "inputSettings": dict(datos.get("inputSettings") or {}),
        }
        escena = datos.get("sceneName")
        if escena:
            item = self._item(nombre)
            item["sceneItemIndex"] = len(self.escenas[escena])
            self.escenas[escena].append(item)
            return {"sceneItemId": item["sceneItemId"]}
        return {}

    def _GetInputList(self, datos):
        return {"inputs": [{"inputName": nombre,
                            "inputKind": entrada["inputKind"]}
                           for nombre, entrada in self.entradas.items()]}

    def _GetInputSettings(self, datos):
        entrada = self.entradas.get(datos["inputName"])
        if entrada is None:
            raise ObsError("no existe", 600)
        return {"inputSettings": dict(entrada["inputSettings"]),
                "inputKind": entrada["inputKind"]}

    def _SetInputSettings(self, datos):
        entrada = self.entradas.get(datos["inputName"])
        if entrada is None:
            raise ObsError("no existe", 600)
        entrada["inputSettings"].update(datos["inputSettings"])
        return {}

    def _RemoveInput(self, datos):
        nombre = datos["inputName"]
        if nombre not in self.entradas:
            raise ObsError("no existe", 600)
        del self.entradas[nombre]
        self.filtros.pop(nombre, None)
        for items in self.escenas.values():
            items[:] = [item for item in items
                        if item["sourceName"] != nombre]
            self._renumerar(items)
        return {}

    def _GetSourceFilterList(self, datos):
        return {"filters": [dict(filtro) for filtro in
                            self.filtros.get(datos["sourceName"], ())]}

    def _CreateSourceFilter(self, datos):
        self.filtros.setdefault(datos["sourceName"], []).append({
            "filterName": datos["filterName"],
            "filterKind": datos["filterKind"],
            "filterSettings": dict(datos.get("filterSettings") or {}),
            "filterEnabled": True,
        })
        return {}

    def _SetSourceFilterSettings(self, datos):
        for filtro in self.filtros.get(datos["sourceName"], ()):
            if filtro["filterName"] == datos["filterName"]:
                filtro["filterSettings"].update(datos["filterSettings"])
        return {}

    def _SetSourceFilterEnabled(self, datos):
        for filtro in self.filtros.get(datos["sourceName"], ()):
            if filtro["filterName"] == datos["filterName"]:
                filtro["filterEnabled"] = datos["filterEnabled"]
        return {}

    def _GetSourceScreenshot(self, datos):
        if datos.get("sourceName") == FONDO:
            self.fondo_consultas += 1
            if self.fondo_consultas <= self.fondo_falla:
                raise ObsError("todavía no")
            pixel = self.fondo_pixel
            if callable(pixel):
                pixel = pixel(self.fondo_consultas)
            return {"imageData": "data:image/bmp;base64,"
                    + base64.b64encode(_bmp(pixel)).decode("ascii")}
        return {"imageData": "data:image/png;base64,"
                + base64.b64encode(b"PNG").decode("ascii")}


def _bmp(pixel):
    rojo, verde, azul, alfa = pixel
    fila = bytes((azul, verde, rojo, alfa)) * 16
    cuerpo = fila * 16
    cabecera = struct.pack("<2sIHHI", b"BM", 54 + len(cuerpo), 0, 0, 54)
    informacion = struct.pack("<IiiHHIIiiII", 40, 16, 16, 1, 32, 0,
                              len(cuerpo), 0, 0, 0, 0)
    return cabecera + informacion + cuerpo


def _estilo(**cambios):
    base = dict(estilos_aviso.FABRICA[2], zona="arriba_izquierda")
    base.update(cambios)
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name) / "fondos-avisos"
        parche = mock.patch.object(paths, "fondos_de_avisos",
                                   return_value=self.carpeta)
        parche.start()
        self.addCleanup(parche.stop)
        parche = mock.patch.object(
            fuentes_windows, "familias",
            return_value=["Segoe UI", "Arial"])
        parche.start()
        self.addCleanup(parche.stop)
        parche = mock.patch.object(
            fuentes_windows, "medidor",
            side_effect=lambda _familia, _tamano, _negrita: (
                lambda texto: len(texto) * 10))
        parche.start()
        self.addCleanup(parche.stop)
        parche = mock.patch.object(escena_guyrapu.time, "sleep")
        parche.start()
        self.addCleanup(parche.stop)
        self.fondo = mock.Mock(return_value=fondo_tarjeta.Fondo(
            b"PNG", 200, 80, 20, 15))
        parche = mock.patch.object(escena_guyrapu.fondo_tarjeta, "fondo",
                                   self.fondo)
        parche.start()
        self.addCleanup(parche.stop)
        self.cliente = ClienteFalso()
        self.capa = escena_guyrapu.EscenaGuyrapu(self.cliente)


class TestPreparar(Base):
    def test_p1_arma_escenas_entradas_y_filtro_una_sola_vez(self):
        self.capa.preparar()
        self.cliente.filtros[TARJETA][0]["filterSettings"]["opacity"] = 0
        self.capa.preparar()
        self.assertEqual(self.cliente.fuentes_de(ESCENA), [TARJETA])
        self.assertEqual(self.cliente.fuentes_de(TARJETA), [FONDO, TEXTO])
        filtros = self.cliente.filtros[TARJETA]
        self.assertEqual(len(filtros), 1)
        self.assertEqual(filtros[0]["filterName"], OPACIDAD)
        self.assertEqual(filtros[0]["filterKind"], "color_filter_v2")
        self.assertEqual(filtros[0]["filterSettings"]["opacity"], 1)
        self.assertEqual(len(self.cliente.pedidos("CreateScene")), 2)
        self.assertEqual(len(self.cliente.pedidos("CreateInput")), 2)
        self.assertEqual(len(self.cliente.pedidos("CreateSceneItem")), 1)
        self.assertEqual(len(self.cliente.pedidos("CreateSourceFilter")), 1)
        item = self.cliente.escenas[ESCENA][0]
        self.assertEqual(item["sceneItemTransform"]["positionX"], 0)
        self.assertEqual(item["sceneItemTransform"]["positionY"], 0)
        self.assertEqual(item["sceneItemTransform"]["alignment"], 5)
        self.assertTrue(item["sceneItemEnabled"])

    def test_p2_saca_la_escena_de_una_escena_del_usuario(self):
        self.cliente.agregar_item("Juego", ESCENA)
        self.capa.preparar()
        self.assertNotIn(ESCENA, self.cliente.fuentes_de("Juego"))


class TestMostrar(Base):
    def test_p3_manda_estilo_y_texto_en_dos_pedidos_en_orden(self):
        self.capa.preparar()
        estilo = dict(estilos_aviso.FABRICA[0], zona="arriba_izquierda")
        self.capa.mostrar("Hola", estilo)
        ajustes = [datos["inputSettings"] for datos in
                   self.cliente.pedidos("SetInputSettings")
                   if datos["inputName"] == TEXTO]
        self.assertEqual(len(ajustes), 2)
        self.assertNotIn("text", ajustes[0])
        self.assertEqual(ajustes[0]["font"],
                         {"face": "Segoe UI", "size": 50, "flags": 1})
        self.assertEqual(ajustes[0]["color"], 0xFFFFFFFF)
        self.assertEqual(ajustes[0]["outline"], True)
        self.assertEqual(ajustes[0]["outline_size"], 4)
        self.assertEqual(ajustes[0]["outline_color"], 0xFF000000)
        self.assertEqual(ajustes[0]["align"], "left")
        self.assertEqual(ajustes[0]["valign"], "top")
        self.assertEqual(ajustes[1], {"text": "Hola"})

    def test_p3_sin_contorno_lo_deja_apagado(self):
        self.capa.preparar()
        estilo = dict(estilos_aviso.FABRICA[1], zona="arriba_izquierda")
        self.cliente.fondo_pixel = (0x1E, 0x1E, 0x1E, 217)
        self.capa.mostrar("Hola", estilo)
        ajustes = [datos["inputSettings"] for datos in
                   self.cliente.pedidos("SetInputSettings")
                   if datos["inputName"] == TEXTO][0]
        self.assertEqual(ajustes["outline"], False)
        self.assertEqual(ajustes["outline_size"], 0)

    def test_p3_usa_segoe_ui_si_la_fuente_no_esta(self):
        self.capa.preparar()
        estilo = dict(estilos_aviso.FABRICA[0], fuente="No Existe",
                      zona="arriba_izquierda")
        tarjeta = self.capa.mostrar("Hola", estilo)
        self.assertTrue(tarjeta.aviso_fuente)
        ajustes = [datos["inputSettings"] for datos in
                   self.cliente.pedidos("SetInputSettings")
                   if datos["inputName"] == TEXTO][0]
        self.assertEqual(ajustes["font"]["face"], "Segoe UI")

    def test_p4_parte_y_vuelve_a_partir_hasta_tres_veces(self):
        self.capa.preparar()
        self.cliente.ancho_por_caracter = 20
        limites = []
        original = fuentes_windows.partir_en_lineas

        def partir(texto, ancho, medir):
            limites.append(ancho)
            return original(texto, ancho, medir)

        with mock.patch.object(fuentes_windows, "partir_en_lineas", partir):
            self.capa.mostrar("palabra " * 30,
                              dict(estilos_aviso.FABRICA[0],
                                   zona="arriba_izquierda"))
        self.assertEqual(limites, [800, 720, 648, 583])
        textos = [datos["inputSettings"] for datos in
                  self.cliente.pedidos("SetInputSettings")
                  if datos["inputName"] == TEXTO
                  and "text" in datos["inputSettings"]]
        self.assertEqual(len(textos), 4)

    def test_p5_mide_la_tarjeta_y_escribe_el_fondo(self):
        self.capa.preparar()
        estilo = _estilo()
        tarjeta = self.capa.mostrar("Hola", estilo)
        self.assertEqual((tarjeta.ancho, tarjeta.alto), (88, 44))
        self.fondo.assert_called_once()
        argumentos = self.fondo.call_args.args
        self.assertEqual(argumentos[:6],
                         (88, 44, "#FFFFFF", 90, True, True))
        self.assertAlmostEqual(argumentos[6], 1000 / 1080)
        self.assertEqual(len(list(self.carpeta.glob("*.png"))), 1)
        item = next(item for item in self.cliente.escenas[TARJETA]
                    if item["sourceName"] == FONDO)
        self.assertTrue(item["sceneItemEnabled"])

    def test_p5_sin_fondo_mide_el_texto_y_oculta_la_imagen(self):
        self.capa.preparar()
        tarjeta = self.capa.mostrar(
            "Hola", dict(estilos_aviso.FABRICA[0],
                         zona="arriba_izquierda"))
        self.assertEqual((tarjeta.ancho, tarjeta.alto), (40, 20))
        self.fondo.assert_not_called()
        item = next(item for item in self.cliente.escenas[TARJETA]
                    if item["sourceName"] == FONDO)
        self.assertFalse(item["sceneItemEnabled"])

    def test_p5_espera_el_fondo_nuevo_antes_de_ponerlo_al_frente(self):
        self.capa.preparar()
        estilo = _estilo(color_fondo="#112233", opacidad_fondo=90)
        self.cliente.fondo_pixel = lambda consulta: (
            (0, 0, 0, 0) if consulta == 1
            else (0x11, 0x22, 0x33, 230))
        esperas = []
        self.capa.mostrar("Hola", estilo, esperar=esperas.append)
        self.assertEqual(self.cliente.fondo_consultas, 2)
        self.assertEqual(esperas, [0.03])
        pantallas = [indice for indice, (tipo, datos) in
                     enumerate(self.cliente.llamadas)
                     if tipo == "GetSourceScreenshot"
                     and datos.get("sourceName") == FONDO]
        frente = [indice for indice, (tipo, datos) in
                  enumerate(self.cliente.llamadas)
                  if tipo == "CreateSceneItem"
                  and datos.get("sourceName") == ESCENA
                  and datos.get("sceneName") == "Juego"]
        self.assertEqual(len(pantallas), 2)
        self.assertEqual(len(frente), 1)
        self.assertGreater(frente[0], pantallas[1])

    def test_p5_si_la_captura_del_fondo_falla_reintenta(self):
        self.capa.preparar()
        self.cliente.fondo_falla = 1
        esperas = []
        self.capa.mostrar("Hola", _estilo(), esperar=esperas.append)
        self.assertEqual(self.cliente.fondo_consultas, 2)
        self.assertEqual(esperas, [0.03])
        self.assertEqual(self.cliente.fuentes_de("Juego"), [ESCENA])

    def test_p6_ubica_texto_y_fondo_en_la_zona(self):
        self.capa.preparar()
        self.capa.mostrar("Hola", _estilo())
        transformaciones = {
            item["sourceName"]: item["sceneItemTransform"]
            for item in self.cliente.escenas[TARJETA]}
        self.assertEqual(
            (transformaciones[TEXTO]["positionX"],
             transformaciones[TEXTO]["positionY"]),
            (124, 112))
        self.assertEqual(
            (transformaciones[FONDO]["positionX"],
             transformaciones[FONDO]["positionY"]),
            (80, 85))
        for transformacion in transformaciones.values():
            self.assertEqual(transformacion["alignment"], 5)
            self.assertEqual(
                (transformacion["scaleX"], transformacion["scaleY"]),
                (1, 1))

    def test_p7_agrega_la_escena_arriba_de_lo_que_esta_al_aire(self):
        self.capa.preparar()
        self.cliente.agregar_item("Juego", "Cámara")
        tarjeta = self.capa.mostrar("Hola", _estilo())
        self.assertEqual(tarjeta.escena, "Juego")
        self.assertEqual(self.cliente.fuentes_de("Juego"),
                         ["Cámara", ESCENA])

    def test_p7_si_ya_estaba_la_sube_arriba(self):
        self.capa.preparar()
        self.cliente.agregar_item("Juego", ESCENA)
        self.cliente.agregar_item("Juego", "Cámara")
        self.capa.mostrar("Hola", _estilo())
        self.assertEqual(self.cliente.fuentes_de("Juego"),
                         ["Cámara", ESCENA])

    def test_p7_no_agrega_nada_si_la_escena_es_la_propia(self):
        self.capa.preparar()
        self.cliente.programa = ESCENA
        tarjeta = self.capa.mostrar("Hola", _estilo())
        self.assertEqual(tarjeta.escena, "")
        self.assertEqual(self.cliente.fuentes_de(ESCENA), [TARJETA])


class TestArmar(Base):
    def test_p1_arma_igual_que_mostrar_sin_tocar_la_escena_del_programa(self):
        self.capa.preparar()
        self.cliente.agregar_item("Juego", "Cámara")
        self.cliente.llamadas = []
        tarjeta = self.capa.armar("Hola", _estilo())
        armado = list(self.cliente.llamadas)
        tipos = [tipo for tipo, _datos in armado]
        self.assertNotIn("GetCurrentProgramScene", tipos)
        self.assertNotIn("CreateSceneItem", tipos)
        self.assertNotIn("SetSceneItemIndex", tipos)
        self.assertEqual(tarjeta.escena, "")
        self.assertEqual(self.cliente.fuentes_de("Juego"), ["Cámara"])
        self.cliente.llamadas = []
        mostrada = self.capa.mostrar("Hola", _estilo())
        self.assertEqual(mostrada, tarjeta._replace(escena="Juego"))
        self.assertEqual(self.cliente.llamadas[:len(armado)], armado)


class TestMostrarSinTarjeta(Base):
    def test_p3_apaga_la_tarjeta_y_pone_la_escena_al_frente(self):
        self.capa.preparar()
        self.cliente.agregar_item("Juego", "Cámara")
        self.capa.mostrar_sin_tarjeta()
        item = next(item for item in self.cliente.escenas[ESCENA]
                    if item["sourceName"] == TARJETA)
        self.assertFalse(item["sceneItemEnabled"])
        self.assertEqual(self.cliente.fuentes_de("Juego"), ["Cámara", ESCENA])

    def test_p3_mostrar_vuelve_a_habilitar_la_tarjeta(self):
        self.capa.preparar()
        self.capa.mostrar_sin_tarjeta()
        self.capa.mostrar("Hola", _estilo())
        item = next(item for item in self.cliente.escenas[ESCENA]
                    if item["sourceName"] == TARJETA)
        self.assertTrue(item["sceneItemEnabled"])


class TestEnElPrograma(Base):
    def test_p3_dice_si_la_escena_esta_en_la_del_programa(self):
        self.capa.preparar()
        self.assertFalse(self.capa.en_el_programa())
        self.cliente.agregar_item("Juego", ESCENA)
        self.assertTrue(self.capa.en_el_programa())

    def test_p3_la_propia_escena_al_aire_cuenta(self):
        self.cliente.programa = ESCENA
        self.assertTrue(self.capa.en_el_programa())


class TestOcultarYQuitar(Base):
    def test_p8_quita_la_escena_de_donde_la_puso(self):
        self.capa.preparar()
        self.capa.mostrar("Hola", _estilo())
        self.capa.ocultar()
        self.assertNotIn(ESCENA, self.cliente.fuentes_de("Juego"))

    def test_p8_si_la_escena_ya_no_existe_no_falla(self):
        self.capa.preparar()
        self.capa.mostrar("Hola", _estilo())
        del self.cliente.escenas["Juego"]
        self.capa.ocultar()

    def test_p9_quita_escenas_entradas_y_png(self):
        self.capa.preparar()
        self.capa.mostrar("Hola", _estilo())
        self.capa.quitar_todo()
        self.assertNotIn(ESCENA, self.cliente.escenas)
        self.assertNotIn(TARJETA, self.cliente.escenas)
        self.assertNotIn(TEXTO, self.cliente.entradas)
        self.assertNotIn(FONDO, self.cliente.entradas)
        self.assertEqual(self.cliente.filtros, {})
        self.assertEqual(list(self.carpeta.glob("*.png")), [])

    def test_p9_quita_tambien_las_entradas_del_medio(self):
        self.capa.preparar()
        self.cliente.entradas[medio_obs.IMAGEN] = {
            "inputKind": "image_source", "inputSettings": {}}
        self.cliente.entradas[medio_obs.MEDIO] = {
            "inputKind": "ffmpeg_source", "inputSettings": {}}
        self.capa.quitar_todo()
        self.assertNotIn(medio_obs.IMAGEN, self.cliente.entradas)
        self.assertNotIn(medio_obs.MEDIO, self.cliente.entradas)

    def test_p9_reintenta_el_borrado_del_png_hasta_lograrlo(self):
        self.capa.preparar()
        self.capa.mostrar("Hola", _estilo())
        ruta = next(self.carpeta.glob("*.png"))
        real = Path.unlink
        intentos = []
        esperas = []

        def unlink(objetivo, *args, **kwargs):
            intentos.append(1)
            if len(intentos) <= 2:
                raise PermissionError(32, "tomado")
            return real(objetivo, *args, **kwargs)

        with mock.patch.object(Path, "unlink", unlink):
            self.capa.quitar_todo(esperar=esperas.append)
        self.assertEqual(len(intentos), 3)
        self.assertEqual(esperas, [fondo_guardado._ESPERA_BORRADO] * 2)
        self.assertFalse(ruta.exists())

    def test_p9_si_el_png_sigue_tomado_no_falla(self):
        self.capa.preparar()
        self.capa.mostrar("Hola", _estilo())
        ruta = next(self.carpeta.glob("*.png"))
        intentos = []
        esperas = []

        def unlink(_objetivo, *_args, **_kwargs):
            intentos.append(1)
            raise PermissionError(32, "tomado")

        with mock.patch.object(Path, "unlink", unlink):
            self.capa.quitar_todo(esperar=esperas.append)
        self.assertEqual(len(intentos), fondo_guardado._INTENTOS_BORRADO)
        self.assertEqual(len(esperas), fondo_guardado._INTENTOS_BORRADO)
        self.assertTrue(ruta.exists())

    def test_p10_captura_devuelve_el_png_de_la_escena(self):
        self.capa.preparar()
        self.assertEqual(self.capa.captura(), b"PNG")
        pedido = self.cliente.pedidos("GetSourceScreenshot")[0]
        self.assertEqual(pedido["sourceName"], ESCENA)
        self.assertEqual(pedido["imageFormat"], "png")


class TestFondos(Base):
    def _mostrar(self, **cambios):
        self.cliente = ClienteFalso()
        estilo = _estilo(**cambios)
        color = estilo["color_fondo"]
        self.cliente.fondo_pixel = (
            int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16),
            round(255 * float(estilo["opacidad_fondo"]) / 100))
        self.capa = escena_guyrapu.EscenaGuyrapu(self.cliente)
        self.capa.preparar()
        return self.capa.mostrar("Hola", estilo)

    def test_p11_reusa_el_mismo_fondo(self):
        self._mostrar()
        ruta = next(self.carpeta.glob("*.png"))
        ruta.write_bytes(b"viejo")
        os.utime(ruta, (1, 1))
        self._mostrar()
        self.assertTrue(ruta.exists())
        self.assertEqual(ruta.read_bytes(), b"viejo")
        self.assertGreater(ruta.stat().st_mtime, 1)

    def test_p11_un_fondo_distinto_cambia_el_archivo(self):
        self._mostrar(color_fondo="#112233")
        primero = set(self.carpeta.glob("*.png"))
        self._mostrar(color_fondo="#445566")
        self.assertEqual(len(set(self.carpeta.glob("*.png")) - primero), 1)

    def test_p11_guarda_como_mucho_veinte_y_no_borra_el_puesto(self):
        self.carpeta.mkdir(parents=True)
        futuro = time.time() + 1000
        for numero in range(20):
            ruta = self.carpeta / f"fondo-viejo{numero:02d}.png"
            ruta.write_bytes(b"viejo")
            os.utime(ruta, (futuro, futuro))
        anteriores = set(self.carpeta.glob("*.png"))
        self._mostrar(color_fondo="#778899")
        actuales = set(self.carpeta.glob("*.png"))
        nuevos = actuales - anteriores
        self.assertEqual(len(actuales), 20)
        self.assertEqual(len(nuevos), 1)
        self.assertTrue(next(iter(nuevos)).exists())


if __name__ == "__main__":
    unittest.main()
